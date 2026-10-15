import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen px-6 py-8">
      <div className="mx-auto flex max-w-6xl items-center justify-between">
        <span className="text-xl font-semibold tracking-tight">PrivGadai</span>
        <Link
          href="/login"
          className="rounded-full border border-border px-5 py-2 text-sm font-medium hover:bg-muted"
        >
          Masuk
        </Link>
      </div>

      <section className="mx-auto grid min-h-[80vh] max-w-6xl items-center gap-12 py-16 lg:grid-cols-2">
        <div className="space-y-7">
          <span className="inline-flex rounded-full bg-muted px-4 py-2 text-sm font-medium text-primary">
            Prototipe B2B untuk lembaga pergadaian
          </span>
          <h1 className="text-5xl font-semibold leading-tight tracking-tight sm:text-6xl">
            Satu ruang kerja untuk menelusuri siklus barang jaminan.
          </h1>
          <p className="max-w-xl text-lg leading-8 text-muted-foreground">
            PrivGadai sedang dibangun untuk membantu lembaga berizin mencatat
            pengajuan, penaksiran manusia, perpindahan barang, dan bukti proses
            yang dapat diaudit.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/login"
              className="rounded-full bg-primary px-6 py-3 font-medium text-primary-foreground hover:opacity-90"
            >
              Masuk ke ruang kerja
            </Link>
            <Link
              href="/register"
              className="rounded-full border border-border px-6 py-3 font-medium hover:bg-muted"
            >
              Buat akun uji
            </Link>
          </div>
          <p className="text-sm text-muted-foreground">
            Fitur transaksi gadai masih dalam pengembangan. Gunakan data
            sintetis untuk pengujian.
          </p>
        </div>

        <div className="rounded-3xl border border-border bg-muted/40 p-8">
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">
            Alur produk yang dituju
          </p>
          <ol className="mt-8 space-y-5">
            {[
              "Pengajuan aset dan foto",
              "Pemeriksaan dan keputusan penaksir",
              "Penawaran dari lembaga mitra",
              "Serah terima dan Collateral Passport",
              "Jejak audit dan verifikasi bukti",
            ].map((step, index) => (
              <li key={step} className="flex items-start gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                  {index + 1}
                </span>
                <span className="pt-1 font-medium">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </main>
  );
}
