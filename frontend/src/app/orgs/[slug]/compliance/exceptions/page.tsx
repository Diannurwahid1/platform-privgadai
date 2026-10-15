"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Clock3, Search, ShieldAlert, TriangleAlert } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listApplications, type ApplicationQueueItem } from "@/lib/operations";

export default function ExceptionsPage() {
  const { slug } = useParams<{ slug: string }>();
  const [items, setItems] = useState<ApplicationQueueItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { listApplications(100).then(setItems).catch((reason: { detail?: string }) => setError(reason.detail ?? "Exception queue gagal dimuat")); }, []);
  const exceptions = useMemo(() => (items ?? []).filter((item) => item.priority === "high" || ["under_review", "submitted"].includes(item.status)).filter((item) => [item.application_no, item.borrower_name, item.asset_label].join(" ").toLowerCase().includes(query.toLowerCase())), [items, query]);
  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat exception queue" />;
  return <div className="space-y-5"><header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Compliance · Exceptions</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Exception queue</h1><p className="mt-2 text-sm text-muted-foreground">Pekerjaan yang membutuhkan verifikasi, bukti tambahan, keputusan supervisor, atau tindak lanjut SLA.</p></header><section className="grid gap-3 sm:grid-cols-3"><Summary label="Kasus terbuka" value={exceptions.length} icon={ShieldAlert} /><Summary label="Prioritas tinggi" value={exceptions.filter((item) => item.priority === "high").length} icon={TriangleAlert} /><Summary label="Perlu triase" value={exceptions.filter((item) => item.status === "submitted").length} icon={Clock3} /></section><section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border p-4"><div className="relative max-w-xl"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari exception…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-3 text-sm" /></div></div><div className="divide-y divide-border">{exceptions.map((item) => <Link key={item.id} href={`/orgs/${slug}/loans/applications/${item.id}`} className="grid gap-3 px-5 py-4 hover:bg-surface-soft/70 md:grid-cols-[1fr_170px_140px_42px] md:items-center"><div><p className="font-mono text-xs font-semibold text-primary">{item.application_no}</p><p className="mt-1 text-sm font-semibold">{item.borrower_name} · {item.asset_label}</p><p className="mt-1 text-xs text-muted-foreground">{item.priority === "high" ? "Prioritas tinggi membutuhkan keputusan supervisor" : "Dokumen atau verifikasi proses belum lengkap"}</p></div><span className="text-xs text-muted-foreground">{item.branch_code} · {item.asset_category}</span><span className={`rounded-lg px-2.5 py-1 text-center text-xs font-semibold ${item.priority === "high" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-800"}`}>{item.priority === "high" ? "Tinggi" : "Perlu review"}</span><ArrowRight className="h-4 w-4 text-muted-foreground" /></Link>)}{!exceptions.length && <div className="px-6 py-14 text-center text-sm text-muted-foreground">Tidak ada exception terbuka.</div>}</div></section></div>;
}
function Summary({ label, value, icon: Icon }: { label: string; value: number; icon: typeof ShieldAlert }) { return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className="h-4 w-4 text-primary" /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 text-xl font-bold">{value}</p></article>; }
