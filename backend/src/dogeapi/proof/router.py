"""Tenant-scoped custody proof register and live verifier."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.operations.mvp_service import visible_branch_ids
from dogeapi.proof.service import get_visible_proof, list_proofs, public_record, verify_proof
from dogeapi.security import require_scope

router = APIRouter(prefix="/v1/proofs", tags=["custody-proofs"], dependencies=[Depends(require_scope("org:read"))])
READ_ROLES = {"ops_admin", "branch_manager", "custodian", "auditor"}


@router.get("")
async def proof_register(
    session: SessionDep, org_id: OrgIdDep, user: UserDep, application_id: UUID | None = Query(None)
) -> list[dict[str, object]]:
    branch_ids = await visible_branch_ids(session, org_id, user.id, READ_ROLES)
    rows = await list_proofs(session, org_id, branch_ids, application_id)
    return [public_record(row) for row in rows]


@router.get("/{proof_id}/verify")
async def proof_verification(proof_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep) -> dict[str, object]:
    branch_ids = await visible_branch_ids(session, org_id, user.id, READ_ROLES)
    proof = await get_visible_proof(session, org_id, branch_ids, proof_id)
    if proof is None:
        raise HTTPException(404, "Proof not found")
    return {**public_record(proof), **await verify_proof(proof)}
