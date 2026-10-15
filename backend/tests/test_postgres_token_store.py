"""Security properties of the PostgreSQL auth token store."""

from __future__ import annotations

import asyncio
from secrets import token_urlsafe

from sqlalchemy import text

from dogeapi.token_store import PostgresTokenStore


async def test_token_is_consumed_only_once_under_concurrency(redis_client: PostgresTokenStore) -> None:
    key = f"test:one-use:{token_urlsafe(12)}"
    await redis_client.setex(key, 60, "user-id")

    values = await asyncio.gather(redis_client.getdel(key), redis_client.getdel(key))
    assert values.count(b"user-id") == 1
    assert values.count(None) == 1


async def test_key_is_hashed_in_database(redis_client: PostgresTokenStore) -> None:
    key = f"test:secret-key:{token_urlsafe(12)}"
    await redis_client.setex(key, 60, "marker")

    async with redis_client._engine.connect() as conn:
        rows = (await conn.execute(text("SELECT key_hash FROM auth_token_store"))).scalars().all()

    assert key not in rows
    assert await redis_client.get(key) == b"marker"
