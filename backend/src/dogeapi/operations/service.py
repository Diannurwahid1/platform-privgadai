"""Tenant-scoped dashboard queries for partner operations."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    ApplicationStatusHistory,
    Asset,
    Borrower,
    Branch,
    Cashbox,
    CustodyLocation,
    LoanApplication,
    StaffAssignment,
)
from dogeapi.operations.schemas import (
    ActivityItem,
    ApplicationQueueItem,
    BranchOverviewItem,
    BranchSummary,
    CollateralStatusItem,
    OperationsDashboardResponse,
    OperationsMetrics,
)


async def list_branch_overview(
    session: AsyncSession, org_id: UUID, *, branch_ids: set[UUID] | None = None
) -> list[BranchOverviewItem]:
    query = select(Branch).where(Branch.org_id == org_id).order_by(Branch.code)
    if branch_ids is not None:
        query = query.where(Branch.id.in_(branch_ids))
    branches = (await session.scalars(query)).all()
    result: list[BranchOverviewItem] = []
    for branch in branches:
        application_count, requested_amount = (
            await session.execute(
                select(
                    func.count(LoanApplication.id),
                    func.coalesce(func.sum(LoanApplication.requested_amount), Decimal("0")),
                ).where(LoanApplication.org_id == org_id, LoanApplication.branch_id == branch.id)
            )
        ).one()
        staff_count = await session.scalar(
            select(func.count(StaffAssignment.id)).where(
                StaffAssignment.org_id == org_id,
                StaffAssignment.branch_id == branch.id,
                StaffAssignment.is_active,
            )
        )
        cashbox_count = await session.scalar(
            select(func.count(Cashbox.id)).where(Cashbox.org_id == org_id, Cashbox.branch_id == branch.id)
        )
        custody_location_count = await session.scalar(
            select(func.count(CustodyLocation.id)).where(
                CustodyLocation.org_id == org_id, CustodyLocation.branch_id == branch.id
            )
        )
        result.append(
            BranchOverviewItem(
                id=branch.id,
                code=branch.code,
                name=branch.name,
                city=branch.city,
                address=branch.address,
                is_active=branch.is_active,
                application_count=int(application_count),
                requested_amount=float(requested_amount),
                staff_count=int(staff_count or 0),
                cashbox_count=int(cashbox_count or 0),
                custody_location_count=int(custody_location_count or 0),
            )
        )
    return result


async def list_application_queue(
    session: AsyncSession,
    org_id: UUID,
    *,
    limit: int = 20,
    branch_ids: set[UUID] | None = None,
    branch_id: UUID | None = None,
) -> list[ApplicationQueueItem]:
    statement = (
        select(LoanApplication, Borrower, Branch, Asset)
        .join(Borrower, Borrower.id == LoanApplication.borrower_id)
        .join(Branch, Branch.id == LoanApplication.branch_id)
        .join(Asset, Asset.application_id == LoanApplication.id)
        .where(
            LoanApplication.org_id == org_id,
            Borrower.org_id == org_id,
            Branch.org_id == org_id,
            Asset.org_id == org_id,
        )
        .order_by(LoanApplication.submitted_at.desc().nullslast(), LoanApplication.created_at.desc())
        .limit(limit)
    )
    if branch_ids is not None:
        statement = statement.where(LoanApplication.branch_id.in_(branch_ids))
    if branch_id is not None:
        statement = statement.where(LoanApplication.branch_id == branch_id)
    rows = (await session.execute(statement)).all()
    return [
        ApplicationQueueItem(
            id=application.id,
            application_no=application.application_no,
            borrower_name=borrower.full_name,
            phone_masked=borrower.phone_masked,
            branch_name=branch.name,
            branch_code=branch.code,
            status=application.status,
            priority=application.priority,
            asset_category=application.asset_category,
            asset_label=" ".join(part for part in (asset.brand, asset.model) if part) or asset.category,
            requested_amount=float(application.requested_amount),
            indicative_value=float(asset.indicative_value) if asset.indicative_value is not None else None,
            collateral_status=asset.collateral_status,
            submitted_at=application.submitted_at,
        )
        for application, borrower, branch, asset in rows
    ]


async def get_operations_dashboard(
    session: AsyncSession, org_id: UUID, *, branch_ids: set[UUID] | None = None
) -> OperationsDashboardResponse:
    branch_query = select(Branch).where(Branch.org_id == org_id)
    if branch_ids is not None:
        branch_query = branch_query.where(Branch.id.in_(branch_ids))
    branches = (await session.scalars(branch_query.order_by(Branch.code))).all()

    status_query = select(LoanApplication.status, func.count(LoanApplication.id)).where(
        LoanApplication.org_id == org_id
    )
    if branch_ids is not None:
        status_query = status_query.where(LoanApplication.branch_id.in_(branch_ids))
    status_rows = (await session.execute(status_query.group_by(LoanApplication.status))).all()
    status_counts = {status: int(count) for status, count in status_rows}

    amount_query = select(func.coalesce(func.sum(LoanApplication.requested_amount), Decimal("0"))).where(
        LoanApplication.org_id == org_id,
        LoanApplication.status != "draft",
    )
    if branch_ids is not None:
        amount_query = amount_query.where(LoanApplication.branch_id.in_(branch_ids))
    requested_amount = await session.scalar(amount_query)

    collateral_query = (
        select(Asset.collateral_status, func.count(Asset.id))
        .join(LoanApplication, LoanApplication.id == Asset.application_id)
        .where(Asset.org_id == org_id, LoanApplication.org_id == org_id)
    )
    if branch_ids is not None:
        collateral_query = collateral_query.where(LoanApplication.branch_id.in_(branch_ids))
    collateral_rows = (
        await session.execute(collateral_query.group_by(Asset.collateral_status).order_by(Asset.collateral_status))
    ).all()

    activity_query = (
        select(ApplicationStatusHistory, LoanApplication.application_no)
        .join(LoanApplication, LoanApplication.id == ApplicationStatusHistory.application_id)
        .where(
            ApplicationStatusHistory.org_id == org_id,
            LoanApplication.org_id == org_id,
        )
    )
    if branch_ids is not None:
        activity_query = activity_query.where(LoanApplication.branch_id.in_(branch_ids))
    activity_rows = (
        await session.execute(activity_query.order_by(ApplicationStatusHistory.created_at.desc()).limit(8))
    ).all()

    return OperationsDashboardResponse(
        generated_at=datetime.now(UTC),
        branches=[BranchSummary.model_validate(branch) for branch in branches],
        metrics=OperationsMetrics(
            submitted=status_counts.get("submitted", 0),
            under_review=status_counts.get("under_review", 0),
            appraisal=status_counts.get("appraisal", 0),
            offered=status_counts.get("offered", 0),
            accepted=status_counts.get("accepted", 0),
            exceptions=sum(status_counts.get(status, 0) for status in ("rejected", "cancelled", "incident_hold")),
            requested_amount=float(requested_amount or 0),
        ),
        work_queue=await list_application_queue(session, org_id, limit=8, branch_ids=branch_ids),
        collateral=[CollateralStatusItem(status=status, count=int(count)) for status, count in collateral_rows],
        recent_activity=[
            ActivityItem(
                id=history.id,
                application_id=history.application_id,
                application_no=application_no,
                to_status=history.to_status,
                note=history.note,
                created_at=history.created_at,
            )
            for history, application_no in activity_rows
        ],
    )
