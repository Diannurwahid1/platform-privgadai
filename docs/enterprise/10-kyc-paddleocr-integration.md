# KYC internal dengan PaddleOCR

## Keputusan arsitektur

PrivGadai menggunakan layanan PaddleOCR lokal untuk membaca foto KTP. Integrasi Verihubs dan endpoint identity verification tidak digunakan. Layanan OCR tidak mengirim foto atau NIK ke provider eksternal.

## Alur operasional

1. Maker merekam data KYC dan mengunggah foto depan KTP.
2. Backend mengenkripsi file KTP dan menyimpan checksum SHA-256.
3. Petugas menjalankan `POST /v1/customers/{customer_id}/kyc/{verification_id}/provider/ocr`.
4. Backend mendekripsi KTP hanya di memori dan mengirimnya ke service internal `POST /scan/ktp`.
5. PaddleOCR mengekstrak field terstruktur.
6. Backend membandingkan NIK, nama, dan tanggal lahir dengan data KYC.
7. Bila ketiganya cocok, evidence OCR berstatus `matched` dan diberi label **Internal verified**.
8. Checker yang berbeda dari maker memberi keputusan akhir KYC.

OCR tidak diberi label Dukcapil verified dan tidak membuktikan keaslian identitas pada sumber pemerintah. Dalam proses PrivGadai, hasil cocok menjadi bukti verifikasi dokumen internal.

## Konfigurasi

```env
KYC_OCR_PROVIDER=paddle_http
KYC_OCR_BASE_URL=http://localhost:8001
KYC_OCR_API_KEY=
KYC_OCR_TIMEOUT_SECONDS=60
```

Layanan lokal berada di `ocr_service/` dan dijalankan tanpa Docker:

```powershell
cd ocr_service
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001
```

## Kontrol

- Foto maksimal 10 MB dan hanya JPG, PNG, atau WebP.
- Raw OCR line tidak disimpan oleh backend utama.
- Payload terstruktur disimpan terenkripsi dan NIK dimasking saat dibaca UI.
- Ketidakcocokan atau field yang tidak terbaca menghasilkan `needs_review`.
- Status KYC akhir tetap membutuhkan maker-checker.
- Seluruh eksekusi OCR dan keputusan masuk event history.
