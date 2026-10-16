"""Content inspection and malware scanning for private operational evidence."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dogeapi.settings import Settings


@dataclass(frozen=True)
class FileScanResult:
    status: str
    engine: str
    detail: str
    detected_content_type: str | None


_EICAR_MARKER = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
_PDF_ACTIVE_MARKERS = (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile")


def detect_content_type(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    return None


async def scan_upload(content: bytes, declared_content_type: str, settings: Settings) -> FileScanResult:
    """Fail closed on type spoofing and known malicious/active payloads.

    Production can select ClamAV. The built-in engine remains useful for local
    development and deterministic tests, but production settings reject it.
    """
    detected = detect_content_type(content)
    if detected is None or detected != declared_content_type:
        return FileScanResult("quarantined", "content-guard-v1", "File signature does not match MIME type", detected)
    if _EICAR_MARKER in content:
        return FileScanResult("quarantined", "content-guard-v1", "EICAR test signature detected", detected)
    if detected == "application/pdf" and any(marker in content for marker in _PDF_ACTIVE_MARKERS):
        return FileScanResult(
            "quarantined", "content-guard-v1", "Active or embedded PDF content is not allowed", detected
        )
    if settings.MALWARE_SCANNER_MODE == "clamav":
        return await _scan_with_clamav(content, detected, settings)
    return FileScanResult("clean", "content-guard-v1", "Signature and active-content checks passed", detected)


async def _scan_with_clamav(content: bytes, detected: str, settings: Settings) -> FileScanResult:
    executable = shutil.which(settings.CLAMAV_EXECUTABLE)
    if executable is None:
        return FileScanResult("scan_failed", "clamav", "ClamAV executable is unavailable", detected)

    def run() -> tuple[int, str]:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(content)
            path = Path(handle.name)
        try:
            completed = subprocess.run(
                [executable, "--no-summary", str(path)],
                capture_output=True,
                text=True,
                timeout=settings.MALWARE_SCAN_TIMEOUT_SECONDS,
                check=False,
            )
            return completed.returncode, (completed.stdout or completed.stderr).strip()[-500:]
        finally:
            path.unlink(missing_ok=True)

    try:
        code, output = await asyncio.to_thread(run)
    except subprocess.TimeoutExpired:
        return FileScanResult("scan_failed", "clamav", "ClamAV scan timed out", detected)
    if code == 0:
        return FileScanResult("clean", "clamav", output or "No malware detected", detected)
    if code == 1:
        return FileScanResult("quarantined", "clamav", output or "Malware detected", detected)
    return FileScanResult("scan_failed", "clamav", output or "ClamAV scan failed", detected)
