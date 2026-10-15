# 07 — KYC, CDD, dan Identitas Nasabah

## Keputusan produk

Untuk WNI, data identitas utama PrivGadai berasal dari KTP elektronik/NIK. Foto KTP adalah bukti dalam Customer Due Diligence (CDD), bukan hasil verifikasi dengan sendirinya. CDD mencakup identifikasi, verifikasi, klasifikasi risiko, keputusan checker, pengkinian, dan pemantauan. Kasus berisiko tinggi masuk Enhanced Due Diligence (EDD).

## Alur operasional

1. Maker merekam NIK 16 digit dan data sesuai KTP.
2. Sistem menyimpan fingerprint HMAC tenant-scoped dan NIK termasking, tanpa menyimpan NIK mentah.
3. Maker mengunggah sisi depan KTP; selfie dan dokumen pendukung dapat ditambahkan.
4. Dokumen disimpan pada private storage dalam bentuk terenkripsi dan memiliki checksum SHA-256.
5. Checker yang berbeda memeriksa bukti, hasil provider bila tersedia, PEP/sanctions flag, dan risk level.
6. Checker memilih `verified`, `needs_information`, atau `rejected` dengan alasan wajib.
7. KYC terverifikasi memiliki masa berlaku dan harus diperbarui.
8. Pengajuan tidak dapat masuk appraisal bila KYC belum terverifikasi atau kedaluwarsa.
9. Setiap langkah menghasilkan domain event untuk Audit Explorer.

## Integrasi resmi

PrivGadai menggunakan adapter provider-neutral. Integrasi NIK/Dukcapil atau e-KYC hanya diaktifkan setelah mitra memiliki kerja sama, dasar pemrosesan, kredensial, SLA, serta persetujuan security/compliance yang sah. Respons simulasi tidak boleh ditampilkan sebagai verifikasi resmi.

Kontrak adapter berikutnya mencakup correlation ID, versi provider, hasil match per atribut, face match/liveness, retry dan idempotency, signed callback, evidence, retention, provider health, serta reconciliation.

## Kontrol data

- `PII_ENCRYPTION_KEY` terpisah dari JWT secret dan wajib pada production.
- NIK tidak dikembalikan melalui API setelah intake.
- Detail KYC tenant-scoped.
- Maker tidak dapat menjadi checker pada verifikasi yang sama.
- Duplicate NIK dalam tenant ditolak, kecuali verifikasi sebelumnya rejected.
- Object key dokumen tidak dikirim kepada frontend.
- Preview/download memerlukan otorisasi, watermark, dan download event; endpoint belum dibuka pada slice awal.
- Malware scanner harus terintegrasi sebelum berkas dianggap bersih untuk production.

## Acuan resmi

- POJK 8 Tahun 2023 tentang APU, PPT, dan PPPSPM di sektor jasa keuangan.
- POJK 39 Tahun 2024 tentang Pergadaian.
- UU 27 Tahun 2022 tentang Pelindungan Data Pribadi.
- Lampiran, pedoman, dan perjanjian akses Dukcapil/provider yang berlaku ketika implementasi produksi.

## Status implementasi 16 Oktober 2026

- [x] Model verifikasi, dokumen, dan event tenant-scoped.
- [x] NIK fingerprint dan masking.
- [x] Penyimpanan dokumen terenkripsi.
- [x] Form KTP pada Customer 360.
- [x] Maker-checker dan alasan keputusan.
- [x] Guard KYC sebelum appraisal.
- [x] Event KYC pada Audit Explorer.
- [ ] Adapter Dukcapil/provider e-KYC resmi.
- [ ] OCR terkontrol dan perbandingan atribut.
- [ ] Face match dan liveness provider.
- [ ] Screening PEP, sanctions, adverse media, dan EDD case.
- [ ] Malware scanner dan authorized evidence viewer.
- [ ] Pengkinian berkala, expiry job, serta ongoing monitoring.
- [ ] Privacy request, retention, legal hold, dan purge workflow.
