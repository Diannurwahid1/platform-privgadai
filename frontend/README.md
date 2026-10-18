# Frontend PrivGadai

Next.js 16 untuk workspace petugas dan portal borrower. Route `/` mengarah ke `/login`; nasabah memakai `/borrower`. API diproksi melalui `/api/backend/*` agar cookie dan unggahan KTP tetap berada pada origin frontend.

## Lokal

Jalankan backend terlebih dahulu sesuai [README utama](../README.md). Kemudian:

```powershell
Copy-Item .env.example .env.local
bun install --frozen-lockfile
bun run dev
```

Frontend tersedia di `http://localhost:3000`. Untuk server, set `INTERNAL_API_BASE_URL` pada environment proses frontend ke alamat backend privat. `NEXT_PUBLIC_API_BASE_URL` adalah URL yang dapat terlihat oleh browser; jangan taruh kunci API di variabel `NEXT_PUBLIC_*`.

## Pemeriksaan dan build

```powershell
bun run typecheck
bun run lint
bun run test
bun run build
```

Gunakan `bun run start` hanya setelah build berhasil. Alur deploy dan gerbang kesiapan produksi ada di [README utama](../README.md) dan [runbook](../docs/enterprise/09-production-readiness.md).
