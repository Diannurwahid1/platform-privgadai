# PrivGadai KTP OCR

Layanan internal berbasis PaddleOCR untuk mengekstrak data foto KTP. Tidak memanggil Verihubs atau Dukcapil.

```powershell
cd ocr_service
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001
```

Endpoint:

- `GET /healthz`
- `POST /scan/ktp` dengan multipart field `file`

Jika `OCR_API_KEY` diisi, client wajib mengirim header `X-API-Key`.

