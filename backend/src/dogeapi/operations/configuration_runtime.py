"""Validated, effective-dated configuration access for operational engines."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import ConfigurationVersion

_SECRET_MARKERS = ("password", "secret", "token", "api_key", "private_key")
_PERCENT_FIELDS = {"max_ltv_percent", "service_fee_percent", "tolerance_percent"}
_POSITIVE_NUMBER_FIELDS = {
    "min_amount",
    "max_amount",
    "submission_sla_hours",
    "approval_sla_hours",
    "retention_years",
    "session_idle_minutes",
    "session_absolute_hours",
    "idle_timeout_minutes",
    "absolute_timeout_hours",
}
_BOOLEAN_FIELDS = {
    "enabled",
    "dispatch_evidence_required",
    "release_dual_control",
    "period_close_requires_approval",
    "official_validator_required",
    "require_active_template",
}
_ALLOWED_FIELDS: dict[str, set[str]] = {
    "product": {
        "enabled",
        "min_amount",
        "max_amount",
        "allowed_tenors_days",
        "agreement_type",
        "required_kyc_status",
    },
    "pricing": {"max_ltv_percent", "service_fee_percent", "rounding_mode", "currency"},
    "appraisal": {"max_ltv_percent", "required_evidence_types", "reappraisal_days", "specialist_categories"},
    "workflow": {"submission_sla_hours", "approval_sla_hours", "required_steps", "escalation_hours"},
    "custody": {"dispatch_evidence_required", "required_evidence_types", "release_dual_control"},
    "accounting": {
        "payment_allocation_order",
        "period_close_requires_approval",
        "reconciliation_tolerance",
    },
    "regulatory": {"require_active_template", "official_validator_required", "retention_years", "code_set_version"},
    "access": {"authority_limits", "step_up_actions", "allowed_roles"},
    "security": {
        "session_idle_minutes",
        "session_absolute_hours",
        "idle_timeout_minutes",
        "absolute_timeout_hours",
        "mfa_required_roles",
        "lockout_attempts",
    },
}


def _problem(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, message)


def _decimal(value: object, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise _problem(f"{field} harus berupa angka") from exc


def _validate_no_plaintext_secret(value: object, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            child_path = f"{path}.{key}"
            if any(marker in key.lower() for marker in _SECRET_MARKERS):
                if isinstance(nested, str) and nested.startswith(("ref:", "env:", "vault:")):
                    continue
                raise _problem(f"{child_path} harus memakai reference secret, bukan plaintext")
            _validate_no_plaintext_secret(nested, child_path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_no_plaintext_secret(nested, f"{path}[{index}]")


def validate_configuration_payload(domain: str, payload: dict[str, object]) -> dict[str, object]:
    """Validate common controls and known fields for a configuration domain."""
    if not payload:
        raise _problem("payload konfigurasi tidak boleh kosong")
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise _problem("payload konfigurasi harus JSON yang valid") from exc
    _validate_no_plaintext_secret(payload)

    known = _ALLOWED_FIELDS.get(domain)
    if known is not None:
        unknown = sorted(set(payload) - known)
        if unknown:
            raise _problem(f"Field tidak dikenal untuk domain {domain}: {', '.join(unknown)}")
    for field in _PERCENT_FIELDS & payload.keys():
        value = _decimal(payload[field], field)
        if value < 0 or value > 100:
            raise _problem(f"{field} harus berada pada rentang 0 sampai 100")
    for field in _POSITIVE_NUMBER_FIELDS & payload.keys():
        if _decimal(payload[field], field) <= 0:
            raise _problem(f"{field} harus lebih besar dari 0")
    for field in _BOOLEAN_FIELDS & payload.keys():
        if not isinstance(payload[field], bool):
            raise _problem(f"{field} harus berupa boolean")
    if (
        "min_amount" in payload
        and "max_amount" in payload
        and _decimal(payload["min_amount"], "min_amount") > _decimal(payload["max_amount"], "max_amount")
    ):
        raise _problem("min_amount tidak boleh melebihi max_amount")
    for field in ("allowed_tenors_days", "required_steps", "required_evidence_types", "specialist_categories"):
        if field in payload and (not isinstance(payload[field], list) or not payload[field]):
            raise _problem(f"{field} harus berupa daftar yang tidak kosong")
    if "allowed_tenors_days" in payload and any(
        not isinstance(day, int) or day <= 0 for day in payload["allowed_tenors_days"]
    ):
        raise _problem("allowed_tenors_days hanya boleh berisi integer positif")
    if "payment_allocation_order" in payload:
        order = payload["payment_allocation_order"]
        if not isinstance(order, list) or set(order) != {"fee", "principal"} or len(order) != 2:
            raise _problem("payment_allocation_order harus memuat fee dan principal tepat satu kali")
    return payload


async def get_effective_configuration(
    session: AsyncSession,
    org_id: UUID,
    domain: str,
    keys: str | list[str],
    *,
    at: datetime | None = None,
) -> ConfigurationVersion | None:
    """Resolve the first matching effective configuration in key priority order."""
    point_in_time = at or datetime.now(UTC)
    candidates = [keys] if isinstance(keys, str) else keys
    for key in candidates:
        item = await session.scalar(
            select(ConfigurationVersion).where(
                ConfigurationVersion.org_id == org_id,
                ConfigurationVersion.domain == domain,
                ConfigurationVersion.config_key == key,
                ConfigurationVersion.status == "effective",
                ConfigurationVersion.effective_from <= point_in_time,
                (
                    ConfigurationVersion.effective_until.is_(None)
                    | (ConfigurationVersion.effective_until > point_in_time)
                ),
            )
        )
        if item is not None:
            validate_configuration_payload(domain, item.payload)
            return item
    return None


async def get_effective_payload(
    session: AsyncSession,
    org_id: UUID,
    domain: str,
    keys: str | list[str],
) -> dict[str, Any]:
    item = await get_effective_configuration(session, org_id, domain, keys)
    return dict(item.payload) if item else {}
