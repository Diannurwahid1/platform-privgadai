"""API contracts for customer identity verification."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class KycCreate(BaseModel):
    nik: str = Field(pattern=r"^\d{16}$")
    legal_name: str = Field(min_length=3, max_length=180)
    birth_place: str = Field(min_length=2, max_length=100)
    birth_date: date
    gender: str = Field(pattern="^(male|female)$")
    address: str = Field(min_length=8, max_length=1000)
    province: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    occupation: str | None = Field(default=None, max_length=120)
    verification_method: str = Field(default="ocr_internal", pattern="^(manual_branch|ocr_internal|electronic_provider)$")
    provider_name: str | None = Field(default=None, max_length=80)
    provider_reference: str | None = Field(default=None, max_length=120)

    @field_validator("legal_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.upper().split())


class KycReview(BaseModel):
    decision: str = Field(pattern="^(verified|rejected|needs_information)$")
    reason: str = Field(min_length=5, max_length=2000)
    risk_level: str = Field(default="standard", pattern="^(low|standard|high|enhanced)$")
    face_match_score: float | None = Field(default=None, ge=0, le=100)
    liveness_score: float | None = Field(default=None, ge=0, le=100)
    document_authenticity_score: float | None = Field(default=None, ge=0, le=100)
    pep_match: bool = False
    sanctions_match: bool = False
