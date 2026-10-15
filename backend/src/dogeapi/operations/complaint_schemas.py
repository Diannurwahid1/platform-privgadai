"""Contracts for customer complaint and support cases."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ComplaintCreate(BaseModel):
    branch_id: UUID
    borrower_id: UUID
    application_id: UUID | None = None
    category: str = Field(pattern="^(service|billing|appraisal|custody|privacy|collection|fraud|other)$")
    channel: str = Field(pattern="^(branch|phone|email|web|whatsapp|regulator)$")
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    subject: str = Field(min_length=5, max_length=240)
    description: str = Field(min_length=10, max_length=6000)
    vulnerable_customer: bool = False
    regulator_reportable: bool = False


class ComplaintAssign(BaseModel):
    assigned_to_user_id: UUID
    reason: str = Field(min_length=5, max_length=1000)


class ComplaintCommunication(BaseModel):
    direction: str = Field(pattern="^(inbound|outbound|internal)$")
    channel: str = Field(pattern="^(branch|phone|email|web|whatsapp|letter|regulator|internal)$")
    message: str = Field(min_length=3, max_length=6000)


class ComplaintResolution(BaseModel):
    resolution_summary: str = Field(min_length=10, max_length=6000)
    outcome: str = Field(pattern="^(upheld|partially_upheld|not_upheld|withdrawn|duplicate)$")
    compensation_amount: Decimal = Field(default=0, ge=0)


class ComplaintReopen(BaseModel):
    reason: str = Field(min_length=10, max_length=4000)
