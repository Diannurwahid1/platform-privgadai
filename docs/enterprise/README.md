# Rancangan Enterprise PrivGadai

Dokumen ini menjadi baseline perombakan PrivGadai setelah audit terhadap:

- `PrivGadai_Technical_Architecture_Blueprint_V3_Lengkap.pdf`;
- `Blueprint_Bisnis_PrivGadai_Lengkap_2026.pdf`;
- implementasi frontend, backend, model data, dan tangkapan layar aplikasi per 16 Oktober 2026;
- regulasi serta format pelaporan resmi OJK yang relevan.

## Status produk saat ini

PrivGadai saat ini adalah **MVP internal/pilot**. Fondasi tenant, cabang, alur pengajuan, penaksiran, agunan, kas, jurnal, collection, dan laporan sudah tersedia sebagian. Produk belum dapat dinyatakan siap operasi produksi sebelum kontrol, SOP, skema pelaporan, keamanan, pemulihan bencana, migrasi data, dan UAT disahkan oleh pemilik proses dan fungsi kepatuhan.

## Urutan dokumen

1. [Audit kondisi saat ini](./01-current-state-ux-audit.md)
2. [Arsitektur informasi dan sistem desain](./02-information-architecture-and-design-system.md)
3. [Modul operasional dan SOP](./03-operational-modules-and-sop.md)
4. [Pelaporan OJK dan SLIK](./04-ojk-slik-regulatory-reporting.md)
5. [Audit event, keamanan, dan kontrol](./05-domain-audit-security-and-controls.md)
6. [Roadmap implementasi dan acceptance criteria](./06-delivery-roadmap-and-acceptance.md)
7. [KYC, CDD, dan identitas nasabah](./07-kyc-cdd-implementation.md)

## Prinsip keputusan

- Satu menu leaf memiliki satu route dan satu tanggung jawab.
- Semua data operasional selalu memiliki konteks `tenant_id`; data cabang dibatasi oleh `branch_id` dan otorisasi pengguna.
- Aksi penting memakai maker-checker, alasan, bukti, dan event bisnis yang tidak dapat diubah.
- Kode referensi dan format regulator diberi versi serta tanggal efektif; format tidak ditanam permanen di UI.
- Informasi utama disajikan sebagai work queue, tabel, detail record, timeline, dan tindakan terkontrol. Kartu dekoratif hanya dipakai jika benar-benar membantu keputusan.
- Istilah UI memakai bahasa operasional pergadaian Indonesia dan konsisten di seluruh modul.

## Definition of Ready untuk implementasi

- [ ] Pemilik proses menyetujui alur dan RACI tiap modul.
- [ ] Tim kepatuhan mengesahkan interpretasi regulasi dan format laporan.
- [ ] Kamus data, status, reason code, dan matriks approval disetujui.
- [ ] Prototype route, shell, tabel, detail record, serta keadaan error/empty/loading direview.
- [ ] Risiko migrasi dan kompatibilitas endpoint dicatat.
