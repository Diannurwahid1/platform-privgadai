"""Single-partner borrower portal. Staff credentials are never accepted here."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, Response, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from dogeapi.agreement import service as agreement_service
from dogeapi.auth.passwords import hash_password, verify_password
from dogeapi.deps import SessionDep
from dogeapi.file_security import scan_upload
from dogeapi.models import (
    AiAppraisalEstimate,
    ApplicationStatusHistory,
    Asset,
    AssetCategory,
    Borrower,
    BorrowerAccount,
    BorrowerSession,
    Branch,
    CollateralEvent,
    Consent,
    CustomerAcceptance,
    DebtorProfile,
    EvidenceEvent,
    EvidenceFile,
    HumanAppraisal,
    KycVerification,
    LoanApplication,
    LoanProduct,
    Offer,
    Organization,
    PawnAgreement,
)
from dogeapi.operations import ai_appraisal, kyc_provider, kyc_service, mvp_service
from dogeapi.operations.kyc_schemas import KycCreate
from dogeapi.operations.kyc_service import encrypt_pii
from dogeapi.operations.mvp_schemas import ApplicationCreate, AssetInput, BorrowerInput
from dogeapi.settings import Settings

router = APIRouter(prefix="/borrower/v1", tags=["privgadai-borrower"])
logger = logging.getLogger(__name__)
SESSION_COOKIE = "pg_borrower_session"
CSRF_COOKIE = "pg_borrower_csrf"


class RegisterInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=24)
    password: str = Field(min_length=10, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class SubmitInput(BaseModel):
    estimate_id: UUID
    branch_id: UUID
    product_id: UUID
    requested_amount: Decimal = Field(gt=0)
    requested_tenor_days: int = Field(gt=0)
    purpose: str | None = Field(default=None, max_length=1000)
    consent_document_version: str = Field(min_length=1, max_length=32)


class AcceptOfferInput(BaseModel):
    preview_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consent: bool


@dataclass(frozen=True)
class Principal:
    org: Organization
    account: BorrowerAccount
    borrower: Borrower
    login_session: BorrowerSession


async def _org(session: SessionDep, settings: Settings) -> Organization:
    org = await session.scalar(select(Organization).where(Organization.slug == settings.BORROWER_ORG_SLUG))
    if org is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Portal borrower belum dikonfigurasi")
    return org


async def _principal(request: Request, session: SessionDep) -> Principal:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Silakan masuk sebagai borrower")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = (
        await session.execute(
            select(BorrowerSession, BorrowerAccount, Borrower, Organization)
            .join(BorrowerAccount, BorrowerAccount.id == BorrowerSession.account_id)
            .join(Borrower, Borrower.id == BorrowerAccount.borrower_id)
            .join(Organization, Organization.id == BorrowerAccount.org_id)
            .where(BorrowerSession.token_hash == token_hash, BorrowerSession.revoked_at.is_(None),
                   BorrowerSession.expires_at > datetime.now(UTC),
                   Organization.slug == request.app.state.settings.BORROWER_ORG_SLUG,
                   Borrower.org_id == BorrowerAccount.org_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesi borrower sudah berakhir")
    login_session, account, borrower, org = row
    return Principal(org, account, borrower, login_session)


async def _csrf(
    request: Request, principal: Annotated[Principal, Depends(_principal)],
    x_borrower_csrf: Annotated[str | None, Header()] = None,
) -> Principal:
    cookie = request.cookies.get(CSRF_COOKIE)
    if not cookie or not x_borrower_csrf or not secrets.compare_digest(cookie, x_borrower_csrf):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token keamanan tidak cocok")
    if not secrets.compare_digest(hashlib.sha256(cookie.encode()).hexdigest(), principal.login_session.csrf_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token keamanan tidak berlaku")
    return principal


def _set_session(response: Response, settings: Settings, login_session: BorrowerSession,
                 token: str, csrf: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, max_age=7 * 86400, httponly=True,
                        secure=settings.JWT_COOKIE_SECURE, samesite="lax", path="/")
    response.set_cookie(CSRF_COOKIE, csrf, max_age=7 * 86400, httponly=False,
                        secure=settings.JWT_COOKIE_SECURE, samesite="lax", path="/")


async def _start_session(session: SessionDep, response: Response, settings: Settings,
                         account: BorrowerAccount) -> None:
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(36)
    login_session = BorrowerSession(account_id=account.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        csrf_hash=hashlib.sha256(csrf.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=7))
    session.add(login_session)
    await session.flush()
    _set_session(response, settings, login_session, token, csrf)


def _me(principal: Principal) -> dict[str, object]:
    return {"id": principal.borrower.id, "full_name": principal.borrower.full_name,
            "email": principal.account.email, "phone_masked": principal.borrower.phone_masked,
            "partner": {"name": principal.org.name, "slug": principal.org.slug}}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterInput, response: Response, request: Request, session: SessionDep) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    org = await _org(session, settings)
    email = data.email.strip().lower()
    if await session.scalar(select(BorrowerAccount.id).where(BorrowerAccount.org_id == org.id,
                                                              BorrowerAccount.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email sudah terdaftar")
    borrower = Borrower(org_id=org.id, customer_reference=f"CUS-{secrets.token_hex(8).upper()}",
                        full_name=data.full_name.strip(), phone_masked=mvp_service._mask_phone(data.phone))
    session.add(borrower)
    await session.flush()
    session.add(DebtorProfile(org_id=org.id, borrower_id=borrower.id))
    account = BorrowerAccount(org_id=org.id, borrower_id=borrower.id, email=email,
                              phone_ciphertext=encrypt_pii(settings, data.phone),
                              password_hash=hash_password(data.password))
    session.add(account)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email sudah terdaftar") from exc
    await _start_session(session, response, settings, account)
    await session.commit()
    return {"id": borrower.id, "full_name": borrower.full_name, "email": email,
            "partner": {"name": org.name, "slug": org.slug}}


@router.post("/login")
async def login(data: LoginInput, response: Response, request: Request, session: SessionDep) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    org = await _org(session, settings)
    account = await session.scalar(select(BorrowerAccount).where(
        BorrowerAccount.org_id == org.id, BorrowerAccount.email == data.email.strip().lower()))
    if account is None or not verify_password(data.password, account.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email atau kata sandi tidak cocok")
    borrower = await session.get(Borrower, account.borrower_id)
    await _start_session(session, response, settings, account)
    await session.commit()
    return {"id": borrower.id, "full_name": borrower.full_name, "email": account.email,
            "partner": {"name": org.name, "slug": org.slug}}


@router.post("/logout")
async def logout(response: Response, principal: Annotated[Principal, Depends(_csrf)], session: SessionDep) -> dict[str, str]:
    principal.login_session.revoked_at = datetime.now(UTC)
    await session.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"status": "signed_out"}


@router.get("/me")
async def me(principal: Annotated[Principal, Depends(_principal)]) -> dict[str, object]:
    return _me(principal)


@router.get("/config")
async def config(principal: Annotated[Principal, Depends(_principal)], session: SessionDep) -> dict[str, object]:
    org_id = principal.org.id
    branches = list(await session.scalars(select(Branch).where(Branch.org_id == org_id, Branch.is_active).order_by(Branch.code)))
    products = list(await session.scalars(select(LoanProduct).where(LoanProduct.org_id == org_id, LoanProduct.is_active).order_by(LoanProduct.code)))
    categories = list(await session.scalars(select(AssetCategory).where(AssetCategory.org_id == org_id, AssetCategory.is_active).order_by(AssetCategory.code)))
    return {"partner": {"name": principal.org.name}, "branches": [
        {"id": b.id, "code": b.code, "name": b.name, "city": b.city} for b in branches],
        "products": [{"id": p.id, "name": p.name, "min_amount": p.min_amount,
                      "max_amount": p.max_amount, "allowed_tenors_days": p.allowed_tenors_days,
                      "max_ltv_percent": p.max_ltv_percent, "service_fee_percent": p.service_fee_percent} for p in products],
        "categories": [{"code": c.code, "name": c.name} for c in categories],
        "consent_version": "PRIV-2026.1"}


async def _latest_kyc(session: SessionDep, principal: Principal) -> KycVerification | None:
    return await session.scalar(select(KycVerification).where(
        KycVerification.org_id == principal.org.id,
        KycVerification.borrower_id == principal.borrower.id,
    ).order_by(KycVerification.created_at.desc(), KycVerification.id.desc()))


def _borrower_kyc_status(item: KycVerification | None) -> dict[str, object]:
    effective = item.status if item else "not_started"
    if item and item.status == "verified" and item.expires_at and item.expires_at <= datetime.now(UTC):
        effective = "expired"
    return {
        "id": item.id if item else None,
        "status": effective,
        "can_apply": effective == "verified",
        "national_id_masked": item.national_id_masked if item else None,
        "legal_name": item.legal_name if item else None,
        "verification_method": item.verification_method if item else None,
        "decision_reason": item.decision_reason if item else None,
        "created_at": item.created_at if item else None,
        "expires_at": item.expires_at if item else None,
    }


@router.get("/kyc")
async def borrower_kyc(principal: Annotated[Principal, Depends(_principal)], session: SessionDep) -> dict[str, object]:
    return _borrower_kyc_status(await _latest_kyc(session, principal))


@router.post("/kyc/ocr-preview")
async def borrower_ktp_preview(request: Request, principal: Annotated[Principal, Depends(_csrf)],
                               file: Annotated[UploadFile, File()]) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    if settings.KYC_OCR_PROVIDER == "disabled":
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "OCR KTP belum aktif; lengkapi data secara manual")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Foto KTP harus JPG, PNG, atau WebP")
    content = await file.read(10 * 1024 * 1024 + 1)
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Foto KTP wajib tersedia dan maksimal 10 MB")
    scan = await scan_upload(content, file.content_type, settings)
    if scan.status != "clean":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Foto KTP gagal pemeriksaan keamanan")
    result = await kyc_provider.run_ocr(settings, content, file.content_type, file.filename or "ktp.jpg")
    return {"fields": kyc_provider.normalize_ocr_autofill(result.payload),
            "message": "Data KTP terbaca. Periksa dan koreksi sebelum mengirim untuk verifikasi petugas."}


@router.post("/kyc", status_code=status.HTTP_201_CREATED)
async def borrower_submit_kyc(request: Request, principal: Annotated[Principal, Depends(_csrf)],
                              session: SessionDep, file: Annotated[UploadFile, File()],
                              nik: Annotated[str, Form()], legal_name: Annotated[str, Form()],
                              birth_place: Annotated[str, Form()], birth_date: Annotated[date, Form()],
                              gender: Annotated[str, Form()], address: Annotated[str, Form()],
                              province: Annotated[str, Form()], city: Annotated[str, Form()],
                              consent_kyc_processing: Annotated[bool, Form()],
                              occupation: Annotated[str | None, Form()] = None,
                              verification_method: Annotated[str, Form()] = "ocr_internal") -> dict[str, object]:
    if not consent_kyc_processing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Persetujuan pemrosesan KTP diperlukan")
    settings: Settings = request.app.state.settings
    if verification_method not in {"ocr_internal", "manual_branch"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Metode verifikasi tidak tersedia")
    if verification_method == "ocr_internal" and settings.KYC_OCR_PROVIDER == "disabled":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "OCR tidak aktif; pilih pemeriksaan manual")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Foto KTP harus JPG, PNG, atau WebP")
    content = await file.read(10 * 1024 * 1024 + 1)
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Foto KTP wajib tersedia dan maksimal 10 MB")
    try:
        data = KycCreate(nik=nik, legal_name=legal_name, birth_place=birth_place, birth_date=birth_date,
            gender=gender, address=address, province=province, city=city,
            occupation=occupation, verification_method=verification_method)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Data identitas belum lengkap atau tidak sesuai") from exc
    # Lock this borrower so concurrent uploads cannot create competing active reviews.
    await session.scalar(select(Borrower).where(Borrower.org_id == principal.org.id,
        Borrower.id == principal.borrower.id).with_for_update())
    previous = await _latest_kyc(session, principal)
    if previous and _borrower_kyc_status(previous)["status"] in {"verified", "pending_review"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "KYC sudah terverifikasi atau sedang diperiksa petugas")
    item = await kyc_service.create_verification(session, settings, principal.org.id, None,
                                                 principal.borrower.id, data)
    await kyc_service.store_document(session, settings, principal.org.id, None, principal.borrower.id,
                                     item.id, "ktp_front", file.filename or "ktp.jpg",
                                     file.content_type, content)
    session.add(Consent(org_id=principal.org.id, borrower_id=principal.borrower.id,
        consent_type="ktp_kyc_processing", document_version="KYC-2026.1", channel="borrower_web"))
    await session.commit()
    return _borrower_kyc_status(item)


@router.post("/estimates", status_code=status.HTTP_201_CREATED)
async def estimate(request: Request, session: SessionDep, principal: Annotated[Principal, Depends(_csrf)],
                   category_code: Annotated[str, Form()], condition_grade: Annotated[str, Form()],
                   photo: Annotated[UploadFile, File()],
                   share_photo_with_ai: Annotated[bool, Form()] = False,
                   brand: Annotated[str | None, Form()] = None,
                   model: Annotated[str | None, Form()] = None,
                   asset_description: Annotated[str | None, Form(max_length=1000)] = None) -> dict[str, object]:
    if not share_photo_with_ai:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Persetujuan analisis foto diperlukan")
    if condition_grade.upper() not in {"A", "B", "C", "D"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Kondisi harus A, B, C, atau D")
    category = await session.scalar(select(AssetCategory).where(AssetCategory.org_id == principal.org.id,
                              AssetCategory.code == category_code, AssetCategory.is_active))
    if category is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Kategori tidak tersedia")
    if photo.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Gunakan foto JPEG, PNG, atau WebP")
    content = await photo.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Foto maksimal 5 MB")
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Foto wajib diunggah")
    item = await ai_appraisal.create_estimate(session, request.app.state.settings, principal.org.id,
        principal.borrower.id, category_code, brand, model, condition_grade.upper(),
        photo.filename or "barang.jpg", photo.content_type, content,
        asset_description=asset_description.strip() or None if asset_description else None)
    session.add(Consent(org_id=principal.org.id, borrower_id=principal.borrower.id,
        consent_type="asset_photo_ai_processing", document_version="AI-VISION-2026.1", channel="web"))
    await session.commit()
    return ai_appraisal.public_estimate(item)


@router.post("/estimates/stream")
async def estimate_stream(request: Request, session: SessionDep,
                          principal: Annotated[Principal, Depends(_csrf)],
                          category_code: Annotated[str, Form()], condition_grade: Annotated[str, Form()],
                          photo: Annotated[UploadFile, File()],
                          share_photo_with_ai: Annotated[bool, Form()] = False,
                          brand: Annotated[str | None, Form()] = None,
                          model: Annotated[str | None, Form()] = None,
                          asset_description: Annotated[str | None, Form(max_length=1000)] = None) -> StreamingResponse:
    if not share_photo_with_ai:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Persetujuan analisis foto diperlukan")
    if condition_grade.upper() not in {"A", "B", "C", "D"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Kondisi harus A, B, C, atau D")
    category = await session.scalar(select(AssetCategory).where(
        AssetCategory.org_id == principal.org.id, AssetCategory.code == category_code, AssetCategory.is_active))
    if category is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Kategori tidak tersedia")
    if photo.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Gunakan foto JPEG, PNG, atau WebP")
    content = await photo.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Foto maksimal 5 MB")
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Foto wajib diunggah")

    async def events():
        queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

        async def progress(stage: str, message: str) -> None:
            await queue.put({"type": "stage", "stage": stage, "message": message})

        async def work() -> None:
            try:
                item = await ai_appraisal.create_estimate(
                    session, request.app.state.settings, principal.org.id, principal.borrower.id,
                    category_code, brand, model, condition_grade.upper(),
                    photo.filename or "barang.jpg", photo.content_type or "image/jpeg", content,
                    asset_description=asset_description.strip() or None if asset_description else None,
                    on_progress=progress,
                )
                session.add(Consent(org_id=principal.org.id, borrower_id=principal.borrower.id,
                    consent_type="asset_photo_ai_processing", document_version="AI-VISION-2026.1", channel="web"))
                await session.commit()
                await queue.put({"type": "complete", "estimate": ai_appraisal.public_estimate(item)})
            except HTTPException as exc:
                await session.rollback()
                await queue.put({"type": "error", "message": str(exc.detail)})
            except Exception:
                await session.rollback()
                logger.exception("Borrower appraisal stream failed")
                await queue.put({"type": "error", "message": "Analisis belum berhasil. Silakan coba lagi."})
            finally:
                await queue.put(None)

        yield json.dumps({"type": "stage", "stage": "received", "message": "Foto diterima, memulai analisis"}, ensure_ascii=False) + "\n"
        task = asyncio.create_task(work())
        try:
            while (event := await queue.get()) is not None:
                yield json.dumps(jsonable_encoder(event), ensure_ascii=False) + "\n"
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    return StreamingResponse(events(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.post("/applications", status_code=status.HTTP_201_CREATED)
async def submit_application(data: SubmitInput, principal: Annotated[Principal, Depends(_csrf)],
                             session: SessionDep) -> dict[str, object]:
    kyc = await _latest_kyc(session, principal)
    if not _borrower_kyc_status(kyc)["can_apply"]:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "KYC KTP harus terverifikasi dan masih berlaku sebelum pengajuan dikirim")
    item = await session.scalar(select(AiAppraisalEstimate).where(
        AiAppraisalEstimate.org_id == principal.org.id, AiAppraisalEstimate.id == data.estimate_id,
        AiAppraisalEstimate.borrower_id == principal.borrower.id).with_for_update())
    if item is None or item.application_id is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estimasi tidak tersedia")
    if item.created_at < datetime.now(UTC) - timedelta(days=1):
        raise HTTPException(status.HTTP_409_CONFLICT, "Estimasi kedaluwarsa; unggah foto baru")
    midpoint = (item.low_value + item.high_value) / 2 if item.low_value and item.high_value else None
    payload = ApplicationCreate(branch_id=data.branch_id, product_id=data.product_id,
        borrower=BorrowerInput(full_name=principal.borrower.full_name, phone=principal.borrower.phone_masked),
        asset=AssetInput(category_code=item.category_code, brand=item.brand, model=item.model,
                         condition_grade=item.condition_grade, indicative_value=midpoint),
        requested_amount=data.requested_amount, requested_tenor_days=data.requested_tenor_days,
        purpose=data.purpose, consent_document_version=data.consent_document_version, submit=True)
    application = await mvp_service.create_application(session, principal.org.id, None, payload,
                                                       borrower_id=principal.borrower.id)
    item.application_id = application.id
    photo_path = Path(__file__).resolve().parents[3] / ".data" / "evidence" / item.photo_key
    evidence = EvidenceFile(org_id=principal.org.id, application_id=application.id, evidence_type="asset_photo",
        file_name=item.photo_file_name, object_key=item.photo_key, content_type=item.photo_content_type,
        size_bytes=photo_path.stat().st_size, sha256=item.photo_sha256, scan_status="clean",
        subject_type="application", subject_id=application.id, scanner_engine="upload-validation",
        scanned_at=datetime.now(UTC))
    session.add(evidence)
    await session.flush()
    session.add_all([
        EvidenceEvent(org_id=principal.org.id, evidence_file_id=evidence.id, event_type="uploaded",
                      to_status="clean", detail="Borrower mengunggah foto barang untuk pengajuan"),
        CollateralEvent(org_id=principal.org.id, application_id=application.id, actor_user_id=None,
            event_type="ai_estimate", title="Estimasi awal dari foto",
            description=item.explanation, event_metadata={"estimate_id": str(item.id),
                "status": item.status, "low_value": str(item.low_value) if item.low_value else None,
                "high_value": str(item.high_value) if item.high_value else None,
                "model": item.model_name, "estimator_version": item.estimator_version}),
    ])
    await session.commit()
    return {"id": application.id, "application_no": application.application_no,
            "status": application.status, "message": "Pengajuan masuk ke tim penaksiran"}


async def _owned_application(session: SessionDep, principal: Principal, application_id: UUID) -> LoanApplication:
    item = await session.scalar(select(LoanApplication).where(LoanApplication.id == application_id,
       LoanApplication.org_id == principal.org.id, LoanApplication.borrower_id == principal.borrower.id))
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pengajuan tidak ditemukan")
    return item


@router.get("/applications")
async def applications(principal: Annotated[Principal, Depends(_principal)], session: SessionDep) -> list[dict[str, object]]:
    rows = list(await session.scalars(select(LoanApplication).where(
        LoanApplication.org_id == principal.org.id, LoanApplication.borrower_id == principal.borrower.id)
        .order_by(LoanApplication.created_at.desc())))
    return [{"id": row.id, "application_no": row.application_no, "status": row.status,
             "requested_amount": row.requested_amount, "requested_tenor_days": row.requested_tenor_days,
             "created_at": row.created_at} for row in rows]


@router.get("/applications/{application_id}")
async def application_detail(application_id: UUID, principal: Annotated[Principal, Depends(_principal)],
                             session: SessionDep) -> dict[str, object]:
    app = await _owned_application(session, principal, application_id)
    estimate = await session.scalar(select(AiAppraisalEstimate).where(
        AiAppraisalEstimate.org_id == principal.org.id, AiAppraisalEstimate.application_id == app.id))
    asset = await session.scalar(select(Asset).where(Asset.org_id == principal.org.id, Asset.application_id == app.id))
    appraisals = list(await session.scalars(select(HumanAppraisal).where(
        HumanAppraisal.org_id == principal.org.id, HumanAppraisal.application_id == app.id)
        .order_by(HumanAppraisal.revision.desc())))
    offers = list(await session.scalars(select(Offer).where(Offer.org_id == principal.org.id,
        Offer.application_id == app.id).order_by(Offer.version.desc())))
    history = list(await session.scalars(select(ApplicationStatusHistory).where(
        ApplicationStatusHistory.org_id == principal.org.id,
        ApplicationStatusHistory.application_id == app.id).order_by(ApplicationStatusHistory.created_at)))
    kyc = await session.scalar(select(KycVerification).where(
        KycVerification.org_id == principal.org.id,
        KycVerification.borrower_id == principal.borrower.id
    ).order_by(KycVerification.created_at.desc()))
    return {"id": app.id, "application_no": app.application_no, "status": app.status,
        "kyc_status": _borrower_kyc_status(kyc)["status"],
        "requested_amount": app.requested_amount, "requested_tenor_days": app.requested_tenor_days,
        "purpose": app.purpose, "created_at": app.created_at,
        "asset": {"category": asset.category, "brand": asset.brand, "model": asset.model,
                  "condition_grade": asset.condition_grade} if asset else None,
        "estimate": ai_appraisal.public_estimate(estimate) if estimate else None,
        "appraisal": {"market_value": appraisals[0].market_value,
                       "liquidation_value": appraisals[0].liquidation_value,
                       "recommended_loan": appraisals[0].recommended_loan,
                       "rationale": appraisals[0].rationale,
                       "status": appraisals[0].status} if appraisals else None,
        "offer": {"id": offers[0].id, "principal_amount": offers[0].principal_amount,
                  "tenor_days": offers[0].tenor_days, "service_fee_amount": offers[0].service_fee_amount,
                  "total_due_amount": offers[0].total_due_amount, "decision_reason": offers[0].decision_reason,
                  "agreement_version": offers[0].agreement_version, "expires_at": offers[0].expires_at,
                  "status": offers[0].status} if offers else None,
        "history": [{"status": h.to_status, "note": h.note, "at": h.created_at} for h in history]}


@router.get("/applications/{application_id}/photo")
async def application_photo(application_id: UUID, principal: Annotated[Principal, Depends(_principal)],
                            session: SessionDep) -> FileResponse:
    await _owned_application(session, principal, application_id)
    item = await session.scalar(select(AiAppraisalEstimate).where(
        AiAppraisalEstimate.org_id == principal.org.id, AiAppraisalEstimate.application_id == application_id))
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto tidak ditemukan")
    root = (Path(__file__).resolve().parents[3] / ".data" / "evidence").resolve()
    path = (root / item.photo_key).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto tidak ditemukan")
    return FileResponse(path, media_type=item.photo_content_type, headers={"Cache-Control": "private, no-store"})


@router.get("/applications/{application_id}/agreement-preview")
async def agreement_preview(application_id: UUID, principal: Annotated[Principal, Depends(_principal)],
                            session: SessionDep) -> dict[str, object]:
    app = await _owned_application(session, principal, application_id)
    offer = await session.scalar(select(Offer).where(
        Offer.org_id == principal.org.id, Offer.application_id == app.id, Offer.status == "offered",
    ).order_by(Offer.version.desc()))
    if offer is None or offer.expires_at <= datetime.now(UTC):
        raise HTTPException(status.HTTP_409_CONFLICT, "Tidak ada penawaran aktif")
    try:
        snapshot = await agreement_service.document_snapshot(session, principal.org, principal.borrower, app, offer)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return {"document": snapshot, "preview_sha256": agreement_service.preview_digest(snapshot)}


@router.get("/applications/{application_id}/agreement")
async def agreement_record(application_id: UUID, principal: Annotated[Principal, Depends(_principal)],
                           session: SessionDep) -> dict[str, object]:
    await _owned_application(session, principal, application_id)
    agreement = await session.scalar(select(PawnAgreement).where(
        PawnAgreement.org_id == principal.org.id, PawnAgreement.application_id == application_id,
    ))
    if agreement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perjanjian belum tersedia")
    return agreement_service.public_record(agreement, include_snapshot=True)


@router.get("/applications/{application_id}/agreement/verify")
async def verify_agreement(application_id: UUID, principal: Annotated[Principal, Depends(_principal)],
                           session: SessionDep) -> dict[str, object]:
    await _owned_application(session, principal, application_id)
    agreement = await session.scalar(select(PawnAgreement).where(
        PawnAgreement.org_id == principal.org.id, PawnAgreement.application_id == application_id,
    ))
    if agreement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perjanjian belum tersedia")
    return {**agreement_service.public_record(agreement), **await agreement_service.verify(agreement)}


@router.post("/applications/{application_id}/accept-offer")
async def accept_offer(application_id: UUID, data: AcceptOfferInput, request: Request,
                       principal: Annotated[Principal, Depends(_csrf)], session: SessionDep) -> dict[str, str]:
    if not data.consent:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Persetujuan dokumen wajib diberikan")
    if _borrower_kyc_status(await _latest_kyc(session, principal))["status"] != "verified":
        raise HTTPException(status.HTTP_409_CONFLICT, "KYC harus terverifikasi sebelum menerima penawaran")
    app = await _owned_application(session, principal, application_id)
    offer = await session.scalar(select(Offer).where(Offer.org_id == principal.org.id,
        Offer.application_id == app.id, Offer.status == "offered").order_by(Offer.version.desc()))
    if offer is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Belum ada penawaran aktif")
    try:
        snapshot = await agreement_service.document_snapshot(session, principal.org, principal.borrower, app, offer)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if not secrets.compare_digest(data.preview_sha256, agreement_service.preview_digest(snapshot)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Isi penawaran berubah. Buka dan tinjau lagi dokumennya")
    await mvp_service.accept_offer(session, principal.org.id, None, offer.id, "web",
        request.client.host if request.client else None, borrower_id=principal.borrower.id)
    current_snapshot = await agreement_service.document_snapshot(session, principal.org, principal.borrower, app, offer)
    if not secrets.compare_digest(data.preview_sha256, agreement_service.preview_digest(current_snapshot)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Isi penawaran berubah saat persetujuan. Ulangi tinjauan")
    agreement = await session.scalar(select(PawnAgreement).where(
        PawnAgreement.org_id == principal.org.id, PawnAgreement.application_id == app.id,
    ))
    acceptance = await session.scalar(select(CustomerAcceptance).where(
        CustomerAcceptance.org_id == principal.org.id, CustomerAcceptance.offer_id == offer.id,
    ))
    if agreement is None or acceptance is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Bukti persetujuan gagal dibuat")
    await agreement_service.capture_acceptance(
        session, agreement, acceptance, current_snapshot,
        session_id=principal.login_session.id, user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return {"status": "accepted", "message": "Penawaran diterima"}
