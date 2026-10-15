"""End-to-end MVP workflow and tenant boundary coverage."""

from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    ApprovalRequest,
    DebtorProfile,
    KycVerification,
    LoanApplication,
    Membership,
    RegulatoryReportRun,
    RegulatoryReportTemplate,
    Role,
    User,
)
from dogeapi.operations import approval_service, erp_service, mvp_service
from dogeapi.operations.erp_schemas import InventoryCheckSubmit, InventoryObservation
from dogeapi.operations.kyc_service import encrypt_pii
from dogeapi.operations.state_machine import APPLICATION_TRANSITIONS, COLLATERAL_TRANSITIONS, can_transition
from dogeapi.settings import Settings


def test_state_machines_reject_shortcuts() -> None:
    assert can_transition(APPLICATION_TRANSITIONS, "submitted", "under_review")
    assert not can_transition(APPLICATION_TRANSITIONS, "submitted", "accepted")
    assert can_transition(COLLATERAL_TRANSITIONS, "received", "stored")
    assert not can_transition(COLLATERAL_TRANSITIONS, "with_customer", "stored")


pytestmark = pytest.mark.integration


async def _register_and_switch(client: AsyncClient) -> tuple[dict[str, str], dict[str, str]]:
    registered = await client.post(
        "/auth/register",
        json={"email": "mvp-owner@example.com", "password": "correct horse battery staple", "full_name": "MVP Owner"},
    )
    assert registered.status_code == 201
    base = {"Authorization": f"Bearer {registered.json()['tokens']['access_token']}"}
    created = await client.post("/orgs", json={"name": "Mitra MVP", "slug": "mitra-mvp"}, headers=base)
    assert created.status_code == 201
    switched = await client.post("/orgs/mitra-mvp/switch", headers=base)
    assert switched.status_code == 200
    return base, {"Authorization": f"Bearer {switched.json()['access_token']}"}


