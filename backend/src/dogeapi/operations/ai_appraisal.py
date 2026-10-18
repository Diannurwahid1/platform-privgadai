"""Photo quality, visual identity, and cited live market research.

The gateway extracts attributes and source prices. Backend guards validate
evidence and calculate the indicative range. The older local kNN estimator is
retained for historical comparison and tests, never as a borrower price fallback.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import math
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.file_security import scan_upload
from dogeapi.models import AiAppraisalEstimate, AppraisalComparable, Asset, HumanAppraisal, LoanApplication
from dogeapi.operations.market_research import _json_object, research_market
from dogeapi.settings import Settings, get_settings

ESTIMATOR_VERSION = "comparable-knn-v1"
_GRADES = {"A": 0, "B": 1, "C": 2, "D": 3}
ProgressCallback = Callable[[str, str], Awaitable[None]]


@dataclass(frozen=True)
class PhotoQuality:
    score: float
    findings: list[str]
    gateway_image: bytes


@dataclass(frozen=True)
class ComparablePoint:
    source_id: str
    brand: str | None
    model: str | None
    condition_grade: str
    market_value: Decimal
    observed_at: datetime
    is_demo: bool = False


@dataclass(frozen=True)
class LocalEstimate:
    low: Decimal | None
    high: Decimal | None
    confidence: float | None
    source_ids: list[str]
    explanation: str


def _normalize(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def inspect_photo(content: bytes) -> PhotoQuality:
    try:
        with Image.open(io.BytesIO(content)) as source:
            image = ImageOps.exif_transpose(source)
            image.load()
            width, height = image.size
            if width * height > 24_000_000:
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Resolusi foto terlalu besar")
            rgb = image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Foto barang tidak dapat dibaca") from exc

    sample = rgb.copy()
    sample.thumbnail((768, 768))
    gray = ImageOps.grayscale(sample)
    brightness = ImageStat.Stat(gray).mean[0]
    edge_strength = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).stddev[0]
    findings: list[str] = []
    score = 1.0
    if min(width, height) < 480:
        findings.append("Resolusi rendah; foto ulang dari jarak yang lebih dekat.")
        score -= 0.25
    if brightness < 45:
        findings.append("Foto terlalu gelap; tambah pencahayaan.")
        score -= 0.25
    elif brightness > 220:
        findings.append("Foto terlalu terang; hindari pantulan cahaya.")
        score -= 0.2
    if edge_strength < 16:
        findings.append("Detail kurang tajam; pastikan kamera fokus.")
        score -= 0.3
    if max(width, height) / max(min(width, height), 1) > 3.2:
        findings.append("Barang tampak terpotong; ambil foto seluruh barang.")
        score -= 0.15
    gateway = rgb.copy()
    gateway.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    gateway.save(buffer, format="JPEG", quality=84, optimize=True)
    return PhotoQuality(max(0.0, min(1.0, score)), findings, buffer.getvalue())


def _parse_vision_json(raw: str) -> dict[str, object]:
    result = _json_object(raw)
    allowed = {"category", "brand", "model", "visible_condition", "missing_views", "confidence", "notes", "search_queries"}
    parsed = {key: value for key, value in result.items() if key in allowed}
    confidence = parsed.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        parsed["confidence"] = 0.0
    queries = parsed.get("search_queries")
    parsed["search_queries"] = [str(query)[:180] for query in queries[:3] if isinstance(query, str)] if isinstance(queries, list) else []
    return parsed


async def describe_photo(settings: Settings, jpeg: bytes, declared_category: str,
                         declared_brand: str | None = None, declared_model: str | None = None,
                         asset_description: str | None = None) -> tuple[str, dict[str, object]]:
    if not settings.BYNARA_API_KEY:
        return "unavailable", {}
    image_url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
    payload = {
        "model": settings.BYNARA_MODEL,
        "stream": False,
        "reasoning_effort": "low",
        "max_tokens": 1400,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You inspect photos of pledged goods. Return one JSON object only with keys "
                    "category, brand, model, visible_condition, missing_views, confidence, notes, search_queries. "
                    "confidence is 0..1. Describe only what is visible; use null if unknown. "
                    "search_queries is exactly three short Indonesian market-price web queries: official/dealer, used or buyback, and independent source. "
                    "Use all borrower details only as unverified hints; never claim they are visible in the photo. "
                    "Preserve gold weight, phone variant, or vehicle year when known. "
                    "Never estimate price, authenticity, ownership, gold purity, or loan eligibility."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Declared asset category: {declared_category}; brand: {declared_brand or 'unknown'}; model: {declared_model or 'unknown'}; borrower details (unverified): {asset_description or 'none'}. Inspect this photo and plan market-price queries."},
                    {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                ],
            },
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=settings.BYNARA_TIMEOUT_SECONDS) as client:
            response = await client.post(
                settings.BYNARA_BASE_URL.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {settings.BYNARA_API_KEY}"},
                json=payload,
            )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Vision response has no text")
        return "succeeded", _parse_vision_json(content)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return "unavailable", {}


async def _comparables(session: AsyncSession, org_id: UUID, category_code: str) -> list[ComparablePoint]:
    recent = datetime.now(UTC) - timedelta(days=730)
    curated = list(
        await session.scalars(
            select(AppraisalComparable).where(
                AppraisalComparable.org_id == org_id,
                AppraisalComparable.category_code == category_code,
                AppraisalComparable.is_active,
                AppraisalComparable.observed_at >= recent,
            )
        )
    )
    rows = (
        await session.execute(
            select(HumanAppraisal, Asset)
            .join(
                LoanApplication,
                (LoanApplication.id == HumanAppraisal.application_id) & (LoanApplication.org_id == org_id),
            )
            .join(Asset, (Asset.application_id == LoanApplication.id) & (Asset.org_id == org_id))
            .where(
                HumanAppraisal.org_id == org_id,
                HumanAppraisal.status == "final",
                Asset.category == category_code,
                HumanAppraisal.created_at >= recent,
            )
        )
    ).all()
    settings = get_settings()
    return [
        ComparablePoint(
            f"demo:{item.id}" if item.source_label.startswith("DEMO SINTETIS") else str(item.id),
            item.brand, item.model, item.condition_grade, item.market_value, item.observed_at,
            item.source_label.startswith("DEMO SINTETIS"),
        )
        for item in curated if not (settings.is_production and item.source_label.startswith("DEMO SINTETIS"))
    ] + [
        ComparablePoint(
            f"appraisal:{appraisal.id}", asset.brand, asset.model, appraisal.condition_grade,
            appraisal.market_value, appraisal.created_at,
        )
        for appraisal, asset in rows
    ]


def estimate_from_comparables(
    points: list[ComparablePoint], brand: str | None, model: str | None, condition_grade: str, quality_score: float
) -> LocalEstimate:
    if not _normalize(brand) and not _normalize(model):
        return LocalEstimate(None, None, None, [], "Isi merek atau tipe barang agar pembanding relevan.")
    if len(points) < 3:
        return LocalEstimate(None, None, None, [], "Belum ada tiga pembanding terverifikasi untuk kategori ini.")
    today = datetime.now(UTC)

    def distance(point: ComparablePoint) -> float:
        grade_delta = abs(_GRADES.get(point.condition_grade.upper(), 1) - _GRADES.get(condition_grade.upper(), 1))
        brand_penalty = 0 if not brand or _normalize(brand) == _normalize(point.brand) else 1.2
        model_penalty = 0 if not model or _normalize(model) == _normalize(point.model) else 0.8
        age_days = max(0, (today - point.observed_at).days)
        return grade_delta * 0.65 + brand_penalty + model_penalty + min(age_days / 730, 1.0) * 0.4

    nearest = sorted(points, key=distance)[:7]
    if distance(nearest[2]) > 1.2:
        return LocalEstimate(None, None, None, [], "Pembanding yang tersedia terlalu berbeda dari barang ini.")
    weights = [1 / (1 + distance(point)) ** 2 for point in nearest]
    values = [float(point.market_value) for point in nearest]
    weighted_mean = sum(value * weight for value, weight in zip(values, weights, strict=True)) / sum(weights)
    variance = sum(weight * (value - weighted_mean) ** 2 for value, weight in zip(values, weights, strict=True)) / sum(weights)
    if weighted_mean <= 0 or math.sqrt(variance) / weighted_mean > 0.45:
        return LocalEstimate(None, None, None, [], "Harga pembanding terlalu beragam untuk membuat kisaran yang layak.")
    relative_spread = min(0.4, max(0.12, math.sqrt(variance) / weighted_mean if weighted_mean else 0.4))
    spread = weighted_mean * relative_spread
    granularity = Decimal("1000")
    low = (Decimal(str(max(1000, weighted_mean - spread))) / granularity).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * granularity
    high = (Decimal(str(weighted_mean + spread)) / granularity).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * granularity
    confidence = min(0.9, (0.42 + min(len(nearest), 7) * 0.055) * quality_score * (1 - relative_spread / 2))
    demo_only = any(point.is_demo for point in nearest)
    explanation = (
        "SIMULASI DATA DEMO SINTETIS. Angka ini hanya untuk menguji alur; penaksir harus memakai pembanding riil. "
        if demo_only else ""
    ) + f"Kisaran awal dari {len(nearest)} pembanding; variasi harga dan kondisi tetap perlu pemeriksaan fisik."
    return LocalEstimate(
        low, high, round(confidence, 4), [point.source_id for point in nearest],
        explanation,
    )


async def create_estimate(
    session: AsyncSession,
    settings: Settings,
    org_id: UUID,
    borrower_id: UUID,
    category_code: str,
    brand: str | None,
    model: str | None,
    condition_grade: str,
    file_name: str,
    content_type: str,
    content: bytes,
    asset_description: str | None = None,
    on_progress: ProgressCallback | None = None,
) -> AiAppraisalEstimate:
    async def progress(stage: str, message: str) -> None:
        if on_progress:
            await on_progress(stage, message)

    await progress("security", "Memeriksa format dan keamanan foto")
    scan = await scan_upload(content, content_type, settings)
    if scan.status != "clean":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Foto barang gagal pemeriksaan keamanan")
    await progress("photo", "Mengukur ketajaman, pencahayaan, dan kelengkapan foto")
    quality = await asyncio.to_thread(inspect_photo, content)
    digest = hashlib.sha256(content).hexdigest()
    existing = await session.scalar(
        select(AiAppraisalEstimate.id).where(
            AiAppraisalEstimate.org_id == org_id,
            AiAppraisalEstimate.photo_sha256 == digest,
            AiAppraisalEstimate.borrower_id == borrower_id,
        )
    )
    findings = quality.findings.copy()
    if existing is not None:
        findings.append("Foto ini pernah dipakai; pastikan barang dan kondisi masih sama.")
    await progress("vision", "AI mengenali barang dan atribut yang tampak di foto")
    vision_status, vision_result = await describe_photo(
        settings, quality.gateway_image, category_code, brand, model, asset_description
    )
    visual_category = str(vision_result.get("category") or "").casefold().strip()
    if visual_category and visual_category != category_code.casefold().strip():
        findings.append("Kategori dari foto berbeda dari pilihan Anda; petugas perlu memeriksa.")
    visual_brand = str(vision_result.get("brand") or "").casefold().strip()
    if visual_brand and brand and visual_brand != brand.casefold().strip():
        findings.append("Merek dari foto berbeda dari isian; petugas perlu memeriksa.")
    visual_notes = " ".join(str(vision_result.get(key) or "") for key in ("notes", "visible_condition")).casefold()
    if any(word in visual_notes for word in ("illustration", "rendering", "drawing", "screenshot")):
        findings.append("Gambar tampak seperti ilustrasi atau tangkapan layar; unggah foto barang asli untuk penaksiran.")
    research = await research_market(
        settings, category_code, brand, model, condition_grade, vision_result, quality.score,
        asset_description=asset_description, on_progress=on_progress,
    )
    selected = research.get("selected", [])
    state = "SUCCESS" if research["status"] == "COMPARED" else "NEEDS_REVIEW"
    if vision_status != "succeeded" or any("berbeda" in finding for finding in findings):
        state = "NEEDS_REVIEW"
    if quality.score < 0.65 or any("ilustrasi" in finding for finding in findings):
        state = "NEEDS_REVIEW"
    if vision_status != "succeeded":
        findings.append("Analisis visual sementara tidak tersedia; atribut perlu diperiksa petugas.")
    await progress("saving", "Menyimpan bukti dan hasil estimasi untuk penaksir")
    relative_key = f"clean/{org_id}/borrower-previews/{secrets.token_hex(20)}{Path(file_name).suffix.lower()[:8]}"
    storage_root = Path(__file__).resolve().parents[3] / ".data" / "evidence"
    target = (storage_root / relative_key).resolve()
    if storage_root.resolve() not in target.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid photo path")
    target.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(target.write_bytes, content)
    item = AiAppraisalEstimate(
        org_id=org_id,
        borrower_id=borrower_id,
        category_code=category_code,
        brand=brand,
        model=model,
        asset_description=asset_description,
        condition_grade=condition_grade,
        photo_sha256=digest,
        photo_key=relative_key,
        photo_content_type=content_type,
        photo_file_name=Path(file_name).name[:255],
        status=state,
        quality_score=Decimal(str(round(quality.score, 4))),
        quality_findings=findings,
        vision_result=vision_result,
        research_result=research,
        vision_status=vision_status,
        model_name=settings.BYNARA_MODEL,
        estimator_version="tavily-step5-median-v1",
        low_value=research.get("low_value") if quality.score >= 0.65 else None,
        high_value=research.get("high_value") if quality.score >= 0.65 else None,
        confidence=Decimal(str(research["confidence"])) if research.get("confidence") is not None and quality.score >= 0.65 else None,
        comparable_count=len(selected),
        comparable_ids=[str(row["url"]) for row in selected],
        explanation=str(research["reason"]),
    )
    session.add(item)
    await session.flush()
    return item


def public_estimate(item: AiAppraisalEstimate) -> dict[str, object]:
    return {
        "id": item.id,
        "status": item.status,
        "quality_score": item.quality_score,
        "quality_findings": item.quality_findings,
        "vision_status": item.vision_status,
        "vision_result": item.vision_result,
        "asset_description": item.asset_description,
        "research_result": item.research_result,
        "low_value": item.low_value,
        "high_value": item.high_value,
        "confidence": item.confidence,
        "comparable_count": item.comparable_count,
        "explanation": item.explanation,
        "model_name": item.model_name,
        "estimator_version": item.estimator_version,
        "created_at": item.created_at,
    }
