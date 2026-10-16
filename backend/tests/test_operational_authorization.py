"""Negative authorization matrix for tenant objects and branch-scoped reads."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import CollectionCase, LoanAccount

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"


async def _register(client: AsyncClient, email: str) -> dict[str, Any]:
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": email.split("@", 1)[0].title()},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "id": body["user"]["id"],
        "headers": {"Authorization": f"Bearer {body['tokens']['access_token']}"},
    }


async def _switch(client: AsyncClient, headers: dict[str, str], slug: str) -> dict[str, str]:
    response = await client.post(f"/orgs/{slug}/switch", headers=headers)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _create_application(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    branch_id: str,
    product_id: str,
    customer_name: str,
) -> dict[str, Any]:
    response = await client.post(
        "/v1/applications",
        json={
            "branch_id": branch_id,
            "product_id": product_id,
            "borrower": {"full_name": customer_name, "phone": "081234567890"},
            "asset": {
                "category_code": "gold",
                "brand": "Antam",
                "model": "Logam Mulia 10gr",
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
    assert response.status_code == 201, response.text
    detail = await client.get(f"/v1/applications/{response.json()['application_id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    return detail.json()


@pytest.fixture
async def branch_matrix(client: AsyncClient, db_session: AsyncSession) -> dict[str, Any]:
    owner = await _register(client, "scope-owner@example.com")
    created_org = await client.post(
        "/orgs",
        json={"name": "Scope Matrix", "slug": "scope-matrix"},
        headers=owner["headers"],
    )
    assert created_org.status_code == 201, created_org.text
    owner["headers"] = await _switch(client, owner["headers"], "scope-matrix")

    member = await _register(client, "scope-member@example.com")
    invitation = await client.post(
        "/orgs/scope-matrix/invitations",
        json={"email": "scope-member@example.com", "role": "member"},
        headers=owner["headers"],
    )
    assert invitation.status_code == 201, invitation.text
    token = invitation.json()["invite_link"].split("token=", 1)[1]
    accepted = await client.post(
        "/invitations/accept",
        json={"token": token},
        headers=member["headers"],
    )
    assert accepted.status_code == 200, accepted.text
    member["headers"] = await _switch(client, member["headers"], "scope-matrix")

    branches = []
    for code, city in (("JKT-01", "Jakarta"), ("SBY-01", "Surabaya")):
        response = await client.post(
            "/v1/master/branches",
            json={"code": code, "name": f"Cabang {city}", "city": city, "address": f"Jl. {city}"},
            headers=owner["headers"],
        )
        assert response.status_code == 201, response.text
        branches.append(response.json())

    category = await client.post(
        "/v1/master/asset-categories",
        json={"code": "gold", "name": "Emas", "requires_serial_number": True},
        headers=owner["headers"],
    )
    assert category.status_code == 201, category.text
    product = await client.post(
        "/v1/master/loan-products",
        json={
            "code": "GOLD-30",
            "name": "Gadai Emas",
            "min_amount": "500000",
            "max_amount": "20000000",
            "max_ltv_percent": "80",
            "allowed_tenors_days": [30],
            "service_fee_percent": "5",
        },
        headers=owner["headers"],
    )
    assert product.status_code == 201, product.text

    for operational_role in ("loan_officer", "finance", "custodian"):
        assignment = await client.post(
            "/v1/master/staff-assignments",
            json={
                "user_id": member["id"],
                "branch_id": branches[0]["id"],
                "operational_role": operational_role,
                "is_active": True,
            },
            headers=owner["headers"],
        )
        assert assignment.status_code == 201, assignment.text

    visible = await _create_application(
        client,
        owner["headers"],
        branch_id=branches[0]["id"],
        product_id=product.json()["id"],
        customer_name="Nasabah Jakarta",
    )
    hidden = await _create_application(
        client,
        owner["headers"],
        branch_id=branches[1]["id"],
        product_id=product.json()["id"],
        customer_name="Nasabah Surabaya",
    )
    collection_cases = []
    for index, application in enumerate((visible, hidden), start=1):
        loan = LoanAccount(
            org_id=UUID(created_org.json()["id"]),
            application_id=UUID(application["id"]),
            account_no=f"LN-SCOPE-{index}",
            status="active",
            principal_amount=Decimal("7000000"),
            total_due_amount=Decimal("7350000"),
            outstanding_principal=Decimal("7000000"),
            outstanding_fee=Decimal("350000"),
            due_at=datetime.now(UTC) - timedelta(days=5),
        )
        db_session.add(loan)
        await db_session.flush()
        case = CollectionCase(
            org_id=UUID(created_org.json()["id"]),
            loan_account_id=loan.id,
            due_at=loan.due_at,
            outstanding_amount=Decimal("7350000"),
        )
        db_session.add(case)
        await db_session.flush()
        collection_cases.append(case)
    evidence = await client.post(
        f"/v1/applications/{hidden['id']}/evidence/upload",
        data={"evidence_type": "asset_photo"},
        files={"file": ("asset.png", b"\x89PNG\r\n\x1a\nprivate", "image/png")},
        headers=owner["headers"],
    )
    assert evidence.status_code == 201, evidence.text
    cashboxes = await client.get("/v1/finance/cashboxes", headers=owner["headers"])
    assert cashboxes.status_code == 200, cashboxes.text
    cashbox_by_branch = {item["branch_id"]: item for item in cashboxes.json()}
    inventory_checks = []
    for index, branch in enumerate(branches, start=1):
        location = await client.post(
            "/v1/master/custody-locations",
            json={
                "branch_id": branch["id"],
                "code": f"VAULT-{index}",
                "name": f"Vault {branch['code']}",
                "location_type": "branch_vault",
            },
            headers=owner["headers"],
        )
        assert location.status_code == 201, location.text
        inventory = await client.post(
            "/v1/inventory-checks",
            json={"location_id": location.json()["id"]},
            headers=owner["headers"],
        )
        assert inventory.status_code == 201, inventory.text
        inventory_checks.append(inventory.json())

    return {
        "owner": owner,
        "member": member,
        "visible": visible,
        "hidden": hidden,
        "evidence_id": evidence.json()["id"],
        "visible_cashbox": cashbox_by_branch[branches[0]["id"]],
        "hidden_cashbox": cashbox_by_branch[branches[1]["id"]],
        "visible_inventory": inventory_checks[0],
        "hidden_inventory": inventory_checks[1],
        "visible_collection_id": str(collection_cases[0].id),
        "hidden_collection_id": str(collection_cases[1].id),
        "visible_branch_id": branches[0]["id"],
        "hidden_branch_id": branches[1]["id"],
    }


async def test_branch_assignment_filters_queue_dashboard_and_customers(
    client: AsyncClient, branch_matrix: dict[str, Any]
) -> None:
    headers = branch_matrix["member"]["headers"]

    queue = await client.get("/v1/applications", headers=headers)
    assert queue.status_code == 200, queue.text
    assert [item["id"] for item in queue.json()] == [branch_matrix["visible"]["id"]]

    dashboard = await client.get("/v1/operations/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    assert [item["id"] for item in dashboard.json()["work_queue"]] == [branch_matrix["visible"]["id"]]
    assert [item["code"] for item in dashboard.json()["branches"]] == ["JKT-01"]

    customers = await client.get("/v1/customers", headers=headers)
    assert customers.status_code == 200, customers.text
    assert [item["id"] for item in customers.json()] == [branch_matrix["visible"]["borrower"]["id"]]


@pytest.mark.parametrize(
    "path_template",
    [
        "/v1/applications/{application_id}",
        "/v1/collateral/{application_id}/timeline",
        "/v1/customers/{customer_id}",
        "/v1/customers/{customer_id}/kyc",
    ],
)
async def test_branch_assignment_denies_hidden_object_details(
    client: AsyncClient,
    branch_matrix: dict[str, Any],
    path_template: str,
) -> None:
    hidden = branch_matrix["hidden"]
    path = path_template.format(
        application_id=hidden["id"],
        customer_id=hidden["borrower"]["id"],
    )
    response = await client.get(path, headers=branch_matrix["member"]["headers"])
    assert response.status_code in {403, 404}, response.text


async def test_branch_assignment_denies_hidden_file_download(
    client: AsyncClient, branch_matrix: dict[str, Any]
) -> None:
    response = await client.get(
        f"/v1/evidence/{branch_matrix['evidence_id']}/download",
        headers=branch_matrix["member"]["headers"],
    )
    assert response.status_code == 403, response.text


async def test_branch_assignment_denies_hidden_kyc_command(client: AsyncClient, branch_matrix: dict[str, Any]) -> None:
    customer_id = branch_matrix["hidden"]["borrower"]["id"]
    response = await client.post(
        f"/v1/customers/{customer_id}/kyc",
        json={
            "nik": "3173010101900001",
            "legal_name": "NASABAH SURABAYA",
            "birth_place": "Surabaya",
            "birth_date": "1990-01-01",
            "gender": "male",
            "address": "Jl. Surabaya",
            "province": "Jawa Timur",
            "city": "Surabaya",
            "occupation": "Wiraswasta",
            "verification_method": "manual_branch",
        },
        headers=branch_matrix["member"]["headers"],
    )
    assert response.status_code == 403, response.text


async def test_business_audit_requires_an_audit_capable_assignment(
    client: AsyncClient, branch_matrix: dict[str, Any]
) -> None:
    response = await client.get("/v1/domain-events", headers=branch_matrix["member"]["headers"])
    assert response.status_code == 403, response.text


async def test_finance_views_and_commands_are_branch_scoped(client: AsyncClient, branch_matrix: dict[str, Any]) -> None:
    headers = branch_matrix["member"]["headers"]
    cashboxes = await client.get("/v1/finance/cashboxes", headers=headers)
    assert cashboxes.status_code == 200, cashboxes.text
    assert [item["id"] for item in cashboxes.json()] == [branch_matrix["visible_cashbox"]["id"]]

    denied = await client.post(
        f"/v1/finance/cashboxes/{branch_matrix['hidden_cashbox']['id']}/fund",
        json={
            "amount": "1000000",
            "external_reference": "SCOPE-TEST-HIDDEN",
            "idempotency_key": "scope-test-hidden-fund",
        },
        headers=headers,
    )
    assert denied.status_code == 403, denied.text

    accounts = await client.get("/v1/finance/loan-accounts", headers=headers)
    assert accounts.status_code == 200, accounts.text
    assert [item["application_id"] for item in accounts.json()] == [branch_matrix["visible"]["id"]]

    reconciliation = await client.post(
        "/v1/finance/reconciliations",
        json={
            "scope": "cash_gl",
            "business_date": datetime.now(UTC).date().isoformat(),
            "branch_id": branch_matrix["hidden_branch_id"],
            "tolerance_amount": "0",
        },
        headers=headers,
    )
    assert reconciliation.status_code == 403, reconciliation.text


async def test_regulatory_workspace_rejects_branch_finance_role(
    client: AsyncClient, branch_matrix: dict[str, Any]
) -> None:
    response = await client.get("/v1/regulatory/templates", headers=branch_matrix["member"]["headers"])
    assert response.status_code == 403, response.text


async def test_inventory_register_and_detail_are_branch_scoped(
    client: AsyncClient, branch_matrix: dict[str, Any]
) -> None:
    headers = branch_matrix["member"]["headers"]
    register = await client.get("/v1/inventory-checks", headers=headers)
    assert register.status_code == 200, register.text
    assert [item["id"] for item in register.json()] == [branch_matrix["visible_inventory"]["id"]]

    hidden = await client.get(
        f"/v1/inventory-checks/{branch_matrix['hidden_inventory']['id']}",
        headers=headers,
    )
    assert hidden.status_code == 403, hidden.text


async def test_collection_register_detail_and_command_are_branch_scoped(
    client: AsyncClient, branch_matrix: dict[str, Any]
) -> None:
    headers = branch_matrix["member"]["headers"]
    register = await client.get("/v1/collections", headers=headers)
    assert register.status_code == 200, register.text
    assert [item["id"] for item in register.json()] == [branch_matrix["visible_collection_id"]]

    hidden_id = branch_matrix["hidden_collection_id"]
    detail = await client.get(f"/v1/collections/{hidden_id}", headers=headers)
    assert detail.status_code == 403, detail.text
    command = await client.post(
        f"/v1/collections/{hidden_id}/notes",
        json={"channel": "phone", "note": "Percobaan lintas cabang", "outcome": "contacted"},
        headers=headers,
    )
    assert command.status_code == 403, command.text


async def test_owner_retains_tenant_wide_visibility(client: AsyncClient, branch_matrix: dict[str, Any]) -> None:
    response = await client.get("/v1/applications", headers=branch_matrix["owner"]["headers"])
    assert response.status_code == 200, response.text
    assert {item["id"] for item in response.json()} == {
        branch_matrix["visible"]["id"],
        branch_matrix["hidden"]["id"],
    }
