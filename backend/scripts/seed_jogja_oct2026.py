"""Populate the isolated staging tenant with a traceable October 2026 scenario.

The people, identity checks, valuations, and applications created here are
synthetic. They must never be submitted as regulatory or production records.
No acceptance, disbursement, cash posting, or on-chain evidence is fabricated.

Run from backend:
    .venv/bin/python scripts/seed_jogja_oct2026.py --dry-run
    .venv/bin/python scripts/seed_jogja_oct2026.py
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from dogeapi.auth.passwords import hash_password
from dogeapi.db import get_session_factory
from dogeapi.models import (
    ApplicationStatusHistory,
    Asset,
    AssetCategory,
    Borrower,
    Branch,
    CustodyLocation,
    DebtorProfile,
    HumanAppraisal,
    KycEvent,
    KycVerification,
    LoanApplication,
    LoanProduct,
    Membership,
    Offer,
    Organization,
    RegulatoryReportTemplate,
    Role,
    StaffAssignment,
    User,
)
from dogeapi.operations import erp_service
from dogeapi.settings import get_settings

JAKARTA = ZoneInfo("Asia/Jakarta")
ORG_SLUG = "murah-gadai-jogja"
ORG_NAME = "PT Gadai Murah Jogja"
OPERATOR_EMAIL = "operasional@privgadai.web.id"
SEED_PREFIX = "PG-2610"


def local_time(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=JAKARTA).astimezone(UTC)


@dataclass(frozen=True)
class Scenario:
    day: int
    hour: int
    minute: int
    name: str
    category: str
    brand: str
    model: str
    grade: str
    requested: int
    indicative: int
    stage: str
    branch: int
    reason: str


SCENARIOS = (
    Scenario(
        20,
        8,
        35,
        "Retno Wulandari",
        "smartphone",
        "Apple",
        "iPhone 13 Pro 256GB",
        "B",
        6_500_000,
        9_200_000,
        "submitted",
        0,
        "Kebutuhan usaha kecil",
    ),
    Scenario(
        20,
        9,
        10,
        "Arif Nugroho",
        "emas",
        "Antam",
        "Logam Mulia 10 gram",
        "A",
        12_000_000,
        17_400_000,
        "under_review",
        1,
        "Modal kerja",
    ),
    Scenario(
        20,
        9,
        40,
        "Dwi Puspitasari",
        "laptop",
        "ASUS",
        "Vivobook 14 OLED",
        "B",
        4_000_000,
        6_800_000,
        "appraisal",
        0,
        "Biaya pendidikan",
    ),
    Scenario(
        20,
        10,
        5,
        "Sri Rahayu",
        "emas",
        "UBS",
        "Logam Mulia 5 gram",
        "A",
        5_500_000,
        8_400_000,
        "offered",
        0,
        "Modal usaha",
    ),
    Scenario(
        20,
        11,
        15,
        "Andika Pratama",
        "smartphone",
        "Samsung",
        "Galaxy S22 128GB",
        "C",
        8_000_000,
        5_600_000,
        "rejected",
        1,
        "Kebutuhan mendesak",
    ),
    Scenario(
        20,
        13,
        20,
        "Nadia Permata",
        "kamera",
        "Sony",
        "Alpha A6400",
        "B",
        6_000_000,
        9_500_000,
        "offered",
        1,
        "Modal produksi",
    ),
    Scenario(
        20,
        14,
        0,
        "Citra Ayu Lestari",
        "laptop",
        "Lenovo",
        "ThinkPad X1 Carbon",
        "B",
        5_000_000,
        8_000_000,
        "under_review",
        0,
        "Biaya operasional",
    ),
    Scenario(
        21,
        8,
        5,
        "Bagus Maulana",
        "jam tangan",
        "Tissot",
        "PRX Powermatic 80",
        "B",
        7_000_000,
        11_200_000,
        "submitted",
        1,
        "Modal kerja",
    ),
    Scenario(
        21,
        8,
        20,
        "Wulan Safitri",
        "emas",
        "Antam",
        "Logam Mulia 5 gram",
        "A",
        5_000_000,
        8_400_000,
        "appraisal",
        0,
        "Biaya keluarga",
    ),
    Scenario(
        21,
        8,
        50,
        "Fajar Kurniawan",
        "smartphone",
        "Apple",
        "iPhone 14 128GB",
        "B",
        5_500_000,
        8_800_000,
        "submitted",
        1,
        "Modal usaha",
    ),
    Scenario(
        21,
        9,
        15,
        "Nanda Larasati",
        "laptop",
        "Apple",
        "MacBook Air M2",
        "B",
        7_000_000,
        11_500_000,
        "appraisal",
        0,
        "Biaya pendidikan",
    ),
    Scenario(
        21,
        9,
        45,
        "Yusuf Anwar",
        "kamera",
        "Canon",
        "EOS R50",
        "B",
        4_500_000,
        7_200_000,
        "under_review",
        1,
        "Modal produksi",
    ),
)


async def seed(*, dry_run: bool) -> None:
    settings = get_settings()
    if settings.APP_ENV != "staging" or settings.BORROWER_ORG_SLUG != ORG_SLUG:
        raise SystemExit("Seed hanya boleh dijalankan pada tenant staging Jogja yang dituju")
    async with get_session_factory()() as session:
        org = await session.scalar(select(Organization).where(Organization.slug == ORG_SLUG))
        if org is None:
            raise SystemExit(f"Tenant {ORG_SLUG} belum ada")
        if await session.scalar(select(func.count(LoanApplication.id)).where(LoanApplication.org_id == org.id)):
            raise SystemExit("Tenant sudah memiliki pengajuan; seed dibatalkan agar data tidak tertimpa")
        if await session.scalar(select(func.count(Branch.id)).where(Branch.org_id == org.id)):
            raise SystemExit("Tenant sudah memiliki master cabang; seed dibatalkan agar setup tidak tertimpa")
        if await session.scalar(select(User.id).where(User.email == OPERATOR_EMAIL)):
            raise SystemExit("Akun operasional sudah ada; seed dibatalkan")

        owner_id = await session.scalar(
            select(Membership.user_id).where(Membership.org_id == org.id, Membership.role == Role.OWNER).limit(1)
        )
        if owner_id is None:
            raise SystemExit("Tenant belum memiliki owner")

        org.name = ORG_NAME
        password = secrets.token_urlsafe(24)
        operator = User(
            email=OPERATOR_EMAIL,
            password_hash=hash_password(password),
            full_name="Admin Operasional",
            is_active=True,
            is_superadmin=False,
        )
        session.add(operator)
        await session.flush()
        session.add(Membership(user_id=operator.id, org_id=org.id, role=Role.ADMIN))

        master_at = local_time(20, 8)
        branches = [
            Branch(
                org_id=org.id,
                code="YK-01",
                name="Cabang Kota Yogyakarta",
                city="Yogyakarta",
                address="Area Kotabaru, Kota Yogyakarta; alamat rinci perlu dikonfirmasi",
                created_at=master_at,
            ),
            Branch(
                org_id=org.id,
                code="YK-02",
                name="Cabang Sleman",
                city="Sleman",
                address="Area Depok, Kabupaten Sleman; alamat rinci perlu dikonfirmasi",
                created_at=master_at,
            ),
        ]
        session.add_all(branches)
        await session.flush()
        session.add_all(
            AssetCategory(
                org_id=org.id,
                code=code,
                name=name,
                requires_serial_number=serial,
                created_at=master_at,
            )
            for code, name, serial in (
                ("smartphone", "Smartphone", True),
                ("laptop", "Laptop", True),
                ("emas", "Emas dan perhiasan", False),
                ("kamera", "Kamera", True),
                ("jam tangan", "Jam tangan", True),
            )
        )
        products = [
            LoanProduct(
                org_id=org.id,
                code="GADAI-REG-30",
                name="Gadai Reguler 30-60 Hari",
                min_amount=Decimal("500000"),
                max_amount=Decimal("25000000"),
                max_ltv_percent=Decimal("75"),
                allowed_tenors_days=[30, 60],
                service_fee_percent=Decimal("5"),
                created_at=master_at,
            ),
            LoanProduct(
                org_id=org.id,
                code="GADAI-REG-90",
                name="Gadai Reguler 90-120 Hari",
                min_amount=Decimal("1000000"),
                max_amount=Decimal("50000000"),
                max_ltv_percent=Decimal("70"),
                allowed_tenors_days=[90, 120],
                service_fee_percent=Decimal("5"),
                created_at=master_at,
            ),
        ]
        session.add_all(products)
        await session.flush()

        for branch in branches:
            session.add(
                CustodyLocation(
                    org_id=org.id,
                    branch_id=branch.id,
                    code=f"VAULT-{branch.code}",
                    name=f"Vault {branch.name}",
                    location_type="branch_vault",
                    created_at=master_at,
                )
            )
            await erp_service.ensure_finance_masters(session, org.id, branch.id)
        session.add_all(
            [
                StaffAssignment(
                    org_id=org.id, user_id=owner_id, branch_id=branches[0].id, operational_role="ops_admin"
                ),
                StaffAssignment(
                    org_id=org.id, user_id=operator.id, branch_id=branches[0].id, operational_role="reviewer"
                ),
                StaffAssignment(
                    org_id=org.id, user_id=operator.id, branch_id=branches[1].id, operational_role="branch_manager"
                ),
            ]
        )
        session.add_all(
            [
                RegulatoryReportTemplate(
                    org_id=org.id,
                    report_type=report_type,
                    code=code,
                    name=name,
                    version="draft-2026.10",
                    effective_from=date(2026, 10, 20),
                    mapping_schema={"status": "draft", "source": "sandbox_synthetic"},
                    validation_rules=[],
                    status="draft",
                )
                for report_type, code, name in (
                    ("OJK", "OJK-MONTHLY-DRAFT", "Persiapan laporan bulanan OJK"),
                    ("SLIK", "SLIK-DRAFT", "Persiapan data SLIK"),
                )
            ]
        )

        stage_paths = {
            "submitted": ["submitted"],
            "under_review": ["submitted", "under_review"],
            "appraisal": ["submitted", "under_review", "appraisal"],
            "offered": ["submitted", "under_review", "appraisal", "offered"],
            "rejected": ["submitted", "under_review", "rejected"],
        }
        for index, row in enumerate(SCENARIOS, start=1):
            start = local_time(row.day, row.hour, row.minute)
            reference = f"SBOX-2610-{index:04d}"
            borrower = Borrower(
                org_id=org.id,
                customer_reference=reference,
                full_name=row.name,
                phone_masked=f"08•• •••• {1000 + index}",
                created_at=start,
            )
            session.add(borrower)
            await session.flush()
            session.add(
                DebtorProfile(
                    org_id=org.id,
                    borrower_id=borrower.id,
                    risk_status="normal",
                    risk_notes="SANDBOX_SYNTHETIC: identitas dan transaksi bukan data nasabah nyata.",
                    created_at=start,
                )
            )
            application = LoanApplication(
                org_id=org.id,
                branch_id=branches[row.branch].id,
                borrower_id=borrower.id,
                assigned_user_id=operator.id,
                product_id=products[0].id,
                application_no=f"{SEED_PREFIX}-{index:04d}",
                status=row.stage,
                priority="high" if row.stage == "rejected" else "normal",
                asset_category=row.category,
                requested_amount=Decimal(row.requested),
                requested_tenor_days=30,
                purpose=row.reason,
                revision=len(stage_paths[row.stage]),
                submitted_at=start,
                sla_due_at=start + timedelta(hours=24),
                created_at=start,
            )
            session.add(application)
            await session.flush()
            session.add(
                Asset(
                    org_id=org.id,
                    application_id=application.id,
                    asset_code=f"AST-2610-{index:04d}",
                    category=row.category,
                    brand=row.brand,
                    model=row.model,
                    condition_grade=row.grade,
                    indicative_value=Decimal(row.indicative),
                    collateral_status="with_customer",
                    created_at=start,
                )
            )
            path = stage_paths[row.stage]
            for step, state in enumerate(path):
                event_at = start + timedelta(minutes=step * 45)
                session.add(
                    ApplicationStatusHistory(
                        org_id=org.id,
                        application_id=application.id,
                        actor_user_id=None if step == 0 else operator.id,
                        from_status=path[step - 1] if step else None,
                        to_status=state,
                        note=(
                            "Skenario operasional sintetis untuk pemeriksaan alur."
                            if state != "rejected"
                            else "Nilai diminta melebihi batas agunan dan tidak dilanjutkan."
                        ),
                        created_at=event_at,
                    )
                )

            if row.stage in {"appraisal", "offered"}:
                fingerprint = hashlib.sha256(f"SBOX-KYC:{reference}".encode()).hexdigest()
                verification = KycVerification(
                    org_id=org.id,
                    borrower_id=borrower.id,
                    initiated_by_user_id=operator.id,
                    reviewed_by_user_id=owner_id,
                    document_type="ktp",
                    nik_fingerprint=fingerprint,
                    national_id_ciphertext=None,
                    national_id_masked=f"XXXXXXXXXXXX{index:04d}",
                    legal_name=row.name,
                    birth_place="Yogyakarta",
                    birth_date=date(1990, 1, min(index, 28)),
                    gender="female" if index % 2 else "male",
                    address="Wilayah DI Yogyakarta; alamat sintetis",
                    province="DI Yogyakarta",
                    city="Yogyakarta",
                    occupation="Wiraswasta",
                    verification_method="sandbox_seed",
                    status="verified",
                    risk_level="standard",
                    decision_reason="SANDBOX_SYNTHETIC: bukan hasil verifikasi KTP atau Dukcapil.",
                    reviewed_at=start + timedelta(minutes=60),
                    expires_at=local_time(21, 23) + timedelta(days=365),
                    created_at=start,
                )
                session.add(verification)
                await session.flush()
                session.add(
                    KycEvent(
                        org_id=org.id,
                        verification_id=verification.id,
                        actor_user_id=owner_id,
                        event_type="sandbox_seed",
                        from_status="pending_documents",
                        to_status="verified",
                        reason="Skenario sintetis internal; tidak boleh dipakai sebagai verifikasi identitas nyata.",
                        occurred_at=start + timedelta(minutes=60),
                    )
                )
                market = Decimal(row.indicative)
                liquidation = (market * Decimal("0.80")).quantize(Decimal("1"))
                recommended = min(
                    Decimal(row.requested),
                    (liquidation * Decimal("0.75")).quantize(Decimal("1")),
                )
                session.add(
                    HumanAppraisal(
                        org_id=org.id,
                        application_id=application.id,
                        appraiser_user_id=operator.id,
                        revision=1,
                        market_value=market,
                        liquidation_value=liquidation,
                        recommended_loan=recommended,
                        condition_grade=row.grade,
                        rationale="Penaksiran skenario sintetis; inspeksi fisik dan bukti pembanding aktual tetap diperlukan.",
                        status="final",
                        created_at=start + timedelta(minutes=90),
                    )
                )
                if row.stage == "offered":
                    principal = recommended
                    fee = (principal * Decimal("0.05")).quantize(Decimal("1"))
                    session.add(
                        Offer(
                            org_id=org.id,
                            application_id=application.id,
                            created_by_user_id=owner_id,
                            version=1,
                            principal_amount=principal,
                            tenor_days=30,
                            service_fee_amount=fee,
                            total_due_amount=principal + fee,
                            expires_at=local_time(23, 17),
                            agreement_version="draft-2026.10",
                            decision_reason="Kisaran penawaran untuk skenario sintetis; belum disetujui borrower.",
                            status="offered",
                            created_at=start + timedelta(minutes=135),
                        )
                    )

        await session.flush()
        if dry_run:
            await session.rollback()
            print(f"dry_run=ok branches={len(branches)} products={len(products)} applications={len(SCENARIOS)}")
            return
        await session.commit()
        print(
            f"seed=complete org={ORG_SLUG} branches={len(branches)} products={len(products)} applications={len(SCENARIOS)}"
        )
        print(f"operator_login={OPERATOR_EMAIL}")
        print(f"operator_password={password}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(seed(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
