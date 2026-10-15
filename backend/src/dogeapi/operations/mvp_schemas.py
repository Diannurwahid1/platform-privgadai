"""Pydantic contracts for PrivGadai master data and workflow actions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BranchCreate(BaseModel):
    code: str = Field(min_length=2, max_length=24)
    name: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=100)
    address: str | None = None


class AssetCategoryCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    requires_serial_number: bool = False


class LoanProductCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=140)
    min_amount: Decimal = Field(gt=0)
    max_amount: Decimal = Field(gt=0)
    max_ltv_percent: Decimal = Field(gt=0, le=100)
    allowed_tenors_days: list[int] = Field(min_length=1)
    service_fee_percent: Decimal = Field(ge=0, le=100)
    agreement_type: str = Field(default="pawn", pattern="^(pawn|fiduciary)$")
    fee_rules: dict[str, object] = Field(default_factory=dict)
    approval_policy: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_amounts(self) -> LoanProductCreate:
        if self.max_amount < self.min_amount:
            raise ValueError("max_amount must be greater than or equal to min_amount")
        if any(day <= 0 for day in self.allowed_tenors_days):
            raise ValueError("allowed_tenors_days must contain positive values")
        return self


class StaffAssignmentCreate(BaseModel):
    user_id: UUID
    branch_id: UUID
    operational_role: str = Field(
        pattern="^(ops_admin|branch_manager|loan_officer|reviewer|appraiser|field_agent|custodian|finance|auditor)$"
    )


class MasterItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    is_active: bool


class BranchItem(MasterItem):
    city: str
    address: str | None


class AssetCategoryItem(MasterItem):
    description: str | None
    requires_serial_number: bool


class LoanProductItem(MasterItem):
    min_amount: Decimal
    max_amount: Decimal
    max_ltv_percent: Decimal
    allowed_tenors_days: list[int]
    service_fee_percent: Decimal
    agreement_type: str
    fee_rules: dict[str, object]
    approval_policy: dict[str, object]


class StaffAssignmentItem(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    branch_id: UUID
    branch_name: str
    operational_role: str
    is_active: bool


class BorrowerInput(BaseModel):
    customer_reference: str | None = Field(default=None, max_length=32)
    full_name: str = Field(min_length=2, max_length=180)
    phone: str = Field(min_length=8, max_length=24)


class AssetInput(BaseModel):
    category_code: str = Field(min_length=2, max_length=40)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=120)
    condition_grade: str | None = Field(default=None, max_length=24)
    indicative_value: Decimal | None = Field(default=None, gt=0)


class ApplicationCreate(BaseModel):
    branch_id: UUID
    product_id: UUID
    borrower: BorrowerInput
    asset: AssetInput
    requested_amount: Decimal = Field(gt=0)
    requested_tenor_days: int = Field(gt=0)
    purpose: str | None = Field(default=None, max_length=1000)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    consent_document_version: str = Field(min_length=1, max_length=32)
    submit: bool = True


class TransitionInput(BaseModel):
    to_status: str = Field(min_length=2, max_length=32)
    note: str | None = Field(default=None, max_length=1000)


class EvidenceCreate(BaseModel):
    evidence_type: str = Field(min_length=2, max_length=40)
    file_name: str = Field(min_length=1, max_length=255)
    object_key: str = Field(min_length=1, max_length=500)
    content_type: str = Field(min_length=3, max_length=100)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern="^[a-fA-F0-9]{64}$")


class AppraisalCreate(BaseModel):
    application_id: UUID
    market_value: Decimal = Field(gt=0)
    liquidation_value: Decimal = Field(gt=0)
    recommended_loan: Decimal = Field(gt=0)
    condition_grade: str = Field(min_length=1, max_length=24)
    rationale: str = Field(min_length=5, max_length=4000)


class OfferCreate(BaseModel):
    application_id: UUID
    principal_amount: Decimal = Field(gt=0)
    tenor_days: int = Field(gt=0)
    service_fee_amount: Decimal = Field(ge=0)
    expires_at: datetime
    agreement_version: str = Field(min_length=1, max_length=32)


class AcceptanceCreate(BaseModel):
    channel: str = Field(default="web", pattern="^(web|mobile|branch)$")
    ip_address: str | None = Field(default=None, max_length=64)


class PickupCreate(BaseModel):
    application_id: UUID
    assigned_user_id: UUID | None = None
    scheduled_at: datetime | None = None
    pickup_address: str = Field(min_length=5, max_length=2000)


class PickupTransition(BaseModel):
    to_status: str = Field(pattern="^(in_transit|received|incident_hold)$")
    condition_note: str | None = Field(default=None, max_length=2000)


class CustodyEventCreate(BaseModel):
    application_id: UUID
    location_id: UUID
    event_type: str = Field(pattern="^(stored|incident_hold|release_authorized|returned)$")
    condition_note: str | None = Field(default=None, max_length=2000)


class CustodyMovementCreate(BaseModel):
    application_id: UUID
    to_location_id: UUID
    reason: str = Field(min_length=5, max_length=2000)


class CustodyMovementDispatch(BaseModel):
    seal_out: str = Field(min_length=3, max_length=80)
    note: str = Field(min_length=3, max_length=2000)


class CustodyMovementReceive(BaseModel):
    seal_in: str = Field(min_length=3, max_length=80)
    note: str = Field(min_length=3, max_length=2000)


class CustodyLocationCreate(BaseModel):
    branch_id: UUID
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=140)
    location_type: str = Field(pattern="^(branch_vault|central_vault|temporary)$")


class DisbursementCreate(BaseModel):
    external_reference: str = Field(min_length=3, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=100)


class SettlementCreate(BaseModel):
    application_id: UUID
    settlement_type: str = Field(pattern="^(repayment|auction|insurance)$")
    external_reference: str = Field(min_length=3, max_length=100)
    amount: Decimal = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=100)


class IncidentCreate(BaseModel):
    application_id: UUID
    incident_type: str = Field(min_length=2, max_length=40)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    description: str = Field(min_length=5, max_length=4000)


class ActionResult(BaseModel):
    id: UUID
    application_id: UUID
    status: str
    message: str


class ApplicationDetail(BaseModel):
    id: UUID
    application_no: str
    status: str
    priority: str
    branch: dict[str, object]
    product: dict[str, object] | None
    borrower: dict[str, object]
    asset: dict[str, object]
    requested_amount: Decimal
    requested_tenor_days: int | None
    purpose: str | None
    submitted_at: datetime | None
    evidence: list[dict[str, object]]
    appraisals: list[dict[str, object]]
    offers: list[dict[str, object]]
    pickup: dict[str, object] | None
    loan: dict[str, object] | None
    incidents: list[dict[str, object]]
    history: list[dict[str, object]]


class CollateralTimeline(BaseModel):
    application_id: UUID
    application_no: str
    asset_code: str
    collateral_status: str
    events: list[dict[str, object]]


class PublicIntakeConfig(BaseModel):
    partner: dict[str, object]
    branches: list[BranchItem]
    asset_categories: list[AssetCategoryItem]
    loan_products: list[LoanProductItem]
    consent_version: str


class FieldTaskItem(BaseModel):
    id: UUID
    application_id: UUID
    application_no: str
    assignment_code: str
    status: str
    scheduled_at: datetime | None
    pickup_address: str
    borrower_name: str
    phone_masked: str
    asset_label: str
    branch_name: str
