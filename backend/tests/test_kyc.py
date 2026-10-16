"""Customer KYC control and tenant isolation coverage."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import Borrower, User
from dogeapi.operations import kyc_provider, kyc_service
from dogeapi.operations.kyc_schemas import KycCreate, KycReview
from dogeapi.settings import Settings

pytestmark = pytest.mark.integration


async def test_ktp_kyc_masks_nik_encrypts_document_and_enforces_checker(
    client: AsyncClient, db_session: AsyncSession, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    registered = await client.post(
        "/auth/register",
        json={"email": "kyc-maker@example.com", "password": "correct horse battery staple", "full_name": "KYC Maker"},
    )
    base_headers = {"Authorization": f"Bearer {registered.json()['tokens']['access_token']}"}
    created = await client.post("/orgs", json={"name": "Mitra KYC", "slug": "mitra-kyc"}, headers=base_headers)
    org_id = UUID(created.json()["id"])
    maker = await db_session.scalar(select(User).where(User.email == "kyc-maker@example.com"))
    assert maker is not None
    checker = User(email="kyc-checker@example.com", full_name="KYC Checker")
    borrower = Borrower(
        org_id=org_id, customer_reference="CIF-KYC-001", full_name="BUDI SANTOSO", phone_masked="0812••••1234"
    )
    db_session.add_all([checker, borrower])
    await db_session.flush()

    verification = await kyc_service.create_verification(
        db_session,
        settings,
        org_id,
        maker.id,
        borrower.id,
        KycCreate(
            nik="3273010101900001",
            legal_name="Budi Santoso",
            birth_place="Bandung",
            birth_date=date(1990, 1, 1),
            gender="male",
            address="Jalan Merdeka Nomor 1",
            province="Jawa Barat",
            city="Kota Bandung",
            occupation="Wiraswasta",
        ),
    )
    assert verification.national_id_masked == "327301••••••0001"
    assert "3273010101900001" not in verification.nik_fingerprint
    assert verification.national_id_ciphertext is not None
    assert "3273010101900001" not in verification.national_id_ciphertext
    assert kyc_service.decrypt_pii(settings, verification.national_id_ciphertext) == "3273010101900001"

    document = await kyc_service.store_document(
        db_session,
        settings,
        verification.org_id,
        maker.id,
        borrower.id,
        verification.id,
        "ktp_front",
        "ktp.jpg",
        "image/jpeg",
        b"\xff\xd8\xffsynthetic-image-content\xff\xd9",
    )
    assert document.object_key.endswith(".enc")
    assert document.sha256 != "synthetic-image-content"
    assert document.scan_status == "clean"
    assert document.scanner_engine == "content-guard-v1"

    async def fake_ocr(
        _settings: Settings, _content: bytes, _content_type: str, _file_name: str
    ) -> kyc_provider.ProviderResult:
        return kyc_provider.ProviderResult(
            provider_name="paddleocr",
            environment="internal",
            status="completed",
            reference="ocr-test-001",
            payload={
                "nik": "3273010101900001",
                "nama": "BUDI SANTOSO",
                "tanggal_lahir": "01-01-1990",
                "confidence": 0.98,
            },
        )

    monkeypatch.setattr(kyc_provider, "run_ocr", fake_ocr)
    provider_check = await kyc_service.run_ocr_check(
        db_session, settings, verification.org_id, maker.id, borrower.id, verification.id
    )
    assert provider_check.internal_verified is True
    assert provider_check.status == "matched"
    assert "3273010101900001" not in provider_check.response_ciphertext
    serialized = await kyc_service.serialize_customer_kyc(
        db_session, verification.org_id, borrower.id, settings
    )
    provider_result = serialized["verifications"][0]["provider_checks"][0]  # type: ignore[index]
    assert provider_result["result"]["nik"] == "327301••••••0001"  # type: ignore[index]
    assert provider_result["result"]["field_matches"] == {  # type: ignore[index]
        "nik": True,
        "legal_name": True,
        "birth_date": True,
    }

    with pytest.raises(Exception) as maker_error:
        await kyc_service.review_verification(
            db_session,
            verification.org_id,
            maker.id,
            borrower.id,
            verification.id,
            KycReview(decision="verified", reason="Data dan foto identitas sesuai", risk_level="standard"),
        )
    assert "Maker KYC" in str(maker_error.value)

    reviewed = await kyc_service.review_verification(
        db_session,
        verification.org_id,
        checker.id,
        borrower.id,
        verification.id,
        KycReview(decision="verified", reason="Data dan foto identitas sesuai", risk_level="standard"),
    )
    assert reviewed.status == "verified"
    assert reviewed.reviewed_by_user_id == checker.id

    switched = await client.post("/orgs/mitra-kyc/switch", headers=base_headers)
    scoped = {"Authorization": f"Bearer {switched.json()['access_token']}"}
    queue = await client.get("/v1/kyc/verifications", headers=scoped)
    assert queue.status_code == 200, queue.text
    assert queue.json()[0]["national_id_masked"] == "327301••••••0001"
    detail = await client.get(f"/v1/customers/{borrower.id}/kyc", headers=scoped)
    assert detail.status_code == 200, detail.text
    assert detail.json()["current_status"] == "verified"
