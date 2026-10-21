"""Submit borrower document and consent commitments to BNB Testnet."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import and_, case, or_, select
from web3 import Web3
from web3.exceptions import TransactionNotFound

from dogeapi.agreement.service import AGREEMENT_ABI
from dogeapi.db import get_session_factory
from dogeapi.models import PawnAgreement
from dogeapi.proof.service import make_digest
from dogeapi.settings import get_settings

log = logging.getLogger("privgadai.agreement")


def connect() -> tuple[Web3, object, object]:
    settings = get_settings()
    if not settings.PROOF_CHAIN_ENABLED or not settings.AGREEMENT_CONTRACT_ADDRESS:
        raise RuntimeError("Agreement chain anchoring is not configured")
    web3 = Web3(Web3.HTTPProvider(settings.PROOF_RPC_URL, request_kwargs={"timeout": 15}))
    if web3.eth.chain_id != 97:
        raise RuntimeError("Refusing to submit outside BSC Testnet")
    account = web3.eth.account.from_key(settings.PROOF_RELAYER_PRIVATE_KEY)
    contract = web3.eth.contract(address=Web3.to_checksum_address(settings.AGREEMENT_CONTRACT_ADDRESS), abi=AGREEMENT_ABI)
    if not web3.eth.get_code(contract.address):
        raise RuntimeError("Agreement registry bytecode not found")
    return web3, account, contract


def _ids(agreement: PawnAgreement) -> tuple[bytes, bytes, bytes]:
    if not agreement.opaque_chain_id or not agreement.document_digest or not agreement.consent_digest:
        raise RuntimeError("Agreement commitment is incomplete")
    if not agreement.document_snapshot or not agreement.consent_snapshot or not agreement.document_salt:
        raise RuntimeError("Agreement snapshot is missing")
    if agreement.document_digest != make_digest(agreement.document_snapshot, agreement.document_salt):
        raise RuntimeError("Document digest mismatch")
    if agreement.consent_digest != make_digest(agreement.consent_snapshot, agreement.document_salt):
        raise RuntimeError("Consent digest mismatch")
    return (bytes.fromhex(agreement.opaque_chain_id[2:]), bytes.fromhex(agreement.document_digest[2:]),
            bytes.fromhex(agreement.consent_digest[2:]))


def submit(agreement: PawnAgreement) -> str:
    agreement_id, document_digest, consent_digest = _ids(agreement)
    web3, account, contract = connect()
    current_document, current_consent, recorded_at = contract.functions.commitmentOf(agreement_id, 1).call()
    if recorded_at:
        if current_document != document_digest or current_consent != consent_digest:
            raise RuntimeError("On-chain agreement conflict")
        return "already_registered"
    call = contract.functions.recordVersion(agreement_id, 1, document_digest, consent_digest)
    nonce = web3.eth.get_transaction_count(account.address, "pending")
    gas = int(call.estimate_gas({"from": account.address}) * 1.25)
    tx = call.build_transaction({"chainId": 97, "from": account.address, "nonce": nonce,
                                 "gas": gas, "gasPrice": web3.eth.gas_price})
    signed = account.sign_transaction(tx)
    return Web3.to_hex(web3.eth.send_raw_transaction(signed.raw_transaction))


def receipt_status(agreement: PawnAgreement) -> tuple[str, int | None]:
    web3, _, contract = connect()
    try:
        receipt = web3.eth.get_transaction_receipt(agreement.chain_tx_hash)
    except TransactionNotFound:
        return "submitted", None
    if receipt.status != 1:
        return "reverted", receipt.blockNumber
    if web3.eth.block_number - receipt.blockNumber + 1 < get_settings().PROOF_CONFIRMATIONS:
        return "submitted", receipt.blockNumber
    agreement_id, document_digest, consent_digest = _ids(agreement)
    current_document, current_consent, recorded_at = contract.functions.commitmentOf(agreement_id, 1).call()
    if not recorded_at or current_document != document_digest or current_consent != consent_digest:
        return "reverted", receipt.blockNumber
    return "confirmed", receipt.blockNumber


async def process_one() -> bool:
    if not get_settings().AGREEMENT_CONTRACT_ADDRESS:
        return False
    factory = get_session_factory()
    async with factory() as session:
        agreement = await session.scalar(
            select(PawnAgreement)
            .where(or_(
                and_(PawnAgreement.chain_status.in_(["pending", "failed"]),
                     PawnAgreement.chain_tx_hash.is_(None), PawnAgreement.chain_attempts < 5),
                PawnAgreement.chain_status == "submitted",
            ))
            .order_by(case((PawnAgreement.chain_status == "pending", 0),
                           (PawnAgreement.chain_status == "failed", 1), else_=2), PawnAgreement.updated_at)
            .with_for_update(skip_locked=True).limit(1)
        )
        if agreement is None:
            return False
        try:
            if agreement.chain_tx_hash:
                agreement.chain_status, agreement.chain_block_number = await asyncio.to_thread(receipt_status, agreement)
                if agreement.chain_status == "confirmed":
                    agreement.chain_confirmed_at = datetime.now(UTC)
                    agreement.chain_last_error = None
                    log.info("Agreement confirmed: %s block=%s", agreement.id, agreement.chain_block_number)
            else:
                tx_hash = await asyncio.to_thread(submit, agreement)
                if tx_hash == "already_registered":
                    agreement.chain_status = "verified_on_chain"
                    agreement.chain_last_error = "Previously registered; original receipt unavailable"
                else:
                    agreement.chain_tx_hash = tx_hash
                    agreement.chain_contract_address = get_settings().AGREEMENT_CONTRACT_ADDRESS
                    agreement.chain_status = "submitted"
                    agreement.chain_last_error = None
                    log.info("Agreement submitted: %s tx=%s", agreement.id, tx_hash)
                agreement.chain_attempts += 1
        except Exception as exc:
            agreement.chain_status = "failed" if not agreement.chain_tx_hash else "submitted"
            if not agreement.chain_tx_hash:
                agreement.chain_attempts += 1
            agreement.chain_last_error = type(exc).__name__[:240]
            log.warning("Agreement %s attempt %s failed: %s", agreement.id, agreement.chain_attempts, type(exc).__name__)
        agreement.updated_at = datetime.now(UTC)
        await session.commit()
        return True
