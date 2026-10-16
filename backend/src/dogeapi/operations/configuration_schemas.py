"""Contracts for versioned tenant configuration."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ConfigurationCreate(BaseModel):
    domain: str = Field(
        pattern="^(institution|product|pricing|appraisal|workflow|custody|document|accounting|regulatory|access|integration|notification|security)$"
    )
    config_key: str = Field(min_length=2, max_length=80, pattern="^[a-z0-9][a-z0-9_.-]+$")
    effective_from: datetime
    payload: dict[str, object]
    change_summary: str = Field(min_length=10, max_length=2000)

    @field_validator("payload")
    @classmethod
    def payload_not_empty(cls, value: dict[str, object]) -> dict[str, object]:
        if not value:
            raise ValueError("payload konfigurasi tidak boleh kosong")
        return value


class ConfigurationSubmit(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


class ConfigurationClone(BaseModel):
    effective_from: datetime
    change_summary: str = Field(min_length=10, max_length=2000)


class ConfigurationUpdateDraft(BaseModel):
    effective_from: datetime
    payload: dict[str, object]
    change_summary: str = Field(min_length=10, max_length=2000)

    @field_validator("payload")
    @classmethod
    def payload_not_empty(cls, value: dict[str, object]) -> dict[str, object]:
        if not value:
            raise ValueError("payload konfigurasi tidak boleh kosong")
        return value


class ConfigurationIdResult(BaseModel):
    id: UUID
    status: str
    message: str
