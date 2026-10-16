from __future__ import annotations

import pytest
from pydantic import ValidationError

from dogeapi.settings import Settings


def test_production_rejects_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(APP_ENV="production", JWT_SECRET_KEY="change-me")


def test_production_requires_secure_cookies() -> None:
    with pytest.raises(ValidationError, match="JWT_COOKIE_SECURE"):
        Settings(APP_ENV="production", JWT_SECRET_KEY="x" * 40, JWT_COOKIE_SECURE=False)


def test_production_accepts_hardened_core_settings() -> None:
    settings = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="x" * 40,
        JWT_COOKIE_SECURE=True,
        PII_ENCRYPTION_KEY="production-fernet-key",
        BUILD_SHA="release-2026.10.16",
        MALWARE_SCANNER_MODE="clamav",
    )

    assert settings.is_production is True


def test_production_requires_release_identity() -> None:
    with pytest.raises(ValidationError, match="BUILD_SHA"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="x" * 40,
            JWT_COOKIE_SECURE=True,
            PII_ENCRYPTION_KEY="production-fernet-key",
        )


def test_enabled_integrations_require_secrets_outside_tests() -> None:
    with pytest.raises(ValidationError, match="LLM_GATEWAY_API_KEY"):
        Settings(
            APP_ENV="development",
            JWT_SECRET_KEY="x" * 40,
            TOKEN_STORE_BACKEND="redis",
            FEATURE_AI_CHAT=True,
        )
