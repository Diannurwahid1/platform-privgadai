# PrivGadai — Implementation Ledger

Dokumen ini menjadi daftar kerja teknis aktif berdasarkan business blueprint dan technical blueprint. Status **tersedia** berarti sudah mempunyai model data, API, UI operasional, migrasi, dan pengujian terpilih. Status **pilot** belum berarti siap produksi penuh.

## Status saat ini

| Area | Implementasi yang tersedia | Gate berikutnya |
|---|---|---|
| Enterprise shell | Sidebar collapse/expand, route unik, satu active leaf, global search | visual regression, keyboard audit, WCAG |
| Multi-tenant | tenant scoped query, composite tenant FK pada domain kritis, role/branch assignment, object filtering pada operasi, KYC, evidence, custody, finance, collection, inventory, audit, dan regulator | background job tenant context serta branch attribution jurnal/report |
| Customer 360 | profil, relasi pengajuan/pinjaman/agunan/collection, consent, activity | duplicate/merge/correction/freeze workflow |
| KYC/CDD | data KTP/NIK terenkripsi, masking, upload KTP terenkripsi, checksum, malware scan/karantina, maker-checker, expiry, event history | provider Dukcapil/eKYC resmi, PEP/sanction provider, monitoring berkala |
| Loan origination | intake, queue, detail, state guard, offer, acceptance, agreement evidence dasar | assignment balancing, request changes, e-sign provider, policy exception |
| Appraisal | human appraisal, revision, evidence tertaut dan dipindai, LTV guard, approval independen dengan evidence gate | comparable register, price source versioning, specialist matrix, re-appraisal |
| Custody | passport, pickup, receive/store/release, mutasi vault dua petugas, seal chain, evidence gate saat dispatch | QR scan, proof-of-handover signature, insurance workflow |
| Stock opname | snapshot register, blind first count, variance, recount user berbeda, approval | evidence per variance, investigation otomatis, cycle-count scheduler |
| Teller | exclusive cashbox, opening/closing count, selisih wajib alasan, approval supervisor, history | denomination count, tolerance matrix, cash transfer, branch EOD |
| Payment | partial/full payment, receipt unik, alokasi fee→principal, idempotency, teller guard, refund/reversal/waiver/adjustment approval, contra journal | payment gateway callback, receipt PDF/signature, configurable allocation waterfall |
| Accounting | COA dasar, balanced journal, drill-down, reversal approval, period close/lock, cash/loan/bank reconciliation snapshot dan exception approval | posting-rule configurator, bank statement file adapter, controlled reopen |
| Collection | case detail, strategy/stage, SLA, notes, PTP, broken-promise escalation | contact policy versioning, evidence, legal handoff, channel integration |
| Incident/exception | real case register, branch scope, SLA, owner, RCA/CAPA, event log, evidence privat, collateral hold, approval resolution, reopen | taxonomy versioning, multi-aggregate relation, CAPA analytics |
| Complaint/support | tiket unik, Customer 360, branch scope, owner, response/resolution SLA, komunikasi, escalation, outcome, compensation decision, approval, reopen | evidence, channel adapter, refund posting, regulator acknowledgement, taxonomy versioning |
| Approval | append-only ledger, snapshot, separation of duty, role/branch scope, delegation, SLA escalation | managed scheduler, authority matrix by amount/product/risk |
| Audit | business domain event explorer dan technical request audit | immutable archival, retention/legal hold, SIEM export |
| OJK monthly | controlled snapshot, Form 1100/2100/9100 package, validation, reconciliation, checksum, sign-off | seluruh lampiran resmi, official validator test, submission acknowledgement |
| SLIK | encrypted D01/F01/A01 snapshot, NIK protected at rest, validation, reconciliation, ZIP export | full official field/code dictionary, correction/delete semantics, official validator |
| Configuration | version register, checksum, impact diff, effective date, maker-checker, scheduled activation, rollback, domain schema, runtime resolver; product/pricing/appraisal/workflow/accounting/custody/regulatory/access sudah terikat | managed scheduler dan binding domain integrasi tambahan |
| Identity security | TOTP MFA, one-time recovery code, encrypted secret, lockout, governed session inventory/revoke, step-up TTL, security event explorer | WebAuthn/passkey, enterprise IdP/SCIM, risk-based authentication |
| Runtime | liveness/readiness, migration head check, request ID, headers, release identity | telemetry backend, SLO/alert routing, backup restore, DR, load/security test |

## P0 — sebelum pilot operasional terkontrol

- [ ] Lengkapi branch/role/object authorization tests pada seluruh detail, command, export, dan file.
  - Matriks negatif mencakup dashboard, inbox, detail pengajuan, Customer 360, KYC, timeline agunan, evidence download, custody, finance, payment, reconciliation, collection, inventory, business audit, serta regulator/export. Job terjadwal dan branch attribution untuk jurnal/report agregat masih harus ditutup sebelum gate dinyatakan selesai.
