"""Complaint intake, SLA, communication, and controlled resolution."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    Borrower,
    Branch,
    ComplaintCase,
    ComplaintEvent,
    LoanApplication,
    Membership,
    StaffAssignment,
    User,
)
from dogeapi.operations import approval_service, mvp_service
from dogeapi.operations.complaint_schemas import ComplaintCreate, ComplaintResolution

ALLOWED_ROLES = {"ops_admin", "branch_manager", "loan_officer", "reviewer", "finance", "auditor"}
SLA_HOURS = {
    "urgent": (1, 24),
    "high": (4, 48),
    "normal": (8, 120),
    "low": (24, 240),
}


async def _case(session: AsyncSession, org_id: UUID, case_id: UUID, *, lock: bool = False) -> ComplaintCase:
    statement = select(ComplaintCase).where(ComplaintCase.org_id == org_id, ComplaintCase.id == case_id)
    if lock:
        statement = statement.with_for_update()
    item = await session.scalar(statement)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Complaint tidak ditemukan")
    return item


async def _ensure_access(session: AsyncSession, org_id: UUID, actor_id: UUID, item: ComplaintCase) -> None:
    await mvp_service.ensure_operational_access(session, org_id, actor_id, item.branch_id, ALLOWED_ROLES)


def _event(
    session: AsyncSession,
    item: ComplaintCase,
    actor_id: UUID | None,
    event_type: str,
    message: str | None,
    *,
    direction: str | None = None,
    channel: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
) -> None:
    session.add(
        ComplaintEvent(
            org_id=item.org_id,
            complaint_id=item.id,
            actor_user_id=actor_id,
            event_type=event_type,
            direction=direction,
            channel=channel,
            from_status=from_status,
            to_status=to_status,
            message=message,
        )
    )


async def create_complaint(session: AsyncSession, org_id: UUID, actor_id: UUID, data: ComplaintCreate) -> ComplaintCase:
    await mvp_service.ensure_operational_access(session, org_id, actor_id, data.branch_id, ALLOWED_ROLES)
    branch = await session.scalar(select(Branch).where(Branch.org_id == org_id, Branch.id == data.branch_id))
    borrower = await session.scalar(select(Borrower).where(Borrower.org_id == org_id, Borrower.id == data.borrower_id))
    if branch is None or borrower is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cabang atau nasabah tidak valid pada tenant aktif")
    if data.application_id is not None:
        application = await session.scalar(
            select(LoanApplication).where(
                LoanApplication.org_id == org_id,
                LoanApplication.id == data.application_id,
                LoanApplication.borrower_id == data.borrower_id,
                LoanApplication.branch_id == data.branch_id,
            )
        )
        if application is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Pengajuan tidak terkait nasabah dan cabang")
    now = datetime.now(UTC)
    response_hours, resolution_hours = SLA_HOURS[data.priority]
    item = ComplaintCase(
        org_id=org_id,
        ticket_no=f"CMP-{now:%Y%m%d}-{secrets.token_hex(3).upper()}",
        reported_by_user_id=actor_id,
        response_due_at=now + timedelta(hours=response_hours),
        resolution_due_at=now + timedelta(hours=resolution_hours),
        **data.model_dump(),
    )
    session.add(item)
    await session.flush()
    _event(
        session,
        item,
        actor_id,
        "ComplaintCreated",
        data.description,
        direction="inbound",
        channel=data.channel,
        to_status="new",
    )
    await session.flush()
    return item


async def _visible_branch_ids(session: AsyncSession, org_id: UUID, actor_id: UUID) -> list[UUID] | None:
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == actor_id)
    )
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No membership in active tenant")
    if membership.role.value in {"owner", "admin"}:
        return None
    return list(
        await session.scalars(
            select(StaffAssignment.branch_id).where(
                StaffAssignment.org_id == org_id,
                StaffAssignment.user_id == actor_id,
                StaffAssignment.operational_role.in_(ALLOWED_ROLES),
                StaffAssignment.is_active,
            )
        )
    )


async def list_complaints(session: AsyncSession, org_id: UUID, actor_id: UUID) -> list[dict[str, object]]:
    branch_ids = await _visible_branch_ids(session, org_id, actor_id)
    statement = (
        select(ComplaintCase, Borrower, Branch, User.full_name)
        .join(Borrower, (Borrower.id == ComplaintCase.borrower_id) & (Borrower.org_id == org_id))
        .join(Branch, (Branch.id == ComplaintCase.branch_id) & (Branch.org_id == org_id))
        .outerjoin(User, User.id == ComplaintCase.assigned_to_user_id)
        .where(ComplaintCase.org_id == org_id)
    )
    if branch_ids is not None:
        statement = statement.where(ComplaintCase.branch_id.in_(branch_ids))
    rows = (await session.execute(statement.order_by(ComplaintCase.created_at.desc()))).all()
    now = datetime.now(UTC)
    return [
        {
            "id": item.id,
            "ticket_no": item.ticket_no,
            "borrower_id": borrower.id,
            "borrower_name": borrower.full_name,
            "branch_id": branch.id,
            "branch_code": branch.code,
            "category": item.category,
            "channel": item.channel,
            "priority": item.priority,
            "status": item.status,
            "subject": item.subject,
            "assigned_to_name": assigned_name,
            "response_due_at": item.response_due_at,
            "resolution_due_at": item.resolution_due_at,
            "response_overdue": item.acknowledged_at is None and item.response_due_at < now,
            "resolution_overdue": item.status != "resolved" and item.resolution_due_at < now,
            "vulnerable_customer": item.vulnerable_customer,
            "regulator_reportable": item.regulator_reportable,
            "escalation_level": item.escalation_level,
            "created_at": item.created_at,
        }
        for item, borrower, branch, assigned_name in rows
    ]


async def get_complaint(session: AsyncSession, org_id: UUID, actor_id: UUID, case_id: UUID) -> dict[str, object]:
    item = await _case(session, org_id, case_id)
    await _ensure_access(session, org_id, actor_id, item)
    borrower = await session.scalar(select(Borrower).where(Borrower.org_id == org_id, Borrower.id == item.borrower_id))
    branch = await session.scalar(select(Branch).where(Branch.org_id == org_id, Branch.id == item.branch_id))
    events = list(
        await session.scalars(
            select(ComplaintEvent)
            .where(ComplaintEvent.org_id == org_id, ComplaintEvent.complaint_id == item.id)
            .order_by(ComplaintEvent.occurred_at.desc())
        )
    )
    return {
        "id": item.id,
        "ticket_no": item.ticket_no,
        "borrower": {"id": item.borrower_id, "name": borrower.full_name if borrower else "—"},
        "branch": {
            "id": item.branch_id,
            "code": branch.code if branch else "—",
            "name": branch.name if branch else "—",
        },
        "application_id": item.application_id,
        "reported_by_user_id": item.reported_by_user_id,
        "assigned_to_user_id": item.assigned_to_user_id,
        "category": item.category,
        "channel": item.channel,
        "priority": item.priority,
        "status": item.status,
        "subject": item.subject,
        "description": item.description,
        "vulnerable_customer": item.vulnerable_customer,
        "regulator_reportable": item.regulator_reportable,
        "response_due_at": item.response_due_at,
        "resolution_due_at": item.resolution_due_at,
        "acknowledged_at": item.acknowledged_at,
        "resolution_summary": item.resolution_summary,
        "outcome": item.outcome,
        "compensation_amount": item.compensation_amount,
        "resolved_by_user_id": item.resolved_by_user_id,
        "resolved_at": item.resolved_at,
        "escalation_level": item.escalation_level,
        "reopened_count": item.reopened_count,
        "created_at": item.created_at,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "actor_user_id": event.actor_user_id,
                "direction": event.direction,
                "channel": event.channel,
                "from_status": event.from_status,
                "to_status": event.to_status,
                "message": event.message,
                "occurred_at": event.occurred_at,
            }
            for event in events
        ],
    }


async def assign_complaint(
    session: AsyncSession, org_id: UUID, actor_id: UUID, case_id: UUID, assigned_to_user_id: UUID, reason: str
) -> ComplaintCase:
    item = await _case(session, org_id, case_id, lock=True)
    await _ensure_access(session, org_id, actor_id, item)
    assignment = await session.scalar(
        select(StaffAssignment).where(
            StaffAssignment.org_id == org_id,
            StaffAssignment.user_id == assigned_to_user_id,
            StaffAssignment.branch_id == item.branch_id,
            StaffAssignment.is_active,
        )
    )
    if assignment is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Owner tidak memiliki penugasan aktif di cabang kasus"
        )
    previous = item.status
    item.assigned_to_user_id = assigned_to_user_id
    if item.status == "new":
        item.status = "assigned"
    _event(session, item, actor_id, "ComplaintAssigned", reason, from_status=previous, to_status=item.status)
    await session.flush()
    return item


async def add_communication(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    case_id: UUID,
    direction: str,
    channel: str,
    message: str,
) -> ComplaintCase:
    item = await _case(session, org_id, case_id, lock=True)
    await _ensure_access(session, org_id, actor_id, item)
    if item.status in {"resolved", "pending_resolution"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complaint tidak menerima komunikasi pada status ini")
    previous = item.status
    if direction == "outbound" and item.acknowledged_at is None:
        item.acknowledged_at = datetime.now(UTC)
    if item.status in {"new", "assigned"}:
        item.status = "investigating"
    _event(
        session,
        item,
        actor_id,
        "ComplaintCommunicationRecorded",
        message,
        direction=direction,
        channel=channel,
        from_status=previous,
        to_status=item.status,
    )
    await session.flush()
    return item


async def request_resolution(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    case_id: UUID,
    data: ComplaintResolution,
) -> ComplaintCase:
    item = await _case(session, org_id, case_id, lock=True)
    await _ensure_access(session, org_id, actor_id, item)
    if item.status not in {"assigned", "investigating", "reopened"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complaint belum siap diajukan untuk resolusi")
    if item.assigned_to_user_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Owner complaint wajib ditetapkan")
    previous = item.status
    item.status = "pending_resolution"
    item.resolution_summary = data.resolution_summary
    item.outcome = data.outcome
    item.compensation_amount = data.compensation_amount
    await approval_service.request_approval(
        session,
        org_id=org_id,
        branch_id=item.branch_id,
        aggregate_type="complaint",
        aggregate_id=item.id,
        aggregate_reference=item.ticket_no,
        action="resolve_complaint",
        requested_by=actor_id,
        assigned_role="branch_manager",
        reason=data.resolution_summary,
        payload={
            "borrower_id": str(item.borrower_id),
            "application_id": str(item.application_id) if item.application_id else None,
            "category": item.category,
            "outcome": data.outcome,
            "compensation_amount": str(data.compensation_amount),
            "regulator_reportable": item.regulator_reportable,
        },
        priority="high" if item.regulator_reportable or data.compensation_amount > 0 else item.priority,
        sla_hours=4,
    )
    _event(
        session,
        item,
        actor_id,
        "ComplaintResolutionRequested",
        data.resolution_summary,
        from_status=previous,
        to_status=item.status,
    )
    await session.flush()
    return item


async def reopen_complaint(
    session: AsyncSession, org_id: UUID, actor_id: UUID, case_id: UUID, reason: str
) -> ComplaintCase:
    item = await _case(session, org_id, case_id, lock=True)
    await _ensure_access(session, org_id, actor_id, item)
    if item.status != "resolved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Hanya complaint resolved yang dapat dibuka kembali")
    previous = item.status
    item.status = "reopened"
    item.reopened_count += 1
    item.resolved_by_user_id = None
    item.resolved_at = None
    _event(session, item, actor_id, "ComplaintReopened", reason, from_status=previous, to_status=item.status)
    await session.flush()
    return item


async def escalate_overdue(session: AsyncSession, org_id: UUID, actor_id: UUID) -> int:
    await mvp_service.ensure_any_operational_role(session, org_id, actor_id, {"ops_admin", "branch_manager", "auditor"})
    now = datetime.now(UTC)
    rows = list(
        await session.scalars(
            select(ComplaintCase)
            .where(
                ComplaintCase.org_id == org_id,
                ComplaintCase.status.not_in({"resolved", "pending_resolution"}),
                (
                    ((ComplaintCase.acknowledged_at.is_(None)) & (ComplaintCase.response_due_at < now))
                    | (ComplaintCase.resolution_due_at < now)
                ),
                ComplaintCase.escalation_level < 2,
            )
            .with_for_update()
        )
    )
    for item in rows:
        item.escalation_level += 1
        item.escalated_at = now
        item.priority = "urgent" if item.escalation_level >= 2 else "high"
        _event(
            session,
            item,
            actor_id,
            "ComplaintSlaEscalated",
            f"SLA escalation level {item.escalation_level}",
            to_status=item.status,
        )
    await session.flush()
    return len(rows)
