# Gap analysis: borrower, AI appraisal, dan penyedia pendanaan

Status audit: 18 Oktober 2026. Dokumen ini membandingkan dua PDF blueprint di root workspace dengan implementasi yang dapat ditelusuri di repository. Label **tersedia** berarti ada kode yang menjalankan bagian alur, bukan bukti siap produksi.

## Keputusan yang memang tertulis di blueprint

| Topik | Sumber blueprint | Konsekuensi produk |
|---|---|---|
| Portal nasabah | Technical V3 hlm. 5–6, 8; Business V2 hlm. 10–11 | PWA mobile-first untuk **nasabah lembaga mitra tertentu** sudah masuk fase 1/P0. Login, beranda, foto aset, pengajuan, status, jadwal, dokumen, dan bantuan adalah pengalaman tersendiri. |
| AI appraisal | Technical V3 hlm. 4, 10, 14; Business V2 hlm. 13–14 | Kualitas gambar, pengenalan kategori, lalu estimasi indikatif berbasis sumber harga yang sah. Keluaran punya status `SUCCESS`, `NEEDS_REVIEW`, atau `UNSUPPORTED`. Penaksir manusia menetapkan nilai akhir. |
| Portal petugas lapangan | Technical V3 hlm. 6–7; Business V2 hlm. 11 | Pengalaman mobile dengan tugas, pemeriksaan identitas, checklist barang, handover, dan insiden; identitas dan izin terpisah dari nasabah. |
| Penyedia dana institusional | Technical V3 hlm. 5; Business V2 hlm. 2, 10, 17, 24 | **Fase 3**, setelah struktur kontrak dan model kewenangan disepakati. Blueprint hanya menetapkan integrasi dan akses portofolio sesuai izin/kontrak; belum menetapkan katalog investasi publik atau mekanisme wallet. |
| Investor ritel | Technical V3 hlm. 5, 15; Business V2 hlm. 2, 10, 27 | **Fase 4** dengan legal gate. Materi contoh “Provider Flow” adalah referensi arah visual, bukan izin untuk menyalakan tombol pendanaan ritel sekarang. |
| Platform | Technical V3 hlm. 1–2, 8; Business V2 hlm. 16 | Satu frontend Next.js dengan beberapa portal dan satu backend FastAPI modular, PostgreSQL multi-tenant. Pemisahan pengalaman tidak mewajibkan backend kedua. Setup lokal mengikuti keputusan proyek: PostgreSQL langsung, tanpa Docker. |

## Yang sudah ada dan yang belum

| Kapabilitas | Bukti di kode | Penilaian dan gap |
|---|---|---|
| Portal staf mitra | `frontend/src/app/orgs/[slug]`, API `backend/src/dogeapi/operations` | Ada shell dan modul operasional; bukan portal nasabah. Kematangan dan gate produksi tetap mengikuti `TASKS.md`. |
| Intake nasabah publik | `frontend/src/app/apply/[slug]/page.tsx` | Hanya formulir sekali kirim. Belum punya akun nasabah, penyimpanan draft, unggah foto aset, beranda, daftar pengajuan, status sendiri, jadwal, pembayaran, dokumen, atau pusat bantuan. Form menerima angka `indicative_value` yang diketik nasabah; ini belum hasil AI. |
| Identitas nasabah | `backend/src/dogeapi/models/operations.py` (`Borrower`), `models/kyc.py`; UI KYC staf | Rekam nasabah/KYC ada untuk operator, tetapi belum ada kredensial, tautan akun-ke-customer, consent/session nasabah, atau kebijakan `self-only` untuk portal. PaddleOCR KTP hanya mengekstrak identitas; **bukan** AI penaksiran barang. |
| Penaksiran manusia | `frontend/src/app/orgs/[slug]/loans/appraisals/page.tsx`, `backend/src/dogeapi/models/mvp.py` (`HumanAppraisal`) | Queue, revisi, bukti, dan approval manusia ada. Hasil AI, sumber pembanding, confidence, override AI, dan evaluasi model belum terhubung. |
| AI aplikasi | `backend/src/dogeapi/ai/router.py`, `frontend/src/app/orgs/[slug]/ai` | Workspace chat/agent generik dari template. Tidak ditemukan tabel `ai_estimations`, job analisis aset, model version, atau endpoint appraisal AI sesuai contoh Technical V3 hlm. 9, 12. |
| Penyedia dana | Tidak ada route `/provider`, akun institusi pendana, mandate/permission portofolio, atau model opportunity/alokasi | Belum ada portal maupun domain pendanaan. Menggunakan akun/role staf mitra untuk pendana akan mencampur boundary data. |
| Petugas lapangan | Ada `frontend/src/app/orgs/[slug]/field/page.tsx` dan modul pickup/custody | Masih berada di shell organisasi. Perlu PWA tugas lapangan khusus seperti blueprint, dengan permission per assignment. |
| PWA dan notifikasi nasabah | Tidak ditemukan manifest/service worker atau pusat notifikasi borrower pada `frontend/src` | Mobile UI dan kemampuan kamera/unggah harus dibangun, lalu notifikasi terikat pada event dan preferensi nasabah. |
| Discovery lintas mitra | Tidak ada route marketplace/discovery atau domain routing mitra | Fase 2 dengan gate kerja sama dan klasifikasi model layanan; fase 1 harus tetap satu mitra per nasabah. |
| Proof Web3 | Blueprint menyebut registry testnet opsional | Perlakukan sebagai workstream terpisah setelah bukti custody dan audit stabil; jangan mengganti audit bisnis dengan klaim “blockchain menjamin aset”. |
| Readiness operasional | `TASKS.md` masih memuat gate terbuka untuk data pembanding AI, bukti custody, integrasi pembayaran, laporan regulator, backup/DR, dan UAT | Portal baru tidak boleh dijadikan dasar label “siap produksi” sebelum kontrol P0 dan pengujian per role selesai. |

