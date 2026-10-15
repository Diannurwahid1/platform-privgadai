"""Contracts for operational exception and incident cases."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentTriage(BaseModel):
    assigned_to_user_id: UUID
    due_at: datetime
    root_cause: str = Field(min_length=5, max_length=4000)
    action_plan: str = Field(min_length=5, max_length=4000)


class IncidentNoteCreate(BaseModel):
    note: str = Field(min_length=3, max_length=4000)


class IncidentResolutionRequest(BaseModel):
    resolution_note: str = Field(min_length=10, max_length=4000)


class IncidentReopen(BaseModel):
    reason: str = Field(min_length=10, max_length=4000)
