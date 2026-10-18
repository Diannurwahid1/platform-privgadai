# Riset harga langsung untuk estimasi borrower

Alur estimasi: foto dan atribut barang → `step-5-preview` membaca foto serta membuat tiga kueri harga → Tavily Search mencari halaman Indonesia → `step-5-preview` membaca kelompok hasil yang kecil → backend memeriksa kutipan harga, mencocokkan sumber, dan menghitung rentang dari beberapa situs independen. Foto hanya dikirim ke router vision; Tavily menerima kueri atribut barang tanpa identitas nasabah.

Kisaran ditampilkan bila ada sedikitnya dua harga sejenis dari dua domain independen dengan jenis harga yang sama. Dua sumber selalu berstatus terbatas dan wajib ditinjau penaksir; tiga sumber atau lebih dapat menjadi estimasi otomatis. Barang emas mengutamakan harga buyback; elektronik dan kendaraan mengutamakan harga barang bekas. Harga per gram tidak boleh dipakai sebagai harga keping 10 gram. Sumber bertanggal lebih dari 7 hari untuk emas atau 60 hari untuk barang lain disisihkan. Hasil dengan bukti kurang, harga terpaut jauh, sumber tidak cocok, atau layanan eksternal gagal tetap masuk proses pengajuan tanpa angka otomatis. Penaksir manusia memutuskan nilai pasar, likuidasi, dana, serta alasan perubahan.

Catatan harga yang lolos disimpan bersama URL, domain, jenis harga, kutipan angka, tanggal sumber bila tersedia, dan waktu penelusuran. UI borrower dan petugas menampilkan tautan sumber. Waktu penelusuran bukan jaminan tanggal perubahan harga pada halaman: sumber tanpa tanggal ditandai. Semua harga web adalah harga indikatif, bukan bukti transaksi dan bukan verifikasi keaslian barang.

Konfigurasi server di `.env` yang diabaikan Git: `BYNARA_API_KEY`, `BYNARA_MODEL=step-5-preview`, dan `TAVILY_API_KEY`. Jangan memakai prefix `NEXT_PUBLIC_` untuk kunci tersebut. Lakukan migrasi `alembic upgrade head` sebelum menjalankan endpoint estimasi. Batas waktu jaringan dibatasi oleh `BYNARA_TIMEOUT_SECONDS` dan `TAVILY_TIMEOUT_SECONDS`.

## Uji langsung 19 Oktober 2026

- Antam LM 10 gram: tabel dealer bertanggal 15 Oktober dan halaman buyback Logam Mulia memberi dua harga dari dua domain. Status `LIMITED` karena halaman kedua tidak mencantumkan tanggal pasti; ini belum keputusan appraisal.
- iPhone 15 Pro 256 GB bekas: dua listing dari domain berbeda menghasilkan status `LIMITED` dan kisaran sementara. Tanggal pada kedua listing tidak pasti, sehingga penaksir perlu mengecek ulang.
- Honda Vario 160 tahun 2023: pencarian menemukan listing relevan, harga motor baru, cicilan, dan harga lelang. Bukti harga bekas sejenis dari domain independen belum cukup, sehingga sistem tidak menampilkan angka otomatis.

Ketiga contoh menunjukkan bahwa hasil dapat berubah saat mesin pencari atau halaman sumber diperbarui. Pengujian fungsi riset langsung, tes backend, dan pemeriksaan tipe frontend telah dilakukan; unggah foto borrower end-to-end untuk versi riset ini masih perlu uji operasional dengan foto dan akun pilot.
