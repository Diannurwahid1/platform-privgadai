"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, Clock3, FileSearch, History, ShieldAlert, UserRoundCheck } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  addIncidentNote,
  getIncident,
  listStaffAssignments,
  reopenIncident,
  requestIncidentResolution,
  triageIncident,
  type IncidentDetail,
  type StaffAssignmentItem,
} from "@/lib/operations";

export default function IncidentDetailPage() {
  const { slug, id } = useParams<{ slug: string; id: string }>();
  const [item, setItem] = useState<IncidentDetail | null>(null);
  const [staff, setStaff] = useState<StaffAssignmentItem[]>([]);
  const [owner, setOwner] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [rootCause, setRootCause] = useState("");
  const [actionPlan, setActionPlan] = useState("");
  const [note, setNote] = useState("");
  const [resolution, setResolution] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const load = useCallback(async () => {
    const [detail, assignments] = await Promise.all([getIncident(id), listStaffAssignments()]);
    setItem(detail); setStaff(assignments);
    setOwner(detail.assigned_to_user_id ?? "");
    setDueAt(detail.due_at ? new Date(detail.due_at).toISOString().slice(0, 16) : "");
    setRootCause(detail.root_cause ?? ""); setActionPlan(detail.action_plan ?? "");
  }, [id]);
  useEffect(() => { load().catch((reason: { detail?: string }) => setError(reason.detail ?? "Detail incident gagal dimuat")); }, [load]);
  const branchStaff = useMemo(() => staff.filter((person) => person.branch_id === item?.application.branch_id), [staff, item]);
  async function execute(action: () => Promise<unknown>, message: string) { setBusy(true); setError(null); try { await action(); setNotice(message); await load(); } catch (reason) { setError((reason as { detail?: string }).detail ?? "Tindakan incident gagal"); } finally { setBusy(false); } }
  if (error && !item) return <ErrorState message={error} />;
  if (!item) return <LoadingState label="Membuka incident case" />;
  const canInvestigate = ["open", "reopened", "investigating"].includes(item.status);
  return (
    <div className="space-y-5">
      <header className="border-b border-border pb-5"><Link href={`/orgs/${slug}/compliance/exceptions`} className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-primary"><ArrowLeft className="h-4 w-4" />Incident register</Link><div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between"><div><div className="flex flex-wrap items-center gap-2"><Severity value={item.severity} /><Status value={item.status} />{item.reopened_count > 0 && <span className="rounded-lg bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">Reopened {item.reopened_count}×</span>}</div><h1 className="mt-3 text-3xl font-bold tracking-[-0.045em]">{item.incident_type.replaceAll("_", " ")}</h1><p className="mt-2 font-mono text-xs text-primary">INC-{item.id.slice(0, 8).toUpperCase()} · {item.application.application_no}</p></div><Link href={`/orgs/${slug}/loans/applications/${item.application.id}`} className="rounded-xl border border-border px-4 py-2.5 text-xs font-bold">Buka pengajuan terkait</Link></div></header>
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
      <section className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <div className="space-y-4"><Panel title="Ringkasan kejadian" icon={ShieldAlert}><p className="text-sm leading-6">{item.description}</p><div className="mt-5 grid gap-3 sm:grid-cols-3"><Fact label="Nasabah" value={item.application.borrower_name} /><Fact label="Cabang" value={`${item.application.branch_code} · ${item.application.branch_name}`} /><Fact label="Agunan" value={`${item.asset.asset_code} · ${item.asset.label || "—"}`} /></div></Panel>
          {canInvestigate && <Panel title="Triage & investigation plan" icon={UserRoundCheck}><div className="grid gap-3 sm:grid-cols-2"><Field label="Owner kasus"><select value={owner} onChange={(event) => setOwner(event.target.value)} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm"><option value="">Pilih owner</option>{branchStaff.map((person) => <option key={person.id} value={person.user_id}>{person.user_name} · {person.operational_role}</option>)}</select></Field><Field label="Target SLA"><input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm" /></Field></div><Field label="Root cause"><textarea value={rootCause} onChange={(event) => setRootCause(event.target.value)} className="min-h-24 w-full rounded-xl border border-border bg-background px-3 py-3 text-sm" placeholder="Fakta penyebab dasar berdasarkan hasil investigasi" /></Field><Field label="Corrective action plan"><textarea value={actionPlan} onChange={(event) => setActionPlan(event.target.value)} className="min-h-24 w-full rounded-xl border border-border bg-background px-3 py-3 text-sm" placeholder="Tindakan, PIC, dan kontrol agar kejadian tidak berulang" /></Field><button disabled={busy || !owner || !dueAt || rootCause.length < 5 || actionPlan.length < 5} onClick={() => execute(() => triageIncident(id, { assigned_to_user_id: owner, due_at: new Date(dueAt).toISOString(), root_cause: rootCause, action_plan: actionPlan }), "Triage dan rencana investigasi diperbarui.")} className="rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Simpan triage</button></Panel>}
          <Panel title="Catatan investigasi" icon={FileSearch}><div className="flex gap-2"><input value={note} onChange={(event) => setNote(event.target.value)} className="h-10 min-w-0 flex-1 rounded-xl border border-border bg-background px-3 text-sm" placeholder="Tambahkan fakta, temuan, atau referensi bukti…" /><button disabled={busy || note.length < 3} onClick={() => execute(async () => { await addIncidentNote(id, note); setNote(""); }, "Catatan investigasi ditambahkan.")} className="rounded-xl border border-primary px-4 py-2.5 text-xs font-bold text-primary disabled:opacity-50">Tambah catatan</button></div></Panel>
          {["investigating", "reopened"].includes(item.status) && <Panel title="Ajukan resolusi" icon={CheckCircle2}><p className="mb-3 text-xs text-muted-foreground">Resolusi tidak langsung menutup kasus. Branch manager harus memeriksa root cause dan action plan melalui Approval Inbox.</p><textarea value={resolution} onChange={(event) => setResolution(event.target.value)} className="min-h-24 w-full rounded-xl border border-border bg-background px-3 py-3 text-sm" placeholder="Ringkasan hasil, bukti penyelesaian, dan residual risk" /><button disabled={busy || resolution.length < 10} onClick={() => execute(() => requestIncidentResolution(id, resolution), "Resolusi dikirim ke branch manager untuk approval.")} className="mt-3 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Kirim untuk approval</button></Panel>}
          {item.status === "resolved" && <Panel title="Reopen case" icon={ShieldAlert}><textarea value={resolution} onChange={(event) => setResolution(event.target.value)} className="min-h-20 w-full rounded-xl border border-border bg-background px-3 py-3 text-sm" placeholder="Alasan kasus perlu dibuka kembali" /><button disabled={busy || resolution.length < 10} onClick={() => execute(() => reopenIncident(id, resolution), "Incident dibuka kembali dan agunan ditahan.")} className="mt-3 rounded-xl border border-primary px-4 py-2.5 text-xs font-bold text-primary disabled:opacity-50">Buka kembali</button></Panel>}
        </div>
        <div className="space-y-4"><Panel title="Case control" icon={Clock3}><div className="space-y-4"><Fact label="Owner" value={staff.find((person) => person.user_id === item.assigned_to_user_id)?.user_name ?? "Belum ditugaskan"} /><Fact label="SLA" value={item.due_at ? new Date(item.due_at).toLocaleString("id-ID") : "Belum ditetapkan"} /><Fact label="Status agunan" value={item.asset.collateral_status.replaceAll("_", " ")} /><Fact label="Resolusi" value={item.resolution_note ?? "Belum diajukan"} /></div></Panel><Panel title="Event history" icon={History}><div className="space-y-4">{item.events.map((event) => <div key={event.id} className="border-l-2 border-primary/20 pl-3"><p className="text-xs font-bold">{event.event_type.replaceAll(/([A-Z])/g, " $1").trim()}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{event.note ?? `${event.from_status ?? "—"} → ${event.to_status ?? "—"}`}</p><time className="mt-1 block text-[10px] text-muted-foreground">{new Date(event.occurred_at).toLocaleString("id-ID")}</time></div>)}</div></Panel></div>
      </section>
    </div>
  );
}

function Panel({ title, icon: Icon, children }: { title: string; icon: typeof ShieldAlert; children: React.ReactNode }) { return <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="flex items-center gap-2 font-bold"><Icon className="h-4 w-4 text-primary" />{title}</h2><div className="mt-4">{children}</div></article>; }
function Fact({ label, value }: { label: string; value: string }) { return <div><p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-sm font-semibold capitalize">{value}</p></div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="mb-3 block"><span className="mb-1.5 block text-xs font-semibold">{label}</span>{children}</label>; }
function Severity({ value }: { value: string }) { return <span className={`rounded-lg px-2.5 py-1 text-xs font-bold uppercase ${["critical", "high"].includes(value) ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-800"}`}>{value}</span>; }
function Status({ value }: { value: string }) { return <span className="rounded-lg bg-surface-blue px-2.5 py-1 text-xs font-semibold capitalize text-primary">{value.replaceAll("_", " ")}</span>; }
