"""Contracts for payment allocation, adjustments, and reconciliation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PaymentCreate(BaseModel):
    loan_account_id: UUID
    amount: Decimal = Field(gt=0)
    channel: str = Field(pattern="^(cash|bank_transfer|virtual_account|debit_card|other)$")
    external_reference: str = Field(min_length=3, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=100)


class PaymentAdjustmentCreate(BaseModel):
    loan_account_id: UUID
    payment_receipt_id: UUID | None = None
    adjustment_type: str = Field(pattern="^(waiver|refund|payment_reversal|debit_adjustment|credit_adjustment)$")
    component: str = Field(pattern="^(principal|fee|allocation)$")
    amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=10, max_length=2000)
    external_reference: str = Field(min_length=3, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=100)

    @model_validator(mode="after")
    def validate_receipt_link(self) -> PaymentAdjustmentCreate:
        requires_receipt = self.adjustment_type in {"refund", "payment_reversal"}
        if requires_receipt and self.payment_receipt_id is None:
            raise ValueError("refund dan payment reversal wajib merujuk receipt")
        if requires_receipt and self.component != "allocation":
            raise ValueError("refund dan payment reversal memakai component allocation")
        if not requires_receipt and self.component == "allocation":
            raise ValueError("component allocation hanya untuk refund atau reversal")
        return self


class ReconciliationCreate(BaseModel):
    scope: str = Field(pattern="^(cash_gl|loan_subledger_gl|bank_statement)$")
    business_date: date
    branch_id: UUID | None = None
    observed_amount: Decimal | None = Field(default=None, ge=0)
    tolerance_amount: Decimal = Field(default=Decimal("0"), ge=0)
    statement_reference: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def bank_requires_observed(self) -> ReconciliationCreate:
        if self.scope == "bank_statement" and self.observed_amount is None:
            raise ValueError("bank statement reconciliation memerlukan observed_amount")
        return self


class ReconciliationResolve(BaseModel):
    resolution_note: str = Field(min_length=10, max_length=2000)


class PaymentActionResult(BaseModel):
    id: UUID
    status: str
    message: str
