"""Versioning, approval, effective dating, and rollback for tenant configuration."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import ConfigurationEvent, ConfigurationVersion
from dogeapi.operations import approval_service, mvp_service
from dogeapi.operations.configuration_runtime import validate_configuration_payload
from dogeapi.operations.configuration_schemas import ConfigurationCreate, ConfigurationUpdateDraft

ADMIN_ROLES = {"ops_admin", "branch_manager", "auditor"}


def _checksum(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _event(
    session: AsyncSession,
    item: ConfigurationVersion,
    actor_id: UUID | None,
    event_type: str,
    reason: str | None,
    *,
    from_status: str | None = None,
    to_status: str | None = None,
) -> None:
    session.add(
        ConfigurationEvent(
            org_id=item.org_id,
            configuration_id=item.id,
            actor_user_id=actor_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
        )
    )


async def _get(
    session: AsyncSession, org_id: UUID, configuration_id: UUID, *, lock: bool = False
) -> ConfigurationVersion:
    statement = select(ConfigurationVersion).where(
        ConfigurationVersion.org_id == org_id, ConfigurationVersion.id == configuration_id
    )
    if lock:
        statement = statement.with_for_update()
    item = await session.scalar(statement)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuration version tidak ditemukan")
    return item


async def create_configuration(
    session: AsyncSession, org_id: UUID, actor_id: UUID, data: ConfigurationCreate
) -> ConfigurationVersion:
    await mvp_service.ensure_any_operational_role(session, org_id, actor_id, ADMIN_ROLES)
    validate_configuration_payload(data.domain, data.payload)
    version = (
        int(
            (
                await session.scalar(
                    select(func.coalesce(func.max(ConfigurationVersion.version), 0)).where(
                        ConfigurationVersion.org_id == org_id,
                        ConfigurationVersion.domain == data.domain,
                        ConfigurationVersion.config_key == data.config_key,
                    )
                )
            )
            or 0
        )
        + 1
    )
    current = await session.scalar(
        select(ConfigurationVersion).where(
            ConfigurationVersion.org_id == org_id,
            ConfigurationVersion.domain == data.domain,
            ConfigurationVersion.config_key == data.config_key,
            ConfigurationVersion.status == "effective",
        )
    )
    item = ConfigurationVersion(
        org_id=org_id,
        domain=data.domain,
        config_key=data.config_key,
        version=version,
        effective_from=data.effective_from,
        payload=data.payload,
        checksum_sha256=_checksum(data.payload),
        change_summary=data.change_summary,
        created_by_user_id=actor_id,
        supersedes_id=current.id if current else None,
    )
    session.add(item)
    await session.flush()
    _event(session, item, actor_id, "ConfigurationDraftCreated", data.change_summary, to_status="draft")
    await session.flush()
    return item


async def update_draft(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    configuration_id: UUID,
    data: ConfigurationUpdateDraft,
) -> ConfigurationVersion:
    await mvp_service.ensure_any_operational_role(session, org_id, actor_id, ADMIN_ROLES)
    item = await _get(session, org_id, configuration_id, lock=True)
    if item.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Hanya draft yang dapat diubah")
    if item.created_by_user_id != actor_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Draft hanya dapat diubah oleh pembuatnya")
    validate_configuration_payload(item.domain, data.payload)
    item.effective_from = data.effective_from
    item.payload = data.payload
    item.checksum_sha256 = _checksum(data.payload)
    item.change_summary = data.change_summary
    _event(session, item, actor_id, "ConfigurationDraftUpdated", data.change_summary, to_status="draft")
    await session.flush()
    return item


async def clone_configuration(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    source_id: UUID,
    effective_from: datetime,
    change_summary: str,
) -> ConfigurationVersion:
    source = await _get(session, org_id, source_id)
    return await create_configuration(
        session,
        org_id,
        actor_id,
        ConfigurationCreate(
            domain=source.domain,
            config_key=source.config_key,
            effective_from=effective_from,
            payload=source.payload,
            change_summary=change_summary,
        ),
    )


async def submit_configuration(
    session: AsyncSession, org_id: UUID, actor_id: UUID, configuration_id: UUID, reason: str
) -> ConfigurationVersion:
    await mvp_service.ensure_any_operational_role(session, org_id, actor_id, ADMIN_ROLES)
    item = await _get(session, org_id, configuration_id, lock=True)
    if item.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Configuration tidak berstatus draft")
    item.status = "pending_approval"
    await approval_service.request_approval(
        session,
        org_id=org_id,
        branch_id=None,
        aggregate_type="configuration",
        aggregate_id=item.id,
        aggregate_reference=f"CFG-{item.domain.upper()}-{item.config_key}-V{item.version}",
        action="activate_configuration",
        requested_by=actor_id,
        assigned_role="ops_admin",
        reason=reason,
        payload={
            "domain": item.domain,
            "config_key": item.config_key,
            "version": item.version,
            "effective_from": item.effective_from.isoformat(),
            "checksum_sha256": item.checksum_sha256,
            "change_summary": item.change_summary,
            "payload": item.payload,
        },
        priority="high" if item.domain in {"access", "security", "regulatory", "accounting"} else "normal",
        sla_hours=8,
    )
    _event(
        session,
        item,
        actor_id,
        "ConfigurationSubmitted",
        reason,
        from_status="draft",
        to_status="pending_approval",
    )
    await session.flush()
    return item


async def activate_configuration(session: AsyncSession, item: ConfigurationVersion, actor_id: UUID | None) -> None:
    validate_configuration_payload(item.domain, item.payload)
    now = datetime.now(UTC)
    current = await session.scalar(
        select(ConfigurationVersion)
        .where(
            ConfigurationVersion.org_id == item.org_id,
            ConfigurationVersion.domain == item.domain,
            ConfigurationVersion.config_key == item.config_key,
            ConfigurationVersion.status == "effective",
            ConfigurationVersion.id != item.id,
        )
        .with_for_update()
    )
    if current is not None:
        current.status = "superseded"
        current.effective_until = item.effective_from
        _event(
            session,
            current,
            actor_id,
            "ConfigurationSuperseded",
            f"Superseded by version {item.version}",
            from_status="effective",
            to_status="superseded",
        )
        await session.flush()
    previous = item.status
    item.status = "effective"
    item.activated_at = now
    _event(
        session,
        item,
        actor_id,
        "ConfigurationActivated",
        item.change_summary,
        from_status=previous,
        to_status="effective",
    )


async def apply_due_configurations(session: AsyncSession, org_id: UUID, actor_id: UUID) -> int:
    await mvp_service.ensure_any_operational_role(session, org_id, actor_id, {"ops_admin", "auditor"})
    now = datetime.now(UTC)
    rows = list(
        await session.scalars(
            select(ConfigurationVersion)
            .where(
                ConfigurationVersion.org_id == org_id,
                ConfigurationVersion.status == "approved",
                ConfigurationVersion.effective_from <= now,
            )
            .order_by(ConfigurationVersion.effective_from, ConfigurationVersion.version)
            .with_for_update()
        )
    )
    for item in rows:
        await activate_configuration(session, item, actor_id)
    await session.flush()
    return len(rows)


async def list_configurations(session: AsyncSession, org_id: UUID, actor_id: UUID) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(session, org_id, actor_id, ADMIN_ROLES)
    rows = list(
        await session.scalars(
            select(ConfigurationVersion)
            .where(ConfigurationVersion.org_id == org_id)
            .order_by(ConfigurationVersion.domain, ConfigurationVersion.config_key, ConfigurationVersion.version.desc())
        )
    )
    return [_serialize(item) for item in rows]


async def get_configuration(
    session: AsyncSession, org_id: UUID, actor_id: UUID, configuration_id: UUID
) -> dict[str, object]:
    await mvp_service.ensure_any_operational_role(session, org_id, actor_id, ADMIN_ROLES)
    item = await _get(session, org_id, configuration_id)
    events = list(
        await session.scalars(
            select(ConfigurationEvent)
            .where(ConfigurationEvent.org_id == org_id, ConfigurationEvent.configuration_id == item.id)
            .order_by(ConfigurationEvent.occurred_at.desc())
        )
    )
    result = _serialize(item)
    result["events"] = [
        {
            "id": event.id,
            "event_type": event.event_type,
            "actor_user_id": event.actor_user_id,
            "from_status": event.from_status,
            "to_status": event.to_status,
            "reason": event.reason,
            "occurred_at": event.occurred_at,
        }
        for event in events
    ]
    return result


async def preview_configuration(
    session: AsyncSession, org_id: UUID, actor_id: UUID, configuration_id: UUID
) -> dict[str, object]:
    await mvp_service.ensure_any_operational_role(session, org_id, actor_id, ADMIN_ROLES)
    item = await _get(session, org_id, configuration_id)
    current = await session.scalar(
        select(ConfigurationVersion).where(
            ConfigurationVersion.org_id == org_id,
            ConfigurationVersion.domain == item.domain,
            ConfigurationVersion.config_key == item.config_key,
            ConfigurationVersion.status == "effective",
        )
    )
    current_payload = current.payload if current else {}
    keys = sorted(set(current_payload) | set(item.payload))
    changes = [
        {"field": key, "before": current_payload.get(key), "after": item.payload.get(key)}
        for key in keys
        if current_payload.get(key) != item.payload.get(key)
    ]
    return {
        "configuration_id": item.id,
        "current_version": current.version if current else None,
        "candidate_version": item.version,
        "changed_field_count": len(changes),
        "changes": changes,
        "effective_from": item.effective_from,
        "impact": {
            "domain": item.domain,
            "key": item.config_key,
            "requires_approval": True,
            "supersedes_id": current.id if current else None,
        },
    }


def _serialize(item: ConfigurationVersion) -> dict[str, object]:
    return {
        "id": item.id,
        "domain": item.domain,
        "config_key": item.config_key,
        "version": item.version,
        "status": item.status,
        "effective_from": item.effective_from,
        "effective_until": item.effective_until,
        "payload": item.payload,
        "checksum_sha256": item.checksum_sha256,
        "change_summary": item.change_summary,
        "created_by_user_id": item.created_by_user_id,
        "approved_by_user_id": item.approved_by_user_id,
        "approved_at": item.approved_at,
        "activated_at": item.activated_at,
        "supersedes_id": item.supersedes_id,
        "created_at": item.created_at,
    }
