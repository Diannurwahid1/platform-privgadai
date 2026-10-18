"""Borrower KTP intake must be completed and checked before any new application."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import KycDocument, KycVerification, Organization, User
from dogeapi.operations import kyc_provider, kyc_service
from dogeapi.operations.kyc_schemas import KycReview
from dogeapi.settings import Settings

pytestmark = pytest.mark.integration


async def test_borrower_kyc_upload_and_verified_gate(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.KYC_OCR_PROVIDER = "paddle_http"
    org = Organization(slug=settings.BORROWER_ORG_SLUG, name="PT Murah Gadai Jogja")
    db_session.add(org)
    await db_session.flush()
    registered = await client.post("/borrower/v1/register", json={
        "email": "borrower-kyc@example.com", "password": "borrower-password-123",
        "full_name": "Budi Santoso", "phone": "081234567890",
    })
    assert registered.status_code == 201, registered.text
    borrower_id = registered.json()["id"]
    csrf = {"X-Borrower-CSRF": client.cookies["pg_borrower_csrf"]}
    application = {"estimate_id": str(uuid4()), "branch_id": str(uuid4()), "product_id": str(uuid4()),
                   "requested_amount": 1_000_000, "requested_tenor_days": 30,
                   "consent_document_version": "PRIV-2026.1"}

    assert (await client.get("/borrower/v1/kyc")).json()["status"] == "not_started"
    blocked = await client.post("/borrower/v1/applications", json=application, headers=csrf)
    assert blocked.status_code == 409

    async def fake_ocr(_settings: Settings, _content: bytes, _type: str, _name: str) -> kyc_provider.ProviderResult:
        return kyc_provider.ProviderResult("paddleocr", "internal", "completed", "ocr-test", {
            "nik": "3273010101900001", "nama": "BUDI SANTOSO", "tempat_lahir": "BANDUNG",
            "tanggal_lahir": "01-01-1990", "jenis_kelamin": "LAKI-LAKI", "alamat": "JALAN MERDEKA NOMOR 1",
            "provinsi": "JAWA BARAT", "kabupaten_kota": "KOTA BANDUNG",
        })

    monkeypatch.setattr(kyc_provider, "run_ocr", fake_ocr)
    photo = b"\xff\xd8\xffsynthetic-ktp\xff\xd9"
    preview = await client.post("/borrower/v1/kyc/ocr-preview", headers=csrf,
        files={"file": ("ktp.jpg", photo, "image/jpeg")})
    assert preview.status_code == 200, preview.text
    assert preview.json()["fields"]["nik"] == "3273010101900001"

    sent = await client.post("/borrower/v1/kyc", headers=csrf,
        data={"nik": "3273010101900001", "legal_name": "Budi Santoso", "birth_place": "Bandung",
              "birth_date": "1990-01-01", "gender": "male", "address": "Jalan Merdeka Nomor 1",
              "province": "Jawa Barat", "city": "Kota Bandung", "verification_method": "ocr_internal",
              "consent_kyc_processing": "true"},
        files={"file": ("ktp.jpg", photo, "image/jpeg")})
    assert sent.status_code == 201, sent.text
    assert sent.json()["status"] == "pending_review"
    assert sent.json()["can_apply"] is False
    assert "3273010101900001" not in sent.text
    assert (await client.post("/borrower/v1/applications", json=application, headers=csrf)).status_code == 409

    verification = await db_session.scalar(select(KycVerification).where(
        KycVerification.org_id == org.id, KycVerification.borrower_id == borrower_id))
    assert verification is not None and verification.initiated_by_user_id is None
    document = await db_session.scalar(select(KycDocument).where(KycDocument.verification_id == verification.id))
    assert document is not None and document.scan_status == "clean"
    checker = User(email="kyc-checker-borrower@example.com", full_name="KYC Checker")
    db_session.add(checker)
    await db_session.flush()
    await kyc_service.run_ocr_check(db_session, settings, org.id, checker.id, verification.borrower_id, verification.id)
    await kyc_service.review_verification(db_session, org.id, checker.id, verification.borrower_id,
        verification.id, KycReview(decision="verified", reason="KTP dan data identitas sesuai"), settings)
    await db_session.commit()

    status = await client.get("/borrower/v1/kyc")
    assert status.json()["can_apply"] is True
    no_estimate = await client.post("/borrower/v1/applications", json=application, headers=csrf)
    assert no_estimate.status_code == 404  # The KYC gate opened; the supplied estimate does not exist.

    verification.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    assert (await client.get("/borrower/v1/kyc")).json()["status"] == "expired"
    expired = await client.post("/borrower/v1/applications", json=application, headers=csrf)
    assert expired.status_code == 409

    storage_root = Path(__file__).resolve().parents[1] / ".data" / "kyc"
    (storage_root / document.object_key).unlink(missing_ok=True)
