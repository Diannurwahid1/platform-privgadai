"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Boxes, CheckCircle2, ClipboardCheck, ScanLine, ShieldCheck, Warehouse } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  createInventoryCheck,
  getInventoryCheck,
  listCustodyLocations,
  listInventoryChecks,
  submitInventoryCheck,
  type InventoryCheckDetail,
  type MasterItem,
} from "@/lib/operations";

type Observation = { observed_status: string; note: string };

export default function InventoryPage() {
  const { slug } = useParams<{ slug: string }>();
  const [data, setData] = useState<{ locations: MasterItem[]; checks: Array<Record<string, unknown>> } | null>(null);
  const [selected, setSelected] = useState<InventoryCheckDetail | null>(null);
  const [observations, setObservations] = useState<Record<string, Observation>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [locations, checks] = await Promise.all([listCustodyLocations(), listInventoryChecks()]);
    setData({ locations, checks });
  }, []);

  useEffect(() => { void load().catch((reason: { detail?: string }) => setError(reason.detail ?? "Stock opname gagal dimuat")); }, [load]);

  async function startCheck(locationId: string) {
    setBusy(locationId); setNotice(null); setError(null);
    try {
      const result = await createInventoryCheck(locationId);
      await load();
      await openCheck(result.id);
      setNotice("Draft dibuat dari register custody terkini. Catat hasil penghitungan fisik lalu kirim ke checker.");
    } catch (reason) { setError((reason as { detail?: string }).detail ?? "Stock opname gagal dimulai"); }
    finally { setBusy(null); }
  }

  async function openCheck(id: string) {
    setBusy(id); setError(null);
    try {
      const detail = await getInventoryCheck(id);
      setSelected(detail);
      setObservations(Object.fromEntries(detail.assets.map((asset) => [asset.application_id, {
        observed_status: asset.observed_status ?? asset.expected_status,
        note: asset.note ?? "",
      }])));
    } catch (reason) { setError((reason as { detail?: string }).detail ?? "Detail stock opname gagal dimuat"); }
    finally { setBusy(null); }
  }

  async function submit() {
    if (!selected?.assets.length) { setError("Tidak ada agunan terdaftar pada lokasi ini."); return; }
    setBusy(selected.id); setError(null); setNotice(null);
    try {
      await submitInventoryCheck(selected.id, selected.assets.map((asset) => ({
        application_id: asset.application_id,
        observed_status: observations[asset.application_id]?.observed_status ?? "missing",
        note: observations[asset.application_id]?.note || null,
      })));
      setNotice("Hasil stock opname terkunci dan dikirim ke approval inbox.");
      await load(); await openCheck(selected.id);
    } catch (reason) { setError((reason as { detail?: string }).detail ?? "Stock opname gagal dikirim"); }
    finally { setBusy(null); }
  }

  const variance = useMemo(() => selected?.assets.filter((asset) => (observations[asset.application_id]?.observed_status ?? asset.expected_status) !== asset.expected_status).length ?? 0, [selected, observations]);

  if (!data) return error ? <ErrorState message={error} /> : <LoadingState label="Memuat stock opname" />;
  return <div className="space-y-5">
    <header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Collateral control · Dual control</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Vault & stock opname</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Snapshot register per lokasi, penghitungan fisik per agunan, variance queue, dan persetujuan checker independen.</p></header>
    {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <section className="grid gap-3 md:grid-cols-3">{data.locations.map((location) => <article key={location.id} className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><div className="flex items-start justify-between"><Warehouse className="h-6 w-6 text-primary"/><span className="rounded-lg bg-surface-soft px-2 py-1 font-mono text-[10px]">{location.code}</span></div><h2 className="mt-4 font-bold">{location.name}</h2><p className="mt-1 text-xs text-muted-foreground">Register fisik dan custody location</p><button onClick={()=>startCheck(location.id)} disabled={busy!==null} className="mt-4 rounded-lg bg-primary px-3 py-2 text-xs font-bold text-white disabled:opacity-50">Mulai penghitungan</button></article>)}</section>
    <section className="grid gap-5 xl:grid-cols-[0.75fr_1.25fr]">
      <article className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border p-4"><div className="flex items-center gap-2"><ScanLine className="h-5 w-5 text-primary"/><h2 className="font-bold">Riwayat opname</h2></div></div><div className="divide-y divide-border">{data.checks.map((item)=><button key={String(item.id)} onClick={()=>openCheck(String(item.id))} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-soft"><ClipboardCheck className="h-4 w-4 text-primary"/><div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold">{new Date(String(item.counted_at)).toLocaleString("id-ID")}</p><p className="mt-1 text-[10px] text-muted-foreground">{String(item.item_count)} item · {String(item.variance_count)} variance</p></div><Status value={String(item.status)}/></button>)}{!data.checks.length&&<p className="p-8 text-center text-xs text-muted-foreground">Belum ada stock opname.</p>}</div></article>
      <article className="rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]">{!selected?<div className="grid min-h-80 place-items-center p-8 text-center"><div><Boxes className="mx-auto h-8 w-8 text-muted-foreground"/><p className="mt-3 text-sm font-semibold">Pilih sesi stock opname</p><p className="mt-1 text-xs text-muted-foreground">Register dan lembar hitung akan tampil di sini.</p></div></div>:<><div className="flex flex-col gap-3 border-b border-border p-5 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-bold">{selected.location.name}</p><p className="mt-1 font-mono text-[11px] text-muted-foreground">{selected.location.code} · {selected.assets.length} agunan</p></div><div className="flex items-center gap-2"><Status value={selected.status}/>{variance>0&&<span className="rounded-lg bg-red-50 px-2 py-1 text-xs font-bold text-red-700">{variance} variance</span>}</div></div><div className="divide-y divide-border">{selected.assets.map((asset)=>{const current=observations[asset.application_id]??{observed_status:asset.expected_status,note:""};const mismatch=current.observed_status!==asset.expected_status;return <div key={asset.application_id} className="grid gap-3 p-4 lg:grid-cols-[1fr_160px_1fr]"><div><Link href={`/orgs/${slug}/applications/${asset.application_id}`} className="font-mono text-xs font-bold text-primary">{asset.asset_code}</Link><p className="mt-1 text-sm font-semibold">{asset.asset_label}</p><p className="mt-1 text-[11px] text-muted-foreground">Expected: {asset.expected_status}</p></div><select disabled={selected.status!=="draft"} value={current.observed_status} onChange={(event)=>setObservations((old)=>({...old,[asset.application_id]:{...current,observed_status:event.target.value}}))} className={`h-10 rounded-xl border px-3 text-xs font-semibold ${mismatch?"border-red-300 bg-red-50":"border-border bg-background"}`}><option value={asset.expected_status}>Sesuai · {asset.expected_status}</option><option value="missing">Tidak ditemukan</option><option value="seal_broken">Segel rusak</option><option value="damaged">Kondisi rusak</option><option value="wrong_location">Salah lokasi</option></select><input disabled={selected.status!=="draft"} value={current.note} onChange={(event)=>setObservations((old)=>({...old,[asset.application_id]:{...current,note:event.target.value}}))} placeholder="Catatan scan, segel, kondisi…" className="h-10 rounded-xl border border-border bg-background px-3 text-xs"/></div>})}{!selected.assets.length&&<p className="p-10 text-center text-xs text-muted-foreground">Tidak ada agunan aktif pada lokasi ini.</p>}</div>{selected.status==="draft"&&<div className="flex items-center justify-between border-t border-border p-4"><p className="flex items-center gap-2 text-xs text-muted-foreground">{variance?<AlertTriangle className="h-4 w-4 text-red-600"/>:<CheckCircle2 className="h-4 w-4 text-emerald-600"/>}{variance?"Variance wajib dijelaskan dan direview.":"Semua item sesuai register."}</p><button onClick={submit} disabled={busy!==null||!selected.assets.length} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-white disabled:opacity-50"><ShieldCheck className="h-4 w-4"/>Kirim ke checker</button></div>}</>}</article>
    </section>
  </div>;
}

function Status({value}:{value:string}){const tone=value==="approved"?"bg-emerald-100 text-emerald-700":value==="rejected"?"bg-red-100 text-red-700":value==="submitted"?"bg-amber-100 text-amber-800":"bg-blue-50 text-blue-700";return <span className={`rounded-lg px-2 py-1 text-[10px] font-bold uppercase ${tone}`}>{value}</span>}
