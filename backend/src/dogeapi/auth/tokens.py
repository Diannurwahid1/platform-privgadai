"""Single-use email-verification tokens in the configured token store."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from uuid import UUID

from redis.asyncio import Redis

from dogeapi.token_store import PostgresTokenStore

VERIFY_PREFIX = "verify-email:"
VERIFY_TTL = timedelta(hours=24)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_email_verify_token(redis: Redis | PostgresTokenStore, user_id: UUID) -> str:
    """Generate + persist a single-use verification token.

    Returns the *plaintext* token; only the hash is stored.
    """
    token = secrets.token_urlsafe(32)
    await redis.setex(
        f"{VERIFY_PREFIX}{_hash(token)}",
        int(VERIFY_TTL.total_seconds()),
        str(user_id),
    )
    return token


async def consume_email_verify_token(redis: Redis | PostgresTokenStore, token: str) -> UUID | None:
    """Validate + atomically delete a verification token.

    Returns the associated user id on success, or ``None`` if the token is
    unknown / expired / already consumed.
    """
    key = f"{VERIFY_PREFIX}{_hash(token)}"
    raw_user_id = await redis.getdel(key)
    if not raw_user_id:
        return None
    return UUID(raw_user_id.decode("utf-8") if isinstance(raw_user_id, bytes) else raw_user_id)
