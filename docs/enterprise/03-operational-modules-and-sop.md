# 03 — Modul Operasional dan SOP

Dokumen ini menerjemahkan dua blueprint menjadi workbench operasional. Setiap command harus memeriksa tenant, cabang, peran, state machine, kelengkapan dokumen, approval, dan idempotency di server.

## 1. Debitur & CRM

### Daftar debitur

Kolom minimum: CIF/referensi, nama, identitas termasking, cabang pemilik, status KYC, risk status, jumlah fasilitas aktif, outstanding, tunggakan, consent terbaru, last interaction, dan alert.

Filter: cabang, KYC, risk/watchlist, fasilitas aktif, tunggakan, consent kedaluwarsa, duplikasi, dan pemilik relasi.

### Detail debitur 360°

Header: nomor CIF, nama, status aktif/frozen, KYC, risk status, cabang, owner, dan warning. Tab:

1. **Ringkasan** — identitas ringkas, exposure, fasilitas, pembayaran berikutnya, exception.
2. **Identitas & KYC** — identitas, alamat, pekerjaan, beneficial owner jika relevan, hasil verifikasi, bukti.
3. **Pengajuan & Pinjaman** — histori seluruh pengajuan, kontrak, status, saldo, dan tunggakan.
4. **Agunan** — passport, valuasi, lokasi custody, mutasi, asuransi, dan status fisik.
5. **Pembayaran** — ledger pelanggan, receipt, reversal, alokasi pokok/bunga/biaya/denda.
6. **Komunikasi** — kontak, collection activity, janji bayar, kanal, hasil, rekaman bukti yang diizinkan.
7. **Consent & Dokumen** — versi dokumen, purpose, waktu, kanal, evidence hash, pencabutan.
8. **SLIK & Regulator** — mapping subjek, kualitas, validation issue, histori periode.
9. **Pengaduan** — tiket, kategori, SLA, resolusi, kompensasi.
10. **Aktivitas & Audit** — event bisnis terurut dan dapat difilter.

### Tindakan

- Buat pengajuan.
- Perbarui kontak/identitas dengan before-after dan approval sesuai risk.
- Verifikasi KYC dan unggah bukti.
- Rekam/pencabutan consent.
- Tambah/koreksi watchlist dengan reason code dan maker-checker.
- Freeze/unfreeze dengan alasan, durasi, dan approval.
- Tandai potensi duplikasi dan merge dengan preview dampak.
- Buat pengaduan atau tugas tindak lanjut.

Tidak ada hard delete debitur yang sudah memiliki transaksi.

## 2. Pengajuan pinjaman

State baseline:

```text
DRAFT → SUBMITTED → TRIAGE → APPRAISAL_REQUIRED → APPRAISED
      → OFFERED → ACCEPTED → AGREEMENT_PENDING → READY_TO_DISBURSE
      → DISBURSED → ACTIVE → SETTLED/CLOSED
```

Jalur samping tervalidasi: `NEEDS_INFO`, `ON_HOLD`, `REJECTED`, `WITHDRAWN`, `EXPIRED`, `CANCELLED`. Setiap transition memiliki role, guard, reason code, evidence, dan SLA.

### Inbox pengajuan

- Queue berdasarkan stage, cabang, kategori agunan, nilai, SLA, priority, assignee, dan exception.
- Saved views untuk intake, verification, appraisal, approval, dokumen, dan pencairan.
- Assignment tunggal/massal dengan capacity dan conflict warning.
- Duplicate detection terhadap debitur, identitas, device, kontak, dan agunan.

### Detail pengajuan

- Checklist intake, KYC, consent, dokumen, appraisal, offer, agreement, approval, pickup, custody, dan disbursement.
- Timeline event bisnis.
- Snapshot kebijakan produk dan biaya yang dipakai saat keputusan.
- Decision panel menampilkan guard yang lulus/gagal.
- Perbandingan requested amount, appraisal value, LTV, offer, dan disbursement.

## 3. Penaksiran

Penaksiran memiliki route dan queue sendiri. Penaksir hanya melihat cabang/kategori sesuai assignment dan sertifikasi.

### Workbench penaksir

