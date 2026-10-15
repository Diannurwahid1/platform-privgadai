# 09 — Production Readiness dan Runbook Operasi

Dokumen ini mencatat kontrol teknis yang sudah tersedia dan gerbang yang wajib dibuktikan sebelum PrivGadai menerima data nasabah produksi. Menjalankan aplikasi tanpa Docker tetap didukung; layanan aplikasi dijalankan sebagai proses terkelola dan PostgreSQL sebagai system of record.

## Kontrol runtime yang tersedia

| Kontrol | Implementasi | Bukti operasional |
|---|---|---|
| Liveness | `GET /healthz` tanpa akses dependency | HTTP 200, versi, environment, dan build SHA |
| Readiness | `GET /readyz` memeriksa PostgreSQL, token store, serta revisi Alembic | HTTP 200 hanya jika seluruh pemeriksaan lulus; selain itu HTTP 503 |
| Release identity | `BUILD_SHA` wajib bukan `local` pada production | Nilai terlihat pada health/readiness dan dapat dicocokkan dengan release |
| Request correlation | `X-Request-ID` diterima jika valid atau dibuat server | Header yang sama selalu dikembalikan pada response |
| Browser hardening | `nosniff`, deny framing, no-referrer, permissions policy, no-store | Dapat diperiksa dari response API |
| Transport hardening | HSTS aktif pada environment production | Response production memuat `Strict-Transport-Security` |
| Startup guard | secret JWT, secure cookie, kunci enkripsi PII, dan build identity divalidasi | Aplikasi gagal start jika konfigurasi production tidak aman |

## Urutan release tanpa Docker

1. Buat backup PostgreSQL yang dapat direstore dan catat checksum serta waktu backup.
2. Tetapkan artefak release yang immutable dan isi `BUILD_SHA` dari commit/release tersebut.
3. Jalankan migrasi menggunakan virtual environment release: `python -m alembic upgrade head`.
4. Pastikan tabel `alembic_version` sama dengan head yang dibawa artefak.
5. Mulai backend memakai process manager dengan restart policy dan graceful shutdown.
6. Mulai frontend dari hasil build production, bukan development server.
7. Uji `/healthz`, lalu `/readyz`; traffic hanya boleh dibuka setelah readiness HTTP 200.
8. Jalankan smoke test per role pada tenant dan cabang pilot.
9. Pantau error rate, latency, koneksi database, kegagalan login, approval yang macet, dan journal imbalance.

## Konfigurasi minimum production

- `APP_ENV=production`
- `BUILD_SHA=<commit atau release id>`
- `DATABASE_URL` dan `DATABASE_URL_SYNC` memakai user aplikasi dengan hak minimum
- `JWT_SECRET_KEY` acak minimal 32 karakter
- `JWT_COOKIE_SECURE=true`
- `PII_ENCRYPTION_KEY` terpisah dari JWT dan disimpan di secret manager
- `CORS_ORIGINS` hanya domain resmi
- TLS berakhir pada reverse proxy yang dikelola dan meneruskan request ke backend privat
- akun migrasi terpisah dari akun runtime bila lingkungan produksi mengizinkan

## Gerbang yang belum dapat dinyatakan lulus dari kode saja

| Gerbang | Bukti kelulusan |
|---|---|
| Backup dan restore | restore ke lingkungan terisolasi, checksum valid, waktu pemulihan tercatat |
| Disaster recovery | simulasi kehilangan service/database dan hasil RPO/RTO disetujui |
| Load dan soak | hasil pada volume target, p95/p99, error rate, pool saturation |
| Penetration test | laporan pihak berwenang dan seluruh temuan kritis/tinggi ditutup |
| UAT | sign-off per role dan cabang untuk happy path, exception, reversal, dan correction |
| Operational readiness | roster on-call, jalur eskalasi, SOP insiden, SOP akses, pelatihan pengguna |
| Regulatory validation | file periode uji lolos validator resmi dan disetujui fungsi kepatuhan |

## Prosedur insiden singkat

1. Catat waktu, tenant/cabang, `X-Request-ID`, actor, command bisnis, dan dampaknya.
2. Hentikan command berisiko melalui permission atau release control; pertahankan akses baca jika aman.
3. Jangan mengubah audit event, approval event, jurnal, atau custody event yang sudah terbentuk.
4. Lakukan koreksi melalui command reversal/correction resmi dengan alasan dan approval.
5. Rekonsiliasi record sumber, subledger, GL, kas, agunan, dan laporan regulator yang terdampak.
6. Tutup insiden setelah bukti pemulihan, akar masalah, dan tindakan pencegahan disetujui owner.

## Definition of Done Fase 8

PrivGadai baru dapat diberi status siap produksi setelah seluruh gerbang F8 memiliki bukti, owner, tanggal pelaksanaan, hasil, temuan, remediation, dan sign-off. Endpoint readiness adalah kontrol deployment, bukan pengganti UAT, audit keamanan, restore drill, atau persetujuan kepatuhan.
