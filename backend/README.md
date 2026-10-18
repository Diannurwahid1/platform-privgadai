# Backend PrivGadai

FastAPI, PostgreSQL, SQLAlchemy, dan Alembic untuk operasi mitra serta portal borrower. Baca [README utama](../README.md) untuk persiapan database, frontend, OCR, dan deployment.

## Lokal

Siapkan `.env` di akar repository dari `.env.example`; isi URL database, secret, dan `BORROWER_ORG_SLUG`. Dari direktori `backend/`:

```powershell
uv sync --frozen --python 3.12
uv run alembic upgrade head
uv run uvicorn dogeapi.main:app --reload --host 127.0.0.1 --port 8000
```

Setelah organisasi dibuat melalui frontend, `uv run python scripts/seed_privgadai_demo.py --org <slug>` dapat mengisi data sintetis untuk development. Skrip ini tidak untuk produksi.

## Pemeriksaan

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

OpenAPI: `/docs`; liveness: `/healthz`; readiness database, token store, dan migrasi: `/readyz`. Produksi memerlukan environment aman dan proses terkelola sesuai [runbook](../docs/enterprise/09-production-readiness.md). API menolak startup produksi bila secret, cookie, scanner, MFA, atau identitas build belum sesuai persyaratan.
