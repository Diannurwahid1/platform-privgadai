# PrivGadai — Implementation Ledger

Dokumen ini menjadi daftar kerja teknis aktif berdasarkan business blueprint dan technical blueprint. Status **tersedia** berarti sudah mempunyai model data, API, UI operasional, migrasi, dan pengujian terpilih. Status **pilot** belum berarti siap produksi penuh.

## Status saat ini

| Area | Implementasi yang tersedia | Gate berikutnya |
|---|---|---|
| Enterprise shell | Sidebar collapse/expand, route unik, satu active leaf, global search | visual regression, keyboard audit, WCAG |
| Multi-tenant | tenant scoped query, composite tenant FK pada domain kritis, role dan branch assignment | negative authorization matrix seluruh object/export/job |
| Customer 360 | profil, relasi pengajuan/pinjaman/agunan/collection, consent, activity | duplicate/merge/correction/freeze workflow |
| KYC/CDD | data KTP/NIK terenkripsi, masking, upload KTP terenkripsi, checksum, maker-checker, expiry, event history | provider Dukcapil/eKYC resmi, PEP/sanction provider, malware scan, monitoring berkala |
| Loan origination | intake, queue, detail, state guard, offer, acceptance, agreement evidence dasar | assignment balancing, request changes, e-sign provider, policy exception |
| Appraisal | human appraisal, revision, evidence konteks, LTV guard, approval independen | comparable register, price source versioning, specialist matrix, re-appraisal |
| Custody | passport, pickup, receive/store/release, mutasi vault dua petugas, seal chain | QR scan, proof-of-handover signature, insurance workflow |
| Stock opname | snapshot register, blind first count, variance, recount user berbeda, approval | evidence per variance, investigation otomatis, cycle-count scheduler |
| Teller | exclusive cashbox, opening/closing count, selisih wajib alasan, approval supervisor, history | denomination count, tolerance matrix, cash transfer, branch EOD |
| Accounting | COA dasar, balanced journal, drill-down, reversal approval, period close/lock | posting-rule configurator, reconciliation workbench, controlled reopen |
| Collection | case detail, strategy/stage, SLA, notes, PTP, broken-promise escalation | contact policy versioning, evidence, legal handoff, channel integration |
| Incident/exception | real case register, branch scope, SLA, owner, RCA/CAPA, event log, collateral hold, approval resolution, reopen | evidence case, taxonomy versioning, multi-aggregate relation, CAPA analytics |
| Complaint/support | tiket unik, Customer 360, branch scope, owner, response/resolution SLA, komunikasi, escalation, outcome, compensation decision, approval, reopen | evidence, channel adapter, refund posting, regulator acknowledgement, taxonomy versioning |
| Approval | append-only ledger, snapshot, separation of duty, role/branch scope, delegation, SLA escalation | managed scheduler, authority matrix by amount/product/risk |
| Audit | business domain event explorer dan technical request audit | immutable archival, retention/legal hold, SIEM export |
| OJK monthly | controlled snapshot, Form 1100/2100/9100 package, validation, reconciliation, checksum, sign-off | seluruh lampiran resmi, official validator test, submission acknowledgement |
| SLIK | encrypted D01/F01/A01 snapshot, NIK protected at rest, validation, reconciliation, ZIP export | full official field/code dictionary, correction/delete semantics, official validator |
| Runtime | liveness/readiness, migration head check, request ID, headers, release identity | telemetry backend, SLO/alert routing, backup restore, DR, load/security test |

## P0 — sebelum pilot operasional terkontrol

- [ ] Lengkapi branch/role/object authorization tests pada seluruh detail, command, export, dan file.
- [ ] Tambahkan payment allocation rule, receipt numbering, refund, waiver, adjustment, dan contra posting.
- [ ] Bangun reconciliation workbench untuk cashbox, loan subledger, GL, dan bank statement.
- [x] Bangun complaint/support case dengan SLA response dan resolution, escalation, komunikasi, outcome, dan maker-checker.
- [ ] Bangun configuration workbench versioned/effective-dated untuk product, pricing, appraisal, workflow, accounting, custody, regulatory, dan authority matrix.
- [ ] Tambahkan evidence attachment dan malware scan pada incident, appraisal, custody, serta KYC.
- [ ] Terapkan MFA privileged, session inventory/revoke, step-up auth, dan security event explorer.
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
