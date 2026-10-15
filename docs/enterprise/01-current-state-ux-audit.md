# 01 — Audit Kondisi Saat Ini

Tanggal audit: 16 Oktober 2026
Ruang lingkup: partner operations di `frontend`, API operasional di `backend`, dua blueprint PrivGadai, dan dua tangkapan layar pengguna.

## Ringkasan eksekutif

Implementasi saat ini sudah membuktikan alur MVP dan isolasi organisasi pada beberapa endpoint. Namun tampilan masih menggabungkan beberapa domain ke satu route, detail record belum tersedia pada area penting, dan kontrol operasional belum cukup untuk penggunaan harian skala enterprise.

Masalah menu aktif ganda berasal dari struktur route, bukan hanya CSS:

| Menu | Route saat ini | Dampak |
|---|---|---|
| Pengajuan | `/applications` | Aktif bersamaan dengan Penaksiran |
| Penaksiran | `/applications` | Tidak memiliki work queue sendiri |
| Teller & Cash | `/finance` | Aktif bersama Collections dan General Ledger |
| Collections | `/finance` | Tanggung jawab bercampur |
| General Ledger | `/finance` | Tanggung jawab bercampur |
| Financial & BI | `/reports` | Aktif bersama OJK & SLIK |
| OJK & SLIK | `/reports` | Tidak memiliki workspace regulator |
| Exceptions | `/applications` | Aktif bersama menu pinjaman |

Logika aktif di layout membandingkan `pathname` dengan `href`. Karena beberapa leaf memakai `href` yang identik, dua atau tiga item wajar terbaca aktif. Solusi wajib adalah memecah route dan kontrak modul, lalu memakai pencocokan `exact` atau `section` secara eksplisit.

## Temuan visual dan interaksi

### A. App shell dan sidebar — P0

- Sidebar tidak dapat collapse/expand dan memakan ruang tetap.
- Logo dan wordmark tidak memiliki batas ukuran yang stabil di semua viewport.
- Scrollbar native tampil dominan; area navigasi dan halaman memiliki pola scroll yang terasa terpisah.
- Tombol keluar berada di footer sidebar tanpa profil pengguna, konteks cabang, atau kontrol sesi yang jelas.
- Seluruh grup selalu terbuka sehingga daftar panjang dan sulit dipindai.
- Navigasi mobile meratakan semua leaf menjadi deretan horizontal panjang.
- Top bar memuat pencarian dan notifikasi yang terlihat interaktif, tetapi belum memiliki perilaku operasional yang lengkap.
- Pada viewport sempit, tabel dapat terpotong ke kanan tanpa pola overflow yang jelas.

### B. Konsistensi halaman — P0

- Judul dan microcopy bercampur bahasa Indonesia dan bahasa Inggris.
- Banyak halaman memakai pola kartu sederhana walaupun pekerjaannya membutuhkan queue, tabel, filter, timeline, bukti, dan aksi.
- Hierarki visual terlalu longgar untuk pekerjaan operasional padat data.
- Status sering berupa pill yang tampak sama penting walaupun urgensinya berbeda.
- Tidak ada pola baku untuk breadcrumb, record header, action bar, side panel, warning, dan approval.
- Empty, error, loading, disabled, read-only, dan partial access belum didefinisikan sebagai satu sistem.

### C. Debitur & CRM — P0

Halaman hanya menampilkan kartu hasil pencarian. Kartu tidak menuju detail debitur dan tidak menyediakan tindakan. Belum ada:

- profil identitas/KYC dan histori perubahan;
- consent beserta versi dokumen dan bukti penerimaan;
- relasi pengajuan, kontrak, agunan, pembayaran, dan keluhan;
- duplikasi CIF, koreksi data, watchlist, dan reason code;
- komunikasi serta janji bayar;
- jejak SLIK per debitur;
- pembatasan cabang dan masking berdasarkan peran.

### D. Audit — P0

Audit saat ini adalah daftar mutasi HTTP berisi `method`, `path`, `status_code`, actor, dan metadata. Data ini berguna untuk investigasi teknis, tetapi tidak menjawab pertanyaan operasional seperti:

