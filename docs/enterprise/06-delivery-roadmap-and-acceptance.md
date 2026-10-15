# 06 — Roadmap Implementasi dan Acceptance

## Cara menggunakan roadmap

Pekerjaan dibagi menjadi release slice yang menghasilkan alur dapat diuji. Estimasi waktu baru dibuat setelah discovery data, SOP, dan kapasitas tim selesai. Label:

- **P0**: dibutuhkan sebelum pilot operasional terkontrol.
- **P1**: dibutuhkan sebelum perluasan pilot/produksi terbatas.
- **P2**: optimasi setelah kontrol inti stabil.

## Fase 0 — Baseline, SOP, dan regulasi (P0)

- [ ] F0-01: finalisasi glossary, role, branch scope, state machine, reason code, dan RACI.
- [ ] F0-02: regulatory walkthrough POJK/SEOJK dan lampiran resmi.
- [ ] F0-03: data dictionary dan system-of-record ownership.
- [ ] F0-04: threat model, data classification, retention, RPO/RTO.
- [ ] F0-05: arsitektur route, event, approval, configuration versioning, dan reporting.

Exit: artefak disetujui product, operations, finance, risk/compliance, security, dan engineering.

## Fase 1 — Enterprise shell dan design system (P0)

- [x] F1-01: route unik dan kompatibilitas route lama.
- [x] F1-02: sidebar collapse/expand, group accordion, mobile drawer.
- [x] F1-03: satu active leaf pada seluruh route baru.
- [ ] F1-04: tabel, filter, saved views, record header, timeline, evidence, approval components.
- [ ] F1-05: perbaikan responsive, overflow, keyboard, WCAG, microcopy.
- [ ] F1-06: global search dan notification center yang terhubung data.

Exit: shell lulus visual regression, keyboard, responsive, dan active-route tests.

## Fase 2 — Customer 360 dan governance identitas (P0)

- [x] F2-01: customer list tenant-scoped dan detail route.
- [ ] F2-02: KYC, consent, document evidence, history.
  - Fondasi KTP/KYC, bukti terenkripsi, maker-checker, dan event history tersedia; provider resmi, screening, malware scan, dan ongoing monitoring masih terbuka.
- [ ] F2-03: customer-loan-collateral-payment relationships.
- [ ] F2-04: duplicate, merge, correction, freeze, watchlist workflow.
- [ ] F2-05: tenant/branch/masking authorization tests.

Exit: operator dapat membuka detail dan menjalankan tindakan aman; auditor dapat melihat historinya.

## Fase 3 — Loan origination dan appraisal (P0)

- [ ] F3-01: application queue/detail/checklist/assignment/SLA.
- [ ] F3-02: state machine dan server-side transition guards.
- [ ] F3-03: appraisal workbench, evidence, version, supervisor review.
- [ ] F3-04: offer, simulation, acceptance, agreement, signature evidence.
- [ ] F3-05: approval matrix dan domain events.

Exit: happy path dan negative path tervalidasi end-to-end tanpa perubahan status manual.

## Fase 4 — Collateral, pickup, custody, inventory (P0)

- [ ] F4-01: passport/QR dan detail record.
- [ ] F4-02: pickup scheduling dan proof of handover.
- [ ] F4-03: custody receive/QC/store/move/release.
  - Receive/store/release dan mutasi vault dua tahap tersedia; mutasi menyimpan asal, tujuan, seal keluar/masuk, dispatch, receiver berbeda, timestamp, dan event passport.
- [ ] F4-04: stock opname blind count/recount/discrepancy.
  - Snapshot register per vault, first count blind, klasifikasi observasi fisik, variance, penguncian sesi per lokasi, recount oleh petugas berbeda, dan approval branch manager sudah tersedia.
  - Assignment acak, evidence per variance, investigation otomatis untuk confirmed variance, dan cycle-count scheduler masih dilanjutkan.
- [ ] F4-05: chain-of-custody event dan reconciliation.

Exit: lokasi dan status setiap agunan dapat direkonstruksi; selisih tidak dapat ditutup tanpa bukti dan approval.

## Fase 5 — Finance, accounting, dan collection (P0/P1)

