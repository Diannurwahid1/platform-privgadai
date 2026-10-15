# 02 — Arsitektur Informasi dan Sistem Desain

## Tujuan

Membentuk UI operasional padat data yang cepat dipahami, konsisten, dapat diaudit, dan tetap nyaman di laptop kantor. Desain memakai identitas PrivGadai, permukaan netral, warna biru sebagai aksen tindakan, dan warna status hanya saat menyampaikan arti.

## Peta route target

Setiap leaf harus memiliki route unik.

```text
/orgs/[slug]
├── /overview
├── /customers
│   ├── /[customerId]
│   ├── /duplicates
│   └── /consents
├── /loans
│   ├── /applications
│   │   └── /[applicationId]
│   ├── /appraisals
│   │   └── /[appraisalId]
│   ├── /agreements
│   └── /accounts/[loanId]
├── /collateral
│   ├── /passports
│   │   └── /[collateralId]
│   ├── /pickups
│   ├── /custody
│   └── /inventory
├── /finance
│   ├── /teller
│   ├── /cash
│   ├── /collections
│   ├── /general-ledger
│   └── /reconciliation
├── /reports
│   ├── /financial
│   ├── /operational
│   ├── /regulatory/ojk
│   ├── /regulatory/slik
│   └── /health
├── /compliance
│   ├── /exceptions
│   ├── /approvals
│   ├── /audit
│   └── /complaints
└── /management
    ├── /master-data
    ├── /team-access
    └── /settings
        ├── /institution
        ├── /products-rates
        ├── /workflow-sla
        ├── /accounting
        ├── /regulatory
        ├── /integrations
        ├── /notifications
        └── /security-retention
```

Route lama diberi redirect terukur selama masa migrasi. Route default `/orgs/[slug]` diarahkan ke `/overview`.

## Aturan menu aktif

Konfigurasi navigasi memiliki `id`, `href`, `permission`, dan `match`.

- `match: exact` hanya aktif bila pathname sama persis.
- `match: section` aktif untuk route detail di bawah leaf tersebut.
- Hanya satu leaf boleh terpilih pada satu waktu.
- Parent group boleh tampil expanded, tetapi tidak diberi gaya selected seperti leaf.
- Badge menampilkan jumlah pekerjaan dari endpoint summary, bukan angka statis.
- Item tanpa izin tidak dirender; deep link tetap divalidasi server.

Acceptance test: untuk seluruh route dalam matriks, jumlah elemen `[aria-current="page"]` harus tepat satu.

## Sidebar enterprise

### Expanded

- Lebar 280 px; logo penuh, tenant switcher, group label, icon, label, badge.
- Group dapat dibuka/tutup; grup route aktif otomatis terbuka.
- Satu scrollbar tipis di area menu dengan `scrollbar-gutter: stable`.
- Footer tetap berisi avatar, nama, peran, cabang aktif, akses profil, dan keluar.
- Tombol collapse selalu terlihat, punya tooltip dan `aria-label`.

### Collapsed

- Lebar 72 px; hanya icon, active indicator, dan badge ringkas.
- Tooltip menampilkan nama menu serta shortcut.
- Tenant switcher menjadi icon; saat diklik membuka popover.
- State disimpan per pengguna di local storage dan dapat dipulihkan tanpa layout shift.

### Mobile

- Sidebar menjadi drawer overlay, bukan deretan semua menu horizontal.
- Header berisi hamburger, nama modul aktif, pencarian, dan profil.
- Drawer menutup setelah navigasi dan menjaga focus trap.

### Scroll dan layout

- `html/body` menangani scroll halaman; sidebar memiliki satu scroll internal hanya untuk daftar menu.
- Tidak ada scrollbar di container berlapis.
- Main area memakai `min-width: 0`; tabel memakai overflow container yang jelas dan sticky header/kolom bila diperlukan.
- Breakpoint diuji pada 1280×720, 1366×768, 1440×900, 1920×1080, tablet, dan mobile.

## Anatomi halaman

Setiap halaman menggunakan urutan tetap:

1. Breadcrumb dan konteks tenant/cabang.
2. Page header: judul, deskripsi singkat, status data, primary action.
3. Context bar: cabang, periode, saved view, filter aktif.
4. Summary strip yang ringkas bila diperlukan.
5. Work area: tabel, board, form, atau detail record.
6. Action bar/drawer untuk tindakan terpilih.
7. Metadata: waktu pemutakhiran, sumber, dan scope.

