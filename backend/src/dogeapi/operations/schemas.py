"""API contracts for the PrivGadai operations dashboard."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BranchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    city: str
    is_active: bool


class OperationsMetrics(BaseModel):
    submitted: int
    under_review: int
    appraisal: int
    offered: int
    accepted: int
    exceptions: int
    requested_amount: float


class ApplicationQueueItem(BaseModel):
    id: UUID
    application_no: str
    borrower_name: str
    phone_masked: str
    branch_name: str
    branch_code: str
    status: str
    priority: str
    asset_category: str
    asset_label: str
    requested_amount: float
    indicative_value: float | None
    collateral_status: str
    submitted_at: datetime | None


class CollateralStatusItem(BaseModel):
    status: str
    count: int


class ActivityItem(BaseModel):
    id: UUID
    application_id: UUID
    application_no: str
    to_status: str
    note: str | None
    created_at: datetime


class OperationsDashboardResponse(BaseModel):
    generated_at: datetime
    branches: list[BranchSummary]
    metrics: OperationsMetrics
    work_queue: list[ApplicationQueueItem]
    collateral: list[CollateralStatusItem]
    recent_activity: list[ActivityItem]
