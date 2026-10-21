"""Tenant-scoped custody proof register and live verifier."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from dogeapi.agreement.service import public_record as agreement_public_record
from dogeapi.agreement.service import verify as verify_agreement_record
from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.models import LoanApplication, PawnAgreement
from dogeapi.operations.mvp_service import visible_branch_ids
from dogeapi.proof.service import get_visible_proof, list_proofs, public_record, verify_proof
from dogeapi.security import require_scope

router = APIRouter(prefix="/v1/proofs", tags=["custody-proofs"], dependencies=[Depends(require_scope("org:read"))])
READ_ROLES = {"ops_admin", "branch_manager", "custodian", "auditor"}
AGREEMENT_ROLES = READ_ROLES | {"loan_officer", "reviewer"}


@router.get("")
async def proof_register(
    session: SessionDep, org_id: OrgIdDep, user: UserDep, application_id: UUID | None = Query(None)
) -> list[dict[str, object]]:
    branch_ids = await visible_branch_ids(session, org_id, user.id, READ_ROLES)
    rows = await list_proofs(session, org_id, branch_ids, application_id)
    return [public_record(row) for row in rows]


async def _visible_agreement(session: SessionDep, org_id: UUID, user: UserDep,
                             application_id: UUID) -> PawnAgreement:
    branch_ids = await visible_branch_ids(session, org_id, user.id, AGREEMENT_ROLES)
    stmt = select(PawnAgreement).join(LoanApplication,
        (LoanApplication.id == PawnAgreement.application_id) & (LoanApplication.org_id == org_id)
    ).where(PawnAgreement.org_id == org_id, PawnAgreement.application_id == application_id)
    if branch_ids is not None:
        stmt = stmt.where(LoanApplication.branch_id.in_(branch_ids))
    agreement = await session.scalar(stmt)
    if agreement is None:
        raise HTTPException(404, "Agreement not found")
    return agreement


@router.get("/agreements/{application_id}")
async def agreement_record(application_id: UUID, session: SessionDep, org_id: OrgIdDep,
                           user: UserDep) -> dict[str, object]:
    agreement = await _visible_agreement(session, org_id, user, application_id)
    return agreement_public_record(agreement, include_snapshot=True)


@router.get("/agreements/{application_id}/verify")
async def agreement_verification(application_id: UUID, session: SessionDep, org_id: OrgIdDep,
                                 user: UserDep) -> dict[str, object]:
    agreement = await _visible_agreement(session, org_id, user, application_id)
    return {**agreement_public_record(agreement), **await verify_agreement_record(agreement)}


@router.get("/{proof_id}/verify")
async def proof_verification(proof_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep) -> dict[str, object]:
    branch_ids = await visible_branch_ids(session, org_id, user.id, READ_ROLES)
    proof = await get_visible_proof(session, org_id, branch_ids, proof_id)
    if proof is None:
        raise HTTPException(404, "Proof not found")
    return {**public_record(proof), **await verify_proof(proof)}
