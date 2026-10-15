"""Seed clearly-labelled synthetic PrivGadai operations data.

Run from ``backend`` with::

    .venv/Scripts/python scripts/seed_privgadai_demo.py --org denjaka
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from dogeapi.db import get_session_factory
from dogeapi.models import (
    ApplicationStatusHistory,
    Asset,
    Borrower,
    Branch,
    LoanApplication,
    Membership,
    Organization,
)

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
            branch_count = await session.scalar(select(func.count(Branch.id)).where(Branch.org_id == org.id))
            if branch_count:
                print(f"skip {org.slug}: operations data already exists")
                continue

            actor_user_id = await session.scalar(
                select(Membership.user_id).where(Membership.org_id == org.id).order_by(Membership.created_at).limit(1)
            )
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
                    application_no=f"PG-DEMO-2026-{index:04d}",
                    status=status,
                    priority=priority,
                    asset_category=category,
                    requested_amount=Decimal(requested),
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
