"""Provider-neutral OCR and identity verification adapters.

OCR is extraction evidence only. Only a successful live identity verification
may set ``officially_verified``; sandbox responses are always simulations.
"""

from __future__ import annotations

import base64
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
    officially_verified: bool = False


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


def _match_status(payload: dict[str, Any]) -> bool | None:
    source = _data(payload)
    for key in ("is_match", "matched", "match", "verified"):
        value = source.get(key)
        if isinstance(value, bool):
            return value
    match_fields = [source.get(key) for key in ("nik", "name", "birth_date")]
    boolean_fields = [value for value in match_fields if isinstance(value, bool)]
    if boolean_fields:
        return all(boolean_fields) and len(boolean_fields) == len(match_fields)
    return None


async def _post_json(url: str, settings: Settings, payload: dict[str, object]) -> dict[str, Any]:
    headers = {"App-ID": settings.VERIHUBS_APP_ID, "API-Key": settings.VERIHUBS_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=settings.KYC_PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            decoded = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Provider KYC tidak dapat memproses permintaan") from exc
    if not isinstance(decoded, dict):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Respons provider KYC tidak valid")
    return decoded


async def run_ocr(settings: Settings, content: bytes, content_type: str, file_name: str) -> ProviderResult:
    if settings.KYC_OCR_PROVIDER == "disabled":
        raise HTTPException(status.HTTP_409_CONFLICT, "Provider OCR KTP belum dikonfigurasi")
    if settings.KYC_OCR_PROVIDER == "local_http":
        headers = {"X-API-Key": settings.KYC_OCR_API_KEY} if settings.KYC_OCR_API_KEY else {}
        url = f"{settings.KYC_OCR_BASE_URL.rstrip('/')}/scan/ktp"
        try:
            async with httpx.AsyncClient(timeout=settings.KYC_PROVIDER_TIMEOUT_SECONDS) as client:
                response = await client.post(url, files={"file": (file_name, content, content_type)}, headers=headers)
                response.raise_for_status()
                decoded = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Layanan OCR lokal tidak dapat memproses KTP") from exc
        if not isinstance(decoded, dict):
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Respons OCR lokal tidak valid")
        return ProviderResult("local_http", "local", "completed", _reference(decoded), _ocr_payload(decoded))

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "OCR Verihubs menerima gambar maksimal 5 MB")
    decoded = await _post_json(
        "https://api.verihubs.com/v2/ktp/extract",
        settings,
        {
            "image": base64.b64encode(content).decode(),
            "validate_quality": True,
            "validate_rotation": True,
        },
    )
    return ProviderResult("verihubs", "provider", "completed", _reference(decoded), _ocr_payload(decoded))


async def run_identity_verification(
    settings: Settings, *, nik: str, legal_name: str, birth_date: str, reference_id: str
) -> ProviderResult:
    if settings.KYC_IDV_MODE == "disabled":
        raise HTTPException(status.HTTP_409_CONFLICT, "Provider identity verification belum dikonfigurasi")
    decoded = await _post_json(
        settings.KYC_IDV_URL,
        settings,
        {"nik": nik, "name": legal_name, "birth_date": birth_date, "reference_id": reference_id},
    )
    matched = _match_status(decoded)
    environment = "sandbox" if settings.KYC_IDV_MODE == "verihubs_sandbox" else "live"
    check_status = "matched" if matched is True else "not_matched" if matched is False else "completed"
    officially_verified = environment == "live" and matched is True
    summary: dict[str, object] = {
        "match_result": matched,
        "message": str(decoded.get("message", "Respons provider diterima"))[:500],
    }
    return ProviderResult(
        "verihubs",
        environment,
        check_status,
        _reference(decoded) or reference_id,
        summary,
        officially_verified,
    )