- [ ] F5-01: teller/cashbox open, transaction, count, variance, close.
  - Open/close, eksklusivitas satu sesi aktif per cashbox, cash count expected-versus-actual, alasan selisih, riwayat 50 sesi, serta approval independen branch manager sudah tersedia.
  - Denomination breakdown, tolerance matrix, bukti berita acara, cash transfer antar-teller, dan end-of-day branch reconciliation masih dilanjutkan.
- [ ] F5-02: payment allocation, receipt, reversal, refund.
- [ ] F5-03: COA, posting rules, journal, period lock.
  - COA dasar, jurnal berimbang, register dan drill-down jurnal, reversal via approval, serta accounting period lock tersedia; posting rule configurator dan reopen terkontrol masih dilanjutkan.
- [ ] F5-04: bank/subledger/cash reconciliation dan exception.
- [ ] F5-05: collection queue, activity, promise-to-pay, strategy.
  - Queue, detail kasus, DPD/aging, strategi, stage, SLA next action, structured contact note, promise-to-pay, serta broken-promise escalation sudah tersedia.
  - Contact policy effective-dated, evidence attachment, assignment balancing, legal case handoff, dan dialer/messaging integration masih dilanjutkan.

Exit: transaksi uang mempunyai source event, balanced journal, receipt, dan rekonsiliasi.

## Fase 6 — Compliance, audit, settings, support (P0/P1)

- [ ] F6-01: domain event ledger dan audit explorer.
- [ ] F6-02: approval inbox, separation of duty, delegation, escalation.
  - Approval ledger generik, snapshot keputusan, SLA, histori append-only, dan pencegahan maker menjadi checker sudah tersedia.
  - Appraisal, stock opname, pelepasan agunan setelah settlement, reversal jurnal, dan sign-off laporan regulator sudah masuk approval inbox.
  - Delegasi/out-of-office berjangka, pencabutan tanpa menghapus histori, jejak keputusan delegasi, dan sweep eskalasi SLA dua tingkat sudah tersedia.
  - Integrasi scheduler terkelola untuk menjalankan sweep tanpa tindakan operator masih menjadi deployment task.
- [ ] F6-03: exception case dan investigation workflow.
  - Incident register nyata, branch scope, owner, SLA, root cause, corrective action, event history, collateral hold, maker-checker resolution, dan reopen tersedia.
  - Evidence attachment khusus kasus, taxonomy efektif-bertanggal, multi-aggregate linking, dan CAPA analytics masih dilanjutkan.
- [ ] F6-04: complaint/support ticket dan SLA.
  - Intake multi-channel, tiket unik, Customer 360, branch scope, vulnerable/regulator flags, owner, response/resolution SLA, komunikasi, escalation, outcome, compensation decision, maker-checker resolution, dan reopen tersedia.
  - Evidence, messaging/email adapter, refund posting, acknowledgement regulator, dan taxonomy effective-dated masih dilanjutkan.
- [ ] F6-05: configuration workbench versioned/effective-dated.
- [ ] F6-06: privileged access, MFA, session, security event.

Exit: semua command P0 memiliki event, kontrol approval, dan konfigurasi terversi.

## Fase 7 — OJK, SLIK, dan management reporting (P1)

- [ ] F7-01: reporting calendar dan obligation profile.
- [ ] F7-02: OJK monthly templates, lineage, validation, reconciliation.
  - Baseline Formulir Lampiran II SEOJK 17/SEOJK.06/2025, snapshot GL/loan/aging, dan rekonsiliasi cabang tersedia; seluruh formulir profil dan kamus field resmi masih dilanjutkan.
- [ ] F7-03: SLIK segment mapping, reference codes, validation.
  - Snapshot terenkripsi D01/F01/A01, validasi KYC/NIK/DATI II/kode subjek, segment count, dan rekonsiliasi outstanding sudah tersedia.
  - Kamus seluruh field, code set effective-dated, correction/delete semantics, dan uji validator resmi masih dilanjutkan.
- [ ] F7-04: revision, review, sign-off, file generation, checksum.
  - Sign-off maker-checker dan paket ZIP bermanifest dengan Formulir 1100/2100/9100 serta checksum SHA-256 tersedia.
  - Aktivasi template regulator juga memakai approval independen; paket SLIK menyimpan validation results dan segmen terenkripsi-at-rest.
