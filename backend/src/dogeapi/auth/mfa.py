"""Dependency-free TOTP, secret encryption, and recovery-code helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from cryptography.fernet import Fernet

from dogeapi.settings import Settings


def _fernet(settings: Settings) -> Fernet:
    configured = settings.PII_ENCRYPTION_KEY.strip()
    if configured:
        try:
            return Fernet(configured.encode())
        except ValueError:
            pass
    material = hashlib.sha256(f"privgadai:mfa:{configured or settings.JWT_SECRET_KEY}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(material))


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def encrypt_totp_secret(settings: Settings, secret: str) -> str:
    return _fernet(settings).encrypt(secret.encode()).decode()


def decrypt_totp_secret(settings: Settings, ciphertext: str) -> str:
    return _fernet(settings).decrypt(ciphertext.encode()).decode()


def totp_code(secret: str, *, at_time: int | None = None) -> str:
    normalized = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(normalized)
    counter = int((at_time if at_time is not None else time.time()) // 30)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 1_000_000:06d}"


def verify_totp(secret: str, code: str, *, at_time: int | None = None) -> bool:
    if len(code) != 6 or not code.isdigit():
        return False
    current = at_time if at_time is not None else int(time.time())
    return any(hmac.compare_digest(totp_code(secret, at_time=current + offset * 30), code) for offset in (-1, 0, 1))


def otpauth_uri(secret: str, email: str, issuer: str = "PrivGadai") -> str:
    return f"otpauth://totp/{quote(issuer)}:{quote(email)}?secret={secret}&issuer={quote(issuer)}&digits=6&period=30"


def generate_recovery_codes(count: int = 8) -> list[str]:
    return [f"{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}" for _ in range(count)]


def hash_recovery_code(settings: Settings, code: str) -> str:
    return hmac.new(settings.JWT_SECRET_KEY.encode(), code.strip().upper().encode(), hashlib.sha256).hexdigest()
