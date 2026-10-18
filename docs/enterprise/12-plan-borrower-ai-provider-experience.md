# Rencana implementasi: portal nasabah, AI appraisal, dan portal pendana

Dasar keputusan: [gap analysis](./11-blueprint-gap-borrower-ai-funding.md), Technical Architecture Blueprint V3 hlm. 5–15, dan Business Blueprint V2 hlm. 10–17 serta 24. Status awal: **rencana siap dikerjakan**, bukan klaim fitur telah selesai. Backend tetap FastAPI modular monolith, frontend tetap Next.js, database PostgreSQL lokal, tanpa Docker.

## Target hasil

1. Nasabah mitra dapat masuk melalui portal khusus dan menyelesaikan siklus pengajuan hingga melihat status, jadwal, penawaran, dokumen, kewajiban, dan bantuan, tanpa mengakses shell staf.
2. Penaksir mendapat bantuan foto dan data pembanding yang dapat ditelusuri. Estimasi AI tetap indikatif, bisa abstain, dan finalisasi selalu keputusan manusia dengan approval yang berlaku.
3. Desain mengikuti referensi: permukaan putih, biru elektrik/navy, gradien terukur, kartu padat tetapi terbaca, ikon sederhana, ilustrasi robot konsisten, dan navigasi mobile yang jelas.
4. Portal pendana memiliki desain dan autentikasi terpisah; fase awal hanya prototipe dengan data sintetis. Akses institusi terhadap data nyata, opportunity, alokasi, dan transaksi menunggu kontrak, izin, dan keputusan model bisnis fase 3. Investor ritel tetap fase 4.

## Workstream A — fondasi akses multi-portal (P0)

- [ ] **A01 — Kontrak identitas.** Tetapkan principal `staff`, `borrower`, `field_agent`, `institutional_provider`; audience token, logout, reset, MFA sesuai risiko, expiry, device/session policy, dan anti-enumeration. Pertahankan auth staf yang ada tanpa memberi `org:staff` scope kepada nasabah.
- [ ] **A02 — Tautan customer.** Tambah akun nasabah ↔ `borrower_id` ↔ `org_id` dengan verifikasi kepemilikan, aturan duplikat, histori pengaitan, dan revocation. Jangan menggabungkan data nasabah lintas tenant otomatis.
- [ ] **A03 — API self-service.** Buat namespace `/v1/borrower/me/...`; semua list, detail, command, evidence download, dan event stream memakai owner scope server-side. Tidak menerima `borrower_id` bebas dari klien sebagai sumber otorisasi.
- [ ] **A04 — Route dan shell.** `/borrower/{slug}/login`, `/borrower/{slug}/register`, `/borrower/{slug}`, `/borrower/{slug}/apply`, `/borrower/{slug}/applications/{id}`, `/borrower/{slug}/pickups`, `/borrower/{slug}/payments`, `/borrower/{slug}/documents`, `/borrower/{slug}/help`, `/borrower/{slug}/account`. `/` dapat tetap ke login staf; buat pemilihan portal yang jelas di layar masuk tanpa memindahkan sesi antar-audience.
- [ ] **A05 — Uji boundary.** ID tampering, akses silang tenant, dokumen orang lain, sesi staf di borrower, sesi borrower di staf, logout/revoke, link account yang salah, dan job notifikasi lintas tenant harus ditolak.

**Selesai jika:** dua akun nasabah dari tenant/cabang berbeda hanya melihat data miliknya; satu akun staf tidak dapat menyamar menjadi borrower dengan mengubah path. Semua bukti akses tercatat sebagai event bisnis/keamanan.

## Workstream B — alur borrower nyata (P0/P1)

