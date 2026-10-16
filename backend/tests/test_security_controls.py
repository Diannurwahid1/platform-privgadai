"""Privileged MFA, step-up, session revocation, and security event coverage."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from dogeapi.auth.mfa import totp_code

pytestmark = pytest.mark.integration


async def test_mfa_session_inventory_step_up_and_revocation(client: AsyncClient) -> None:
    password = "correct horse battery staple"
    registered = await client.post(
        "/auth/register",
        json={"email": "security-owner@example.com", "password": password, "full_name": "Security Owner"},
    )
    assert registered.status_code == 201, registered.text
    first_token = registered.json()["tokens"]["access_token"]
    first_headers = {"Authorization": f"Bearer {first_token}"}

    overview = await client.get("/auth/security", headers=first_headers)
    assert overview.status_code == 200, overview.text
    assert overview.json()["mfa_enabled"] is False
    first_session_id = overview.json()["current_session_id"]

    setup = await client.post("/auth/mfa/setup", json={"password": password}, headers=first_headers)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/")

    activated = await client.post("/auth/mfa/activate", json={"code": totp_code(secret)}, headers=first_headers)
    assert activated.status_code == 200, activated.text
    assert activated.json()["enabled"] is True
    assert len(activated.json()["recovery_codes"]) == 8

    missing_mfa = await client.post("/auth/login", json={"email": "security-owner@example.com", "password": password})
    assert missing_mfa.status_code == 401
    authenticated = await client.post(
        "/auth/login",
        json={"email": "security-owner@example.com", "password": password, "mfa_code": totp_code(secret)},
    )
    assert authenticated.status_code == 200, authenticated.text
    second_token = authenticated.json()["access_token"]
    second_headers = {"Authorization": f"Bearer {second_token}"}

    sessions = await client.get("/auth/sessions", headers=second_headers)
    assert sessions.status_code == 200, sessions.text
    assert len(sessions.json()) == 2
    assert any(item["mfa_authenticated"] for item in sessions.json())

    blocked_revoke = await client.post(
        f"/auth/sessions/{first_session_id}/revoke",
        json={"reason": "Close prior browser session"},
        headers=second_headers,
    )
    assert blocked_revoke.status_code == 403

    step_up = await client.post(
        "/auth/step-up",
        json={"password": password, "mfa_code": totp_code(secret)},
        headers=second_headers,
    )
    assert step_up.status_code == 200, step_up.text
    assert step_up.json()["status"] == "verified"

    revoked = await client.post(
        f"/auth/sessions/{first_session_id}/revoke",
        json={"reason": "Close prior browser session"},
        headers=second_headers,
    )
    assert revoked.status_code == 200, revoked.text
    rejected_old_session = await client.get("/auth/me", headers=first_headers)
    assert rejected_old_session.status_code == 401

    events = await client.get("/auth/security-events", headers=second_headers)
    assert events.status_code == 200, events.text
    event_types = {item["event_type"] for item in events.json()}
    assert {"MfaActivated", "StepUpSucceeded", "SessionRevoked"}.issubset(event_types)
