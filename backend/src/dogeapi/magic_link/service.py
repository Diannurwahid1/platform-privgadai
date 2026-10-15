"""Magic-link tokens persisted in the configured short-lived token store."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from redis.asyncio import Redis

from dogeapi.token_store import PostgresTokenStore

PREFIX = "magiclink:"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue(redis: Redis | PostgresTokenStore, email: str, *, ttl: timedelta) -> str:
    token = secrets.token_urlsafe(32)
    await redis.setex(
        f"{PREFIX}{_hash(token)}",
        int(ttl.total_seconds()),
        email,
    )
    return token


async def consume(redis: Redis | PostgresTokenStore, token: str) -> str | None:
    """Validate and atomically delete a magic-link token. Returns email or None."""
    key = f"{PREFIX}{_hash(token)}"
    raw = await redis.getdel(key)
    if not raw:
        return None
    return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
