"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpenCheck, Landmark, RotateCcw, Scale, ShieldCheck } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { getFinancialReports, listJournals, requestJournalReversal, type FinancialReports, type JournalItem } from "@/lib/operations";

const idr = (value: unknown) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));

export default function GeneralLedgerPage() {
  const [data, setData] = useState<{ reports: FinancialReports; journals: JournalItem[] } | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const load = useCallback(async () => { const [reports, journals] = await Promise.all([getFinancialReports(), listJournals()]); setData({ reports, journals }); }, []);
  useEffect(() => { void load().catch((reason: { detail?: string }) => setError(reason.detail ?? "General Ledger gagal dimuat")); }, [load]);
  async function reverse(item: JournalItem) {
    const reason = window.prompt(`Alasan reversal ${item.entry_no}:`);
    if (!reason) return;
    setBusy(item.id); setError(null); setNotice(null);
    try { await requestJournalReversal(item.id, reason); setNotice("Reversal dikirim ke approval inbox; jurnal belum berubah sebelum checker menyetujui."); }
    catch (reason) { setError((reason as { detail?: string }).detail ?? "Reversal gagal diajukan"); }
    finally { setBusy(null); }
  }
  if (error && !data) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Menyusun general ledger" />;
  const debit = data.reports.trial_balance.reduce((sum, item) => sum + Number(item.debit ?? 0), 0);
  const credit = data.reports.trial_balance.reduce((sum, item) => sum + Number(item.credit ?? 0), 0);
  return <div className="space-y-5">
    <header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Finance · Accounting</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">General ledger</h1><p className="mt-2 text-sm text-muted-foreground">Trial balance, journal drill-down, loan subledger, dan reversal dengan kontrol empat mata.</p></header>
    {error&&<div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice&&<div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <section className="grid gap-3 sm:grid-cols-3"><Summary label="Total debit" value={idr(debit)} icon={Landmark}/><Summary label="Total kredit" value={idr(credit)} icon={BookOpenCheck}/><Summary label="Selisih" value={idr(debit-credit)} icon={debit===credit?ShieldCheck:Scale} alert={debit!==credit}/></section>
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border px-5 py-4"><h2 className="font-bold">Trial balance</h2><p className="mt-1 text-xs text-muted-foreground">Saldo akun berdasarkan jurnal posted.</p></div><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Kode</th><th className="px-5 py-3">Nama akun</th><th className="px-5 py-3">Tipe</th><th className="px-5 py-3 text-right">Debit</th><th className="px-5 py-3 text-right">Kredit</th></tr></thead><tbody className="divide-y divide-border">{data.reports.trial_balance.map((item)=><tr key={String(item.code)}><td className="px-5 py-4 font-mono text-xs font-semibold text-primary">{String(item.code)}</td><td className="px-5 py-4 font-medium">{String(item.name)}</td><td className="px-5 py-4 capitalize text-muted-foreground">{String(item.account_type??"—")}</td><td className="px-5 py-4 text-right font-semibold">{idr(item.debit)}</td><td className="px-5 py-4 text-right font-semibold">{idr(item.credit)}</td></tr>)}</tbody></table></div></section>
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border px-5 py-4"><h2 className="font-bold">Journal register</h2><p className="mt-1 text-xs text-muted-foreground">Klik jurnal untuk memeriksa pasangan debit dan kredit.</p></div><div className="divide-y divide-border">{data.journals.map((item)=><article key={item.id}><button onClick={()=>setExpanded(expanded===item.id?null:item.id)} className="grid w-full gap-2 px-5 py-4 text-left md:grid-cols-[170px_1fr_150px_120px] md:items-center"><span className="font-mono text-xs font-bold text-primary">{item.entry_no}</span><span><b className="block text-sm">{item.description}</b><small className="text-muted-foreground">{item.event_type.replaceAll("_"," ")} · {new Date(item.posted_at).toLocaleString("id-ID")}</small></span><span className="text-right text-sm font-semibold">{idr(item.total_debit)}</span><span className="justify-self-start rounded-lg bg-surface-soft px-2 py-1 text-[10px] font-bold uppercase md:justify-self-end">{item.status}</span></button>{expanded===item.id&&<div className="border-t border-border bg-surface-soft px-5 py-4"><div className="space-y-2">{item.lines.map((line,index)=><div key={`${item.id}-${index}`} className="grid grid-cols-[1fr_120px_120px] gap-3 text-xs"><span>{line.account_code} · {line.account_name}</span><span className="text-right">D {idr(line.debit)}</span><span className="text-right">K {idr(line.credit)}</span></div>)}</div>{item.status==="posted"&&!item.reversal_of_id&&<button disabled={busy!==null} onClick={()=>reverse(item)} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-bold text-red-700"><RotateCcw className="h-4 w-4"/>Ajukan reversal</button>}</div>}</article>)}</div></section>
  </div>;
}

function Summary({label,value,icon:Icon,alert=false}:{label:string;value:string;icon:typeof Landmark;alert?:boolean}){return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className={`h-4 w-4 ${alert?"text-destructive":"text-primary"}`}/><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 truncate text-xl font-bold">{value}</p></article>}
