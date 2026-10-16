"""Versioned tenant configuration endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.operations import configuration_service
from dogeapi.operations.configuration_schemas import (
    ConfigurationClone,
    ConfigurationCreate,
    ConfigurationIdResult,
    ConfigurationSubmit,
    ConfigurationUpdateDraft,
)
from dogeapi.security import require_scope

router = APIRouter(
    prefix="/v1/configurations",
    tags=["configuration-control"],
    dependencies=[Depends(require_scope("org:read"))],
)


@router.get("")
async def configurations(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    return await configuration_service.list_configurations(session, org_id, user.id)


@router.post(
    "",
    response_model=ConfigurationIdResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:write"))],
)
async def create_configuration(
    data: ConfigurationCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ConfigurationIdResult:
    item = await configuration_service.create_configuration(session, org_id, user.id, data)
    await session.commit()
    return ConfigurationIdResult(id=item.id, status=item.status, message="Configuration draft dibuat")


@router.post("/apply-due", dependencies=[Depends(require_scope("org:write"))])
async def apply_due_configurations(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> dict[str, object]:
    count = await configuration_service.apply_due_configurations(session, org_id, user.id)
    await session.commit()
    return {"count": count, "message": f"{count} configuration version diaktifkan"}


@router.get("/{configuration_id}")
async def configuration_detail(
    configuration_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    return await configuration_service.get_configuration(session, org_id, user.id, configuration_id)


@router.get("/{configuration_id}/preview")
async def configuration_preview(
    configuration_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    return await configuration_service.preview_configuration(session, org_id, user.id, configuration_id)


@router.put(
    "/{configuration_id}",
    response_model=ConfigurationIdResult,
    dependencies=[Depends(require_scope("org:write"))],
)
async def update_configuration(
    configuration_id: UUID,
    data: ConfigurationUpdateDraft,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ConfigurationIdResult:
    item = await configuration_service.update_draft(session, org_id, user.id, configuration_id, data)
    await session.commit()
    return ConfigurationIdResult(id=item.id, status=item.status, message="Configuration draft diperbarui")


@router.post(
    "/{configuration_id}/submit",
    response_model=ConfigurationIdResult,
    dependencies=[Depends(require_scope("org:write"))],
)
async def submit_configuration(
    configuration_id: UUID,
    data: ConfigurationSubmit,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ConfigurationIdResult:
    item = await configuration_service.submit_configuration(session, org_id, user.id, configuration_id, data.reason)
    await session.commit()
    return ConfigurationIdResult(id=item.id, status=item.status, message="Configuration menunggu approval")


@router.post(
    "/{configuration_id}/clone",
    response_model=ConfigurationIdResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:write"))],
)
async def clone_configuration(
    configuration_id: UUID,
    data: ConfigurationClone,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ConfigurationIdResult:
    item = await configuration_service.clone_configuration(
        session, org_id, user.id, configuration_id, data.effective_from, data.change_summary
    )
    await session.commit()
    return ConfigurationIdResult(id=item.id, status=item.status, message="Draft versi baru dibuat")
