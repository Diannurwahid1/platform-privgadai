from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    ApprovalRequest,
    Borrower,
    Branch,
    ComplaintEvent,
    LoanApplication,
    Membership,
    Organization,
    Role,
    StaffAssignment,
    User,
)
from dogeapi.operations import approval_service, complaint_service
from dogeapi.operations.complaint_schemas import ComplaintCreate, ComplaintResolution


async def test_complaint_sla_communication_resolution_and_reopen(db_session: AsyncSession) -> None:
    suffix = uuid4().hex[:8]
    org = Organization(slug=f"complaint-{suffix}", name="Complaint Test")
    maker = User(email=f"maker-{suffix}@example.com", full_name="Complaint Officer")
    checker = User(email=f"checker-{suffix}@example.com", full_name="Branch Manager")
    db_session.add_all([org, maker, checker])
    await db_session.flush()
    branch = Branch(org_id=org.id, code="JKT-01", name="Jakarta", city="Jakarta")
    borrower = Borrower(
        org_id=org.id,
        customer_reference=f"CUS-{suffix}",
        full_name="Nasabah Complaint",
        phone_masked="0812••••4321",
    )
    db_session.add_all([branch, borrower])
    await db_session.flush()
    application = LoanApplication(
        org_id=org.id,
        branch_id=branch.id,
        borrower_id=borrower.id,
        application_no=f"PG-{suffix}",
        status="active",
        priority="normal",
        asset_category="emas",
        requested_amount=Decimal("4000000"),
    )
    db_session.add(application)
    db_session.add_all(
        [
            Membership(org_id=org.id, user_id=maker.id, role=Role.MEMBER),
            Membership(org_id=org.id, user_id=checker.id, role=Role.ADMIN),
        ]
    )
    await db_session.flush()
    db_session.add(
        StaffAssignment(
            org_id=org.id,
            user_id=maker.id,
            branch_id=branch.id,
            operational_role="reviewer",
            is_active=True,
        )
    )
    await db_session.flush()

    complaint = await complaint_service.create_complaint(
        db_session,
        org.id,
        maker.id,
        ComplaintCreate(
            branch_id=branch.id,
            borrower_id=borrower.id,
            application_id=application.id,
            category="service",
            channel="branch",
            priority="high",
            subject="Waktu layanan pencairan melebihi penjelasan awal",
            description="Nasabah menyampaikan keterlambatan pencairan dan meminta penjelasan tertulis.",
            vulnerable_customer=True,
        ),
    )
    assert complaint.status == "new"
    assert complaint.response_due_at < complaint.resolution_due_at

    await complaint_service.assign_complaint(
        db_session,
        org.id,
        checker.id,
        complaint.id,
        maker.id,
        "Reviewer cabang ditetapkan sebagai case owner",
    )
    await complaint_service.add_communication(
        db_session,
        org.id,
        maker.id,
        complaint.id,
        "outbound",
        "phone",
        "Keluhan telah diterima dan sedang ditelusuri bersama tim pencairan.",
    )
    assert complaint.status == "investigating"
    assert complaint.acknowledged_at is not None

    await complaint_service.request_resolution(
        db_session,
        org.id,
        maker.id,
        complaint.id,
        ComplaintResolution(
            resolution_summary="Keterlambatan dikonfirmasi, penjelasan diberikan, dan biaya layanan dikembalikan.",
            outcome="upheld",
            compensation_amount=Decimal("50000"),
        ),
    )
    approval = await db_session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.org_id == org.id,
            ApprovalRequest.aggregate_type == "complaint",
            ApprovalRequest.aggregate_id == complaint.id,
        )
    )
    assert complaint.status == "pending_resolution"
    assert approval is not None and approval.priority == "high"

    with pytest.raises(HTTPException) as maker_checker:
        await approval_service.decide_approval(
            db_session, org.id, approval.id, maker.id, "approved", "Maker mencoba menyetujui kasus sendiri"
        )
    assert maker_checker.value.status_code == 409

    await approval_service.decide_approval(
        db_session,
        org.id,
        approval.id,
        checker.id,
        "approved",
        "Kronologi, komunikasi, outcome, dan kompensasi telah diverifikasi",
    )
    assert complaint.status == "resolved"
    assert complaint.resolved_by_user_id == checker.id

    await complaint_service.reopen_complaint(
        db_session,
        org.id,
        checker.id,
        complaint.id,
        "Nasabah menyampaikan bahwa kompensasi belum diterima pada rekening tujuan",
    )
    assert complaint.status == "reopened"
    assert complaint.reopened_count == 1
    event_count = await db_session.scalar(
        select(func.count(ComplaintEvent.id)).where(
            ComplaintEvent.org_id == org.id,
            ComplaintEvent.complaint_id == complaint.id,
        )
    )
    assert event_count == 6


async def test_complaint_sla_escalation_is_bounded(db_session: AsyncSession) -> None:
    suffix = uuid4().hex[:8]
    org = Organization(slug=f"complaint-sla-{suffix}", name="Complaint SLA")
    actor = User(email=f"owner-{suffix}@example.com", full_name="Owner")
    db_session.add_all([org, actor])
    await db_session.flush()
    branch = Branch(org_id=org.id, code="SBY-01", name="Surabaya", city="Surabaya")
    borrower = Borrower(
        org_id=org.id,
        customer_reference=f"CUS-{suffix}",
        full_name="Nasabah SLA",
        phone_masked="0813••••0001",
    )
    db_session.add_all([branch, borrower, Membership(org_id=org.id, user_id=actor.id, role=Role.ADMIN)])
    await db_session.flush()
    complaint = await complaint_service.create_complaint(
        db_session,
        org.id,
        actor.id,
        ComplaintCreate(
            branch_id=branch.id,
            borrower_id=borrower.id,
            category="billing",
            channel="email",
            subject="Permintaan rincian biaya layanan",
            description="Nasabah meminta penjelasan tertulis mengenai rincian biaya pada kontrak.",
        ),
    )
    complaint.response_due_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.flush()

    assert await complaint_service.escalate_overdue(db_session, org.id, actor.id) == 1
    assert complaint.escalation_level == 1 and complaint.priority == "high"
    assert await complaint_service.escalate_overdue(db_session, org.id, actor.id) == 1
    assert complaint.escalation_level == 2 and complaint.priority == "urgent"
    assert await complaint_service.escalate_overdue(db_session, org.id, actor.id) == 0
