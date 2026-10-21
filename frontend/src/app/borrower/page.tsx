"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, Camera, ClipboardCheck, ShieldCheck, Sparkles } from "lucide-react";
import { borrowerFetch, money, type BorrowerApplication, type BorrowerKyc, type BorrowerMe } from "@/lib/borrower";
import { ErrorBox, Footer, Mascot, Shell, Status } from "./ui";
import s from "./borrower.module.css";

export default function BorrowerHome() {
  const [me, setMe] = useState<BorrowerMe | null>(null);
  const [applications, setApplications] = useState<BorrowerApplication[]>([]);
  const [kyc, setKyc] = useState<BorrowerKyc | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    borrowerFetch<BorrowerMe>("/me").then(async (person) => {
      setMe(person);
      const [items, identity] = await Promise.all([borrowerFetch<BorrowerApplication[]>("/applications"), borrowerFetch<BorrowerKyc>("/kyc")]);
      setApplications(items); setKyc(identity);
    }).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  async function submitAuth(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null);
    try {
      const person = await borrowerFetch<BorrowerMe>(mode === "login" ? "/login" : "/register", {
        method: "POST", body: JSON.stringify(mode === "login" ? { email, password } : { full_name: fullName, phone, email, password }),
      });
      setMe(person);
      const [items, identity] = await Promise.all([borrowerFetch<BorrowerApplication[]>("/applications"), borrowerFetch<BorrowerKyc>("/kyc")]);
      setApplications(items); setKyc(identity);
      setPassword("");
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }

  if (loading) return <Shell><main className={s.main}>Membuka portal borrower…</main></Shell>;

  if (!me) return <Shell><div className={s.authWrap}>
    <section className={s.authVisual}><span className={s.eyebrow}>PT GADAI MURAH JOGJA</span>
      <h1>Gadai privat.<br />Dana lebih dekat.</h1>
      <p>Unggah foto barang, lihat estimasi awal, dan ikuti keputusan petugas dalam satu tempat.</p>
      <Mascot /></section>
    <section className={s.authPane}><form className={s.authForm} onSubmit={submitAuth}>
      <h2>{mode === "login" ? "Selamat datang kembali" : "Mulai bersama PrivGadai"}</h2>
      <p>{mode === "login" ? "Masuk ke akun borrower Anda. Akun petugas memakai portal terpisah." : "Daftar untuk mengajukan gadai ke PT Gadai Murah Jogja."}</p>
      {mode === "register" && <><label className={s.field}><span>Nama lengkap sesuai KTP</span><input required minLength={2} value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Nama lengkap" /></label>
        <label className={s.field}><span>Nomor ponsel</span><input required minLength={8} type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="08…" /></label></>}
      <label className={s.field}><span>Email</span><input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@email.com" /></label>
      <label className={s.field}><span>Kata sandi</span><input required type="password" minLength={mode === "register" ? 10 : undefined} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Minimal 10 karakter" /></label>
      <ErrorBox message={error} />
      <button type="submit" disabled={busy} className={s.button} style={{ width: "100%" }}>{busy ? "Memproses…" : mode === "login" ? "Masuk ke portal" : "Buat akun"}<ArrowRight size={17} /></button>
      <div className={s.switch}>{mode === "login" ? "Belum punya akun?" : "Sudah punya akun?"} <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>{mode === "login" ? "Daftar" : "Masuk"}</button></div>
    </form></section>
  </div></Shell>;

  return <Shell me={me}><main className={s.main}>
    <section className={s.hero}><div className={s.heroText}><span className={s.eyebrow}>PORTAL BORROWER · {me.partner.name}</span>
      <h1>Halo, {me.full_name.split(" ")[0]}.<br />Ada rencana baru?</h1>
      <p>Verifikasi KTP, lihat kisaran nilai barang, lalu ajukan dana. Keputusan akhir dicatat oleh penaksir dan petugas.</p>
      <Link href={kyc?.can_apply ? "/borrower/apply" : "/borrower/kyc"} className={s.buttonWhite}>{kyc?.can_apply ? "Ajukan gadai" : kyc?.status === "pending_review" ? "Pantau verifikasi KTP" : "Verifikasi KTP dahulu"} <ArrowRight size={17} /></Link>
    </div><Mascot className={s.heroImage} /></section>
    <div className={s.sectionTitle}><div><h2>Proses yang jelas</h2><p>Anda dapat memantau setiap keputusan dan alasannya.</p></div></div>
    <section className={s.steps}>
      <div className={s.step}><span className={s.stepIcon}><ShieldCheck size={22} /></span><h3>1. KYC KTP</h3><p>Unggah KTP, koreksi hasil OCR, lalu tunggu verifikasi petugas sebelum mengajukan.</p></div>
      <div className={s.step}><span className={s.stepIcon}><Camera size={22} /></span><h3>2. Foto dan estimasi</h3><p>Unggah foto barang. Sistem memeriksa kualitas foto dan harga pembanding.</p></div>
      <div className={s.step}><span className={s.stepIcon}><Sparkles size={22} /></span><h3>3. Review dan penawaran</h3><p>Penaksir menilai barang; Anda melihat nominal, tenor, biaya, dan alasan keputusan.</p></div>
    </section>
    <div id="applications" className={s.sectionTitle}><div><h2>Pengajuan Anda</h2><p>{applications.length ? `${applications.length} pengajuan tercatat` : "Belum ada pengajuan. Mulai dari foto barang Anda."}</p></div>
      {applications.length > 0 && <Link href={kyc?.can_apply ? "/borrower/apply" : "/borrower/kyc"} className={s.buttonOutline}>{kyc?.can_apply ? "Pengajuan baru" : "Lengkapi KYC"} <ArrowRight size={16} /></Link>}</div>
    <section className={s.list}>{applications.map((item) => <Link className={s.listItem} href={`/borrower/applications/${item.id}`} key={item.id}>
      <div><strong>{item.application_no}</strong><small>{new Date(item.created_at).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })} · {money(item.requested_amount)} · {item.requested_tenor_days} hari</small></div><Status value={item.status} /></Link>)}
      {applications.length === 0 && <div className={s.card} style={{ textAlign: "center", padding: 35 }}><ClipboardCheck size={30} color="#2776ed" /><p style={{ color: "#677b9b", fontSize: 13 }}>Pengajuan pertama Anda akan muncul di sini.</p><Link href={kyc?.can_apply ? "/borrower/apply" : "/borrower/kyc"} className={s.button}>{kyc?.can_apply ? "Mulai ajukan gadai" : "Mulai verifikasi KTP"} <ArrowRight size={16} /></Link></div>}</section>
    <Footer />
  </main></Shell>;
}
