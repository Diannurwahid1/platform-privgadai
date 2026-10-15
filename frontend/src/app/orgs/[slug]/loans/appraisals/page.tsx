"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Clock3, Scale, Search, ShieldCheck } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listApplications, type ApplicationQueueItem } from "@/lib/operations";

const idr = (value: number | null) => value == null ? "Belum dinilai" : new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(value);

export default function AppraisalsPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [items, setItems] = useState<ApplicationQueueItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState("all");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { listApplications(100).then(setItems).catch((reason: { detail?: string }) => setError(reason.detail ?? "Antrean penaksiran gagal dimuat")); }, []);
  const queue = useMemo(() => (items ?? []).filter((item) => ["submitted", "under_review", "appraisal"].includes(item.status) && (stage === "all" || item.status === stage) && [item.application_no, item.borrower_name, item.asset_label].join(" ").toLowerCase().includes(query.toLowerCase())), [items, query, stage]);
  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat antrean penaksiran" />;
  const awaiting = queue.filter((item) => item.status !== "appraisal").length;
  return <div className="space-y-5">
    <header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Loan operations · Appraisal</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Antrean penaksiran</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Pemeriksaan barang jaminan, pembanding harga, nilai likuidasi, rekomendasi pinjaman, dan keputusan penaksir manusia.</p></header>
    <section className="grid gap-3 sm:grid-cols-3"><Summary label="Dalam antrean" value={queue.length} icon={Scale} /><Summary label="Menunggu pemeriksaan" value={awaiting} icon={Clock3} /><Summary label="Siap keputusan" value={queue.length - awaiting} icon={ShieldCheck} /></section>
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
      <div className="flex items-center gap-3 border-b border-border p-4"><div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari nomor, debitur, atau barang…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-3 text-sm" /></div><select value={stage} onChange={(event) => setStage(event.target.value)} className="h-10 rounded-xl border border-border bg-surface px-3 text-xs font-semibold"><option value="all">Semua tahap</option><option value="submitted">Diajukan</option><option value="under_review">Dalam review</option><option value="appraisal">Penaksiran</option></select></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[920px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Pengajuan</th><th className="px-5 py-3">Barang</th><th className="px-5 py-3">Cabang</th><th className="px-5 py-3 text-right">Diminta</th><th className="px-5 py-3 text-right">Indikatif</th><th className="px-5 py-3">Tahap</th><th className="px-5 py-3"></th></tr></thead><tbody className="divide-y divide-border">{queue.map((item) => <tr key={item.id} className="hover:bg-surface-soft/70"><td className="px-5 py-4"><p className="font-mono text-xs font-semibold text-primary">{item.application_no}</p><p className="mt-1 font-semibold">{item.borrower_name}</p></td><td className="px-5 py-4"><p className="font-medium">{item.asset_label}</p><p className="mt-1 text-xs capitalize text-muted-foreground">{item.asset_category}</p></td><td className="px-5 py-4 font-semibold">{item.branch_code}</td><td className="px-5 py-4 text-right font-semibold">{idr(item.requested_amount)}</td><td className="px-5 py-4 text-right font-semibold">{idr(item.indicative_value)}</td><td className="px-5 py-4"><span className="rounded-lg bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">{item.status === "appraisal" ? "Penaksiran" : "Perlu verifikasi"}</span></td><td className="px-5 py-4"><Link href={`/orgs/${slug}/loans/applications/${item.id}`} className="grid h-9 w-9 place-items-center rounded-lg border border-border text-muted-foreground hover:border-primary/30 hover:text-primary"><ArrowRight className="h-4 w-4" /></Link></td></tr>)}</tbody></table>{!queue.length && <div className="px-6 py-14 text-center text-sm text-muted-foreground">Tidak ada pengajuan dalam antrean penaksiran.</div>}</div>
    </section>
  </div>;
}

function Summary({ label, value, icon: Icon }: { label: string; value: number; icon: typeof Scale }) { return <article className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-4"><span className="grid h-10 w-10 place-items-center rounded-xl bg-surface-blue text-primary"><Icon className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-xl font-bold">{value}</p></div></article>; }
