"""Verify an exported borrower agreement bundle against BNB Testnet.

Run from backend/: .venv/bin/python scripts/verify_agreement_export.py FILE.json
The file remains local; only opaque bytes32 values are sent to the RPC.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from web3 import Web3

from dogeapi.agreement.service import AGREEMENT_ABI
from dogeapi.proof.service import make_digest
from dogeapi.settings import get_settings

EXPECTED_REGISTRY = "0xa90f0d609ca697cdc1c22fe2cc1b73dca9774abb"


def main(path: Path) -> int:
    record = json.loads(path.read_text(encoding="utf-8"))
    document = record["document"]
    consent = record["consent"]
    salt = record["document_salt"]
    opaque_id = record["opaque_chain_id"]
    local_document = make_digest(document, salt)
    local_consent = make_digest(consent, salt)
    local_match = local_document == record["document_digest"] and local_consent == record["consent_digest"]
    settings = get_settings()
    if str(record.get("contract_address", "")).lower() != EXPECTED_REGISTRY:
        raise SystemExit("Export points to an unrecognized agreement registry")
    web3 = Web3(Web3.HTTPProvider(settings.PROOF_RPC_URL, request_kwargs={"timeout": 15}))
    if web3.eth.chain_id != 97:
        raise SystemExit("Refusing a non-BNB-Testnet RPC")
    contract = web3.eth.contract(address=Web3.to_checksum_address(EXPECTED_REGISTRY), abi=AGREEMENT_ABI)
    chain_document, chain_consent, recorded_at = contract.functions.commitmentOf(bytes.fromhex(opaque_id[2:]), 1).call()
    chain_match = recorded_at > 0 and chain_document == bytes.fromhex(local_document[2:]) and chain_consent == bytes.fromhex(local_consent[2:])
    print(f"Local integrity: {local_match}")
    print(f"BNB Testnet match: {chain_match}")
    print(f"Transaction: {record.get('tx_hash') or 'not in export'}")
    return 0 if local_match and chain_match else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_agreement_export.py FILE.json")
    raise SystemExit(main(Path(sys.argv[1])))
