"""Contracts for four-eyes approvals."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str = Field(min_length=5, max_length=2000)


class ApprovalDelegationCreate(BaseModel):
    delegator_user_id: UUID
    delegate_user_id: UUID
    branch_id: UUID | None = None
    assigned_role: str = Field(min_length=2, max_length=40)
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(min_length=10, max_length=2000)

    @model_validator(mode="after")
    def validate_window(self) -> "ApprovalDelegationCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at harus setelah starts_at")
        return self
