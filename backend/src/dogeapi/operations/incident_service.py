"""Incident register, investigation, and maker-checker resolution."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    Asset,
    Borrower,
    Branch,
    Incident,
    IncidentEvent,
    LoanApplication,
    Membership,
    StaffAssignment,
    User,
)
from dogeapi.operations import approval_service, mvp_service
from dogeapi.operations.incident_schemas import IncidentResolutionRequest, IncidentTriage

ALLOWED_ROLES = {"ops_admin", "branch_manager", "reviewer", "custodian", "auditor"}


async def _incident(session: AsyncSession, org_id: UUID, incident_id: UUID, *, lock: bool = False) -> Incident:
    statement = select(Incident).where(Incident.org_id == org_id, Incident.id == incident_id)
    if lock:
        statement = statement.with_for_update()
    item = await session.scalar(statement)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident tidak ditemukan")
    return item


async def _ensure_access(session: AsyncSession, org_id: UUID, actor_id: UUID, item: Incident) -> LoanApplication:
    application = await session.scalar(
        select(LoanApplication).where(
            LoanApplication.org_id == org_id,
            LoanApplication.id == item.application_id,
        )
    )
    if application is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Pengajuan terkait incident tidak ditemukan")
    await mvp_service.ensure_operational_access(session, org_id, actor_id, application.branch_id, ALLOWED_ROLES)
    return application


def add_event(
    session: AsyncSession,
    item: Incident,
    actor_id: UUID | None,
    event_type: str,
    note: str | None,
    *,
    from_status: str | None = None,
    to_status: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    session.add(
        IncidentEvent(
            org_id=item.org_id,
            incident_id=item.id,
            actor_user_id=actor_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            note=note,
            event_metadata=metadata or {},
        )
    )


async def list_incidents(session: AsyncSession, org_id: UUID, actor_id: UUID) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(session, org_id, actor_id, ALLOWED_ROLES)
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == actor_id)
    )
    statement = (
        select(Incident, LoanApplication, Borrower, Branch, User.full_name)
        .join(
            LoanApplication,
            (LoanApplication.id == Incident.application_id) & (LoanApplication.org_id == org_id),
        )
        .join(Borrower, (Borrower.id == LoanApplication.borrower_id) & (Borrower.org_id == org_id))
        .join(Branch, (Branch.id == LoanApplication.branch_id) & (Branch.org_id == org_id))
        .outerjoin(User, User.id == Incident.assigned_to_user_id)
        .where(Incident.org_id == org_id)
    )
    if membership is not None and membership.role.value not in {"owner", "admin"}:
        branch_ids = list(
            await session.scalars(
                select(StaffAssignment.branch_id).where(
                    StaffAssignment.org_id == org_id,
                    StaffAssignment.user_id == actor_id,
                    StaffAssignment.operational_role.in_(ALLOWED_ROLES),
                    StaffAssignment.is_active,
                )
            )
        )
        statement = statement.where(LoanApplication.branch_id.in_(branch_ids))
    rows = (await session.execute(statement.order_by(Incident.created_at.desc()))).all()
    return [
        {
            "id": item.id,
            "application_id": application.id,
            "application_no": application.application_no,
            "borrower_name": borrower.full_name,
            "branch_code": branch.code,
            "branch_name": branch.name,
            "incident_type": item.incident_type,
            "severity": item.severity,
            "status": item.status,
            "description": item.description,
            "assigned_to_user_id": item.assigned_to_user_id,
            "assigned_to_name": assignee_name,
            "due_at": item.due_at,
            "is_overdue": bool(item.due_at and item.due_at < datetime.now(UTC) and item.status != "resolved"),
            "created_at": item.created_at,
        }
        for item, application, borrower, branch, assignee_name in rows
    ]


async def get_incident(session: AsyncSession, org_id: UUID, actor_id: UUID, incident_id: UUID) -> dict[str, object]:
    item = await _incident(session, org_id, incident_id)
    application = await _ensure_access(session, org_id, actor_id, item)
    borrower = await session.scalar(
        select(Borrower).where(Borrower.org_id == org_id, Borrower.id == application.borrower_id)
    )
    branch = await session.scalar(select(Branch).where(Branch.org_id == org_id, Branch.id == application.branch_id))
    asset = await session.scalar(select(Asset).where(Asset.org_id == org_id, Asset.application_id == application.id))
    events = list(
        await session.scalars(
            select(IncidentEvent)
            .where(IncidentEvent.org_id == org_id, IncidentEvent.incident_id == item.id)
            .order_by(IncidentEvent.occurred_at.desc())
        )
    )
    return {
        "id": item.id,
        "application": {
            "id": application.id,
            "application_no": application.application_no,
            "borrower_name": borrower.full_name if borrower else "—",
            "branch_id": application.branch_id,
            "branch_code": branch.code if branch else "—",
            "branch_name": branch.name if branch else "—",
        },
        "asset": {
            "asset_code": asset.asset_code if asset else "—",
            "label": " ".join(value for value in (asset.brand, asset.model) if value) if asset else "—",
            "collateral_status": asset.collateral_status if asset else "unknown",
        },
        "incident_type": item.incident_type,
        "severity": item.severity,
        "status": item.status,
        "description": item.description,
        "reported_by_user_id": item.reported_by_user_id,
        "assigned_to_user_id": item.assigned_to_user_id,
        "root_cause": item.root_cause,
        "action_plan": item.action_plan,
        "due_at": item.due_at,
        "resolution_note": item.resolution_note,
        "resolved_by_user_id": item.resolved_by_user_id,
        "resolved_at": item.resolved_at,
        "reopened_count": item.reopened_count,
        "created_at": item.created_at,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "actor_user_id": event.actor_user_id,
                "from_status": event.from_status,
                "to_status": event.to_status,
                "note": event.note,
                "metadata": event.event_metadata,
                "occurred_at": event.occurred_at,
            }
            for event in events
        ],
    }


async def triage_incident(
    session: AsyncSession, org_id: UUID, actor_id: UUID, incident_id: UUID, data: IncidentTriage
) -> Incident:
    item = await _incident(session, org_id, incident_id, lock=True)
    await _ensure_access(session, org_id, actor_id, item)
    if item.status not in {"open", "reopened", "investigating"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Incident tidak dapat ditriase pada status ini")
    assignee = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == data.assigned_to_user_id)
    )
    if assignee is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Owner incident bukan anggota tenant aktif")
    previous = item.status
    item.status = "investigating"
    item.assigned_to_user_id = data.assigned_to_user_id
    item.due_at = data.due_at
    item.root_cause = data.root_cause
    item.action_plan = data.action_plan
    add_event(
        session,
        item,
        actor_id,
        "IncidentTriaged",
        data.action_plan,
        from_status=previous,
        to_status=item.status,
        metadata={"assigned_to_user_id": str(data.assigned_to_user_id), "due_at": data.due_at.isoformat()},
    )
    await session.flush()
    return item


async def add_note(session: AsyncSession, org_id: UUID, actor_id: UUID, incident_id: UUID, note: str) -> Incident:
    item = await _incident(session, org_id, incident_id)
    await _ensure_access(session, org_id, actor_id, item)
    add_event(session, item, actor_id, "InvestigationNoteAdded", note, to_status=item.status)
    await session.flush()
    return item


async def request_resolution(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    incident_id: UUID,
    data: IncidentResolutionRequest,
) -> Incident:
    item = await _incident(session, org_id, incident_id, lock=True)
    application = await _ensure_access(session, org_id, actor_id, item)
    if item.status not in {"investigating", "reopened"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Incident harus dalam investigasi sebelum resolusi")
    if not item.root_cause or not item.action_plan:
        raise HTTPException(status.HTTP_409_CONFLICT, "Root cause dan action plan wajib lengkap")
    previous = item.status
    item.status = "pending_resolution"
    item.resolution_note = data.resolution_note
    approval = await approval_service.request_approval(
        session,
        org_id=org_id,
        branch_id=application.branch_id,
        aggregate_type="incident",
        aggregate_id=item.id,
        aggregate_reference=f"INC-{str(item.id)[:8].upper()}",
        action="resolve_incident",
        requested_by=actor_id,
        assigned_role="branch_manager",
        reason=data.resolution_note,
        payload={
            "application_id": str(application.id),
            "incident_type": item.incident_type,
            "severity": item.severity,
            "root_cause": item.root_cause,
            "action_plan": item.action_plan,
        },
        priority="critical" if item.severity == "critical" else "high",
        sla_hours=2 if item.severity == "critical" else 8,
    )
    add_event(
        session,
        item,
        actor_id,
        "IncidentResolutionRequested",
        data.resolution_note,
        from_status=previous,
        to_status=item.status,
        metadata={"approval_id": str(approval.id)},
    )
    await session.flush()
    return item


async def reopen_incident(
    session: AsyncSession, org_id: UUID, actor_id: UUID, incident_id: UUID, reason: str
) -> Incident:
    item = await _incident(session, org_id, incident_id, lock=True)
    application = await _ensure_access(session, org_id, actor_id, item)
    if item.status != "resolved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Hanya incident resolved yang dapat dibuka kembali")
    previous = item.status
    item.status = "reopened"
    item.reopened_count += 1
    item.resolved_by_user_id = None
    item.resolved_at = None
    asset = await session.scalar(
        select(Asset).where(Asset.org_id == org_id, Asset.application_id == application.id).with_for_update()
    )
    if asset is not None:
        asset.collateral_status = "incident_hold"
    add_event(session, item, actor_id, "IncidentReopened", reason, from_status=previous, to_status=item.status)
    await session.flush()
    return item
