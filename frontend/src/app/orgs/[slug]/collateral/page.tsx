"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeftRight, ArrowRight, PackageCheck, ShieldCheck, Truck, Warehouse } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { dispatchCustodyMovement, listApplications, listCustodyLocations, listCustodyMovements, receiveCustodyMovement, requestCustodyMovement, type ApplicationQueueItem, type CustodyMovement, type MasterItem } from "@/lib/operations";

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
  const [locations, setLocations] = useState<MasterItem[]>([]);
  const [movements, setMovements] = useState<CustodyMovement[]>([]);
  const [applicationId, setApplicationId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([listApplications(100), listCustodyLocations(), listCustodyMovements()]).then(([applications, vaults, movementRows]) => { setItems(applications); setLocations(vaults); setMovements(movementRows); }).catch((reason: { detail?: string }) => setError(reason.detail ?? "Collateral Passport gagal dimuat"));
  }, []);
  async function refreshMovements(){setMovements(await listCustodyMovements());setItems(await listApplications(100));}
  async function createMovement(){if(!applicationId||!destinationId||reason.length<5){setError("Pilih agunan, vault tujuan, dan isi alasan mutasi.");return;}setBusy("create");setError(null);try{await requestCustodyMovement({application_id:applicationId,to_location_id:destinationId,reason});setNotice("Mutasi dibuat. Custodian asal harus mencatat dispatch dan nomor segel.");setApplicationId("");setDestinationId("");setReason("");await refreshMovements();}catch(value){setError((value as {detail?:string}).detail??"Mutasi gagal dibuat");}finally{setBusy(null);}}
  async function dispatch(item:CustodyMovement){const seal=window.prompt("Nomor segel keluar:");if(!seal)return;setBusy(item.id);try{await dispatchCustodyMovement(item.id,seal,"Barang dan segel diperiksa saat keluar vault");setNotice("Barang berstatus in transit.");await refreshMovements();}catch(value){setError((value as {detail?:string}).detail??"Dispatch gagal");}finally{setBusy(null);}}
  async function receive(item:CustodyMovement){const seal=window.prompt("Nomor segel saat diterima:",item.seal_out??"");if(!seal)return;setBusy(item.id);try{await receiveCustodyMovement(item.id,seal,"Segel cocok dan kondisi barang diterima utuh");setNotice("Mutasi selesai dan lokasi custody diperbarui.");await refreshMovements();}catch(value){setError((value as {detail?:string}).detail??"Penerimaan gagal");}finally{setBusy(null);}}
  if (error && !items) return <ErrorState message={error} />;
  if (!items) return <LoadingState label="Memuat register agunan tenant" />;
  const counts = Object.fromEntries(Object.keys(labels).map((key) => [key, items.filter((item) => item.collateral_status === key).length]));
  return <div className="space-y-6">
    <header><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Chain of custody</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Collateral Passport</h1><p className="mt-2 text-sm text-muted-foreground">Identitas dan jejak perpindahan setiap barang jaminan dalam tenant aktif.</p></header>
    {error&&<div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice&&<div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Stat icon={Truck} label="Pickup dan transit" value={(counts.pickup_assigned ?? 0) + (counts.in_transit ?? 0)} />
      <Stat icon={Warehouse} label="Dalam custody" value={counts.stored ?? 0} />
      <Stat icon={ShieldCheck} label="Siap dilepas" value={counts.release_authorized ?? 0} />
      <Stat icon={PackageCheck} label="Selesai" value={counts.returned ?? 0} />
    </section>
    <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]"><article className="rounded-2xl border border-border bg-surface p-5"><div className="flex items-center gap-2"><ArrowLeftRight className="h-5 w-5 text-primary"/><h2 className="font-bold">Buat mutasi vault</h2></div><div className="mt-4 space-y-3"><select value={applicationId} onChange={(event)=>setApplicationId(event.target.value)} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm"><option value="">Pilih agunan dalam custody</option>{items.filter((item)=>item.collateral_status==="stored").map((item)=><option key={item.id} value={item.id}>{item.application_no} · {item.asset_label}</option>)}</select><select value={destinationId} onChange={(event)=>setDestinationId(event.target.value)} className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm"><option value="">Pilih vault tujuan</option>{locations.map((item)=><option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select><textarea value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Alasan operasional mutasi…" className="min-h-20 w-full rounded-xl border border-border bg-background p-3 text-sm"/><button disabled={busy!==null} onClick={createMovement} className="w-full rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Buat instruksi mutasi</button></div></article><article className="overflow-hidden rounded-2xl border border-border bg-surface"><div className="border-b border-border p-4"><h2 className="font-bold">Movement register</h2><p className="text-xs text-muted-foreground">Dispatch dan penerimaan harus direkam oleh petugas berbeda.</p></div><div className="divide-y divide-border">{movements.map((item)=><div key={item.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center"><div className="flex-1"><p className="font-mono text-xs font-bold text-primary">{item.movement_no}</p><p className="mt-1 text-xs text-muted-foreground">{item.reason}</p><p className="mt-1 text-[10px]">Seal: {item.seal_out??"belum dicatat"}</p></div><b className="text-xs uppercase">{item.status}</b>{item.status==="requested"&&<button disabled={busy!==null} onClick={()=>dispatch(item)} className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-white">Dispatch</button>}{item.status==="in_transit"&&<button disabled={busy!==null} onClick={()=>receive(item)} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white">Terima</button>}</div>)}{!movements.length&&<p className="p-8 text-center text-xs text-muted-foreground">Belum ada mutasi custody.</p>}</div></article></section>
    <section className="overflow-hidden rounded-[var(--pg-radius-lg)] border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
      <div className="border-b border-border px-5 py-4"><h2 className="font-bold">Register agunan</h2><p className="mt-1 text-xs text-muted-foreground">Klik pengajuan untuk menjalankan pickup, custody, settlement, dan pengembalian.</p></div>
      <div className="divide-y divide-border">{items.map((item) => <Link key={item.id} href={`/orgs/${slug}/loans/applications/${item.id}`} className="flex flex-col gap-3 px-5 py-4 transition hover:bg-surface-soft sm:flex-row sm:items-center"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-surface-blue text-primary"><PackageCheck className="h-5 w-5" /></div><div className="min-w-0 flex-1"><p className="font-mono text-xs font-bold text-primary">{item.application_no}</p><p className="mt-1 truncate text-sm font-semibold">{item.asset_label}</p></div><div className="sm:text-right"><p className="text-xs font-bold">{labels[item.collateral_status] ?? item.collateral_status}</p><p className="mt-1 text-[11px] text-muted-foreground">{item.branch_code} · {item.borrower_name}</p></div><ArrowRight className="h-4 w-4 text-muted-foreground" /></Link>)}</div>
    </section>
  </div>;
}

function Stat({ icon: Icon, label, value }: { icon: typeof Truck; label: string; value: number }) {
  return <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><Icon className="h-5 w-5 text-primary" /><p className="mt-4 text-3xl font-bold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{label}</p></article>;
}
