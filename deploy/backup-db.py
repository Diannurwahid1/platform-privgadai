"""Create a private PostgreSQL dump before a staging migration."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from dogeapi.settings import get_settings


def main(destination_dir: Path) -> None:
    destination_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(destination_dir, 0o700)
    url = make_url(get_settings().DATABASE_URL_SYNC)
    if not url.database or not url.username:
        raise SystemExit("Database URL is incomplete")
    target = destination_dir / f"privgadai-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.dump"
    environment = os.environ.copy()
    environment["PGPASSWORD"] = url.password or ""
    subprocess.run(
        [
            "pg_dump", "--format=custom", "--no-owner", "--no-acl",
            "--host", url.host or "localhost", "--port", str(url.port or 5432),
            "--username", url.username, "--dbname", url.database, "--file", str(target),
        ],
        env=environment,
        check=True,
    )
    os.chmod(target, 0o600)
    print(f"Backup saved: {target}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: backup-db.py PRIVATE_BACKUP_DIR")
    main(Path(sys.argv[1]))
