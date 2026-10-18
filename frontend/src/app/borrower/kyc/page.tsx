"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Clock3, IdCard, LoaderCircle, ShieldCheck, Upload } from "lucide-react";
import { borrowerFetch, type BorrowerKtpOcrPreview, type BorrowerKyc, type BorrowerMe } from "@/lib/borrower";
import { ErrorBox, Footer, Shell } from "../ui";
import s from "../borrower.module.css";

type IdentityForm = {
  nik: string; legal_name: string; birth_place: string; birth_date: string; gender: string;
  address: string; province: string; city: string; occupation: string;
};

const emptyForm: IdentityForm = {
  nik: "", legal_name: "", birth_place: "", birth_date: "", gender: "",
  address: "", province: "", city: "", occupation: "",
};

const statusCopy: Record<string, { title: string; detail: string }> = {
  not_started: { title: "Verifikasi identitas belum dimulai", detail: "Unggah foto sisi depan KTP untuk membaca data dan mengirimnya ke petugas." },
  pending_documents: { title: "Dokumen belum lengkap", detail: "Foto KTP perlu dikirim ulang agar petugas dapat memeriksanya." },
  pending_review: { title: "KTP sedang diperiksa", detail: "Data dan foto KTP sudah diterima. Petugas akan mencocokkan dokumen serta mengambil keputusan KYC." },
  needs_information: { title: "Perlu perbaikan data", detail: "Periksa catatan petugas, lalu kirim ulang foto dan data KTP yang benar." },
  rejected: { title: "Verifikasi belum disetujui", detail: "Anda dapat memperbaiki data dan mengajukan verifikasi baru." },
  expired: { title: "Verifikasi telah kedaluwarsa", detail: "Perbarui KTP dan data identitas sebelum membuat pengajuan baru." },
  verified: { title: "Identitas sudah terverifikasi", detail: "Anda dapat melanjutkan ke estimasi barang dan pengajuan gadai." },
};

