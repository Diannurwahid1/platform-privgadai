"""Backend-only BSC Testnet relayer. Run with ``python -m dogeapi.proof.worker``."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import and_, case, or_, select
from web3 import Web3
from web3.exceptions import TransactionNotFound

from dogeapi.db import get_session_factory
from dogeapi.models import CollateralProof
from dogeapi.proof.service import PROOF_ABI, make_digest
from dogeapi.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("privgadai.proof")


def connect() -> tuple[Web3, object, object]:
    settings = get_settings()
    if not settings.PROOF_CHAIN_ENABLED:
        raise RuntimeError("BSC proof service is disabled")
    web3 = Web3(Web3.HTTPProvider(settings.PROOF_RPC_URL, request_kwargs={"timeout": 15}))
    if web3.eth.chain_id != 97:
        raise RuntimeError("Refusing to submit proof to a non-BSC-Testnet chain")
    account = web3.eth.account.from_key(settings.PROOF_RELAYER_PRIVATE_KEY)
    contract = web3.eth.contract(address=Web3.to_checksum_address(settings.PROOF_CONTRACT_ADDRESS), abi=PROOF_ABI)
    if not web3.eth.get_code(contract.address):
        raise RuntimeError("Proof registry bytecode not found on BSC Testnet")
    return web3, account, contract


def submit(proof: CollateralProof) -> str:
    if proof.digest != make_digest(proof.payload, proof.salt):
        raise RuntimeError("Local snapshot digest mismatch")
    web3, account, contract = connect()
    event_id = bytes.fromhex(proof.opaque_event_id[2:])
    digest = bytes.fromhex(proof.digest[2:])
    current = contract.functions.proofOf(event_id).call()
    if current != bytes(32):
        if current != digest:
            raise RuntimeError("On-chain digest conflict")
        return "already_registered"
    call = contract.functions.registerProof(event_id, digest)
    nonce = web3.eth.get_transaction_count(account.address, "pending")
    gas = int(call.estimate_gas({"from": account.address}) * 1.25)
    tx = call.build_transaction(
        {
            "chainId": 97,
            "from": account.address,
            "nonce": nonce,
            "gas": gas,
            "gasPrice": web3.eth.gas_price,
        }
    )
    signed = account.sign_transaction(tx)
    return Web3.to_hex(web3.eth.send_raw_transaction(signed.raw_transaction))


def receipt_status(proof: CollateralProof) -> tuple[str, int | None]:
    web3, _, contract = connect()
    try:
        receipt = web3.eth.get_transaction_receipt(proof.tx_hash)
    except TransactionNotFound:
        return "submitted", None
    if receipt.status != 1:
        return "reverted", receipt.blockNumber
    if web3.eth.block_number - receipt.blockNumber + 1 < get_settings().PROOF_CONFIRMATIONS:
        return "submitted", receipt.blockNumber
    current = contract.functions.proofOf(bytes.fromhex(proof.opaque_event_id[2:])).call()
    if current != bytes.fromhex(proof.digest[2:]):
        return "reverted", receipt.blockNumber
    return "confirmed", receipt.blockNumber


async def process_one() -> bool:
    factory = get_session_factory()
    async with factory() as session:
        proof = await session.scalar(
            select(CollateralProof)
            .where(
                or_(
                    and_(
                        CollateralProof.status.in_(["pending", "failed"]),
                        CollateralProof.tx_hash.is_(None),
                        CollateralProof.attempts < 5,
                    ),
                    CollateralProof.status == "submitted",
                )
            )
            .order_by(
                case((CollateralProof.status == "pending", 0), (CollateralProof.status == "failed", 1), else_=2),
                CollateralProof.updated_at,
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if proof is None:
            return False
        try:
            if proof.tx_hash:
                proof.status, proof.block_number = await asyncio.to_thread(receipt_status, proof)
                if proof.status == "confirmed":
                    proof.confirmed_at = datetime.now(UTC)
                    proof.last_error = None
                    log.info("Proof confirmed: %s block=%s", proof.id, proof.block_number)
            else:
                tx_hash = await asyncio.to_thread(submit, proof)
                if tx_hash == "already_registered":
                    proof.status = "verified_on_chain"
                    proof.last_error = "Registered previously; original receipt unavailable"
                else:
                    proof.tx_hash = tx_hash
                    proof.contract_address = get_settings().PROOF_CONTRACT_ADDRESS
                    proof.status = "submitted"
                    proof.last_error = None
                    log.info("Proof submitted: %s tx=%s", proof.id, tx_hash)
                proof.attempts += 1
        except Exception as exc:
            proof.status = "failed" if not proof.tx_hash else "submitted"
            if proof.tx_hash is None:
                proof.attempts += 1
            proof.last_error = type(exc).__name__[:240]
            log.warning("Proof %s attempt %s failed: %s", proof.id, proof.attempts, type(exc).__name__)
        proof.updated_at = datetime.now(UTC)
        await session.commit()
        return True


async def run(once: bool) -> None:
    connect()
    while True:
        processed = await process_one()
        if once:
            return
        await asyncio.sleep(4 if processed else 12)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.once))
