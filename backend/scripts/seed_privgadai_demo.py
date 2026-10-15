"""Seed clearly-labelled synthetic PrivGadai operations data.

Run from ``backend`` with::

    .venv/Scripts/python scripts/seed_privgadai_demo.py --org denjaka
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select, update

from dogeapi.db import get_session_factory
from dogeapi.models import (
    ApplicationStatusHistory,
    Asset,
    AssetCategory,
    Borrower,
    Branch,
    CustodyLocation,
    LoanApplication,
    LoanProduct,
    Membership,
    Organization,
    RegulatoryReportTemplate,
    StaffAssignment,
)
from dogeapi.operations import erp_service

DEMO_APPLICATIONS = (
    (
        "Dewi Lestari",
        "BRW-DEMO-001",
        "08•• •••• 1201",
        "smartphone",
        "Apple",
        "iPhone 15 Pro",
        "under_review",
        "normal",
        12500000,
        16800000,
        "with_customer",
        1,
    ),
    (
        "Rizky Pratama",
        "BRW-DEMO-002",
        "08•• •••• 2287",
        "emas",
        "Antam",
        "Logam Mulia 10gr",
        "appraisal",
        "high",
        9800000,
        11200000,
        "with_customer",
        2,
    ),
    (
        "Siti Rahma",
        "BRW-DEMO-003",
        "08•• •••• 3412",
        "laptop",
        "ASUS",
        "Zenbook 14 OLED",
        "offered",
        "normal",
        8500000,
        12750000,
        "pickup_assigned",
        3,
    ),
    (
        "Bagus Saputra",
        "BRW-DEMO-004",
        "08•• •••• 4578",
        "kamera",
        "Sony",
        "Alpha A7 III",
        "accepted",
        "high",
        16000000,
        22400000,
        "in_transit",
        4,
    ),
    (
        "Nadia Permata",
        "BRW-DEMO-005",
        "08•• •••• 5634",
        "jam tangan",
        "Tissot",
        "PRX Powermatic 80",
        "accepted",
        "normal",
        7000000,
        10300000,
        "stored",
        5,
    ),
    (
        "Andi Wijaya",
        "BRW-DEMO-006",
        "08•• •••• 6755",
        "smartphone",
        "Samsung",
        "Galaxy S24 Ultra",
        "submitted",
        "normal",
        11000000,
        15700000,
        "with_customer",
        6,
    ),
    (
        "Maya Anggraini",
        "BRW-DEMO-007",
        "08•• •••• 7821",
        "laptop",
        "Apple",
        "MacBook Air M3",
        "rejected",
        "normal",
        9000000,
        14200000,
        "with_customer",
        7,
    ),
    (
        "Fajar Nugroho",
        "BRW-DEMO-008",
        "08•• •••• 8940",
        "emas",
        "UBS",
        "Perhiasan 18K",
        "accepted",
        "normal",
        6200000,
        9100000,
        "stored",
        8,
    ),
)


async def seed(org_slug: str | None) -> None:
    factory = get_session_factory()
    async with factory() as session:
        query = select(Organization).order_by(Organization.created_at)
        if org_slug:
            query = query.where(Organization.slug == org_slug)
        organizations = (await session.scalars(query)).all()
        if not organizations:
            raise SystemExit(f"No organization found for slug: {org_slug or '(any)'}")

        for org in organizations:
            actor_user_id = await session.scalar(
                select(Membership.user_id).where(Membership.org_id == org.id).order_by(Membership.created_at).limit(1)
            )
            branch_count = await session.scalar(select(func.count(Branch.id)).where(Branch.org_id == org.id))
            if branch_count:
                branches = list(
                    await session.scalars(select(Branch).where(Branch.org_id == org.id).order_by(Branch.code))
                )
            else:
                branches = [
                    Branch(
                        org_id=org.id,
                        code="JKT-01",
                        name="Cabang Jakarta Pusat",
                        city="Jakarta",
                        address="Data sintetis — area operasional Jakarta Pusat",
                    ),
                    Branch(
                        org_id=org.id,
                        code="JKT-02",
                        name="Cabang Jakarta Selatan",
                        city="Jakarta",
                        address="Data sintetis — area operasional Jakarta Selatan",
                    ),
                ]
                session.add_all(branches)
                await session.flush()

            if not await session.scalar(select(func.count(AssetCategory.id)).where(AssetCategory.org_id == org.id)):
                session.add_all(
                    [
                        AssetCategory(org_id=org.id, code="smartphone", name="Smartphone", requires_serial_number=True),
                        AssetCategory(org_id=org.id, code="laptop", name="Laptop", requires_serial_number=True),
                        AssetCategory(org_id=org.id, code="emas", name="Emas & Perhiasan"),
                        AssetCategory(org_id=org.id, code="kamera", name="Kamera", requires_serial_number=True),
                        AssetCategory(
                            org_id=org.id, code="jam tangan", name="Jam Tangan Premium", requires_serial_number=True
                        ),
                    ]
                )

            product = await session.scalar(select(LoanProduct).where(LoanProduct.org_id == org.id).limit(1))
            if product is None:
                product = LoanProduct(
                    org_id=org.id,
                    code="REGULER-30",
                    name="Gadai Reguler",
                    min_amount=Decimal("500000"),
                    max_amount=Decimal("50000000"),
                    max_ltv_percent=Decimal("80"),
                    allowed_tenors_days=[30, 60, 90, 120],
                    service_fee_percent=Decimal("5"),
                )
                session.add(product)
                await session.flush()

            if not await session.scalar(select(func.count(CustodyLocation.id)).where(CustodyLocation.org_id == org.id)):
                session.add_all(
                    [
                        CustodyLocation(
                            org_id=org.id,
                            branch_id=branch.id,
                            code=f"VAULT-{branch.code}",
                            name=f"Brankas {branch.name}",
                            location_type="branch_vault",
                        )
                        for branch in branches
                    ]
                )

            if actor_user_id and not await session.scalar(
                select(func.count(StaffAssignment.id)).where(StaffAssignment.org_id == org.id)
            ):
                session.add(
                    StaffAssignment(
                        org_id=org.id,
                        user_id=actor_user_id,
                        branch_id=branches[0].id,
                        operational_role="ops_admin",
                    )
                )

            if actor_user_id:
                for branch in branches:
                    _, cashbox = await erp_service.ensure_finance_masters(session, org.id, branch.id)
                    await erp_service.fund_cashbox(
                        session,
                        org.id,
                        actor_user_id,
                        cashbox.id,
                        Decimal("100000000"),
                        f"DEMO-CAPITAL-{branch.code}",
                        f"demo-capital-{org.id}-{branch.code}",
                    )

            if not await session.scalar(
                select(func.count(RegulatoryReportTemplate.id)).where(RegulatoryReportTemplate.org_id == org.id)
            ):
                session.add_all(
                    [
                        RegulatoryReportTemplate(
                            org_id=org.id,
                            report_type="OJK",
                            code="OJK-MONTHLY-DRAFT",
                            name="Template laporan bulanan — perlu validasi regulasi resmi",
                            version="draft-2026.1",
                            effective_from=datetime.now(UTC).date(),
                            mapping_schema={"status": "draft", "source": "loan_subledger"},
                            validation_rules=[],
                            status="draft",
                        ),
                        RegulatoryReportTemplate(
                            org_id=org.id,
                            report_type="SLIK",
                            code="SLIK-DRAFT",
                            name="Template persiapan data SLIK — bukan kanal submission",
                            version="draft-2026.1",
                            effective_from=datetime.now(UTC).date(),
                            mapping_schema={"status": "draft", "segments": []},
                            validation_rules=[],
                            status="draft",
                        ),
                    ]
                )

            if branch_count:
                await session.execute(
                    update(LoanApplication)
                    .where(LoanApplication.org_id == org.id, LoanApplication.product_id.is_(None))
                    .values(product_id=product.id, requested_tenor_days=30)
                )
                await session.commit()
                print(f"updated {org.slug}: master data ready; operations data preserved")
                continue

            now = datetime.now(UTC)
            for index, item in enumerate(DEMO_APPLICATIONS, start=1):
                (
                    name,
                    borrower_ref,
                    phone,
                    category,
                    brand,
                    model,
                    status,
                    priority,
                    requested,
                    indicative,
                    collateral_status,
                    age_days,
                ) = item
                borrower = Borrower(
                    org_id=org.id,
                    customer_reference=borrower_ref,
                    full_name=name,
                    phone_masked=phone,
                )
                session.add(borrower)
                await session.flush()

                submitted_at = now - timedelta(days=age_days, hours=index)
                application = LoanApplication(
                    org_id=org.id,
                    branch_id=branches[index % 2].id,
                    borrower_id=borrower.id,
                    assigned_user_id=actor_user_id,
                    product_id=product.id,
                    application_no=f"PG-DEMO-2026-{index:04d}",
                    status=status,
                    priority=priority,
                    asset_category=category,
                    requested_amount=Decimal(requested),
                    requested_tenor_days=30,
                    submitted_at=submitted_at,
                )
                session.add(application)
                await session.flush()

                session.add(
                    Asset(
                        org_id=org.id,
                        application_id=application.id,
                        asset_code=f"AST-DEMO-{index:04d}",
                        category=category,
                        brand=brand,
                        model=model,
                        condition_grade="B" if index % 3 else "A",
                        indicative_value=Decimal(indicative),
                        collateral_status=collateral_status,
                    )
                )
                session.add_all(
                    [
                        ApplicationStatusHistory(
                            org_id=org.id,
                            application_id=application.id,
                            actor_user_id=actor_user_id,
                            from_status=None,
                            to_status="submitted",
                            note="Pengajuan sintetis diterima melalui portal nasabah.",
                            created_at=submitted_at,
                        ),
                        ApplicationStatusHistory(
                            org_id=org.id,
                            application_id=application.id,
                            actor_user_id=actor_user_id,
                            from_status="submitted" if status != "submitted" else None,
                            to_status=status,
                            note="Aktivitas demo untuk Partner Operations Dashboard.",
                            created_at=submitted_at + timedelta(hours=4),
                        ),
                    ]
                )

            await session.commit()
            print(f"seeded {org.slug}: 2 branches, {len(DEMO_APPLICATIONS)} applications")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", help="Organization slug. Defaults to every organization without operations data.")
    args = parser.parse_args()
    asyncio.run(seed(args.org))


if __name__ == "__main__":
    main()
