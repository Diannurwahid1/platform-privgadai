"""Freeze the exact terms shown to a borrower and verify their commitments."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
from datetime import UTC
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from dogeapi.models import (
    Asset,
    Borrower,
    Branch,
    CustomerAcceptance,
    HumanAppraisal,
    LoanApplication,
    LoanProduct,
    Offer,
    Organization,
    PawnAgreement,
)
from dogeapi.proof.service import canonical_bytes, make_digest
from dogeapi.settings import get_settings

AGREEMENT_ABI = [
    {"type": "function", "name": "recordVersion", "stateMutability": "nonpayable", "inputs": [
        {"name": "agreementId", "type": "bytes32"}, {"name": "version", "type": "uint32"},
        {"name": "documentDigest", "type": "bytes32"}, {"name": "consentDigest", "type": "bytes32"},
    ], "outputs": []},
    {"type": "function", "name": "commitmentOf", "stateMutability": "view", "inputs": [
        {"name": "agreementId", "type": "bytes32"}, {"name": "version", "type": "uint32"},
    ], "outputs": [{"components": [
        {"name": "documentDigest", "type": "bytes32"},
        {"name": "consentDigest", "type": "bytes32"},
        {"name": "recordedAt", "type": "uint64"},
    ], "name": "", "type": "tuple"}]},
]


def amount(value: object) -> str:
    return f"{value:.2f}"


def agreement_number(application: LoanApplication, offer: Offer) -> str:
    return f"SBG-{application.id.hex[:16].upper()}-{offer.version}"


async def document_snapshot(
    session: AsyncSession, org: Organization, borrower: Borrower, application: LoanApplication, offer: Offer,
) -> dict[str, object]:
    """Produce canonical, human-readable offer terms; no mutable DB references in the result."""
    asset = await session.scalar(select(Asset).where(Asset.org_id == org.id, Asset.application_id == application.id))
    branch = await session.scalar(select(Branch).where(Branch.org_id == org.id, Branch.id == application.branch_id))
    product = await session.scalar(select(LoanProduct).where(LoanProduct.org_id == org.id, LoanProduct.id == application.product_id))
    appraisal = await session.scalar(select(HumanAppraisal).where(
        HumanAppraisal.org_id == org.id, HumanAppraisal.application_id == application.id,
        HumanAppraisal.status == "final",
    ).order_by(HumanAppraisal.revision.desc()))
    if asset is None or branch is None or product is None or appraisal is None:
        raise ValueError("Data barang, cabang, produk, dan appraisal final wajib lengkap")
    return {
        "schema": "privgadai.offer-agreement.v1",
        "document_number": agreement_number(application, offer),
        "document_version": offer.agreement_version,
        "offer_version": offer.version,
        "offer_id": str(offer.id),
        "application_number": application.application_no,
        "issued_at": offer.created_at.isoformat(),
        "expires_at": offer.expires_at.isoformat(),
        "company": {"name": org.name, "branch": branch.name, "branch_address": branch.address or "", "branch_city": branch.city},
        "borrower": {"name": borrower.full_name, "customer_reference": borrower.customer_reference},
        "collateral": {"asset_code": asset.asset_code, "category": asset.category, "brand": asset.brand or "", "model": asset.model or "", "condition_grade": asset.condition_grade or ""},
        "valuation": {"market_value_idr": amount(appraisal.market_value), "liquidation_value_idr": amount(appraisal.liquidation_value)},
        "terms": {
            "principal_idr": amount(offer.principal_amount),
            "tenor_days": offer.tenor_days,
            "service_fee_idr": amount(offer.service_fee_amount),
            "total_due_idr": amount(offer.total_due_amount),
            "requested_principal_idr": amount(application.requested_amount),
            "requested_tenor_days": application.requested_tenor_days,
            "decision_reason": offer.decision_reason or "Sesuai permintaan dan appraisal final",
            "tenor_start": "Tanggal pencairan yang tercatat dalam sistem; jatuh tempo dihitung dari tanggal tersebut.",
            "disbursement": "Pencairan hanya dilakukan setelah verifikasi akhir dan serah terima barang jaminan.",
            "late_fee": "Tidak ada denda keterlambatan yang disetujui melalui ringkasan penawaran ini. Ketentuan tambahan memerlukan perjanjian tertulis tersendiri.",
            "default_and_collateral": "Penanganan wanprestasi dan eksekusi agunan mengikuti perjanjian tertulis final, SOP, dan hukum yang berlaku; tidak dilakukan otomatis oleh smart contract.",
            "dispute": "Ajukan keberatan melalui kanal pengaduan perusahaan. Penyelesaian selanjutnya mengikuti perjanjian tertulis final dan hukum Indonesia.",
        },
        "notice": "Ringkasan syarat penawaran yang disetujui di portal. Surat Bukti Gadai final dan tanda tangan elektronik tersertifikasi memerlukan proses dokumen tersendiri.",
    }


def preview_digest(snapshot: dict[str, object]) -> str:
    return hashlib.sha256(canonical_bytes(snapshot)).hexdigest()


async def capture_acceptance(
    session: AsyncSession, agreement: PawnAgreement, acceptance: CustomerAcceptance,
    snapshot: dict[str, object], *, session_id: UUID, user_agent: str | None,
) -> PawnAgreement:
    settings = get_settings()
    salt = secrets.token_hex(32)
    consent: dict[str, object] = {
        "schema": "privgadai.borrower-consent.v1",
        "offer_id": str(acceptance.offer_id),
        "borrower_id": str(acceptance.borrower_id),
        "document_preview_sha256": preview_digest(snapshot),
        "accepted_at": acceptance.accepted_at.astimezone(UTC).isoformat(),
        "channel": acceptance.channel,
        "ip_address": acceptance.ip_address,
        "user_agent": (user_agent or "")[:500],
        "authenticated_session_id": str(session_id),
        "consent_action": "Saya telah membaca ringkasan syarat ini dan menyetujui penawaran versi yang ditampilkan.",
        "signature_level": "authenticated_portal_consent_not_certified_esign",
    }
    secret = settings.PROOF_DIGEST_SECRET or settings.JWT_SECRET_KEY
    agreement.document_snapshot = snapshot
    agreement.consent_snapshot = consent
    agreement.document_salt = salt
    agreement.document_digest = make_digest(snapshot, salt)
    agreement.consent_digest = make_digest(consent, salt)
    agreement.opaque_chain_id = "0x" + hmac.new(
        secret.encode(), f"agreement:{agreement.org_id}:{agreement.id}".encode(), hashlib.sha256,
    ).hexdigest()
    agreement.chain_status = "pending" if settings.PROOF_CHAIN_ENABLED and settings.AGREEMENT_CONTRACT_ADDRESS else "not_configured"
    agreement.status = "accepted"
    await session.flush()
    return agreement


def public_record(agreement: PawnAgreement, *, include_snapshot: bool = False) -> dict[str, object]:
    result: dict[str, object] = {
        "id": str(agreement.id), "sbg_number": agreement.sbg_number,
        "document_version": agreement.document_version, "status": agreement.status,
        "accepted_at": agreement.signed_at.isoformat(), "document_digest": agreement.document_digest,
        "consent_digest": agreement.consent_digest, "chain_status": agreement.chain_status,
        "chain_id": get_settings().PROOF_CHAIN_ID,
        "contract_address": agreement.chain_contract_address or get_settings().AGREEMENT_CONTRACT_ADDRESS or None,
        "tx_hash": agreement.chain_tx_hash, "block_number": agreement.chain_block_number,
        "confirmed_at": agreement.chain_confirmed_at.isoformat() if agreement.chain_confirmed_at else None,
        "explorer_url": f"https://testnet.bscscan.com/tx/{agreement.chain_tx_hash}" if agreement.chain_tx_hash else None,
    }
    if include_snapshot:
        result["document"] = agreement.document_snapshot
        result["consent"] = agreement.consent_snapshot
        result["document_salt"] = agreement.document_salt
        result["opaque_chain_id"] = agreement.opaque_chain_id
    return result


def chain_commitment(opaque_id: str) -> tuple[str, str, int]:
    settings = get_settings()
    web3 = Web3(Web3.HTTPProvider(settings.PROOF_RPC_URL, request_kwargs={"timeout": 12}))
    if web3.eth.chain_id != 97:
        raise RuntimeError("RPC chain ID mismatch")
    contract = web3.eth.contract(address=Web3.to_checksum_address(settings.AGREEMENT_CONTRACT_ADDRESS), abi=AGREEMENT_ABI)
    document, consent, recorded_at = contract.functions.commitmentOf(bytes.fromhex(opaque_id[2:]), 1).call()
    return Web3.to_hex(document), Web3.to_hex(consent), recorded_at


async def verify(agreement: PawnAgreement) -> dict[str, object]:
    if not agreement.document_snapshot or not agreement.consent_snapshot or not agreement.document_salt:
        return {"local_integrity": False, "chain_match": False, "detail": "Perjanjian lama belum memiliki snapshot"}
    local = (
        hmac.compare_digest(agreement.document_digest or "", make_digest(agreement.document_snapshot, agreement.document_salt))
        and hmac.compare_digest(agreement.consent_digest or "", make_digest(agreement.consent_snapshot, agreement.document_salt))
    )
    if not get_settings().AGREEMENT_CONTRACT_ADDRESS or not agreement.opaque_chain_id:
        return {"local_integrity": local, "chain_match": False, "detail": "Registry belum dikonfigurasi"}
    try:
        document, consent, recorded_at = await asyncio.to_thread(chain_commitment, agreement.opaque_chain_id)
        match = recorded_at > 0 and hmac.compare_digest(document.lower(), (agreement.document_digest or "").lower()) and hmac.compare_digest(consent.lower(), (agreement.consent_digest or "").lower())
        return {"local_integrity": local, "chain_match": match, "detail": None if match else "Digest di chain tidak cocok atau belum tercatat"}
    except Exception:
        return {"local_integrity": local, "chain_match": False, "detail": "RPC BNB Testnet tidak tersedia"}
