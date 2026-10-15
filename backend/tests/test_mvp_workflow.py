"""End-to-end MVP workflow and tenant boundary coverage."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from dogeapi.operations.state_machine import APPLICATION_TRANSITIONS, COLLATERAL_TRANSITIONS, can_transition


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


async def test_complete_mvp_workflow_is_tenant_scoped(client: AsyncClient) -> None:
    base_headers, headers = await _register_and_switch(client)

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
    disbursed = await client.post(
        f"/v1/loans/{application_id}/disburse",
        json={"external_reference": "DISB-TEST-001"},
        headers=headers,
    )
    assert disbursed.status_code == 200, disbursed.text
    settled = await client.post(
        "/v1/settlements",
        json={
            "application_id": application_id,
            "settlement_type": "repayment",
            "external_reference": "PAY-TEST-001",
            "amount": "7350000",
        },
        headers=headers,
    )
    assert settled.status_code == 201, settled.text

    passport = await client.get(f"/v1/collateral/{application_id}/timeline", headers=headers)
    assert passport.status_code == 200
    assert passport.json()["collateral_status"] == "release_authorized"
    assert len(passport.json()["events"]) >= 6

    other = await client.post("/orgs", json={"name": "Tenant Lain", "slug": "tenant-lain-mvp"}, headers=base_headers)
    assert other.status_code == 201
    switched = await client.post("/orgs/tenant-lain-mvp/switch", headers=base_headers)
    other_headers = {"Authorization": f"Bearer {switched.json()['access_token']}"}
    isolated = await client.get(f"/v1/applications/{application_id}", headers=other_headers)
    assert isolated.status_code == 404
