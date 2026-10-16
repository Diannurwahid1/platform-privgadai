"""PaddleOCR adapter contract tests."""

from __future__ import annotations

import httpx
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
async def test_paddleocr_normalizes_payload_and_discards_raw_lines() -> None:
    respx.post("http://localhost:8001/scan/ktp").mock(
        return_value=httpx.Response(
            200,
            json={
                "request_id": "ocr-001",
                "data": {
                    "nik": "3273010101900001",
                    "nama": "BUDI SANTOSO",
                    "tanggal_lahir": "01-01-1990",
                    "confidence": 0.97,
                    "raw_lines": [{"text": "discard this"}],
                },
            },
        )
    )
    result = await kyc_provider.run_ocr(
        _settings(KYC_OCR_PROVIDER="paddle_http"), b"synthetic-image", "image/jpeg", "ktp.jpg"
    )
    assert result.provider_name == "paddleocr"
    assert result.environment == "internal"
    assert result.internal_verified is False
    assert result.payload["nik"] == "3273010101900001"
    assert result.payload["tanggal_lahir"] == "01-01-1990"
    assert "raw_lines" not in result.payload


@respx.mock
async def test_paddleocr_rejects_empty_structured_result() -> None:
    respx.post("http://localhost:8001/scan/ktp").mock(return_value=httpx.Response(200, json={"data": {}}))
    try:
        await kyc_provider.run_ocr(
            _settings(KYC_OCR_PROVIDER="paddle_http"), b"synthetic-image", "image/jpeg", "ktp.jpg"
        )
    except Exception as exc:
        assert "tidak menemukan data KTP" in str(exc)
    else:
        raise AssertionError("empty PaddleOCR result should be rejected")