- [ ] **B01 — Onboarding dan identitas.** Halaman pembuka seperti layar 1 referensi: manfaat, identitas mitra yang memberi layanan, langkah proses, syarat dokumen, masuk/daftar, dan kebijakan persetujuan. Gunakan verifikasi kontak sebelum menghubungkan ke CIF. Unggah KTP di awal KYC, jalankan PaddleOCR untuk autofill NIK/nama/tanggal lahir/alamat, tampilkan foto dan hasil ekstraksi untuk koreksi, lalu teruskan ke checker internal yang berbeda. OCR yang gagal menyediakan ulang foto dan jalur manual; hasil OCR sendiri tidak menandai identitas sebagai terverifikasi resmi.
- [ ] **B02 — Beranda.** Layar 2: satu aksi utama “Ajukan gadai”, status pengajuan aktif, tindakan berikutnya, ringkasan kewajiban dari sumber mitra, dokumen, bantuan, dan notifikasi nyata. Empty state membimbing pengajuan pertama.
- [ ] **B03 — Wizard pengajuan.** Layar 3: kategori/atribut, unggah foto barang dengan petunjuk sudut, review kualitas, data identitas/KYC yang sudah disetujui, lokasi layanan, simulasi biaya dari konfigurasi mitra, consent versi, draft, revisi, kirim. Hapus kebutuhan nasabah mengetik `indicative_value` sebagai seolah hasil AI.
- [ ] **B04 — Status & keputusan.** Timeline aplikasi berisi waktu, aktor layanan, alasan status yang boleh dibuka, permintaan perbaikan, perbedaan estimasi AI dan hasil penaksir, rincian offer, dokumen kontrak, serta acceptance eksplisit. Status dan nilai dari API, bukan teks statis.
- [ ] **B05 — Pickup.** Layar 4: pilihan slot yang tersedia, alamat privat, identitas petugas yang ditugaskan, konfirmasi/reschedule, kode serah terima, foto kondisi, bukti tanda terima; sinkron dengan tugas field dan event custody.
- [ ] **B06 — Tracking/pelunasan.** Layar 5: tiga timeline terpisah untuk pengajuan, barang, dan pinjaman; jumlah/tenor/jatuh tempo resmi; pembayaran terverifikasi, perpanjangan bila produk mendukung, pelepasan dan pengembalian; tautan ke receipt/SBG. Tombol “Bayar sekarang” hanya muncul setelah kanal resmi tersedia dan terintegrasi.
- [ ] **B07 — Bantuan.** FAQ versi disahkan, tiket/komplain terkait aplikasi, SLA respons, lampiran aman, riwayat dan jalur banding manusia.
- [ ] **B08 — PWA.** Manifest, ikon, install prompt, kamera/upload yang andal, offline state informatif, notifikasi yang bisa di-opt-in, loading/empty/error, aksesibilitas keyboard dan screen reader.

**Selesai jika:** nasabah uji mengajukan aset berfoto, menerima permintaan perbaikan/offer, memilih pickup, melihat serah terima dan status pembayaran yang sama dengan portal staf; semua perubahan bisa dilacak ke event dan bukti. Tidak ada data finansial yang dikarang oleh UI.

## Workstream C — AI appraisal dengan manusia sebagai pemutus (P1)

