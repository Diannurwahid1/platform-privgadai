"""One-time staging setup for BSC proof relayer; never prints private values."""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

CONTRACT = "0xad982f249ad9460a8f40b0306029228dc548fd4f"


def main(root: Path, wallet_file: Path) -> None:
    env_file = root / ".env"
    if not env_file.is_file() or not wallet_file.is_file():
        raise SystemExit("Missing server .env or temporary wallet file")
    wallet_line = next((line for line in wallet_file.read_text().splitlines() if line.startswith("BSC_TESTNET_PRIVATE_KEY=")), "")
    private_key = wallet_line.removeprefix("BSC_TESTNET_PRIVATE_KEY=").strip()
    if len(private_key) != 66 or not private_key.startswith("0x"):
        raise SystemExit("Invalid testnet wallet key")
    lines = env_file.read_text().splitlines()
    current = dict(line.split("=", 1) for line in lines if "=" in line and not line.lstrip().startswith("#"))
    digest_secret = current.get("PROOF_DIGEST_SECRET") or secrets.token_hex(32)
    desired = {
        "PROOF_CHAIN_ENABLED": "true",
        "PROOF_CHAIN_ID": "97",
        "PROOF_RPC_URL": "https://bsc-testnet-dataseed.bnbchain.org",
        "PROOF_CONTRACT_ADDRESS": CONTRACT,
        "PROOF_RELAYER_PRIVATE_KEY": private_key,
        "PROOF_DIGEST_SECRET": digest_secret,
        "PROOF_CONFIRMATIONS": "3",
    }
    remaining = [line for line in lines if not any(line.startswith(f"{name}=") for name in desired)]
    content = "\n".join([*remaining, "", "# BSC Testnet proof registry", *(f"{key}={value}" for key, value in desired.items()), ""])
    temporary = env_file.with_name(".env.proof-new")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, env_file)
        os.chmod(env_file, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("BSC Testnet proof environment configured")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: configure-bsc-testnet.py REPO_ROOT TEMP_WALLET_FILE")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
