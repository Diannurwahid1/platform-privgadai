"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, FileSearch, Play } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { createReconciliation, listBranches, listReconciliations, requestReconciliationResolution, type BranchItem, type ReconciliationRun } from "@/lib/operations";

const idr = (value: unknown) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));
const today = () => new Date().toISOString().slice(0, 10);
const scopeLabels: Record<string, string> = { cash_gl: "Cash transaction ↔ GL", loan_subledger_gl: "Loan subledger ↔ GL", bank_statement: "Bank statement ↔ receipt" };

export default function ReconciliationPage() {
  const [runs, setRuns] = useState<ReconciliationRun[] | null>(null);
  const [branches, setBranches] = useState<BranchItem[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [form, setForm] = useState({ scope: "cash_gl", business_date: today(), branch_id: "", observed_amount: "", tolerance_amount: "0", statement_reference: "" });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const load = useCallback(async () => { const [runRows, branchRows] = await Promise.all([listReconciliations(), listBranches()]); setRuns(runRows); setBranches(branchRows); }, []);
  useEffect(() => { void load().catch((reason: { detail?: string }) => setError(reason.detail ?? "Reconciliation workbench gagal dimuat")); }, [load]);

  async function run() {
    if (form.scope === "bank_statement" && (!form.observed_amount || !form.statement_reference)) { setError("Total statement dan referensi wajib untuk rekonsiliasi bank."); return; }
    setBusy("run"); setError(null);
    try {
      const result = await createReconciliation({ scope: form.scope, business_date: form.business_date, branch_id: form.branch_id || null, observed_amount: form.scope === "bank_statement" ? Number(form.observed_amount) : null, tolerance_amount: Number(form.tolerance_amount || 0), statement_reference: form.statement_reference || null });
      setNotice(`${result.message}: ${result.status}.`); await load();
    } catch (reason) { setError((reason as { detail?: string }).detail ?? "Rekonsiliasi gagal dijalankan"); }
    finally { setBusy(null); }
  }

  async function resolve(item: ReconciliationRun) {
    const note = window.prompt("Root cause dan tindakan koreksi (minimal 10 karakter):");
    if (!note || note.trim().length < 10) return;
    setBusy(item.id); setError(null);
    try { const result = await requestReconciliationResolution(item.id, note.trim()); setNotice(result.message); await load(); }
    catch (reason) { setError((reason as { detail?: string }).detail ?? "Resolusi exception gagal diajukan"); }
    finally { setBusy(null); }
  }

  if (!runs) return error ? <ErrorState message={error} /> : <LoadingState label="Memuat reconciliation workbench" />;
  const matched = runs.filter((item) => item.status === "matched").length;
  const exceptions = runs.filter((item) => ["exception", "pending_resolution"].includes(item.status)).length;
  return <div className="space-y-5">
    <header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Finance · Reconciliation</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Reconciliation workbench</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Bandingkan cash transaction, loan subledger, general ledger, dan bank statement dari snapshot bertanggal. Exception diselesaikan melalui maker-checker.</p></header>
    {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <section className="grid gap-3 sm:grid-cols-3"><Metric icon={FileSearch} label="Run tersimpan" value={runs.length} /><Metric icon={CheckCircle2} label="Matched" value={matched} /><Metric icon={AlertTriangle} label="Exception aktif" value={exceptions} attention={exceptions > 0} /></section>
    <section className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><div className="flex items-center gap-2"><Play className="h-4 w-4 text-primary" /><div><h2 className="font-bold">Jalankan snapshot</h2><p className="text-xs text-muted-foreground">Nilai dihitung ulang dari source transaction dan journal posted.</p></div></div><div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-6"><Field label="Scope"><select value={form.scope} onChange={(event) => setForm({ ...form, scope: event.target.value })} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm disabled:opacity-50"><option value="cash_gl">Cash ↔ GL</option><option value="loan_subledger_gl">Subledger ↔ GL</option><option value="bank_statement">Bank ↔ Receipt</option></select></Field><Field label="Business date"><input type="date" value={form.business_date} onChange={(event) => setForm({ ...form, business_date: event.target.value })} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm disabled:opacity-50" /></Field><Field label="Cabang"><select value={form.branch_id} onChange={(event) => setForm({ ...form, branch_id: event.target.value })} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm disabled:opacity-50"><option value="">Semua cabang</option>{branches.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select></Field><Field label="Observed / statement"><input disabled={form.scope !== "bank_statement"} inputMode="numeric" value={form.observed_amount} onChange={(event) => setForm({ ...form, observed_amount: event.target.value })} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm disabled:opacity-50" placeholder="0" /></Field><Field label="Tolerance"><input inputMode="numeric" value={form.tolerance_amount} onChange={(event) => setForm({ ...form, tolerance_amount: event.target.value })} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm disabled:opacity-50" /></Field><Field label="Statement reference"><input disabled={form.scope !== "bank_statement"} value={form.statement_reference} onChange={(event) => setForm({ ...form, statement_reference: event.target.value })} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm disabled:opacity-50" placeholder="File / statement ID" /></Field></div><button disabled={busy !== null} onClick={() => void run()} className="mt-4 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Run reconciliation</button></section>
    <section className="overflow-hidden rounded-2xl border border-border bg-surface"><div className="overflow-x-auto"><table className="w-full min-w-[1080px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Tanggal & scope</th><th className="px-5 py-3 text-right">Expected</th><th className="px-5 py-3 text-right">Observed</th><th className="px-5 py-3 text-right">Variance</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Aksi</th></tr></thead><tbody className="divide-y divide-border">{runs.map((item) => <tr key={item.id} className="align-top"><td className="px-5 py-4"><button onClick={() => setExpanded(expanded === item.id ? null : item.id)} className="text-left"><p className="font-semibold">{scopeLabels[item.scope] ?? item.scope}</p><p className="mt-1 font-mono text-xs text-muted-foreground">{item.business_date}</p>{expanded === item.id && <pre className="mt-3 max-w-md overflow-auto rounded-lg bg-surface-soft p-3 text-[10px] leading-5">{JSON.stringify(item.snapshot, null, 2)}</pre>}</button></td><td className="px-5 py-4 text-right font-semibold">{idr(item.expected_amount)}</td><td className="px-5 py-4 text-right font-semibold">{idr(item.observed_amount)}</td><td className={`px-5 py-4 text-right font-bold ${Number(item.variance_amount) ? "text-red-700" : "text-emerald-700"}`}>{idr(item.variance_amount)}</td><td className="px-5 py-4"><Status value={item.status} /></td><td className="px-5 py-4">{item.status === "exception" && <button disabled={busy !== null} onClick={() => void resolve(item)} className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800">Ajukan resolusi</button>}{item.resolution_note && <p className="mt-2 max-w-xs text-xs text-muted-foreground">{item.resolution_note}</p>}</td></tr>)}</tbody></table>{!runs.length && <div className="px-6 py-14 text-center text-sm text-muted-foreground">Belum ada reconciliation run.</div>}</div></section>
  </div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="grid gap-2 text-xs font-semibold text-muted-foreground">{label}{children}</label>; }
function Metric({ icon: Icon, label, value, attention = false }: { icon: typeof FileSearch; label: string; value: number; attention?: boolean }) { return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className={`h-4 w-4 ${attention ? "text-red-600" : "text-primary"}`} /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></article>; }
function Status({ value }: { value: string }) { const color = value === "matched" || value === "resolved" ? "bg-emerald-50 text-emerald-700" : value === "exception" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-800"; return <span className={`rounded-lg px-2.5 py-1 text-[10px] font-bold uppercase ${color}`}>{value.replaceAll("_", " ")}</span>; }
