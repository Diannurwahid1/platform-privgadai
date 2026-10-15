"""Approval inbox API."""

from uuid import UUID

from fastapi import APIRouter, Depends

from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.operations import approval_service, mvp_service
from dogeapi.operations.approval_schemas import ApprovalDecision
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
