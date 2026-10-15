# PrivGadai

Codebase awal untuk MVP B2B SaaS PrivGadai. Rancangan produk dan urutan pengerjaan mengikuti `../PrivGadai_Technical_Architecture_Blueprint_V3_Lengkap.pdf` dan `../TASK.md`.

**Status:** fondasi SaaS sudah disalin dari `../ai-template-main/`. Modul transaksi gadai, Collateral Passport, AI appraisal, dan proof registry belum diimplementasikan. Gunakan data sintetis untuk semua pengujian.

## Arsitektur yang dituju

- Satu frontend Next.js/PWA untuk portal nasabah, mitra, petugas, dan admin platform.
- Satu backend FastAPI modular monolith, SQLAlchemy/Alembic, dan PostgreSQL multi-tenant.
- Redis/worker untuk pekerjaan asinkron; storage privat untuk evidence; AI dengan review penaksir manusia; proof EVM testnet opsional.
- Lembaga mitra yang berizin tetap mengambil keputusan gadai dan menguasai proses fisik serta keuangan.

## Struktur saat ini

| Path | Kondisi |
| --- | --- |
| `backend/` | Auth, organisasi/tenant dasar, audit HTTP, admin, dan migrasi dari template. Domain PrivGadai belum ada. |
| `frontend/` | Frontend tenant dari template; halaman awal telah diberi konteks PrivGadai. Portal per role belum ada. |
| `admin/` | Portal super-admin bawaan template. Akan digabung ke satu pengalaman frontend sesuai V3.0. |
| `infra/` | Compose untuk PostgreSQL, Redis, mailpit, API, frontend, dan admin. Storage evidence dan worker belum ada. |

Struktur target V3.0 (`apps/web`, `services/backend`, `contracts`, `packages/api-types`, `infrastructure`, `docs`) diterapkan bertahap setelah fondasi dapat diuji. Perubahan lokasi folder tidak boleh memutus jalur migrasi atau build.

## Menjalankan fondasi lokal

Prasyarat bawaan template: Docker, `uv`, dan `bun`. Perintah di bawah berasal dari fondasi dan perlu diverifikasi pada mesin pengembang:

```bash
cp .env.example .env
make stack-build
make stack-up
make stack-create-admin email=admin@example.com password=<password-lokal>
```

Gateway: `http://localhost:8080`; frontend: `http://localhost:3000`; API docs: `http://localhost:8000/docs`; admin sementara: `http://localhost:3001`.

Jangan memakai akun contoh atau secret contoh untuk lingkungan selain lokal. Konfigurasi `.env.example` adalah contoh development, bukan konfigurasi produksi.

## Pekerjaan berikutnya

Lihat `../TASK.md`. Mulai dari audit fondasi, desain ERD dan tiga state machine, tenant isolation, lalu Sprint 1–8 sesuai Technical Blueprint V3.0.

## Asal kode dan lisensi

Fondasi berasal dari `ai-template-main/` karya Yasser Tahiri, berlisensi MIT. Pemberitahuan hak cipta dan teks lisensi dipertahankan dalam `LICENSE`. `lending-develop/` (Frappe Lending, GPLv3) tidak disalin atau diintegrasikan ke codebase ini.
