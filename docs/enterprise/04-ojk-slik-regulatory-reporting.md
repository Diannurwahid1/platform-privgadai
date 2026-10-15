# 04 — Pelaporan OJK dan SLIK

## Batasan dan prinsip

PrivGadai harus membangun **reporting engine yang dapat dikonfigurasi dan diverifikasi**, bukan satu tombol “generate OJK”. Setiap format resmi perlu divalidasi terhadap lampiran regulasi yang berlaku, profil izin perusahaan, jenis usaha konvensional/syariah/UUS, serta tanggal efektif.

Paket laporan yang dihasilkan aplikasi belum boleh disebut “sesuai OJK” sampai:

- pemetaan field disahkan fungsi kepatuhan;
- file lolos validator resmi yang berlaku;
- sign-off maker, reviewer, dan pejabat berwenang selesai;
- bukti pengiriman serta acknowledgement disimpan;
- perubahan regulasi telah melalui regression test.

## Sumber resmi baseline

1. [POJK Nomor 39 Tahun 2024 tentang Pergadaian](https://ojk.go.id/id/regulasi/Pages/POJK-39-Tahun-2024-Pergadaian.aspx) — perjanjian, penaksir, kualitas pinjaman, batas maksimum pemberian pinjaman, ekuitas, tingkat kesehatan, dan pelaporan.
2. [POJK Nomor 29 Tahun 2025, perubahan POJK 39/2024](https://ojk.go.id/id/regulasi/Pages/POJK-29-Tahun-2025-Perubahan-atas-Peraturan-Otoritas-Jasa-Keuangan-Nomor-39-Tahun-2024-tentang-Pergadaian.aspx).
3. [SEOJK Nomor 17/SEOJK.06/2025 tentang Laporan Bulanan Perusahaan Pergadaian](https://ojk.go.id/id/regulasi/Pages/SEOJK-17-SEOJK06-2025-Laporan-Bulanan-Perusahaan-Pergadaian-dan-Perusahaan-Pergadaian-Syariah.aspx) — berlaku 1 Desember 2025; [PDF resminya](https://www.ojk.go.id/id/regulasi/Documents/Pages/SEOJK-17-SEOJK06-2025-Laporan-Bulanan-Perusahaan-Pergadaian-dan-Perusahaan-Pergadaian-Syariah/SEOJK%2017-SEOJK06-2025%20Laporan%20Bulanan%20Perusahaan%20Pergadaian%20dan%20Perusahaan%20Pergadaian%20Syariah.pdf) menetapkan Formulir 0000, 0020, 0030, 0035, 0036, 0041, 0043, 0050, 1100, 1200, 1300, 2100, 2200, 2300, 4100, 5100, 6100, 7100, 8100, dan 9100 pada Lampiran II untuk perusahaan konvensional.
4. [SEOJK Nomor 30/SEOJK.06/2025 tentang Perizinan, Persetujuan, dan Pelaporan Elektronik](https://ojk.go.id/id/regulasi/Pages/SEOJK-30-SEOJK06-2025-Perizinan,-Persetujuan,-dan-Pelaporan-secara-Elektronik-Perusahaan-Pergadaian-dan-Perusahaan-Pergadai.aspx) — self-assessment, verifikasi oleh pejabat berbeda, dokumen sumber, kanal elektronik, dan fallback.
5. [SEOJK Nomor 11/SEOJK.01/2024 tentang Pelaporan dan Permintaan Informasi Debitur melalui SLIK](https://ojk.go.id/id/regulasi/Pages/Pelaporan-dan-Permintaan-Informasi-Debitur-Melalui-Sistem-Layanan-Informasi-Keuangan-11-SEOJK01-2024.aspx) — pedoman, segmen, referensi, dan opsi host-to-host.
6. [POJK Nomor 11 Tahun 2024, perubahan kedua pelaporan SLIK](https://ojk.go.id/id/regulasi/Pages/Perubahan-Kedua-POJK-Nomor-18-2017-tentang-Pelaporan-dan-Permintaan-Informasi-Debitur-melalui-SLIK.aspx).
7. [SEOJK Nomor 20/SEOJK.08/2025 tentang publikasi penanganan dan laporan layanan pengaduan](https://ojk.go.id/id/regulasi/Pages/SEOJK-20-SEOJK08-2025-Publikasi-Penanganan-Pengaduan-dan-Laporan-Layanan-Pengaduan.aspx) — efektif 1 Januari 2027.
8. [Dokumen OJK penilaian tingkat kesehatan perusahaan pergadaian](https://ojk.go.id/id/regulasi/documents/forms/allitems.aspx?rootfolder=%2Fid%2Fregulasi%2Fdocuments%2Fpages%2Fseojk-35-seojk05-2025-penilaian-tingkat-kesehatan-perusahaan-pergadaian-dan-perusahaan-pergadaian-syariah) — lembar kerja faktor permodalan, kualitas piutang, rentabilitas, likuiditas, manajemen, dan peringkat komposit. Nomor final harus dikonfirmasi dari PDF resmi sebelum schema lock.

## Workspace regulator

OJK dan SLIK menjadi submodul terpisah karena frekuensi, struktur data, validator, kewenangan, dan mekanisme submission berbeda.

### Reporting calendar

- Daftar kewajiban berdasarkan izin, jenis usaha, wilayah, dan periode.
- Due date, cutoff, status, owner, reviewer, pejabat penandatangan, dan escalation.
- Kalender versioned untuk menangani aturan transisi.
- Reminder berdasarkan SLA internal sebelum due date regulator.

### Pipeline laporan

```text
OPEN_PERIOD
→ EXTRACTING
→ VALIDATING
→ CORRECTION_REQUIRED / READY_FOR_REVIEW
→ REVIEWED
→ APPROVED
→ FILE_GENERATED
→ SUBMITTED
→ ACKNOWLEDGED / REJECTED_BY_CHANNEL
→ CLOSED
```

Setiap run immutable. Koreksi membuat revision baru dengan hubungan ke revision sebelumnya.

Run yang telah mendapat sign-off dapat diekspor sebagai paket ZIP deterministik berisi manifest regulasi, versi template, periode, revision, identitas sign-off, status `not_submitted`, CSV Formulir 1100/2100/9100, rekonsiliasi cabang, dan checksum SHA-256 pada response. File tetap berstatus paket kerja sampai validator dan kanal OJK tenant menerbitkan acknowledgement.

### Validation workbench

- Validasi schema, tipe, panjang, mandatory, referential integrity, code set, dan cross-field rule.
- Rekonsiliasi ke GL, loan subledger, customer, collateral, cash, dan laporan periode sebelumnya.
- Error dapat ditelusuri hingga source record dan source event.
- Koreksi data sumber dilakukan di modul pemilik, lalu laporan diekstrak ulang.
- Override terbatas, beralasan, berjangka, dan mendapat approval.

### Data lineage

Setiap cell/record laporan menyimpan:

- template dan rule version;
- source table/aggregate dan record ID;
- source event/cutoff;
- transformasi/perhitungan;
- pengguna atau job pembuat;
- validation result;
- checksum file akhir.

## Laporan bulanan pergadaian

Engine harus mendukung kelompok laporan sesuai lampiran yang berlaku, antara lain posisi keuangan, laba rugi dan penghasilan komprehensif, arus kas, asset-liability matching, serta laporan lain yang dipersyaratkan.

Task:

- [ ] REG-OJK-101: inventaris seluruh form/field/definition dari lampiran resmi sesuai tipe usaha.
- [ ] REG-OJK-102: buat data dictionary dan owner sumber per field.
- [ ] REG-OJK-103: buat rule engine terversi dan effective-dated.
- [ ] REG-OJK-104: buat reconciliation pack terhadap GL/subledger.
- [ ] REG-OJK-105: buat review, self-assessment, checker, dan director sign-off.
- [ ] REG-OJK-106: generate file tepat sesuai format resmi, termasuk penamaan dan encoding.
- [ ] REG-OJK-107: simpan bukti submission, fallback, acknowledgement, dan correction.

## SLIK

Schema SLIK harus diturunkan dari lampiran terbaru SEOJK 11/2024. Daftar segmen dan code list lama hanya boleh menjadi orientasi, bukan sumber implementasi final.

Area data yang perlu dipetakan:

- identitas debitur/CIF individual atau badan;
- fasilitas dan akad/perjanjian;
- plafond, pencairan, outstanding/baki debet, kualitas, tunggakan, denda;
- agunan/jaminan sesuai definisi segmen;
- penjamin/pengurus bila relevan;
- cabang, reporter, operation code, correction/delete semantics;
- referensi DATI II dan code set lain yang berlaku.

Kontrol:

- CIF unik dan tidak didaur ulang.
- Matching identitas, duplicate resolution, serta correction history.
- Code list disimpan sebagai reference data terversi.
- Snapshot periode tidak berubah setelah freeze; correction menjadi revision.
- Validation issue memiliki owner, SLA, dan reason code.
- File, log transfer/host-to-host, response, dan acknowledgement dienkripsi dan diberi retention policy.

Task:

- [ ] REG-SLIK-101: legal/regulatory walkthrough lampiran terbaru.
- [ ] REG-SLIK-102: data contract tiap segmen dan mapping sumber.
- [ ] REG-SLIK-103: CIF governance, duplicate/correction workflow.
- [ ] REG-SLIK-104: code set registry dan effective date.
- [ ] REG-SLIK-105: validation engine serta cross-segment reconciliation.
- [ ] REG-SLIK-106: file generator dan official validator integration test.
- [ ] REG-SLIK-107: submission/host-to-host adapter setelah akses resmi tersedia.

### Implementasi work package SLIK saat ini

Fondasi generator internal sudah tersedia dengan baseline [SEOJK 11/SEOJK.01/2024](https://ojk.go.id/id/regulasi/Pages/Pelaporan-dan-Permintaan-Informasi-Debitur-Melalui-Sistem-Layanan-Informasi-Keuangan-11-SEOJK01-2024.aspx):

- template memiliki tipe, kode, versi, tanggal efektif, mapping, rule, status, dan approval aktivasi;
- report run memisahkan payload preview yang aman dari snapshot sensitif terenkripsi;
- NIK berasal dari KYC terverifikasi, disimpan terenkripsi, dan tidak tampil pada response API/report payload biasa;
- segmen kerja D01 debitur individual, F01 fasilitas kredit, dan A01 agunan dihasilkan dari satu snapshot;
- validator memblokir NIK/KYC, kode DATI II, serta kode subjek SLIK yang belum lengkap;
- jumlah record per segmen dan total outstanding direkonsiliasi;
- sign-off maker-checker wajib sebelum paket ZIP dapat diekspor;
- paket memuat manifest, validation results, tiga CSV segmen, rekonsiliasi, dan checksum response.

Paket ini masih berstatus **work package terkendali** sampai kamus seluruh kolom, code set, aturan koreksi/hapus, penamaan file, dan validator kanal resmi milik pelapor telah diuji. Sistem tidak menandai file sebagai submitted dan belum mengirimkannya ke OJK.

## Keamanan dan separation of duty

- Maker menyiapkan run dan menangani error.
- Reviewer memeriksa mapping, rekonsiliasi, dan evidence.
- Pejabat berwenang menyetujui/sign-off.
- User yang mengubah source record tidak boleh sendirian menyetujui laporan terkait jika matriks konflik melarangnya.
- File regulator memiliki akses terbatas, enkripsi, masking preview, checksum, malware scan untuk attachment, dan download event.

## Acceptance criteria regulator

- [ ] Template/rule/code set memiliki versi dan tanggal efektif.
- [ ] Satu angka laporan dapat ditelusuri ke sumber dan perhitungannya.
- [ ] Total/rekonsiliasi dan aturan lintas field berjalan otomatis.
- [ ] File lolos validator resmi untuk periode uji yang disepakati.
- [ ] Maker-checker-signatory serta conflict check tidak dapat dilewati lewat API.
- [ ] Regeneration tidak menimpa file/revision lama.
- [ ] Submission manual maupun elektronik memiliki evidence dan acknowledgement.
- [ ] Run terisolasi per tenant dan profil reporter.
