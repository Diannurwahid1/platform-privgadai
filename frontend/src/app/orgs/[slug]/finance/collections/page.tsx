"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarClock, HandCoins, Search, ShieldAlert } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listCollections } from "@/lib/operations";

const idr = (value: unknown) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));
const date = (value: unknown) => value ? new Intl.DateTimeFormat("id-ID", { dateStyle: "medium" }).format(new Date(String(value))) : "Belum dijadwalkan";

export default function CollectionsPage() {
  const [items, setItems] = useState<Array<Record<string, unknown>> | null>(null);
  const [query, setQuery] = useState("");
  const [bucket, setBucket] = useState("all");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { listCollections().then(setItems).catch((reason: { detail?: string }) => setError(reason.detail ?? "Collection queue gagal dimuat")); }, []);
  const filtered = useMemo(() => (items ?? []).filter((item) => (bucket === "all" || String(item.aging_bucket) === bucket) && [item.application_no, item.account_no, item.borrower_name].join(" ").toLowerCase().includes(query.toLowerCase())), [items, query, bucket]);
  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat collection queue" />;
  const outstanding = filtered.reduce((sum, item) => sum + Number(item.outstanding_amount ?? 0), 0);
  return <div className="space-y-5">
    <header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Finance · Collections</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Collection work queue</h1><p className="mt-2 text-sm text-muted-foreground">Prioritaskan rekening berdasarkan aging, exposure, status, dan jadwal tindakan berikutnya.</p></header>
    <section className="grid gap-3 sm:grid-cols-3"><Summary label="Kasus terpantau" value={String(filtered.length)} icon={HandCoins} /><Summary label="Outstanding" value={idr(outstanding)} icon={ShieldAlert} /><Summary label="Tindakan terjadwal" value={String(filtered.filter((item) => item.next_action_at).length)} icon={CalendarClock} /></section>
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="flex flex-col gap-3 border-b border-border p-4 md:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari rekening atau pengajuan…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-3 text-sm" /></div><select value={bucket} onChange={(event) => setBucket(event.target.value)} className="h-10 rounded-xl border border-border bg-surface px-3 text-xs font-semibold"><option value="all">Semua bucket</option><option value="current">Current</option><option value="1_30">1–30 hari</option><option value="31_60">31–60 hari</option><option value="61_90">61–90 hari</option><option value="90_plus">90+ hari</option></select></div><div className="overflow-x-auto"><table className="w-full min-w-[920px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Rekening</th><th className="px-5 py-3">Aging</th><th className="px-5 py-3">Status</th><th className="px-5 py-3 text-right">Outstanding</th><th className="px-5 py-3">Jatuh tempo</th><th className="px-5 py-3">Tindakan berikutnya</th></tr></thead><tbody className="divide-y divide-border">{filtered.map((item) => <tr key={String(item.id)} className="hover:bg-surface-soft/70"><td className="px-5 py-4"><p className="font-mono text-xs font-semibold text-primary">{String(item.account_no ?? item.application_no)}</p><p className="mt-1 text-xs text-muted-foreground">{String(item.application_no ?? "—")}</p></td><td className="px-5 py-4"><span className="rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">{String(item.aging_bucket)}</span></td><td className="px-5 py-4 capitalize">{String(item.status)}</td><td className="px-5 py-4 text-right font-semibold">{idr(item.outstanding_amount)}</td><td className="px-5 py-4 text-muted-foreground">{date(item.due_at)}</td><td className="px-5 py-4 text-muted-foreground">{date(item.next_action_at)}</td></tr>)}</tbody></table>{!filtered.length && <div className="px-6 py-14 text-center text-sm text-muted-foreground">Tidak ada collection case pada filter ini.</div>}</div></section>
  </div>;
}

function Summary({ label, value, icon: Icon }: { label: string; value: string; icon: typeof HandCoins }) { return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className="h-4 w-4 text-primary" /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 truncate text-xl font-bold">{value}</p></article>; }
