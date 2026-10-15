# PrivGadai

Codebase awal untuk MVP B2B SaaS PrivGadai. Rancangan produk dan urutan pengerjaan mengikuti `../PrivGadai_Technical_Architecture_Blueprint_V3_Lengkap.pdf` dan `../TASK.md`.

**Status:** MVP operasional manual sudah tersedia di atas fondasi `../ai-template-main/`: multi-tenant/branch, master data, intake nasabah, review, human appraisal, offer/acceptance, pickup, custody, settlement, incident, evidence privat, dan Collateral Passport. Ekspansi V3.1 menambahkan Debitur & CRM, akad/SBG, loan subledger, teller/cashbox, jurnal double-entry dan reversal, collections, stock opname maker-checker, laporan keuangan/BI, serta template/report run OJK dan SLIK berversi. Modul regulasi masih berupa draft internal dan belum merupakan format atau koneksi submission resmi regulator. AI dan proof registry tetap fase lanjutan. Gunakan data sintetis untuk semua pengujian.

## Arsitektur yang dituju

- Satu frontend Next.js/PWA untuk portal nasabah, mitra, petugas, dan admin platform.
- Satu backend FastAPI modular monolith, SQLAlchemy/Alembic, dan PostgreSQL multi-tenant.
- Worker untuk pekerjaan asinkron, storage privat untuk evidence, AI dengan review penaksir manusia, dan proof EVM testnet opsional. Token auth jangka pendek saat ini tersimpan di PostgreSQL; queue produksi belum dibuat.
- Lembaga mitra yang berizin tetap mengambil keputusan gadai dan menguasai proses fisik serta keuangan.

## Struktur saat ini

| Path | Kondisi |
| --- | --- |
| `backend/` | Auth, tenant/RBAC, master data, tiga state machine, proses pinjaman/agunan, loan subledger, cash/GL, collections, stock opname, reporting, audit domain, evidence privat, admin, migrasi, seed, dan tes tenant. |
| `frontend/` | Partner Operations, portal intake nasabah, Field Agent workspace, Debitur & CRM, Master Data, Applications, Collateral Passport, Finance, Reports, dan Stock Opname. |
| `admin/` | Portal super-admin bawaan template. Akan digabung ke satu pengalaman frontend sesuai V3.0. |
| `infra/` | Konfigurasi Compose warisan template yang tidak dipakai untuk setup lokal. Evidence MVP memakai storage privat lokal `backend/.data/evidence`; worker belum ada. |

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
   .\.venv\Scripts\python.exe scripts\seed_privgadai_demo.py
   .\.venv\Scripts\python.exe -m uvicorn dogeapi.main:app --reload
   ```

4. Pada terminal lain, jalankan `npm install` lalu `npm run dev` dari `frontend/`. Portal admin sementara dapat dijalankan dengan perintah yang sama dari `admin/`.

Frontend: `http://localhost:3000`; API docs: `http://localhost:8000/docs`; admin sementara: `http://localhost:3001`. `GET /readyz` memeriksa database dan token store PostgreSQL.

Tes backend memakai database `privgadai_test` yang dibuat otomatis dari konfigurasi `.env` jika pengguna PostgreSQL memiliki izin. Fitur rate limiting dan AI chat warisan template masih memerlukan Redis; keduanya nonaktif pada mode lokal ini. Jangan memakai data nasabah nyata atau konfigurasi development untuk produksi.

## Route MVP

- Partner shell: `/orgs/[slug]/overview`, `/customers`, `/loans/*`, `/collateral/*`, `/finance/*`, `/reports/*`, `/compliance/*`, `/management/*`.
- Route lama `/applications`, `/collateral`, `/field`, `/finance`, `/reports`, `/inventory`, `/audit-log`, `/master-data`, `/members`, dan `/settings` tetap kompatibel selama migrasi.
- Setiap menu operasional memiliki route unik sehingga hanya satu leaf navigasi aktif.
- Nasabah: `/apply/[slug]`
- API/OpenAPI: `http://localhost:8000/docs`

## Pekerjaan berikutnya

Lihat `../TASK.md`. Fokus hardening berikutnya: object storage terenkripsi, malware scanner, signed URL, MFA sensitif, identitas borrower, offline PWA, backup/restore, pemetaan spesifikasi resmi OJK/SLIK, akuntansi lanjutan, lalu AI decision-support dan proof registry opsional.

## Asal kode dan lisensi

Fondasi berasal dari `ai-template-main/` karya Yasser Tahiri, berlisensi MIT. Pemberitahuan hak cipta dan teks lisensi dipertahankan dalam `LICENSE`. `lending-develop/` (Frappe Lending, GPLv3) tidak disalin atau diintegrasikan ke codebase ini.
