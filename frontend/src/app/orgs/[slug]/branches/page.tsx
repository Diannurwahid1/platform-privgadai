"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, Building2, MapPin, Users, Vault } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listBranchOverview, type BranchOverviewItem } from "@/lib/operations";

const idr = (amount: number) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(amount);

export default function BranchesPage() {
  const { slug } = useParams<{ slug: string }>();
  const [branches, setBranches] = useState<BranchOverviewItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listBranchOverview().then(setBranches).catch((reason: { detail?: string }) => setError(reason.detail ?? "Daftar cabang gagal dimuat"));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!branches) return <LoadingState label="Memuat lima cabang operasional" />;

  return <div className="space-y-6">
    <header className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Jaringan cabang</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Daftar cabang</h1><p className="mt-2 text-sm text-muted-foreground">Buka cabang untuk melihat pengajuan, petugas, kas, dan penyimpanan yang tercatat.</p></div>
      <span className="inline-flex items-center gap-2 self-start rounded-full border border-border bg-surface px-4 py-2 text-xs font-semibold"><Building2 className="h-4 w-4 text-primary" /> {branches.length} cabang</span>
    </header>
    <div className="grid gap-4 lg:grid-cols-2">
      {branches.map((branch) => {
        const primary = slug === "murah-gadai-jogja" && branch.code === "01-UAD-K4";
        return <Link key={branch.id} href={`/orgs/${slug}/branches/${branch.id}`} className="group rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)] transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-[var(--pg-shadow-lg)]">
          <div className="flex items-start justify-between gap-4"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-surface-blue text-primary"><Building2 className="h-5 w-5" /></span><span className="flex items-center gap-2 text-[11px] font-semibold text-primary">Detail <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-1" /></span></div>
          <div className="mt-4 flex flex-wrap items-center gap-2"><span className="rounded-lg bg-surface-soft px-2 py-1 font-mono text-[11px] font-semibold text-muted-foreground">{branch.code}</span>{primary && <span className="rounded-lg bg-blue-50 px-2 py-1 text-[11px] font-bold text-blue-700">Cabang utama</span>}{!branch.is_active && <span className="rounded-lg bg-amber-50 px-2 py-1 text-[11px] font-bold text-amber-700">Nonaktif</span>}</div>
          <h2 className="mt-3 text-lg font-bold leading-6">{branch.name}</h2><p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground"><MapPin className="h-3.5 w-3.5" /> {branch.address || branch.city}</p>
          <div className="mt-5 grid grid-cols-3 gap-3 border-t border-border pt-4"><div><p className="text-xl font-bold">{branch.application_count}</p><p className="text-[11px] text-muted-foreground">Pengajuan</p></div><div><p className="flex items-center gap-1 text-xl font-bold"><Users className="h-4 w-4 text-primary" />{branch.staff_count}</p><p className="text-[11px] text-muted-foreground">Petugas</p></div><div><p className="flex items-center gap-1 text-xl font-bold"><Vault className="h-4 w-4 text-primary" />{branch.custody_location_count}</p><p className="text-[11px] text-muted-foreground">Lokasi simpan</p></div></div>
          <p className="mt-4 text-xs font-semibold text-muted-foreground">Nilai diminta: <span className="text-foreground">{idr(branch.requested_amount)}</span></p>
        </Link>;
      })}
    </div>
    {branches.length === 0 && <div className="rounded-2xl border border-dashed border-border bg-surface p-10 text-center text-sm text-muted-foreground">Belum ada cabang yang dapat diakses.</div>}
  </div>;
}
