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


def test_normalize_ocr_autofill_maps_indonesian_ktp_fields() -> None:
    result = kyc_provider.normalize_ocr_autofill(
        {
            "nik": "3171234567890123",
            "nama": "Mira Setiawan",
            "tempat_lahir": "Jakarta",
            "tanggal_lahir": "18-02-1986",
            "jenis_kelamin": "PEREMPUAN",
            "alamat": "JL. PASTI CEPAT A7/66",
            "rt_rw": "007/008",
            "kelurahan_desa": "PEGADUNGAN",
            "kecamatan": "KALIDERES",
            "provinsi": "DKI Jakarta",
            "kabupaten_kota": "Jakarta Barat",
            "pekerjaan": "Pegawai Swasta",
            "confidence": 0.94,
        }
    )
    assert result == {
        "nik": "3171234567890123",
        "legal_name": "MIRA SETIAWAN",
        "birth_place": "JAKARTA",
        "birth_date": "1986-02-18",
        "gender": "female",
        "address": "JL. PASTI CEPAT A7/66, RT/RW 007/008, Kel/Desa PEGADUNGAN, Kec. KALIDERES",
        "province": "DKI JAKARTA",
        "city": "JAKARTA BARAT",
        "occupation": "PEGAWAI SWASTA",
        "confidence": 0.94,
    }


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
