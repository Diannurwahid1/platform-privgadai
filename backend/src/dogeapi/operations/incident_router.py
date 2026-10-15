"""Operational exception and incident endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.operations import incident_service
from dogeapi.operations.incident_schemas import (
    IncidentNoteCreate,
    IncidentReopen,
    IncidentResolutionRequest,
    IncidentTriage,
)
from dogeapi.security import require_scope

router = APIRouter(
    prefix="/v1/incidents",
    tags=["operational-incidents"],
    dependencies=[Depends(require_scope("org:read"))],
)


@router.get("")
async def incidents(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    return await incident_service.list_incidents(session, org_id, user.id)


@router.get("/{incident_id}")
async def incident_detail(incident_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep) -> dict[str, object]:
    return await incident_service.get_incident(session, org_id, user.id, incident_id)


@router.post("/{incident_id}/triage", dependencies=[Depends(require_scope("org:write"))])
async def triage_incident(
    incident_id: UUID, data: IncidentTriage, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    item = await incident_service.triage_incident(session, org_id, user.id, incident_id, data)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Incident ditriase dan owner ditetapkan"}


@router.post("/{incident_id}/notes", dependencies=[Depends(require_scope("org:write"))])
async def add_incident_note(
    incident_id: UUID, data: IncidentNoteCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    item = await incident_service.add_note(session, org_id, user.id, incident_id, data.note)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Catatan investigasi ditambahkan"}


@router.post("/{incident_id}/resolution", dependencies=[Depends(require_scope("org:write"))])
async def request_incident_resolution(
    incident_id: UUID,
    data: IncidentResolutionRequest,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> dict[str, object]:
    item = await incident_service.request_resolution(session, org_id, user.id, incident_id, data)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Resolusi menunggu approval branch manager"}


@router.post("/{incident_id}/reopen", dependencies=[Depends(require_scope("org:write"))])
async def reopen_incident(
    incident_id: UUID, data: IncidentReopen, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    item = await incident_service.reopen_incident(session, org_id, user.id, incident_id, data.reason)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Incident dibuka kembali"}
