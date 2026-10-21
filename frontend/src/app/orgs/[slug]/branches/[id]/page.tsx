"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Building2, MapPin, Users, Wallet, Warehouse } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listApplications, listBranchOverview, listStaffAssignments, type ApplicationQueueItem, type BranchOverviewItem, type StaffAssignmentItem } from "@/lib/operations";

const idr = (amount: number) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(amount);

export default function BranchDetailPage() {
  const { slug, id } = useParams<{ slug: string; id: string }>();
  const [branch, setBranch] = useState<BranchOverviewItem | null>(null);
  const [applications, setApplications] = useState<ApplicationQueueItem[]>([]);
  const [staff, setStaff] = useState<StaffAssignmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listBranchOverview(), listApplications(50, id), listStaffAssignments()])
      .then(([branches, applicationRows, assignments]) => {
        const selected = branches.find((item) => item.id === id);
        if (!selected) { setError("Cabang tidak ditemukan atau tidak dapat diakses."); return; }
        setBranch(selected);
        setApplications(applicationRows);
        setStaff(assignments.filter((item) => item.branch_id === id && item.is_active));
      })
      .catch((reason: { detail?: string }) => setError(reason.detail ?? "Detail cabang gagal dimuat"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <LoadingState label="Memuat aktivitas cabang" />;
  if (error || !branch) return <ErrorState message={error ?? "Cabang tidak ditemukan"} actionHref={`/orgs/${slug}/branches`} actionLabel="Kembali ke daftar cabang" />;

  const primary = slug === "murah-gadai-jogja" && branch.code === "01-UAD-K4";
  return <div className="space-y-6">
    <header className="border-b border-border pb-5"><Link href={`/orgs/${slug}/branches`} className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-primary"><ArrowLeft className="h-4 w-4" /> Semua cabang</Link><div className="mt-4 flex flex-wrap items-center gap-2"><span className="rounded-lg bg-surface-blue px-2.5 py-1 font-mono text-xs font-bold text-primary">{branch.code}</span>{primary && <span className="rounded-lg bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">Cabang utama</span>}</div><h1 className="mt-3 text-3xl font-bold tracking-[-0.045em]">{branch.name}</h1><p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground"><MapPin className="h-4 w-4" /> {branch.address || `${branch.city} · Alamat rinci belum diisi`}</p></header>
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {[{ label: "Pengajuan", value: String(branch.application_count), icon: Building2 }, { label: "Nilai diminta", value: idr(branch.requested_amount), icon: Wallet }, { label: "Petugas aktif", value: String(branch.staff_count), icon: Users }, { label: "Lokasi penyimpanan", value: String(branch.custody_location_count), icon: Warehouse }].map(({ label, value, icon: Icon }) => <article key={label} className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><Icon className="h-5 w-5 text-primary" /><p className="mt-3 text-xl font-bold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{label}</p></article>)}
    </section>
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(260px,0.7fr)]">
      <article className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4"><div><h2 className="font-bold">Pengajuan terbaru</h2><p className="mt-1 text-xs text-muted-foreground">Data yang tercatat untuk cabang ini</p></div><Link href={`/orgs/${slug}/loans/applications`} className="text-xs font-semibold text-primary">Buka inbox <ArrowRight className="inline h-3.5 w-3.5" /></Link></div><div className="divide-y divide-border">{applications.map((item) => <Link key={item.id} href={`/orgs/${slug}/loans/applications/${item.id}`} className="flex items-center justify-between gap-3 px-5 py-4 transition hover:bg-surface-soft"><span className="min-w-0"><span className="block font-mono text-xs font-bold text-primary">{item.application_no}</span><span className="mt-1 block truncate text-sm font-semibold">{item.borrower_name} · {item.asset_label}</span></span><span className="shrink-0 text-right"><span className="block text-xs font-semibold">{idr(item.requested_amount)}</span><span className="mt-1 block text-[11px] text-muted-foreground">{item.status.replaceAll("_", " ")}</span></span></Link>)}</div>{applications.length === 0 && <div className="px-5 py-12 text-center text-sm text-muted-foreground">Belum ada pengajuan di cabang ini.</div>}</article>
      <div className="space-y-5"><article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="font-bold">Petugas cabang</h2><div className="mt-4 space-y-3">{staff.map((item) => <div key={item.id} className="rounded-xl bg-surface-soft px-3 py-3"><p className="text-sm font-semibold">{item.user_name}</p><p className="mt-1 text-xs capitalize text-muted-foreground">{item.operational_role.replaceAll("_", " ")}</p></div>)}{staff.length === 0 && <p className="text-xs leading-5 text-muted-foreground">Belum ada petugas yang ditugaskan.</p>}</div></article><article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="font-bold">Fasilitas operasional</h2><p className="mt-3 text-sm text-muted-foreground">{branch.cashbox_count} kas · {branch.custody_location_count} lokasi penyimpanan</p><Link href={`/orgs/${slug}/management/master-data`} className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-primary">Lihat master data <ArrowRight className="h-3.5 w-3.5" /></Link></article></div>
    </section>
  </div>;
}
