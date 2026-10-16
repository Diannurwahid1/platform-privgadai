"""PaddleOCR adapter for internal KTP document verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException, status

from dogeapi.settings import Settings


@dataclass(frozen=True)
class ProviderResult:
    provider_name: str
    environment: str
    status: str
    reference: str | None
    payload: dict[str, object]
    internal_verified: bool = False


OCR_FIELDS = {
    "nik",
    "full_name",
    "nama",
    "date_of_birth",
    "tanggal_lahir",
    "place_of_birth",
    "tempat_lahir",
    "gender",
    "jenis_kelamin",
    "address",
    "alamat",
    "province",
    "provinsi",
    "city",
    "kabupaten_kota",
    "occupation",
    "pekerjaan",
    "nationality",
    "kewarganegaraan",
    "marital_status",
    "status_perkawinan",
    "confidence",
    "image_quality",
    "message",
    "status_code",
}


def _data(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("data", "result"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            return nested
    return payload


def _reference(payload: dict[str, Any]) -> str | None:
    source = _data(payload)
    for key in ("reference_id", "transaction_id", "id", "request_id"):
        value = source.get(key) or payload.get(key)
        if isinstance(value, (str, int)):
            return str(value)[:160]
    return None


def _ocr_payload(payload: dict[str, Any]) -> dict[str, object]:
    source = _data(payload)
    return {key: value for key, value in source.items() if key in OCR_FIELDS and value is not None}


async def run_ocr(settings: Settings, content: bytes, content_type: str, file_name: str) -> ProviderResult:
    if settings.KYC_OCR_PROVIDER == "disabled":
        raise HTTPException(status.HTTP_409_CONFLICT, "PaddleOCR KTP belum diaktifkan")
    headers = {"X-API-Key": settings.KYC_OCR_API_KEY} if settings.KYC_OCR_API_KEY else {}
    url = f"{settings.KYC_OCR_BASE_URL.rstrip('/')}/scan/ktp"
    try:
        async with httpx.AsyncClient(timeout=settings.KYC_OCR_TIMEOUT_SECONDS) as client:
            response = await client.post(url, files={"file": (file_name, content, content_type)}, headers=headers)
            response.raise_for_status()
            decoded = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Layanan PaddleOCR tidak dapat memproses KTP") from exc
    if not isinstance(decoded, dict):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Respons PaddleOCR tidak valid")
    payload = _ocr_payload(decoded)
    if not payload:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "PaddleOCR tidak menemukan data KTP")
    return ProviderResult("paddleocr", "internal", "completed", _reference(decoded), payload)
