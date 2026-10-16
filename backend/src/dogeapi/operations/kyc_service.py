"""Tenant-scoped customer due diligence workflow."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.file_security import scan_upload
from dogeapi.models import Borrower, DebtorProfile, KycDocument, KycEvent, KycProviderCheck, KycVerification
from dogeapi.operations import kyc_provider
from dogeapi.operations.kyc_schemas import KycCreate, KycReview
from dogeapi.settings import Settings, get_settings


def _fingerprint_nik(settings: Settings, org_id: UUID, nik: str) -> str:
    secret = (settings.PII_ENCRYPTION_KEY or settings.JWT_SECRET_KEY).encode()
    return hmac.new(secret, f"{org_id}:{nik}".encode(), hashlib.sha256).hexdigest()


def _masked_nik(nik: str) -> str:
    return f"{nik[:6]}••••••{nik[-4:]}"


def _fernet(settings: Settings) -> Fernet:
    configured = settings.PII_ENCRYPTION_KEY.strip()
    if configured:
        try:
            return Fernet(configured.encode())
        except ValueError as exc:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "PII encryption key is invalid") from exc
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest())
    return Fernet(derived)


def encrypt_pii(settings: Settings, value: str) -> str:
    """Encrypt a sensitive scalar for database persistence."""
    return _fernet(settings).encrypt(value.encode()).decode()


def decrypt_pii(settings: Settings, value: str) -> str:
    """Decrypt a sensitive scalar only inside an authorized workflow."""
    return _fernet(settings).decrypt(value.encode()).decode()


async def _borrower(session: AsyncSession, org_id: UUID, borrower_id: UUID) -> Borrower:
    item = await session.scalar(select(Borrower).where(Borrower.org_id == org_id, Borrower.id == borrower_id))
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Debitur tidak ditemukan")
    return item


async def create_verification(
    session: AsyncSession, settings: Settings, org_id: UUID, actor_id: UUID, borrower_id: UUID, data: KycCreate
) -> KycVerification:
    borrower = await _borrower(session, org_id, borrower_id)
    fingerprint = _fingerprint_nik(settings, org_id, data.nik)
    duplicate = await session.scalar(
        select(KycVerification).where(
            KycVerification.org_id == org_id,
            KycVerification.nik_fingerprint == fingerprint,
            KycVerification.borrower_id != borrower_id,
            KycVerification.status != "rejected",
        )
    )
    if duplicate is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "NIK sudah terhubung dengan CIF lain di tenant ini")

    item = KycVerification(
        org_id=org_id,
        borrower_id=borrower_id,
        initiated_by_user_id=actor_id,
        nik_fingerprint=fingerprint,
        national_id_ciphertext=encrypt_pii(settings, data.nik),
        national_id_masked=_masked_nik(data.nik),
        legal_name=data.legal_name,
        birth_place=data.birth_place,
        birth_date=data.birth_date,
        gender=data.gender,
        address=data.address,
        province=data.province,
        city=data.city,
        occupation=data.occupation,
        verification_method=data.verification_method,
        provider_name=data.provider_name,
        provider_reference=data.provider_reference,
        status="pending_documents",
    )
    session.add(item)
    await session.flush()
    session.add(
        KycEvent(
            org_id=org_id,
            verification_id=item.id,
            actor_user_id=actor_id,
            event_type="KycInitiated",
            to_status=item.status,
            reason="Data identitas KTP direkam",
        )
    )

    profile = await session.scalar(
        select(DebtorProfile).where(DebtorProfile.org_id == org_id, DebtorProfile.borrower_id == borrower_id)
    )
    if profile is None:
        profile = DebtorProfile(org_id=org_id, borrower_id=borrower_id)
        session.add(profile)
    profile.national_id_masked = item.national_id_masked
    if borrower.full_name.upper() != data.legal_name:
        profile.correction_status = "identity_name_review"
    await session.flush()
    return item


async def store_document(
    session: AsyncSession,
    settings: Settings,
    org_id: UUID,
    actor_id: UUID,
    borrower_id: UUID,
    verification_id: UUID,
    document_side: str,
    file_name: str,
    content_type: str,
    content: bytes,
) -> KycDocument:
    verification = await session.scalar(
        select(KycVerification).where(
            KycVerification.org_id == org_id,
            KycVerification.id == verification_id,
            KycVerification.borrower_id == borrower_id,
        )
    )
    if verification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Verifikasi KYC tidak ditemukan")
    if verification.status in {"verified", "rejected"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Verifikasi yang sudah diputuskan tidak dapat diubah")

    scan_result = await scan_upload(content, content_type, settings)
    digest = hashlib.sha256(content).hexdigest()
    zone = "clean" if scan_result.status == "clean" else "quarantine"
    relative_key = f"{zone}/{org_id}/{borrower_id}/{verification_id}/{secrets.token_hex(16)}.enc"
    storage_root = Path(__file__).resolve().parents[3] / ".data" / "kyc"
    target = (storage_root / relative_key).resolve()
    if storage_root.resolve() not in target.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid KYC document path")
    target.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _fernet(settings).encrypt(content)
    await asyncio.to_thread(target.write_bytes, encrypted)
    item = KycDocument(
        org_id=org_id,
        verification_id=verification.id,
        document_side=document_side,
        file_name=Path(file_name).name,
        object_key=relative_key,
        content_type=content_type,
        size_bytes=len(content),
        sha256=digest,
        scan_status=scan_result.status,
        scanner_engine=scan_result.engine,
        scan_detail=scan_result.detail,
        scanned_at=datetime.now(UTC),
        quarantined_at=datetime.now(UTC) if scan_result.status != "clean" else None,
    )
    session.add(item)
    previous = verification.status
    verification.status = "pending_review" if scan_result.status == "clean" else "needs_information"
    session.add(
        KycEvent(
            org_id=org_id,
            verification_id=verification.id,
            actor_user_id=actor_id,
            event_type="KycDocumentUploaded",
            from_status=previous,
            to_status=verification.status,
            reason=f"{document_side} dienkripsi; {scan_result.engine}: {scan_result.detail}",
        )
    )
    await session.flush()
    return item


async def _verification(
    session: AsyncSession, org_id: UUID, borrower_id: UUID, verification_id: UUID
) -> KycVerification:
    item = await session.scalar(
        select(KycVerification).where(
            KycVerification.org_id == org_id,
            KycVerification.id == verification_id,
            KycVerification.borrower_id == borrower_id,
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Verifikasi KYC tidak ditemukan")
    return item


async def _ktp_document(
    session: AsyncSession, org_id: UUID, verification_id: UUID
) -> KycDocument:
    item = await session.scalar(
        select(KycDocument)
        .where(
            KycDocument.org_id == org_id,
            KycDocument.verification_id == verification_id,
            KycDocument.document_side == "ktp_front",
        )
        .order_by(KycDocument.created_at.desc())
    )
    if item is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Foto sisi depan KTP wajib tersedia")
    if item.scan_status != "clean":
        raise HTTPException(status.HTTP_409_CONFLICT, "Foto KTP belum lulus malware scanning")
    return item


async def _document_bytes(settings: Settings, document: KycDocument) -> bytes:
    storage_root = Path(__file__).resolve().parents[3] / ".data" / "kyc"
    target = (storage_root / document.object_key).resolve()
    if storage_root.resolve() not in target.parents or not target.is_file():
        raise HTTPException(status.HTTP_409_CONFLICT, "Berkas KTP terenkripsi tidak tersedia")
    encrypted = await asyncio.to_thread(target.read_bytes)
    try:
        return _fernet(settings).decrypt(encrypted)
    except Exception as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Berkas KTP tidak dapat didekripsi") from exc


def _normalized(value: object) -> str:
    return "".join(character for character in str(value or "").upper() if character.isalnum())


def _ocr_comparison(verification: KycVerification, nik: str, payload: dict[str, object]) -> dict[str, bool | None]:
    extracted_nik = payload.get("nik")
    extracted_name = payload.get("full_name") or payload.get("nama")
    extracted_birth = payload.get("date_of_birth") or payload.get("tanggal_lahir")
    return {
        "nik": _normalized(extracted_nik) == _normalized(nik) if extracted_nik else None,
        "legal_name": _normalized(extracted_name) == _normalized(verification.legal_name) if extracted_name else None,
        "birth_date": (
            _normalized(extracted_birth)
            in {_normalized(verification.birth_date.isoformat()), _normalized(verification.birth_date.strftime("%d-%m-%Y"))}
            if extracted_birth
            else None
        ),
    }


async def _record_provider_check(
    session: AsyncSession,
    settings: Settings,
    verification: KycVerification,
    actor_id: UUID,
    check_type: str,
    request_fingerprint: str,
    result: kyc_provider.ProviderResult,
    payload: dict[str, object],
) -> KycProviderCheck:
    item = KycProviderCheck(
        org_id=verification.org_id,
        verification_id=verification.id,
        requested_by_user_id=actor_id,
        check_type=check_type,
        provider_name=result.provider_name,
        environment=result.environment,
        status=result.status,
        provider_reference=result.reference,
        request_fingerprint=request_fingerprint,
        response_ciphertext=encrypt_pii(settings, json.dumps(payload, ensure_ascii=False, default=str)),
        internal_verified=result.internal_verified,
        completed_at=datetime.now(UTC),
    )
    session.add(item)
    verification.provider_name = result.provider_name
    verification.provider_reference = result.reference
    session.add(
        KycEvent(
            org_id=verification.org_id,
            verification_id=verification.id,
            actor_user_id=actor_id,
            event_type="KycOcrCompleted" if check_type == "ocr" else "KycIdentityProviderCompleted",
            from_status=verification.status,
            to_status=verification.status,
            reason=(
                f"{result.provider_name}/{result.environment}: {result.status}; "
                f"internal_verified={result.internal_verified}"
            ),
        )
    )
    await session.flush()
    return item


async def run_ocr_check(
    session: AsyncSession,
    settings: Settings,
    org_id: UUID,
    actor_id: UUID,
    borrower_id: UUID,
    verification_id: UUID,
) -> KycProviderCheck:
    verification = await _verification(session, org_id, borrower_id, verification_id)
    document = await _ktp_document(session, org_id, verification.id)
    content = await _document_bytes(settings, document)
    result = await kyc_provider.run_ocr(settings, content, document.content_type, document.file_name)
    nik = decrypt_pii(settings, verification.national_id_ciphertext or "")
    payload = dict(result.payload)
    field_matches = _ocr_comparison(verification, nik, payload)
    payload["field_matches"] = field_matches
    required_matches = (field_matches["nik"], field_matches["legal_name"], field_matches["birth_date"])
    internal_verified = all(value is True for value in required_matches)
    payload["internal_verified"] = internal_verified
    result = kyc_provider.ProviderResult(
        provider_name=result.provider_name,
        environment=result.environment,
        status="matched" if internal_verified else "needs_review",
        reference=result.reference,
        payload=result.payload,
        internal_verified=internal_verified,
    )
    return await _record_provider_check(
        session, settings, verification, actor_id, "ocr", document.sha256, result, payload
    )


async def review_verification(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    borrower_id: UUID,
    verification_id: UUID,
    data: KycReview,
    settings: Settings | None = None,
) -> KycVerification:
    item = await session.scalar(
        select(KycVerification).where(
            KycVerification.org_id == org_id,
            KycVerification.id == verification_id,
            KycVerification.borrower_id == borrower_id,
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Verifikasi KYC tidak ditemukan")
    if item.initiated_by_user_id == actor_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Maker KYC tidak boleh menjadi checker untuk verifikasi yang sama"
        )
    if item.status not in {"pending_review", "needs_information"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Status KYC belum dapat diputuskan")
    if data.decision == "verified":
        document = await session.scalar(
            select(KycDocument).where(
                KycDocument.org_id == org_id,
                KycDocument.verification_id == item.id,
                KycDocument.document_side == "ktp_front",
            )
        )
        if document is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Foto sisi depan KTP wajib tersedia")
        if document.scan_status != "clean":
            raise HTTPException(status.HTTP_409_CONFLICT, "Foto KTP belum lulus malware scanning")
        if data.sanctions_match:
            raise HTTPException(status.HTTP_409_CONFLICT, "Sanctions match memerlukan eskalasi EDD sebelum verifikasi")
        if item.verification_method in {"ocr_internal", "electronic_provider"}:
            provider_check = await session.scalar(
                select(KycProviderCheck)
                .where(
                    KycProviderCheck.org_id == org_id,
                    KycProviderCheck.verification_id == item.id,
                    KycProviderCheck.check_type == "ocr",
                )
                .order_by(KycProviderCheck.completed_at.desc())
            )
            if provider_check is None or provider_check.status != "matched":
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Hasil PaddleOCR yang cocok untuk NIK, nama, dan tanggal lahir wajib tersedia",
                )

    previous = item.status
    item.status = data.decision
    item.risk_level = data.risk_level
    item.face_match_score = data.face_match_score
    item.liveness_score = data.liveness_score
    item.document_authenticity_score = data.document_authenticity_score
    item.pep_match = data.pep_match
    item.sanctions_match = data.sanctions_match
    item.decision_reason = data.reason
    item.reviewed_by_user_id = actor_id
    item.reviewed_at = datetime.now(UTC)
    item.expires_at = datetime.now(UTC) + timedelta(days=365) if data.decision == "verified" else None
    session.add(
        KycEvent(
            org_id=org_id,
            verification_id=item.id,
            actor_user_id=actor_id,
            event_type="KycDecisionRecorded",
            from_status=previous,
            to_status=item.status,
            reason=data.reason,
        )
    )
    await session.flush()
    return item


async def serialize_customer_kyc(
    session: AsyncSession, org_id: UUID, borrower_id: UUID, settings: Settings | None = None
) -> dict[str, object]:
    await _borrower(session, org_id, borrower_id)
    active_settings = settings or get_settings()
    rows = list(
        await session.scalars(
            select(KycVerification)
            .where(KycVerification.org_id == org_id, KycVerification.borrower_id == borrower_id)
            .order_by(KycVerification.created_at.desc())
        )
    )
    result: list[dict[str, object]] = []
    for item in rows:
        documents = list(
            await session.scalars(
                select(KycDocument)
                .where(KycDocument.org_id == org_id, KycDocument.verification_id == item.id)
                .order_by(KycDocument.created_at)
            )
        )
        events = list(
            await session.scalars(
                select(KycEvent)
                .where(KycEvent.org_id == org_id, KycEvent.verification_id == item.id)
                .order_by(KycEvent.occurred_at.desc())
            )
        )
        provider_checks = list(
            await session.scalars(
                select(KycProviderCheck)
                .where(KycProviderCheck.org_id == org_id, KycProviderCheck.verification_id == item.id)
                .order_by(KycProviderCheck.completed_at.desc())
            )
        )
        serialized_checks: list[dict[str, object]] = []
        for check in provider_checks:
            try:
                payload = json.loads(decrypt_pii(active_settings, check.response_ciphertext))
            except Exception:
                payload = {"message": "Hasil provider tidak dapat dibaca"}
            if isinstance(payload, dict) and payload.get("nik"):
                payload["nik"] = _masked_nik(str(payload["nik"]))
            serialized_checks.append(
                {
                    "id": check.id,
                    "check_type": check.check_type,
                    "provider_name": check.provider_name,
                    "environment": check.environment,
                    "status": check.status,
                    "provider_reference": check.provider_reference,
                    "internal_verified": check.internal_verified,
                    "result": payload,
                    "requested_by_user_id": check.requested_by_user_id,
                    "completed_at": check.completed_at,
                }
            )
        result.append(
            {
                "id": item.id,
                "status": item.status,
                "document_type": item.document_type,
                "national_id_masked": item.national_id_masked,
                "legal_name": item.legal_name,
                "birth_place": item.birth_place,
                "birth_date": item.birth_date,
                "gender": item.gender,
                "address": item.address,
                "province": item.province,
                "city": item.city,
                "occupation": item.occupation,
                "verification_method": item.verification_method,
                "provider_name": item.provider_name,
                "provider_reference": item.provider_reference,
                "risk_level": item.risk_level,
                "face_match_score": item.face_match_score,
                "liveness_score": item.liveness_score,
                "document_authenticity_score": item.document_authenticity_score,
                "pep_match": item.pep_match,
                "sanctions_match": item.sanctions_match,
                "decision_reason": item.decision_reason,
                "initiated_by_user_id": item.initiated_by_user_id,
                "reviewed_by_user_id": item.reviewed_by_user_id,
                "created_at": item.created_at,
                "reviewed_at": item.reviewed_at,
                "expires_at": item.expires_at,
                "documents": [
                    {
                        "id": doc.id,
                        "document_side": doc.document_side,
                        "file_name": doc.file_name,
                        "content_type": doc.content_type,
                        "size_bytes": doc.size_bytes,
                        "sha256": doc.sha256,
                        "scan_status": doc.scan_status,
                        "scanner_engine": doc.scanner_engine,
                        "scan_detail": doc.scan_detail,
                        "scanned_at": doc.scanned_at,
                        "created_at": doc.created_at,
                    }
                    for doc in documents
                ],
                "events": [
                    {
                        "id": event.id,
                        "event_type": event.event_type,
                        "from_status": event.from_status,
                        "to_status": event.to_status,
                        "reason": event.reason,
                        "actor_user_id": event.actor_user_id,
                        "occurred_at": event.occurred_at,
                    }
                    for event in events
                ],
                "provider_checks": serialized_checks,
            }
        )
    return {
        "customer_id": borrower_id,
        "current_status": rows[0].status if rows else "not_started",
        "verifications": result,
    }
