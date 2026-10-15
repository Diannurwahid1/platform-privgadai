"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Banknote, Boxes, ClipboardList, ContactRound, FileCheck2, Filter, Search, ServerCog, ShieldCheck } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listAuditLog, type AuditLogEntry } from "@/lib/audit-log";
import { listDomainEvents, type DomainEvent } from "@/lib/operations";
import { useOrgContext } from "@/lib/org-context";
import { canViewAuditLog } from "@/lib/permissions";

const categories = {
  customer: { label: "Nasabah", icon: ContactRound, tone: "bg-cyan-50 text-cyan-700" },
  loan: { label: "Pinjaman", icon: ClipboardList, tone: "bg-blue-50 text-blue-700" },
  collateral: { label: "Agunan", icon: Boxes, tone: "bg-violet-50 text-violet-700" },
  finance: { label: "Keuangan", icon: Banknote, tone: "bg-emerald-50 text-emerald-700" },
  regulatory: { label: "Regulator", icon: FileCheck2, tone: "bg-amber-50 text-amber-800" },
};
const date = (value: string) => new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "medium" }).format(new Date(value));

export default function AuditLogPage() {
  const { slug } = useParams<{ slug: string }>();
  const { role } = useOrgContext();
  const canView = role ? canViewAuditLog(role) : false;
  const [events, setEvents] = useState<DomainEvent[] | null>(null);
  const [technical, setTechnical] = useState<AuditLogEntry[] | null>(null);
  const [tab, setTab] = useState<"business" | "technical">("business");
  const [category, setCategory] = useState("all");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canView) return;
    Promise.all([listDomainEvents(), listAuditLog(slug, { limit: 100 })])
      .then(([domainRows, technicalRows]) => { setEvents(domainRows); setTechnical(technicalRows); })
      .catch((reason: { detail?: string }) => setError(reason.detail ?? "Audit event gagal dimuat"));
  }, [slug, canView]);

  const filtered = useMemo(() => (events ?? []).filter((event) => (category === "all" || event.category === category) && [event.title, event.description, event.aggregate_reference, event.event_type].join(" ").toLowerCase().includes(query.toLowerCase())), [events, category, query]);
  if (!canView) return <ErrorState message="Peran Anda tidak memiliki izin untuk melihat audit." />;
  if (error) return <ErrorState message={error} />;
  if (!events || !technical) return <LoadingState label="Menyusun jejak kejadian bisnis" />;

  return <div className="space-y-5">
    <header className="flex flex-col gap-4 border-b border-border pb-5 xl:flex-row xl:items-end xl:justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Compliance · Audit</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Audit explorer</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Rekonstruksi kejadian bisnis dari pengajuan, agunan, keuangan, dan laporan regulator. Log HTTP tetap tersedia untuk investigasi teknis.</p></div><div className="inline-flex rounded-xl border border-border bg-surface p-1"><button type="button" onClick={() => setTab("business")} className={`rounded-lg px-3 py-2 text-xs font-semibold ${tab === "business" ? "bg-primary text-white" : "text-muted-foreground"}`}>Kejadian bisnis</button><button type="button" onClick={() => setTab("technical")} className={`rounded-lg px-3 py-2 text-xs font-semibold ${tab === "technical" ? "bg-primary text-white" : "text-muted-foreground"}`}>Log teknis</button></div></header>
    {tab === "business" ? <>
      <section className="flex flex-col gap-3 rounded-2xl border border-border bg-surface p-4 shadow-[var(--pg-shadow-sm)] md:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari event, record, atau referensi…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-3 text-sm" /></div><div className="flex items-center gap-2"><Filter className="h-4 w-4 text-muted-foreground" /><select value={category} onChange={(event) => setCategory(event.target.value)} className="h-10 rounded-xl border border-border bg-surface px-3 text-xs font-semibold"><option value="all">Semua domain</option><option value="customer">Nasabah/KYC</option><option value="loan">Pinjaman</option><option value="collateral">Agunan</option><option value="finance">Keuangan</option><option value="regulatory">Regulator</option></select></div></section>
      <section className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><div className="relative ml-3 border-l border-border pl-7">{filtered.map((event) => <EventRow key={`${event.category}-${event.id}`} event={event} slug={slug} />)}</div>{!filtered.length && <div className="py-12 text-center text-sm text-muted-foreground">Tidak ada event pada filter ini.</div>}</section>
    </> : <TechnicalLog entries={technical} />}
  </div>;
}

function EventRow({ event, slug }: { event: DomainEvent; slug: string }) {
  const category = categories[event.category as keyof typeof categories] ?? { label: event.category, icon: ShieldCheck, tone: "bg-surface-soft text-muted-foreground" };
  const Icon = category.icon;
  const target = event.aggregate_type === "application" ? `/orgs/${slug}/loans/applications/${event.aggregate_id}` : event.aggregate_type === "customer" ? `/orgs/${slug}/customers/${event.aggregate_id}` : null;
  return <article className="relative pb-7 last:pb-0"><span className={`absolute -left-[43px] top-0 grid h-8 w-8 place-items-center rounded-xl ring-4 ring-surface ${category.tone}`}><Icon className="h-4 w-4" /></span><div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between"><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><span className={`rounded-lg px-2 py-1 text-[10px] font-bold ${category.tone}`}>{category.label}</span><span className="font-mono text-[10px] text-muted-foreground">{event.event_type}</span></div><h2 className="mt-2 text-sm font-bold">{event.title}</h2><p className="mt-1 text-xs leading-5 text-muted-foreground">{event.description}</p>{target ? <Link href={target} className="mt-2 inline-block font-mono text-[11px] font-semibold text-primary hover:underline">{event.aggregate_reference}</Link> : <p className="mt-2 font-mono text-[11px] text-primary">{event.aggregate_reference}</p>}<details className="mt-3"><summary className="cursor-pointer text-[11px] font-semibold text-muted-foreground">Lihat metadata event</summary><pre className="mt-2 overflow-x-auto rounded-xl bg-slate-950 p-3 text-[10px] leading-5 text-slate-200">{JSON.stringify(event.metadata, null, 2)}</pre></details></div><div className="shrink-0 text-left lg:text-right"><time className="text-xs text-muted-foreground">{date(event.occurred_at)}</time><p className="mt-1 font-mono text-[10px] text-muted-foreground">actor {event.actor_id?.slice(0, 8) ?? "system"}</p></div></div></article>;
}

function TechnicalLog({ entries }: { entries: AuditLogEntry[] }) {
  return <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="flex gap-3 border-b border-border px-5 py-4"><ServerCog className="h-5 w-5 text-primary" /><div><h2 className="font-bold">Technical request log</h2><p className="mt-1 text-xs text-muted-foreground">Dipakai untuk trace API, status response, IP, dan user agent.</p></div></div><div className="divide-y divide-border">{entries.map((entry) => <div key={entry.id} className="grid gap-2 px-5 py-4 md:grid-cols-[1fr_150px_190px] md:items-center"><div><p className="text-sm font-semibold">{entry.action}</p><p className="mt-1 font-mono text-[11px] text-muted-foreground">{entry.method} {entry.path}</p></div><span className={`w-fit rounded-lg px-2 py-1 text-xs font-semibold ${entry.status_code < 400 ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>HTTP {entry.status_code}</span><time className="text-xs text-muted-foreground">{date(entry.created_at)}</time></div>)}</div></section>;
}
