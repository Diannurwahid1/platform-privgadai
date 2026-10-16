"""Partner operations endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.operations import mvp_service, service
from dogeapi.operations.mvp_schemas import (
    AcceptanceCreate,
    ActionResult,
    ApplicationCreate,
    ApplicationDetail,
    AppraisalCreate,
    AssetCategoryCreate,
    AssetCategoryItem,
    BranchCreate,
    BranchItem,
    CollateralTimeline,
    CustodyEventCreate,
    CustodyLocationCreate,
    CustodyMovementCreate,
    CustodyMovementDispatch,
    CustodyMovementReceive,
    DisbursementCreate,
    EvidenceCreate,
    FieldTaskItem,
    IncidentCreate,
    LoanProductCreate,
    LoanProductItem,
    MasterItem,
    OfferCreate,
    PickupCreate,
    PickupTransition,
    SettlementCreate,
    StaffAssignmentCreate,
    StaffAssignmentItem,
    TransitionInput,
)
from dogeapi.operations.schemas import ApplicationQueueItem, OperationsDashboardResponse
from dogeapi.security import require_scope

router = APIRouter(
    prefix="/v1",
    tags=["privgadai-operations"],
    dependencies=[Depends(require_scope("org:read"))],
)


@router.get("/operations/dashboard", response_model=OperationsDashboardResponse)
async def operations_dashboard(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> OperationsDashboardResponse:
    branch_ids = await mvp_service.visible_branch_ids(
        session,
        org_id,
        user.id,
        {"ops_admin", "branch_manager", "loan_officer", "reviewer", "appraiser", "custodian", "finance", "auditor"},
    )
    return await service.get_operations_dashboard(session, org_id, branch_ids=branch_ids)


@router.get("/applications", response_model=list[ApplicationQueueItem])
async def applications_inbox(
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ApplicationQueueItem]:
    branch_ids = await mvp_service.visible_branch_ids(
        session,
        org_id,
        user.id,
        {"ops_admin", "branch_manager", "loan_officer", "reviewer", "appraiser", "custodian", "finance", "auditor"},
    )
    return await service.list_application_queue(session, org_id, limit=limit, branch_ids=branch_ids)


@router.get("/field/tasks", response_model=list[FieldTaskItem])
async def field_tasks(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    return await mvp_service.list_field_tasks(session, org_id, user.id)


write_access = Depends(require_scope("org:operations:write"))
master_write_access = Depends(require_scope("org:master:write"))


@router.get("/master/branches", response_model=list[BranchItem])
async def branches(session: SessionDep, org_id: OrgIdDep) -> list[object]:
    return await mvp_service.list_branches(session, org_id)


@router.post(
    "/master/branches",
    response_model=BranchItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[master_write_access],
)
async def create_branch(data: BranchCreate, session: SessionDep, org_id: OrgIdDep) -> object:
    item = await mvp_service.create_branch(session, org_id, data)
    await session.commit()
    return item


@router.get("/master/asset-categories", response_model=list[AssetCategoryItem])
async def asset_categories(session: SessionDep, org_id: OrgIdDep) -> list[object]:
    return await mvp_service.list_asset_categories(session, org_id)


@router.post(
    "/master/asset-categories",
    response_model=AssetCategoryItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[master_write_access],
)
async def create_asset_category(data: AssetCategoryCreate, session: SessionDep, org_id: OrgIdDep) -> object:
    item = await mvp_service.create_asset_category(session, org_id, data)
    await session.commit()
    return item


@router.get("/master/loan-products", response_model=list[LoanProductItem])
async def loan_products(session: SessionDep, org_id: OrgIdDep) -> list[object]:
    return await mvp_service.list_loan_products(session, org_id)


@router.post(
    "/master/loan-products",
    response_model=LoanProductItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[master_write_access],
)
async def create_loan_product(data: LoanProductCreate, session: SessionDep, org_id: OrgIdDep) -> object:
    item = await mvp_service.create_loan_product(session, org_id, data)
    await session.commit()
    return item


@router.get("/master/custody-locations", response_model=list[MasterItem])
async def custody_locations(session: SessionDep, org_id: OrgIdDep) -> list[object]:
    return await mvp_service.list_custody_locations(session, org_id)


@router.post(
    "/master/custody-locations",
    response_model=MasterItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[master_write_access],
)
async def create_custody_location(data: CustodyLocationCreate, session: SessionDep, org_id: OrgIdDep) -> object:
    item = await mvp_service.create_custody_location(session, org_id, data)
    await session.commit()
    return item


@router.get("/master/staff-assignments", response_model=list[StaffAssignmentItem])
async def staff_assignments(session: SessionDep, org_id: OrgIdDep) -> list[dict[str, object]]:
    return await mvp_service.list_staff_assignments(session, org_id)


@router.post(
    "/master/staff-assignments",
    response_model=StaffAssignmentItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[master_write_access],
)
async def create_staff_assignment(
    data: StaffAssignmentCreate, session: SessionDep, org_id: OrgIdDep
) -> dict[str, object]:
    item = await mvp_service.create_staff_assignment(session, org_id, data)
    await session.commit()
    return item


@router.post(
    "/applications", response_model=ActionResult, status_code=status.HTTP_201_CREATED, dependencies=[write_access]
)
async def create_application(
    data: ApplicationCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ActionResult:
    item = await mvp_service.create_application(session, org_id, user.id, data)
    await session.commit()
    return ActionResult(id=item.id, application_id=item.id, status=item.status, message="Application created")


@router.get("/applications/{application_id}", response_model=ApplicationDetail)
async def application_detail(
    application_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ApplicationDetail:
    return await mvp_service.get_application_detail(session, org_id, user.id, application_id)


@router.post("/applications/{application_id}/transition", response_model=ActionResult, dependencies=[write_access])
async def transition_application(
    application_id: UUID,
    data: TransitionInput,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ActionResult:
    item = await mvp_service.transition_application(session, org_id, user.id, application_id, data.to_status, data.note)
    await session.commit()
    return ActionResult(id=item.id, application_id=item.id, status=item.status, message="Application status updated")


@router.post(
    "/applications/{application_id}/evidence",
    response_model=ActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_access],
)
async def add_evidence(
    application_id: UUID, data: EvidenceCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ActionResult:
    item = await mvp_service.add_evidence(session, org_id, user.id, application_id, data)
    await session.commit()
    return ActionResult(
        id=item.id, application_id=application_id, status=item.scan_status, message="Evidence registered"
    )


@router.post(
    "/applications/{application_id}/evidence/upload",
    response_model=ActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_access],
)
async def upload_evidence(
    application_id: UUID,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
    evidence_type: Annotated[str, Form(min_length=2, max_length=40)],
    file: Annotated[UploadFile, File()],
    subject_type: Annotated[str, Form(pattern="^(application|appraisal|custody_movement|incident)$")] = "application",
    subject_id: Annotated[UUID | None, Form()] = None,
) -> ActionResult:
    allowed = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only JPEG, PNG, WebP, or PDF evidence is allowed")
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Evidence file exceeds 10 MB")
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Evidence file is empty")
    item = await mvp_service.store_evidence_upload(
        session,
        org_id,
        user.id,
        application_id,
        evidence_type,
        file.filename or "evidence",
        file.content_type or "application/octet-stream",
        content,
        subject_type=subject_type,
        subject_id=subject_id,
    )
    await session.commit()
    return ActionResult(
        id=item.id,
        application_id=application_id,
        status=item.scan_status,
        message="Evidence scanned and stored in private clean storage"
        if item.scan_status == "clean"
        else "Evidence quarantined",
    )


@router.get("/applications/{application_id}/evidence")
async def list_application_evidence(
    application_id: UUID,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
    subject_type: Annotated[str | None, Query(pattern="^(application|appraisal|custody_movement|incident)$")] = None,
    subject_id: UUID | None = None,
) -> list[dict[str, object]]:
    items = await mvp_service.list_evidence(
        session, org_id, user.id, application_id, subject_type=subject_type, subject_id=subject_id
    )
    return [
        {
            "id": item.id,
            "application_id": item.application_id,
            "subject_type": item.subject_type,
            "subject_id": item.subject_id,
            "evidence_type": item.evidence_type,
            "file_name": item.file_name,
            "content_type": item.content_type,
            "size_bytes": item.size_bytes,
            "sha256": item.sha256,
            "scan_status": item.scan_status,
            "scanner_engine": item.scanner_engine,
            "scan_detail": item.scan_detail,
            "scanned_at": item.scanned_at,
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.get("/evidence/{evidence_id}/download")
async def download_evidence(evidence_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep) -> FileResponse:
    item, path = await mvp_service.get_evidence_download(session, org_id, user.id, evidence_id)
    await session.commit()
    return FileResponse(path, media_type=item.content_type, filename=item.file_name)


@router.post(
    "/appraisals", response_model=ActionResult, status_code=status.HTTP_201_CREATED, dependencies=[write_access]
)
async def create_appraisal(data: AppraisalCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep) -> ActionResult:
    item = await mvp_service.create_appraisal(session, org_id, user.id, data)
    await session.commit()
    return ActionResult(
        id=item.id,
        application_id=item.application_id,
        status=item.status,
        message="Appraisal submitted for checker approval",
    )


@router.post("/offers", response_model=ActionResult, status_code=status.HTTP_201_CREATED, dependencies=[write_access])
async def create_offer(data: OfferCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep) -> ActionResult:
    item = await mvp_service.create_offer(session, org_id, user.id, data)
    await session.commit()
    return ActionResult(id=item.id, application_id=item.application_id, status=item.status, message="Offer issued")


@router.post("/offers/{offer_id}/accept", response_model=ActionResult, dependencies=[write_access])
async def accept_offer(
    offer_id: UUID, data: AcceptanceCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ActionResult:
    item = await mvp_service.accept_offer(session, org_id, user.id, offer_id, data.channel, data.ip_address)
    await session.commit()
    return ActionResult(id=item.id, application_id=item.application_id, status=item.status, message="Offer accepted")


@router.post("/pickups", response_model=ActionResult, status_code=status.HTTP_201_CREATED, dependencies=[write_access])
async def create_pickup(data: PickupCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep) -> ActionResult:
    item = await mvp_service.create_pickup(session, org_id, user.id, data)
    await session.commit()
    return ActionResult(id=item.id, application_id=item.application_id, status=item.status, message="Pickup assigned")


@router.post("/pickups/{pickup_id}/transition", response_model=ActionResult, dependencies=[write_access])
async def transition_pickup(
    pickup_id: UUID,
    data: PickupTransition,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ActionResult:
    item = await mvp_service.transition_pickup(session, org_id, user.id, pickup_id, data.to_status, data.condition_note)
    await session.commit()
    return ActionResult(id=item.id, application_id=item.application_id, status=item.status, message="Pickup updated")


@router.post(
    "/custody/events", response_model=ActionResult, status_code=status.HTTP_201_CREATED, dependencies=[write_access]
)
async def create_custody_event(
    data: CustodyEventCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ActionResult:
    item = await mvp_service.create_custody_event(session, org_id, user.id, data)
    await session.commit()
    return ActionResult(
        id=item.id, application_id=item.application_id, status=item.event_type, message="Custody event recorded"
    )


@router.get("/custody/movements")
async def custody_movements(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    branch_ids = await mvp_service.visible_branch_ids(
        session, org_id, user.id, {"ops_admin", "branch_manager", "custodian", "auditor"}
    )
    return await mvp_service.list_custody_movements(session, org_id, branch_ids=branch_ids)


@router.post(
    "/custody/movements", response_model=ActionResult, status_code=status.HTTP_201_CREATED, dependencies=[write_access]
)
async def request_custody_movement(
    data: CustodyMovementCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ActionResult:
    item = await mvp_service.request_custody_movement(session, org_id, user.id, data)
    await session.commit()
    return ActionResult(
        id=item.id, application_id=item.application_id, status=item.status, message="Custody movement requested"
    )


@router.post("/custody/movements/{movement_id}/dispatch", response_model=ActionResult, dependencies=[write_access])
async def dispatch_custody_movement(
    movement_id: UUID, data: CustodyMovementDispatch, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ActionResult:
    item = await mvp_service.dispatch_custody_movement(session, org_id, user.id, movement_id, data.seal_out, data.note)
    await session.commit()
    return ActionResult(
        id=item.id, application_id=item.application_id, status=item.status, message="Custody movement dispatched"
    )


@router.post("/custody/movements/{movement_id}/receive", response_model=ActionResult, dependencies=[write_access])
async def receive_custody_movement(
    movement_id: UUID, data: CustodyMovementReceive, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ActionResult:
    item = await mvp_service.receive_custody_movement(session, org_id, user.id, movement_id, data.seal_in, data.note)
    await session.commit()
    return ActionResult(
        id=item.id, application_id=item.application_id, status=item.status, message="Custody movement received"
    )


@router.post("/loans/{application_id}/disburse", response_model=ActionResult, dependencies=[write_access])
async def disburse_loan(
    application_id: UUID,
    data: DisbursementCreate,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ActionResult:
    item = await mvp_service.disburse_loan(
        session, org_id, user.id, application_id, data.external_reference, data.idempotency_key
    )
    await session.commit()
    return ActionResult(id=item.id, application_id=item.application_id, status=item.status, message="Loan disbursed")


@router.post(
    "/settlements", response_model=ActionResult, status_code=status.HTTP_201_CREATED, dependencies=[write_access]
)
async def verify_settlement(
    data: SettlementCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ActionResult:
    item = await mvp_service.verify_settlement(session, org_id, user.id, data)
    await session.commit()
    return ActionResult(
        id=item.id, application_id=item.application_id, status=item.status, message="Settlement verified"
    )


@router.post(
    "/incidents", response_model=ActionResult, status_code=status.HTTP_201_CREATED, dependencies=[write_access]
)
async def create_incident(data: IncidentCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep) -> ActionResult:
    item = await mvp_service.create_incident(session, org_id, user.id, data)
    await session.commit()
    return ActionResult(id=item.id, application_id=item.application_id, status=item.status, message="Incident reported")


@router.get("/collateral/{application_id}/timeline", response_model=CollateralTimeline)
async def collateral_timeline(
    application_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> CollateralTimeline:
    return await mvp_service.get_collateral_timeline(session, org_id, user.id, application_id)