- siapa mengubah nilai taksiran, dari berapa menjadi berapa, dan mengapa;
- siapa menyetujui pencairan serta bukti apa yang digunakan;
- kapan barang diterima, dipindahkan rak, dihitung, atau dinyatakan selisih;
- versi template laporan apa yang digunakan dan siapa yang menandatangani;
- tindakan bisnis apa yang gagal, dibatalkan, atau dibalik.

Audit teknis harus tetap ada, tetapi dipisahkan dari buku kejadian bisnis yang append-only.

### E. Settings dan master data — P0

Settings masih menampilkan feature flag boilerplate seperti API keys, billing, dan AI workspace. Master data sudah memiliki form dasar cabang, kategori, produk, lokasi custody, dan assignment, tetapi belum memiliki:

- versi dan tanggal efektif;
- edit/deactivate dengan dampak ke transaksi aktif;
- approval perubahan kebijakan;
- perbandingan versi;
- policy appraisal, limit, fee, SLA, COA, posting rule, nomor dokumen, dan regulator;
- scope tenant/cabang dan hak akses field-level.

### F. Finance, reporting, dan compliance — P0

- Teller, kas, collection, dan GL bercampur pada satu halaman.
- Belum ada closing kas, dual control, rekonsiliasi, reversal workflow, accounting period lock, dan exception queue yang matang.
- Report bersifat ringkasan tampilan; belum ada reporting calendar, data lineage, validation workbench, freeze, approval, checksum, evidence submission, dan acknowledgement.
- Format OJK/SLIK belum boleh disebut resmi hanya karena sistem dapat menghasilkan JSON/CSV generik.

## Kesesuaian dengan dua blueprint

| Area blueprint | Kondisi sekarang | Gap utama |
|---|---|---|
| Partner dashboard | Ada ringkasan dan antrean | Belum role-based, filter cabang belum menyeluruh, action queue terbatas |
| Appraisal | Ada bagian alur | Queue dan detail keputusan penaksir belum berdiri sendiri |
| Collateral & custody | Ada passport/timeline/opname dasar | Mutasi, chain of custody, evidence, discrepancy resolution belum lengkap |
| Customers | Ada daftar | Tidak ada record 360°, consent, history, correction workflow |
| Reports & analytics | Ada overview tipis | Belum ada report catalog, schedule, lineage, export governance |
| Risk & audit | Ada log HTTP | Belum domain event, exception case, approval evidence |
| Support | Belum menjadi modul | Ticket, complaint, SLA, incident belum lengkap |
| Settings | Boilerplate | Kebijakan operasi dan konfigurasi regulator belum ada |
| Multi-tenant dan branch scope | Fondasi tersedia | Perlu pengujian ABAC dan enforcement di seluruh query/action |
| Maker-checker/four-eyes | Sebagian implisit | Belum konsisten dan configurable |

## Risiko bila langsung digunakan untuk operasi nyata

1. Kesalahan otorisasi cabang dapat membuka data lintas unit.
2. Status transaksi dapat berubah tanpa approval dan bukti yang dapat direkonstruksi.
3. Perubahan master data dapat mengubah hasil historis jika tidak diberi versi.
4. Laporan regulator dapat lolos secara teknis tetapi salah secara definisi data.
5. Selisih kas dan agunan sulit diinvestigasi tanpa event serta chain of custody.
6. Operator dapat menjalankan proses di luar urutan SOP karena guard dan checklist belum lengkap.

## Keputusan audit

Status: **lanjut sebagai program enterprise hardening**, dengan urutan app shell → data/record detail → workflow operasional → kontrol → regulator → production readiness.

### Tugas audit yang harus ditutup

- [ ] UX-001: pecah setiap menu leaf ke route unik.
- [ ] UX-002: bangun sidebar responsive yang dapat collapse dan menyimpan preferensi pengguna.
- [ ] UX-003: hilangkan nested scroll dan horizontal clipping.
- [ ] UX-004: tetapkan page anatomy dan komponen enterprise bersama.
- [ ] CRM-001: sediakan daftar, detail, relasi, tindakan, dan riwayat debitur.
- [ ] AUD-001: pisahkan audit teknis dari domain event ledger.
- [ ] CFG-001: ganti settings boilerplate dengan configuration workbench.
- [ ] REG-001: bangun reporting workspace berbasis template resmi terversi.
- [ ] SEC-001: audit enforcement tenant/cabang/role pada seluruh endpoint dan query.
