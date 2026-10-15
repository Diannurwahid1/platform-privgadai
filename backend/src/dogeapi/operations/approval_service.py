"""Generic maker-checker approval workflow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import ApprovalEvent, ApprovalRequest, HumanAppraisal


async def request_approval(
    session: AsyncSession,
    *,
    org_id: UUID,
    branch_id: UUID,
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
