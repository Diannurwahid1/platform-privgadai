"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, ClipboardCheck, ShieldCheck } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listApplications, type ApplicationQueueItem } from "@/lib/operations";

export default function ApprovalsPage() {
  const { slug } = useParams<{ slug: string }>();
  const [items, setItems] = useState<ApplicationQueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { listApplications(100).then((rows) => setItems(rows.filter((item) => ["appraisal", "offered", "accepted"].includes(item.status)))).catch((reason: { detail?: string }) => setError(reason.detail ?? "Approval inbox gagal dimuat")); }, []);
  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat approval inbox" />;
  return <div className="space-y-5"><header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Compliance · Four eyes</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Approval inbox</h1><p className="mt-2 text-sm text-muted-foreground">Review nilai, kebijakan, bukti, dan konflik kewenangan sebelum keputusan dijalankan.</p></header><div className="flex gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900"><ShieldCheck className="h-5 w-5 shrink-0" /><p><strong>Separation of duty aktif.</strong> Maker dan checker harus berbeda untuk keputusan yang diwajibkan oleh matriks kewenangan.</p></div><section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border px-5 py-4"><h2 className="font-bold">Menunggu keputusan</h2><p className="mt-1 text-xs text-muted-foreground">Buka record untuk melihat appraisal, offer, dokumen, dan histori sebelum memberi keputusan.</p></div><div className="divide-y divide-border">{items.map((item) => <Link key={item.id} href={`/orgs/${slug}/loans/applications/${item.id}`} className="grid gap-3 px-5 py-4 hover:bg-surface-soft/70 md:grid-cols-[1fr_160px_160px_42px] md:items-center"><div><p className="font-mono text-xs font-semibold text-primary">{item.application_no}</p><p className="mt-1 text-sm font-semibold">{item.borrower_name}</p><p className="mt-1 text-xs text-muted-foreground">{item.asset_label} · {item.branch_code}</p></div><span className="inline-flex items-center gap-2 text-xs"><ClipboardCheck className="h-4 w-4 text-primary" />{item.status === "appraisal" ? "Review penaksiran" : item.status === "offered" ? "Review penawaran" : "Siap perjanjian"}</span><span className="rounded-lg bg-amber-50 px-2.5 py-1 text-center text-xs font-semibold text-amber-800">Menunggu checker</span><ArrowRight className="h-4 w-4 text-muted-foreground" /></Link>)}{!items.length && <div className="flex flex-col items-center px-6 py-14 text-center"><CheckCircle2 className="h-8 w-8 text-emerald-600" /><p className="mt-3 text-sm font-semibold">Tidak ada approval tertunda</p></div>}</div></section></div>;
}
