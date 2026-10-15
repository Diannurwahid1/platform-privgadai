"""Integration coverage for the first PrivGadai operations vertical slice."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import ApplicationStatusHistory, Asset, Borrower, Branch, LoanApplication

pytestmark = pytest.mark.integration


async def _register(client: AsyncClient) -> tuple[dict[str, str], UUID]:
    response = await client.post(
        "/auth/register",
        json={
            "email": "ops-owner@example.com",
            "password": "correct horse battery staple",
            "full_name": "Ops Owner",
        },
    )
    assert response.status_code == 201
    body = response.json()
    return {"Authorization": f"Bearer {body['tokens']['access_token']}"}, UUID(body["user"]["id"])


async def _create_and_switch(
    client: AsyncClient, headers: dict[str, str], *, name: str, slug: str
) -> tuple[UUID, dict[str, str]]:
    created = await client.post("/orgs", json={"name": name, "slug": slug}, headers=headers)
    assert created.status_code == 201
    switched = await client.post(f"/orgs/{slug}/switch", headers=headers)
    assert switched.status_code == 200
    scoped = {"Authorization": f"Bearer {switched.json()['access_token']}"}
    return UUID(created.json()["id"]), scoped


async def test_dashboard_uses_real_tenant_scoped_operations_data(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    base_headers, actor_id = await _register(client)
    org_id, scoped_headers = await _create_and_switch(client, base_headers, name="Mitra Gadai Demo", slug="mitra-demo")

    branch = Branch(org_id=org_id, code="JKT-01", name="Cabang Jakarta", city="Jakarta")
    borrower = Borrower(
        org_id=org_id,
        customer_reference="BRW-001",
        full_name="Nasabah Sintetis",
        phone_masked="08•• •••• 1001",
    )
    db_session.add_all([branch, borrower])
    await db_session.flush()

    application = LoanApplication(
        org_id=org_id,
        branch_id=branch.id,
        borrower_id=borrower.id,
        assigned_user_id=actor_id,
        application_no="PG-2026-0001",
        status="appraisal",
        priority="high",
        asset_category="emas",
        requested_amount=Decimal("7500000"),
        submitted_at=datetime.now(UTC),
    )
    db_session.add(application)
    await db_session.flush()
    db_session.add_all(
        [
            Asset(
                org_id=org_id,
                application_id=application.id,
                asset_code="AST-0001",
                category="emas",
                brand="Antam",
                model="Logam Mulia 10gr",
                condition_grade="A",
                indicative_value=Decimal("10500000"),
                collateral_status="with_customer",
            ),
            ApplicationStatusHistory(
                org_id=org_id,
                application_id=application.id,
                actor_user_id=actor_id,
                from_status="under_review",
                to_status="appraisal",
                note="Siap ditaksir oleh penaksir manusia.",
            ),
        ]
    )
    await db_session.flush()

    response = await client.get("/v1/operations/dashboard", headers=scoped_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["metrics"]["appraisal"] == 1
    assert body["metrics"]["requested_amount"] == 7_500_000
    assert body["work_queue"][0]["application_no"] == "PG-2026-0001"
    assert body["work_queue"][0]["borrower_name"] == "Nasabah Sintetis"
    assert body["recent_activity"][0]["to_status"] == "appraisal"

    _, other_scoped_headers = await _create_and_switch(client, base_headers, name="Mitra Lain", slug="mitra-lain")
    isolated = await client.get("/v1/operations/dashboard", headers=other_scoped_headers)
    assert isolated.status_code == 200
    assert isolated.json()["metrics"]["appraisal"] == 0
    assert isolated.json()["work_queue"] == []