- Informasi aset dan foto terstruktur.
- Checklist pemeriksaan fisik per kategori.
- Sumber harga pembanding, tanggal, wilayah, kondisi, dan confidence.
- Hasil AI sebagai rekomendasi dengan model/version/source, tidak menjadi keputusan final.
- Nilai pasar, nilai likuidasi, faktor koreksi, LTV, dan nilai rekomendasi.
- Evidence annotation dan alasan deviasi.
- Conflict of interest declaration.
- Review supervisor jika melewati threshold atau confidence rendah.

Revisi tidak menimpa hasil lama. Setiap versi appraisal memiliki status, author, approver, timestamp, alasan, dan evidence hash.

## 4. Penawaran dan perjanjian

- Offer memiliki masa berlaku, snapshot rate/fee, jadwal, syarat, dan approval.
- Simulasi menjelaskan pokok, bunga/ujrah, biaya, denda, total kewajiban, dan skenario keterlambatan.
- Acceptance menyimpan kanal, timestamp, identitas penerima, dan versi dokumen.
- Agreement generator memakai template terversi dan data snapshot.
- Perubahan setelah acceptance memerlukan offer/version baru.
- Signature evidence, checksum, dan arsip dokumen dicatat.

## 5. Pickup, passport agunan, dan custody

### Pickup

- Assignment petugas dan kapasitas rute.
- Jadwal, lokasi, contact window, proof of pickup, geolocation bila diizinkan, dan exception.
- Serah terima memakai manifest, foto, seal/tag, waktu, dan dua pihak.

### Passport agunan

- ID/QR unik, kategori, atribut, foto, serial, owner/customer, appraisal terakhir, kontrak, status, dan custody location.
- QR tidak memuat PII langsung.
- Duplicate serial/tag check dan lost/damaged/fraud flags.

### Chain of custody

```text
PICKUP_ASSIGNED → PICKED_UP → IN_TRANSIT → RECEIVED
→ QC_VERIFIED → STORED → MOVED/COUNTED → RELEASE_PENDING
→ RELEASED/LIQUIDATION_PROCESS
```

Setiap perpindahan mencatat asal, tujuan, petugas menyerahkan/menerima, waktu, alasan, evidence, dan approval sesuai risiko. Movement tidak boleh mengubah histori.

### Stock opname

- Buat sesi dengan scope cabang/gudang/rak dan cutoff.
- Freeze atau aturan mutation window.
- Blind count dan recount oleh petugas berbeda.
- Klasifikasi selisih: missing, unexpected, wrong location, damaged, tag mismatch.
- Investigation case, root cause, evidence, approval resolution, dan adjustment event.

## 6. Teller, kas, dan pembayaran

### Teller session

- Open session dengan opening balance yang disetujui.
- Cash in/out tercatat terhadap source transaction dan receipt.
- Limit teller/cashbox, dual control untuk nominal tertentu.
- Cash count, expected vs actual, denomination breakdown, variance case.
- Close session dan supervisor sign-off.
- Implementasi saat ini mengunci satu sesi aktif per cashbox, mengambil saldo buku saat close, mewajibkan alasan untuk selisih, dan mengirim selisih ke approval branch manager dengan separation of duty.
- Penolakan supervisor membuka kembali sesi untuk recount; persetujuan menyimpan approver dan waktu keputusan pada sesi serta approval event ledger.
- Denomination breakdown, lampiran berita acara, batas toleransi bertingkat, dan serah-terima shift masih menjadi pekerjaan lanjutan sebelum go-live.

### Pembayaran

- Idempotent posting.
- Allocation rule terversi untuk pokok, bunga/ujrah, fee, denda.
- Receipt bernomor unik dan dapat diverifikasi.
- Reversal adalah transaksi lawan, tidak menghapus transaksi awal.
- Refund, waiver, adjustment, dan backdate memakai approval serta accounting period guard.

## 7. Collection

- Queue berdasarkan DPD, bucket, exposure, risk, branch, promise-to-pay, dan strategy.
- Case owner, next action date, contact policy, dan SLA.
- Activity log terstruktur: kanal, pihak dihubungi, outcome, notes, evidence.
- Implementasi tersedia: queue tenant/cabang, detail kasus, DPD dan aging, exposure, strategi, tahap, next action SLA, last contact, activity timeline, serta promise-to-pay dengan resolusi kept/broken/cancelled.
- Broken promise otomatis menaikkan kasus ke intensive collection, mengganti strategi menjadi field visit, dan membuat tindakan lanjutan 24 jam.
- Settlement tetap menjadi sumber kebenaran pembayaran; menandai promise `kept` tidak memposting kas atau mengurangi saldo pinjaman.
- Promise-to-pay: jumlah, tanggal, status kept/broken, dan follow-up otomatis.
- Restrukturisasi, settlement, atau penanganan agunan mengikuti approval matrix.
- Complaint dan vulnerable customer flag terlihat pada queue.

