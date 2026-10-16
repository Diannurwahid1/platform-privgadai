# 05 — Domain Audit, Keamanan, dan Kontrol

## Pemisahan log

PrivGadai membutuhkan tiga lapisan observabilitas:

1. **Technical access log** — request, response status, latency, trace, IP, user agent.
2. **Security audit log** — login, MFA, token/session, permission denial, secret/config access, export.
3. **Domain event ledger** — fakta bisnis yang dapat dibaca auditor dan operator.

Halaman “Audit” utama menampilkan domain event. Technical log tersedia untuk admin/engineer yang berwenang.

## Model domain event

Field minimum:

| Field | Keterangan |
|---|---|
| `event_id` | UUID unik |
| `tenant_id`, `branch_id` | batas isolasi dan scope |
| `aggregate_type`, `aggregate_id` | customer, application, appraisal, collateral, loan, payment, report |
| `event_type`, `event_version` | nama stabil dan versi payload |
| `occurred_at`, `recorded_at` | waktu bisnis dan waktu persist |
| `actor_type`, `actor_id`, `actor_role` | user, service, integration |
| `command_id`, `correlation_id`, `causation_id` | rekonstruksi satu proses |
| `reason_code`, `reason_text` | alasan terstruktur dan catatan |
| `before`, `after` | diff terkontrol; PII sensitif dimasking/enkripsi |
| `policy_version` | kebijakan yang dipakai |
| `approval_id` | referensi approval bila diperlukan |
| `evidence_refs`, `evidence_hashes` | bukti tanpa menaruh binary di event |
| `source` | UI, API, batch, regulator, integration |
| `integrity_hash`, `previous_hash` | tamper evidence per stream/partition |

Event append-only. Koreksi dibuat sebagai event baru. Retention dan legal hold diterapkan berdasarkan klasifikasi.

## Katalog event minimum

### Customer

`CustomerCreated`, `CustomerIdentityCorrected`, `KycVerified`, `ConsentCaptured`, `ConsentWithdrawn`, `RiskStatusChanged`, `CustomerFrozen`, `DuplicateMerged`.

### Loan dan appraisal

`ApplicationSubmitted`, `ApplicationAssigned`, `ApplicationStateChanged`, `AppraisalRecorded`, `AppraisalRevised`, `AppraisalApproved`, `OfferIssued`, `OfferAccepted`, `AgreementSigned`, `LoanApproved`, `DisbursementPosted`, `LoanSettled`.

### Collateral

`PickupAssigned`, `CollateralPickedUp`, `CustodyReceived`, `CustodyQcVerified`, `CollateralStored`, `CollateralMoved`, `InventoryCounted`, `InventoryDiscrepancyRaised`, `DiscrepancyResolved`, `CollateralReleased`.

### Finance

`TellerSessionOpened`, `CashMovementPosted`, `PaymentPosted`, `PaymentAllocated`, `PaymentReversed`, `CashVarianceRaised`, `TellerSessionClosed`, `JournalPosted`, `JournalReversed`, `PeriodLocked`, `ReconciliationCompleted`.

### Compliance dan regulator

`ApprovalRequested`, `ApprovalDecided`, `ExceptionRaised`, `ExceptionResolved`, `ComplaintCreated`, `ComplaintResolved`, `ReportExtracted`, `ReportValidated`, `ReportApproved`, `ReportGenerated`, `ReportSubmitted`, `ReportAcknowledged`, `ConfigurationActivated`.

## Transactional consistency

- Aggregate state, journal/outbox record, dan domain event ditulis dalam satu database transaction.
- Outbox publisher mengirim integrasi secara idempotent.
- Consumer menyimpan idempotency key dan tidak memproses event dua kali.
- Event tidak boleh menyatakan sukses sebelum commit bisnis selesai.
- Batch memiliki correlation ID dan per-item outcome.

## Audit explorer

Filter: periode, tenant, cabang, actor, event type, aggregate, customer, severity, reason, approval, dan correlation ID.

Fitur:

- timeline manusiawi dalam bahasa Indonesia;
- before-after untuk field yang berubah;
- relasi command → approval → event → journal → report;
- evidence viewer dan integrity status;
- export bertandatangan/checksum dengan masking sesuai role;
- saved investigation case;
- akses technical trace hanya untuk role yang tepat.

## Multi-tenant, branch scope, dan ABAC

