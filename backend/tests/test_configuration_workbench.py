from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    ApprovalRequest,
    AssetCategory,
    Branch,
    ConfigurationVersion,
    LoanProduct,
    Membership,
    Organization,
    Role,
    User,
)
from dogeapi.operations import approval_service, configuration_service, mvp_service
from dogeapi.operations.configuration_runtime import get_effective_configuration
from dogeapi.operations.configuration_schemas import ConfigurationCreate
from dogeapi.operations.mvp_schemas import ApplicationCreate


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


async def test_domain_schema_rejects_invalid_ranges_and_plaintext_secrets(db_session: AsyncSession) -> None:
    org, maker, _checker, _scheduler = await _configuration_team(db_session)
    with pytest.raises(HTTPException) as invalid_ltv:
        await configuration_service.create_configuration(
            db_session,
            org.id,
            maker.id,
            ConfigurationCreate(
                domain="pricing",
                config_key="gadai-emas",
                effective_from=datetime.now(UTC),
                payload={"max_ltv_percent": 125, "service_fee_percent": 5},
                change_summary="Uji validasi parameter pricing di luar batas",
            ),
        )
    assert invalid_ltv.value.status_code == 422

    with pytest.raises(HTTPException) as plaintext_secret:
        await configuration_service.create_configuration(
            db_session,
            org.id,
            maker.id,
            ConfigurationCreate(
                domain="integration",
                config_key="ekyc-provider",
                effective_from=datetime.now(UTC),
                payload={"api_key": "plain-secret-value"},
                change_summary="Uji pencegahan secret plaintext pada configuration",
            ),
        )
    assert plaintext_secret.value.status_code == 422


async def test_effective_workflow_configuration_controls_approval_sla(db_session: AsyncSession) -> None:
    org, maker, checker, _scheduler = await _configuration_team(db_session)
    policy = await configuration_service.create_configuration(
        db_session,
        org.id,
        maker.id,
        ConfigurationCreate(
            domain="workflow",
            config_key="approval.default",
            effective_from=datetime.now(UTC) - timedelta(minutes=1),
            payload={"approval_sla_hours": 2},
            change_summary="SLA approval default dua jam untuk transaksi operasional",
        ),
    )
    await _approve(db_session, org, maker, checker, policy)
    resolved = await get_effective_configuration(db_session, org.id, "workflow", "approval.default")
    assert resolved is not None and resolved.id == policy.id

    before = datetime.now(UTC)
    approval = await approval_service.request_approval(
        db_session,
        org_id=org.id,
        branch_id=None,
        aggregate_type="test_control",
        aggregate_id=uuid4(),
        aggregate_reference="TEST-CONTROL-001",
        action="test_runtime_sla",
        requested_by=maker.id,
        assigned_role="ops_admin",
        reason="Membuktikan runtime memakai konfigurasi efektif",
        payload={"source": "test"},
    )
    assert approval.due_at is not None
    assert before + timedelta(hours=1, minutes=59) <= approval.due_at <= before + timedelta(hours=2, minutes=1)


async def test_effective_product_and_workflow_policy_control_intake(db_session: AsyncSession) -> None:
    org, maker, checker, _scheduler = await _configuration_team(db_session)
    branch = Branch(org_id=org.id, code="JKT-01", name="Jakarta", city="Jakarta")
    category = AssetCategory(org_id=org.id, code="gold", name="Emas")
    product = LoanProduct(
        org_id=org.id,
        code="REG-30",
        name="Gadai Reguler",
        min_amount=Decimal("500000"),
        max_amount=Decimal("20000000"),
        max_ltv_percent=Decimal("80"),
        allowed_tenors_days=[30, 60],
        service_fee_percent=Decimal("5"),
    )
    db_session.add_all([branch, category, product])
    await db_session.flush()
    for domain, key, payload, summary in (
        (
            "product",
            "reg-30",
            {"enabled": True, "min_amount": 1_000_000, "max_amount": 5_000_000, "allowed_tenors_days": [30]},
            "Batasi plafon dan tenor produk untuk pilot terkontrol",
        ),
        (
            "workflow",
            "application-intake",
            {"submission_sla_hours": 6},
            "Tetapkan SLA intake pengajuan menjadi enam jam",
        ),
    ):
        policy = await configuration_service.create_configuration(
            db_session,
            org.id,
            maker.id,
            ConfigurationCreate(
                domain=domain,
                config_key=key,
                effective_from=datetime.now(UTC) - timedelta(minutes=1),
                payload=payload,
                change_summary=summary,
            ),
        )
        await _approve(db_session, org, maker, checker, policy)

    base = {
        "branch_id": branch.id,
        "product_id": product.id,
        "borrower": {"full_name": "Nasabah Konfigurasi", "phone": "081234567890"},
        "asset": {"category_code": "gold", "brand": "Antam", "model": "10gr"},
        "requested_tenor_days": 30,
        "consent_document_version": "2026.1",
    }
    with pytest.raises(HTTPException) as outside_policy:
        await mvp_service.create_application(
            db_session,
            org.id,
            maker.id,
            ApplicationCreate(**base, requested_amount=Decimal("7000000")),
        )
    assert outside_policy.value.status_code == 422

    before = datetime.now(UTC)
    application = await mvp_service.create_application(
        db_session,
        org.id,
        maker.id,
        ApplicationCreate(**base, requested_amount=Decimal("4000000")),
    )
    assert application.sla_due_at is not None
    assert before + timedelta(hours=5, minutes=59) <= application.sla_due_at <= before + timedelta(hours=6, minutes=1)


async def test_effective_authority_matrix_blocks_excess_approval(db_session: AsyncSession) -> None:
    org, maker, checker, _scheduler = await _configuration_team(db_session)
    policy = await configuration_service.create_configuration(
        db_session,
        org.id,
        maker.id,
        ConfigurationCreate(
            domain="access",
            config_key="authority-matrix",
            effective_from=datetime.now(UTC) - timedelta(minutes=1),
            payload={"authority_limits": {"ops_admin": 5000000}},
            change_summary="Batasi nominal approval ops admin menjadi lima juta rupiah",
        ),
    )
    await _approve(db_session, org, maker, checker, policy)
    approval = await approval_service.request_approval(
        db_session,
        org_id=org.id,
        branch_id=None,
        aggregate_type="test_authority",
        aggregate_id=uuid4(),
        aggregate_reference="AUTH-LIMIT-001",
        action="approve_high_value",
        requested_by=maker.id,
        assigned_role="ops_admin",
        reason="Uji pembatasan kewenangan berdasarkan nominal",
        payload={"amount": "7000000"},
    )
    with pytest.raises(HTTPException) as denied:
        await approval_service.decide_approval(
            db_session,
            org.id,
            approval.id,
            checker.id,
            "approved",
            "Nominal sengaja melebihi batas untuk pengujian",
        )
    assert denied.value.status_code == 403
