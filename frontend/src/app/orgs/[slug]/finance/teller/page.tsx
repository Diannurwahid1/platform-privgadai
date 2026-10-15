"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Banknote,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  Landmark,
  LockKeyhole,
  Scale,
} from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  closeTellerSession,
  getFinanceOverview,
  listCashboxes,
  listTellerSessions,
  openTellerSession,
  type FinanceOverview,
} from "@/lib/operations";

type Row = Record<string, unknown>;
type TellerData = { overview: FinanceOverview; cashboxes: Row[]; sessions: Row[] };

const idr = (value: unknown) =>
  new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(Number(value ?? 0));

const statusLabels: Record<string, string> = {
  open: "Aktif",
  closed: "Sesuai",
  variance_pending: "Menunggu approval",
  closed_with_variance: "Selisih disetujui",
};

export default function TellerPage() {
  const [data, setData] = useState<TellerData | null>(null);
  const [actual, setActual] = useState<Record<string, string>>({});
  const [varianceReasons, setVarianceReasons] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [overview, cashboxes, sessions] = await Promise.all([
      getFinanceOverview(),
      listCashboxes(),
      listTellerSessions(),
    ]);
    setData({ overview, cashboxes, sessions });
  }, []);

  useEffect(() => {
    load().catch((reason: { detail?: string }) =>
      setError(reason.detail ?? "Teller workspace gagal dimuat"),
    );
  }, [load]);

  const cashboxById = useMemo(
    () => new Map(data?.cashboxes.map((item) => [String(item.id), item]) ?? []),
    [data?.cashboxes],
  );

  async function open(cashboxId: string) {
    setBusy(`open-${cashboxId}`);
    setError(null);
    try {
      await openTellerSession(cashboxId);
      setNotice("Sesi teller dibuka. Saldo awal dicatat untuk rekonsiliasi akhir shift.");
      await load();
    } catch (reason) {
      setError((reason as { detail?: string }).detail ?? "Sesi teller gagal dibuka");
    } finally {
      setBusy(null);
    }
  }

  async function close(session: Row) {
    const sessionId = String(session.id);
    const balance = Number(actual[sessionId]);
    const expected = Number(cashboxById.get(String(session.cashbox_id))?.balance ?? 0);
    const reason = varianceReasons[sessionId]?.trim();
    if (!Number.isFinite(balance) || balance < 0) {
      setError("Masukkan hasil hitung kas aktual.");
      return;
    }
    if (balance !== expected && (!reason || reason.length < 5)) {
      setError("Selisih kas wajib disertai alasan minimal 5 karakter.");
      return;
    }
    setBusy(`close-${sessionId}`);
    setError(null);
    try {
      const result = await closeTellerSession(sessionId, balance, reason);
      setNotice(
        result.status === "variance_pending"
          ? "Cash count selesai. Selisih kas menunggu approval branch manager."
          : "Sesi ditutup dan hasil cash count sesuai.",
      );
      setActual((current) => ({ ...current, [sessionId]: "" }));
      setVarianceReasons((current) => ({ ...current, [sessionId]: "" }));
      await load();
    } catch (reasonValue) {
      setError((reasonValue as { detail?: string }).detail ?? "Sesi teller gagal ditutup");
    } finally {
      setBusy(null);
    }
  }

  if (!data) return error ? <ErrorState message={error} /> : <LoadingState label="Membuka teller dan cashbox" />;

  const openSessions = data.sessions.filter((item) => item.status === "open");
  const pendingVariance = data.sessions.filter((item) => item.status === "variance_pending").length;

  return (
    <div className="space-y-5">
      <header className="border-b border-border pb-5">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Finance · Teller</p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Teller & Cash Control</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Kendalikan kepemilikan cashbox, cash count akhir shift, selisih, dan approval supervisor.
        </p>
      </header>

      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Summary label="Saldo kas" value={idr(data.overview.cash_balance)} icon={Landmark} />
        <Summary label="Pembayaran hari ini" value={idr(data.overview.payment_today)} icon={CircleDollarSign} />
        <Summary label="Sesi aktif" value={String(data.overview.open_teller_sessions)} icon={Clock3} />
        <Summary label="Selisih menunggu approval" value={String(pendingVariance)} icon={AlertTriangle} attention={pendingVariance > 0} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel title="Cashbox cabang" subtitle="Satu cashbox hanya dapat dikuasai satu teller aktif.">
          {data.cashboxes.map((item) => {
            const session = openSessions.find((row) => String(row.cashbox_id) === String(item.id));
            return (
              <div key={String(item.id)} className="flex items-center gap-3 rounded-xl border border-border bg-surface-soft p-3">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-surface-blue text-primary"><Banknote className="h-4 w-4" /></span>
                <div className="min-w-0 flex-1"><p className="text-sm font-semibold">{String(item.code)} · {String(item.name)}</p><p className="mt-1 text-xs text-muted-foreground">Saldo buku {idr(item.balance)}</p></div>
                {session ? (
                  <span className="inline-flex items-center gap-1 rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700"><LockKeyhole className="h-3.5 w-3.5" /> Dikuasai teller</span>
                ) : (
                  <button type="button" disabled={busy !== null} onClick={() => open(String(item.id))} className="h-9 rounded-lg bg-primary px-3 text-xs font-bold text-white disabled:opacity-50">{busy === `open-${String(item.id)}` ? "Membuka…" : "Buka sesi"}</button>
                )}
              </div>
            );
          })}
        </Panel>

        <Panel title="Cash count akhir shift" subtitle="Saldo buku dikunci saat rekonsiliasi diproses.">
          {openSessions.map((item) => {
            const sessionId = String(item.id);
            const expected = cashboxById.get(String(item.cashbox_id))?.balance ?? 0;
            const entered = actual[sessionId];
            const hasVariance = entered !== undefined && entered !== "" && Number(entered) !== Number(expected);
            return (
              <div key={sessionId} className="rounded-xl border border-border bg-surface-soft p-4">
                <div className="grid gap-3 sm:grid-cols-3"><Definition label="Saldo awal" value={idr(item.opening_balance)} /><Definition label="Saldo buku" value={idr(expected)} /><Definition label="Dibuka" value={new Date(String(item.opened_at)).toLocaleString("id-ID")} /></div>
                <div className="mt-4 grid gap-2 sm:grid-cols-[0.7fr_1.3fr_auto]">
                  <input inputMode="numeric" value={actual[sessionId] ?? ""} onChange={(event) => setActual((current) => ({ ...current, [sessionId]: event.target.value }))} placeholder="Kas aktual" className="h-10 min-w-0 rounded-xl border border-border bg-surface px-3 text-sm" />
                  <input value={varianceReasons[sessionId] ?? ""} onChange={(event) => setVarianceReasons((current) => ({ ...current, [sessionId]: event.target.value }))} placeholder={hasVariance ? "Alasan selisih (wajib)" : "Alasan selisih bila ada"} className={`h-10 min-w-0 rounded-xl border bg-surface px-3 text-sm ${hasVariance ? "border-amber-400" : "border-border"}`} />
                  <button type="button" disabled={busy !== null} onClick={() => close(item)} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-primary px-3 text-xs font-bold text-primary disabled:opacity-50"><Scale className="h-4 w-4" /> Rekonsiliasi</button>
                </div>
                {hasVariance && <p className="mt-2 text-xs font-medium text-amber-700">Selisih {idr(Number(entered) - Number(expected))} akan dikirim ke branch manager.</p>}
              </div>
            );
          })}
          {!openSessions.length && <Empty text="Tidak ada sesi teller terbuka." />}
        </Panel>
      </section>

      <Panel title="Riwayat rekonsiliasi" subtitle="50 sesi terbaru beserta jejak selisih dan approval.">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[840px] text-left text-sm">
            <thead className="border-b border-border text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-3 py-3">Waktu</th><th className="px-3 py-3">Cashbox</th><th className="px-3 py-3 text-right">Expected</th><th className="px-3 py-3 text-right">Aktual</th><th className="px-3 py-3 text-right">Selisih</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Alasan</th></tr></thead>
            <tbody className="divide-y divide-border">
              {data.sessions.map((item) => (
                <tr key={String(item.id)}>
                  <td className="px-3 py-3 text-xs">{new Date(String(item.opened_at)).toLocaleString("id-ID")}</td>
                  <td className="px-3 py-3 font-semibold">{String(cashboxById.get(String(item.cashbox_id))?.code ?? String(item.cashbox_id).slice(0, 8))}</td>
                  <td className="px-3 py-3 text-right">{item.expected_closing_balance == null ? "—" : idr(item.expected_closing_balance)}</td>
                  <td className="px-3 py-3 text-right">{item.actual_closing_balance == null ? "—" : idr(item.actual_closing_balance)}</td>
                  <td className={`px-3 py-3 text-right font-semibold ${Number(item.variance_amount ?? 0) ? "text-amber-700" : ""}`}>{item.variance_amount == null ? "—" : idr(item.variance_amount)}</td>
                  <td className="px-3 py-3"><Status value={String(item.status)} /></td>
                  <td className="max-w-64 px-3 py-3 text-xs text-muted-foreground">{String(item.variance_reason ?? "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function Summary({ label, value, icon: Icon, attention = false }: { label: string; value: string; icon: typeof Landmark; attention?: boolean }) {
  return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className={`h-4 w-4 ${attention ? "text-amber-600" : "text-primary"}`} /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 truncate text-lg font-bold">{value}</p></article>;
}
function Panel({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="font-bold">{title}</h2><p className="mt-1 text-xs text-muted-foreground">{subtitle}</p><div className="mt-5 space-y-3">{children}</div></article>;
}
function Definition({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-xs font-semibold">{value}</p></div>;
}
function Status({ value }: { value: string }) {
  const pending = value === "variance_pending";
  return <span className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold ${pending ? "bg-amber-50 text-amber-700" : value === "open" ? "bg-blue-50 text-blue-700" : "bg-emerald-50 text-emerald-700"}`}>{pending ? <AlertTriangle className="h-3 w-3" /> : <CheckCircle2 className="h-3 w-3" />}{statusLabels[value] ?? value}</span>;
}
function Empty({ text }: { text: string }) {
  return <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">{text}</div>;
}
