"""Create immutable private snapshots and verify their public commitments."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from dogeapi.models import CollateralEvent, CollateralProof, EvidenceFile, LoanApplication
from dogeapi.settings import get_settings

PROOF_ABI = [
    {
        "inputs": [{"name": "eventId", "type": "bytes32"}, {"name": "digest", "type": "bytes32"}],
        "name": "registerProof",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "eventId", "type": "bytes32"}],
        "name": "proofOf",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def canonical_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def make_digest(payload: dict[str, object], salt: str) -> str:
    return "0x" + hashlib.sha256(bytes.fromhex(salt) + canonical_bytes(payload)).hexdigest()


def opaque_id(org_id: UUID, event_id: UUID, secret: str) -> str:
    return "0x" + hmac.new(secret.encode(), f"{org_id}:{event_id}".encode(), hashlib.sha256).hexdigest()


async def enqueue_custody_event(session: AsyncSession, event: CollateralEvent) -> CollateralProof | None:
    settings = get_settings()
    if not settings.PROOF_CHAIN_ENABLED:
        return None
    if event.event_type not in {"stored", "custody_dispatched", "custody_moved"}:
        return None
    if not event.id or not event.occurred_at:
        await session.flush()
    existing = await session.scalar(select(CollateralProof).where(CollateralProof.collateral_event_id == event.id))
    if existing is not None:
        return existing
    movement_id = event.event_metadata.get("movement_id")
    evidence_stmt = select(EvidenceFile).where(
        EvidenceFile.org_id == event.org_id,
        EvidenceFile.application_id == event.application_id,
        EvidenceFile.scan_status == "clean",
    )
    if movement_id:
        evidence_stmt = evidence_stmt.where(
            EvidenceFile.subject_type == "custody_movement", EvidenceFile.subject_id == UUID(str(movement_id))
        )
    else:
        evidence_stmt = evidence_stmt.where(
            EvidenceFile.evidence_type.in_(["custody_handover", "asset_condition", "pickup_handover"])
        )
    evidence = list(await session.scalars(evidence_stmt.order_by(EvidenceFile.id)))
    payload: dict[str, object] = {
        "schema": "privgadai.custody-proof.v1",
        "org_id": str(event.org_id),
        "application_id": str(event.application_id),
        "event_id": str(event.id),
        "event_type": event.event_type,
        "occurred_at": event.occurred_at.isoformat(),
        "actor_id": str(event.actor_user_id) if event.actor_user_id else None,
        "event_metadata": event.event_metadata,
        "evidence": [{"id": str(item.id), "sha256": item.sha256, "type": item.evidence_type} for item in evidence],
    }
    salt = secrets.token_hex(32)
    proof = CollateralProof(
        org_id=event.org_id,
        application_id=event.application_id,
        collateral_event_id=event.id,
        event_type=event.event_type,
        opaque_event_id=opaque_id(event.org_id, event.id, settings.PROOF_DIGEST_SECRET),
        digest=make_digest(payload, salt),
        payload=payload,
        salt=salt,
        chain_id=settings.PROOF_CHAIN_ID,
    )
    session.add(proof)
    await session.flush()
    return proof


def chain_digest(opaque_event_id: str) -> str:
    settings = get_settings()
    provider = Web3(Web3.HTTPProvider(settings.PROOF_RPC_URL, request_kwargs={"timeout": 12}))
    if provider.eth.chain_id != settings.PROOF_CHAIN_ID:
        raise RuntimeError("RPC chain ID mismatch")
    contract = provider.eth.contract(address=Web3.to_checksum_address(settings.PROOF_CONTRACT_ADDRESS), abi=PROOF_ABI)
    return Web3.to_hex(contract.functions.proofOf(bytes.fromhex(opaque_event_id[2:])).call())


async def verify_proof(proof: CollateralProof) -> dict[str, object]:
    local_match = hmac.compare_digest(proof.digest, make_digest(proof.payload, proof.salt))
    result: dict[str, object] = {"local_integrity": local_match, "chain_match": False, "chain_error": None}
    if not get_settings().PROOF_CONTRACT_ADDRESS:
        result["chain_error"] = "Kontrak testnet belum dikonfigurasi"
        return result
    try:
        actual = await asyncio.to_thread(chain_digest, proof.opaque_event_id)
        result["chain_match"] = hmac.compare_digest(actual.lower(), proof.digest.lower())
    except Exception:
        result["chain_error"] = "RPC BSC sementara tidak tersedia"
    return result


def public_record(proof: CollateralProof) -> dict[str, object]:
    return {
        "id": str(proof.id),
        "application_id": str(proof.application_id),
        "event_type": proof.event_type,
        "status": proof.status,
        "chain_id": proof.chain_id,
        "opaque_event_id": proof.opaque_event_id,
        "digest": proof.digest,
        "tx_hash": proof.tx_hash,
        "block_number": proof.block_number,
        "confirmed_at": proof.confirmed_at.isoformat() if proof.confirmed_at else None,
        "explorer_url": f"https://testnet.bscscan.com/tx/{proof.tx_hash}" if proof.tx_hash else None,
    }


async def list_proofs(
    session: AsyncSession, org_id: UUID, branch_ids: set[UUID] | None, application_id: UUID | None
) -> list[CollateralProof]:
    stmt = (
        select(CollateralProof)
        .join(
            LoanApplication,
            (LoanApplication.id == CollateralProof.application_id) & (LoanApplication.org_id == org_id),
        )
        .where(CollateralProof.org_id == org_id)
    )
    if branch_ids is not None:
        stmt = stmt.where(LoanApplication.branch_id.in_(branch_ids))
    if application_id is not None:
        stmt = stmt.where(CollateralProof.application_id == application_id)
    return list(await session.scalars(stmt.order_by(CollateralProof.created_at.desc()).limit(100)))


async def get_visible_proof(
    session: AsyncSession, org_id: UUID, branch_ids: set[UUID] | None, proof_id: UUID
) -> CollateralProof | None:
    stmt = (
        select(CollateralProof)
        .join(
            LoanApplication,
            (LoanApplication.id == CollateralProof.application_id) & (LoanApplication.org_id == org_id),
        )
        .where(CollateralProof.org_id == org_id, CollateralProof.id == proof_id)
    )
    if branch_ids is not None:
        stmt = stmt.where(LoanApplication.branch_id.in_(branch_ids))
    return await session.scalar(stmt)
