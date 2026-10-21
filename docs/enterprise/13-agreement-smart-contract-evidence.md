# Bukti perjanjian gadai dan smart contract BNB Testnet

Status: registry diuji lokal dan dideploy di BNB Testnet pada `0xa90f0d609ca697cdc1c22fe2cc1b73dca9774abb`. Transaksi sintetis `0xb4a1b12735c0725ba74897c3be794b83210fa5f90a63b4c3b0a8642081bae1e0` terkonfirmasi di blok `138024176`, dan dua digest terbaca kembali dengan benar. Alur **ringkasan penawaran dan persetujuan portal** kini terhubung ke registry melalui outbox. Ini belum merupakan SBG final atau tanda tangan elektronik tersertifikasi; kontrak tidak menggantikannya.

## Implementasi yang berjalan

- Borrower harus memiliki KYC verified. API memberi preview syarat dengan SHA-256; aksi setuju wajib membawa digest preview dan persetujuan eksplisit. Preview basi atau tanpa persetujuan ditolak.
- Rekam privat menyimpan snapshot syarat, identitas sesi yang terautentikasi, kanal, waktu, IP yang terlihat server, user agent, salt, dan dua digest. Snapshot dan persetujuan dibuat dalam transaksi database yang sama dengan acceptance.
- Relayer yang sudah berjalan untuk custody juga membaca antrian perjanjian. Ia mengirim dua digest tersalt ke registry, memantau konfirmasi, dan menyimpan transaksi/blok. Portal borrower dan staf bisa menjalankan pemeriksaan ulang lokal serta on-chain. Export JSON untuk paket bukti tersedia di borrower.
- Paket JSON dapat diperiksa terpisah dari sesi portal memakai `backend/scripts/verify_agreement_export.py FILE.json`. Pemeriksa menghitung ulang dua digest dan membandingkannya dengan registry yang dipin ke alamat deployment resmi.
- Jalur staf untuk menerima penawaran atas nama borrower ditutup. Pickup dan pencairan mensyaratkan persetujuan portal yang direkam. Kegagalan BNB tidak menghapus penerimaan yang sudah sah di database; status pending/failed tetap terlihat untuk tindak lanjut.

Dokumen yang dihasilkan saat ini adalah **ringkasan syarat penawaran**, termasuk pihak, agunan, appraisal, dana, tenor, biaya, alasan keputusan, dan penjelasan proses. Klausul SBG final yang ditandatangani harus disetujui PT sebelum alur ini dipakai sebagai satu-satunya kontrak operasional.

## Mengapa diperlukan

Saat ini penerimaan penawaran membuat `PawnAgreement`, tetapi rekamnya hanya nomor SBG, jenis, versi template, status `signed`, dan waktu. `CustomerAcceptance` menyimpan kanal, IP, dan waktu. Tidak ada salinan isi syarat yang dibekukan dan ditandatangani. Karena itu nomor SBG atau transaksi BNB saja belum bisa menjawab sengketa tentang nilai, tenor, biaya, keadaan agunan, atau versi klausul yang disetujui.

Blueprint operasional bagian **Penawaran dan perjanjian** menuntut offer dengan snapshot syarat/biaya, generator perjanjian dari template terversi, acceptance yang menunjuk versi, signature evidence, checksum, dan arsip. Perubahan setelah acceptance harus membuat versi baru. Bukti BNB menambah kemampuan membuktikan bahwa arsip tertentu sudah tercatat pada waktu tertentu; keputusan dan pelaksanaan gadai tetap di sistem operasional.

## Alur target

