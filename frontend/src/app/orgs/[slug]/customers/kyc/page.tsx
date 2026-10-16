"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, Filter, IdCard, Search, UserPlus } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listKycVerifications, type KycQueueItem } from "@/lib/operations";

const statusLabel: Record<string, string> = { not_started: "Belum dimulai", pending_documents: "Menunggu dokumen", pending_review: "Menunggu checker", needs_information: "Perlu data", verified: "Terverifikasi", expired: "Kedaluwarsa", rejected: "Ditolak" };
const when = (value: string | null) => value ? new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";

export default function KycQueuePage() {
  const { slug } = useParams<{ slug: string }>();
  const [items, setItems] = useState<KycQueueItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { listKycVerifications().then(setItems).catch((e: { detail?: string }) => setError(e.detail ?? "Antrean KYC gagal dimuat")); }, []);
  const filtered = useMemo(() => (items ?? []).filter((item) => {
    const q = query.trim().toLowerCase();
    return (status === "all" || item.status === status) && (!q || `${item.customer_name} ${item.customer_reference} ${item.national_id_masked}`.toLowerCase().includes(q));
  }), [items, query, status]);
  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat antrean KYC" />;
  const pending = items.filter((item) => ["not_started", "pending_documents", "pending_review", "needs_information", "expired"].includes(item.status)).length;
  const verified = items.filter((item) => item.status === "verified").length;
  const high = items.filter((item) => ["high", "enhanced"].includes(item.risk_level)).length;

  return <div className="space-y-5">
    <header className="flex flex-col gap-4 border-b border-border pb-5 xl:flex-row xl:items-end xl:justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Customer due diligence</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">KYC & CDD</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Antrean seluruh nasabah, mulai perekaman KTP, PaddleOCR, pemeriksaan checker, risiko, dan masa berlaku verifikasi.</p></div><Link href={`/orgs/${slug}/customers`} className="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-surface px-4 text-xs font-bold"><UserPlus className="h-4 w-4" />Pilih dari Debitur & CRM</Link></header>
    <section className="grid gap-3 sm:grid-cols-3"><Metric icon={Clock3} label="Perlu tindakan" value={pending} tone="amber" /><Metric icon={CheckCircle2} label="Terverifikasi" value={verified} tone="green" /><Metric icon={AlertTriangle} label="High/EDD" value={high} tone="red" /></section>
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
      <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Cari nama, CIF, atau NIK termasking…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-4 text-sm outline-none focus:border-primary" /></div><div className="flex items-center gap-2 overflow-x-auto"><Filter className="h-4 w-4 shrink-0 text-muted-foreground" />{[["all", "Semua"], ["not_started", "Belum dimulai"], ["pending_review", "Menunggu checker"], ["needs_information", "Perlu data"], ["expired", "Kedaluwarsa"], ["verified", "Terverifikasi"], ["rejected", "Ditolak"]].map(([value, label]) => <button key={value} onClick={() => setStatus(value)} className={`shrink-0 rounded-lg border px-3 py-2 text-xs font-semibold ${status === value ? "border-primary bg-primary text-white" : "border-border"}`}>{label}</button>)}</div></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[1080px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">CIF / Nasabah</th><th className="px-5 py-3">Identitas</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Risiko</th><th className="px-5 py-3">Metode</th><th className="px-5 py-3">Dibuat</th><th className="px-5 py-3">Berlaku sampai</th><th className="px-5 py-3 text-right">Aksi</th></tr></thead><tbody className="divide-y divide-border">{filtered.map((item) => <tr key={item.id ?? item.customer_id} className="hover:bg-surface-soft"><td className="px-5 py-4"><Link href={`/orgs/${slug}/customers/${item.customer_id}?tab=identity`} className="font-semibold hover:text-primary">{item.customer_name}</Link><p className="mt-1 font-mono text-[11px] text-primary">{item.customer_reference}</p></td><td className="px-5 py-4 font-mono text-xs">{item.national_id_masked ?? "Belum direkam"}</td><td className="px-5 py-4"><Badge status={item.status} /></td><td className="px-5 py-4 capitalize">{item.risk_level === "unassessed" ? "Belum dinilai" : item.risk_level}</td><td className="px-5 py-4 text-xs capitalize text-muted-foreground">{item.verification_method?.replaceAll("_", " ") ?? "—"}</td><td className="px-5 py-4 text-xs text-muted-foreground">{when(item.created_at)}</td><td className="px-5 py-4 text-xs text-muted-foreground">{when(item.expires_at)}</td><td className="px-5 py-4 text-right"><Link href={`/orgs/${slug}/customers/${item.customer_id}?tab=identity`} className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-xs font-bold text-white">{actionLabel(item.status)}<ArrowRight className="h-3.5 w-3.5" /></Link></td></tr>)}</tbody></table>{!filtered.length && <div className="p-12 text-center text-sm text-muted-foreground">Tidak ada nasabah pada filter ini.</div>}</div>
    </section>
  </div>;
}

function Metric({ icon: Icon, label, value, tone }: { icon: typeof IdCard; label: string; value: number; tone: string }) { const colors: Record<string,string>={amber:"bg-amber-50 text-amber-700",green:"bg-emerald-50 text-emerald-700",red:"bg-red-50 text-red-700"}; return <article className="rounded-2xl border border-border bg-surface p-4"><span className={`grid h-9 w-9 place-items-center rounded-xl ${colors[tone]}`}><Icon className="h-4 w-4" /></span><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></article>; }
function Badge({ status }: { status: string }) { const color=status === "verified" ? "bg-emerald-100 text-emerald-700" : status === "rejected" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"; return <span className={`rounded-lg px-2.5 py-1 text-xs font-bold ${color}`}>{statusLabel[status] ?? status}</span>; }
function actionLabel(status: string) { if (status === "not_started") return "Mulai KYC"; if (status === "pending_review") return "Periksa"; if (status === "needs_information") return "Lengkapi"; if (status === "expired") return "Perbarui"; return "Buka KYC"; }
