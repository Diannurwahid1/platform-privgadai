"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowUpRight, CheckCircle2, ClipboardCheck, Clock3, History, Plus, Search, ShieldCheck, UserRoundCog, XCircle } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  createApprovalDelegation, decideApproval, listApprovalDelegations, listApprovals, listStaffAssignments,
  revokeApprovalDelegation, runApprovalEscalations, type ApprovalDelegation, type ApprovalQueueItem,
  type StaffAssignmentItem,
} from "@/lib/operations";

const when = (value: string | null) => value ? new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
const idr = (value: unknown) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));

export default function ApprovalsPage() {
  const { slug } = useParams<{ slug: string }>();
  const [items, setItems] = useState<ApprovalQueueItem[] | null>(null);
  const [delegations, setDelegations] = useState<ApprovalDelegation[]>([]);
  const [staff, setStaff] = useState<StaffAssignmentItem[]>([]);
  const [view, setView] = useState<"queue" | "delegations">("queue");
  const [status, setStatus] = useState("pending");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [assignmentId, setAssignmentId] = useState("");
  const [delegateId, setDelegateId] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [reason, setReason] = useState("");

  const load = useCallback(async () => {
    try {
      const [approvalRows, delegationRows, staffRows] = await Promise.all([listApprovals(), listApprovalDelegations(), listStaffAssignments()]);
      setItems(approvalRows); setDelegations(delegationRows); setStaff(staffRows.filter((row) => row.is_active));
    } catch (failure) { setError((failure as { detail?: string }).detail ?? "Approval workspace gagal dimuat"); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => (items ?? []).filter((item) =>
    (status === "all" || item.status === status) && `${item.aggregate_reference} ${item.action} ${item.request_reason}`.toLowerCase().includes(query.toLowerCase())), [items, status, query]);

  async function decide(item: ApprovalQueueItem, decision: "approved" | "rejected") {
    const decisionReason = window.prompt(`Alasan ${decision === "approved" ? "persetujuan" : "penolakan"}:`);
    if (!decisionReason) return;
    setBusy(item.id); setError(null);
    try { await decideApproval(item.id, decision, decisionReason); setNotice("Keputusan dan jejak checker berhasil dicatat."); await load(); }
    catch (failure) { setError((failure as { detail?: string }).detail ?? "Keputusan gagal disimpan"); }
    finally { setBusy(null); }
  }

  async function escalate() {
    setBusy("escalation"); setError(null);
    try { const result = await runApprovalEscalations(); setNotice(result.message); await load(); }
    catch (failure) { setError((failure as { detail?: string }).detail ?? "Eskalasi SLA gagal dijalankan"); }
    finally { setBusy(null); }
  }

  async function createDelegation() {
    const assignment = staff.find((row) => row.id === assignmentId);
    if (!assignment || !delegateId || !startsAt || !endsAt || reason.trim().length < 10) { setError("Lengkapi delegator, penerima, periode, dan alasan minimal 10 karakter."); return; }
    setBusy("delegation"); setError(null);
    try {
      await createApprovalDelegation({ delegator_user_id: assignment.user_id, delegate_user_id: delegateId,
        branch_id: assignment.branch_id, assigned_role: assignment.operational_role,
        starts_at: new Date(startsAt).toISOString(), ends_at: new Date(endsAt).toISOString(), reason: reason.trim() });
      setNotice("Delegasi berjangka berhasil dicatat."); setShowForm(false); setAssignmentId(""); setDelegateId(""); setReason(""); await load();
    } catch (failure) { setError((failure as { detail?: string }).detail ?? "Delegasi gagal dibuat"); }
    finally { setBusy(null); }
  }

  async function revoke(item: ApprovalDelegation) {
    setBusy(item.id); setError(null);
    try { await revokeApprovalDelegation(item.id); setNotice("Delegasi dicabut untuk keputusan berikutnya."); await load(); }
    catch (failure) { setError((failure as { detail?: string }).detail ?? "Delegasi gagal dicabut"); }
    finally { setBusy(null); }
  }

  if (error && !items) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat approval control center" />;
  const pending = items.filter((item) => item.status === "pending").length;
  const overdue = items.filter((item) => item.status === "pending" && item.due_at && new Date(item.due_at) < new Date()).length;
  const activeDelegations = delegations.filter((item) => !item.revoked_at && new Date(item.ends_at) >= new Date()).length;

  return <div className="space-y-5">
    <header className="flex flex-col gap-4 border-b border-border pb-5 xl:flex-row xl:items-end xl:justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Compliance · Four eyes</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Approval control center</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Keputusan berisiko, delegasi berjangka, SLA, eskalasi, snapshot, dan histori dalam satu ledger.</p></div><div className="flex flex-wrap gap-2"><button onClick={() => void escalate()} disabled={busy === "escalation"} className="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-surface px-4 text-xs font-bold"><ArrowUpRight className="h-4 w-4" />Jalankan eskalasi SLA</button><button onClick={() => { setView("delegations"); setShowForm(true); }} className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-white"><Plus className="h-4 w-4" />Delegasi</button></div></header>
    <div className="flex gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900"><ShieldCheck className="h-5 w-5 shrink-0" /><p><strong>Separation of duty aktif.</strong> Maker tidak dapat menjadi checker; keputusan melalui delegasi menyimpan identitas delegator.</p></div>
    {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    <section className="grid gap-3 sm:grid-cols-4"><Metric icon={Clock3} label="Menunggu" value={pending} /><Metric icon={AlertTriangle} label="Melewati SLA" value={overdue} alert /><Metric icon={ArrowUpRight} label="Terieskalasi" value={items.filter((item) => item.escalation_level > 0).length} /><Metric icon={UserRoundCog} label="Delegasi aktif" value={activeDelegations} /></section>
    <div className="flex gap-2 border-b border-border"><Tab active={view === "queue"} onClick={() => setView("queue")}>Antrean keputusan</Tab><Tab active={view === "delegations"} onClick={() => setView("delegations")}>Delegasi & out of office</Tab></div>
    {view === "queue" ? <Queue slug={slug} items={filtered} status={status} query={query} busy={busy} onQuery={setQuery} onStatus={setStatus} onDecision={decide} /> : <Delegations items={delegations} staff={staff} showForm={showForm} assignmentId={assignmentId} delegateId={delegateId} startsAt={startsAt} endsAt={endsAt} reason={reason} busy={busy} onShowForm={setShowForm} onAssignment={setAssignmentId} onDelegate={setDelegateId} onStartsAt={setStartsAt} onEndsAt={setEndsAt} onReason={setReason} onCreate={createDelegation} onRevoke={revoke} />}
  </div>;
}

function Queue({ slug, items, status, query, busy, onQuery, onStatus, onDecision }: { slug: string; items: ApprovalQueueItem[]; status: string; query: string; busy: string | null; onQuery: (value: string) => void; onStatus: (value: string) => void; onDecision: (item: ApprovalQueueItem, decision: "approved" | "rejected") => Promise<void> }) {
  return <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Cari referensi, aksi, atau alasan…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-4 text-sm" /></div><div className="flex gap-2">{[["pending", "Menunggu"], ["approved", "Disetujui"], ["rejected", "Ditolak"], ["all", "Semua"]].map(([value, label]) => <button key={value} onClick={() => onStatus(value)} className={`rounded-lg border px-3 py-2 text-xs font-semibold ${status === value ? "border-primary bg-primary text-white" : "border-border"}`}>{label}</button>)}</div></div><div className="divide-y divide-border">{items.map((item) => { const applicationId = String(item.payload_snapshot.application_id ?? ""); const destination = item.aggregate_type === "complaint" ? `/orgs/${slug}/compliance/complaints/${item.aggregate_id}` : item.aggregate_type === "configuration" ? `/orgs/${slug}/management/settings` : item.aggregate_type === "payment_adjustment" ? `/orgs/${slug}/finance/payments` : item.aggregate_type === "reconciliation" ? `/orgs/${slug}/finance/reconciliation` : applicationId ? `/orgs/${slug}/loans/applications/${applicationId}` : "#"; return <article key={item.id} className="p-5"><div className="flex flex-col gap-4 xl:flex-row xl:justify-between"><div><div className="flex flex-wrap items-center gap-2"><Badge status={item.status} /><span className="rounded-lg bg-surface-soft px-2 py-1 text-[10px] font-bold uppercase">{item.priority}</span><span className="font-mono text-[10px] text-muted-foreground">v{item.version}</span>{item.escalation_level > 0 && <span className="rounded-lg bg-red-50 px-2 py-1 text-[10px] font-bold text-red-700">Eskalasi L{item.escalation_level}</span>}</div><Link href={destination} className="mt-3 block font-mono text-sm font-bold text-primary">{item.aggregate_reference}</Link><p className="mt-1 text-sm font-semibold">{item.action.replaceAll("_", " ")}</p><p className="mt-1 text-xs text-muted-foreground">{item.request_reason}</p></div><div className="grid gap-1 text-xs text-muted-foreground xl:text-right"><span>Dibuat {when(item.created_at)}</span><span>SLA {when(item.due_at)}</span><span>Checker: {item.assigned_role}</span></div></div>{item.aggregate_type === "appraisal" && <div className="mt-4 grid gap-3 rounded-xl bg-surface-soft p-4 sm:grid-cols-4"><Fact label="Pasar" value={idr(item.payload_snapshot.market_value)} /><Fact label="Likuidasi" value={idr(item.payload_snapshot.liquidation_value)} /><Fact label="Rekomendasi" value={idr(item.payload_snapshot.recommended_loan)} /><Fact label="Grade" value={String(item.payload_snapshot.condition_grade ?? "—")} /></div>}<div className="mt-4 rounded-xl border border-border bg-background p-3"><p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground"><History className="h-3.5 w-3.5" />Histori kontrol</p><div className="mt-2 grid gap-2">{item.events.map((event) => <div key={event.id} className="flex flex-col gap-1 text-xs sm:flex-row sm:justify-between"><span><strong>{event.event_type}</strong>{event.reason ? ` · ${event.reason}` : ""}</span><span className="text-muted-foreground">{when(event.occurred_at)}</span></div>)}</div></div>{item.status === "pending" && <div className="mt-4 flex gap-2"><button disabled={busy === item.id} onClick={() => void onDecision(item, "approved")} className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white"><CheckCircle2 className="h-4 w-4" />Setujui</button><button disabled={busy === item.id} onClick={() => void onDecision(item, "rejected")} className="inline-flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs font-bold text-red-700"><XCircle className="h-4 w-4" />Tolak</button></div>}{item.decision_reason && <p className="mt-3 text-xs text-muted-foreground">Alasan keputusan: {item.decision_reason}</p>}</article>; })}{!items.length && <div className="flex flex-col items-center px-6 py-14 text-center"><ClipboardCheck className="h-8 w-8 text-emerald-600" /><p className="mt-3 text-sm font-semibold">Tidak ada approval pada filter ini</p></div>}</div></section>;
}

type DelegationProps = { items: ApprovalDelegation[]; staff: StaffAssignmentItem[]; showForm: boolean; assignmentId: string; delegateId: string; startsAt: string; endsAt: string; reason: string; busy: string | null; onShowForm: (value: boolean) => void; onAssignment: (value: string) => void; onDelegate: (value: string) => void; onStartsAt: (value: string) => void; onEndsAt: (value: string) => void; onReason: (value: string) => void; onCreate: () => Promise<void>; onRevoke: (item: ApprovalDelegation) => Promise<void> };
function Delegations(props: DelegationProps) {
  const delegates = Array.from(new Map(props.staff.map((row) => [row.user_id, row])).values());
  return <div className="space-y-4">{props.showForm && <section className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><div className="flex items-center justify-between"><div><h2 className="font-bold">Delegasi approval berjangka</h2><p className="mt-1 text-xs text-muted-foreground">Hak berlaku hanya pada peran, cabang, dan periode yang dipilih.</p></div><button onClick={() => props.onShowForm(false)} className="text-xs font-semibold text-muted-foreground">Tutup</button></div><div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3"><Field label="Penugasan delegator"><select value={props.assignmentId} onChange={(event) => props.onAssignment(event.target.value)} className="control"><option value="">Pilih pemegang peran</option>{props.staff.map((row) => <option key={row.id} value={row.id}>{row.user_name} · {row.operational_role} · {row.branch_name}</option>)}</select></Field><Field label="Penerima delegasi"><select value={props.delegateId} onChange={(event) => props.onDelegate(event.target.value)} className="control"><option value="">Pilih penerima</option>{delegates.map((row) => <option key={row.user_id} value={row.user_id}>{row.user_name}</option>)}</select></Field><Field label="Mulai"><input type="datetime-local" value={props.startsAt} onChange={(event) => props.onStartsAt(event.target.value)} className="control" /></Field><Field label="Berakhir"><input type="datetime-local" value={props.endsAt} onChange={(event) => props.onEndsAt(event.target.value)} className="control" /></Field><Field label="Alasan / out of office"><input value={props.reason} onChange={(event) => props.onReason(event.target.value)} className="control" placeholder="Cuti, dinas, atau pengganti sementara" /></Field><div className="flex items-end"><button disabled={props.busy === "delegation"} onClick={() => void props.onCreate()} className="h-10 rounded-xl bg-primary px-4 text-xs font-bold text-white">Aktifkan delegasi</button></div></div></section>}<section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border px-5 py-4"><h2 className="font-bold">Register delegasi</h2><p className="mt-1 text-xs text-muted-foreground">Periode terdahulu tetap dipertahankan untuk audit.</p></div><div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Penerima</th><th className="px-5 py-3">Peran</th><th className="px-5 py-3">Periode</th><th className="px-5 py-3">Alasan</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Aksi</th></tr></thead><tbody className="divide-y divide-border">{props.items.map((item) => { const active = !item.revoked_at && new Date(item.ends_at) >= new Date(); return <tr key={item.id}><td className="px-5 py-4 font-semibold">{item.delegate_name}</td><td className="px-5 py-4">{item.assigned_role}</td><td className="px-5 py-4 text-xs">{when(item.starts_at)} — {when(item.ends_at)}</td><td className="max-w-xs px-5 py-4 text-xs text-muted-foreground">{item.reason}</td><td className="px-5 py-4"><span className={`rounded-lg px-2 py-1 text-xs font-bold ${active ? "bg-emerald-50 text-emerald-700" : "bg-surface-soft text-muted-foreground"}`}>{item.revoked_at ? "Dicabut" : active ? "Aktif" : "Berakhir"}</span></td><td className="px-5 py-4">{active && <button disabled={props.busy === item.id} onClick={() => void props.onRevoke(item)} className="text-xs font-bold text-red-700">Cabut</button>}</td></tr>; })}</tbody></table>{!props.items.length && <div className="px-6 py-14 text-center text-sm text-muted-foreground">Belum ada delegasi approval.</div>}</div></section></div>;
}

function Tab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) { return <button onClick={onClick} className={`border-b-2 px-3 py-3 text-xs font-bold ${active ? "border-primary text-primary" : "border-transparent text-muted-foreground"}`}>{children}</button>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="grid gap-2 text-xs font-semibold text-muted-foreground">{label}{children}</label>; }
function Badge({ status }: { status: string }) { const color = status === "approved" ? "bg-emerald-100 text-emerald-700" : status === "rejected" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"; return <span className={`rounded-lg px-2.5 py-1 text-xs font-bold ${color}`}>{status}</span>; }
function Metric({ icon: Icon, label, value, alert = false }: { icon: typeof Clock3; label: string; value: number; alert?: boolean }) { return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className={`h-4 w-4 ${alert ? "text-red-600" : "text-primary"}`} /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></article>; }
function Fact({ label, value }: { label: string; value: string }) { return <div><p className="text-[10px] font-bold uppercase text-muted-foreground">{label}</p><p className="mt-1 text-sm font-semibold">{value}</p></div>; }