async def test_complete_mvp_workflow_is_tenant_scoped(
    client: AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    base_headers, headers = await _register_and_switch(client)
    today = datetime.now(UTC).date()
    period_start = today.replace(day=1)
    next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    period_end = next_month - timedelta(days=1)

    branch = await client.post(
        "/v1/master/branches",
        json={"code": "YGY-01", "name": "Cabang Yogyakarta", "city": "Yogyakarta", "address": "Jl. Demo"},
        headers=headers,
    )
    assert branch.status_code == 201, branch.text
    category = await client.post(
        "/v1/master/asset-categories",
        json={"code": "laptop", "name": "Laptop", "requires_serial_number": True},
        headers=headers,
    )
    assert category.status_code == 201, category.text
    product = await client.post(
        "/v1/master/loan-products",
        json={
            "code": "REG-30",
            "name": "Gadai Reguler",
            "min_amount": "500000",
            "max_amount": "20000000",
            "max_ltv_percent": "80",
            "allowed_tenors_days": [30, 60],
            "service_fee_percent": "5",
        },
        headers=headers,
    )
    assert product.status_code == 201, product.text
    location = await client.post(
        "/v1/master/custody-locations",
        json={
            "branch_id": branch.json()["id"],
            "code": "VAULT-YGY",
            "name": "Brankas Yogyakarta",
            "location_type": "branch_vault",
        },
        headers=headers,
    )
    assert location.status_code == 201, location.text
    location_two = await client.post(
        "/v1/master/custody-locations",
        json={
            "branch_id": branch.json()["id"],
            "code": "VAULT-YGY-02",
            "name": "Brankas Yogyakarta 2",
            "location_type": "branch_vault",
        },
        headers=headers,
    )
    assert location_two.status_code == 201, location_two.text
    accounting_period = await client.post(
        "/v1/accounting/periods",
        json={"period_start": period_start.isoformat(), "period_end": period_end.isoformat()},
        headers=headers,
    )
    assert accounting_period.status_code == 201, accounting_period.text
    cashboxes = await client.get("/v1/finance/cashboxes", headers=headers)
    assert cashboxes.status_code == 200, cashboxes.text
    funded = await client.post(
        f"/v1/finance/cashboxes/{cashboxes.json()[0]['id']}/fund",
        json={
            "amount": "100000000",
            "external_reference": "CAPITAL-TEST-001",
            "idempotency_key": "capital-test-001",
        },
        headers=headers,
    )
    assert funded.status_code == 200, funded.text

    public_config = await client.get("/public/v1/partners/mitra-mvp/intake-config")
    assert public_config.status_code == 200
    assert public_config.json()["partner"]["name"] == "Mitra MVP"
    public_application = await client.post(
        "/public/v1/partners/mitra-mvp/applications",
        json={
            "branch_id": branch.json()["id"],
            "product_id": product.json()["id"],
            "borrower": {"full_name": "Nasabah Portal", "phone": "081200001111"},
            "asset": {
                "category_code": "laptop",
                "brand": "Dell",
                "model": "Latitude",
                "condition_grade": "B",
                "indicative_value": "9000000",
            },
            "requested_amount": "5000000",
            "requested_tenor_days": 30,
            "purpose": "Kebutuhan produktif",
            "consent_document_version": "PRIV-2026.1",
        },
    )
    assert public_application.status_code == 201, public_application.text

    created = await client.post(
        "/v1/applications",
        json={
            "branch_id": branch.json()["id"],
            "product_id": product.json()["id"],
            "borrower": {"full_name": "Nasabah Uji", "phone": "081234567890"},
            "asset": {
                "category_code": "laptop",
                "brand": "Lenovo",
                "model": "ThinkPad X1",
                "condition_grade": "A",
                "indicative_value": "12000000",
            },
            "requested_amount": "7000000",
            "requested_tenor_days": 30,
            "purpose": "Modal usaha",
            "consent_document_version": "2026.1",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    application_id = created.json()["application_id"]

    application = await db_session.scalar(select(LoanApplication).where(LoanApplication.id == application_id))
    actor = await db_session.scalar(select(User).where(User.email == "mvp-owner@example.com"))
    assert application is not None and actor is not None
    db_session.add(
        KycVerification(
            org_id=application.org_id,
            borrower_id=application.borrower_id,
            initiated_by_user_id=actor.id,
            reviewed_by_user_id=actor.id,
            nik_fingerprint="a" * 64,
            national_id_ciphertext=encrypt_pii(settings, "3471010101900001"),
            national_id_masked="3471••••••0001",
            legal_name="NASABAH UJI",
            birth_place="Yogyakarta",
            birth_date=datetime(1990, 1, 1, tzinfo=UTC).date(),
            gender="male",
            address="Alamat pengujian",
            province="DI Yogyakarta",
            city="Yogyakarta",
            status="verified",
            decision_reason="Seeded verified identity for the end-to-end workflow",
            reviewed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=365),
        )
    )
    debtor_profile = await db_session.scalar(
        select(DebtorProfile).where(
            DebtorProfile.org_id == application.org_id,
            DebtorProfile.borrower_id == application.borrower_id,
        )
    )
    assert debtor_profile is not None
    debtor_profile.national_id_masked = "3471••••••0001"
    debtor_profile.dati_ii_code = "3471"
    debtor_profile.slik_subject_code = "I01"
    await db_session.flush()

    for next_status in ("under_review", "appraisal"):
        transitioned = await client.post(
            f"/v1/applications/{application_id}/transition",
            json={"to_status": next_status, "note": "Verified in workflow test"},
            headers=headers,
        )
        assert transitioned.status_code == 200, transitioned.text

    appraisal = await client.post(
        "/v1/appraisals",
        json={
            "application_id": application_id,
            "market_value": "12000000",
            "liquidation_value": "10000000",
            "recommended_loan": "7500000",
            "condition_grade": "A",
            "rationale": "Kondisi fisik baik dan harga pasar terverifikasi.",
        },
        headers=headers,
    )
    assert appraisal.status_code == 201, appraisal.text
    approval = await db_session.scalar(
        select(ApprovalRequest).where(ApprovalRequest.aggregate_id == appraisal.json()["id"])
    )
    assert approval is not None and approval.status == "pending"
    with pytest.raises(HTTPException) as maker_decision:
        await approval_service.decide_approval(
            db_session,
            application.org_id,
            approval.id,
            actor.id,
            "approved",
            "Maker must not approve their own request",
        )
    assert getattr(maker_decision.value, "status_code", None) == 409
    checker = User(email="mvp-checker@example.com", full_name="MVP Checker")
    db_session.add(checker)
    await db_session.flush()
    db_session.add(Membership(user_id=checker.id, org_id=application.org_id, role=Role.ADMIN))
    await db_session.flush()
    approved = await approval_service.decide_approval(
        db_session, application.org_id, approval.id, checker.id, "approved", "Nilai dan bukti appraisal sesuai"
    )
    assert approved.status == "approved"
    approvals = await client.get("/v1/approvals", headers=headers)
    assert approvals.status_code == 200, approvals.text
    assert approvals.json()[0]["status"] == "approved"
    offer = await client.post(
        "/v1/offers",
        json={
            "application_id": application_id,
            "principal_amount": "7000000",
            "tenor_days": 30,
            "service_fee_amount": "350000",
            "expires_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "agreement_version": "AGR-2026.1",
        },
        headers=headers,
    )
    assert offer.status_code == 201, offer.text
    detail = await client.get(f"/v1/applications/{application_id}", headers=headers)
    assert detail.status_code == 200
    offer_id = detail.json()["offers"][0]["id"]

    accepted = await client.post(
        f"/v1/offers/{offer_id}/accept", json={"channel": "web", "ip_address": "127.0.0.1"}, headers=headers
    )
    assert accepted.status_code == 200, accepted.text
    pickup = await client.post(
        "/v1/pickups",
        json={"application_id": application_id, "pickup_address": "Jl. Nasabah No. 1"},
        headers=headers,
    )
    assert pickup.status_code == 201, pickup.text
    pickup_id = pickup.json()["id"]
    for next_status in ("in_transit", "received"):
        moved = await client.post(
            f"/v1/pickups/{pickup_id}/transition",
            json={"to_status": next_status, "condition_note": "Segel utuh"},
            headers=headers,
        )
        assert moved.status_code == 200, moved.text
    stored = await client.post(
        "/v1/custody/events",
        json={
            "application_id": application_id,
            "location_id": location.json()["id"],
            "event_type": "stored",
            "condition_note": "Disimpan di rak A-01",
        },
        headers=headers,
    )
    assert stored.status_code == 201, stored.text
    stock_check = await client.post(
        "/v1/inventory-checks",
        json={"location_id": location.json()["id"]},
        headers=headers,
    )
    assert stock_check.status_code == 201, stock_check.text
    stock_detail = await client.get(f"/v1/inventory-checks/{stock_check.json()['id']}", headers=headers)
    assert stock_detail.status_code == 200, stock_detail.text
    assert stock_detail.json()["assets"][0]["application_id"] == application_id
    stock_submit = await client.post(
        f"/v1/inventory-checks/{stock_check.json()['id']}/submit",
        json={
            "observations": [{"application_id": application_id, "observed_status": "present", "note": "Seal matched"}]
        },
        headers=headers,
    )
    assert stock_submit.status_code == 200, stock_submit.text
    stock_approval = await db_session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.org_id == application.org_id,
            ApprovalRequest.aggregate_type == "inventory_check",
            ApprovalRequest.aggregate_id == stock_check.json()["id"],
        )
    )
    assert stock_approval is not None
    await approval_service.decide_approval(
        db_session,
        application.org_id,
        stock_approval.id,
        checker.id,
        "approved",
        "Hasil scan fisik dan seal sesuai register",
    )
    blind_check = await client.post(
        "/v1/inventory-checks",
        json={"location_id": location.json()["id"]},
        headers=headers,
    )
    assert blind_check.status_code == 201, blind_check.text
    blind_detail = await client.get(f"/v1/inventory-checks/{blind_check.json()['id']}", headers=headers)
    assert blind_detail.status_code == 200
    assert blind_detail.json()["assets"][0]["expected_status"] is None
    first_count = await client.post(
        f"/v1/inventory-checks/{blind_check.json()['id']}/submit",
        json={
            "observations": [
                {
                    "application_id": application_id,
                    "observed_status": "missing",
                    "note": "Tag tidak ditemukan pada first count blind",
                }
            ]
        },
        headers=headers,
    )
    assert first_count.status_code == 200
    assert first_count.json()["status"] == "recount_required"
    with pytest.raises(HTTPException) as same_counter:
        await erp_service.recount_inventory_check(
            db_session,
            application.org_id,
            actor.id,
            blind_check.json()["id"],
            InventoryCheckSubmit(
                observations=[
                    InventoryObservation(
                        application_id=application_id,
                        observed_status="present",
                        note="Item ditemukan pada rak sekunder",
                    )
                ]
            ),
        )
    assert same_counter.value.status_code == 409
    recounted = await erp_service.recount_inventory_check(
        db_session,
        application.org_id,
        checker.id,
        blind_check.json()["id"],
        InventoryCheckSubmit(
            observations=[
                InventoryObservation(
                    application_id=application_id,
                    observed_status="present",
                    note="Item ditemukan pada rak sekunder dan tag diverifikasi",
                )
            ]
        ),
    )
    assert recounted.status == "submitted"
    assert recounted.recounted_by_user_id == checker.id
    recount_approval = await db_session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.org_id == application.org_id,
            ApprovalRequest.aggregate_type == "inventory_check",
            ApprovalRequest.aggregate_id == recounted.id,
        )
    )
    assert recount_approval is not None and recount_approval.requested_by_user_id == checker.id
    inventory_reviewer = User(email="inventory-reviewer@example.com", full_name="Inventory Reviewer")
    db_session.add(inventory_reviewer)
    await db_session.flush()
    db_session.add(Membership(user_id=inventory_reviewer.id, org_id=application.org_id, role=Role.ADMIN))
    await db_session.flush()
    await approval_service.decide_approval(
        db_session,
        application.org_id,
        recount_approval.id,
        inventory_reviewer.id,
        "approved",
        "Recount independen dan lokasi sekunder telah diverifikasi",
    )
    movement = await client.post(
        "/v1/custody/movements",
        json={
            "application_id": application_id,
            "to_location_id": location_two.json()["id"],
            "reason": "Redistribusi kapasitas vault",
        },
        headers=headers,
    )
    assert movement.status_code == 201, movement.text
    dispatched = await client.post(
        f"/v1/custody/movements/{movement.json()['id']}/dispatch",
        json={"seal_out": "SEAL-001", "note": "Segel dipasang di bawah CCTV"},
        headers=headers,
    )
    assert dispatched.status_code == 200, dispatched.text
    with pytest.raises(HTTPException) as same_receiver:
        await mvp_service.receive_custody_movement(
            db_session, application.org_id, actor.id, movement.json()["id"], "SEAL-001", "Received"
        )
    assert same_receiver.value.status_code == 409
    received = await mvp_service.receive_custody_movement(
        db_session,
        application.org_id,
        checker.id,
        movement.json()["id"],
        "SEAL-001",
        "Segel cocok dan kondisi barang utuh",
    )
    assert received.status == "received"
    disbursed = await client.post(
        f"/v1/loans/{application_id}/disburse",
        json={"external_reference": "DISB-TEST-001", "idempotency_key": "disbursement-test-001"},
        headers=headers,
    )
    assert disbursed.status_code == 200, disbursed.text
    repeated_disbursement = await client.post(
        f"/v1/loans/{application_id}/disburse",
        json={"external_reference": "DISB-TEST-001", "idempotency_key": "disbursement-test-001"},
        headers=headers,
    )
    assert repeated_disbursement.status_code == 200, repeated_disbursement.text
    finance = await client.get("/v1/finance/overview", headers=headers)
    assert finance.status_code == 200, finance.text
    assert finance.json()["active_loan_count"] == 1
    assert float(finance.json()["outstanding_principal"]) == 7_000_000
    reports = await client.get("/v1/accounting/reports", headers=headers)
    assert reports.status_code == 200, reports.text
    journals = await client.get("/v1/accounting/journals", headers=headers)
    assert journals.status_code == 200, journals.text
    assert journals.json()[0]["total_debit"] == journals.json()[0]["total_credit"]
    trial = reports.json()["trial_balance"]
    assert sum(float(row["debit"]) for row in trial) == sum(float(row["credit"]) for row in trial)
    template = await client.post(
        "/v1/regulatory/templates",
        json={
            "report_type": "OJK",
            "code": "LAPBUL-TEST",
            "name": "Laporan Bulanan Pengujian",
            "version": "2026.1",
            "effective_from": "2026-01-01",
            "mapping_schema": {"portfolio": "loan_portfolio"},
            "validation_rules": [],
        },
        headers=headers,
    )
    assert template.status_code == 201, template.text
    template_row = await db_session.scalar(
        select(RegulatoryReportTemplate).where(RegulatoryReportTemplate.id == template.json()["id"])
    )
    assert template_row is not None
    template_row.status = "active"
    await db_session.flush()
    report_run = await client.post(
        "/v1/regulatory/runs",
        json={"template_id": template.json()["id"], "period_start": "2026-09-01", "period_end": "2026-09-30"},
        headers=headers,
    )
    assert report_run.status_code == 201, report_run.text
    signoff = await client.post(
        f"/v1/regulatory/runs/{report_run.json()['id']}/submit-for-approval",
        json={"reason": "Rekonsiliasi sumber data periode September selesai"},
        headers=headers,
    )
    assert signoff.status_code == 200, signoff.text
    regulatory_approval = await db_session.get(ApprovalRequest, signoff.json()["id"])
    assert regulatory_approval is not None
    await approval_service.decide_approval(
        db_session,
        application.org_id,
        regulatory_approval.id,
        checker.id,
        "approved",
        "Angka, mapping, dan validation evidence telah diperiksa",
    )
    exported = await client.get(f"/v1/regulatory/runs/{report_run.json()['id']}/export", headers=headers)
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"] == "application/zip"
    assert len(exported.headers["x-content-sha256"]) == 64
    assert exported.content.startswith(b"PK")
    slik_template = await client.post(
        "/v1/regulatory/templates",
        json={
            "report_type": "SLIK",
            "code": "SLIK-TEST",
            "name": "SLIK Segments Test",
            "version": "SEOJK11-2024.1",
            "effective_from": "2024-10-02",
            "mapping_schema": {
                "source_url": "https://ojk.go.id/id/regulasi/Pages/Pelaporan-dan-Permintaan-Informasi-Debitur-Melalui-Sistem-Layanan-Informasi-Keuangan-11-SEOJK01-2024.aspx"
            },
            "validation_rules": [],
        },
        headers=headers,
    )
    assert slik_template.status_code == 201, slik_template.text
    slik_template_row = await db_session.get(RegulatoryReportTemplate, slik_template.json()["id"])
    assert slik_template_row is not None
    slik_activation = await client.post(
        f"/v1/regulatory/templates/{slik_template.json()['id']}/submit-for-activation",
        json={"reason": "Mapping SLIK direview terhadap SEOJK 11/SEOJK.01/2024"},
        headers=headers,
    )
    assert slik_activation.status_code == 200, slik_activation.text
    activation_approval = await db_session.get(ApprovalRequest, slik_activation.json()["id"])
    assert activation_approval is not None
    await approval_service.decide_approval(
        db_session,
        application.org_id,
        activation_approval.id,
        checker.id,
        "approved",
        "Sumber, versi, mapping, dan validation rule telah diperiksa",
    )
    assert slik_template_row.status == "active"
    slik_run = await client.post(
        "/v1/regulatory/runs",
        json={
            "template_id": slik_template.json()["id"],
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
        },
        headers=headers,
    )
    assert slik_run.status_code == 201, slik_run.text
    slik_run_row = await db_session.get(RegulatoryReportRun, slik_run.json()["id"])
    assert slik_run_row is not None
    assert slik_run_row.status == "draft"
    assert slik_run_row.report_payload["segment_counts"] == {"D01": 1, "F01": 1, "A01": 1}
    assert "3471010101900001" not in str(slik_run_row.report_payload)
    slik_signoff = await client.post(
        f"/v1/regulatory/runs/{slik_run.json()['id']}/submit-for-approval",
        json={"reason": "Segmen dan rekonsiliasi SLIK telah diperiksa"},
        headers=headers,
    )
    assert slik_signoff.status_code == 200, slik_signoff.text
    slik_approval = await db_session.get(ApprovalRequest, slik_signoff.json()["id"])
    assert slik_approval is not None
    await approval_service.decide_approval(
        db_session,
        application.org_id,
        slik_approval.id,
        checker.id,
        "approved",
        "D01, F01, A01 dan rekonsiliasi sesuai snapshot",
    )
    slik_export = await client.get(f"/v1/regulatory/runs/{slik_run.json()['id']}/export", headers=headers)
    assert slik_export.status_code == 200, slik_export.text
    with zipfile.ZipFile(io.BytesIO(slik_export.content)) as package:
        assert {"D01_debitur_individual.csv", "F01_fasilitas_kredit.csv", "A01_agunan.csv"}.issubset(package.namelist())
        assert "3471010101900001" in package.read("D01_debitur_individual.csv").decode("utf-8-sig")
    collections = await client.get("/v1/collections", headers=headers)
    assert collections.status_code == 200
    assert len(collections.json()) == 1
    collection_case_id = collections.json()[0]["id"]
    collection_detail = await client.get(f"/v1/collections/{collection_case_id}", headers=headers)
    assert collection_detail.status_code == 200, collection_detail.text
    assert collection_detail.json()["borrower"]["name"] == "Nasabah Uji"
    collection_plan = await client.patch(
        f"/v1/collections/{collection_case_id}/plan",
        json={
            "strategy": "negotiation",
            "stage": "soft_collection",
            "next_action_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert collection_plan.status_code == 200, collection_plan.text
    contact_note = await client.post(
        f"/v1/collections/{collection_case_id}/notes",
        json={
            "channel": "phone",
            "note": "Nasabah berhasil dihubungi dan menyampaikan rencana pembayaran.",
            "outcome": "promise_to_pay",
            "next_action_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
        headers=headers,
    )
    assert contact_note.status_code == 201, contact_note.text
    promise = await client.post(
        f"/v1/collections/{collection_case_id}/promises",
        json={
            "amount": "7350000",
            "promised_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "channel": "phone",
            "note": "Nasabah berjanji melunasi seluruh kewajiban setelah penerimaan usaha.",
        },
        headers=headers,
    )
    assert promise.status_code == 201, promise.text
    broken_promise = await client.post(
        f"/v1/collections/{collection_case_id}/promises/{promise.json()['id']}/resolve",
        json={"status": "broken", "reason": "Dana belum tersedia pada tanggal yang disepakati"},
        headers=headers,
    )
    assert broken_promise.status_code == 200, broken_promise.text
    escalated_collection = await client.get(f"/v1/collections/{collection_case_id}", headers=headers)
    assert escalated_collection.json()["stage"] == "intensive_collection"
    assert escalated_collection.json()["strategy"] == "field_visit"
    settled = await client.post(
        "/v1/settlements",
        json={
            "application_id": application_id,
            "settlement_type": "repayment",
            "external_reference": "PAY-TEST-001",
            "amount": "7350000",
            "idempotency_key": "repayment-test-001",
        },
        headers=headers,
    )
    assert settled.status_code == 201, settled.text
    repeated_settlement = await client.post(
        "/v1/settlements",
        json={
            "application_id": application_id,
            "settlement_type": "repayment",
            "external_reference": "PAY-TEST-001",
            "amount": "7350000",
            "idempotency_key": "repayment-test-001",
        },
        headers=headers,
    )
    assert repeated_settlement.status_code == 201, repeated_settlement.text
    finance_after = await client.get("/v1/finance/overview", headers=headers)
    assert float(finance_after.json()["outstanding_principal"]) == 0

    release_approval = await db_session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.org_id == application.org_id,
            ApprovalRequest.aggregate_type == "custody_release",
            ApprovalRequest.aggregate_id == application.id,
            ApprovalRequest.status == "pending",
        )
    )
    assert release_approval is not None
    await approval_service.decide_approval(
        db_session,
        application.org_id,
        release_approval.id,
        checker.id,
        "approved",
        "Settlement dan identitas penerima telah diverifikasi",
    )

    passport = await client.get(f"/v1/collateral/{application_id}/timeline", headers=headers)
    assert passport.status_code == 200
    assert passport.json()["collateral_status"] == "release_authorized"
    assert len(passport.json()["events"]) >= 6

    period_close = await client.post(
        f"/v1/accounting/periods/{accounting_period.json()['id']}/close",
        json={"reason": "Rekonsiliasi kas, subledger, dan trial balance periode Oktober selesai"},
        headers=headers,
    )
    assert period_close.status_code == 200, period_close.text
    period_approval = await db_session.get(ApprovalRequest, period_close.json()["id"])
    assert period_approval is not None
    await approval_service.decide_approval(
        db_session,
        application.org_id,
        period_approval.id,
        checker.id,
        "approved",
        "Closing checklist dan rekonsiliasi telah diperiksa",
    )
    blocked_posting = await client.post(
        f"/v1/finance/cashboxes/{cashboxes.json()[0]['id']}/fund",
        json={"amount": "1000", "external_reference": "LATE-POST", "idempotency_key": "late-posting-test"},
        headers=headers,
    )
    assert blocked_posting.status_code == 409, blocked_posting.text

    other = await client.post("/orgs", json={"name": "Tenant Lain", "slug": "tenant-lain-mvp"}, headers=base_headers)
    assert other.status_code == 201
    switched = await client.post("/orgs/tenant-lain-mvp/switch", headers=base_headers)
    other_headers = {"Authorization": f"Bearer {switched.json()['access_token']}"}
    isolated = await client.get(f"/v1/applications/{application_id}", headers=other_headers)
    assert isolated.status_code == 404
