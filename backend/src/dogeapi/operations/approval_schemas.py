"""Contracts for four-eyes approvals."""

from pydantic import BaseModel, Field


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str = Field(min_length=5, max_length=2000)
