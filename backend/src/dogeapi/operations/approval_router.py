"""Approval inbox API."""

from uuid import UUID

from fastapi import APIRouter, Depends

from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.operations import approval_service, mvp_service
from dogeapi.operations.approval_schemas import ApprovalDecision, ApprovalDelegationCreate
from dogeapi.security import require_scope

router = APIRouter(prefix="/v1/approvals", tags=["approvals"], dependencies=[Depends(require_scope("org:read"))])


@router.get("")
async def list_approvals(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "reviewer", "auditor"}
    )
    return await approval_service.approval_queue(session, org_id)


@router.post("/{approval_id}/decision", dependencies=[Depends(require_scope("org:write"))])
async def decide_approval(
    approval_id: UUID, data: ApprovalDecision, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    item = await approval_service.decide_approval(session, org_id, approval_id, user.id, data.decision, data.reason)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Keputusan approval tercatat"}


@router.get("/delegations")
async def list_delegations(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "reviewer", "auditor"}
    )
    return await approval_service.list_delegations(session, org_id)


@router.post("/delegations", status_code=201, dependencies=[Depends(require_scope("org:write"))])
async def create_delegation(
    data: ApprovalDelegationCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    item = await approval_service.create_delegation(
        session,
        org_id=org_id,
        actor_id=user.id,
        delegator_user_id=data.delegator_user_id,
        delegate_user_id=data.delegate_user_id,
        branch_id=data.branch_id,
        assigned_role=data.assigned_role,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        reason=data.reason,
    )
    await session.commit()
    return {"id": item.id, "status": "active", "message": "Delegasi approval dicatat"}


@router.post("/delegations/{delegation_id}/revoke", dependencies=[Depends(require_scope("org:write"))])
async def revoke_delegation(
    delegation_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    item = await approval_service.revoke_delegation(session, org_id, delegation_id, user.id)
    await session.commit()
    return {"id": item.id, "status": "revoked", "message": "Delegasi approval dicabut"}


@router.post("/escalations/run", dependencies=[Depends(require_scope("org:write"))])
async def run_escalations(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> dict[str, object]:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "auditor"})
    count = await approval_service.escalate_overdue_approvals(session, org_id, user.id)
    await session.commit()
    return {"count": count, "message": f"{count} approval melewati SLA berhasil dieskalasi"}