## Pola daftar dan work queue

- Server-side pagination, sort, filter, dan search.
- Saved view per user/role.
- Column chooser, density selector, sticky header, dan column pinning.
- Checkbox dan bulk action hanya untuk tindakan yang aman dilakukan massal.
- Row membuka detail lewat link dan keyboard; overflow menu memuat aksi sekunder.
- Status, SLA, assignee, branch, dan last event terlihat tanpa membuka detail.
- Export mengikuti permission, masking, filter aktif, serta tercatat sebagai event.
- Empty state menjelaskan filter/izin/data, lalu memberi tindakan relevan.

## Pola detail record

Record header memuat nomor, nama/status, cabang, owner, SLA, dan tindakan utama. Tab standar:

- Ringkasan;
- Data dan relasi;
- Dokumen/bukti;
- Aktivitas bisnis;
- Approval;
- Audit.

Panel kanan dapat menampilkan checklist, exception, dan tindakan. Perubahan status tidak dilakukan hanya dengan dropdown; pengguna menjalankan command yang memiliki guard, alasan, bukti, dan konfirmasi dampak.

## Bahasa visual

- Typography: skala 12/14/16/20/28/36 dengan line-height rapat untuk data dan lebih longgar untuk penjelasan.
- Grid: 12 kolom; content max-width dipakai untuk form, bukan untuk tabel lebar.
- Spacing: basis 4 px; kontrol standar 36–40 px; kepadatan dapat dipilih.
- Radius: 8–12 px untuk kontrol dan panel; hindari semua elemen berbentuk pill.
- Shadow: hanya untuk overlay, sticky state, dan elevation yang nyata.
- Warna status: hijau selesai, kuning perhatian, merah gagal/risiko, biru aktif/informasi, abu netral.
- Angka uang rata kanan, font tabular, format `Rp 12.500.000`.
- Tanggal menyertakan zona waktu saat relevan; ID teknis memakai monospace.
- Animasi maksimal 150–200 ms dan tunduk pada `prefers-reduced-motion`.

## Aksesibilitas

- WCAG 2.2 AA untuk contrast, focus, keyboard, target size, dan label.
- Tidak mengandalkan warna untuk membedakan status.
- Semua dialog focus-trapped dan dapat ditutup dengan Escape bila aman.
- Tabel memiliki caption/heading dan navigasi keyboard.
- Error form muncul di field dan summary; fokus pindah ke error pertama.

## Task breakdown

- [ ] SHELL-001: buat konfigurasi route/menu tunggal dan typed.
- [ ] SHELL-002: migrasikan route unik beserta redirect route lama.
- [ ] SHELL-003: implementasi sidebar 280/72 px dan persistensi state.
- [ ] SHELL-004: implementasi drawer mobile dan focus management.
- [ ] SHELL-005: perbaiki scroll, overflow, sticky header, dan responsive table.
- [ ] SHELL-006: buat command palette serta pencarian global yang benar-benar bekerja.
- [ ] SHELL-007: buat notification center berbasis event dan status terbaca.
- [ ] DS-001: tetapkan token warna, spacing, typography, radius, elevation, dan density.
- [ ] DS-002: buat komponen PageHeader, ContextBar, DataTable, RecordHeader, Timeline, ApprovalPanel, EvidenceList, EmptyState, dan ErrorSummary.
- [ ] DS-003: konsolidasikan istilah Indonesia dan microcopy.
- [ ] DS-004: buat Storybook/catalog state untuk seluruh komponen kritis.
- [ ] QA-001: uji tepat satu menu aktif untuk seluruh route.
- [ ] QA-002: uji visual seluruh breakpoint dan browser yang didukung.

## Acceptance criteria shell

- [ ] Collapse/expand tidak memotong logo, label, badge, atau footer.
- [ ] Preferensi sidebar bertahan setelah reload dan login ulang pada perangkat yang sama.
- [ ] Satu dan hanya satu leaf menu aktif di setiap halaman.
- [ ] Tidak ada horizontal overflow pada app shell.
- [ ] Sidebar dapat dipakai penuh dengan keyboard dan screen reader.
- [ ] Pergantian tenant/cabang mengubah konteks data, permission, dan cache secara atomik.
- [ ] Tidak ada tombol, badge, filter, atau indikator notifikasi palsu.
