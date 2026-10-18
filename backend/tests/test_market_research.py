"""Market evidence must be cited, comparable, and independently corroborated."""

from types import SimpleNamespace

import pytest

from dogeapi.operations import market_research
from dogeapi.operations.market_research import (
    _aggregate,
    _date_from_source,
    _dated_at,
    _focus_content,
    _has_exact_day,
    _host,
    _json_object,
    _structured_antam_row,
    _valid_observations,
    research_market,
)


def test_parser_accepts_json_followed_by_router_text() -> None:
    assert _json_object('Analysis follows. {"observations": []}\nAdditional text: {"debug": true}') == {"observations": []}


def test_source_independence_groups_subdomains() -> None:
    assert _host("https://www.anekalogam.co.id/id") == _host("https://store.anekalogam.co.id/product")
    assert _host("https://www.blibli.com/item") != _host("https://anekalogam.co.id/id")


def test_rejects_prices_without_exact_source_evidence() -> None:
    sources = [{"id": "S1", "title": "Harga", "url": "https://a.example/item", "host": "a.example",
                "content": "Antam 10 gram Rp 24.000.000", "published_date": ""}]
    rows = [
        {"source_id": "S1", "comparable": True, "price_idr": 24_000_000,
         "price_evidence": "Rp 24.000.000", "price_kind": "buyback"},
        {"source_id": "S1", "comparable": True, "price_idr": 99_000_000,
         "price_evidence": "Rp 99.000.000", "price_kind": "buyback"},
    ]
    found = _valid_observations(rows, sources)
    assert len(found) == 1
    assert found[0]["price_idr"] == 24_000_000


def test_requires_multiple_independent_domains_and_same_price_type() -> None:
    rows = [
        {"source_id": "S1", "host": "one.example", "price_idr": 24_000_000, "price_kind": "buyback"},
        {"source_id": "S2", "host": "one.example", "price_idr": 25_000_000, "price_kind": "buyback"},
        {"source_id": "S3", "host": "one.example", "price_idr": 26_000_000, "price_kind": "buyback"},
    ]
    assert _aggregate(rows, "Emas", 1)["status"] == "INSUFFICIENT"
    rows[2]["host"] = "two.example"
    assert _aggregate(rows, "Emas", 1)["status"] == "COMPARED"
    rows[2]["price_kind"] = "retail"
    assert _aggregate(rows, "Emas", 1)["status"] == "INSUFFICIENT"


def test_two_gold_dealer_prices_make_limited_retail_range() -> None:
    rows = [
        {"source_id": "S1", "host": "dealer.example", "price_idr": 24_970_000, "price_kind": "new"},
        {"source_id": "S2", "host": "shop.example", "price_idr": 26_280_000, "price_kind": "retail"},
    ]
    result = _aggregate(rows, "Emas", 0.9)
    assert result["status"] == "LIMITED"
    assert result["price_kind"] == "retail"
    assert result["low_value"] < result["high_value"]


def test_extracts_indonesian_update_date_from_source() -> None:
    source = {"title": "Harga Antam", "content": "Terakhir Diperbarui:15 Oktober 2026 11.35"}
    assert _dated_at(_date_from_source(source)).date().isoformat() == "2026-10-15"
    assert _has_exact_day("15 Oktober 2026")
    assert not _has_exact_day("Oktober 2026")
    assert _dated_at("April 2026").date().isoformat() == "2026-04-01"


def test_gold_table_focus_keeps_only_requested_weight_and_update_date() -> None:
    content = "Terakhir Diperbarui:15 Oktober 2026\nHarga berlaku untuk LM Antam\n| Emas LM | Harga kami jual | Harga kami beli |\n| 1gram | Rp 2.500.000 | Rp 2.400.000 |\n| 10gram | Rp 24.970.000 | Rp 24.500.000 |\n| 25gram | Rp 62.000.000 |"
    focused = _focus_content(content, "Emas", "Logam Mulia 10 gram")
    assert "15 Oktober 2026" in focused
    assert "Rp 24.970.000" in focused
    assert "Rp 62.000.000" not in focused
    row = _structured_antam_row({"id": "S1", "title": "Harga Antam", "content": focused}, "Antam", "Logam Mulia 10 gram")
    assert row is not None and row["price_idr"] == 24_500_000
    assert row["source_date"] == "15 Oktober 2026"


def test_abstains_on_wide_dispersion() -> None:
    rows = [
        {"source_id": f"S{i}", "host": f"{i}.example", "price_idr": value, "price_kind": "used"}
        for i, value in enumerate((2_000_000, 8_000_000, 20_000_000), start=1)
    ]
    assert _aggregate(rows, "Smartphone", 1)["status"] == "DISPERSED"


@pytest.mark.asyncio
async def test_borrower_details_replan_queries_without_personal_identifiers(monkeypatch: pytest.MonkeyPatch) -> None:
    planned: list[dict[str, object]] = []
    stages: list[str] = []

    async def fake_llm(_settings: object, _system: str, attributes: dict[str, object], _tokens: int) -> dict[str, object]:
        planned.append(attributes)
        return {"queries": []}

    async def progress(stage: str, _message: str) -> None:
        stages.append(stage)

    monkeypatch.setattr(market_research, "_llm", fake_llm)
    settings = SimpleNamespace(BYNARA_API_KEY="test", TAVILY_API_KEY="test")
    result = await research_market(settings, "smartphone", "Apple", "iPhone 13 Pro", "C",
                                   {"search_queries": ["query one", "query two", "query three"]}, 0.9,
                                   asset_description="256 GB, baterai 83%, kontak 081234567890", on_progress=progress)

    assert result["status"] == "UNAVAILABLE"
    assert planned[0]["borrower_details_unverified"] == "256 GB, baterai 83%, kontak "
    assert stages == ["planning"]
