"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ClipboardCheck, Clock3, Search, ShieldCheck, XCircle } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { decideApproval, listApprovals, type ApprovalQueueItem } from "@/lib/operations";

const when = (value: string | null) => value ? new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
const idr = (value: unknown) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));

export default function ApprovalsPage() {
  const { slug } = useParams<{ slug: string }>();
  const [items, setItems] = useState<ApprovalQueueItem[] | null>(null);
  const [status, setStatus] = useState("pending");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => listApprovals().then(setItems).catch((e: { detail?: string }) => setError(e.detail ?? "Approval inbox gagal dimuat")), []);
  useEffect(() => { void load(); }, [load]);
  const filtered = useMemo(() => (items ?? []).filter((item) => (status === "all" || item.status === status) && `${item.aggregate_reference} ${item.action} ${item.request_reason}`.toLowerCase().includes(query.toLowerCase())), [items, status, query]);
  async function decide(item: ApprovalQueueItem, decision: "approved" | "rejected") {
    const reason = window.prompt(`Alasan ${decision === "approved" ? "persetujuan" : "penolakan"}:`);
    if (!reason) return;
    setBusy(item.id); setError(null);
    try { await decideApproval(item.id, decision, reason); await load(); }
    catch (e) { setError((e as { detail?: string }).detail ?? "Keputusan gagal disimpan"); }
    finally { setBusy(null); }
  }
  if (error && !items) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat approval ledger" />;
  const pending = items.filter((item) => item.status === "pending").length;
  const overdue = items.filter((item) => item.status === "pending" && item.due_at && new Date(item.due_at) < new Date()).length;

  return <div className="space-y-5">
    <header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Compliance · Four eyes</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Approval inbox</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Ledger keputusan untuk appraisal dan command berisiko, lengkap dengan maker, checker, snapshot, SLA, alasan, dan histori.</p></header>
    <div className="flex gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900"><ShieldCheck className="h-5 w-5 shrink-0" /><p><strong>Separation of duty aktif.</strong> Pembuat permintaan tidak dapat menyetujui permintaannya sendiri melalui API.</p></div>
    {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    <section className="grid gap-3 sm:grid-cols-3"><Metric icon={Clock3} label="Menunggu" value={pending} /><Metric icon={AlertTriangle} label="Melewati SLA" value={overdue} alert /><Metric icon={CheckCircle2} label="Diputuskan" value={items.length-pending} /></section>
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
      <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="Cari referensi, aksi, atau alasan…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-4 text-sm" /></div><div className="flex gap-2">{[["pending","Menunggu"],["approved","Disetujui"],["rejected","Ditolak"],["all","Semua"]].map(([value,label])=><button key={value} onClick={()=>setStatus(value)} className={`rounded-lg border px-3 py-2 text-xs font-semibold ${status===value?"border-primary bg-primary text-white":"border-border"}`}>{label}</button>)}</div></div>
      <div className="divide-y divide-border">{filtered.map((item)=>{const applicationId=String(item.payload_snapshot.application_id??"");return <article key={item.id} className="p-5"><div className="flex flex-col gap-4 xl:flex-row xl:justify-between"><div><div className="flex items-center gap-2"><Badge status={item.status}/><span className="rounded-lg bg-surface-soft px-2 py-1 text-[10px] font-bold uppercase">{item.priority}</span><span className="font-mono text-[10px] text-muted-foreground">v{item.version}</span></div><Link href={applicationId?`/orgs/${slug}/loans/applications/${applicationId}`:"#"} className="mt-3 block font-mono text-sm font-bold text-primary">{item.aggregate_reference}</Link><p className="mt-1 text-sm font-semibold">{item.action.replaceAll("_"," ")}</p><p className="mt-1 text-xs text-muted-foreground">{item.request_reason}</p></div><div className="grid gap-1 text-xs text-muted-foreground xl:text-right"><span>Dibuat {when(item.created_at)}</span><span>SLA {when(item.due_at)}</span><span>Checker: {item.assigned_role}</span></div></div>{item.aggregate_type==="appraisal"&&<div className="mt-4 grid gap-3 rounded-xl bg-surface-soft p-4 sm:grid-cols-4"><Fact label="Pasar" value={idr(item.payload_snapshot.market_value)}/><Fact label="Likuidasi" value={idr(item.payload_snapshot.liquidation_value)}/><Fact label="Rekomendasi" value={idr(item.payload_snapshot.recommended_loan)}/><Fact label="Grade" value={String(item.payload_snapshot.condition_grade??"—")}/></div>}{item.status==="pending"&&<div className="mt-4 flex gap-2"><button disabled={busy===item.id} onClick={()=>decide(item,"approved")} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white"><CheckCircle2 className="h-4 w-4"/>Setujui</button><button disabled={busy===item.id} onClick={()=>decide(item,"rejected")} className="inline-flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs font-bold text-red-700"><XCircle className="h-4 w-4"/>Tolak</button></div>}{item.decision_reason&&<p className="mt-3 text-xs text-muted-foreground">Alasan keputusan: {item.decision_reason}</p>}</article>})}{!filtered.length&&<div className="flex flex-col items-center px-6 py-14 text-center"><ClipboardCheck className="h-8 w-8 text-emerald-600"/><p className="mt-3 text-sm font-semibold">Tidak ada approval pada filter ini</p></div>}</div>
    </section>
  </div>;
}

function Badge({status}:{status:string}){const color=status==="approved"?"bg-emerald-100 text-emerald-700":status==="rejected"?"bg-red-100 text-red-700":"bg-amber-100 text-amber-700";return <span className={`rounded-lg px-2.5 py-1 text-xs font-bold ${color}`}>{status}</span>}
function Metric({icon:Icon,label,value,alert=false}:{icon:typeof Clock3;label:string;value:number;alert?:boolean}){return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className={`h-4 w-4 ${alert?"text-red-600":"text-primary"}`}/><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></article>}
function Fact({label,value}:{label:string;value:string}){return <div><p className="text-[10px] font-bold uppercase text-muted-foreground">{label}</p><p className="mt-1 text-sm font-semibold">{value}</p></div>}
