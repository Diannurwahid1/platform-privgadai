from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import ApprovalRequest, ConfigurationVersion, Membership, Organization, Role, User
from dogeapi.operations import approval_service, configuration_service
from dogeapi.operations.configuration_schemas import ConfigurationCreate


async def _configuration_team(session: AsyncSession) -> tuple[Organization, User, User, User]:
    suffix = uuid4().hex[:8]
    org = Organization(slug=f"config-{suffix}", name="Configuration Test")
    maker = User(email=f"maker-{suffix}@example.com", full_name="Configuration Maker")
    checker = User(email=f"checker-{suffix}@example.com", full_name="Configuration Checker")
    scheduler = User(email=f"scheduler-{suffix}@example.com", full_name="Configuration Scheduler")
    session.add_all([org, maker, checker, scheduler])
    await session.flush()
    session.add_all(
        [
            Membership(org_id=org.id, user_id=maker.id, role=Role.ADMIN),
            Membership(org_id=org.id, user_id=checker.id, role=Role.ADMIN),
            Membership(org_id=org.id, user_id=scheduler.id, role=Role.ADMIN),
        ]
    )
    await session.flush()
    return org, maker, checker, scheduler


async def _approve(
    session: AsyncSession, org: Organization, maker: User, checker: User, item: ConfigurationVersion
) -> None:
    await configuration_service.submit_configuration(
        session, org.id, maker.id, item.id, "Perubahan telah direview maker dan siap diperiksa checker"
    )
    approval = await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.org_id == org.id,
            ApprovalRequest.aggregate_type == "configuration",
            ApprovalRequest.aggregate_id == item.id,
        )
    )
    assert approval is not None
    with pytest.raises(HTTPException) as maker_checker:
        await approval_service.decide_approval(
            session, org.id, approval.id, maker.id, "approved", "Maker tidak boleh approve"
        )
    assert maker_checker.value.status_code == 409
    await approval_service.decide_approval(
        session, org.id, approval.id, checker.id, "approved", "Payload, dampak, dan effective date sesuai"
    )


async def test_configuration_versions_supersede_and_rollback_as_new_version(db_session: AsyncSession) -> None:
    org, maker, checker, _scheduler = await _configuration_team(db_session)
    now = datetime.now(UTC) - timedelta(minutes=1)
    first = await configuration_service.create_configuration(
        db_session,
        org.id,
        maker.id,
        ConfigurationCreate(
            domain="pricing",
            config_key="gadai-reguler",
            effective_from=now,
            payload={"max_ltv_percent": 80, "service_fee_percent": 5},
            change_summary="Baseline pricing untuk produk gadai reguler",
        ),
    )
    await _approve(db_session, org, maker, checker, first)
    assert first.status == "effective"

    second = await configuration_service.create_configuration(
        db_session,
        org.id,
        maker.id,
        ConfigurationCreate(
            domain="pricing",
            config_key="gadai-reguler",
            effective_from=now,
            payload={"max_ltv_percent": 75, "service_fee_percent": 5},
            change_summary="Penurunan LTV sesuai hasil review risiko portofolio",
        ),
    )
    preview = await configuration_service.preview_configuration(db_session, org.id, maker.id, second.id)
    assert preview["changed_field_count"] == 1
    assert preview["changes"][0]["field"] == "max_ltv_percent"
    await _approve(db_session, org, maker, checker, second)
    assert first.status == "superseded"
    assert second.status == "effective"

    rollback = await configuration_service.clone_configuration(
        db_session,
        org.id,
        maker.id,
        first.id,
        now,
        "Rollback terkontrol ke parameter versi pertama setelah evaluasi",
    )
    assert rollback.version == 3
    assert rollback.payload == first.payload
    await _approve(db_session, org, maker, checker, rollback)
    assert second.status == "superseded"
    assert rollback.status == "effective"


async def test_future_configuration_requires_due_activation(db_session: AsyncSession) -> None:
    org, maker, checker, scheduler = await _configuration_team(db_session)
    item = await configuration_service.create_configuration(
        db_session,
        org.id,
        maker.id,
        ConfigurationCreate(
            domain="security",
            config_key="session-policy",
            effective_from=datetime.now(UTC) + timedelta(days=1),
            payload={"idle_timeout_minutes": 15, "absolute_timeout_hours": 8},
            change_summary="Perketat batas sesi pengguna dengan hak operasional",
        ),
    )
    await _approve(db_session, org, maker, checker, item)
    assert item.status == "approved"
    assert await configuration_service.apply_due_configurations(db_session, org.id, scheduler.id) == 0

    item.effective_from = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.flush()
    assert await configuration_service.apply_due_configurations(db_session, org.id, scheduler.id) == 1
    assert item.status == "effective"
