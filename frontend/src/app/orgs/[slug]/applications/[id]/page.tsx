"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  AlertTriangle,
  CircleDollarSign,
  ClipboardCheck,
  FileCheck2,
  IdCard,
  PackageCheck,
  Scale,
  ShieldCheck,
  Truck,
} from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  createAppraisal,
  createCustodyEvent,
  createIncident,
  createOffer,
  createPickup,
  disburseLoan,
  downloadEvidence,
  getApplicationDetail,
  getCollateralTimeline,
  listCustodyLocations,
  transitionApplication,
  transitionPickup,
  uploadEvidence,
  type ApplicationDetail,
  type CollateralTimeline,
  type MasterItem,
} from "@/lib/operations";

const labels: Record<string, string> = {
  draft: "Draf",
  submitted: "Baru masuk",
  under_review: "Dalam review",
  appraisal: "Penaksiran",
  offered: "Penawaran",
  accepted: "Disetujui",
  awaiting_disbursement: "Menunggu pencairan",
  active: "Aktif",
  settled: "Lunas",
  with_customer: "Di nasabah",
  pickup_assigned: "Pickup ditugaskan",
  in_transit: "Dalam perjalanan",
  received: "Diterima",
  stored: "Tersimpan",
  release_authorized: "Boleh dilepas",
  returned: "Dikembalikan",
};

function idr(value: unknown) {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));
}

