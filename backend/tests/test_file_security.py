"""File signature, malware quarantine, and production scanner controls."""

from __future__ import annotations

import pytest

from dogeapi.file_security import scan_upload
from dogeapi.settings import Settings


async def test_builtin_scanner_accepts_matching_image_and_quarantines_eicar(settings: Settings) -> None:
    clean = await scan_upload(b"\x89PNG\r\n\x1a\nclean-image", "image/png", settings)
    assert clean.status == "clean"
    assert clean.detected_content_type == "image/png"

    eicar = b"\x89PNG\r\n\x1a\nX5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    infected = await scan_upload(eicar, "image/png", settings)
    assert infected.status == "quarantined"
    assert "EICAR" in infected.detail


async def test_builtin_scanner_rejects_mime_spoof_and_active_pdf(settings: Settings) -> None:
    spoofed = await scan_upload(b"%PDF-1.7\ncontent", "image/jpeg", settings)
    assert spoofed.status == "quarantined"
    assert "MIME" in spoofed.detail

    active_pdf = await scan_upload(b"%PDF-1.7\n/JavaScript malicious", "application/pdf", settings)
    assert active_pdf.status == "quarantined"
    assert "Active" in active_pdf.detail


def test_production_requires_external_malware_scanner() -> None:
    with pytest.raises(ValueError, match="MALWARE_SCANNER_MODE=clamav"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="production-secret-that-is-longer-than-thirty-two-characters",
            JWT_COOKIE_SECURE=True,
            PII_ENCRYPTION_KEY="production-pii-key",
            BUILD_SHA="release-2026-10-16",
            MALWARE_SCANNER_MODE="builtin",
        )
