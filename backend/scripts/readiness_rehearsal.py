"""Run a non-destructive PostgreSQL backup, restore, and migration rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL, make_url

from dogeapi.settings import get_settings

KEY_TABLES = (
    "organizations",
    "users",
    "loan_applications",
    "loan_accounts",
    "journal_entries",
    "evidence_files",
    "approval_requests",
)


def _command(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"PostgreSQL utility {name} was not found on PATH")
    return resolved


def _run(args: list[str], *, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Command failed ({Path(args[0]).name}): {message[-2000:]}")
    return result


def _connection_kwargs(url: URL, database: str) -> dict[str, object]:
    return {
        "host": url.host or "localhost",
        "port": url.port or 5432,
        "dbname": database,
        "user": url.username,
        "password": url.password,
    }


def _database_url(url: URL, database: str, driver: str) -> str:
    return url.set(drivername=driver, database=database).render_as_string(hide_password=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-backup", action="store_true", help="Retain the local dump after successful restore")
    args = parser.parse_args()
    backend_root = Path(__file__).resolve().parents[1]
    project_root = backend_root.parent
    started_at = datetime.now(UTC)
    stamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    evidence_dir = project_root / ".artifacts" / "readiness"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    backup_path = evidence_dir / f"privgadai-{stamp}.dump"
    evidence_path = evidence_dir / f"rehearsal-{stamp}.json"

    source_url = make_url(get_settings().DATABASE_URL_SYNC)
    if source_url.get_backend_name() != "postgresql" or not source_url.database:
        raise RuntimeError("Readiness rehearsal requires a PostgreSQL DATABASE_URL_SYNC")
    temporary_database = f"privgadai_rehearsal_{uuid4().hex[:10]}"
    admin_database = "postgres" if source_url.database != "postgres" else "template1"
    env = os.environ.copy()
    if source_url.password:
        env["PGPASSWORD"] = source_url.password
    common = ["--host", source_url.host or "localhost", "--port", str(source_url.port or 5432)]
    if source_url.username:
        common.extend(["--username", source_url.username])

    evidence: dict[str, object] = {
        "started_at": started_at.isoformat(),
        "source": {"host": source_url.host, "port": source_url.port, "database": source_url.database},
        "temporary_database": temporary_database,
        "status": "running",
    }
    started = time.perf_counter()
    created = False
    try:
        dump_started = time.perf_counter()
        _run(
            [_command("pg_dump"), *common, "--format=custom", "--file", str(backup_path), source_url.database],
            env=env,
            cwd=backend_root,
        )
        dump_seconds = time.perf_counter() - dump_started
        digest = hashlib.sha256(backup_path.read_bytes()).hexdigest()
        with psycopg.connect(**_connection_kwargs(source_url, admin_database), autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(temporary_database)))
        created = True

        restore_started = time.perf_counter()
        _run(
            [
                _command("pg_restore"),
                *common,
                "--dbname",
                temporary_database,
                "--no-owner",
                "--no-privileges",
                str(backup_path),
            ],
            env=env,
            cwd=backend_root,
        )
        restore_seconds = time.perf_counter() - restore_started

        rehearsal_env = env.copy()
        rehearsal_env["DATABASE_URL_SYNC"] = _database_url(source_url, temporary_database, "postgresql+psycopg")
        rehearsal_env["DATABASE_URL"] = _database_url(source_url, temporary_database, "postgresql+asyncpg")
        migration = _run([sys.executable, "-m", "alembic", "upgrade", "head"], env=rehearsal_env, cwd=backend_root)
        migration_check = _run([sys.executable, "-m", "alembic", "check"], env=rehearsal_env, cwd=backend_root)

        counts: dict[str, int] = {}
        with psycopg.connect(**_connection_kwargs(source_url, temporary_database)) as connection:
            for table in KEY_TABLES:
                row = connection.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()
                counts[table] = int(row[0]) if row else 0
            revision_row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
            revision = revision_row[0] if revision_row else None

        evidence.update(
            {
                "status": "passed",
                "completed_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "backup": {
                    "sha256": digest,
                    "size_bytes": backup_path.stat().st_size,
                    "duration_seconds": round(dump_seconds, 3),
                    "retained": args.keep_backup,
                },
                "restore": {"duration_seconds": round(restore_seconds, 3), "table_counts": counts},
                "migration": {
                    "revision": revision,
                    "upgrade_head": "passed" if migration.returncode == 0 else "failed",
                    "schema_check": "passed" if migration_check.returncode == 0 else "failed",
                },
            }
        )
        return 0
    except Exception as exc:
        evidence.update(
            {
                "status": "failed",
                "completed_at": datetime.now(UTC).isoformat(),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "error": str(exc),
            }
        )
        return 1
    finally:
        if created:
            with psycopg.connect(**_connection_kwargs(source_url, admin_database), autocommit=True) as connection:
                connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(temporary_database)))
        if backup_path.exists() and not args.keep_backup:
            backup_path.unlink()
        evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"status": evidence["status"], "evidence": str(evidence_path)}, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
