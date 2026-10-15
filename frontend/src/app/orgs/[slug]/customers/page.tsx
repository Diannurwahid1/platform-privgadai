"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, ShieldCheck, UserRound } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listCustomers } from "@/lib/operations";

export default function CustomersPage() {
  const [items, setItems] = useState<Array<Record<string, unknown>> | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCustomers()
      .then(setItems)
      .catch((reason: { detail?: string }) => setError(reason.detail ?? "Debitur gagal dimuat"));
  }, []);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLocaleLowerCase("id-ID");
    if (!items || !keyword) return items ?? [];
    return items.filter((item) =>
      [item.full_name, item.customer_reference, item.phone_masked, item.dati_ii_code]
        .map((value) => String(value ?? "").toLocaleLowerCase("id-ID"))
        .some((value) => value.includes(keyword)),
    );
  }, [items, query]);

  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat Debitur & CRM" />;

  return (
    <div className="space-y-6">
      <header>
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Customers</p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Debitur & CRM</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Profil tenant, kode wilayah/SLIK, consent, risk note, dan mekanisme koreksi watchlist.
        </p>
      </header>

      <div className="relative">
        <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Cari nama, referensi, telepon, atau DATI II..."
          className="h-12 w-full rounded-xl border border-border bg-surface pl-11 pr-4 text-sm"
        />
      </div>

      <section className="grid gap-4 xl:grid-cols-2">
        {filtered.map((item) => (
          <article key={String(item.id)} className="flex gap-4 rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-surface-blue text-primary">
              <UserRound className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="font-bold">{String(item.full_name)}</h2>
                  <p className="mt-1 font-mono text-[11px] text-primary">{String(item.customer_reference)}</p>
                </div>
                <span className="rounded-full bg-success/10 px-2.5 py-1 text-[10px] font-bold text-success">
                  {String(item.risk_status)}
                </span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <p>{String(item.phone_masked)}</p>
                <p>DATI II: {String(item.dati_ii_code ?? "belum diisi")}</p>
                <p>SLIK: {String(item.slik_subject_code ?? "belum dipetakan")}</p>
                <p className="flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5" /> Koreksi: {String(item.correction_status)}</p>
              </div>
            </div>
          </article>
        ))}
      </section>

      {!filtered.length && <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">Debitur tidak ditemukan.</p>}
    </div>
  );
}
