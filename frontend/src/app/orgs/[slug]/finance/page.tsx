"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Banknote, BookOpenCheck, CircleDollarSign, Clock3, HandCoins, Landmark } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  closeTellerSession,
  getFinanceOverview,
  getFinancialReports,
  listCashboxes,
  listCollections,
  listTellerSessions,
  openTellerSession,
  type FinanceOverview,
  type FinancialReports,
} from "@/lib/operations";

type FinanceData = {
  overview: FinanceOverview;
  reports: FinancialReports;
  cashboxes: Array<Record<string, unknown>>;
  sessions: Array<Record<string, unknown>>;
  collections: Array<Record<string, unknown>>;
};

const idr = (value: unknown) =>
  new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(
    Number(value ?? 0),
  );

export default function FinancePage() {
  const [data, setData] = useState<FinanceData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actualBalances, setActualBalances] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [overview, reports, cashboxes, sessions, collections] = await Promise.all([
      getFinanceOverview(),
      getFinancialReports(),
      listCashboxes(),
      listTellerSessions(),
      listCollections(),
    ]);
    setData({ overview, reports, cashboxes, sessions, collections });
  }, []);

  useEffect(() => {
    load().catch((reason: { detail?: string }) => setError(reason.detail ?? "Modul finance gagal dimuat"));
  }, [load]);

  async function openSession(cashboxId: string) {
    setBusy(`open-${cashboxId}`);
    setNotice(null);
    try {
      await openTellerSession(cashboxId);
      setNotice("Sesi teller dibuka dan saldo awal dikunci untuk rekonsiliasi.");
      await load();
    } catch (reason) {
      setError((reason as { detail?: string }).detail ?? "Sesi teller gagal dibuka");
    } finally {
      setBusy(null);
    }
  }

  async function closeSession(sessionId: string) {
    const actual = Number(actualBalances[sessionId]);
    if (!Number.isFinite(actual) || actual < 0) {
      setError("Masukkan hasil hitung kas aktual sebelum menutup sesi teller.");
      return;
    }
    setBusy(`close-${sessionId}`);
    setNotice(null);
    try {
      const result = await closeTellerSession(sessionId, actual);
      setNotice(
        result.status === "variance"
          ? "Sesi ditutup dengan variance dan harus ditindaklanjuti."
          : "Sesi teller ditutup dengan saldo sesuai.",
      );
      await load();
    } catch (reason) {
      setError((reason as { detail?: string }).detail ?? "Sesi teller gagal ditutup");
    } finally {
      setBusy(null);
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Membuka teller, subledger, dan general ledger" />;

  const cards = [
    ["Saldo kas", idr(data.overview.cash_balance), Landmark],
    ["Piutang pokok", idr(data.overview.outstanding_principal), CircleDollarSign],
    ["Pembayaran hari ini", idr(data.overview.payment_today), HandCoins],
    ["Sesi teller terbuka", String(data.overview.open_teller_sessions), Clock3],
  ] as const;
  const openSessions = data.sessions.filter((item) => item.status === "open");

  return (
    <div className="space-y-6">
      <header>
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Finance operations</p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Teller, kas, dan General Ledger</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Pencairan dan pembayaran memposting loan subledger, mutasi kas, serta jurnal double-entry dalam satu
          transaksi PostgreSQL.
        </p>
      </header>

      {notice && <div className="rounded-xl border border-success/20 bg-success/8 p-3 text-sm text-success">{notice}</div>}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value, Icon]) => (
          <article key={label} className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
            <Icon className="h-5 w-5 text-primary" />
            <p className="mt-4 text-xs text-muted-foreground">{label}</p>
            <p className="mt-1 text-xl font-bold">{value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <Panel title="Cashbox cabang" icon={Banknote}>
          {data.cashboxes.map((item) => (
            <div key={String(item.id)} className="flex items-center gap-3 rounded-xl bg-surface-soft p-3 text-xs">
              <div className="flex-1">
                <strong className="text-primary">{String(item.code)}</strong>
                <p className="mt-1 text-muted-foreground">{String(item.name)} · {idr(item.balance)}</p>
              </div>
              <button
                onClick={() => openSession(String(item.id))}
                disabled={busy !== null}
                className="rounded-lg bg-primary px-3 py-2 font-semibold text-primary-foreground disabled:opacity-50"
              >
                {busy === `open-${String(item.id)}` ? "Membuka…" : "Buka teller"}
              </button>
            </div>
          ))}
        </Panel>

        <Panel title="Rekonsiliasi teller" icon={Clock3}>
          {openSessions.map((item) => (
            <div key={String(item.id)} className="rounded-xl bg-surface-soft p-3 text-xs">
              <div className="flex items-center justify-between gap-3">
                <span>Saldo awal</span><strong>{idr(item.opening_balance)}</strong>
              </div>
              <div className="mt-3 flex gap-2">
                <input
                  inputMode="numeric"
                  value={actualBalances[String(item.id)] ?? ""}
                  onChange={(event) =>
                    setActualBalances((current) => ({ ...current, [String(item.id)]: event.target.value }))
                  }
                  placeholder="Hasil hitung kas aktual"
                  className="h-9 min-w-0 flex-1 rounded-lg border border-border bg-surface px-3"
                />
                <button
                  onClick={() => closeSession(String(item.id))}
                  disabled={busy !== null}
                  className="rounded-lg border border-primary px-3 font-semibold text-primary disabled:opacity-50"
                >
                  Tutup sesi
                </button>
              </div>
            </div>
          ))}
          {!openSessions.length && <p className="text-xs text-muted-foreground">Tidak ada sesi teller terbuka.</p>}
        </Panel>

        <Panel title="Loan portfolio" icon={CircleDollarSign}>
          <Row left="Pinjaman" center="Total rekening" right={String(data.reports.loan_portfolio.loan_count ?? 0)} />
          <Row left="Pokok" center="Nilai penyaluran" right={idr(data.reports.loan_portfolio.principal)} />
          <Row left="Outstanding" center="Saldo berjalan" right={idr(data.reports.loan_portfolio.outstanding)} />
          <Row left="Paid" center="Pembayaran" right={idr(data.reports.loan_portfolio.paid)} />
        </Panel>

        <Panel title="Trial balance" icon={BookOpenCheck}>
          {data.reports.trial_balance.map((item) => (
            <Row key={String(item.code)} left={String(item.code)} center={String(item.name)} right={`${idr(item.debit)} / ${idr(item.credit)}`} />
          ))}
        </Panel>

        <Panel title="Collections & aging" icon={HandCoins}>
          {data.collections.map((item) => (
            <Row key={String(item.id)} left={String(item.application_no)} center={`${String(item.aging_bucket)} · ${String(item.status)}`} right={idr(item.outstanding_amount)} />
          ))}
          {!data.collections.length && <p className="text-xs text-muted-foreground">Belum ada rekening aktif.</p>}
        </Panel>
      </section>
    </div>
  );
}

function Panel({ title, icon: Icon, children }: { title: string; icon: typeof Banknote; children: ReactNode }) {
  return (
    <article className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
      <div className="flex items-center gap-2"><Icon className="h-5 w-5 text-primary" /><h2 className="font-bold">{title}</h2></div>
      <div className="mt-4 space-y-2">{children}</div>
    </article>
  );
}

function Row({ left, center, right }: { left: string; center: string; right: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-surface-soft px-3 py-3 text-xs">
      <strong className="w-24 text-primary">{left}</strong><span className="flex-1">{center}</span><span className="font-semibold">{right}</span>
    </div>
  );
}
