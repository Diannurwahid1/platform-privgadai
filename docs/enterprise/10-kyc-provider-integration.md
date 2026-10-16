# 10 — Integrasi OCR KTP dan Identity Provider

## Tujuan

PrivGadai memakai adapter provider agar proses KYC tidak tergantung pada satu vendor. OCR, identity verification, dan keputusan checker dipisahkan karena ketiganya menghasilkan bukti yang berbeda.

| Proses | Arti | Dapat memberi status resmi |
|---|---|---|
| OCR KTP | Mengekstrak teks dari gambar KTP dan membandingkannya dengan data yang diketik | Tidak |
| IDV sandbox | Menguji kontrak request/response dengan data simulasi provider | Tidak |
| IDV live | Memeriksa atribut identitas melalui provider produksi yang dikontrak | Hanya jika respons live menyatakan match |
| Keputusan checker | Keputusan internal KYC/CDD oleh petugas berbeda | Status internal PrivGadai |

UI menggunakan label `Sandbox simulation`, `Live verified`, atau status ekstraksi. Hasil sandbox tidak pernah ditampilkan sebagai `Dukcapil Verified`.

## Endpoint PrivGadai

- `GET /v1/kyc/provider-capabilities` menampilkan adapter yang aktif tanpa membocorkan kredensial.
- `POST /v1/customers/{customer_id}/kyc/{verification_id}/provider/ocr` membaca KTP bersih dari penyimpanan terenkripsi dan menjalankan OCR.
- `POST /v1/customers/{customer_id}/kyc/{verification_id}/provider/identity-verification` mengirim NIK, nama, tanggal lahir, dan reference ID ke adapter IDV.

Setiap hasil disimpan sebagai `kyc_provider_checks`. Payload hasil dienkripsi, request hanya menyimpan fingerprint, dan event bisnis ditambahkan ke histori KYC.

## Konfigurasi

```env
KYC_OCR_PROVIDER=disabled
KYC_OCR_BASE_URL=http://localhost:8001
KYC_OCR_API_KEY=

KYC_IDV_MODE=disabled
KYC_IDV_URL=https://api.verihubs.com/v1/data-verification/id-verification/sandbox
VERIHUBS_APP_ID=
VERIHUBS_API_KEY=
KYC_PROVIDER_TIMEOUT_SECONDS=30
KYC_REQUIRE_LIVE_IDV_FOR_ELECTRONIC=false
```

Pilihan OCR:

- `local_http`: service internal dengan kontrak `POST /scan/ktp`, multipart field `file`, dan optional `X-API-Key`.
- `verihubs`: Verihubs Extract KTP Sync. PrivGadai mengirim gambar base64, quality validation, dan rotation validation.
- `disabled`: tombol OCR tidak ditampilkan.

Pilihan IDV:

- `verihubs_sandbox`: simulasi kontrak provider; dilarang pada `APP_ENV=production`.
- `verihubs_live`: endpoint live eksplisit, kredensial production, dan hasil match dapat memperoleh flag resmi.
- `disabled`: proses KYC manual branch tetap tersedia.

## Kontrol keamanan

1. Dokumen harus berstatus malware scan `clean` sebelum dikirim ke provider.
2. Dokumen didekripsi hanya di memori saat request provider berlangsung.
3. API key dan App ID hanya berasal dari environment server.
4. Respons provider yang disimpan dienkripsi dengan kunci PII.
5. NIK dalam response UI selalu dimasking.
6. OCR tidak mengubah data CIF atau KYC secara otomatis.
7. Maker-checker tetap berlaku setelah provider check.
8. Mode sandbox ditolak oleh startup guard production.

## Catatan referensi open source

Repository [wildanisme/ocr](https://github.com/wildanisme/ocr) diaudit pada commit `3a3d2d6a5c86a7168a38134f39710aeb3bff8fb4`. Repository tidak mempunyai file lisensi pada root saat audit. Karena itu PrivGadai tidak menyalin source code tersebut. Adapter `local_http` hanya memakai kontrak HTTP generik dan dapat diarahkan ke service internal yang memiliki lisensi dan hasil security review yang jelas.

## Gate aktivasi produksi

- kontrak dan dasar pemrosesan data dengan provider disetujui;
- endpoint live, kredensial, allowlist, timeout, dan retry policy disiapkan;
- data minimization serta retention provider disetujui;
- hasil uji sandbox dan live terdokumentasi;
- callback/reconciliation bila provider memakai proses asynchronous;
- fungsi kepatuhan menyetujui label serta arti keputusan yang ditampilkan.