1. Petugas menetapkan appraisal final, nilai, tenor, biaya, denda, serta alasan deviasi; checker menyetujui menurut limit kewenangan.
2. Sistem membuat **draft Surat Bukti Gadai** dalam Bahasa Indonesia dari template hukum yang disetujui PT Murah Gadai Jogja. Nomor, identitas para pihak, rincian barang, nilai taksiran, pinjaman, tenor, biaya, jatuh tempo, wanprestasi, eksekusi, pengembalian kelebihan, dan jalur sengketa adalah bagian dokumen yang dibekukan. Preview borrower harus menampilkan dokumen lengkap, bukan hanya nominal.
3. Borrower yang KYC-nya sudah verified membaca dokumen, lalu memberi persetujuan eksplisit pada **digest versi yang tampil**. Bukti autentikasi, sesi, waktu, kanal, dan hasil tanda tangan elektronik disimpan privat. Integrasi PSrE Indonesia perlu untuk tanda tangan tersertifikasi; jika belum terintegrasi, UI harus menyebut bukti persetujuan portal, bukan tanda tangan tersertifikasi.
4. Arsipkan byte PDF yang identik dengan yang disetujui secara privat dan tahan ubah. Simpan versi template, data snapshot, checksum PDF, bukti tanda tangan, dan audit event. Revisi nilai/tenor/klausul menghasilkan offer dan dokumen baru serta persetujuan ulang. Tidak ada overwrite.
5. Relayer mendaftarkan `opaqueAgreementId`, versi berurutan, `documentDigest` dan `consentDigest` yang **diasinkan** pada `PawnAgreementEvidenceRegistry` BNB Testnet. Tidak ada nama, NIK, nomor SBG publik, nominal, foto, UUID, atau hash mentah file di chain.
6. Di borrower dan staf tampilkan dokumen, status tanda tangan, status anchoring, tautan transaksi, dan aksi **Verifikasi bukti**. Verifikasi menghitung ulang digest dari arsip privat lalu membandingkannya dengan data on-chain. Bukti sengketa adalah satu paket: dokumen yang disetujui, identitas dan signature evidence, riwayat revisi/serah terima/pembayaran, hasil verifikasi digest, dan transaksi BNB.

## Batas smart contract

`PawnAgreementEvidenceRegistry` menyimpan komitmen yang tidak bisa ditimpa, memaksa nomor versi berurutan, membolehkan retry identik, menolak konflik, memiliki role registrar dan pause. Pengiriman transaksi oleh wallet relayer **membuktikan pencatatan oleh platform, bukan bahwa borrower menandatangani**. Kontrak tidak mentransfer dana, tidak mengeksekusi agunan, tidak memutus sengketa, dan tidak menyimpan data pribadi.

## Gate sebelum mengaktifkan di aplikasi

- [ ] PT menyetujui template SBG, klausul biaya/denda, dan pilihan forum sengketa untuk tiap produk. Tinjau terhadap POJK 39/2024 beserta perubahan POJK 29/2025.
- [ ] Template SBG final yang disetujui PT dan generator PDF byte-identik dengan preview; snapshot ringkasan penawaran saja sudah berjalan.
- [ ] Bukti persetujuan borrower terikat ke digest dokumen; integrasi tanda tangan elektronik/PSrE dan mekanisme verifikasi identitas penanda tangan.
- [ ] Arsip immutable privat dengan retensi, akses per tenant, checksum, backup, dan export paket sengketa.
- [ ] Transactional outbox untuk BNB, relayer dengan retry/idempotency/konfirmasi, monitoring, dan verifier independen; kegagalan chain tidak boleh mengubah isi perjanjian.
- [ ] UAT sengketa: dokumen diubah, acceptance palsu, revisi tenor, gagal RPC, tx tertunda, salah tenant, dan bukti yang tidak cocok harus terdeteksi.

## Rujukan regulasi

- [OJK POJK 39/2024 Pergadaian](https://ojk.go.id/id/regulasi/Pages/POJK-39-Tahun-2024-Pergadaian.aspx): perjanjian tertulis, termasuk Surat Bukti Gadai, dan cakupan informasi minimum.
- [OJK POJK 29/2025](https://ojk.go.id/id/regulasi/Pages/POJK-29-Tahun-2025-Perubahan-atas-Peraturan-Otoritas-Jasa-Keuangan-Nomor-39-Tahun-2024-tentang-Pergadaian.aspx): perubahan yang berlaku atas POJK 39/2024.
- [PP 71/2019](https://peraturan.bpk.go.id/Download/112816/PP%20Nomor%2071%20Tahun%202019.pdf): Pasal 46–49 tentang kontrak elektronik dan kesepakatan, Pasal 59–60 tentang tanda tangan elektronik.
