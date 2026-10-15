"""Customer KYC control and tenant isolation coverage."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import Borrower, User
from dogeapi.operations import kyc_service
from dogeapi.operations.kyc_schemas import KycCreate, KycReview
from dogeapi.settings import Settings

pytestmark = pytest.mark.integration


async def test_ktp_kyc_masks_nik_encrypts_document_and_enforces_checker(
    client: AsyncClient, db_session: AsyncSession, settings: Settings
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
        b"synthetic-image-content",
    )
    assert document.object_key.endswith(".enc")
    assert document.sha256 != "synthetic-image-content"

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
