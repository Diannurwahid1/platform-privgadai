"""Private PaddleOCR HTTP service used by PrivGadai."""

from __future__ import annotations

import asyncio
import os
import re
import secrets
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status

# Paddle's oneDNN executor currently fails on some Windows CPU builds for the
# official OCR model. The plain CPU executor is slower but stable for local KYC.
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

app = FastAPI(title="PrivGadai KTP OCR", version="0.1.0", docs_url=None, redoc_url=None)


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    expected = os.getenv("OCR_API_KEY", "")
    if expected and (not x_api_key or not secrets.compare_digest(expected, x_api_key)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key OCR tidak valid")


@lru_cache(maxsize=1)
def _engine() -> Any:
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise RuntimeError("PaddleOCR belum terpasang") from exc
    return PaddleOCR(
        lang=os.getenv("OCR_LANGUAGE", "id"),
        enable_mkldnn=False,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def _extract_lines(result: Any) -> tuple[list[str], list[float]]:
    texts: list[str] = []
    scores: list[float] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("rec_texts"), list):
                texts.extend(str(item) for item in value["rec_texts"] if str(item).strip())
                raw_scores = value.get("rec_scores", [])
                scores.extend(float(item) for item in raw_scores if isinstance(item, (int, float)))
                return
            for nested in value.values():
                visit(nested)
        elif isinstance(value, (list, tuple)):
            # PaddleOCR 2.x line: [box, (text, confidence)]
            if len(value) == 2 and isinstance(value[1], (list, tuple)) and len(value[1]) >= 2:
                text, score = value[1][0], value[1][1]
                if isinstance(text, str) and isinstance(score, (int, float)):
                    texts.append(text)
                    scores.append(float(score))
                    return
            for nested in value:
                visit(nested)
        else:
            json_value = getattr(value, "json", None)
            if json_value is not None:
                visit(json_value() if callable(json_value) else json_value)

    visit(result)
    return texts, scores


def _value_after_label(line: str, labels: tuple[str, ...]) -> str | None:
    normalized = " ".join(line.upper().replace("：", ":").split())
    for label in labels:
        match = re.match(rf"^{re.escape(label)}\s*:?[\s-]*(.+)$", normalized)
        if match and match.group(1).strip():
            return match.group(1).strip(" :-")
    return None


def _field_value(lines: list[str], index: int, labels: tuple[str, ...]) -> str | None:
    value = _value_after_label(lines[index], labels)
    if value:
        return value
    normalized = " ".join(lines[index].upper().replace("：", ":").split()).strip(" :")
    if normalized in labels and index + 1 < len(lines):
        return lines[index + 1].strip(" :-") or None
    return None


def parse_ktp(lines: list[str], scores: list[float] | None = None) -> dict[str, object]:
    clean = [" ".join(line.strip().split()) for line in lines if line.strip()]
    result: dict[str, object] = {}
    for index, line in enumerate(clean):
        digits = re.sub(r"\D", "", line)
        if "nik" in line.lower() and len(digits) >= 16:
            result["nik"] = digits[-16:]
        elif "nik" not in result and re.fullmatch(r"\d{16}", digits):
            result["nik"] = digits

        name = _field_value(clean, index, ("NAMA", "NAME"))
        if name:
            result["nama"] = name

        born = _field_value(clean, index, ("TEMPAT/TGL LAHIR", "TEMPAT TGL LAHIR", "TEMPAT, TGL LAHIR"))
        if born:
            date_match = re.search(r"(\d{2}[-/]\d{2}[-/]\d{4})", born)
            if date_match:
                result["tanggal_lahir"] = date_match.group(1).replace("/", "-")
                result["tempat_lahir"] = born[: date_match.start()].strip(" ,-:")

        mappings = (
            (("ALAMAT",), "alamat"),
            (("PROVINSI",), "provinsi"),
            (("KABUPATEN/KOTA", "KABUPATEN", "KOTA"), "kabupaten_kota"),
            (("JENIS KELAMIN",), "jenis_kelamin"),
            (("PEKERJAAN",), "pekerjaan"),
            (("KEWARGANEGARAAN",), "kewarganegaraan"),
            (("STATUS PERKAWINAN",), "status_perkawinan"),
        )
        for labels, key in mappings:
            value = _field_value(clean, index, labels)
            if value:
                result[key] = value

    if scores:
        result["confidence"] = round(sum(scores) / len(scores), 4)
    result["message"] = "KTP berhasil diekstrak" if result else "Field KTP tidak ditemukan"
    return result


def _run_ocr(path: str) -> tuple[list[str], list[float]]:
    engine = _engine()
    if hasattr(engine, "predict"):
        return _extract_lines(engine.predict(input=path))
    return _extract_lines(engine.ocr(path, cls=True))


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "engine": "paddleocr"}


@app.post("/scan/ktp", dependencies=[Depends(require_api_key)])
async def scan_ktp(file: Annotated[UploadFile, File()]) -> dict[str, object]:
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Gunakan foto JPG, PNG, atau WebP")
    content = await file.read(MAX_FILE_BYTES + 1)
    if not content or len(content) > MAX_FILE_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Ukuran foto KTP maksimal 10 MB")
    suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[content_type]
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary.write(content)
            temp_path = temporary.name
        lines, scores = await asyncio.to_thread(_run_ocr, temp_path)
        extracted = parse_ktp(lines, scores)
        if not extracted.get("nik"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "NIK tidak terbaca dari foto KTP")
        return {"request_id": secrets.token_hex(12), "data": extracted}
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