- [x] Tambahkan payment allocation rule, receipt numbering, refund, waiver, adjustment, dan contra posting.
- [x] Bangun reconciliation workbench untuk cashbox, loan subledger, GL, dan bank statement.
  - Workbench membandingkan cash transaction ↔ GL, loan subledger ↔ receivable GL, dan total statement ↔ receipt per tanggal/cabang; snapshot, tolerance, variance, exception, root cause, dan approval resolution tersimpan.
  - Import file statement bank/provider, auto-matching per baris, dan scheduler EOD tetap menjadi P1 integrasi.
- [x] Bangun complaint/support case dengan SLA response dan resolution, escalation, komunikasi, outcome, dan maker-checker.
- [ ] Bangun configuration workbench versioned/effective-dated untuk product, pricing, appraisal, workflow, accounting, custody, regulatory, dan authority matrix.
  - Control plane, UI register/editor/diff/history, checksum, maker-checker, activation terjadwal, supersede, dan rollback melalui versi baru sudah tersedia.
  - Registry schema menolak field domain yang tidak dikenal, range tidak valid, JSON non-finite, dan secret plaintext. Resolver effective-dated sudah dipakai oleh product intake, plafon/tenor, pricing LTV/fee, payment allocation waterfall, submission SLA, dan approval SLA.
  - Appraisal evidence matrix, custody dispatch evidence, regulator template/validator gate, serta access authority limit sekarang membaca versi efektif.
  - Managed scheduler dan binding domain integrasi tambahan masih harus diselesaikan sebelum gate ditutup.
- [x] Tambahkan evidence attachment dan malware scan pada incident, appraisal, custody, serta KYC.
  - File diperiksa dari magic bytes, checksum SHA-256, active-content PDF, dan malware signature; file gagal dipindahkan ke zona karantina serta tidak dapat diunduh.
  - Appraisal/incident approval dan dispatch custody mewajibkan evidence bersih. KYC hanya dapat diverifikasi bila KTP depan berstatus bersih.
  - Environment production menolak startup bila scanner eksternal ClamAV tidak dipilih; mode built-in hanya untuk development/test.
- [x] Terapkan MFA privileged, session inventory/revoke, step-up auth, dan security event explorer.
  - TOTP secret terenkripsi, recovery code hanya sekali dan tersimpan sebagai hash, retry lockout, session ID tervalidasi per request, remote revoke, serta step-up 10 menit tersedia.
  - Approval decision dan delegasi memakai step-up gate ketika enforcement production aktif. Production menolak konfigurasi yang mematikan privileged MFA.
- [ ] Jalankan migration rehearsal, backup restore, load/soak, dependency/security scan, serta UAT per role dan cabang.

## P1 — sebelum produksi terbatas

- [ ] Integrasikan provider eKYC/Dukcapil yang memiliki kontrak dan dasar pemrosesan sah.
- [ ] Lengkapi PEP/sanctions/adverse media screening dan ongoing monitoring.
- [ ] Lengkapi seluruh kamus field dan code set resmi OJK/SLIK dengan effective date.
- [ ] Lulus validator resmi pada dataset periode uji dan simpan acknowledgement submission.
- [ ] Tambahkan reporting obligation calendar, correction workflow, resubmission, dan evidence regulator.
- [ ] Tambahkan QR custody, signature handover, insurance claim, auction/liquidation, dan legal handoff.
- [ ] Aktifkan telemetry, SLO, alert routing, on-call, incident runbook, RPO/RTO, dan DR drill.

## Acceptance wajib per slice

- Tenant lain tidak dapat membaca, mengubah, mengunduh, atau memutus record.
- User tanpa branch assignment tidak dapat menjalankan command cabang tersebut.
- Maker tidak dapat menjadi checker; delegasi menyimpan sumber kewenangan.
- Perubahan finansial memakai idempotency, balanced journal, period guard, dan reversal.
- Perubahan custody dapat direkonstruksi dari event, actor, waktu, lokasi, seal, dan evidence.
- Data sensitif dimasking di response biasa dan dienkripsi saat disimpan.
- UI menyediakan loading, error, empty, read-only, overflow, dan satu menu aktif.
- Migrasi Alembic, lint, typecheck, serta integration test terkait harus hijau sebelum commit.

## Catatan regulatory

Artefak OJK/SLIK saat ini adalah controlled work package internal. Status laporan hanya boleh disebut **submitted** setelah file lulus validator resmi dan acknowledgement dari kanal regulator disimpan. Implementasi tidak boleh mengarang format, code set, atau acknowledgement eksternal.
