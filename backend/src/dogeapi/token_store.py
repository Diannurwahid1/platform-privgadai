"""PostgreSQL-backed short-lived auth tokens for single-service deployments."""

from __future__ import annotations

import hashlib

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from dogeapi.settings import Settings


class PostgresTokenStore:
    """The small Redis-compatible subset used by the core auth endpoints.

    Keys are hashed before storage so bearer tokens cannot be recovered from
    the database. Values contain user IDs or a blocklist marker, never a JWT.
    """

    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(database_url, pool_pre_ping=True)

    @staticmethod
    def _digest(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    async def setex(self, key: str, ttl: int, value: str) -> None:
        if ttl < 1:
            raise ValueError("Token lifetime must be positive")
        async with self._engine.begin() as conn:
            await conn.execute(text("DELETE FROM auth_token_store WHERE expires_at <= now()"))
            await conn.execute(
                text(
                    """
                    INSERT INTO auth_token_store (key_hash, value, expires_at)
                    VALUES (:key_hash, :value, now() + (:ttl * interval '1 second'))
                    ON CONFLICT (key_hash) DO UPDATE
                    SET value = EXCLUDED.value, expires_at = EXCLUDED.expires_at
                    """
                ),
                {"key_hash": self._digest(key), "value": value, "ttl": ttl},
            )

    async def get(self, key: str) -> bytes | None:
        async with self._engine.connect() as conn:
            value = await conn.scalar(
                text(
                    """
                    SELECT value FROM auth_token_store
                    WHERE key_hash = :key_hash AND expires_at > now()
                    """
                ),
                {"key_hash": self._digest(key)},
            )
        return value.encode("utf-8") if isinstance(value, str) else None

    async def getdel(self, key: str) -> bytes | None:
        """Consume a token once, atomically, including under concurrent requests."""
        async with self._engine.begin() as conn:
            value = await conn.scalar(
                text(
                    """
                    DELETE FROM auth_token_store
                    WHERE key_hash = :key_hash AND expires_at > now()
                    RETURNING value
                    """
                ),
                {"key_hash": self._digest(key)},
            )
        return value.encode("utf-8") if isinstance(value, str) else None

    async def ping(self) -> bool:
        async with self._engine.connect() as conn:
            return bool(await conn.scalar(text("SELECT 1")))

    async def aclose(self) -> None:
        await self._engine.dispose()


def create_token_store(settings: Settings) -> PostgresTokenStore | Redis:
    if settings.TOKEN_STORE_BACKEND == "postgres":
        return PostgresTokenStore(settings.DATABASE_URL)

    return Redis.from_url(settings.REDIS_URL, decode_responses=False)
