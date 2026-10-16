"""PaddleOCR adapter for internal KTP document verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    "rt_rw",
    "kelurahan_desa",
    "kecamatan",
    "confidence",
    "image_quality",
    "message",
    "status_code",
}


def _string(payload: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.strip().split())
    return ""


def normalize_ocr_autofill(payload: dict[str, object]) -> dict[str, object]:
    """Map provider-specific Indonesian KTP fields to the KYC form contract."""
    raw_date = _string(payload, "date_of_birth", "tanggal_lahir")
    birth_date = ""
    for pattern in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            birth_date = datetime.strptime(raw_date, pattern).date().isoformat()
            break
        except ValueError:
            continue

    raw_gender = _string(payload, "gender", "jenis_kelamin").upper()
    gender = "female" if "PEREMPUAN" in raw_gender or raw_gender == "FEMALE" else "male" if raw_gender else ""
    address_parts = [
        _string(payload, "address", "alamat"),
        f"RT/RW {_string(payload, 'rt_rw')}" if _string(payload, "rt_rw") else "",
        f"Kel/Desa {_string(payload, 'kelurahan_desa')}" if _string(payload, "kelurahan_desa") else "",
        f"Kec. {_string(payload, 'kecamatan')}" if _string(payload, "kecamatan") else "",
    ]
    nik = "".join(character for character in _string(payload, "nik") if character.isdigit())[-16:]
    confidence = payload.get("confidence")
    return {
        "nik": nik,
        "legal_name": _string(payload, "full_name", "nama").upper(),
        "birth_place": _string(payload, "place_of_birth", "tempat_lahir").upper(),
        "birth_date": birth_date,
        "gender": gender,
        "address": ", ".join(part for part in address_parts if part),
        "province": _string(payload, "province", "provinsi").upper(),
        "city": _string(payload, "city", "kabupaten_kota").upper(),
        "occupation": _string(payload, "occupation", "pekerjaan").upper(),
        "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
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
