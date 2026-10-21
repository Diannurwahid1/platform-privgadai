# Skenario Operasional Staging, 20–21 Oktober 2026

Script `backend/scripts/seed_jogja_oct2026.py` mengisi tenant `murah-gadai-jogja` hanya saat `APP_ENV=staging`. Identitas, penilaian, dan pengajuan yang dibuat bersifat sintetis. Nomor referensi nasabah diawali `SBOX-2610` agar dapat dipisahkan dari nasabah nyata. Script menolak tenant yang sudah mempunyai pengajuan atau cabang, sehingga tidak menimpa aktivitas yang ada.

Isi skenario: dua cabang, dua produk, lima kategori agunan, dua vault, master GL dan kas bersaldo nol, draft template OJK/SLIK, dua anggota tim dengan penugasan cabang, dua belas nasabah dan pengajuan, lima KYC internal yang ditandai `sandbox_seed`, lima penaksiran, serta dua penawaran terbuka. Seluruh riwayat status dimulai pada 20 Oktober 2026 waktu Asia/Jakarta. Nilai, alamat, dan tarif perlu diputuskan kembali oleh PT sebelum dipakai untuk transaksi nyata.

Script tidak membuat persetujuan borrower, Surat Bukti Gadai final, pencairan, pembayaran, jurnal kas, data pengiriman regulator, atau hash kontrak blockchain. Penawaran yang dibuat belum dapat dianggap diterima oleh nasabah. Data sintetis ini tidak boleh dipakai untuk laporan atau keputusan finansial nyata. Sebelum berpindah ke produksi, data `SBOX-2610` dan semua turunan pengajuannya harus dihapus melalui prosedur migrasi terkontrol atau database baru.

Periksa terlebih dahulu dengan `cd backend && .venv/bin/python scripts/seed_jogja_oct2026.py --dry-run`. Setelah backup database, jalankan tanpa `--dry-run`. Kata sandi akun operasional dibuat secara acak dan hanya dicetak setelah transaksi database berhasil disimpan; simpan di pengelola kata sandi dan aktifkan MFA sebelum penggunaan operasional.
