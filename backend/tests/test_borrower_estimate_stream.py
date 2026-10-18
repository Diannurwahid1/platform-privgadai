"""The borrower receives actual appraisal stages and a saved result."""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from dogeapi.db import get_session
from dogeapi.operations import ai_appraisal
from dogeapi.operations.borrower_router import _csrf, router


@pytest.mark.asyncio
async def test_estimate_stream_emits_work_stages_and_persists_borrower_details(monkeypatch: pytest.MonkeyPatch) -> None:
    class Session:
        def __init__(self) -> None:
            self.committed = False
            self.added: list[object] = []

        async def scalar(self, _query: object) -> object:
            return object()

        def add(self, item: object) -> None:
            self.added.append(item)

        async def commit(self) -> None:
            self.committed = True

        async def rollback(self) -> None:
            raise AssertionError("The estimate should not fail")

    session = Session()
    description = "Kapasitas 256 GB, baterai 83%, layar tergores halus"

    async def fake_create(*_args: object, **kwargs: object) -> SimpleNamespace:
        assert kwargs["asset_description"] == description
        progress = kwargs["on_progress"]
        await progress("vision", "AI membaca foto")
        await progress("searching", "Tavily mencari harga")
        return SimpleNamespace(asset_description=description)

    monkeypatch.setattr(ai_appraisal, "create_estimate", fake_create)
    monkeypatch.setattr(ai_appraisal, "public_estimate", lambda item: {"asset_description": item.asset_description})
    principal = SimpleNamespace(org=SimpleNamespace(id=uuid4()), borrower=SimpleNamespace(id=uuid4()))
    app = FastAPI()
    app.state.settings = object()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[_csrf] = lambda: principal
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/borrower/v1/estimates/stream",
            data={"category_code": "smartphone", "condition_grade": "B", "share_photo_with_ai": "true",
                  "brand": "Apple", "model": "iPhone", "asset_description": description},
            files={"photo": ("barang.jpg", b"sample", "image/jpeg")})
    events = [json.loads(line) for line in response.text.splitlines()]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert [event["stage"] for event in events if event["type"] == "stage"] == ["received", "vision", "searching"]
    assert events[-1] == {"type": "complete", "estimate": {"asset_description": description}}
    assert session.committed
    assert len(session.added) == 1
