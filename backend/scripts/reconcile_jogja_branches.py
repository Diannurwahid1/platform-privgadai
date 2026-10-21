"""Reconcile the Jogja staging tenant to its five confirmed branches.

The existing two-branch October scenario is synthetic. This script keeps its
records, assigns all of them to UAD Kampus 4, and leaves the other four
branches without operational records. It refuses to move unfamiliar records.

Run from backend after taking a database backup:
    .venv/bin/python scripts/reconcile_jogja_branches.py --dry-run
    .venv/bin/python scripts/reconcile_jogja_branches.py
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import func, select

from dogeapi.db import get_session_factory
from dogeapi.models import (
    Base,
    Branch,
    Cashbox,
    CustodyLocation,
    LoanApplication,
    Organization,
    StaffAssignment,
)
from dogeapi.settings import get_settings

ORG_SLUG = "murah-gadai-jogja"
MAIN_CODE = "01-UAD-K4"
BRANCHES = (
    (MAIN_CODE, "Gadai Murah Jogja \u2013 Cabang UAD Kampus 4 (Tamanan)"),
    ("02-UMY", "Gadai Murah Jogja \u2013 Cabang UMY"),
    ("03-KASONGAN", "Gadai Murah Jogja \u2013 Cabang Kasongan"),
    ("04-PLERET", "Gadai Murah Jogja \u2013 Cabang Pleret"),
    ("05-WIYORO", "Gadai Murah Jogja \u2013 Cabang Wiyoro"),
)


async def count_references(session, target: str, ids: list) -> dict[str, int]:
    """Count references to rows being emptied, including future model tables."""
    if not ids:
        return {}
    found: dict[str, int] = {}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if any(fk.column.table.name == target for fk in column.foreign_keys):
                total = await session.scalar(
                    select(func.count()).select_from(table).where(column.in_(ids))
                )
                if total:
                    found[f"{table.name}.{column.name}"] = total
    return found


async def reconcile(*, dry_run: bool) -> None:
    settings = get_settings()
    if settings.APP_ENV != "staging" or settings.BORROWER_ORG_SLUG != ORG_SLUG:
        raise SystemExit("Hanya boleh dijalankan pada tenant staging Jogja yang dituju")

    async with get_session_factory()() as session:
        org = await session.scalar(select(Organization).where(Organization.slug == ORG_SLUG))
        if org is None:
            raise SystemExit(f"Tenant {ORG_SLUG} tidak ditemukan")
        branches = (
            await session.scalars(
                select(Branch).where(Branch.org_id == org.id).order_by(Branch.code).with_for_update()
            )
        ).all()
        by_code = {branch.code: branch for branch in branches}
        if set(by_code) == {code for code, _ in BRANCHES}:
            print("branches=already_reconciled")
            return
        if set(by_code) != {"YK-01", "YK-02"}:
            raise SystemExit(f"Kode cabang tidak sesuai prasyarat: {sorted(by_code)}")

        main, old_secondary = by_code["YK-01"], by_code["YK-02"]
        applications = (
            await session.scalars(select(LoanApplication).where(LoanApplication.org_id == org.id))
        ).all()
        if len(applications) != 12 or any(
            not item.application_no.startswith("PG-2610-")
            or item.branch_id not in {main.id, old_secondary.id}
            for item in applications
        ):
            raise SystemExit("Pengajuan tenant berubah; relokasi otomatis dibatalkan")

        branch_refs = await count_references(session, "branches", [old_secondary.id])
        allowed = {
            "loan_applications.branch_id",
            "staff_assignments.branch_id",
            "cashboxes.branch_id",
            "custody_locations.branch_id",
        }
        unexpected = {key: count for key, count in branch_refs.items() if key not in allowed}
        if unexpected:
            raise SystemExit(f"Cabang lama punya referensi lain; periksa manual: {unexpected}")

        cashboxes = (
            await session.scalars(select(Cashbox).where(Cashbox.org_id == org.id))
        ).all()
        locations = (
            await session.scalars(select(CustodyLocation).where(CustodyLocation.org_id == org.id))
        ).all()
        main_cashboxes = [item for item in cashboxes if item.branch_id == main.id]
        secondary_cashboxes = [item for item in cashboxes if item.branch_id == old_secondary.id]
        main_locations = [item for item in locations if item.branch_id == main.id]
        secondary_locations = [item for item in locations if item.branch_id == old_secondary.id]
        if any(
            len(group) != 1
            for group in (main_cashboxes, secondary_cashboxes, main_locations, secondary_locations)
        ) or len(cashboxes) != 2 or len(locations) != 2:
            raise SystemExit("Master kas atau penyimpanan berubah; periksa manual")
        if secondary_cashboxes[0].balance != Decimal(0):
            raise SystemExit("Saldo kas cabang lama tidak nol; periksa manual")
        cash_refs = await count_references(session, "cashboxes", [secondary_cashboxes[0].id])
        location_refs = await count_references(session, "custody_locations", [secondary_locations[0].id])
        if cash_refs or location_refs:
            raise SystemExit(
                f"Kas atau lokasi penyimpanan sudah dipakai; periksa manual: {cash_refs}, {location_refs}"
            )

        assignments = (
            await session.scalars(select(StaffAssignment).where(StaffAssignment.org_id == org.id))
        ).all()
        if len(assignments) != 3 or any(
            item.branch_id not in {main.id, old_secondary.id} for item in assignments
        ):
            raise SystemExit("Penugasan petugas berubah; periksa manual")
        identity = [(item.user_id, item.operational_role) for item in assignments]
        if len(identity) != len(set(identity)):
            raise SystemExit("Peran petugas akan duplikat di cabang utama")

        for item in applications:
            item.branch_id = main.id
        for item in assignments:
            item.branch_id = main.id
        await session.delete(secondary_cashboxes[0])
        await session.delete(secondary_locations[0])

        main.code, main.name = BRANCHES[0]
        main.city, main.address = "DI Yogyakarta", None
        old_secondary.code, old_secondary.name = BRANCHES[1]
        old_secondary.city, old_secondary.address = "DI Yogyakarta", None
        main_cashboxes[0].code = "CASH-01-UAD-K4"
        main_cashboxes[0].name = f"Kas {main.name}"
        main_locations[0].code = "VAULT-01-UAD-K4"
        main_locations[0].name = f"Vault {main.name}"
        for code, name in BRANCHES[2:]:
            session.add(Branch(org_id=org.id, code=code, name=name, city="DI Yogyakarta"))

        await session.flush()
        if dry_run:
            await session.rollback()
            print("dry_run=ok branches=5 applications_main=12 secondary_activity=0")
            return
        await session.commit()
        print("reconcile=complete branches=5 applications_main=12 secondary_activity=0")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(reconcile(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
