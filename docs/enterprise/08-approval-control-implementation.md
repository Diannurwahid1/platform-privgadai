# Approval control implementation

Dokumen ini mencatat implementasi kontrol empat mata yang dipakai lintas proses PrivGadai. Sumber rancangan tetap `03-operational-modules-and-sop.md` dan `05-domain-audit-security-and-controls.md`.

## Model kontrol

Setiap command berisiko membuat `approval_request` dengan tenant, cabang bila relevan, agregat bisnis, versi, maker, peran checker, alasan, snapshot payload, prioritas, dan batas SLA. Keputusan menghasilkan `approval_event` append-only. Payload snapshot mempertahankan nilai yang benar-benar diperiksa sehingga perubahan record setelah permintaan tidak mengubah konteks persetujuan.

Aturan yang sudah ditegakkan di service:

- tenant pada approval dan target harus sama;
- status hanya dapat diputus dari `pending`;
- maker tidak dapat menjadi checker;
- alasan keputusan wajib;
- keputusan final memutakhirkan target bisnis dalam transaksi database yang sama;
- appraisal berstatus `pending_approval` sampai checker menyetujui, dan penawaran hanya memakai appraisal `final`.

## Integrasi bertahap

| Command | Target checker | Kondisi |
| --- | --- | --- |
| Finalisasi appraisal | Branch manager/reviewer | Tersedia |
| Persetujuan stock opname | Branch manager/auditor | Berikutnya |
| Otorisasi pelepasan agunan | Branch manager/custody supervisor | Berikutnya |
| Reversal jurnal | Finance supervisor | Berikutnya |
| Sign-off laporan regulator | Compliance/pejabat berwenang | Berikutnya |

## Acceptance evidence

- API `GET /v1/approvals` hanya membaca ledger tenant aktif.
- API `POST /v1/approvals/{id}/decision` menjalankan keputusan atomik.
- UI approval menampilkan status, SLA, maker, peran checker, versi, snapshot nilai, serta alasan.
- Pengujian integrasi membuktikan appraisal tidak dapat dipakai sebelum final dan maker ditolak saat mencoba menyetujui permintaannya sendiri.
