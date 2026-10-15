"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  CircleDollarSign,
  ClipboardCheck,
  Clock3,
  PackageCheck,
  ScanSearch,
  Sparkles,
} from "lucide-react";
import { motion } from "framer-motion";
import { useOrgContext } from "@/lib/org-context";
import {
  getOperationsDashboard,
  type ApplicationQueueItem,
  type OperationsDashboard,
} from "@/lib/operations";
import { ErrorState, LoadingState } from "@/components/page-state";

const statusLabel: Record<string, string> = {
  draft: "Draf",
  submitted: "Baru masuk",
  under_review: "Dalam review",
  appraisal: "Penaksiran",
  offered: "Ditawarkan",
  accepted: "Disetujui",
  rejected: "Ditolak",
  cancelled: "Dibatalkan",
};

const collateralLabel: Record<string, string> = {
  with_customer: "Pada nasabah",
  pickup_assigned: "Pickup ditugaskan",
  in_transit: "Dalam perjalanan",
  received: "Diterima",
  stored: "Tersimpan",
  incident_hold: "Ditahan",
  returned: "Dikembalikan",
};

function formatIdr(value: number, compact = false) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
    notation: compact ? "compact" : "standard",
  }).format(value);
}

function formatDate(value: string | null) {
  if (!value) return "Belum dikirim";
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function StatusBadge({ status }: { status: string }) {
  const tones: Record<string, string> = {
    submitted: "border-blue-200 bg-blue-50 text-blue-700",
    under_review: "border-amber-200 bg-amber-50 text-amber-700",
    appraisal: "border-violet-200 bg-violet-50 text-violet-700",
    offered: "border-cyan-200 bg-cyan-50 text-cyan-700",
    accepted: "border-emerald-200 bg-emerald-50 text-emerald-700",
    rejected: "border-red-200 bg-red-50 text-red-700",
  };
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.08em] ${tones[status] ?? "border-border bg-muted text-muted-foreground"}`}
    >
      {statusLabel[status] ?? status.replaceAll("_", " ")}
    </span>
  );
}

function QueueTable({
  items,
  slug,
}: {
  items: ApplicationQueueItem[];
  slug: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-left">
        <thead>
          <tr className="border-b border-border text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            <th className="px-5 py-3 font-semibold">Pengajuan</th>
            <th className="px-5 py-3 font-semibold">Barang</th>
            <th className="px-5 py-3 font-semibold">Cabang</th>
            <th className="px-5 py-3 font-semibold">Nilai diminta</th>
            <th className="px-5 py-3 font-semibold">Status</th>
            <th className="px-5 py-3 text-right font-semibold">Masuk</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className="border-b border-border/75 transition last:border-0 hover:bg-surface-soft"
            >
              <td className="px-5 py-4">
                <div className="flex items-center gap-3">
                  <span className="grid h-9 w-9 place-items-center rounded-xl bg-surface-blue text-xs font-bold text-primary">
                    {item.borrower_name
                      .split(" ")
                      .map((part) => part[0])
                      .slice(0, 2)
                      .join("")}
                  </span>
                  <div>
                    <p className="text-sm font-semibold">{item.borrower_name}</p>
                    <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                      {item.application_no}
                    </p>
                  </div>
                </div>
              </td>
              <td className="px-5 py-4">
                <p className="text-sm font-medium">{item.asset_label}</p>
                <p className="mt-0.5 text-xs capitalize text-muted-foreground">
                  {item.asset_category}
                </p>
              </td>
              <td className="px-5 py-4">
                <p className="text-xs font-semibold">{item.branch_code}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {item.branch_name}
                </p>
              </td>
              <td className="px-5 py-4 text-sm font-semibold">
                {formatIdr(item.requested_amount)}
              </td>
              <td className="px-5 py-4">
                <StatusBadge status={item.status} />
              </td>
              <td className="px-5 py-4 text-right text-xs text-muted-foreground">
                {formatDate(item.submitted_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {items.length === 0 && (
        <div className="px-6 py-12 text-center text-sm text-muted-foreground">
          Belum ada pengajuan pada tenant ini.
        </div>
      )}
      <div className="border-t border-border bg-surface-soft/70 px-5 py-3">
        <Link
          href={`/orgs/${slug}/applications`}
          className="inline-flex items-center gap-2 text-xs font-semibold text-primary hover:underline"
        >
          Lihat seluruh pengajuan <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}

export default function PartnerOperationsDashboard() {
  const { org } = useOrgContext();
  const [dashboard, setDashboard] = useState<OperationsDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOperationsDashboard()
      .then(setDashboard)
      .catch((err: { detail?: string }) =>
        setError(err.detail ?? "Dashboard operasional gagal dimuat"),
      );
  }, []);

  const pipeline = useMemo(() => {
    if (!dashboard) return [];
    const { metrics } = dashboard;
    return [
      { label: "Masuk", value: metrics.submitted, color: "bg-blue-500" },
      { label: "Review", value: metrics.under_review, color: "bg-amber-500" },
      { label: "Appraisal", value: metrics.appraisal, color: "bg-violet-500" },
      { label: "Ditawarkan", value: metrics.offered, color: "bg-cyan-500" },
      { label: "Diterima", value: metrics.accepted, color: "bg-emerald-500" },
    ];
  }, [dashboard]);

  if (error) return <ErrorState message={error} />;
  if (!dashboard) return <LoadingState label="Memuat operasi hari ini" />;

  const metricCards = [
    {
      label: "Pengajuan baru",
      value: dashboard.metrics.submitted,
      detail: "Menunggu triase awal",
      icon: ClipboardCheck,
      tone: "text-blue-600 bg-blue-50",
    },
    {
      label: "Dalam review",
      value: dashboard.metrics.under_review,
      detail: "Perlu verifikasi petugas",
      icon: Clock3,
      tone: "text-amber-600 bg-amber-50",
    },
    {
      label: "Antrean appraisal",
      value: dashboard.metrics.appraisal,
      detail: "Keputusan penaksir manusia",
      icon: ScanSearch,
      tone: "text-violet-600 bg-violet-50",
    },
    {
      label: "Nilai pengajuan",
      value: formatIdr(dashboard.metrics.requested_amount, true),
      detail: "Total selain status draf",
      icon: CircleDollarSign,
      tone: "text-emerald-600 bg-emerald-50",
    },
  ];

  const collateralTotal = dashboard.collateral.reduce(
    (sum, item) => sum + item.count,
    0,
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <section className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-surface-blue px-3 py-1 text-[10px] font-bold uppercase tracking-[0.15em] text-primary">
              Partner Operations
            </span>
            <span className="rounded-full border border-success/25 bg-success/8 px-3 py-1 text-[10px] font-semibold text-success">
              Data demo sintetis
            </span>
          </div>
          <h1 className="text-3xl font-bold tracking-[-0.045em] sm:text-4xl">
            Selamat datang di {org?.name}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Pantau pengajuan, keputusan penaksir, dan pergerakan barang jaminan
            dari satu ruang kerja yang dapat diaudit.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {dashboard.branches.map((branch, index) => (
            <button
              key={branch.id}
              className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${index === 0 ? "border-primary bg-primary text-white" : "border-border bg-surface text-muted-foreground hover:border-primary/40"}`}
            >
              {branch.code}
            </button>
          ))}
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-4">
        {metricCards.map((metric) => {
          const Icon = metric.icon;
          return (
            <article
              key={metric.label}
              className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-medium text-muted-foreground">
                    {metric.label}
                  </p>
                  <p className="mt-3 text-3xl font-bold tracking-[-0.04em]">
                    {metric.value}
                  </p>
                </div>
                <span className={`grid h-10 w-10 place-items-center rounded-xl ${metric.tone}`}>
                  <Icon className="h-5 w-5" />
                </span>
              </div>
              <p className="mt-4 border-t border-border pt-3 text-[11px] text-muted-foreground">
                {metric.detail}
              </p>
            </article>
          );
        })}
      </section>

      <section className="grid gap-5 2xl:grid-cols-[minmax(0,1.65fr)_minmax(330px,0.7fr)]">
        <article className="overflow-hidden rounded-[var(--pg-radius-lg)] border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
          <div className="flex items-center justify-between gap-4 border-b border-border px-5 py-4">
            <div>
              <h2 className="font-bold tracking-tight">Antrean tindakan</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Pengajuan terbaru lintas cabang berdasarkan waktu masuk
              </p>
            </div>
            <span className="rounded-full bg-surface-blue px-2.5 py-1 text-[10px] font-bold text-primary">
              {dashboard.work_queue.length} item
            </span>
          </div>
          <QueueTable items={dashboard.work_queue} slug={org?.slug ?? ""} />
        </article>

        <div className="space-y-5">
          <article className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-bold tracking-tight">Pipeline pengajuan</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  State machine aplikasi
                </p>
              </div>
              <Sparkles className="h-5 w-5 text-primary" />
            </div>
            <div className="mt-5 space-y-4">
              {pipeline.map((item) => {
                const max = Math.max(...pipeline.map((step) => step.value), 1);
                const width = Math.max((item.value / max) * 100, item.value ? 12 : 3);
                return (
                  <div key={item.label}>
                    <div className="mb-1.5 flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">{item.label}</span>
                      <span className="font-bold">{item.value}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full ${item.color}`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </article>

          <article className="rounded-[var(--pg-radius-lg)] bg-[linear-gradient(145deg,var(--pg-navy-900),#0b3b7b)] p-5 text-white shadow-[var(--pg-shadow-lg)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-blue-200">Collateral Passport</p>
                <p className="mt-2 text-3xl font-bold">{collateralTotal}</p>
              </div>
              <PackageCheck className="h-9 w-9 text-blue-300" />
            </div>
            <div className="mt-5 grid grid-cols-2 gap-2">
              {dashboard.collateral.slice(0, 4).map((item) => (
                <div key={item.status} className="rounded-xl bg-white/7 p-3">
                  <p className="text-lg font-bold">{item.count}</p>
                  <p className="mt-1 text-[10px] leading-4 text-blue-100/70">
                    {collateralLabel[item.status] ?? item.status}
                  </p>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <article className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-bold tracking-tight">Aktivitas terbaru</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Jejak status domain yang tersimpan di PostgreSQL
              </p>
            </div>
            <CheckCircle2 className="h-5 w-5 text-success" />
          </div>
          <div className="mt-5 space-y-1">
            {dashboard.recent_activity.map((activity) => (
              <div
                key={activity.id}
                className="flex gap-3 rounded-xl px-2 py-3 transition hover:bg-surface-soft"
              >
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary ring-4 ring-primary/10" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-mono text-[11px] font-semibold text-primary">
                      {activity.application_no}
                    </p>
                    <time className="text-[10px] text-muted-foreground">
                      {formatDate(activity.created_at)}
                    </time>
                  </div>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    Status menjadi{" "}
                    <strong className="text-foreground">
                      {statusLabel[activity.to_status] ?? activity.to_status}
                    </strong>
                    {activity.note ? ` · ${activity.note}` : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-[var(--pg-radius-lg)] border border-amber-200 bg-amber-50/70 p-5 shadow-[var(--pg-shadow-sm)]">
          <div className="flex items-start gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-amber-100 text-amber-700">
              <AlertTriangle className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-bold tracking-tight text-amber-950">
                Perlu perhatian
              </h2>
              <p className="mt-1 text-xs leading-5 text-amber-800/75">
                {dashboard.metrics.exceptions} pengajuan berada pada status
                exception. Setiap penyelesaian memerlukan alasan dan jejak audit.
              </p>
            </div>
          </div>
          <button className="mt-5 inline-flex items-center gap-2 text-xs font-bold text-amber-800">
            Tinjau exception <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </article>
      </section>
    </motion.div>
  );
}

