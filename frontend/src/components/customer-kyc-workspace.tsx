"use client";

import Link from "next/link";
import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";
import { BadgeCheck, Check, CheckCircle2, CircleAlert, FileLock2, IdCard, ScanText, ShieldAlert, Upload, UserRoundCheck } from "lucide-react";
import { me } from "@/lib/auth";
import { getCustomerKyc, getKycProviderCapabilities, previewKycOcr, reviewCustomerKyc, runKycOcr, startCustomerKyc, uploadKycDocument, type CustomerKyc, type KycProviderCapabilities } from "@/lib/operations";

const inputClass = "w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/10";
const initial = { nik: "", legal_name: "", birth_place: "", birth_date: "", gender: "male", address: "", province: "", city: "", occupation: "", verification_method: "ocr_internal" };

export function CustomerKycWorkspace({ customerId, customerName, slug }: { customerId: string; customerName: string; slug: string }) {
  const [data, setData] = useState<CustomerKyc | null>(null);
  const [capabilities, setCapabilities] = useState<KycProviderCapabilities | null>(null);
  const [form, setForm] = useState({ ...initial, legal_name: customerName.toUpperCase() });
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [ktpFile, setKtpFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [ocrConfidence, setOcrConfidence] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [viewerId, setViewerId] = useState<string | null>(null);
  const [reviewReason, setReviewReason] = useState("");
  const [riskLevel, setRiskLevel] = useState("standard");
  const [pepMatch, setPepMatch] = useState(false);
  const [sanctionsMatch, setSanctionsMatch] = useState(false);
  const scanSequence = useRef(0);
  const load = useCallback(() => Promise.all([getCustomerKyc(customerId), getKycProviderCapabilities(), me()]).then(([kyc, provider, viewer]) => { setData(kyc); setCapabilities(provider); setViewerId(viewer.id); }).catch((e: { detail?: string }) => setMessage(e.detail ?? "KYC gagal dimuat")), [customerId]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  const latest = data?.verifications[0];

  async function readKtp(file: File) {
    const sequence = ++scanSequence.current;
    setKtpFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setForm({ ...initial, legal_name: customerName.toUpperCase() });
    setPreviewing(true);
    setOcrConfidence(null);
    setMessage("PaddleOCR sedang membaca foto KTP…");
    try {
      const result = await previewKycOcr(customerId, file);
      if (sequence !== scanSequence.current) return;
      setForm((current) => ({
        ...current,
        nik: result.fields.nik || current.nik,
        legal_name: result.fields.legal_name || current.legal_name,
        birth_place: result.fields.birth_place || current.birth_place,
        birth_date: result.fields.birth_date || current.birth_date,
        gender: result.fields.gender || current.gender,
        address: result.fields.address || current.address,
        province: result.fields.province || current.province,
        city: result.fields.city || current.city,
        occupation: result.fields.occupation || current.occupation,
      }));
      setOcrConfidence(result.fields.confidence);
      setMessage(result.message);
    } catch (error) {
      if (sequence !== scanSequence.current) return;
      setMessage(`OCR belum berhasil: ${(error as { detail?: string }).detail ?? "foto tidak dapat dibaca"}. Anda dapat mengganti foto atau melengkapi data secara manual.`);
    } finally {
      if (sequence === scanSequence.current) setPreviewing(false);
    }
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage(null);
    try {
      if (!ktpFile) throw { detail: "Foto sisi depan KTP wajib dipilih" };
      const result = await startCustomerKyc(customerId, form);
      await uploadKycDocument(customerId, result.id, ktpFile);
      let outcome = "Data dan dokumen KTP direkam. Menunggu pemeriksaan checker.";
      if (form.verification_method === "ocr_internal" && capabilities?.ocr.enabled) {
        try {
          const ocr = await runKycOcr(customerId, result.id);
          outcome = ocr.message;
        } catch (ocrError) {
          outcome = `KTP sudah tersimpan, tetapi OCR perlu diulang: ${(ocrError as { detail?: string }).detail ?? "layanan OCR gagal"}`;
        }
      }
      setShowForm(false); setKtpFile(null); setPreviewUrl(null); setOcrConfidence(null); setMessage(outcome); await load();
    } catch (e) { setMessage((e as { detail?: string }).detail ?? "KYC gagal direkam"); }
    finally { setBusy(false); }
  }

  async function decide(decision: "verified" | "rejected" | "needs_information") {
    if (!latest) return;
    if (reviewReason.trim().length < 5) { setMessage("Alasan keputusan minimal 5 karakter dan wajib masuk audit."); return; }
    setBusy(true); setMessage(null);
    try { await reviewCustomerKyc(customerId, latest.id, { decision, reason: reviewReason.trim(), risk_level: riskLevel, pep_match: pepMatch, sanctions_match: sanctionsMatch }); setMessage("Keputusan KYC tersimpan dan audit event dibuat."); setReviewReason(""); await load(); }
    catch (e) { setMessage((e as { detail?: string }).detail ?? "Keputusan gagal disimpan"); }
    finally { setBusy(false); }
  }

  async function runOcr() {
    if (!latest) return;
    setBusy(true); setMessage(null);
    try {
      const result = await runKycOcr(customerId, latest.id);
      setMessage(result.message); await load();
    } catch (e) { setMessage((e as { detail?: string }).detail ?? "Pemeriksaan provider gagal"); }
    finally { setBusy(false); }
  }

  const isMaker = Boolean(latest && viewerId === latest.initiated_by_user_id);
  const ocrMatched = Boolean(latest?.provider_checks.some((check) => check.check_type === "ocr" && check.status === "matched"));
  const flow = [
    { label: "Data KTP", done: Boolean(latest) },
    { label: "Dokumen", done: Boolean(latest?.documents.length) },
    { label: "OCR", done: latest?.verification_method === "manual_branch" || ocrMatched },
    { label: "Keputusan checker", done: latest?.status === "verified" || latest?.status === "rejected" },
  ];

  return <section className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex items-center gap-2"><IdCard className="h-5 w-5 text-primary" /><h2 className="font-bold">KYC dan Customer Due Diligence</h2></div><p className="mt-1 text-xs text-muted-foreground">Rekam KTP, cocokkan hasil OCR, nilai risiko, lalu minta petugas berbeda mengambil keputusan.</p></div><button type="button" onClick={() => setShowForm((v) => !v)} className="h-10 rounded-xl bg-primary px-4 text-xs font-bold text-white">{showForm ? "Tutup formulir" : latest ? "Buat pemeriksaan baru" : "Mulai KYC"}</button></div>
    {message && <div className="mt-4 rounded-xl border border-primary/20 bg-surface-blue px-4 py-3 text-xs font-medium text-primary">{message}</div>}
    {!showForm && <div className="mt-5 grid gap-2 sm:grid-cols-4">{flow.map((step, index) => <div key={step.label} className={`flex items-center gap-2 rounded-xl border px-3 py-3 text-xs font-semibold ${step.done ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-border bg-surface-soft text-muted-foreground"}`}><span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full ${step.done ? "bg-emerald-600 text-white" : "bg-background"}`}>{step.done ? <Check className="h-3.5 w-3.5" /> : index + 1}</span>{step.label}</div>)}</div>}
    {!showForm && latest && <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_1fr_1.1fr]">
      <Card icon={latest.status === "verified" ? CheckCircle2 : ShieldAlert} title="Status pemeriksaan"><Status value={latest.status} /><p className="mt-2 text-xs text-muted-foreground">Risiko {latest.risk_level} · {latest.verification_method.replaceAll("_", " ")}</p><p className="mt-2 text-xs">{latest.decision_reason ?? "Menunggu keputusan checker."}</p></Card>
      <Card icon={IdCard} title="Identitas KTP"><Line label="NIK" value={latest.national_id_masked} /><Line label="Nama" value={latest.legal_name} /><Line label="Lahir" value={`${latest.birth_place}, ${latest.birth_date}`} /><Line label="Alamat" value={`${latest.address}, ${latest.city}, ${latest.province}`} /></Card>
      <Card icon={FileLock2} title="Bukti terenkripsi"><p className="text-2xl font-bold">{latest.documents.length}</p><p className="text-xs text-muted-foreground">Dokumen privat, malware scan, enkripsi, dan checksum SHA-256.</p><div className="mt-3 space-y-1">{latest.documents.map((document) => <p key={String(document.id)} className="truncate text-[11px] text-muted-foreground">{String(document.document_side).replaceAll("_", " ")} · {String(document.scan_status)}</p>)}</div></Card>
    </div>}
    {!showForm && latest && <div className="mt-4 rounded-xl border border-border bg-surface-soft p-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex items-center gap-2"><ScanText className="h-4 w-4 text-primary"/><h3 className="text-xs font-bold uppercase tracking-wide">Verifikasi dokumen PaddleOCR</h3></div><p className="mt-1 text-xs text-muted-foreground">NIK, nama, dan tanggal lahir dibandingkan dengan data KYC. Jika seluruhnya cocok, dokumen dianggap terverifikasi internal dan siap diputuskan checker.</p></div>{capabilities?.ocr.enabled&&<button disabled={busy} onClick={runOcr} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-bold text-white"><ScanText className="h-4 w-4"/>Proses KTP</button>}</div>{!capabilities?.ocr.enabled&&<div className="mt-3 rounded-lg border border-dashed border-border px-3 py-3 text-xs text-muted-foreground">Layanan PaddleOCR belum aktif pada server.</div>}<div className="mt-4 grid gap-3 md:grid-cols-2">{latest.provider_checks.filter((check)=>check.check_type==="ocr").map((check)=><div key={check.id} className="rounded-xl border border-border bg-surface p-3"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2"><BadgeCheck className="h-4 w-4 text-primary"/><p className="text-xs font-bold">PaddleOCR KTP</p></div><span className={`rounded-md px-2 py-1 text-[10px] font-bold uppercase ${check.status==="matched"?"bg-emerald-100 text-emerald-700":"bg-amber-100 text-amber-800"}`}>{check.status==="matched"?"Internal verified":"Perlu pemeriksaan"}</span></div><p className="mt-2 text-[11px] text-muted-foreground">{check.provider_name} · {new Date(check.completed_at).toLocaleString("id-ID")}</p><MatchSummary result={check.result}/></div>)}{!latest.provider_checks.some((check)=>check.check_type==="ocr")&&<p className="text-xs text-muted-foreground">KTP belum diproses PaddleOCR.</p>}</div></div>}
    {!showForm && latest && ["pending_review", "needs_information"].includes(latest.status) && <div className="mt-4 rounded-xl border border-border bg-surface p-4"><div className="flex items-start gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-surface-blue text-primary"><UserRoundCheck className="h-4 w-4" /></span><div><h3 className="text-sm font-bold">Keputusan checker dan CDD</h3><p className="mt-1 text-xs text-muted-foreground">Petugas berbeda menilai kecocokan dokumen, risiko, PEP, dan sanksi. Keputusan disimpan sebagai audit event.</p></div></div>{isMaker ? <div className="mt-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" /><span>Anda adalah maker pemeriksaan ini sehingga tidak boleh memberi keputusan. Minta petugas reviewer lain membuka antrean KYC. <Link href={`/orgs/${slug}/management/team-access`} className="font-bold text-primary">Kelola Tim & Akses</Link></span></div> : <div className="mt-4 grid gap-4"><div className="grid gap-3 md:grid-cols-[220px_1fr]"><Field label="Tingkat risiko"><select value={riskLevel} onChange={(event) => setRiskLevel(event.target.value)} className={inputClass}><option value="low">Rendah</option><option value="standard">Standar</option><option value="high">Tinggi</option><option value="enhanced">Enhanced due diligence</option></select></Field><Field label="Alasan keputusan"><textarea value={reviewReason} onChange={(event) => setReviewReason(event.target.value)} placeholder="Catat dasar pemeriksaan dan keputusan…" className={`${inputClass} min-h-20`} /></Field></div><div className="flex flex-wrap gap-4"><label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={pepMatch} onChange={(event) => setPepMatch(event.target.checked)} /> Terindikasi PEP</label><label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={sanctionsMatch} onChange={(event) => setSanctionsMatch(event.target.checked)} /> Cocok daftar sanksi</label></div><div className="flex flex-wrap gap-2"><button disabled={busy || reviewReason.trim().length < 5 || (latest.verification_method === "ocr_internal" && !ocrMatched)} onClick={() => decide("verified")} className="rounded-lg bg-emerald-600 px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Verifikasi KYC</button><button disabled={busy || reviewReason.trim().length < 5} onClick={() => decide("needs_information")} className="rounded-lg border border-border px-4 py-2.5 text-xs font-bold disabled:opacity-50">Minta data</button><button disabled={busy || reviewReason.trim().length < 5} onClick={() => decide("rejected")} className="rounded-lg bg-red-50 px-4 py-2.5 text-xs font-bold text-red-700 disabled:opacity-50">Tolak</button></div>{latest.verification_method === "ocr_internal" && !ocrMatched && <p className="text-[11px] text-amber-700">Verifikasi akhir aktif setelah NIK, nama, dan tanggal lahir cocok pada PaddleOCR.</p>}</div>}</div>}
    {!showForm && !latest && <div className="mt-5 rounded-xl border border-dashed border-border p-8 text-center"><IdCard className="mx-auto h-8 w-8 text-primary" /><p className="mt-3 text-sm font-bold">KYC belum dimulai</p><p className="mt-1 text-xs text-muted-foreground">Klik Mulai KYC lalu unggah foto sisi depan KTP. PaddleOCR akan mengisi data identitas secara otomatis.</p><button type="button" onClick={() => setShowForm(true)} className="mt-4 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white">Mulai KYC nasabah</button></div>}
    {showForm && <form onSubmit={submit} className="mt-5 border-t border-border pt-5">
      <div className="mb-5 flex items-center gap-3"><span className="grid h-8 w-8 place-items-center rounded-full bg-primary text-xs font-bold text-white">1</span><div><h3 className="text-sm font-bold">Unggah foto sisi depan KTP</h3><p className="text-xs text-muted-foreground">Sistem membaca identitas lebih dulu, lalu mengisi formulir secara otomatis.</p></div></div>
      <label onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); const file = event.dataTransfer.files[0]; if (file) void readKtp(file); }} className="group grid cursor-pointer gap-4 rounded-2xl border-2 border-dashed border-border bg-surface-soft p-5 transition hover:border-primary/50 hover:bg-surface-blue md:grid-cols-[180px_1fr] md:items-center">
        <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; event.currentTarget.value = ""; if (file) void readKtp(file); }} />
        <div className="relative grid h-28 place-items-center overflow-hidden rounded-xl border border-border bg-surface">
          {previewUrl ? <Image src={previewUrl} alt="Pratinjau foto KTP" fill unoptimized className="object-cover" /> : <IdCard className="h-10 w-10 text-primary/60" />}
          {previewing && <div className="absolute inset-0 grid place-items-center bg-slate-950/60 text-xs font-bold text-white">Membaca KTP…</div>}
        </div>
        <div><div className="flex items-center gap-2"><Upload className="h-4 w-4 text-primary"/><p className="text-sm font-bold">{ktpFile ? ktpFile.name : "Klik atau seret foto KTP ke sini"}</p></div><p className="mt-1 text-xs leading-5 text-muted-foreground">JPG, PNG, atau WebP · maksimal 10 MB · pastikan seluruh sudut KTP terlihat dan tidak silau.</p><span className="mt-3 inline-flex rounded-lg border border-border bg-surface px-3 py-2 text-xs font-bold text-primary">{ktpFile ? "Ganti foto" : "Pilih foto KTP"}</span></div>
      </label>
      {ktpFile && !previewing && <>
        <div className="mb-4 mt-6 flex flex-col gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-950 sm:flex-row sm:items-center sm:justify-between"><span><strong>Hasil OCR internal.</strong> Petugas wajib mencocokkan data berikut dengan foto KTP sebelum menyimpan.</span>{ocrConfidence !== null && <span className="shrink-0 font-bold">Keyakinan {Math.round(ocrConfidence * 100)}%</span>}</div>
        <div className="mb-5 flex items-center gap-3"><span className="grid h-8 w-8 place-items-center rounded-full bg-primary text-xs font-bold text-white">2</span><div><h3 className="text-sm font-bold">Periksa data hasil pembacaan</h3><p className="text-xs text-muted-foreground">Koreksi field yang belum terbaca atau tidak sesuai dengan KTP.</p></div></div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <Field label="NIK 16 digit"><input required inputMode="numeric" pattern="[0-9]{16}" maxLength={16} value={form.nik} onChange={(e) => setForm({ ...form, nik: e.target.value.replace(/\D/g, "") })} className={inputClass} /></Field>
          <Field label="Nama sesuai KTP"><input required value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} className={inputClass} /></Field>
          <Field label="Tempat lahir"><input required value={form.birth_place} onChange={(e) => setForm({ ...form, birth_place: e.target.value })} className={inputClass} /></Field>
          <Field label="Tanggal lahir"><input required type="date" value={form.birth_date} onChange={(e) => setForm({ ...form, birth_date: e.target.value })} className={inputClass} /></Field>
          <Field label="Jenis kelamin"><select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })} className={inputClass}><option value="male">Laki-laki</option><option value="female">Perempuan</option></select></Field>
          <Field label="Pekerjaan"><input value={form.occupation} onChange={(e) => setForm({ ...form, occupation: e.target.value })} className={inputClass} /></Field>
          <Field label="Provinsi"><input required value={form.province} onChange={(e) => setForm({ ...form, province: e.target.value })} className={inputClass} /></Field>
          <Field label="Kabupaten/Kota"><input required value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className={inputClass} /></Field>
          <Field label="Metode verifikasi"><select value={form.verification_method} onChange={(e)=>setForm({...form,verification_method:e.target.value})} className={inputClass}><option value="ocr_internal">PaddleOCR + checker internal</option><option value="manual_branch">Pemeriksaan manual cabang</option></select></Field>
          <Field label="Alamat lengkap" wide><textarea required value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className={`${inputClass} min-h-24`} /></Field>
          <div className="flex items-end"><button disabled={busy || previewing} type="submit" className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-white disabled:opacity-50"><CheckCircle2 className="h-4 w-4" />{busy ? "Menyimpan…" : "Konfirmasi data & simpan KYC"}</button></div>
        </div>
      </>}
    </form>}
  </section>;
}

function Card({ icon: Icon, title, children }: { icon: typeof IdCard; title: string; children: React.ReactNode }) { return <div className="rounded-xl border border-border bg-surface-soft p-4"><div className="flex items-center gap-2"><Icon className="h-4 w-4 text-primary" /><h3 className="text-xs font-bold uppercase tracking-wide">{title}</h3></div><div className="mt-4 space-y-2">{children}</div></div>; }
function Status({ value }: { value: string }) { const ok=value === "verified"; return <span className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-bold ${ok ? "bg-emerald-100 text-emerald-700" : value === "rejected" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>{value.replaceAll("_", " ")}</span>; }
function Line({ label, value }: { label: string; value: string }) { return <div><p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-0.5 text-xs font-medium">{value}</p></div>; }
function Field({ label, wide=false, children }: { label: string; wide?: boolean; children: React.ReactNode }) { return <label className={`space-y-1.5 text-xs font-semibold ${wide ? "md:col-span-2" : ""}`}><span>{label}</span>{children}</label>; }
function MatchSummary({result}:{result:Record<string,unknown>}){const matches=(result.field_matches??{}) as Record<string,boolean|null>;const rows=[["NIK",matches.nik],["Nama",matches.legal_name],["Tanggal lahir",matches.birth_date]] as const;return <div className="mt-3 flex flex-wrap gap-2">{rows.map(([label,value])=><span key={label} className={`rounded-md px-2 py-1 text-[10px] font-bold ${value===true?"bg-emerald-50 text-emerald-700":value===false?"bg-red-50 text-red-700":"bg-surface-soft text-muted-foreground"}`}>{label}: {value===true?"sesuai":value===false?"berbeda":"tidak terbaca"}</span>)}</div>}
