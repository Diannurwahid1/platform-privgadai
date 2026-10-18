"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight, Camera, CheckCircle2, Info, LoaderCircle, Sparkles, X } from "lucide-react";
import { borrowerEstimateStream, borrowerFetch, money, type BorrowerConfig, type BorrowerKyc, type BorrowerMe, type Estimate, type EstimateStage } from "@/lib/borrower";
import { ErrorBox, Footer, Shell, Status } from "../ui";
import s from "../borrower.module.css";

export default function ApplyPage() {
  const router = useRouter();
  const [me, setMe] = useState<BorrowerMe | null>(null);
  const [config, setConfig] = useState<BorrowerConfig | null>(null);
  const [kyc, setKyc] = useState<BorrowerKyc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [estimating, setEstimating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [category, setCategory] = useState("");
  const [brand, setBrand] = useState("");
  const [model, setModel] = useState("");
  const [assetDescription, setAssetDescription] = useState("");
  const [condition, setCondition] = useState("B");
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [aiConsent, setAiConsent] = useState(false);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [progress, setProgress] = useState<EstimateStage[]>([]);
  const [branchId, setBranchId] = useState("");
  const [productId, setProductId] = useState("");
  const [amount, setAmount] = useState("");
  const [tenor, setTenor] = useState("");
  const [purpose, setPurpose] = useState("");
  const [terms, setTerms] = useState(false);

  useEffect(() => {
    Promise.all([borrowerFetch<BorrowerMe>("/me"), borrowerFetch<BorrowerConfig>("/config"), borrowerFetch<BorrowerKyc>("/kyc")])
      .then(([person, setup, identity]) => { setMe(person); setConfig(setup); setKyc(identity); setCategory(setup.categories[0]?.code ?? ""); setBranchId(setup.branches[0]?.id ?? ""); setProductId(setup.products[0]?.id ?? ""); setTenor(String(setup.products[0]?.allowed_tenors_days[0] ?? "")); })
      .catch((cause: Error & { status?: number }) => {
        if (cause.status === 401) router.replace("/borrower");
        else setError(cause.message);
      });
  }, [router]);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function pickPhoto(file: File | undefined) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) return setError("Gunakan foto JPG, PNG, atau WebP.");
    if (file.size > 5 * 1024 * 1024) return setError("Foto maksimal 5 MB.");
    setPhoto(file); setPreview(URL.createObjectURL(file)); setEstimate(null); setError(null);
  }

  function removePhoto() {
    setPhoto(null); setPreview(null); setEstimate(null); setProgress([]);
  }

  async function runEstimate() {
    if (!photo) return setError("Foto barang wajib diunggah.");
    if (!aiConsent) return setError("Setujui pengiriman foto ke layanan analisis visual terlebih dahulu.");
    setEstimating(true); setError(null); setProgress([]); setEstimate(null);
    try {
      const body = new FormData();
      body.set("category_code", category); body.set("condition_grade", condition);
      body.set("brand", brand); body.set("model", model); body.set("photo", photo);
      body.set("asset_description", assetDescription.trim());
      body.set("share_photo_with_ai", "true");
      const result = await borrowerEstimateStream(body, (event) => {
        setProgress((current) => [...current.filter((item) => item.stage !== event.stage), event]);
      });
      setEstimate(result);
      const product = config?.products.find((item) => item.id === productId);
      if (result.low_value && product) setAmount(String(Math.max(product.min_amount, Math.min(product.max_amount, Math.floor(result.low_value * product.max_ltv_percent / 100 / 1000) * 1000))));
    } catch (cause) { setError((cause as Error).message); }
    finally { setEstimating(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!estimate) return setError("Buat estimasi awal dahulu.");
    if (!terms) return setError("Persetujuan pemrosesan data perlu dicentang.");
    setSubmitting(true); setError(null);
    try {
      const item = await borrowerFetch<{ id: string }>("/applications", { method: "POST", body: JSON.stringify({
        estimate_id: estimate.id, branch_id: branchId, product_id: productId,
        requested_amount: Number(amount), requested_tenor_days: Number(tenor), purpose,
        consent_document_version: config?.consent_version,
      }) });
      router.push(`/borrower/applications/${item.id}`);
    } catch (cause) { setError((cause as Error).message); }
    finally { setSubmitting(false); }
  }

  const busy = estimating || submitting;
  const product = config?.products.find((item) => item.id === productId);
  const categoryName = config?.categories.find((item) => item.code === category)?.name ?? category;
  const categoryWords = `${category} ${categoryName}`.toLowerCase();
  const detailHint = /emas|gold|logam/.test(categoryWords)
    ? "Contoh: berat gram, kadar, sertifikat, kondisi kemasan, cacat yang terlihat."
    : /motor|mobil|kendaraan/.test(categoryWords)
      ? "Contoh: tahun, varian, kilometer, STNK/BPKB, riwayat servis, kerusakan."
      : /hp|phone|smartphone|elektronik|laptop/.test(categoryWords)
        ? "Contoh: kapasitas, warna, kesehatan baterai, usia pakai, kelengkapan, cacat layar."
        : "Contoh: ukuran atau spesifikasi, usia pakai, kelengkapan, kondisi, kerusakan.";
  const activeStage = progress.at(-1);
  if (!config || !me || !kyc) return <Shell><main className={s.main}><ErrorBox message={error} />{!error && "Menyiapkan formulir pengajuan…"}</main></Shell>;
  if (!kyc.can_apply) return <Shell me={me}><main className={s.main}><Link href="/borrower" className={s.backLink}><ArrowLeft size={15} /> Beranda</Link><div className={s.kycGate}><span className={s.kycGateIcon}><CheckCircle2 size={28} /></span><h1>Verifikasi KTP sebelum mengajukan</h1><p>Pengajuan gadai baru dapat dibuat setelah petugas menyatakan KYC terverifikasi. Status saat ini: <strong>{kyc.status.replaceAll("_", " ")}</strong>.</p><Link href="/borrower/kyc" className={s.button}>Buka verifikasi KTP <ArrowRight size={17} /></Link></div><Footer /></main></Shell>;

  return <Shell me={me}><main className={s.main}>
    <div className={s.pageHead}><div><Link href="/borrower" style={{ fontSize: 12, color: "#2868d1", display: "inline-flex", gap: 6, alignItems: "center" }}><ArrowLeft size={14} /> Beranda</Link>
      <h1>Ajukan gadai</h1><p>Foto barang → estimasi awal → jumlah dan tenor → dikirim ke petugas.</p></div><Status value={estimate?.status ?? "Foto barang"} /></div>
    <ErrorBox message={error} />
    <div className={s.wizard}><div>
      <section className={s.formSection}><h2>01 / Kenali barang Anda</h2><p>Ceritakan barang dengan cara Anda. Hanya foto yang wajib untuk estimasi; rincian lain membantu AI memilih harga pembanding yang tepat.</p>
        <div className={s.formGrid}>
          <label className={s.field}><span>Jenis barang</span><select disabled={busy} value={category} onChange={(e) => { setCategory(e.target.value); setEstimate(null); }}>{config.categories.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}</select></label>
          <label className={s.field}><span>Perkiraan kondisi</span><select disabled={busy} value={condition} onChange={(e) => { setCondition(e.target.value); setEstimate(null); }}><option value="A">A · Sangat baik</option><option value="B">B · Baik</option><option value="C">C · Cukup</option><option value="D">D · Perlu perbaikan</option></select></label>
          <label className={s.field}><span>Merek <em className={s.optional}>opsional</em></span><input disabled={busy} value={brand} maxLength={100} onChange={(e) => { setBrand(e.target.value); setEstimate(null); }} placeholder="Contoh: Apple, Antam" /></label>
          <label className={s.field}><span>Model / tipe <em className={s.optional}>opsional</em></span><input disabled={busy} value={model} maxLength={120} onChange={(e) => { setModel(e.target.value); setEstimate(null); }} placeholder="Contoh: iPhone 15 Pro" /></label>
          <label className={`${s.field} ${s.wide}`}><span>Ceritakan rincian barang <em className={s.optional}>opsional</em></span><textarea disabled={busy} value={assetDescription} maxLength={1000} onChange={(e) => { setAssetDescription(e.target.value); setEstimate(null); }} placeholder={detailHint} rows={4} /><small className={s.fieldHint}>Sebutkan varian, kelengkapan, dan cacat yang mungkin tidak terlihat di foto. Jangan tulis NIK, nomor telepon, atau data pribadi. {assetDescription.length}/1000</small></label>
        </div>
        <div className={s.photoSection}><div className={s.photoHeading}><div><strong>Foto barang</strong><span>Foto asli, utuh, dan terang membantu identifikasi.</span></div><span className={s.requiredTag}>Wajib</span></div>
          <label className={s.photoPicker}>
            <input disabled={busy} className={s.fileInput} type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => { pickPhoto(e.target.files?.[0]); e.target.value = ""; }} aria-label={photo ? "Ganti foto barang" : "Pilih foto barang"} />
            {preview ? <Image src={preview} alt="Pratinjau foto barang" width={600} height={400} unoptimized className={s.photoPreview} /> : <span className={s.photoIcon}><Camera size={24} /></span>}
            <span className={s.photoCopy}><strong>{photo ? "Ganti foto barang" : "Pilih foto barang"}</strong><small>JPG, PNG, atau WebP · maksimal 5 MB</small></span>
            {photo && <span className={s.photoFileName} title={photo.name}>{photo.name}</span>}
          </label>
          {photo && <button disabled={busy} type="button" className={s.removePhoto} onClick={removePhoto}><X size={14} /> Hapus foto</button>}
        </div>
        <label style={{ display: "flex", gap: 9, alignItems: "start", fontSize: 12, color: "#536e95", lineHeight: 1.5, marginTop: 18 }}><input disabled={busy} type="checkbox" checked={aiConsent} onChange={(e) => setAiConsent(e.target.checked)} /> Saya setuju foto barang dianalisis oleh layanan AI. Atribut barang dipakai untuk mencari pembanding harga di internet; foto tidak dikirim ke mesin pencari. Kisaran dapat berubah setelah pemeriksaan.</label>
        <button type="button" className={`${s.button} ${s.estimateButton}`} disabled={busy || !photo || !aiConsent} onClick={runEstimate}><Sparkles size={17} />{estimating ? "Sedang menganalisis barang…" : estimate ? "Perbarui estimasi" : "Lihat estimasi awal"}</button>
        {estimating && <div className={s.progressPanel} role="status" aria-live="polite"><div className={s.progressHead}><span className={s.progressPulse}><LoaderCircle size={17} /></span><div><strong>{activeStage?.message ?? "Mengirim foto untuk dianalisis"}</strong><small>Progres berasal dari proses yang sedang berjalan di server</small></div></div><div className={s.progressTrack}><span /></div><ol className={s.progressSteps}>{progress.map((item, index) => <li key={item.stage} className={index === progress.length - 1 ? s.progressActive : s.progressDone}><span>{index === progress.length - 1 ? <LoaderCircle size={13} /> : <CheckCircle2 size={13} />}</span>{item.message}</li>)}</ol></div>}
        {estimate && <div className={s.estimateBox}><Status value={estimate.status} />
          {estimate.low_value && estimate.high_value ? <strong>{money(estimate.low_value)} – {money(estimate.high_value)}</strong> : <strong>Nilai belum tersedia</strong>}
          <p>{estimate.explanation} {estimate.comparable_count > 0 ? `${estimate.comparable_count} pembanding digunakan.` : "Petugas akan menaksir secara manual."}</p>
          <p style={{ marginTop: 8 }}>Pemeriksaan foto: {estimate.vision_status === "succeeded" ? "selesai" : "menunggu pemeriksaan petugas"}. {estimate.quality_findings.join(" ")}</p>
          {Boolean(estimate.vision_result.visible_condition) && <p style={{ marginTop: 8 }}>AI melihat: {String(estimate.vision_result.visible_condition)}</p>}
          <p style={{ marginTop: 10, fontSize: 12 }}>Riset pasar: {estimate.research_result?.status === "COMPARED" ? "beberapa pembanding cocok" : estimate.research_result?.status === "LIMITED" ? "cakupan terbatas, perlu penaksir" : "perlu penaksir"}{estimate.research_result?.searched_at ? ` · ditelusuri ${new Date(estimate.research_result.searched_at).toLocaleString("id-ID")}` : ""}</p>
          {estimate.research_result?.selected?.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer" style={{ display: "block", marginTop: 7, fontSize: 12, color: "#1859be", textDecoration: "underline" }}>{source.title} · {money(source.price_idr)} · {source.price_kind}{source.source_date ? ` · ${source.source_date}` : " · tanggal harga tidak tercantum"}</a>)}
        </div>}
      </section>
      <form onSubmit={submit}><section className={s.formSection}><h2>02 / Tentukan kebutuhan dana</h2><p>Nominal awal adalah permintaan Anda. Penawaran akhir dapat berbeda dan alasannya akan ditampilkan.</p>
        <div className={s.formGrid}>
          <label className={s.field}><span>Cabang</span><select required value={branchId} onChange={(e) => setBranchId(e.target.value)}>{config.branches.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.city}</option>)}</select></label>
          <label className={s.field}><span>Produk gadai</span><select required value={productId} onChange={(e) => { const p = config.products.find((item) => item.id === e.target.value); setProductId(e.target.value); setTenor(String(p?.allowed_tenors_days[0] ?? "")); }}>{config.products.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label className={s.field}><span>Nominal diminta (Rp)</span><input required type="number" min={product?.min_amount ?? 1} max={product?.max_amount} step="1000" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Masukkan nominal" /></label>
          <label className={s.field}><span>Tenor</span><select required value={tenor} onChange={(e) => setTenor(e.target.value)}>{product?.allowed_tenors_days.map((days) => <option key={days} value={days}>{days} hari</option>)}</select></label>
          <label className={`${s.field} ${s.wide}`}><span>Tujuan penggunaan dana (opsional)</span><textarea value={purpose} maxLength={1000} onChange={(e) => setPurpose(e.target.value)} placeholder="Ceritakan kebutuhan Anda secara singkat" /></label>
        </div>
        <label style={{ display: "flex", gap: 9, alignItems: "start", fontSize: 12, color: "#536e95", lineHeight: 1.5 }}><input type="checkbox" checked={terms} onChange={(e) => setTerms(e.target.checked)} /> Saya menyetujui pemrosesan data pengajuan versi {config.consent_version}. KYC KTP saya sudah terverifikasi dan masih berlaku.</label>
        <button type="submit" className={s.button} disabled={busy || !estimate || !terms} style={{ marginTop: 20 }}>{submitting ? "Mengirim pengajuan…" : "Kirim pengajuan"} {submitting ? <LoaderCircle size={17} className={s.spin} /> : <ArrowRight size={17} />}</button>
      </section></form>
    </div><aside className={`${s.card} ${s.summary}`}><h3 style={{ margin: 0, fontSize: 16 }}>Ringkasan</h3>
      <div className={s.summaryRow}><span>Barang</span><strong>{[categoryName, brand, model].filter(Boolean).join(" · ")}</strong></div>
      {assetDescription.trim() && <div className={s.summaryDetail}><span>Rincian Anda</span><p>{assetDescription}</p></div>}
      <div className={s.summaryRow}><span>Estimasi awal</span><strong>{estimate?.low_value ? `${money(estimate.low_value)} – ${money(estimate.high_value)}` : "Belum tersedia"}</strong></div>
      <div className={s.summaryRow}><span>Dana diminta</span><strong>{amount ? money(amount) : "—"}</strong></div>
      <div className={s.summaryRow}><span>Tenor</span><strong>{tenor ? `${tenor} hari` : "—"}</strong></div>
      <div style={{ display: "flex", gap: 9, color: "#637c9f", lineHeight: 1.5, fontSize: 12, marginTop: 18 }}><Info size={18} style={{ flexShrink: 0 }} /> Estimasi awal bukan persetujuan kredit. Nilai final, biaya, dan tenor muncul setelah keputusan petugas.</div>
      {estimate && <p style={{ display: "flex", gap: 6, color: "#1577bd", fontSize: 12, marginTop: 15 }}><CheckCircle2 size={16} /> Foto dan estimasi tercatat</p>}
    </aside></div><Footer />
  </main></Shell>;
}