export default function ApplicationDetailPage() {
  const { slug, id } = useParams<{ slug: string; id: string }>();
  const [detail, setDetail] = useState<ApplicationDetail | null>(null);
  const [timeline, setTimeline] = useState<CollateralTimeline | null>(null);
  const [locations, setLocations] = useState<MasterItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [incidentType, setIncidentType] = useState("custody_exception");
  const [incidentSeverity, setIncidentSeverity] = useState("medium");
  const [incidentDescription, setIncidentDescription] = useState("");

  const load = useCallback(async () => {
    const [application, passport, custody] = await Promise.all([
      getApplicationDetail(id),
      getCollateralTimeline(id),
      listCustodyLocations(),
    ]);
    setDetail(application);
    setTimeline(passport);
    setLocations(custody);
  }, [id]);

  useEffect(() => {
    load().catch((reason: { detail?: string }) => setError(reason.detail ?? "Pengajuan gagal dimuat"));
  }, [load]);

  async function act(label: string, operation: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await operation();
      await load();
      setNotice(label);
    } catch (reason) {
      setError((reason as { detail?: string }).detail ?? "Proses gagal dijalankan");
    } finally {
      setBusy(false);
    }
  }

  if (!detail || !timeline) {
    if (error) return <ErrorState message={error} />;
    return <LoadingState label="Membuka berkas pengajuan dan Collateral Passport" />;
  }

  const latestAppraisal = detail.appraisals.at(-1);
  const latestOffer = detail.offers.at(-1);
  const pickupStatus = String(detail.pickup?.status ?? "");
  const pickupId = String(detail.pickup?.id ?? "");
  const loanStatus = String(detail.loan?.status ?? "");
  const collateralStatus = String(detail.asset.collateral_status ?? "");
  const selectedLocation = locations[0];
  const kycStatus = String(detail.borrower.kyc_status ?? "not_started");
  const customerId = String(detail.borrower.id ?? "");
  const kycVerified = kycStatus === "verified";

  return (
    <div className="space-y-6">
      <header>
        <Link href={`/orgs/${slug}/loans/applications`} className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-primary">
          <ArrowLeft className="h-4 w-4" /> Kembali ke inbox
        </Link>
        <div className="mt-4 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="font-mono text-xs font-bold text-primary">{detail.application_no}</p>
            <h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">{String(detail.borrower.full_name)}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{String(detail.asset.brand ?? "")} {String(detail.asset.model ?? detail.asset.category)} · {String(detail.branch.name ?? "")}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Pill>{labels[detail.status] ?? detail.status}</Pill>
            <Pill>{labels[collateralStatus] ?? collateralStatus}</Pill>
            {detail.loan && <Pill>{labels[loanStatus] ?? loanStatus}</Pill>}
          </div>
        </div>
      </header>

      {(error || notice) && <div className={`rounded-xl border px-4 py-3 text-sm ${error ? "border-red-200 bg-red-50 text-red-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>{error ?? notice}</div>}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Metric icon={CircleDollarSign} label="Dana diminta" value={idr(detail.requested_amount)} />
        <Metric icon={Scale} label="Nilai indikatif" value={idr(detail.asset.indicative_value)} />
        <Metric icon={ClipboardCheck} label="Tenor" value={`${detail.requested_tenor_days ?? "—"} hari`} />
        <Metric icon={ShieldCheck} label="Produk" value={String(detail.product?.name ?? "Belum dipilih")} />
      </section>

      <DecisionWorkspace detail={detail} busy={busy} act={act} />

      <section className={`flex flex-col gap-4 rounded-[var(--pg-radius-lg)] border p-5 shadow-[var(--pg-shadow-sm)] sm:flex-row sm:items-center sm:justify-between ${kycVerified ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>
        <div className="flex items-start gap-3"><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${kycVerified ? "bg-emerald-600 text-white" : "bg-amber-100 text-amber-800"}`}><IdCard className="h-5 w-5" /></span><div><h2 className="text-sm font-bold">Gate KYC debitur: {kycVerified ? "Terverifikasi" : labels[kycStatus] ?? kycStatus.replaceAll("_", " ")}</h2><p className="mt-1 text-xs leading-5 text-muted-foreground">{kycVerified ? "Identitas masih berlaku dan pengajuan dapat diteruskan ke penaksiran." : "Pengajuan tidak dapat masuk penaksiran sebelum KTP, OCR, dan keputusan checker selesai."}</p></div></div>
        <Link href={`/orgs/${slug}/customers/${customerId}?tab=identity`} className={`inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-xl px-4 text-xs font-bold ${kycVerified ? "border border-emerald-300 bg-white text-emerald-800" : "bg-amber-700 text-white"}`}><IdCard className="h-4 w-4" />{kycVerified ? "Lihat KYC" : "Kerjakan KYC"}</Link>
      </section>

      <section className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-bold">Evidence privat</h2><p className="mt-1 text-xs text-muted-foreground">Jenis file diperiksa dari isi, dipindai, diberi checksum, dan file berisiko dikarantina.</p></div><div className="flex flex-wrap gap-2"><label className="inline-flex h-10 cursor-pointer items-center justify-center rounded-xl bg-surface-blue px-4 text-xs font-bold text-primary"><input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className="hidden" disabled={busy} onChange={(event) => { const file = event.target.files?.[0]; if (file) void act("Evidence pengajuan dipindai dan disimpan.", () => uploadEvidence(id, file)); event.currentTarget.value = ""; }} />Bukti pengajuan</label>{latestAppraisal && <label className="inline-flex h-10 cursor-pointer items-center justify-center rounded-xl bg-primary px-4 text-xs font-bold text-white"><input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className="hidden" disabled={busy} onChange={(event) => { const file = event.target.files?.[0]; if (file) void act("Evidence appraisal dipindai dan ditautkan.", () => uploadEvidence(id, file, "appraisal_evidence", "appraisal", String(latestAppraisal.id))); event.currentTarget.value = ""; }} />Bukti appraisal</label>}</div></div>
        <div className="mt-4 flex flex-wrap gap-2">{detail.evidence.map((item) => <span key={String(item.id)} title={String(item.scan_detail ?? "")} className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold ${String(item.scan_status) === "clean" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-700"}`}>{String(item.file_name)} · {String(item.subject_type ?? "application")} · {String(item.scan_status)}</span>)}{!detail.evidence.length && <p className="text-xs text-muted-foreground">Belum ada evidence.</p>}</div>
      </section>

      <section className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
        <div className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-amber-600" /><div><h2 className="font-bold">Laporkan incident operasional</h2><p className="mt-1 text-xs text-muted-foreground">Pelaporan menahan agunan bila status memungkinkan dan membuat case dengan SLA sesuai severity.</p></div></div>
        <div className="mt-4 grid gap-3 lg:grid-cols-[0.7fr_0.5fr_1.8fr_auto]">
          <select value={incidentType} onChange={(event) => setIncidentType(event.target.value)} className="h-10 rounded-xl border border-border bg-background px-3 text-sm"><option value="custody_exception">Custody exception</option><option value="seal_mismatch">Seal mismatch</option><option value="asset_damage">Kerusakan agunan</option><option value="missing_asset">Agunan tidak ditemukan</option><option value="process_breach">Pelanggaran proses</option><option value="fraud_suspicion">Indikasi fraud</option></select>
          <select value={incidentSeverity} onChange={(event) => setIncidentSeverity(event.target.value)} className="h-10 rounded-xl border border-border bg-background px-3 text-sm"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select>
          <input value={incidentDescription} onChange={(event) => setIncidentDescription(event.target.value)} placeholder="Uraikan fakta kejadian, waktu, lokasi, dan kondisi awal…" className="h-10 min-w-0 rounded-xl border border-border bg-background px-3 text-sm" />
          <button disabled={busy || incidentDescription.length < 5} onClick={() => void act("Incident dilaporkan dan masuk Exception Register.", async () => { await createIncident({ application_id: id, incident_type: incidentType, severity: incidentSeverity, description: incidentDescription }); setIncidentDescription(""); })} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 text-xs font-bold text-amber-800 disabled:opacity-50"><AlertTriangle className="h-4 w-4" />Laporkan</button>
        </div>
        {detail.incidents.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{detail.incidents.map((incident) => <Link key={String(incident.id)} href={`/orgs/${slug}/compliance/exceptions/${String(incident.id)}`} className="rounded-lg border border-border bg-surface-soft px-3 py-2 text-xs font-semibold hover:border-primary/30"><span className="uppercase text-amber-700">{String(incident.severity)}</span> · {String(incident.type).replaceAll("_", " ")} · {String(incident.status)}</Link>)}</div>}
      </section>

      <section className="grid gap-5 2xl:grid-cols-[minmax(0,1.45fr)_minmax(360px,0.75fr)]">
        <article className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
          <div className="flex items-center justify-between"><div><h2 className="font-bold">Proses pengajuan</h2><p className="mt-1 text-xs text-muted-foreground">Gate manusia dan state machine sesuai blueprint teknikal</p></div><FileCheck2 className="h-5 w-5 text-primary" /></div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {detail.status === "submitted" && <Action disabled={busy} onClick={() => act("Pengajuan masuk ke review.", () => transitionApplication(id, "under_review", "Dokumen awal diverifikasi"))} icon={ClipboardCheck}>Mulai review</Action>}
            {detail.status === "under_review" && kycVerified && <Action disabled={busy} onClick={() => act("Pengajuan siap ditaksir.", () => transitionApplication(id, "appraisal", "Review kelengkapan dan KYC selesai"))} icon={Scale}>Kirim ke appraisal</Action>}
            {detail.status === "under_review" && !kycVerified && <Link href={`/orgs/${slug}/customers/${customerId}?tab=identity`} className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 text-xs font-bold text-amber-800"><IdCard className="h-4 w-4" />Selesaikan KYC dahulu</Link>}
            {detail.status === "appraisal" && latestAppraisal?.status === "pending_approval" && <Link href={`/orgs/${slug}/compliance/approvals`} className="inline-flex h-10 items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 text-xs font-bold text-amber-800"><ShieldCheck className="h-4 w-4" />Menunggu checker appraisal</Link>}
            {detail.status === "offered" && latestOffer && <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-xs text-blue-900">Penawaran telah diterbitkan. Borrower dapat membaca alasan, tenor, dan biaya lalu menyetujuinya dari portal borrower.</div>}
            {detail.status === "accepted" && !detail.pickup && <Action disabled={busy} onClick={() => act("Pickup ditugaskan.", () => createPickup({ application_id: id, pickup_address: "Alamat terverifikasi pada berkas nasabah" }))} icon={Truck}>Tugaskan pickup</Action>}
            {pickupStatus === "assigned" && <Action disabled={busy} onClick={() => act("Barang mulai dibawa petugas.", () => transitionPickup(pickupId, "in_transit"))} icon={Truck}>Mulai perjalanan</Action>}
            {pickupStatus === "in_transit" && <Action disabled={busy} onClick={() => act("Barang diterima mitra.", () => transitionPickup(pickupId, "received"))} icon={PackageCheck}>Konfirmasi diterima</Action>}
            {collateralStatus === "received" && selectedLocation && <Action disabled={busy} onClick={() => act("Barang masuk custody.", () => createCustodyEvent({ application_id: id, location_id: selectedLocation.id, event_type: "stored", condition_note: "Segel dan kondisi diverifikasi saat serah terima." }))} icon={ShieldCheck}>Simpan di {selectedLocation.code}</Action>}
            {loanStatus === "awaiting_disbursement" && <Action disabled={busy} onClick={() => act("Pencairan terverifikasi.", () => disburseLoan(id, `DISB-${Date.now()}`))} icon={CircleDollarSign}>Verifikasi pencairan</Action>}
            {loanStatus === "active" && <Link href={`/orgs/${slug}/finance/payments`} className="inline-flex h-10 items-center gap-2 rounded-xl border border-primary px-4 text-xs font-bold text-primary"><CircleDollarSign className="h-4 w-4" />Buka payment control</Link>}
            {loanStatus === "settled" && collateralStatus === "stored" && <Link href={`/orgs/${slug}/compliance/approvals`} className="inline-flex h-10 items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 text-xs font-bold text-amber-800"><ShieldCheck className="h-4 w-4" />Menunggu otorisasi pelepasan</Link>}
            {collateralStatus === "release_authorized" && selectedLocation && <Action disabled={busy} onClick={() => act("Agunan dikembalikan ke nasabah.", () => createCustodyEvent({ application_id: id, location_id: selectedLocation.id, event_type: "returned", condition_note: "Diterima nasabah setelah verifikasi identitas." }))} icon={PackageCheck}>Serahkan ke nasabah</Action>}
          </div>
          <div className="mt-6 space-y-3">
            {detail.history.map((item, index) => <div key={String(item.id)} className="flex gap-3 rounded-xl bg-surface-soft px-4 py-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-primary text-[10px] font-bold text-white">{index + 1}</span><div><p className="text-xs font-bold">{labels[String(item.to_status)] ?? String(item.to_status)}</p><p className="mt-1 text-[11px] text-muted-foreground">{String(item.note ?? "Perubahan status tercatat")}</p></div></div>)}
          </div>
        </article>

        <article className="rounded-[var(--pg-radius-lg)] bg-[linear-gradient(145deg,var(--pg-navy-900),#0b3b7b)] p-5 text-white shadow-[var(--pg-shadow-lg)]">
          <div className="flex items-center justify-between"><div><p className="text-xs text-blue-200">Collateral Passport</p><h2 className="mt-1 font-mono text-lg font-bold">{timeline.asset_code}</h2></div><PackageCheck className="h-8 w-8 text-blue-300" /></div>
          <div className="mt-5 space-y-1">
            {timeline.events.map((event) => <div key={String(event.id)} className="relative ml-2 border-l border-white/20 pb-5 pl-5 last:pb-0"><span className="absolute -left-1.5 top-1 h-3 w-3 rounded-full bg-blue-300 ring-4 ring-blue-400/15" /><p className="text-xs font-bold">{String(event.title)}</p><p className="mt-1 text-[11px] leading-5 text-blue-100/65">{String(event.description ?? labels[String(event.event_type)] ?? event.event_type)}</p></div>)}
          </div>
        </article>
      </section>
    </div>
  );
}

function DecisionWorkspace({ detail, busy, act }: { detail: ApplicationDetail; busy: boolean; act: (label: string, operation: () => Promise<unknown>) => Promise<void> }) {
  const [market, setMarket] = useState(String(detail.ai_estimate?.high_value ?? detail.asset.indicative_value ?? ""));
  const [liquidation, setLiquidation] = useState("");
  const [recommended, setRecommended] = useState("");
  const [rationale, setRationale] = useState("");
  const [principal, setPrincipal] = useState(String(detail.requested_amount));
  const [tenor, setTenor] = useState(String(detail.requested_tenor_days ?? ""));
  const [decisionReason, setDecisionReason] = useState("");
  const appraisal = detail.appraisals.at(-1);
  const product = detail.product as Record<string, unknown> | null;
  const allowedTenors = (product?.allowed_tenors_days as number[] | undefined) ?? [detail.requested_tenor_days ?? 30];
  const feePercent = Number(product?.service_fee_percent ?? 0);
  const fee = Number((Number(principal) * feePercent / 100).toFixed(2));
  const changed = Number(principal) !== Number(detail.requested_amount) || Number(tenor) !== Number(detail.requested_tenor_days);
  const field = "h-11 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none focus:border-primary";
  return <section className="grid gap-5 xl:grid-cols-2">
    <article className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
      <div className="flex items-center gap-2"><Scale className="h-5 w-5 text-primary" /><h2 className="font-bold">Estimasi AI dan appraisal manusia</h2></div>
      {detail.ai_estimate ? <div className="mt-4 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-2"><span className="font-bold text-blue-950">Kisaran indikatif</span><Pill>{detail.ai_estimate.status}</Pill></div>
        <p className="mt-2 text-xl font-bold text-blue-900">{detail.ai_estimate.low_value ? `${idr(detail.ai_estimate.low_value)} – ${idr(detail.ai_estimate.high_value)}` : "Belum dapat dihitung"}</p>
        <p className="mt-2 text-xs leading-5 text-blue-900/75">{detail.ai_estimate.explanation} · {detail.ai_estimate.comparable_count} pembanding · kualitas foto {Math.round(Number(detail.ai_estimate.quality_score) * 100)}%</p>
        {detail.ai_estimate.asset_description && <p className="mt-2 rounded-xl bg-white p-3 text-xs leading-5 text-blue-950"><strong>Rincian dari nasabah (belum diverifikasi):</strong> {detail.ai_estimate.asset_description}</p>}
        {detail.ai_estimate.quality_findings.map((finding) => <p key={finding} className="mt-1 text-xs text-amber-800">{finding}</p>)}
        {Boolean(detail.ai_estimate.vision_result.visible_condition) && <p className="mt-2 text-xs text-blue-900">Kondisi terlihat: {String(detail.ai_estimate.vision_result.visible_condition)}</p>}
        <div className="mt-3 rounded-xl border border-blue-200 bg-white p-3 text-xs text-blue-950"><p className="font-bold">Riset harga pasar · {detail.ai_estimate.research_result?.status === "COMPARED" ? "pembanding memadai" : detail.ai_estimate.research_result?.status === "LIMITED" ? "cakupan terbatas" : "penilaian manual diperlukan"}</p>
          {detail.ai_estimate.research_result?.searched_at && <p className="mt-1">Penelusuran: {new Date(detail.ai_estimate.research_result.searched_at).toLocaleString("id-ID")}</p>}
          {detail.ai_estimate.research_result?.selected?.map((source) => <div key={source.url} className="mt-2 border-t border-blue-100 pt-2"><a href={source.url} target="_blank" rel="noopener noreferrer" className="font-semibold underline">{source.title}</a><p>{source.host} · {idr(source.price_idr)} · {source.price_kind}{source.source_date ? ` · ${source.source_date}` : " · tanggal harga tidak tercantum"}</p>{source.price_evidence && <p className="mt-1 text-blue-900/70">Kutipan: {source.price_evidence}</p>}</div>)}
          {!detail.ai_estimate.research_result?.selected?.length && <><p className="mt-2">Tidak ada pembanding yang lolos; penaksiran fisik diperlukan.</p>{detail.ai_estimate.research_result?.sources?.slice(0, 4).map((source) => <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer" className="mt-2 block underline">Hasil telusur: {source.title}</a>)}</>}
        </div>
        {detail.evidence.filter((item) => item.type === "asset_photo").map((item) => <button key={String(item.id)} className="mt-3 rounded-lg border border-blue-300 bg-white px-3 py-2 text-xs font-bold text-blue-800" onClick={() => void downloadEvidence(String(item.id))}>Buka foto barang</button>)}
      </div> : <p className="mt-4 text-sm text-muted-foreground">Belum ada estimasi dari portal borrower.</p>}
      {detail.status === "appraisal" && !appraisal && <div className="mt-5 space-y-3 border-t border-border pt-5">
        <h3 className="text-sm font-bold">Penilaian penaksir</h3><p className="text-xs text-muted-foreground">Masukkan hasil pemeriksaan nyata; nilai AI hanya bahan bantu.</p>
        <div className="grid gap-3 sm:grid-cols-3"><label className="text-xs font-semibold">Nilai pasar<input className={`${field} mt-1`} type="number" min="1" value={market} onChange={(e) => setMarket(e.target.value)} /></label>
          <label className="text-xs font-semibold">Nilai likuidasi<input className={`${field} mt-1`} type="number" min="1" value={liquidation} onChange={(e) => setLiquidation(e.target.value)} /></label>
          <label className="text-xs font-semibold">Dana rekomendasi<input className={`${field} mt-1`} type="number" min="1" value={recommended} onChange={(e) => setRecommended(e.target.value)} /></label></div>
        <label className="block text-xs font-semibold">Alasan dan pembanding yang diperiksa<textarea className={`${field} mt-1 min-h-24 py-3`} value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder="Kondisi fisik, kelengkapan, pembanding pasar, serta alasan perbedaan dari estimasi awal…" /></label>
        <button disabled={busy || !market || !liquidation || !recommended || rationale.trim().length < 10} onClick={() => void act("Appraisal dikirim ke checker.", () => createAppraisal({ application_id: detail.id, market_value: Number(market), liquidation_value: Number(liquidation), recommended_loan: Number(recommended), condition_grade: detail.asset.condition_grade ?? "B", rationale }))} className="min-h-11 rounded-xl bg-primary px-4 text-xs font-bold text-white disabled:opacity-50">Ajukan hasil appraisal ke checker</button>
      </div>}
      {appraisal && <div className="mt-4 rounded-xl border border-border p-4 text-xs"><p className="font-bold">Appraisal revisi {String(appraisal.revision)} · {String(appraisal.status)}</p><p className="mt-2">Nilai pasar {idr(appraisal.market_value)} · likuidasi {idr(appraisal.liquidation_value)} · rekomendasi {idr(appraisal.recommended_loan)}</p><p className="mt-2 text-muted-foreground">{String(appraisal.rationale)}</p></div>}
    </article>
    <article className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
      <div className="flex items-center gap-2"><FileCheck2 className="h-5 w-5 text-primary" /><h2 className="font-bold">Keputusan dan penawaran</h2></div>
      <p className="mt-3 text-xs leading-5 text-muted-foreground">Permintaan borrower {idr(detail.requested_amount)} selama {detail.requested_tenor_days} hari. Seluruh perubahan harus disertai alasan yang akan terlihat borrower.</p>
      {detail.status === "appraisal" && appraisal?.status === "final" && <div className="mt-5 space-y-3">
        <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-semibold">Dana ditawarkan<input className={`${field} mt-1`} type="number" min="1" max={String(appraisal.recommended_loan)} value={principal} onChange={(e) => setPrincipal(e.target.value)} /></label>
          <label className="text-xs font-semibold">Tenor<select className={`${field} mt-1`} value={tenor} onChange={(e) => setTenor(e.target.value)}>{allowedTenors.map((days) => <option key={days} value={days}>{days} hari</option>)}</select></label></div>
        <div className="rounded-xl bg-surface-soft p-4 text-xs"><p>Perubahan dana: <strong>{idr(Number(principal) - Number(detail.requested_amount))}</strong></p><p className="mt-2">Perubahan tenor: <strong>{Number(tenor) - Number(detail.requested_tenor_days)} hari</strong></p><p className="mt-2">Biaya layanan ({feePercent}%): <strong>{idr(fee)}</strong></p><p className="mt-2">Total kewajiban: <strong>{idr(Number(principal) + fee)}</strong></p></div>
        <label className="block text-xs font-semibold">Alasan keputusan {changed ? "(wajib)" : ""}<textarea className={`${field} mt-1 min-h-24 py-3`} value={decisionReason} onChange={(e) => setDecisionReason(e.target.value)} placeholder="Contoh: nilai likuidasi lebih rendah karena goresan pada unit dan kelengkapan charger tidak ada…" /></label>
        <button disabled={busy || Number(principal) <= 0 || (changed && decisionReason.trim().length < 10)} onClick={() => void act("Penawaran diterbitkan dan dapat dibaca borrower.", () => createOffer({ application_id: detail.id, principal_amount: Number(principal), tenor_days: Number(tenor), service_fee_amount: fee, expires_at: new Date(Date.now() + 2 * 86400000).toISOString(), agreement_version: "AGR-2026.1", decision_reason: decisionReason.trim() || null }))} className="min-h-11 rounded-xl bg-primary px-4 text-xs font-bold text-white disabled:opacity-50">Terbitkan penawaran</button>
      </div>}
      {detail.offers.at(-1) && <div className="mt-5 rounded-xl border border-border p-4 text-xs"><p className="font-bold">Penawaran versi {String(detail.offers.at(-1)?.version)} · {String(detail.offers.at(-1)?.status)}</p><p className="mt-2">Dana {idr(detail.offers.at(-1)?.principal_amount)} · tenor {String(detail.offers.at(-1)?.tenor_days)} hari · biaya {idr(detail.offers.at(-1)?.service_fee_amount)}</p><p className="mt-2 text-muted-foreground">Alasan: {String(detail.offers.at(-1)?.decision_reason ?? "Sesuai permintaan dan appraisal final")}</p></div>}
      {detail.status === "appraisal" && !appraisal && <p className="mt-5 text-xs text-muted-foreground">Penawaran tersedia setelah appraisal manusia disetujui checker.</p>}
    </article>
  </section>;
}

function Pill({ children }: { children: React.ReactNode }) { return <span className="rounded-full border border-primary/20 bg-surface-blue px-3 py-2 text-xs font-bold text-primary">{children}</span>; }
function Metric({ icon: Icon, label, value }: { icon: typeof Scale; label: string; value: string }) { return <article className="rounded-2xl border border-border bg-surface p-4 shadow-[var(--pg-shadow-sm)]"><Icon className="h-5 w-5 text-primary" /><p className="mt-4 text-xs text-muted-foreground">{label}</p><p className="mt-1 truncate font-bold">{value}</p></article>; }
function Action({ icon: Icon, children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { icon: typeof Scale }) { return <button {...props} className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-white transition hover:bg-blue-strong disabled:opacity-50"><Icon className="h-4 w-4" />{children}</button>; }
