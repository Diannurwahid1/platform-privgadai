"""Partner operations endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from dogeapi.deps import OrgIdDep, SessionDep
from dogeapi.operations import service
from dogeapi.operations.schemas import ApplicationQueueItem, OperationsDashboardResponse
from dogeapi.security import require_scope

router = APIRouter(
    prefix="/v1",
    tags=["privgadai-operations"],
    dependencies=[Depends(require_scope("org:read"))],
)


@router.get("/operations/dashboard", response_model=OperationsDashboardResponse)
async def operations_dashboard(session: SessionDep, org_id: OrgIdDep) -> OperationsDashboardResponse:
    return await service.get_operations_dashboard(session, org_id)


@router.get("/applications", response_model=list[ApplicationQueueItem])
async def applications_inbox(
    session: SessionDep,
    org_id: OrgIdDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ApplicationQueueItem]:
    return await service.list_application_queue(session, org_id, limit=limit)
