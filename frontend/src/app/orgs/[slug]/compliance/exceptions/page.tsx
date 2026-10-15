"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Clock3, Search, ShieldAlert, TriangleAlert, UserRoundCheck } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listIncidents, type IncidentListItem } from "@/lib/operations";

const statusLabel: Record<string, string> = {
  open: "Belum ditriase",
  investigating: "Investigasi",
  pending_resolution: "Menunggu approval",
  resolved: "Selesai",
  reopened: "Dibuka kembali",
};

export default function ExceptionsPage() {
  const { slug } = useParams<{ slug: string }>();
  const [items, setItems] = useState<IncidentListItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("active");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { listIncidents().then(setItems).catch((reason: { detail?: string }) => setError(reason.detail ?? "Incident register gagal dimuat")); }, []);
  const filtered = useMemo(() => (items ?? []).filter((item) => {
    const matchesStatus = status === "all" || (status === "active" ? item.status !== "resolved" : item.status === status);
    const haystack = `${item.application_no} ${item.borrower_name} ${item.incident_type} ${item.description}`.toLowerCase();
    return matchesStatus && haystack.includes(query.toLowerCase());
  }), [items, query, status]);
  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat incident register" />;
  const active = items.filter((item) => item.status !== "resolved");
  return (
    <div className="space-y-5">
      <header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Compliance · Exceptions</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Incident & Exception Register</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Kelola kasus operasional berbasis event dengan owner, SLA, root cause, tindakan korektif, dan approval resolusi.</p></header>
      <section className="grid gap-3 sm:grid-cols-4"><Summary label="Kasus aktif" value={active.length} icon={ShieldAlert} /><Summary label="Critical / high" value={active.filter((item) => ["critical", "high"].includes(item.severity)).length} icon={TriangleAlert} /><Summary label="SLA terlewat" value={active.filter((item) => item.is_overdue).length} icon={Clock3} /><Summary label="Sudah ditugaskan" value={active.filter((item) => item.assigned_to_user_id).length} icon={UserRoundCheck} /></section>
      <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
        <div className="flex flex-col gap-3 border-b border-border p-4 md:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari nomor pengajuan, debitur, tipe, atau uraian…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-3 text-sm" /></div><select value={status} onChange={(event) => setStatus(event.target.value)} className="h-10 rounded-xl border border-border bg-surface px-3 text-xs font-semibold"><option value="active">Semua kasus aktif</option><option value="open">Belum ditriase</option><option value="investigating">Investigasi</option><option value="pending_resolution">Menunggu approval</option><option value="resolved">Selesai</option><option value="all">Semua status</option></select></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[980px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Kasus & nasabah</th><th className="px-5 py-3">Cabang</th><th className="px-5 py-3">Severity</th><th className="px-5 py-3">Owner</th><th className="px-5 py-3">SLA</th><th className="px-5 py-3">Status</th><th className="px-5 py-3"></th></tr></thead><tbody className="divide-y divide-border">{filtered.map((item) => <tr key={item.id} className="hover:bg-surface-soft/70"><td className="px-5 py-4"><p className="font-mono text-xs font-semibold text-primary">{item.application_no}</p><p className="mt-1 font-semibold">{item.borrower_name} · {item.incident_type.replaceAll("_", " ")}</p><p className="mt-1 max-w-md truncate text-xs text-muted-foreground">{item.description}</p></td><td className="px-5 py-4"><p className="font-semibold">{item.branch_code}</p><p className="text-xs text-muted-foreground">{item.branch_name}</p></td><td className="px-5 py-4"><Severity value={item.severity} /></td><td className="px-5 py-4 text-xs">{item.assigned_to_name ?? "Belum ditugaskan"}</td><td className={`px-5 py-4 text-xs ${item.is_overdue ? "font-bold text-red-700" : "text-muted-foreground"}`}>{item.due_at ? new Date(item.due_at).toLocaleString("id-ID") : "—"}</td><td className="px-5 py-4"><span className="rounded-lg bg-surface-blue px-2.5 py-1 text-xs font-semibold text-primary">{statusLabel[item.status] ?? item.status}</span></td><td className="px-5 py-4"><Link href={`/orgs/${slug}/compliance/exceptions/${item.id}`} className="grid h-9 w-9 place-items-center rounded-lg border border-border text-muted-foreground hover:border-primary/30 hover:text-primary"><ArrowRight className="h-4 w-4" /></Link></td></tr>)}</tbody></table>{!filtered.length && <div className="px-6 py-14 text-center text-sm text-muted-foreground">Tidak ada incident pada filter ini.</div>}</div>
      </section>
    </div>
  );
}

function Summary({ label, value, icon: Icon }: { label: string; value: number; icon: typeof ShieldAlert }) { return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className="h-4 w-4 text-primary" /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 text-xl font-bold">{value}</p></article>; }
function Severity({ value }: { value: string }) { const danger = ["critical", "high"].includes(value); return <span className={`rounded-lg px-2.5 py-1 text-xs font-bold uppercase ${danger ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-800"}`}>{value}</span>; }
