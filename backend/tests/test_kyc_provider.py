"""Provider adapter semantics: OCR extraction, sandbox labelling, live verification."""

from __future__ import annotations

import httpx
import pytest
import respx

from dogeapi.operations import kyc_provider
from dogeapi.settings import Settings


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "test",
        "JWT_SECRET_KEY": "test-secret-please-do-not-use-in-prod-32-chars",
        "FEATURE_AUDIT_LOG": False,
    }
    values.update(overrides)
    return Settings(**values)


@respx.mock
async def test_local_ocr_is_extraction_only_and_discards_raw_lines() -> None:
    respx.post("http://localhost:8001/scan/ktp").mock(
        return_value=httpx.Response(
            200,
            json={
                "nik": "3273010101900001",
                "nama": "BUDI SANTOSO",
                "confidence": 0.97,
                "raw_lines": [{"text": "unneeded raw OCR"}],
            },
        )
    )
    result = await kyc_provider.run_ocr(
        _settings(KYC_OCR_PROVIDER="local_http"), b"synthetic-image", "image/jpeg", "ktp.jpg"
    )
    assert result.provider_name == "local_http"
    assert result.environment == "local"
    assert result.officially_verified is False
    assert result.payload["nik"] == "3273010101900001"
    assert "raw_lines" not in result.payload


@respx.mock
async def test_verihubs_sandbox_match_is_never_official() -> None:
    url = "https://api.verihubs.com/v1/data-verification/id-verification/sandbox"
    respx.post(url).mock(
        return_value=httpx.Response(
            200,
            json={"data": {"nik": True, "name": True, "birth_date": True}, "reference_id": "sandbox-001"},
        )
    )
    result = await kyc_provider.run_identity_verification(
        _settings(
            KYC_IDV_MODE="verihubs_sandbox",
            KYC_IDV_URL=url,
            VERIHUBS_APP_ID="test-app",
            VERIHUBS_API_KEY="test-key",
        ),
        nik="3273010101900001",
        legal_name="BUDI SANTOSO",
        birth_date="01-01-1990",
        reference_id="KYC-001",
    )
    assert result.status == "matched"
    assert result.environment == "sandbox"
    assert result.officially_verified is False


@respx.mock
async def test_live_matched_response_can_be_marked_official() -> None:
    url = "https://identity.example.test/v1/verify"
    respx.post(url).mock(return_value=httpx.Response(200, json={"matched": True, "reference_id": "live-001"}))
    result = await kyc_provider.run_identity_verification(
        _settings(
            KYC_IDV_MODE="verihubs_live",
            KYC_IDV_URL=url,
            VERIHUBS_APP_ID="live-app",
            VERIHUBS_API_KEY="live-key",
        ),
        nik="3273010101900001",
        legal_name="BUDI SANTOSO",
        birth_date="01-01-1990",
        reference_id="KYC-001",
    )
    assert result.status == "matched"
    assert result.environment == "live"
    assert result.officially_verified is True


def test_production_rejects_sandbox_identity_mode() -> None:
    with pytest.raises(ValueError, match="sandbox provider"):
        _settings(
            APP_ENV="production",
            BUILD_SHA="release-1",
            JWT_COOKIE_SECURE=True,
            PII_ENCRYPTION_KEY="Z0FBQUFBQm9nMXg1c1F1bW9ja19yRGpIZHcyVXhHZHM=",
            MALWARE_SCANNER_MODE="clamav",
            PRIVILEGED_MFA_ENFORCED=True,
            KYC_IDV_MODE="verihubs_sandbox",
            VERIHUBS_APP_ID="test-app",
            VERIHUBS_API_KEY="test-key",
        )
