"""Negative authorization matrix for tenant objects and branch-scoped reads."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

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
async def branch_matrix(client: AsyncClient) -> dict[str, Any]:
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

    assignment = await client.post(
        "/v1/master/staff-assignments",
        json={
            "user_id": member["id"],
            "branch_id": branches[0]["id"],
            "operational_role": "loan_officer",
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
    evidence = await client.post(
        f"/v1/applications/{hidden['id']}/evidence/upload",
        data={"evidence_type": "asset_photo"},
        files={"file": ("asset.png", b"\x89PNG\r\n\x1a\nprivate", "image/png")},
        headers=owner["headers"],
    )
    assert evidence.status_code == 201, evidence.text

    return {
        "owner": owner,
        "member": member,
        "visible": visible,
        "hidden": hidden,
        "evidence_id": evidence.json()["id"],
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


async def test_owner_retains_tenant_wide_visibility(client: AsyncClient, branch_matrix: dict[str, Any]) -> None:
    response = await client.get("/v1/applications", headers=branch_matrix["owner"]["headers"])
    assert response.status_code == 200, response.text
    assert {item["id"] for item in response.json()} == {
        branch_matrix["visible"]["id"],
        branch_matrix["hidden"]["id"],
    }
