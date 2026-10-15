# PrivGadai

Codebase awal untuk MVP B2B SaaS PrivGadai. Rancangan produk dan urutan pengerjaan mengikuti `../PrivGadai_Technical_Architecture_Blueprint_V3_Lengkap.pdf` dan `../TASK.md`.

**Status:** fondasi SaaS sudah disalin dari `../ai-template-main/`. Modul transaksi gadai, Collateral Passport, AI appraisal, dan proof registry belum diimplementasikan. Gunakan data sintetis untuk semua pengujian.

## Arsitektur yang dituju

- Satu frontend Next.js/PWA untuk portal nasabah, mitra, petugas, dan admin platform.
- Satu backend FastAPI modular monolith, SQLAlchemy/Alembic, dan PostgreSQL multi-tenant.
- Worker untuk pekerjaan asinkron, storage privat untuk evidence, AI dengan review penaksir manusia, dan proof EVM testnet opsional. Token auth jangka pendek saat ini tersimpan di PostgreSQL; queue produksi belum dibuat.
- Lembaga mitra yang berizin tetap mengambil keputusan gadai dan menguasai proses fisik serta keuangan.

## Struktur saat ini

| Path | Kondisi |
| --- | --- |
| `backend/` | Auth, organisasi/tenant dasar, audit HTTP, admin, dan migrasi dari template. Domain PrivGadai belum ada. |
| `frontend/` | Frontend tenant dari template; halaman awal telah diberi konteks PrivGadai. Portal per role belum ada. |
| `admin/` | Portal super-admin bawaan template. Akan digabung ke satu pengalaman frontend sesuai V3.0. |
| `infra/` | Konfigurasi Compose warisan template yang tidak dipakai untuk setup lokal. Storage evidence dan worker belum ada. |

Struktur target V3.0 (`apps/web`, `services/backend`, `contracts`, `packages/api-types`, `infrastructure`, `docs`) diterapkan bertahap setelah fondasi dapat diuji. Perubahan lokasi folder tidak boleh memutus jalur migrasi atau build.

## Menjalankan fondasi lokal tanpa Docker

Prasyarat: PostgreSQL lokal pada port 5432, Python 3.12, `uv`, serta Bun atau pnpm untuk frontend. Pengguna PostgreSQL harus dapat membuat database dan extension `uuid-ossp`, `pgcrypto`, `citext`.

1. Buat database `privgadai` pada PostgreSQL lokal dan jalankan `infra/postgres/init.sql` di database itu.
2. Salin `.env.example` ke `.env` di root **codebase ini**. Isi `DATABASE_URL`, `DATABASE_URL_SYNC`, dan `JWT_SECRET_KEY` dengan nilai lokal sendiri. File `.env` diabaikan Git. Biarkan `TOKEN_STORE_BACKEND=postgres`, `FEATURE_RATE_LIMITING=false`, dan `FEATURE_AI_CHAT=false` untuk mode PostgreSQL saja.
3. Dari PowerShell, jalankan backend:

   ```powershell
   cd backend
   python -m uv sync --frozen --python 3.12
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe -m uvicorn dogeapi.main:app --reload
   ```

4. Pada terminal lain, jalankan `pnpm install` lalu `pnpm run dev` dari `frontend/`. Portal admin sementara dapat dijalankan dengan perintah yang sama dari `admin/`.

Frontend: `http://localhost:3000`; API docs: `http://localhost:8000/docs`; admin sementara: `http://localhost:3001`. `GET /readyz` memeriksa database dan token store PostgreSQL.

Tes backend memakai database `privgadai_test` yang dibuat otomatis dari konfigurasi `.env` jika pengguna PostgreSQL memiliki izin. Fitur rate limiting dan AI chat warisan template masih memerlukan Redis; keduanya nonaktif pada mode lokal ini. Jangan memakai data nasabah nyata atau konfigurasi development untuk produksi.

## Pekerjaan berikutnya

Lihat `../TASK.md`. Mulai dari audit fondasi, desain ERD dan tiga state machine, tenant isolation, lalu Sprint 1–8 sesuai Technical Blueprint V3.0.

## Asal kode dan lisensi

Fondasi berasal dari `ai-template-main/` karya Yasser Tahiri, berlisensi MIT. Pemberitahuan hak cipta dan teks lisensi dipertahankan dalam `LICENSE`. `lending-develop/` (Frappe Lending, GPLv3) tidak disalin atau diintegrasikan ke codebase ini.
