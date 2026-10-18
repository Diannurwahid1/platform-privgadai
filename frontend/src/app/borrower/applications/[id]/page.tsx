"use client";

import Link from "next/link";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Info, ShieldCheck } from "lucide-react";
import { borrowerFetch, money, type BorrowerDetail, type BorrowerMe } from "@/lib/borrower";
import { ErrorBox, Footer, Shell, Status } from "../../ui";
import s from "../../borrower.module.css";

export default function BorrowerApplicationPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [me, setMe] = useState<BorrowerMe | null>(null);
  const [detail, setDetail] = useState<BorrowerDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    const [person, application] = await Promise.all([borrowerFetch<BorrowerMe>("/me"), borrowerFetch<BorrowerDetail>(`/applications/${id}`)]);
    setMe(person); setDetail(application);
  }, [id]);
  useEffect(() => { load().catch((cause: Error & { status?: number }) => { if (cause.status === 401) router.replace("/borrower"); else setError(cause.message); }); }, [load, router]);

  async function accept() {
    if (!detail?.offer) return;
    setBusy(true); setError(null);
    try { await borrowerFetch(`/applications/${id}/accept-offer`, { method: "POST" }); await load(); }
    catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }

  if (!detail) return <Shell me={me}><main className={s.main}>{error ? <ErrorBox message={error} /> : "Membuka pengajuan…"}</main></Shell>;
  const change = detail.offer ? Number(detail.offer.principal_amount) - Number(detail.requested_amount) : 0;
  const tenorChange = detail.offer ? Number(detail.offer.tenor_days) - Number(detail.requested_tenor_days) : 0;
  return <Shell me={me}><main className={s.main}>
    <div className={s.pageHead}><div><Link href="/borrower" style={{ color: "#2868d1", display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12 }}><ArrowLeft size={15} /> Semua pengajuan</Link>
      <h1>{detail.application_no}</h1><p>{detail.asset?.brand} {detail.asset?.model || detail.asset?.category} · Dibuat {new Date(detail.created_at).toLocaleDateString("id-ID")}</p></div><Status value={detail.status} /></div>
    <ErrorBox message={error} />
    {detail.kyc_status !== "verified" && <div className={s.kycMessage}>KYC KTP belum terverifikasi. <Link href="/borrower/kyc" style={{ fontWeight: 800, textDecoration: "underline" }}>Buka verifikasi identitas</Link> untuk melengkapi atau memantau pemeriksaan petugas.</div>}
    <div className={s.detailGrid}><div>
      <section className={s.card}><h2>Ringkasan pengajuan</h2>
        <div className={s.summaryRow}><span>Verifikasi KTP/KYC</span><strong>{detail.kyc_status === "verified" ? "Terverifikasi" : detail.kyc_status === "not_started" ? "Belum dimulai" : detail.kyc_status.replaceAll("_", " ")}</strong></div>
        <div className={s.summaryRow}><span>Dana yang Anda minta</span><strong>{money(detail.requested_amount)}</strong></div>
        <div className={s.summaryRow}><span>Tenor yang Anda minta</span><strong>{detail.requested_tenor_days} hari</strong></div>
        <div className={s.summaryRow}><span>Barang</span><strong>{detail.asset?.category} · {detail.asset?.brand || "Tanpa merek"} {detail.asset?.model}</strong></div>
        {detail.purpose && <div className={s.summaryRow}><span>Tujuan</span><strong>{detail.purpose}</strong></div>}
      </section>
      <section className={s.card}><h2>Foto dan estimasi awal</h2>
        {/* Photo is served through the authenticated borrower endpoint. */}
        {detail.estimate && <><div style={{ minHeight: 180, borderRadius: 14, background: "#edf3fb", overflow: "hidden", textAlign: "center" }}><Image className={s.photo} src={`/api/backend/borrower/v1/applications/${id}/photo`} alt="Foto barang yang diajukan" width={640} height={450} unoptimized /></div>
          <div className={s.summaryRow}><span>Status</span><Status value={detail.estimate.status} /></div>
          <div className={s.summaryRow}><span>Kisaran awal</span><strong>{detail.estimate.low_value ? `${money(detail.estimate.low_value)} – ${money(detail.estimate.high_value)}` : "Belum dapat dihitung"}</strong></div>
          <p style={{ fontSize: 12, color: "#667d9d", lineHeight: 1.55 }}>{detail.estimate.explanation}</p>
          {detail.estimate.research_result?.selected?.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer" style={{ display: "block", marginTop: 7, color: "#1859be", fontSize: 12, textDecoration: "underline" }}>{source.host} · {money(source.price_idr)} · {source.price_kind}{source.source_date ? ` · ${source.source_date}` : " · tanggal harga tidak tercantum"}</a>)}
          {detail.estimate.quality_findings.length > 0 && <p style={{ fontSize: 12, color: "#9b681d" }}>{detail.estimate.quality_findings.join(" ")}</p>}</>}
      </section>
      <section className={s.card}><h2>Keputusan penaksir</h2>
        {detail.appraisal ? <><div className={s.summaryRow}><span>Nilai pasar</span><strong>{money(detail.appraisal.market_value)}</strong></div>
          <div className={s.summaryRow}><span>Nilai likuidasi</span><strong>{money(detail.appraisal.liquidation_value)}</strong></div>
          <div className={s.summaryRow}><span>Dana direkomendasikan</span><strong>{money(detail.appraisal.recommended_loan)}</strong></div>
          <p style={{ fontSize: 13, lineHeight: 1.6, color: "#536b8d" }}>{detail.appraisal.rationale}</p>
          {detail.appraisal.status !== "final" && <p style={{ fontSize: 12, color: "#9a681b" }}>Menunggu pemeriksaan dan persetujuan petugas kedua.</p>}</>
          : <p style={{ color: "#6a7e9b", fontSize: 13 }}>Penaksir belum menyelesaikan pemeriksaan. KYC KTP wajib terverifikasi sebelum penaksiran dilanjutkan.</p>}
      </section>
      {detail.offer && <section className={s.card} style={{ borderColor: detail.offer.status === "offered" ? "#74aafa" : undefined }}><h2>Penawaran akhir</h2>
        <div className={s.summaryRow}><span>Dana yang ditawarkan</span><strong>{money(detail.offer.principal_amount)}</strong></div>
        <div className={s.summaryRow}><span>Perubahan dari permintaan</span><strong>{change >= 0 ? "+" : ""}{money(change)}</strong></div>
        <div className={s.summaryRow}><span>Tenor</span><strong>{detail.offer.tenor_days} hari {tenorChange !== 0 ? `(${tenorChange > 0 ? "+" : ""}${tenorChange} hari)` : ""}</strong></div>
        <div className={s.summaryRow}><span>Biaya layanan</span><strong>{money(detail.offer.service_fee_amount)}</strong></div>
        <div className={s.summaryRow}><span>Total kewajiban</span><strong>{money(detail.offer.total_due_amount)}</strong></div>
        <div className={s.estimateBox}><strong style={{ fontSize: 13 }}>Alasan keputusan</strong><p>{detail.offer.decision_reason || "Nominal dan tenor sesuai permintaan serta appraisal final."}</p></div>
        {detail.offer.status === "offered" && <><p style={{ fontSize: 12, color: "#677e9e" }}>Berlaku sampai {new Date(detail.offer.expires_at).toLocaleString("id-ID")}. Dengan menerima, Anda menyetujui versi dokumen {detail.offer.agreement_version}.</p>
          <button className={s.button} disabled={busy} onClick={accept}><CheckCircle2 size={17} />{busy ? "Menyimpan persetujuan…" : "Terima penawaran"}</button></>}
        {detail.offer.status === "accepted" && <div className={s.notice}><CheckCircle2 size={16} /> Penawaran sudah Anda terima.</div>}
      </section>}
    </div><aside>
      <section className={s.card}><h2>Perjalanan pengajuan</h2><div className={s.timeline}>{detail.history.map((item, index) => <div className={s.timelineItem} key={`${item.status}-${index}`}><strong>{item.status.replaceAll("_", " ")}</strong><p>{item.note ?? "Status dicatat"}</p><small style={{ color: "#899bb1", fontSize: 11 }}>{new Date(item.at).toLocaleString("id-ID")}</small></div>)}</div></section>
      <section className={s.card}><ShieldCheck size={23} color="#1468e7" /><h2 style={{ marginTop: 10 }}>Apa langkah berikutnya?</h2>
        <p style={{ fontSize: 12, color: "#667d9e", lineHeight: 1.6 }}>{detail.status === "submitted" || detail.status === "under_review" ? "Petugas memeriksa berkas dan KTP. Anda dapat melihat perubahan status di halaman ini." : detail.status === "appraisal" ? "Penaksir menilai barang, kemudian checker meninjau hasilnya." : detail.status === "offered" ? "Tinjau jumlah, tenor, biaya, dan alasan sebelum menerima penawaran." : "Petugas akan melanjutkan proses serah terima dan pencairan sesuai SOP."}</p>
        <div style={{ display: "flex", gap: 7, fontSize: 11, color: "#7891b1", marginTop: 18 }}><Info size={15} /> Keputusan akhir dibuat petugas, bukan AI.</div>
      </section>
      <Link className={s.buttonOutline} href="/borrower/apply" style={{ width: "100%" }}>Pengajuan baru <ArrowRight size={16} /></Link>
    </aside></div><Footer />
  </main></Shell>;
}
