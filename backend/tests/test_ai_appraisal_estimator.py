"""Guardrails for indicative valuation, including sparse and unrelated evidence."""

from datetime import UTC, datetime
from decimal import Decimal

from dogeapi.operations.ai_appraisal import ComparablePoint, estimate_from_comparables


def _points(brand: str = "Apple", model: str = "iPhone 15 Pro") -> list[ComparablePoint]:
    return [
        ComparablePoint(str(index), brand, model, "B", Decimal(value), datetime.now(UTC))
        for index, value in enumerate((9_500_000, 10_000_000, 10_500_000), start=1)
    ]


def test_estimator_returns_range_for_matching_recent_evidence() -> None:
    result = estimate_from_comparables(_points(), "Apple", "iPhone 15 Pro", "B", 0.9)
    assert result.low is not None and result.high is not None
    assert result.low < Decimal("10000000") < result.high
    assert len(result.source_ids) == 3


def test_estimator_abstains_without_enough_or_related_evidence() -> None:
    assert estimate_from_comparables(_points()[:2], "Apple", "iPhone 15 Pro", "B", 1).low is None
    assert estimate_from_comparables(_points(), "Samsung", "Galaxy S20", "B", 1).low is None
    assert estimate_from_comparables(_points(), None, None, "B", 1).low is None
    inconsistent = [
        ComparablePoint(str(index), "Apple", "iPhone 15 Pro", "B", Decimal(value), datetime.now(UTC))
        for index, value in enumerate((2_000_000, 10_000_000, 30_000_000), start=1)
    ]
    assert estimate_from_comparables(inconsistent, "Apple", "iPhone 15 Pro", "B", 1).low is None
