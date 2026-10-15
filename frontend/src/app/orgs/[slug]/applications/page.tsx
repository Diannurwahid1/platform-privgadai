"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ClipboardList, Plus, Search, SlidersHorizontal } from "lucide-react";
import { motion } from "framer-motion";
import {
  listApplications,
  type ApplicationQueueItem,
} from "@/lib/operations";
import { ErrorState, LoadingState } from "@/components/page-state";

const statusLabels: Record<string, string> = {
  submitted: "Baru masuk",
  under_review: "Dalam review",
  appraisal: "Penaksiran",
  offered: "Ditawarkan",
  accepted: "Disetujui",
  rejected: "Ditolak",
  cancelled: "Dibatalkan",
};

function idr(value: number) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function ApplicationsInboxPage() {
  const { slug } = useParams<{ slug: string }>();
  const [applications, setApplications] = useState<ApplicationQueueItem[] | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");

  useEffect(() => {
    listApplications()
      .then(setApplications)
      .catch((err: { detail?: string }) =>
        setError(err.detail ?? "Inbox pengajuan gagal dimuat"),
      );
  }, []);

  const filtered = useMemo(() => {
    if (!applications) return [];
    const normalized = query.trim().toLowerCase();
    return applications.filter((item) => {
      const matchesQuery =
        !normalized ||
        item.application_no.toLowerCase().includes(normalized) ||
        item.borrower_name.toLowerCase().includes(normalized) ||
        item.asset_label.toLowerCase().includes(normalized);
      return matchesQuery && (status === "all" || item.status === status);
    });
  }, [applications, query, status]);

  if (error) return <ErrorState message={error} />;
  if (!applications) return <LoadingState label="Membuka inbox pengajuan" />;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <header className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
            Loan application · P0 Blueprint
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.045em] sm:text-4xl">
            Inbox pengajuan
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Triase pengajuan nasabah sebelum masuk ke appraisal manusia.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/orgs/${slug}/applications/new`} className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-xs font-bold text-white">
            <Plus className="h-4 w-4" /> Pengajuan baru
          </Link>
          <div className="inline-flex items-center gap-2 rounded-full border border-success/25 bg-success/8 px-3 py-2 text-xs font-semibold text-success">
            <span className="h-2 w-2 rounded-full bg-success" />
            Tenant isolation aktif
          </div>
        </div>
      </header>

      <section className="rounded-[var(--pg-radius-lg)] border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Cari nomor, nasabah, atau barang..."
              className="h-11 w-full rounded-xl border border-border bg-background pl-10 pr-4 text-sm outline-none focus:border-primary/50 focus:ring-4 focus:ring-primary/8"
            />
          </div>
          <div className="flex items-center gap-2 overflow-x-auto">
            <SlidersHorizontal className="h-4 w-4 shrink-0 text-muted-foreground" />
            {["all", "submitted", "under_review", "appraisal", "offered", "accepted"].map(
              (item) => (
                <button
                  key={item}
                  onClick={() => setStatus(item)}
                  className={`shrink-0 rounded-full border px-3 py-2 text-xs font-semibold transition ${status === item ? "border-primary bg-primary text-white" : "border-border bg-surface text-muted-foreground hover:border-primary/35"}`}
                >
                  {item === "all" ? "Semua" : statusLabels[item]}
                </button>
              ),
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left">
            <thead>
              <tr className="border-b border-border bg-surface-soft/70 text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                <th className="px-5 py-3 font-semibold">Nomor</th>
                <th className="px-5 py-3 font-semibold">Nasabah</th>
                <th className="px-5 py-3 font-semibold">Barang</th>
                <th className="px-5 py-3 font-semibold">Cabang</th>
                <th className="px-5 py-3 font-semibold">Nilai diminta</th>
                <th className="px-5 py-3 font-semibold">Status</th>
                <th className="px-5 py-3 font-semibold">Prioritas</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-border/70 text-sm last:border-0 hover:bg-surface-soft"
                >
                  <td className="px-5 py-4 font-mono text-xs font-semibold text-primary">
                    <Link className="hover:underline" href={`/orgs/${slug}/applications/${item.id}`}>
                      {item.application_no}
                    </Link>
                  </td>
                  <td className="px-5 py-4">
                    <p className="font-semibold">{item.borrower_name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.phone_masked}
                    </p>
                  </td>
                  <td className="px-5 py-4">
                    <p className="font-medium">{item.asset_label}</p>
                    <p className="mt-1 text-xs capitalize text-muted-foreground">
                      {item.asset_category}
                    </p>
                  </td>
                  <td className="px-5 py-4">
                    <span className="rounded-full bg-surface-blue px-2.5 py-1 text-xs font-bold text-primary">
                      {item.branch_code}
                    </span>
                  </td>
                  <td className="px-5 py-4 font-semibold">
                    {idr(item.requested_amount)}
                  </td>
                  <td className="px-5 py-4">
                    <span className="rounded-full border border-border bg-background px-2.5 py-1 text-xs font-semibold">
                      {statusLabels[item.status] ?? item.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${item.priority === "high" ? "bg-red-50 text-red-700" : "bg-surface-soft text-muted-foreground"}`}
                    >
                      {item.priority === "high" ? "Tinggi" : "Normal"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div className="grid place-items-center px-6 py-16 text-center">
              <ClipboardList className="h-9 w-9 text-muted-foreground/40" />
              <p className="mt-3 text-sm font-semibold">Tidak ada hasil</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Ubah kata pencarian atau filter status.
              </p>
            </div>
          )}
        </div>
        <div className="border-t border-border px-5 py-3 text-xs text-muted-foreground">
          Menampilkan {filtered.length} dari {applications.length} pengajuan
        </div>
      </section>
    </motion.div>
  );
}