- [ ] **C01 — Dataset dan hak pakai.** Definisikan kategori awal bersama penaksir mitra, atribut wajib, label kondisi/nilai fisik, sumber pembanding yang berizin, tanggal efektif, provenance, retensi, persetujuan pemakaian dan pemisahan data tenant. Tanpa data pembanding valid, jangan mengeluarkan angka model yang tampak otoritatif.
- [ ] **C02 — Evidence dan job.** Upload foto aset privat dengan checksum/malware scan; job async idempotent dengan status queued/running/succeeded/failed, retry dan observability. Simpan `asset_id`, `org_id`, consent, versi pipeline/model, sumber data, timestamp, serta hash input/output. Tidak perlu Docker; worker dijalankan sebagai proses lokal pada dev.
- [ ] **C03 — Pemeriksa kualitas.** Skor blur, cahaya, resolusi, frame/angle dan duplikasi; rekomendasi foto ulang yang jelas. Benchmark pada set foto berlabel, termasuk foto buruk dan kategori tidak didukung.
- [ ] **C04 — Pengenal aset.** Usulkan kategori, merek/model/atribut dengan confidence; hasil dapat dikoreksi pengguna atau penaksir. Jangan menganggap OCR KTP sebagai pengenal barang.
- [ ] **C05 — Estimasi indikatif.** Retrieval pembanding terverifikasi dan aturan valuasi per kategori menghasilkan kisaran, confidence/coverage, faktor penentu, timestamp referensi, serta `SUCCESS / NEEDS_REVIEW / UNSUPPORTED`. Kategori tanpa pembanding memunculkan “Belum dapat diestimasi”. Hindari LLM bebas menghasilkan nominal.
- [ ] **C06 — Workbench penaksir.** Tampilkan foto asli, kualitas, atribut, pembanding, rentang AI, caveat, dan nilai fisik. Penaksir dapat menerima/mengoreksi/menolak usulan dengan alasan; simpan revision, evidence dan maker-checker final. Offer hanya memakai appraisal manusia yang final.
- [ ] **C07 — Evaluasi.** Model card, versi dan rollback, MAE/WAPE per kategori/kondisi, coverage/abstention, correction rate, drift, biaya/waktu proses, serta test set terpisah. Setiap perubahan model diuji sebelum aktif per tenant.

**Selesai jika:** foto buruk meminta ulang; kategori tak didukung tidak diberi nominal; pembanding dan model version terlihat; perbedaan AI vs penaksir tercatat; AI tidak pernah membuat offer, pencairan, atau pelepasan barang sendiri.

## Workstream D — desain dan aset visual (dijalankan bersama A–C)

- [ ] **D01 — Design tokens.** Petakan warna/logo dari gambar acuan dan `panduan theme.css` ke token: navy teks, biru aksi, biru pucat, putih, status, radius, elevasi, spacing, tipografi. Jangan memakai teks dekoratif yang sulit dibaca atau klaim aman tanpa bukti.
- [ ] **D02 — Figma-equivalent di kode.** Bangun 5 layar borrower sesuai urutan screenshot pada viewport acuan (sekitar 390 px) lalu adaptasi 320 px, tablet dan desktop. Tetapkan komponen `MobileShell`, bottom navigation, header, status timeline, asset card, action sheet, wizard stepper, evidence card, dan toast.
- [ ] **D03 — Maskot.** Aset kandidat transparan ada di `frontend/public/brand/privgadai-mascot-wave.png`; prompt dan provenance tercatat di [dokumen aset](./13-mascot-asset.md). Cocokkan crop/skala/warna dengan screenshot di tiga konteks (onboarding, dashboard, status). Aset ini hasil generatif yang mendekati karakter rujukan; minta review visual sebelum menjadikannya elemen brand final. Logo resmi tetap SVG yang sudah ada.
- [ ] **D04 — Review visual.** Ambil screenshot kode pada viewport referensi, bandingkan hirarki, densitas, warna, maskot, alignment, dan perilaku interaksi dengan gambar contoh. Terima hanya setelah review manusia; tidak menjanjikan identitas piksel 100% lintas perangkat.

## Workstream E — provider institusional (desain sekarang, transaksi setelah gate fase 3)

