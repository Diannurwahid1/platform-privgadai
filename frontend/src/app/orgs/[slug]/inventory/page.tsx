"use client";

import { useCallback, useEffect, useState } from "react";
import { ClipboardCheck, ScanLine, Warehouse } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  createInventoryCheck,
  listCustodyLocations,
  listInventoryChecks,
  type MasterItem,
} from "@/lib/operations";

export default function InventoryPage() {
  const [data, setData] = useState<{ locations: MasterItem[]; checks: Array<Record<string, unknown>> } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [locations, checks] = await Promise.all([listCustodyLocations(), listInventoryChecks()]);
    setData({ locations, checks });
  }, []);

  useEffect(() => {
    load().catch((reason: { detail?: string }) => setError(reason.detail ?? "Stock opname gagal dimuat"));
  }, [load]);

  async function startCheck(locationId: string) {
    setBusy(locationId);
    setNotice(null);
    try {
      await createInventoryCheck(locationId);
      setNotice("Draft stock opname dibuat. Petugas dapat mencatat hasil scan dan mengirimnya ke checker.");
      await load();
    } catch (reason) {
      setError((reason as { detail?: string }).detail ?? "Stock opname gagal dimulai");
    } finally {
      setBusy(null);
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Memuat stock opname" />;

  return (
    <div className="space-y-6">
      <header>
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Collateral control</p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Vaults & Stock Opname</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Penghitungan fisik, pencatatan variance, dan approval oleh checker yang berbeda.
        </p>
      </header>

      {notice && <div className="rounded-xl border border-success/20 bg-success/8 p-3 text-sm text-success">{notice}</div>}

      <section className="grid gap-4 md:grid-cols-2">
        {data.locations.map((location) => (
          <article key={location.id} className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
            <Warehouse className="h-6 w-6 text-primary" />
            <h2 className="mt-4 font-bold">{location.name}</h2>
            <p className="mt-1 font-mono text-xs text-muted-foreground">{location.code}</p>
            <button
              onClick={() => startCheck(location.id)}
              disabled={busy !== null}
              className="mt-4 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-50"
            >
              {busy === location.id ? "Membuat…" : "Mulai stock opname"}
            </button>
          </article>
        ))}
      </section>

      <section className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
        <div className="flex items-center gap-2"><ScanLine className="h-5 w-5 text-primary" /><h2 className="font-bold">Riwayat opname</h2></div>
        <div className="mt-4 space-y-2">
          {data.checks.map((item) => (
            <div key={String(item.id)} className="flex items-center gap-3 rounded-xl bg-surface-soft px-4 py-3 text-xs">
              <ClipboardCheck className="h-4 w-4 text-primary" />
              <span className="flex-1">{String(item.counted_at)}</span>
              <span className="font-bold">{String(item.status)}</span>
            </div>
          ))}
          {!data.checks.length && <p className="text-xs text-muted-foreground">Belum ada stock opname.</p>}
        </div>
      </section>
    </div>
  );
}