- `tenant_id` wajib pada seluruh aggregate operasional, event, job, file, cache key, search index, dan report run.
- Query server selalu menambahkan tenant predicate dari session/token, bukan input client.
- `branch_id` diperiksa terhadap assignment, role, category, product, amount authority, dan purpose.
- Endpoint detail tidak boleh menerima ID lintas tenant walaupun UUID diketahui.
- Background job membawa tenant context eksplisit.
- Object storage memakai prefix/bucket policy tenant dan signed URL berumur pendek.
- Cross-tenant admin access memerlukan role khusus, reason, dan security event.

## RBAC, ABAC, dan separation of duty

Contoh atribut: tenant, branch, region, role, job assignment, product, collateral category, amount band, transaction state, risk level, dan ownership.

Kontrol wajib:

- maker tidak menjadi checker untuk transaksi yang sama;
- penaksir tidak menyetujui keputusan di luar authority;
- teller tidak dapat mengubah GL langsung;
- correction laporan dipisahkan dari sign-off;
- emergency override terbatas waktu, beralasan, dan direview pascakejadian.

Policy decision dicatat beserta policy version dan hasil allow/deny.

## Keamanan aplikasi dan data

- MFA untuk privileged role dan aksi berisiko.
- Session rotation, idle/absolute timeout, revoke, dan device/session list.
- Secret hanya disimpan di secret manager; UI menampilkan metadata, bukan nilai.
- Enkripsi transit dan at-rest; field encryption/tokenization untuk identitas sensitif.
- Masking berdasarkan purpose dan role.
- Malware scan dan content-type validation untuk upload.
- Signed download URL, watermark untuk dokumen sensitif, dan download event.
- Rate limit, anti-automation, CSRF/XSS/SQLi controls, CSP, secure headers.
- Dependency/SAST/DAST/secret scan dan patch SLA.
- Backup terenkripsi, restore drill, RPO/RTO, dan disaster recovery runbook.

## Retention, privacy, dan consent

- Data classification serta retention schedule disetujui legal/compliance.
- Consent menyimpan purpose, legal basis, channel, text version, timestamp, actor/device/evidence.
- Withdrawal menghentikan pemrosesan yang bergantung pada consent, dengan pengecualian kewajiban hukum terdokumentasi.
- Purge/anonymization hanya berjalan setelah retention, legal hold, dan referential checks.
- Subject request menjadi case tervalidasi dan tercatat.

## Task kontrol

- [ ] AUD-101: definisikan schema, registry, dan versioning domain event.
- [ ] AUD-102: transactional outbox dan idempotent publisher/consumer.
- [ ] AUD-103: instrument command P0 dengan event dan correlation ID.
- [ ] AUD-104: audit explorer, timeline, diff, evidence, export.
- [ ] AUD-105: integrity chain, retention, legal hold, dan verification job.
- [ ] SEC-101: tenant/branch negative authorization test di seluruh API.
  - Core operational read boundary sudah diterapkan pada dashboard, inbox, detail pengajuan, Customer 360, KYC, timeline agunan, evidence download, custody movement, dan business audit. Owner/admin tetap tenant-wide; member hanya melihat cabang dengan assignment aktif. Matrix finance, collection, regulatory export, serta background job belum menutup gate ini.
- [ ] SEC-102: policy engine RBAC/ABAC dan policy decision log.
- [ ] SEC-103: maker-checker serta conflict of interest enforcement.
- [x] SEC-104: MFA/session/security center untuk privileged users.

Implementasi SEC-104 mencakup TOTP RFC 6238 dengan secret terenkripsi, recovery code sekali pakai yang hanya disimpan sebagai hash, lockout percobaan, session record dengan absolute expiry dan immediate revoke, current/remote device inventory, step-up berjangka, serta security event ledger. Token baru membawa `sid` dan session tersebut divalidasi pada setiap request. Production mewajibkan `PRIVILEGED_MFA_ENFORCED=true`; approval dan perubahan delegasi memerlukan step-up aktif.
- [ ] SEC-105: data classification, encryption, masking, secure file access.
- [ ] OPS-101: backup/restore, DR drill, monitoring, alert, runbook, incident response.

## Acceptance criteria

- [ ] Auditor dapat merekonstruksi satu transaksi dari intake sampai jurnal dan laporan.
- [ ] Event tidak dapat diubah/dihapus lewat API aplikasi.
- [ ] Diff tidak membocorkan secret atau PII ke role yang tidak berhak.
- [ ] Percobaan akses lintas tenant/cabang selalu ditolak dan tercatat.
- [ ] Maker-checker tidak dapat dilewati melalui UI, API, batch, atau retry.
- [ ] Restore drill memenuhi RPO/RTO yang disepakati dan memiliki evidence.
