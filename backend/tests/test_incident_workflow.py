from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    ApprovalRequest,
    Asset,
    Borrower,
    Branch,
    IncidentEvent,
    LoanApplication,
    Membership,
    Organization,
    Role,
    User,
)
from dogeapi.operations import approval_service, incident_service, mvp_service
from dogeapi.operations.incident_schemas import IncidentResolutionRequest, IncidentTriage
from dogeapi.operations.mvp_schemas import IncidentCreate


async def test_incident_investigation_resolution_and_reopen(db_session: AsyncSession) -> None:
    suffix = uuid4().hex[:8]
    org = Organization(slug=f"incident-{suffix}", name="Incident Test")
    maker = User(email=f"maker-{suffix}@example.com", full_name="Investigator")
    checker = User(email=f"checker-{suffix}@example.com", full_name="Branch Manager")
    db_session.add_all([org, maker, checker])
    await db_session.flush()
    branch = Branch(org_id=org.id, code="JKT-01", name="Jakarta", city="Jakarta")
    borrower = Borrower(
        org_id=org.id,
        customer_reference=f"CUS-{suffix}",
        full_name="Nasabah Incident",
        phone_masked="0812••••1234",
    )
    db_session.add_all([branch, borrower])
    await db_session.flush()
    application = LoanApplication(
        org_id=org.id,
        branch_id=branch.id,
        borrower_id=borrower.id,
        application_no=f"PG-{suffix}",
        status="active",
        priority="high",
        asset_category="emas",
        requested_amount=Decimal("5000000"),
    )
    db_session.add(application)
    await db_session.flush()
    asset = Asset(
        org_id=org.id,
        application_id=application.id,
        asset_code=f"AST-{suffix}",
        category="emas",
        brand="Antam",
        model="10 gram",
        collateral_status="stored",
    )
    db_session.add(asset)
    db_session.add_all(
        [
            Membership(org_id=org.id, user_id=maker.id, role=Role.ADMIN),
            Membership(org_id=org.id, user_id=checker.id, role=Role.ADMIN),
        ]
    )
    await db_session.flush()

    incident = await mvp_service.create_incident(
        db_session,
        org.id,
        maker.id,
        IncidentCreate(
            application_id=application.id,
            incident_type="seal_mismatch",
            severity="high",
            description="Nomor segel fisik tidak sesuai dengan register custody",
        ),
    )
    assert asset.collateral_status == "incident_hold"
    assert incident.due_at is not None

    await incident_service.triage_incident(
        db_session,
        org.id,
        maker.id,
        incident.id,
        IncidentTriage(
            assigned_to_user_id=maker.id,
            due_at=datetime.now(UTC) + timedelta(hours=4),
            root_cause="Kesalahan pencatatan nomor segel pada proses dispatch",
            action_plan="Verifikasi CCTV, cocokkan log serah terima, lalu perbarui kontrol dua petugas",
        ),
    )
    await incident_service.add_note(
        db_session,
        org.id,
        maker.id,
        incident.id,
        "CCTV dan berita acara menunjukkan kondisi agunan tetap utuh.",
    )
    await incident_service.request_resolution(
        db_session,
        org.id,
        maker.id,
        incident.id,
        IncidentResolutionRequest(
            resolution_note="Nomor segel direkonsiliasi dan prosedur dual control telah dijalankan ulang."
        ),
    )
    approval = await db_session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.org_id == org.id,
            ApprovalRequest.aggregate_type == "incident",
            ApprovalRequest.aggregate_id == incident.id,
        )
    )
    assert incident.status == "pending_resolution"
    assert approval is not None

    await approval_service.decide_approval(
        db_session,
        org.id,
        approval.id,
        checker.id,
        "approved",
        "Root cause, evidence, dan corrective action telah diverifikasi",
    )
    assert incident.status == "resolved"
    assert incident.resolved_by_user_id == checker.id
    assert asset.collateral_status == "stored"

    await incident_service.reopen_incident(
        db_session,
        org.id,
        checker.id,
        incident.id,
        "Audit lanjutan menemukan bukti serah terima yang perlu diverifikasi ulang",
    )
    assert incident.status == "reopened"
    assert incident.reopened_count == 1
    assert asset.collateral_status == "incident_hold"
    event_count = await db_session.scalar(
        select(func.count(IncidentEvent.id)).where(
            IncidentEvent.org_id == org.id,
            IncidentEvent.incident_id == incident.id,
        )
    )
    assert event_count == 6
