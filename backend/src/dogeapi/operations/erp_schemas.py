"""Contracts for the V3.1 pawn ERP operational modules."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CashboxFundInput(BaseModel):
    amount: Decimal = Field(gt=0)
    external_reference: str = Field(min_length=3, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=100)


class TellerSessionOpen(BaseModel):
    cashbox_id: UUID


class TellerSessionClose(BaseModel):
    actual_closing_balance: Decimal = Field(ge=0)
    variance_reason: str | None = Field(default=None, min_length=5, max_length=1000)


class JournalReverseInput(BaseModel):
    reason: str = Field(min_length=5, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=100)


class ApprovalSubmitInput(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class AccountingPeriodCreate(BaseModel):
    period_start: date
    period_end: date


class CollectionNoteCreate(BaseModel):
    channel: str = Field(pattern="^(phone|whatsapp|visit|branch|email)$")
    note: str = Field(min_length=3, max_length=4000)
    outcome: str = Field(min_length=2, max_length=32)
    next_action_at: datetime | None = None


class CollectionCasePlanUpdate(BaseModel):
    strategy: str = Field(pattern="^(reminder|negotiation|field_visit|legal_review|collateral_resolution)$")
    stage: str = Field(pattern="^(soft_collection|intensive_collection|pre_legal|legal|resolved)$")
    next_action_at: datetime


class CollectionPromiseCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    promised_at: datetime
    channel: str = Field(pattern="^(phone|whatsapp|visit|branch|email)$")
    note: str = Field(min_length=5, max_length=2000)


class CollectionPromiseResolve(BaseModel):
    status: str = Field(pattern="^(kept|broken|cancelled)$")
    reason: str = Field(min_length=5, max_length=2000)


class RegulatoryTemplateCreate(BaseModel):
    report_type: str = Field(pattern="^(OJK|SLIK)$")
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=3, max_length=180)
    version: str = Field(min_length=1, max_length=32)
    effective_from: date
    mapping_schema: dict[str, object] = Field(default_factory=dict)
    validation_rules: list[dict[str, object]] = Field(default_factory=list)


class RegulatoryRunCreate(BaseModel):
    template_id: UUID
    period_start: date
    period_end: date


class InventoryCheckCreate(BaseModel):
    location_id: UUID


class InventoryObservation(BaseModel):
    application_id: UUID
    observed_status: str = Field(min_length=2, max_length=32)
    note: str | None = Field(default=None, max_length=2000)


class InventoryCheckSubmit(BaseModel):
    observations: list[InventoryObservation] = Field(min_length=1)


class FinanceOverview(BaseModel):
    cash_balance: Decimal
    active_loan_count: int
    outstanding_principal: Decimal
    outstanding_fee: Decimal
    payment_today: Decimal
    open_teller_sessions: int
    recent_transactions: list[dict[str, object]]


class FinancialReports(BaseModel):
    trial_balance: list[dict[str, object]]
    loan_portfolio: dict[str, object]
    aging: list[dict[str, object]]
    branch_analytics: list[dict[str, object]]


class ERPActionResult(BaseModel):
    id: UUID
    status: str
    message: str
