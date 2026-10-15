"""Generic maker-checker approval workflow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    AccountingPeriod,
    ApprovalEvent,
    ApprovalRequest,
    Asset,
    CollateralEvent,
    CustodyEvent,
    HumanAppraisal,
    InventoryCheck,
    Membership,
    RegulatoryReportRun,
    StaffAssignment,
)


async def request_approval(
    session: AsyncSession,
    *,
    org_id: UUID,
    branch_id: UUID | None,
    aggregate_type: str,
    aggregate_id: UUID,
    aggregate_reference: str,
    action: str,
    requested_by: UUID,
    assigned_role: str,
    reason: str,
    payload: dict[str, object],
    priority: str = "normal",
    sla_hours: int = 8,
) -> ApprovalRequest:
    pending = await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.org_id == org_id,
            ApprovalRequest.aggregate_type == aggregate_type,
            ApprovalRequest.aggregate_id == aggregate_id,
            ApprovalRequest.action == action,
            ApprovalRequest.status == "pending",
        )
    )
    if pending is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Permintaan approval yang sama masih menunggu keputusan")
    version = (
        int(
            (
                await session.scalar(
                    select(func.coalesce(func.max(ApprovalRequest.version), 0)).where(
                        ApprovalRequest.org_id == org_id,
                        ApprovalRequest.aggregate_type == aggregate_type,
                        ApprovalRequest.aggregate_id == aggregate_id,
                        ApprovalRequest.action == action,
                    )
                )
            )
            or 0
        )
        + 1
    )
    item = ApprovalRequest(
        org_id=org_id,
        branch_id=branch_id,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        aggregate_reference=aggregate_reference,
        action=action,
        version=version,
        requested_by_user_id=requested_by,
        assigned_role=assigned_role,
        status="pending",
        priority=priority,
        request_reason=reason,
        payload_snapshot=payload,
        due_at=datetime.now(UTC) + timedelta(hours=sla_hours),
    )
    session.add(item)
    await session.flush()
    session.add(
        ApprovalEvent(
            org_id=org_id,
            approval_id=item.id,
            actor_user_id=requested_by,
            event_type="ApprovalRequested",
            to_status="pending",
            reason=reason,
        )
    )
    await session.flush()
    return item


async def decide_approval(
    session: AsyncSession, org_id: UUID, approval_id: UUID, actor_id: UUID, decision: str, reason: str
) -> ApprovalRequest:
    item = await session.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.org_id == org_id, ApprovalRequest.id == approval_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval tidak ditemukan")
    if item.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Approval sudah diputuskan")
    if item.requested_by_user_id == actor_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Maker tidak boleh menjadi checker untuk approval yang sama")
    await _ensure_checker_role(session, item, actor_id)
    previous = item.status
    item.status = decision
    item.decided_by_user_id = actor_id
    item.decided_at = datetime.now(UTC)
    item.decision_reason = reason
    if item.aggregate_type == "appraisal" and item.action == "approve_appraisal":
        appraisal = await session.scalar(
            select(HumanAppraisal)
            .where(HumanAppraisal.org_id == org_id, HumanAppraisal.id == item.aggregate_id)
            .with_for_update()
        )
        if appraisal is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Appraisal approval target tidak ditemukan")
        appraisal.status = "final" if decision == "approved" else "rejected"
    elif item.aggregate_type == "inventory_check" and item.action == "approve_inventory_check":
        inventory = await session.scalar(
            select(InventoryCheck)
            .where(InventoryCheck.org_id == org_id, InventoryCheck.id == item.aggregate_id)
            .with_for_update()
        )
        if inventory is None or inventory.status != "submitted":
            raise HTTPException(status.HTTP_409_CONFLICT, "Stock opname target tidak siap diputuskan")
        inventory.reviewed_by_user_id = actor_id
        inventory.approved_at = datetime.now(UTC)
        inventory.status = "approved" if decision == "approved" else "rejected"
    elif item.aggregate_type == "custody_release" and item.action == "authorize_collateral_release":
        await _decide_custody_release(session, item, actor_id, decision)
    elif item.aggregate_type == "journal_entry" and item.action == "reverse_journal":
        if decision == "approved":
            from dogeapi.operations import erp_service

            await erp_service.reverse_journal(
                session,
                org_id,
                actor_id,
                item.aggregate_id,
                str(item.payload_snapshot["reason"]),
                str(item.payload_snapshot["idempotency_key"]),
            )
    elif item.aggregate_type == "regulatory_report" and item.action == "sign_off_regulatory_report":
        report = await session.scalar(
            select(RegulatoryReportRun)
            .where(RegulatoryReportRun.org_id == org_id, RegulatoryReportRun.id == item.aggregate_id)
            .with_for_update()
        )
        if report is None or report.status != "pending_approval":
            raise HTTPException(status.HTTP_409_CONFLICT, "Laporan regulator tidak siap diputuskan")
        report.status = "approved" if decision == "approved" else "rejected"
        if decision == "approved":
            report.approved_by_user_id = actor_id
            report.approved_at = datetime.now(UTC)
    elif item.aggregate_type == "accounting_period" and item.action == "close_accounting_period":
        period = await session.scalar(
            select(AccountingPeriod)
            .where(AccountingPeriod.org_id == org_id, AccountingPeriod.id == item.aggregate_id)
            .with_for_update()
        )
        if period is None or period.status != "pending_close":
            raise HTTPException(status.HTTP_409_CONFLICT, "Accounting period tidak siap diputuskan")
        if decision == "approved":
            period.status = "closed"
            period.closed_by_user_id = actor_id
            period.closed_at = datetime.now(UTC)
        else:
            period.status = "open"
    session.add(
        ApprovalEvent(
            org_id=org_id,
            approval_id=item.id,
            actor_user_id=actor_id,
            event_type="ApprovalDecided",
            from_status=previous,
            to_status=decision,
            reason=reason,
        )
    )
    await session.flush()
    return item


async def _ensure_checker_role(session: AsyncSession, item: ApprovalRequest, actor_id: UUID) -> None:
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == item.org_id, Membership.user_id == actor_id)
    )
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Checker tidak memiliki membership pada tenant aktif")
    if membership.role.value in {"owner", "admin"}:
        return
    criteria = [
        StaffAssignment.org_id == item.org_id,
        StaffAssignment.user_id == actor_id,
        StaffAssignment.operational_role == item.assigned_role,
        StaffAssignment.is_active,
    ]
    if item.branch_id is not None:
        criteria.append(StaffAssignment.branch_id == item.branch_id)
    assignment = await session.scalar(select(StaffAssignment).where(*criteria))
    if assignment is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Peran atau cabang checker tidak sesuai penugasan approval")


async def _decide_custody_release(session: AsyncSession, item: ApprovalRequest, actor_id: UUID, decision: str) -> None:
    asset = await session.scalar(
        select(Asset).where(Asset.org_id == item.org_id, Asset.application_id == item.aggregate_id).with_for_update()
    )
    if asset is None or asset.collateral_status != "stored":
        raise HTTPException(status.HTTP_409_CONFLICT, "Agunan tidak berada pada status stored")
    if decision != "approved":
        return
    location_id = UUID(str(item.payload_snapshot["location_id"]))
    asset.collateral_status = "release_authorized"
    session.add(
        CustodyEvent(
            org_id=item.org_id,
            application_id=item.aggregate_id,
            location_id=location_id,
            actor_user_id=actor_id,
            event_type="release_authorized",
            condition_note=str(item.payload_snapshot.get("condition_note") or "Release approved after settlement"),
        )
    )
    session.add(
        CollateralEvent(
            org_id=item.org_id,
            application_id=item.aggregate_id,
            actor_user_id=actor_id,
            event_type="release_authorized",
            title="Release Authorized",
            description="Agunan disetujui untuk diserahkan setelah pemeriksaan empat mata.",
            event_metadata={"location_id": str(location_id), "approval_id": str(item.id)},
        )
    )


async def approval_queue(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    rows = list(
        await session.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.org_id == org_id)
            .order_by(ApprovalRequest.created_at.desc())
            .limit(500)
        )
    )
    return [
        {
            "id": item.id,
            "branch_id": item.branch_id,
            "aggregate_type": item.aggregate_type,
            "aggregate_id": item.aggregate_id,
            "aggregate_reference": item.aggregate_reference,
            "action": item.action,
            "version": item.version,
            "requested_by_user_id": item.requested_by_user_id,
            "assigned_role": item.assigned_role,
            "status": item.status,
            "priority": item.priority,
            "request_reason": item.request_reason,
            "payload_snapshot": item.payload_snapshot,
            "due_at": item.due_at,
            "decided_by_user_id": item.decided_by_user_id,
            "decided_at": item.decided_at,
            "decision_reason": item.decision_reason,
            "created_at": item.created_at,
        }
        for item in rows
    ]
