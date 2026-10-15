"""Customer complaint and support case endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.operations import complaint_service
from dogeapi.operations.complaint_schemas import (
    ComplaintAssign,
    ComplaintCommunication,
    ComplaintCreate,
    ComplaintReopen,
    ComplaintResolution,
)
from dogeapi.security import require_scope

router = APIRouter(
    prefix="/v1/complaints",
    tags=["complaints"],
    dependencies=[Depends(require_scope("org:read"))],
)


@router.get("")
async def complaints(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    return await complaint_service.list_complaints(session, org_id, user.id)


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_scope("org:write"))])
async def create_complaint(
    data: ComplaintCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    item = await complaint_service.create_complaint(session, org_id, user.id, data)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Complaint case dibuat", "ticket_no": item.ticket_no}


@router.post("/escalate-overdue", dependencies=[Depends(require_scope("org:write"))])
async def escalate_overdue_complaints(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> dict[str, object]:
    count = await complaint_service.escalate_overdue(session, org_id, user.id)
    await session.commit()
    return {"count": count, "message": f"{count} complaint SLA dieskalasi"}


@router.get("/{case_id}")
async def complaint_detail(case_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep) -> dict[str, object]:
    return await complaint_service.get_complaint(session, org_id, user.id, case_id)


@router.post("/{case_id}/assign", dependencies=[Depends(require_scope("org:write"))])
async def assign_complaint(
    case_id: UUID, data: ComplaintAssign, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    item = await complaint_service.assign_complaint(
        session, org_id, user.id, case_id, data.assigned_to_user_id, data.reason
    )
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Owner complaint ditetapkan"}


@router.post("/{case_id}/communications", dependencies=[Depends(require_scope("org:write"))])
async def add_complaint_communication(
    case_id: UUID,
    data: ComplaintCommunication,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> dict[str, object]:
    item = await complaint_service.add_communication(
        session, org_id, user.id, case_id, data.direction, data.channel, data.message
    )
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Komunikasi complaint tercatat"}


@router.post("/{case_id}/resolution", dependencies=[Depends(require_scope("org:write"))])
async def request_complaint_resolution(
    case_id: UUID,
    data: ComplaintResolution,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> dict[str, object]:
    item = await complaint_service.request_resolution(session, org_id, user.id, case_id, data)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Resolusi complaint menunggu approval"}


@router.post("/{case_id}/reopen", dependencies=[Depends(require_scope("org:write"))])
async def reopen_complaint(
    case_id: UUID, data: ComplaintReopen, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    item = await complaint_service.reopen_complaint(session, org_id, user.id, case_id, data.reason)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Complaint dibuka kembali"}
