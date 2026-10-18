"""Public, tenant-addressed borrower intake endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from dogeapi.deps import SessionDep
from dogeapi.models import AssetCategory, Branch, LoanProduct, Organization
from dogeapi.operations import mvp_service
from dogeapi.operations.mvp_schemas import (
    ActionResult,
    ApplicationCreate,
    AssetCategoryItem,
    BranchItem,
    LoanProductItem,
    PublicIntakeConfig,
)
from dogeapi.settings import get_settings

router = APIRouter(prefix="/public/v1/partners", tags=["privgadai-public-intake"])


async def _partner(session: SessionDep, slug: str) -> Organization:
    partner = await session.scalar(select(Organization).where(Organization.slug == slug))
    if partner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partner not found")
    return partner


@router.get("/{slug}/intake-config", response_model=PublicIntakeConfig)
async def intake_config(slug: str, session: SessionDep) -> PublicIntakeConfig:
    partner = await _partner(session, slug)
    branches = list(
        await session.scalars(select(Branch).where(Branch.org_id == partner.id, Branch.is_active).order_by(Branch.code))
    )
    categories = list(
        await session.scalars(
            select(AssetCategory)
            .where(AssetCategory.org_id == partner.id, AssetCategory.is_active)
            .order_by(AssetCategory.code)
        )
    )
    products = list(
        await session.scalars(
            select(LoanProduct)
            .where(LoanProduct.org_id == partner.id, LoanProduct.is_active)
            .order_by(LoanProduct.code)
        )
    )
    return PublicIntakeConfig(
        partner={"id": partner.id, "slug": partner.slug, "name": partner.name},
        branches=[BranchItem.model_validate(item) for item in branches],
        asset_categories=[AssetCategoryItem.model_validate(item) for item in categories],
        loan_products=[LoanProductItem.model_validate(item) for item in products],
        consent_version="PRIV-2026.1",
    )


@router.post("/{slug}/applications", response_model=ActionResult, status_code=status.HTTP_201_CREATED)
async def public_create_application(slug: str, data: ApplicationCreate, session: SessionDep) -> ActionResult:
    if slug == get_settings().BORROWER_ORG_SLUG:
        raise HTTPException(status.HTTP_410_GONE, "Gunakan akun borrower di /borrower untuk pengajuan baru")
    partner = await _partner(session, slug)
    item = await mvp_service.create_application(session, partner.id, None, data)
    await session.commit()
    return ActionResult(
        id=item.id,
        application_id=item.id,
        status=item.status,
        message="Application submitted to partner",
    )