## Pemisahan pengalaman dan akses

| Pengguna | Layar masuk | Apa yang boleh dilihat | Batas otorisasi |
|---|---|---|---|
| Staf mitra | `/login` lalu `/orgs/{slug}` | Operasi lembaga sesuai role, cabang, kategori, dan limit | Membership organisasi dan assignment cabang. |
| Nasabah | `/borrower/{slug}/login` lalu `/borrower/{slug}` | Hanya profil, pengajuan, agunan, dokumen, pembayaran, dan tiket miliknya pada mitra itu | Principal nasabah terhubung ke `borrower_id` + `org_id`; object ownership diperiksa di API. |
| Petugas lapangan | `/field/{slug}/login` lalu `/field/{slug}` | Hanya tugas yang ditugaskan kepadanya | Assignment tugas dan cabang, sesi perangkat, checklist dan bukti. |
| Institusi pendana | `/provider/login` lalu `/provider` | Hanya portofolio/opportunity yang secara eksplisit dibagikan berdasarkan kontrak | Entitas institusi, mandate, scope data, consent/disclosure, dan audit akses. Portal transaksional baru diaktifkan setelah fase 3 disetujui. |

**Login perlu berbeda secara pengalaman dan ruang akses.** Identity service dapat tetap satu, tetapi token/sesi harus menyatakan audience dan jenis principal; akun nasabah tidak boleh memperoleh endpoint staf dengan mengganti URL. Satu alamat email pada dua pengalaman tidak boleh otomatis menyatukan hak. Nasabah fase 1 tetap berada dalam konteks satu mitra; discovery lintas mitra baru fase 2 (Technical V3 hlm. 8).

## Sikap terhadap gambar referensi

Gambar yang diberikan menggambarkan 5 layar borrower dan 3 layar provider dengan identitas biru-putih, kartu ringkas, ilustrasi robot, dan navigasi bawah. Itu menjadi **acuan visual kuat** untuk prototipe. Teks “blockchain security”, persentase imbal hasil, wallet, tombol “Danai”, klaim “100% aman”, dan peluang investasi pada mockup tidak boleh dianggap fitur yang sudah sah/siap. Konten finansial harus berasal dari data dan perjanjian yang benar, bukan dekorasi. Kesamaan piksel 100% tidak realistis pada berbagai viewport; kriteria desain adalah kedekatan visual yang direview pada ukuran referensi sekaligus responsif dan dapat diakses.

## Referensi internal

- Sumber primer: [Technical Architecture Blueprint V3](../../../PrivGadai_Technical_Architecture_Blueprint_V3_Lengkap.pdf) dan [Business Blueprint V2](../../../Blueprint_Bisnis_PrivGadai_Lengkap_2026.pdf).
- Implementasi: `frontend/src/app/apply/[slug]/page.tsx`, `frontend/src/app/orgs/[slug]/loans/appraisals/page.tsx`, `backend/src/dogeapi/ai/router.py`, `backend/src/dogeapi/models/mvp.py`, dan `TASKS.md`.