- [ ] **E01 — Prototype data sintetis.** Layar login/provider dashboard/discover/detail opportunity seperti 3 layar bawah referensi. Label jelas “simulasi”; semua nominal, return, LTV, progress, dan data aset adalah synthetic seeded fixtures. Tidak ada tombol pendanaan yang memproses uang.
- [ ] **E02 — Definisi bisnis.** Bersama pemilik produk/mitra tentukan apakah penyedia dana adalah institusi pemodal, kreditur, atau pihak lain; siapa lender of record; skema kontrak, recourse, arus dana, exposure, disclosure, akses borrower PII, dan kewajiban laporan. Ini adalah gate sebelum model transaksi dikunci.
- [ ] **E03 — Identity institusi.** Setelah gate: onboarding badan hukum, pengguna institusi, role/approval, MFA, mandate per mitra/portofolio, perjanjian berbagi data, sesi dan audit terpisah dari staf gadai.
- [ ] **E04 — Data room & allocation.** Setelah gate: opportunity yang boleh dibagikan, redaksi PII, dokumen versi, state, eligibility, limit, allocation/reconciliation, event finansial dan sumber resmi. Belum ada wallet/return forecast publik atau “Danai” aktif.
- [ ] **E05 — Gate go-live.** UAT lembaga dan institusi, permission matrix, peninjauan legal/compliance, tes keamanan, audit akses, rekonsiliasi dana dengan pihak berwenang, serta sign-off formal. Investor individu adalah rencana fase 4 yang terpisah.

## Urutan delivery dan dependensi

| Slice | Isi yang dapat didemokan | Prasyarat | Exit gate |
|---|---|---|---|
| 0 | Aset visual, tokens, wireflow dan API contracts; akun/scope borrower | Blueprint dan SOP mitra untuk kategori pilot | Review UX dan threat model. |
| 1 | A01–A05 + B01–B03 | Slice 0 | Borrower login dan pengajuan berfoto end-to-end; tes isolasi tenant/owner hijau. |
| 2 | B04–B08 | Slice 1, integrasi offer/pickup/payment staf | Nasabah melihat hasil nyata dari event operasional dan dapat bertindak aman. |
| 3 | C01–C07 | Dataset sah, label penaksir, Slice 1 | AI abstain dan human review teruji; metrik model terdokumentasi. |
| 4 | E01, lalu E02–E05 hanya setelah keputusan fase 3 | Struktur bisnis/kontrak/izin | Prototype visual boleh didemo; fitur pendanaan transaksional hanya bila seluruh gate disahkan. |

Tidak perlu menunggu fase pendanaan untuk menyelesaikan borrower dan AI. Petugas lapangan punya backlog PWA tersendiri yang harus diselaraskan saat B05; jangan menyelesaikan pickup dengan simulasi statis saja.

## Matriks uji end-to-end wajib

1. **Nasabah:** daftar → verifikasi akun → unggah KTP/foto aset → kirim → pantau → revisi bila diminta → terima/tolak offer → jadwal → lihat bukti custody → lihat pembayaran/pelunasan resmi → tiket.
2. **Penaksir:** foto buruk/kategori tidak didukung/estimasi tersedia → koreksi atribut → nilai fisik berbeda → alasan → checker lain menyetujui → offer memakai nilai final saja.
3. **Isolasi:** tenant A/B, nasabah A/B, petugas tanpa tugas, pendana tanpa mandate; list/detail/file/export/event/job harus menolak akses silang.
4. **Kegagalan:** OCR/AI worker timeout, upload rusak, job berulang, consent dicabut, payment callback ganda, pickup batal, barang berbeda, customer menolak nilai; UI dan audit menunjukkan status sebenarnya.
5. **UX:** screenshot visual pada 390/320/768/desktop, focus order, kontras, teks panjang, empty/loading/error, jaringan lambat, dan satu tab navigasi aktif.

## Hal yang harus diputuskan sebelum implementasi transaksi

- SOP mitra untuk urutan pickup vs appraisal fisik, kategori aset awal, siapa yang mengesahkan offer, dan sumber status pembayaran.
- Hak pakai foto/label/pembanding harga untuk AI, dataset evaluasi, serta batas kategori yang boleh mendapat estimasi.
- Peran hukum dan kontrak penyedia dana institusional sebelum ada opportunity riil, return, wallet, atau alokasi dana.

Keputusan di atas adalah input domain untuk slice terkait; pengerjaan UI borrower, autentikasi terpisah, dan pipeline kualitas foto dapat dimulai dengan data sintetis sambil menunggu SOP final.
