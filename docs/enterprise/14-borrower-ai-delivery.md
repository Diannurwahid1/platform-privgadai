# Implementasi portal borrower dan appraisal berbantuan AI

Status per 18 Oktober 2026. Scope implementasi aktif adalah **PT Murah Gadai Jogja** dan borrower. Slug teknis tenant dev tetap `denjaka-2` agar tautan staf lama tidak putus. Portal pendana pada rencana sebelumnya tidak dikerjakan dalam slice ini.

**Pembaruan 19 Oktober 2026:** langkah estimator lokal pada catatan historis di bawah telah diganti oleh riset harga Tavily dan sintesis `step-5-preview`. Data demo lokal tidak lagi dipakai untuk angka borrower. Alur, syarat sumber, dan hasil uji terbaru dicatat di [Riset harga langsung](./15-live-market-research.md).

## Alur yang sudah tersedia

1. Borrower membuka `/borrower`, mendaftar atau masuk dengan akun dan sesi yang terpisah dari staf. Sesi dapat dicabut lewat logout. API borrower memakai ownership server-side dan CSRF untuk mutasi.
2. Borrower memilih kategori, merek/model, kondisi, dan foto barang. Upload memeriksa MIME, signature, ukuran, dan malware scanner yang dikonfigurasi. Persetujuan pengiriman foto ke layanan vision diwajibkan.
3. `step-5-preview` melalui NaraRouter membaca atribut yang terlihat dari foto. Prompt melarang model menentukan harga, keaslian, kepemilikan, dan kelayakan kredit. Respons atau kegagalan disimpan sebagai bukti proses.
4. Estimator lokal memakai k-nearest neighbours berbobot terhadap pembanding dalam organisasi dan appraisal manusia yang sudah final. Ia memberi kisaran dan confidence hanya jika sedikitnya tiga pembanding cukup mirip. Jika tidak cukup, hasil `UNSUPPORTED` tanpa angka. Foto buruk atau gangguan vision menghasilkan `NEEDS_REVIEW`.
5. Borrower memilih cabang, produk, jumlah diminta, dan tenor yang tersedia. Pengajuan, foto, consent, dan estimasi masuk ke inbox staf yang sama, berstatus `submitted`.
6. Staf menyelesaikan KYC/KTP menurut gate yang sudah ada, lalu penaksir memasukkan nilai pasar, likuidasi, rekomendasi, dan alasan. Appraisal masuk ke checker. Penawaran hanya dapat diterbitkan dari appraisal manusia final.
7. Form penawaran staf menampilkan permintaan awal, nominal/tenor baru, selisih, biaya sesuai produk, dan alasan wajib untuk perubahan. Borrower melihat rincian ini di halaman detail dan dapat menerima penawaran aktif lewat akun sendiri.

## Status data pembanding dev

Tenant dev memiliki sembilan pembanding **DEMO SINTETIS** untuk tiga barang contoh: Apple iPhone 15 Pro, Antam 10gr, dan ASUS Zenbook 14. Setiap estimasi yang memakai pembanding ini berstatus `NEEDS_REVIEW` dan diberi label simulasi. Pembanding demo diabaikan otomatis pada konfigurasi production. Penaksir dapat menambahkan pembanding riil melalui `POST /v1/appraisals/comparables` dengan identitas sumber, referensi, tanggal, kategori, model, kondisi, dan nilai; daftar tersedia di `GET /v1/appraisals/comparables`.

## Batasan operasional saat ini

- Borrower belum mengunggah KTP langsung dari portal. Verifikasi KTP/OCR dan checker tetap di workspace staf sebelum aplikasi boleh masuk status appraisal. Ini gate yang harus dipenuhi untuk pengajuan nyata.
- Kualitas foto saat ini berbasis resolusi, cahaya, ketajaman, dan rasio; validasi fisik, keaslian, IMEI/serial, kadar emas, dan kepemilikan tetap tugas petugas.
- Estimator belum punya evaluasi MAE/WAPE pada dataset mitra, drift monitoring, atau kalibrasi per kategori. Angka demo tidak boleh dipakai sebagai penawaran komersial.
- Browser Codex pada sesi implementasi ini tidak tersedia. UI telah lolos build dan typecheck, tetapi perbandingan screenshot 320/390/desktop dengan referensi perlu pemeriksaan visual langsung.
- Pickup, pembayaran, pelunasan, dan bantuan borrower belum menjadi bagian slice ini. Operasional staf untuk fungsi tersebut tetap berjalan pada portal staf.

## Bukti uji lokal

- Migrasi PostgreSQL `a6b4e3d91c02` diterapkan; `/readyz` melaporkan database, token store, dan migrasi siap.
- API: daftar → cookie sesi → konfigurasi → unggah foto sintetis → vision `step-5-preview` berhasil → kisaran pembanding demo → submit → detail/foto. Contoh pengajuan dev: `PG-261018-0E304D`.
- Akses silang borrower ke detail dan foto akun lain menghasilkan 404; logout tanpa CSRF menghasilkan 403.
- Detail staf untuk contoh pengajuan memuat estimasi dan satu evidence foto.
- Backend `test_ai_appraisal_estimator.py` dan `test_mvp_workflow.py` lulus. Test workflow mencakup checker appraisal, penolakan penawaran berubah tanpa alasan, pembacaan penawaran oleh borrower, dan acceptance borrower. Frontend `next build` dan TypeScript lulus.

## Langkah berikutnya sebelum pilot nyata

1. Masukkan pembanding riil berhak pakai dan lakukan evaluasi per kategori bersama penaksir. Hapus atau nonaktifkan pembanding demo dari tenant pilot.
2. Tambahkan unggah KTP borrower dan tautkan ke antrean KYC existing, termasuk pemeriksaan checker dan koreksi OCR.
3. Uji satu kasus dengan petugas sesungguhnya hingga appraisal final, offer, acceptance borrower, pickup, dan pencairan; ukur selisih estimasi dan nilai final.
4. Audit keamanan akun borrower: verifikasi kontak, pembatasan percobaan login, reset kata sandi, retensi foto, dan audit akses.
