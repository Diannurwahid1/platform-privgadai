# PrivGadai

PrivGadai adalah aplikasi operasional pergadaian untuk PT Murah Gadai Jogja. Repository ini memuat portal nasabah, workspace petugas, API, dan layanan OCR KTP. Fondasinya berasal dari `ai-template-main`; alur pinjaman dan agunan disesuaikan dengan blueprint PrivGadai di [`docs/enterprise`](docs/enterprise/README.md).

**Status:** pilot internal. Kode ini belum merupakan bukti kesiapan produksi atau persetujuan format pelaporan regulator. Gerbang rilis dan pekerjaan operasional yang harus dibuktikan tercatat di [runbook production readiness](docs/enterprise/09-production-readiness.md).

## Komponen

| Direktori | Fungsi |
| --- | --- |
| `frontend/` | Next.js: login petugas, operasi mitra, dan portal borrower `/borrower`. |
| `backend/` | FastAPI, SQLAlchemy/Alembic, PostgreSQL, tenant dan cabang, KYC, proses gadai, appraisal, kas, audit, serta API. |
| `ocr_service/` | PaddleOCR internal untuk membaca KTP; hasil OCR tetap diperiksa petugas. |
| `docs/enterprise/` | Audit, rancangan modul, kontrol, roadmap, dan runbook. |
| `admin/` | Portal admin warisan fondasi; tidak diperlukan untuk alur borrower. |

Portal borrower memakai **satu organisasi yang dikonfigurasi** melalui `BORROWER_ORG_SLUG`. Nasabah mengunggah KTP, memeriksa isian OCR, menunggu keputusan KYC petugas, lalu dapat meminta estimasi barang dan mengirim pengajuan. Estimasi AI adalah bantuan awal; keputusan nilai, jumlah pinjaman, dan tenor tetap melalui petugas.

## Menjalankan lokal tanpa Docker

Prasyarat: PostgreSQL lokal, Python 3.12 dan [`uv`](https://docs.astral.sh/uv/), serta Bun untuk frontend. Layanan OCR membutuhkan Python 3.11 dan dependensi PaddleOCR tersendiri. Siapkan database kosong `privgadai`, lalu pasang extension dari `infra/postgres/init.sql` pada database tersebut.

1. Salin `.env.example` menjadi `.env` di akar repository. Isi `DATABASE_URL`, `DATABASE_URL_SYNC`, `JWT_SECRET_KEY`, `PII_ENCRYPTION_KEY`, dan `BORROWER_ORG_SLUG` sesuai lingkungan. `.env` diabaikan Git. URL PostgreSQL harus meng-encode karakter khusus pada password.
2. Jalankan backend dari `backend/`:

   ```powershell
   uv sync --frozen --python 3.12
   uv run alembic upgrade head
   uv run uvicorn dogeapi.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. Salin `frontend/.env.example` menjadi `frontend/.env.local`. Jalankan frontend dari `frontend/`:

   ```powershell
   bun install --frozen-lockfile
   bun run dev
   ```

4. Buka `http://localhost:3000/login` untuk petugas. Daftarkan organisasi, buat cabang, produk, dan kategori aset dari workspace petugas. Set `BORROWER_ORG_SLUG` ke slug organisasi itu, lalu restart backend. Portal nasabah berada di `http://localhost:3000/borrower`.
5. Jika memakai KYC OCR, jalankan layanan di [`ocr_service/README.md`](ocr_service/README.md), set `KYC_OCR_PROVIDER=paddle_http`, dan pastikan `KYC_OCR_BASE_URL` menuju layanan tersebut. Tanpa OCR, data KTP dapat diisi manual dan tetap harus diperiksa petugas.

Skrip `backend/scripts/seed_privgadai_demo.py --org <slug>` hanya untuk **data sintetis development** setelah organisasi dibuat. Jangan jalankan pada database produksi.

API tersedia di `http://localhost:8000/docs`. `GET /healthz` untuk liveness; `GET /readyz` memeriksa database, token store, dan revisi migrasi.

## Konfigurasi AI

`BYNARA_API_KEY` dan `TAVILY_API_KEY` adalah variabel **server-side** di lingkungan backend. Bynara menangani analisis visual/penalaran; Tavily memasok beberapa pembanding harga pasar. Simpan kunci di secret manager atau environment server, jangan di file yang di-commit dan jangan memakai awalan `NEXT_PUBLIC_`. Nilai perkiraan dapat berubah setelah penaksiran manusia.

## Persiapan server

1. Siapkan PostgreSQL, TLS/reverse proxy, penyimpanan privat untuk bukti dan KTP, secret manager, backup yang telah diuji restore, serta process manager untuk backend, frontend, dan OCR bila diaktifkan.
2. Set environment produksi sesuai [runbook](docs/enterprise/09-production-readiness.md). Backend mewajibkan `APP_ENV=production`, `BUILD_SHA` rilis, secret JWT kuat, `PII_ENCRYPTION_KEY`, cookie aman, ClamAV, dan MFA untuk operasi sensitif. Set `INTERNAL_API_BASE_URL` di proses frontend ke alamat backend privat; URL publik dan CORS harus sesuai domain HTTPS.
3. Instal dependensi dari lockfile, buat backup, jalankan `uv run alembic upgrade head`, lalu build frontend dengan `bun run build`. Jalankan proses aplikasi dengan restart policy; jangan memakai `--reload` atau `bun run dev` di server produksi.
4. Buka trafik setelah `/healthz` dan `/readyz` berhasil. Lakukan smoke test per peran, uji backup/restore, keamanan, dan UAT sebelum memakai data nasabah nyata.

Repository ini belum menyediakan artefak deploy server yang otomatis. Detail operasional dan gerbang yang belum lulus ada di [runbook](docs/enterprise/09-production-readiness.md). Modul OJK/SLIK masih berupa rancangan dan workspace internal, bukan generator atau kanal submission resmi.

## Pemeriksaan sebelum rilis

```powershell
cd backend
uv run pytest
uv run ruff check .

cd ../frontend
bun run typecheck
bun run lint
bun run test
bun run build
```

## Lisensi dan asal kode

Fondasi `ai-template-main` karya Yasser Tahiri berlisensi MIT; pemberitahuan hak cipta dipertahankan di [`LICENSE`](LICENSE). Repository GitHub tujuan juga memiliki pemberitahuan MIT milik Xiao Yan. `lending-develop` dipakai sebagai referensi proses dan model, tidak disalin sebagai backend kedua.
