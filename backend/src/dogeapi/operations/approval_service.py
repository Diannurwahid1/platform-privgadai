"""Generic maker-checker approval workflow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    AccountingPeriod,
    ApprovalDelegation,
    ApprovalEvent,
    ApprovalRequest,
    Asset,
    CollateralEvent,
    ComplaintCase,
    ComplaintEvent,
    ConfigurationEvent,
    ConfigurationVersion,
    CustodyEvent,
    EvidenceFile,
    HumanAppraisal,
    Incident,
    IncidentEvent,
    InventoryCheck,
    Membership,
    PaymentAdjustment,
    ReconciliationRun,
    RegulatoryReportRun,
    RegulatoryReportTemplate,
    StaffAssignment,
    TellerSession,
    User,
)
from dogeapi.operations.configuration_runtime import get_effective_payload


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
    workflow_policy = await get_effective_payload(
        session,
        org_id,
        "workflow",
        [f"approval.{action}", "approval.default"],
    )
    sla_hours = int(workflow_policy.get("approval_sla_hours", sla_hours))
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
    delegation_id = await _ensure_checker_role(session, item, actor_id)
    if decision == "approved" and item.aggregate_type in {"appraisal", "incident"}:
        clean_evidence_id = await session.scalar(
            select(EvidenceFile.id).where(
                EvidenceFile.org_id == org_id,
                EvidenceFile.subject_type == item.aggregate_type,
                EvidenceFile.subject_id == item.aggregate_id,
                EvidenceFile.scan_status == "clean",
            )
        )
        if clean_evidence_id is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Approval memerlukan sedikitnya satu evidence yang lulus malware scanning",
            )
    previous = item.status
    item.status = decision
    item.decided_by_user_id = actor_id
    item.decided_at = datetime.now(UTC)
    item.decision_reason = reason
    item.decided_under_delegation_id = delegation_id
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
    elif item.aggregate_type == "regulatory_template" and item.action == "activate_regulatory_template":
        template = await session.scalar(
            select(RegulatoryReportTemplate)
            .where(RegulatoryReportTemplate.org_id == org_id, RegulatoryReportTemplate.id == item.aggregate_id)
            .with_for_update()
        )
        if template is None or template.status != "pending_approval":
            raise HTTPException(status.HTTP_409_CONFLICT, "Template regulator tidak siap diputuskan")
        template.status = "active" if decision == "approved" else "draft"
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
    elif item.aggregate_type == "teller_session" and item.action == "approve_teller_variance":
        teller_session = await session.scalar(
            select(TellerSession)
            .where(TellerSession.org_id == org_id, TellerSession.id == item.aggregate_id)
            .with_for_update()
        )
        if teller_session is None or teller_session.status != "variance_pending":
            raise HTTPException(status.HTTP_409_CONFLICT, "Selisih kas teller tidak siap diputuskan")
        if decision == "approved":
            teller_session.status = "closed_with_variance"
            teller_session.variance_approved_by_user_id = actor_id
            teller_session.variance_approved_at = datetime.now(UTC)
        else:
            teller_session.status = "open"
            teller_session.expected_closing_balance = None
            teller_session.actual_closing_balance = None
            teller_session.variance_amount = None
            teller_session.variance_reason = None
            teller_session.closed_at = None
    elif item.aggregate_type == "incident" and item.action == "resolve_incident":
        incident = await session.scalar(
            select(Incident).where(Incident.org_id == org_id, Incident.id == item.aggregate_id).with_for_update()
        )
        if incident is None or incident.status != "pending_resolution":
            raise HTTPException(status.HTTP_409_CONFLICT, "Incident tidak siap diputuskan")
        previous_incident_status = incident.status
        if decision == "approved":
            incident.status = "resolved"
            incident.resolved_by_user_id = actor_id
            incident.resolved_at = datetime.now(UTC)
            asset = await session.scalar(
                select(Asset)
                .where(Asset.org_id == org_id, Asset.application_id == incident.application_id)
                .with_for_update()
            )
            if asset is not None and asset.collateral_status == "incident_hold":
                reported_event = await session.scalar(
                    select(IncidentEvent)
                    .where(
                        IncidentEvent.org_id == org_id,
                        IncidentEvent.incident_id == incident.id,
                        IncidentEvent.event_type == "IncidentReported",
                    )
                    .order_by(IncidentEvent.occurred_at)
                )
                previous_collateral_status = (
                    str(reported_event.event_metadata.get("previous_collateral_status"))
                    if reported_event is not None
                    else "stored"
                )
                asset.collateral_status = previous_collateral_status
                session.add(
                    CollateralEvent(
                        org_id=org_id,
                        application_id=incident.application_id,
                        actor_user_id=actor_id,
                        event_type="incident_resolved",
                        title="Incident resolved",
                        description=incident.resolution_note,
                        event_metadata={"incident_id": str(incident.id), "approval_id": str(item.id)},
                    )
                )
        else:
            incident.status = "investigating"
        session.add(
            IncidentEvent(
                org_id=org_id,
                incident_id=incident.id,
                actor_user_id=actor_id,
                event_type="IncidentResolutionApproved" if decision == "approved" else "IncidentResolutionRejected",
                from_status=previous_incident_status,
                to_status=incident.status,
                note=reason,
                event_metadata={"approval_id": str(item.id)},
            )
        )
    elif item.aggregate_type == "complaint" and item.action == "resolve_complaint":
        complaint = await session.scalar(
            select(ComplaintCase)
            .where(ComplaintCase.org_id == org_id, ComplaintCase.id == item.aggregate_id)
            .with_for_update()
        )
        if complaint is None or complaint.status != "pending_resolution":
            raise HTTPException(status.HTTP_409_CONFLICT, "Complaint tidak siap diputuskan")
        previous_complaint_status = complaint.status
        if decision == "approved":
            complaint.status = "resolved"
            complaint.resolved_by_user_id = actor_id
            complaint.resolved_at = datetime.now(UTC)
        else:
            complaint.status = "investigating"
        session.add(
            ComplaintEvent(
                org_id=org_id,
                complaint_id=complaint.id,
                actor_user_id=actor_id,
                event_type="ComplaintResolved" if decision == "approved" else "ComplaintResolutionRejected",
                from_status=previous_complaint_status,
                to_status=complaint.status,
                message=reason,
            )
        )
    elif item.aggregate_type == "configuration" and item.action == "activate_configuration":
        configuration = await session.scalar(
            select(ConfigurationVersion)
            .where(ConfigurationVersion.org_id == org_id, ConfigurationVersion.id == item.aggregate_id)
            .with_for_update()
        )
        if configuration is None or configuration.status != "pending_approval":
            raise HTTPException(status.HTTP_409_CONFLICT, "Configuration tidak siap diputuskan")
        previous_configuration_status = configuration.status
        if decision == "approved":
            configuration.approved_by_user_id = actor_id
            configuration.approved_at = datetime.now(UTC)
            if configuration.effective_from <= datetime.now(UTC):
                from dogeapi.operations import configuration_service

                await configuration_service.activate_configuration(session, configuration, actor_id)
            else:
                configuration.status = "approved"
                session.add(
                    ConfigurationEvent(
                        org_id=org_id,
                        configuration_id=configuration.id,
                        actor_user_id=actor_id,
                        event_type="ConfigurationApproved",
                        from_status=previous_configuration_status,
                        to_status="approved",
                        reason=reason,
                    )
                )
        else:
            configuration.status = "rejected"
            session.add(
                ConfigurationEvent(
                    org_id=org_id,
                    configuration_id=configuration.id,
                    actor_user_id=actor_id,
                    event_type="ConfigurationRejected",
                    from_status=previous_configuration_status,
                    to_status="rejected",
                    reason=reason,
                )
            )
    elif item.aggregate_type == "payment_adjustment" and item.action == "post_payment_adjustment":
        adjustment = await session.scalar(
            select(PaymentAdjustment)
            .where(PaymentAdjustment.org_id == org_id, PaymentAdjustment.id == item.aggregate_id)
            .with_for_update()
        )
        if adjustment is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Payment adjustment target tidak ditemukan")
        from dogeapi.operations import payment_service

        await payment_service.decide_adjustment(session, adjustment, actor_id, decision)
    elif item.aggregate_type == "reconciliation" and item.action == "resolve_reconciliation_exception":
        reconciliation = await session.scalar(
            select(ReconciliationRun)
            .where(ReconciliationRun.org_id == org_id, ReconciliationRun.id == item.aggregate_id)
            .with_for_update()
        )
        if reconciliation is None or reconciliation.status != "pending_resolution":
            raise HTTPException(status.HTTP_409_CONFLICT, "Reconciliation exception tidak siap diputuskan")
        if decision == "approved":
            reconciliation.status = "resolved"
            reconciliation.resolved_by_user_id = actor_id
            reconciliation.resolved_at = datetime.now(UTC)
        else:
            reconciliation.status = "exception"
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


async def _ensure_checker_role(session: AsyncSession, item: ApprovalRequest, actor_id: UUID) -> UUID | None:
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == item.org_id, Membership.user_id == actor_id)
    )
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Checker tidak memiliki membership pada tenant aktif")
    if membership.role.value in {"owner", "admin"}:
        return None
    criteria = [
        StaffAssignment.org_id == item.org_id,
        StaffAssignment.user_id == actor_id,
        StaffAssignment.operational_role == item.assigned_role,
        StaffAssignment.is_active,
    ]
    if item.branch_id is not None:
        criteria.append(StaffAssignment.branch_id == item.branch_id)
    assignment = await session.scalar(select(StaffAssignment).where(*criteria))
    if assignment is not None:
        return None
    now = datetime.now(UTC)
    delegation = await session.scalar(
        select(ApprovalDelegation).where(
            ApprovalDelegation.org_id == item.org_id,
            ApprovalDelegation.delegate_user_id == actor_id,
            ApprovalDelegation.assigned_role == item.assigned_role,
            ApprovalDelegation.revoked_at.is_(None),
            ApprovalDelegation.starts_at <= now,
            ApprovalDelegation.ends_at >= now,
            (ApprovalDelegation.branch_id.is_(None) | (ApprovalDelegation.branch_id == item.branch_id)),
        )
    )
    if delegation is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Peran atau cabang checker tidak sesuai penugasan approval")
    return delegation.id


async def create_delegation(
    session: AsyncSession,
    *,
    org_id: UUID,
    actor_id: UUID,
    delegator_user_id: UUID,
    delegate_user_id: UUID,
    branch_id: UUID | None,
    assigned_role: str,
    starts_at: datetime,
    ends_at: datetime,
    reason: str,
) -> ApprovalDelegation:
    if delegator_user_id == delegate_user_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Delegator dan penerima delegasi harus berbeda")
    if ends_at <= starts_at or ends_at <= datetime.now(UTC):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Periode delegasi tidak valid")
    actor_membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == actor_id)
    )
    if actor_membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Aktor bukan anggota tenant")
    if actor_id != delegator_user_id and actor_membership.role.value not in {"owner", "admin"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Hanya admin yang dapat membuat delegasi untuk pengguna lain")
    await _ensure_user_holds_role(session, org_id, delegator_user_id, assigned_role, branch_id)
    delegate_membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == delegate_user_id)
    )
    if delegate_membership is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Penerima delegasi bukan anggota tenant")
    overlap = await session.scalar(
        select(ApprovalDelegation.id).where(
            ApprovalDelegation.org_id == org_id,
            ApprovalDelegation.delegator_user_id == delegator_user_id,
            ApprovalDelegation.assigned_role == assigned_role,
            ApprovalDelegation.branch_id.is_not_distinct_from(branch_id),
            ApprovalDelegation.revoked_at.is_(None),
            ApprovalDelegation.starts_at < ends_at,
            ApprovalDelegation.ends_at > starts_at,
        )
    )
    if overlap is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Delegasi aktif pada peran dan periode tersebut sudah ada")
    delegation = ApprovalDelegation(
        org_id=org_id,
        delegator_user_id=delegator_user_id,
        delegate_user_id=delegate_user_id,
        branch_id=branch_id,
        assigned_role=assigned_role,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=reason,
    )
    session.add(delegation)
    await session.flush()
    return delegation


async def _ensure_user_holds_role(
    session: AsyncSession, org_id: UUID, user_id: UUID, assigned_role: str, branch_id: UUID | None
) -> None:
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    )
    if membership is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Delegator bukan anggota tenant")
    if membership.role.value in {"owner", "admin"}:
        return
    criteria = [
        StaffAssignment.org_id == org_id,
        StaffAssignment.user_id == user_id,
        StaffAssignment.operational_role == assigned_role,
        StaffAssignment.is_active,
    ]
    if branch_id is not None:
        criteria.append(StaffAssignment.branch_id == branch_id)
    if await session.scalar(select(StaffAssignment.id).where(*criteria)) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Delegator tidak memegang peran yang didelegasikan")


async def list_delegations(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    rows = list(
        (
            await session.execute(
                select(ApprovalDelegation, User.full_name, User.email)
                .join(User, User.id == ApprovalDelegation.delegate_user_id)
                .where(ApprovalDelegation.org_id == org_id)
                .order_by(ApprovalDelegation.created_at.desc())
            )
        ).all()
    )
    return [
        {
            "id": item.id,
            "delegator_user_id": item.delegator_user_id,
            "delegate_user_id": item.delegate_user_id,
            "delegate_name": full_name or email,
            "branch_id": item.branch_id,
            "assigned_role": item.assigned_role,
            "starts_at": item.starts_at,
            "ends_at": item.ends_at,
            "reason": item.reason,
            "revoked_at": item.revoked_at,
            "created_at": item.created_at,
        }
        for item, full_name, email in rows
    ]


async def revoke_delegation(
    session: AsyncSession, org_id: UUID, delegation_id: UUID, actor_id: UUID
) -> ApprovalDelegation:
    delegation = await session.scalar(
        select(ApprovalDelegation)
        .where(ApprovalDelegation.org_id == org_id, ApprovalDelegation.id == delegation_id)
        .with_for_update()
    )
    if delegation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Delegasi tidak ditemukan")
    actor_membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == actor_id)
    )
    is_admin = actor_membership is not None and actor_membership.role.value in {"owner", "admin"}
    if actor_id != delegation.delegator_user_id and not is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Delegasi hanya dapat dicabut delegator atau admin")
    if delegation.revoked_at is None:
        delegation.revoked_at = datetime.now(UTC)
        delegation.revoked_by_user_id = actor_id
        await session.flush()
    return delegation


async def escalate_overdue_approvals(session: AsyncSession, org_id: UUID, actor_id: UUID) -> int:
    now = datetime.now(UTC)
    rows = list(
        await session.scalars(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.org_id == org_id,
                ApprovalRequest.status == "pending",
                ApprovalRequest.due_at <= now,
                ApprovalRequest.escalation_level < 2,
            )
            .order_by(ApprovalRequest.due_at)
            .limit(200)
            .with_for_update(skip_locked=True)
        )
    )
    for item in rows:
        previous_role = item.assigned_role
        item.escalation_level += 1
        item.escalated_at = now
        item.priority = "high" if item.escalation_level == 1 else "critical"
        item.assigned_role = "branch_manager" if item.escalation_level == 1 else "ops_admin"
        item.due_at = now + timedelta(hours=4 if item.escalation_level == 1 else 2)
        session.add(
            ApprovalEvent(
                org_id=org_id,
                approval_id=item.id,
                actor_user_id=actor_id,
                event_type="ApprovalEscalated",
                from_status="pending",
                to_status="pending",
                reason=f"SLA terlewati; routing {previous_role} → {item.assigned_role}",
            )
        )
    await session.flush()
    return len(rows)


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
    approval_ids = [item.id for item in rows]
    events_by_approval: dict[UUID, list[dict[str, object]]] = {approval_id: [] for approval_id in approval_ids}
    if approval_ids:
        events = list(
            await session.scalars(
                select(ApprovalEvent)
                .where(ApprovalEvent.org_id == org_id, ApprovalEvent.approval_id.in_(approval_ids))
                .order_by(ApprovalEvent.occurred_at)
            )
        )
        for event in events:
            events_by_approval[event.approval_id].append(
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "actor_user_id": event.actor_user_id,
                    "from_status": event.from_status,
                    "to_status": event.to_status,
                    "reason": event.reason,
                    "occurred_at": event.occurred_at,
                }
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
            "escalation_level": item.escalation_level,
            "escalated_at": item.escalated_at,
            "decided_under_delegation_id": item.decided_under_delegation_id,
            "events": events_by_approval[item.id],
            "created_at": item.created_at,
        }
        for item in rows
    ]