- [ ] F7-05: submission evidence/acknowledgement dan adapter resmi bila tersedia.
- [ ] F7-06: health, financial, operational, risk dashboards dari governed metrics.

Exit: file periode uji lolos validator resmi dan sign-off compliance.

## Fase 8 — Production readiness (P0 sebelum go-live)

- [ ] F8-01: migration rehearsal dan reconciliation 100% record kritis.
- [ ] F8-02: performance/load/soak test pada volume target.
- [ ] F8-03: security review, penetration test, dependency remediation.
- [ ] F8-04: backup restore dan DR drill.
- [ ] F8-05: observability, SLO, alert, on-call, incident runbook.
  - Liveness, readiness dependency + schema revision, release identity, request correlation, security headers, dan runbook awal sudah tersedia; telemetry, SLO, alert routing, dan roster on-call masih dilanjutkan.
- [ ] F8-06: UAT per role/cabang dan remediation.
- [ ] F8-07: SOP, training, access provisioning, support readiness.
- [ ] F8-08: pilot terbatas, parallel run, go/no-go, rollback plan.

Exit: sign-off formal business owner, operations, finance, risk/compliance, security, IT operations, dan data owner.

## Cross-cutting acceptance matrix

| Dimensi | Kriteria minimum |
|---|---|
| Functional | happy path, negative path, retry, cancel, reversal, correction teruji |
| Tenant isolation | akses silang tenant ditolak pada list/detail/action/export/job/file |
| Branch/role scope | ABAC sesuai assignment, category, amount authority, dan purpose |
| Audit | command penting menghasilkan event, diff, actor, reason, approval, evidence |
| Data integrity | transaction atomic, idempotent, referential integrity, reconciliation |
| UX | satu menu aktif, keyboard, responsive, loading/error/empty/read-only lengkap |
| Performance | target latency dan concurrency disepakati serta diuji dengan dataset representatif |
| Security | MFA privileged, session control, encryption, masking, secure upload/download |
| Resilience | retry, outbox, dead-letter handling, backup/restore, DR |
| Regulatory | template/version/lineage/validation/sign-off/acknowledgement terbukti |

## Test suite wajib

### Unit dan contract

- State transition guard, calculations, allocation, posting rule, validation rule.
- API request/response contract dan event schema compatibility.

### Integration

- Database transaction dan rollback.
- Outbox/idempotency/retry.
- Object storage/evidence/checksum.
- Accounting and subledger reconciliation.

### Authorization

- Matriks role × tenant × branch × state × action.
- Object ID tampering, export, background job, file access, and admin override.

### End-to-end

- Customer → application → appraisal → offer → agreement → custody → disbursement.
- Payment → allocation → journal → reconciliation → settlement.
- Late payment → collection → promise → resolution.
- Stock opname → discrepancy → investigation → approval.
- Report extract → correction → review → sign-off → file → acknowledgement.

### UX dan accessibility

- Visual regression pada viewport target.
- Keyboard navigation, focus, screen reader landmarks, contrast.
- Exactly one active navigation leaf.
- Table overflow dan sticky behavior.

## Release dan migrasi

- Feature release dibatasi tenant/cabang/role, dengan owner dan expiry.
- Database migration backward-compatible bila memungkinkan.
- Backfill idempotent dengan progress dan reconciliation report.
- Route lama diberi redirect; endpoint lama memiliki deprecation window.
- Pilot memakai synthetic/sanitized data sebelum parallel run data produksi.
- Setiap release memiliki rollout, monitoring, rollback, dan communication plan.

## Prioritas implementasi pertama

Sprint implementasi pertama setelah approval rancangan:

1. Pecah route dan perbaiki active state.
2. Bangun sidebar modern collapse/expand dan responsive shell.
3. Bangun DataTable/RecordHeader/Timeline/ApprovalPanel bersama.
4. Ubah CRM menjadi list + detail yang dapat diklik.
5. Pisahkan application dan appraisal queue.
6. Bentuk domain event schema sebelum menambah banyak command baru.

## Go-live decision

Produk hanya diberi label **siap operasi** setelah seluruh gate P0 selesai. Fitur yang belum lulus tetap dibatasi melalui permission/release configuration dan tidak ditampilkan sebagai kontrol aktif.
