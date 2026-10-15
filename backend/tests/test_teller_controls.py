from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import ApprovalRequest, Branch, Cashbox, Membership, Organization, Role, TellerSession, User
from dogeapi.operations import approval_service, erp_service


async def _finance_team(session: AsyncSession) -> tuple[Organization, Branch, Cashbox, User, User, User]:
    suffix = uuid4().hex[:8]
    org = Organization(slug=f"teller-{suffix}", name="Teller Controls")
    teller = User(email=f"teller-{suffix}@example.com", full_name="Teller Satu")
    other_teller = User(email=f"other-{suffix}@example.com", full_name="Teller Dua")
    checker = User(email=f"checker-{suffix}@example.com", full_name="Branch Manager")
    session.add_all([org, teller, other_teller, checker])
    await session.flush()
    branch = Branch(org_id=org.id, code="JKT-01", name="Jakarta", city="Jakarta")
    session.add(branch)
    await session.flush()
    cashbox = Cashbox(
        org_id=org.id,
        branch_id=branch.id,
        code="KAS-01",
        name="Kas Utama",
        balance=Decimal("1000000"),
    )
    session.add(cashbox)
    session.add_all(
        [
            Membership(org_id=org.id, user_id=teller.id, role=Role.MEMBER),
            Membership(org_id=org.id, user_id=other_teller.id, role=Role.MEMBER),
            Membership(org_id=org.id, user_id=checker.id, role=Role.ADMIN),
        ]
    )
    await session.flush()
    return org, branch, cashbox, teller, other_teller, checker


async def test_cashbox_is_exclusive_and_variance_requires_reason(db_session: AsyncSession) -> None:
    org, _branch, cashbox, teller, other_teller, _checker = await _finance_team(db_session)
    opened = await erp_service.open_teller_session(db_session, org.id, teller.id, cashbox.id)

    with pytest.raises(HTTPException) as occupied:
        await erp_service.open_teller_session(db_session, org.id, other_teller.id, cashbox.id)
    assert occupied.value.status_code == 409

    with pytest.raises(HTTPException) as missing_reason:
        await erp_service.close_teller_session(
            db_session,
            org.id,
            teller.id,
            opened.id,
            Decimal("990000"),
            None,
        )
    assert missing_reason.value.status_code == 422


async def test_teller_variance_requires_independent_approval(db_session: AsyncSession) -> None:
    org, _branch, cashbox, teller, _other_teller, checker = await _finance_team(db_session)
    opened = await erp_service.open_teller_session(db_session, org.id, teller.id, cashbox.id)

    pending = await erp_service.close_teller_session(
        db_session,
        org.id,
        teller.id,
        opened.id,
        Decimal("990000"),
        "Kas fisik kurang saat cash count akhir shift",
    )
    approval = await db_session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.org_id == org.id,
            ApprovalRequest.aggregate_type == "teller_session",
            ApprovalRequest.aggregate_id == opened.id,
        )
    )

    assert pending.status == "variance_pending"
    assert pending.variance_amount == Decimal("-10000")
    assert approval is not None and approval.status == "pending"

    with pytest.raises(HTTPException) as maker_checker:
        await approval_service.decide_approval(
            db_session,
            org.id,
            approval.id,
            teller.id,
            "approved",
            "Mencoba menyetujui transaksi sendiri",
        )
    assert maker_checker.value.status_code == 409

    await approval_service.decide_approval(
        db_session,
        org.id,
        approval.id,
        checker.id,
        "approved",
        "Selisih telah diverifikasi dengan berita acara",
    )
    await db_session.refresh(opened)

    assert opened.status == "closed_with_variance"
    assert opened.variance_approved_by_user_id == checker.id
    assert opened.variance_approved_at is not None


async def test_rejected_variance_reopens_teller_session(db_session: AsyncSession) -> None:
    org, _branch, cashbox, teller, _other_teller, checker = await _finance_team(db_session)
    opened = await erp_service.open_teller_session(db_session, org.id, teller.id, cashbox.id)
    await erp_service.close_teller_session(
        db_session,
        org.id,
        teller.id,
        opened.id,
        Decimal("1010000"),
        "Kas fisik lebih saat cash count akhir shift",
    )
    approval = await db_session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.org_id == org.id,
            ApprovalRequest.aggregate_id == opened.id,
        )
    )
    assert approval is not None

    await approval_service.decide_approval(
        db_session,
        org.id,
        approval.id,
        checker.id,
        "rejected",
        "Cash count harus diulang dengan saksi supervisor",
    )
    reopened = await db_session.scalar(select(TellerSession).where(TellerSession.id == opened.id))

    assert reopened is not None and reopened.status == "open"
    assert reopened.actual_closing_balance is None
    assert reopened.variance_amount is None
    assert reopened.closed_at is None
