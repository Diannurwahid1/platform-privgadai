"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, PackageCheck, ShieldCheck, Truck, Warehouse } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listApplications, type ApplicationQueueItem } from "@/lib/operations";

const labels: Record<string, string> = {
  with_customer: "Di nasabah",
  pickup_assigned: "Pickup ditugaskan",
  in_transit: "Dalam perjalanan",
  received: "Diterima",
  stored: "Dalam custody",
  incident_hold: "Ditahan karena insiden",
  release_authorized: "Boleh dilepas",
  returned: "Dikembalikan",
};

export default function CollateralPage() {
  const { slug } = useParams<{ slug: string }>();
  const [items, setItems] = useState<ApplicationQueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    listApplications(100).then(setItems).catch((reason: { detail?: string }) => setError(reason.detail ?? "Collateral Passport gagal dimuat"));
  }, []);
  if (error) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat register agunan tenant" />;
  const counts = Object.fromEntries(Object.keys(labels).map((key) => [key, items.filter((item) => item.collateral_status === key).length]));
  return <div className="space-y-6">
    <header><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Chain of custody</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Collateral Passport</h1><p className="mt-2 text-sm text-muted-foreground">Identitas dan jejak perpindahan setiap barang jaminan dalam tenant aktif.</p></header>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Stat icon={Truck} label="Pickup dan transit" value={(counts.pickup_assigned ?? 0) + (counts.in_transit ?? 0)} />
      <Stat icon={Warehouse} label="Dalam custody" value={counts.stored ?? 0} />
      <Stat icon={ShieldCheck} label="Siap dilepas" value={counts.release_authorized ?? 0} />
      <Stat icon={PackageCheck} label="Selesai" value={counts.returned ?? 0} />
    </section>
    <section className="overflow-hidden rounded-[var(--pg-radius-lg)] border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
      <div className="border-b border-border px-5 py-4"><h2 className="font-bold">Register agunan</h2><p className="mt-1 text-xs text-muted-foreground">Klik pengajuan untuk menjalankan pickup, custody, settlement, dan pengembalian.</p></div>
      <div className="divide-y divide-border">{items.map((item) => <Link key={item.id} href={`/orgs/${slug}/applications/${item.id}`} className="flex flex-col gap-3 px-5 py-4 transition hover:bg-surface-soft sm:flex-row sm:items-center"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-surface-blue text-primary"><PackageCheck className="h-5 w-5" /></div><div className="min-w-0 flex-1"><p className="font-mono text-xs font-bold text-primary">{item.application_no}</p><p className="mt-1 truncate text-sm font-semibold">{item.asset_label}</p></div><div className="sm:text-right"><p className="text-xs font-bold">{labels[item.collateral_status] ?? item.collateral_status}</p><p className="mt-1 text-[11px] text-muted-foreground">{item.branch_code} · {item.borrower_name}</p></div><ArrowRight className="h-4 w-4 text-muted-foreground" /></Link>)}</div>
    </section>
  </div>;
}

function Stat({ icon: Icon, label, value }: { icon: typeof Truck; label: string; value: number }) {
  return <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><Icon className="h-5 w-5 text-primary" /><p className="mt-4 text-3xl font-bold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{label}</p></article>;
}