export default function BorrowerKycPage() {
  const router = useRouter();
  const [me, setMe] = useState<BorrowerMe | null>(null);
  const [kyc, setKyc] = useState<BorrowerKyc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [form, setForm] = useState<IdentityForm>(emptyForm);
  const [method, setMethod] = useState("ocr_internal");
  const [consent, setConsent] = useState(false);
  const [reading, setReading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(true);
  const scanSequence = useRef(0);

  useEffect(() => {
    Promise.all([borrowerFetch<BorrowerMe>("/me"), borrowerFetch<BorrowerKyc>("/kyc")])
      .then(([person, verification]) => {
        setMe(person); setKyc(verification);
        setForm((current) => ({ ...current, legal_name: person.full_name.toUpperCase() }));
        setShowForm(["not_started", "pending_documents"].includes(verification.status));
      })
      .catch((cause: Error & { status?: number }) => {
        if (cause.status === 401) router.replace("/borrower");
        else setError(cause.message);
      });
  }, [router]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  useEffect(() => {
    if (kyc?.status !== "pending_review") return;
    let active = true;
    const timer = window.setInterval(() => {
      void borrowerFetch<BorrowerKyc>("/kyc").then((current) => {
        if (active) setKyc(current);
      }).catch(() => undefined);
    }, 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, [kyc?.status]);

  function update<K extends keyof IdentityForm>(key: K, value: IdentityForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function pickKtp(chosen: File | undefined) {
    if (!chosen) return;
    const sequence = ++scanSequence.current;
    if (!["image/jpeg", "image/png", "image/webp"].includes(chosen.type) || chosen.size > 10 * 1024 * 1024) {
      setFile(null); setPreview(null); setReading(false);
      return setError(chosen.size > 10 * 1024 * 1024 ? "Ukuran foto KTP maksimal 10 MB." : "Gunakan foto KTP JPG, PNG, atau WebP.");
    }
    setFile(chosen); setPreview(URL.createObjectURL(chosen)); setError(null);
    setForm({ ...emptyForm, legal_name: me?.full_name.toUpperCase() ?? "" });
    setReading(true); setMessage("PaddleOCR sedang membaca data pada foto KTP…");
    try {
      const body = new FormData(); body.set("file", chosen);
      const result = await borrowerFetch<BorrowerKtpOcrPreview>("/kyc/ocr-preview", { method: "POST", body });
      if (sequence !== scanSequence.current) return;
      setForm((current) => ({
        ...current, ...Object.fromEntries(Object.entries(result.fields).filter(([key, value]) => key !== "confidence" && value)) as IdentityForm,
      }));
      setMethod("ocr_internal"); setMessage(result.message);
    } catch (cause) {
      if (sequence !== scanSequence.current) return;
      setMethod("manual_branch");
      setMessage(`OCR belum berhasil: ${(cause as Error).message} Isi data sesuai KTP; petugas akan memeriksa fotonya.`);
    } finally { if (sequence === scanSequence.current) setReading(false); }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return setError("Foto sisi depan KTP wajib diunggah.");
    if (!consent) return setError("Persetujuan pemrosesan KTP diperlukan.");
    setSaving(true); setError(null);
    try {
      const body = new FormData();
      for (const [key, value] of Object.entries(form)) body.set(key, value.trim());
      body.set("file", file); body.set("verification_method", method);
      body.set("consent_kyc_processing", "true");
      const result = await borrowerFetch<BorrowerKyc>("/kyc", { method: "POST", body });
      setKyc(result); setShowForm(false); setFile(null); setPreview(null); setConsent(false);
      setForm(emptyForm); setMessage("KTP sudah diterima dan dienkripsi. Pantau status verifikasi di halaman ini.");
    } catch (cause) { setError((cause as Error).message); }
    finally { setSaving(false); }
  }

  if (!me || !kyc) return <Shell><main className={s.main}><ErrorBox message={error} />{!error && "Menyiapkan verifikasi identitas…"}</main></Shell>;
  const copy = statusCopy[kyc.status] ?? statusCopy.not_started;
  const mayRestart = ["needs_information", "rejected", "expired", "pending_documents"].includes(kyc.status);

  return <Shell me={me}><main className={s.main}>
    <div className={s.pageHead}><div><Link href="/borrower" className={s.backLink}><ArrowLeft size={15} /> Beranda</Link><h1>Verifikasi identitas</h1><p>Selesaikan KYC KTP sebelum membuat pengajuan gadai.</p></div></div>
    <div className={s.kycIntro}><span className={s.kycIntroIcon}><ShieldCheck size={26} /></span><div><strong>{copy.title}</strong><p>{copy.detail}</p>{kyc.decision_reason && <p><b>Catatan petugas:</b> {kyc.decision_reason}</p>}{kyc.national_id_masked && <small>{kyc.legal_name} · NIK {kyc.national_id_masked}</small>}</div></div>
    <div className={s.kycSteps}><span className={file || kyc.id ? s.kycStepDone : ""}><IdCard size={18} /> 1. Foto KTP</span><span className={kyc.id ? s.kycStepDone : ""}><Clock3 size={18} /> 2. Pemeriksaan petugas</span><span className={kyc.can_apply ? s.kycStepDone : ""}><CheckCircle2 size={18} /> 3. Ajukan gadai</span></div>
    {kyc.can_apply && <Link href="/borrower/apply" className={s.button}>Lanjut ajukan gadai <ArrowRight size={17} /></Link>}
    {kyc.status === "pending_review" && <button className={s.kycRefresh} type="button" onClick={() => { void borrowerFetch<BorrowerKyc>("/kyc").then(setKyc).catch((cause: Error) => setError(cause.message)); }}>Perbarui status pemeriksaan</button>}
    {!kyc.can_apply && !showForm && mayRestart && <button className={s.button} type="button" onClick={() => setShowForm(true)}>Kirim verifikasi baru <ArrowRight size={17} /></button>}
    {message && <div className={s.kycMessage} role="status">{message}</div>}
    <ErrorBox message={error} />
    {!kyc.can_apply && showForm && kyc.status !== "pending_review" && <form className={s.kycForm} onSubmit={submit}>
      <div className={s.kycSectionHead}><span>01</span><div><h2>Unggah sisi depan KTP</h2><p>Pastikan foto asli, keempat sudut terlihat, dan tulisan tidak silau.</p></div></div>
      <label className={s.kycPicker}><input className={s.fileInput} type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => { void pickKtp(event.target.files?.[0]); event.target.value = ""; }} aria-label="Pilih foto sisi depan KTP" />{preview ? <Image src={preview} alt="Pratinjau KTP" width={280} height={180} unoptimized className={s.kycPreview} /> : <span className={s.photoIcon}><Upload size={24} /></span>}<span><strong>{file ? file.name : "Pilih foto KTP"}</strong><small>JPG, PNG, WebP · maksimal 10 MB</small></span></label>
      {file && <><div className={s.kycSectionHead}><span>02</span><div><h2>Periksa data identitas</h2><p>Hasil OCR hanya mengisi formulir. Cocokkan setiap isian dengan KTP sebelum dikirim.</p></div></div>
        <div className={s.formGrid}>
          <label className={s.field}><span>NIK 16 digit</span><input required inputMode="numeric" pattern="[0-9]{16}" maxLength={16} autoComplete="off" value={form.nik} onChange={(e) => update("nik", e.target.value.replace(/\D/g, ""))} /></label>
          <label className={s.field}><span>Nama sesuai KTP</span><input required minLength={3} value={form.legal_name} onChange={(e) => update("legal_name", e.target.value)} /></label>
          <label className={s.field}><span>Tempat lahir</span><input required value={form.birth_place} onChange={(e) => update("birth_place", e.target.value)} /></label>
          <label className={s.field}><span>Tanggal lahir</span><input required type="date" value={form.birth_date} onChange={(e) => update("birth_date", e.target.value)} /></label>
          <label className={s.field}><span>Jenis kelamin</span><select required value={form.gender} onChange={(e) => update("gender", e.target.value)}><option value="">Pilih</option><option value="male">Laki-laki</option><option value="female">Perempuan</option></select></label>
          <label className={s.field}><span>Pekerjaan <em className={s.optional}>opsional</em></span><input value={form.occupation} onChange={(e) => update("occupation", e.target.value)} /></label>
          <label className={s.field}><span>Provinsi</span><input required value={form.province} onChange={(e) => update("province", e.target.value)} /></label>
          <label className={s.field}><span>Kabupaten / kota</span><input required value={form.city} onChange={(e) => update("city", e.target.value)} /></label>
          <label className={`${s.field} ${s.wide}`}><span>Alamat lengkap</span><textarea required minLength={8} value={form.address} onChange={(e) => update("address", e.target.value)} /></label>
          <label className={`${s.field} ${s.wide}`}><span>Metode pemeriksaan petugas</span><select value={method} onChange={(e) => setMethod(e.target.value)}><option value="ocr_internal">Cocokkan PaddleOCR dan periksa petugas</option><option value="manual_branch">Periksa foto KTP secara manual</option></select></label>
        </div>
        <label className={s.kycConsent}><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /> Saya menyetujui pemrosesan dan penyimpanan terenkripsi foto KTP serta data identitas untuk verifikasi KYC.</label>
        <button className={s.button} type="submit" disabled={reading || saving || !consent}>{reading || saving ? <LoaderCircle size={17} className={s.spin} /> : <ShieldCheck size={17} />}{saving ? "Mengirim KTP…" : reading ? "Membaca KTP…" : "Kirim untuk verifikasi"}</button>
      </>}
    </form>}
    <p className={s.kycFootnote}>OCR membantu membaca teks KTP; status terverifikasi diberikan setelah keputusan petugas. Ini bukan klaim verifikasi Dukcapil.</p>
    <Footer />
  </main></Shell>;
}