## 8. General ledger dan rekonsiliasi

- Chart of accounts terversi per tenant dengan effective date.
- Posting rules berdasarkan domain event; setiap jurnal memiliki source event dan correlation ID.
- Journal balanced sebelum commit.
- Accounting period open/close/lock.
- Manual journal terbatas, wajib reason, attachment, dan maker-checker.
- Reversal memakai contra entry.
- Rekonsiliasi bank, cashbox, payment channel, loan subledger, dan custody exposure.
- Unreconciled item menjadi exception case dengan owner dan aging.

## 9. Exception, approval, complaint, dan support

### Exception case

Field minimum: type, severity, tenant, branch, aggregate, source event, owner, SLA, root cause, action plan, evidence, approval, resolution, dan reopened count.

Implementasi saat ini menyediakan Incident & Exception Register tenant-scoped dan branch-scoped, detail kasus, severity, SLA, owner, root cause, corrective action, catatan investigasi append-only, status agunan `incident_hold`, approval resolusi oleh branch manager, serta reopen counter. Persetujuan resolusi memulihkan status agunan sebelum incident; penolakan mengembalikan kasus ke investigasi.

Lampiran bukti khusus incident, taxonomy root-cause terversi, relasi banyak aggregate, serta dashboard tren CAPA masih dilanjutkan.

### Approval inbox

- Queue berdasarkan authority matrix, nominal, product, branch, dan risk.
- Reviewer melihat before-after, policy, conflict, evidence, serta histori approval.
- Maker tidak boleh menjadi checker pada command yang sama.
- Approve, reject, request changes, dan delegate semuanya direkam sebagai event.

### Complaint/support

- Intake multi-channel, nomor tiket, kategori, pelanggan/kontrak terkait.
- SLA response/resolution, escalation, komunikasi, evidence, outcome, compensation.
- Complaint regulator dan insiden operasional dibedakan tetapi dapat saling direlasikan.

## 10. Settings dan master process

Settings dibangun sebagai configuration workbench:

| Area | Isi minimum |
|---|---|
| Institution | legal entity, izin, kantor, pejabat, identitas regulator |
| Branch | kode, alamat, wilayah, timezone, status, service area |
| Product & pricing | produk, tenor, rate/ujrah, fee, denda, LTV, limit |
| Appraisal | kategori, checklist, threshold, source, approval |
| Workflow & SLA | state, transition, guard, assignee, escalation |
| Custody | gudang, rak, kapasitas, movement policy, insurance |
| Documents | numbering, template, signature, retention |
| Accounting | COA, posting rule, period, cost center |
| Regulatory | reporter identity, code set, calendar, template version |
| Access | role, scope, ABAC, approval authority, separation of duty |
| Integration | endpoint, secret reference, webhook, retry, circuit breaker |
| Notification | template, channel, recipient rule, quiet hours |
| Security & retention | MFA, session, masking, retention, legal hold |

Semua konfigurasi penting memiliki draft, review, approved, effective, superseded; preview dampak; effective date; maker-checker; dan rollback melalui versi baru.

## Task modul

- [ ] CRM-101: customer list server-side dan detail 360°.
- [ ] CRM-102: KYC, consent, correction, duplicate merge, watchlist workflow.
- [ ] LON-101: application queue/detail dan state guard lengkap.
- [ ] APR-101: appraisal queue/workbench/versioning/approval.
- [ ] DOC-101: offer, agreement generator, signature evidence.
- [ ] COL-101: passport, QR, chain of custody, movement, release.
- [ ] INV-101: stock opname blind count, discrepancy, resolution.
- [ ] FIN-101: teller/cash session, receipt, variance, close.
- [ ] FIN-102: payment allocation, reversal, refund, adjustment.
- [ ] ACC-101: COA, posting rule, period lock, reconciliation.
- [ ] CLC-101: collection queue, contact policy, promise-to-pay.
- [ ] CMP-101: exception, approval, complaint, support SLA.
- [ ] CFG-101: configuration workbench terversi dan effective-dated.
