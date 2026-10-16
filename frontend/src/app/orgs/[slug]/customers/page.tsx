"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, Download, Filter, IdCard, Plus, Search, ShieldCheck, Users } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listCustomers, type CustomerListItem } from "@/lib/operations";

const riskLabel: Record<string, string> = { normal: "Normal", review: "Perlu review", high: "Risiko tinggi", blocked: "Diblokir" };

export default function CustomersPage() {
  const params = useParams<{ slug: string }>();
  const slug = params?.slug as string;
  const [items, setItems] = useState<CustomerListItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCustomers().then(setItems).catch((reason: { detail?: string }) => setError(reason.detail ?? "Debitur gagal dimuat"));
  }, []);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLocaleLowerCase("id-ID");
    return (items ?? []).filter((item) => {
      const matchesRisk = risk === "all" || item.risk_status === risk || (risk === "watchlist" && item.internal_watchlist);
      const matchesQuery = !keyword || [item.full_name, item.customer_reference, item.phone_masked, item.dati_ii_code]
        .map((value) => String(value ?? "").toLocaleLowerCase("id-ID"))
        .some((value) => value.includes(keyword));
      return matchesRisk && matchesQuery;
    });
  }, [items, query, risk]);

  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat Debitur & CRM" />;

  const watchlistCount = items.filter((item) => item.internal_watchlist).length;
  const correctionCount = items.filter((item) => item.correction_status !== "none").length;
  const kycPendingCount = items.filter((item) => item.kyc_status !== "verified").length;

  return <div className="space-y-5">
    <header className="flex flex-col gap-4 border-b border-border pb-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Customer operations · CRM</p>
        <h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Debitur</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">Kelola identitas, KYC, consent, fasilitas, agunan, komunikasi, dan koreksi data debitur dalam satu rekam operasional.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Link href={`/orgs/${slug}/customers/kyc`} className="inline-flex h-10 items-center gap-2 rounded-xl border border-primary/25 bg-surface-blue px-3 text-xs font-bold text-primary"><IdCard className="h-4 w-4" />Antrean KYC</Link>
        <button type="button" className="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-surface px-3 text-xs font-semibold"><Download className="h-4 w-4" /> Ekspor terkontrol</button>
        <Link href={`/orgs/${slug}/loans/applications/new`} className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-white"><Plus className="h-4 w-4" /> Pengajuan baru</Link>
      </div>
    </header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Total debitur" value={items.length} icon={Users} tone="blue" />
      <Metric label="KYC perlu tindakan" value={kycPendingCount} icon={IdCard} tone={kycPendingCount ? "amber" : "neutral"} />
      <Metric label="Watchlist internal" value={watchlistCount} icon={AlertTriangle} tone={watchlistCount ? "red" : "neutral"} />
      <Metric label="Koreksi berjalan" value={correctionCount} icon={ShieldCheck} tone={correctionCount ? "amber" : "neutral"} />
    </section>

    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
      <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center">
        <div className="relative min-w-0 flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari nama, CIF, telepon, atau DATI II…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-4 text-sm outline-none focus:border-primary/50" /></div>
        <div className="flex items-center gap-2 overflow-x-auto"><Filter className="h-4 w-4 shrink-0 text-muted-foreground" />{[
          ["all", "Semua"], ["normal", "Normal"], ["review", "Perlu review"], ["watchlist", "Watchlist"],
        ].map(([value, label]) => <button key={value} type="button" onClick={() => setRisk(value)} className={`shrink-0 rounded-lg border px-3 py-2 text-xs font-semibold ${risk === value ? "border-primary bg-primary text-white" : "border-border bg-surface text-muted-foreground"}`}>{label}</button>)}</div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1040px] text-left text-sm">
          <thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-[0.13em] text-muted-foreground"><tr><th className="px-5 py-3">CIF / Debitur</th><th className="px-5 py-3">Kontak</th><th className="px-5 py-3">KYC</th><th className="px-5 py-3">Wilayah</th><th className="px-5 py-3">SLIK</th><th className="px-5 py-3">Risiko</th><th className="px-5 py-3">Koreksi</th><th className="w-16 px-5 py-3"><span className="sr-only">Aksi</span></th></tr></thead>
          <tbody className="divide-y divide-border/70">{filtered.map((item) => <tr key={item.id} className="group hover:bg-surface-soft/70">
            <td className="px-5 py-4"><Link href={`/orgs/${slug}/customers/${item.id}`} className="font-semibold hover:text-primary">{item.full_name}</Link><p className="mt-1 font-mono text-[11px] text-primary">{item.customer_reference}</p></td>
            <td className="px-5 py-4 text-muted-foreground">{item.phone_masked}</td>
            <td className="px-5 py-4"><Link href={`/orgs/${slug}/customers/${item.id}?tab=identity`} className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold ${item.kyc_status === "verified" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}><IdCard className="h-3.5 w-3.5" />{kycLabel(item.kyc_status)}</Link></td>
            <td className="px-5 py-4"><span className="font-medium">DATI II</span><p className="mt-1 text-xs text-muted-foreground">{item.dati_ii_code ?? "Belum dipetakan"}</p></td>
            <td className="px-5 py-4"><span className={item.slik_subject_code ? "text-foreground" : "text-warning"}>{item.slik_subject_code ?? "Perlu dilengkapi"}</span></td>
            <td className="px-5 py-4"><span className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold ${item.internal_watchlist || item.risk_status === "high" ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{item.internal_watchlist ? "Watchlist" : (riskLabel[item.risk_status] ?? item.risk_status)}</span></td>
            <td className="px-5 py-4 text-xs text-muted-foreground">{item.correction_status === "none" ? "Tidak ada" : item.correction_status}</td>
            <td className="px-5 py-4"><Link href={`/orgs/${slug}/customers/${item.id}`} aria-label={`Buka detail ${item.full_name}`} className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-surface text-muted-foreground transition group-hover:border-primary/30 group-hover:text-primary"><ArrowRight className="h-4 w-4" /></Link></td>
          </tr>)}</tbody>
        </table>
        {!filtered.length && <div className="px-6 py-14 text-center"><p className="font-semibold">Debitur tidak ditemukan</p><p className="mt-1 text-sm text-muted-foreground">Ubah pencarian atau filter risiko.</p></div>}
      </div>
      <div className="border-t border-border px-5 py-3 text-xs text-muted-foreground">Menampilkan {filtered.length} dari {items.length} debitur · Data terisolasi pada tenant aktif</div>
    </section>
  </div>;
}

function Metric({ label, value, icon: Icon, tone }: { label: string; value: number; icon: typeof Users; tone: "blue" | "red" | "amber" | "neutral" }) {
  const tones = { blue: "bg-blue-50 text-blue-700", red: "bg-red-50 text-red-700", amber: "bg-amber-50 text-amber-700", neutral: "bg-surface-soft text-muted-foreground" };
  return <article className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-4"><span className={`grid h-10 w-10 place-items-center rounded-xl ${tones[tone]}`}><Icon className="h-5 w-5" /></span><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-xl font-bold tabular-nums">{value}</p></div></article>;
}

function kycLabel(status: string) {
  const labels: Record<string, string> = { not_started: "Mulai KYC", pending_documents: "Dokumen", pending_review: "Menunggu checker", needs_information: "Perlu data", verified: "Terverifikasi", expired: "Kedaluwarsa", rejected: "Ditolak" };
  return labels[status] ?? status.replaceAll("_", " ");
}
