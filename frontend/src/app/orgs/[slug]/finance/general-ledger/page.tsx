"use client";

import { useEffect, useState } from "react";
import { BookOpenCheck, Landmark, Scale, ShieldCheck } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { getFinancialReports, type FinancialReports } from "@/lib/operations";

const idr = (value: unknown) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));

export default function GeneralLedgerPage() {
  const [data, setData] = useState<FinancialReports | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getFinancialReports().then(setData).catch((reason: { detail?: string }) => setError(reason.detail ?? "General Ledger gagal dimuat")); }, []);
  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Menyusun trial balance" />;
  const debit = data.trial_balance.reduce((sum, item) => sum + Number(item.debit ?? 0), 0);
  const credit = data.trial_balance.reduce((sum, item) => sum + Number(item.credit ?? 0), 0);
  return <div className="space-y-5"><header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Finance · Accounting</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">General Ledger</h1><p className="mt-2 text-sm text-muted-foreground">Trial balance, loan subledger, dan kontrol keseimbangan jurnal dari transaksi operasional.</p></header><section className="grid gap-3 sm:grid-cols-3"><Summary label="Total debit" value={idr(debit)} icon={Landmark} /><Summary label="Total kredit" value={idr(credit)} icon={BookOpenCheck} /><Summary label="Selisih" value={idr(debit - credit)} icon={debit === credit ? ShieldCheck : Scale} alert={debit !== credit} /></section><section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border px-5 py-4"><h2 className="font-bold">Trial balance</h2><p className="mt-1 text-xs text-muted-foreground">Saldo akun berdasarkan jurnal yang sudah diposting.</p></div><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Kode</th><th className="px-5 py-3">Nama akun</th><th className="px-5 py-3">Tipe</th><th className="px-5 py-3 text-right">Debit</th><th className="px-5 py-3 text-right">Kredit</th></tr></thead><tbody className="divide-y divide-border">{data.trial_balance.map((item) => <tr key={String(item.code)}><td className="px-5 py-4 font-mono text-xs font-semibold text-primary">{String(item.code)}</td><td className="px-5 py-4 font-medium">{String(item.name)}</td><td className="px-5 py-4 capitalize text-muted-foreground">{String(item.account_type ?? "—")}</td><td className="px-5 py-4 text-right font-semibold">{idr(item.debit)}</td><td className="px-5 py-4 text-right font-semibold">{idr(item.credit)}</td></tr>)}</tbody></table></div></section></div>;
}

function Summary({ label, value, icon: Icon, alert = false }: { label: string; value: string; icon: typeof Landmark; alert?: boolean }) { return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className={`h-4 w-4 ${alert ? "text-destructive" : "text-primary"}`} /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 truncate text-xl font-bold">{value}</p></article>; }
