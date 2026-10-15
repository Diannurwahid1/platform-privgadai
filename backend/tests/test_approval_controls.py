from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import Branch, Membership, Organization, Role, StaffAssignment, User
from dogeapi.operations import approval_service


async def _approval_team(session: AsyncSession) -> tuple[Organization, Branch, User, User, User]:
    suffix = uuid4().hex[:8]
    org = Organization(slug=f"approval-{suffix}", name="Approval Test")
    maker = User(email=f"maker-{suffix}@example.com", full_name="Maker")
    delegator = User(email=f"delegator-{suffix}@example.com", full_name="Reviewer")
    delegate = User(email=f"delegate-{suffix}@example.com", full_name="Delegate")
    session.add_all([org, maker, delegator, delegate])
    await session.flush()
    branch = Branch(org_id=org.id, code="JKT-01", name="Jakarta", city="Jakarta")
    session.add(branch)
    await session.flush()
    session.add_all(
        [
            Membership(org_id=org.id, user_id=maker.id, role=Role.MEMBER),
            Membership(org_id=org.id, user_id=delegator.id, role=Role.MEMBER),
            Membership(org_id=org.id, user_id=delegate.id, role=Role.MEMBER),
        ]
    )
    await session.flush()
    session.add(
        StaffAssignment(
            org_id=org.id,
            user_id=delegator.id,
            branch_id=branch.id,
            operational_role="reviewer",
            is_active=True,
        )
    )
    await session.flush()
    return org, branch, maker, delegator, delegate


async def test_delegated_decision_keeps_delegation_reference(db_session: AsyncSession) -> None:
    org, branch, maker, delegator, delegate = await _approval_team(db_session)
    now = datetime.now(UTC)
    delegation = await approval_service.create_delegation(
        db_session,
        org_id=org.id,
        actor_id=delegator.id,
        delegator_user_id=delegator.id,
        delegate_user_id=delegate.id,
        branch_id=branch.id,
        assigned_role="reviewer",
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(days=2),
        reason="Reviewer sedang menjalankan tugas lapangan di cabang lain",
    )
    approval = await approval_service.request_approval(
        db_session,
        org_id=org.id,
        branch_id=branch.id,
        aggregate_type="test_record",
        aggregate_id=uuid4(),
        aggregate_reference="TEST-001",
        action="approve_test_record",
        requested_by=maker.id,
        assigned_role="reviewer",
        reason="Bukti pengujian lengkap dan siap diperiksa",
        payload={},
    )

    decided = await approval_service.decide_approval(
        db_session, org.id, approval.id, delegate.id, "approved", "Diperiksa atas delegasi yang masih berlaku"
    )

    assert decided.status == "approved"
    assert decided.decided_under_delegation_id == delegation.id


async def test_overdue_sweep_escalates_role_priority_and_due_date(db_session: AsyncSession) -> None:
    org, branch, maker, delegator, _delegate = await _approval_team(db_session)
    approval = await approval_service.request_approval(
        db_session,
        org_id=org.id,
        branch_id=branch.id,
        aggregate_type="test_record",
        aggregate_id=uuid4(),
        aggregate_reference="TEST-OVERDUE",
        action="approve_test_record",
        requested_by=maker.id,
        assigned_role="reviewer",
        reason="Permintaan sengaja dibuat jatuh tempo untuk pengujian",
        payload={},
    )
    approval.due_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.flush()

    count = await approval_service.escalate_overdue_approvals(db_session, org.id, delegator.id)

    assert count == 1
    assert approval.escalation_level == 1
    assert approval.assigned_role == "branch_manager"
    assert approval.priority == "high"
    assert approval.due_at is not None and approval.due_at > datetime.now(UTC)
