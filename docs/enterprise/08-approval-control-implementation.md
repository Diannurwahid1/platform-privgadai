# Approval control implementation

Dokumen ini mencatat implementasi kontrol empat mata yang dipakai lintas proses PrivGadai. Sumber rancangan tetap `03-operational-modules-and-sop.md` dan `05-domain-audit-security-and-controls.md`.

## Model kontrol

Setiap command berisiko membuat `approval_request` dengan tenant, cabang bila relevan, agregat bisnis, versi, maker, peran checker, alasan, snapshot payload, prioritas, dan batas SLA. Keputusan menghasilkan `approval_event` append-only. Payload snapshot mempertahankan nilai yang benar-benar diperiksa sehingga perubahan record setelah permintaan tidak mengubah konteks persetujuan.

Aturan yang sudah ditegakkan di service:

- tenant pada approval dan target harus sama;
- status hanya dapat diputus dari `pending`;
- maker tidak dapat menjadi checker;
- alasan keputusan wajib;
- delegasi hanya berlaku untuk tenant, peran, cabang, dan rentang waktu yang dicatat;
- delegator harus benar-benar memegang peran yang didelegasikan;
- delegator dan penerima delegasi harus berbeda;
- keputusan melalui delegasi menyimpan `decided_under_delegation_id`;
- approval jatuh tempo dapat dieskalasi bertingkat ke `branch_manager` lalu `ops_admin`;
- keputusan final memutakhirkan target bisnis dalam transaksi database yang sama;
- appraisal berstatus `pending_approval` sampai checker menyetujui, dan penawaran hanya memakai appraisal `final`.

## Integrasi bertahap

| Command | Target checker | Kondisi |
| --- | --- | --- |
| Finalisasi appraisal | Branch manager/reviewer | Tersedia |
| Persetujuan stock opname | Branch manager | Tersedia melalui approval inbox |
| Otorisasi pelepasan agunan | Branch manager | Tersedia otomatis setelah pelunasan terverifikasi |
| Reversal jurnal | Finance | Tersedia melalui approval inbox |
| Sign-off laporan regulator | Auditor | Tersedia melalui approval inbox |

Checker anggota biasa harus mempunyai `staff_assignment` aktif dengan peran yang dituju. Owner dan admin tenant dapat melakukan keputusan, tetapi tetap terkena larangan maker menjadi checker. Approval organisasi seperti laporan regulator tidak dipaksa memakai cabang semu.

## Delegasi dan eskalasi

- `POST /v1/approvals/delegations` membuat mandat berjangka dengan alasan.
- `POST /v1/approvals/delegations/{id}/revoke` menghentikan mandat tanpa menghapus histori.
- `POST /v1/approvals/escalations/run` memproses item jatuh tempo memakai row lock dan batas batch.
- Eskalasi level 1 mengubah prioritas menjadi `high`, merutekan ke `branch_manager`, dan memberi SLA baru empat jam.
- Eskalasi level 2 mengubah prioritas menjadi `critical`, merutekan ke `ops_admin`, dan memberi SLA baru dua jam.
- Setiap eskalasi menambah `ApprovalEscalated` pada event ledger.

Endpoint sweep dapat dipanggil scheduler terkelola. UI juga menyediakan tindakan manual untuk petugas ops/auditor saat menangani insiden atau backlog.

## Acceptance evidence

- API `GET /v1/approvals` hanya membaca ledger tenant aktif.
- API `POST /v1/approvals/{id}/decision` menjalankan keputusan atomik.
- UI approval menampilkan status, SLA, maker, peran checker, versi, snapshot nilai, serta alasan.
- UI menampilkan histori event, level eskalasi, register delegasi, pembuatan, dan pencabutan delegasi.
- Pengujian integrasi membuktikan appraisal tidak dapat dipakai sebelum final dan maker ditolak saat mencoba menyetujui permintaannya sendiri.
- Pengujian kontrol membuktikan keputusan delegasi menyimpan referensi mandat dan sweep hanya menaikkan approval jatuh tempo.
