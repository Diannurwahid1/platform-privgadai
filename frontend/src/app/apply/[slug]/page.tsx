"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import { CheckCircle2, LockKeyhole, PackageSearch, ShieldCheck, Sparkles } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  getPublicIntakeConfig,
  submitPublicApplication,
  type PublicIntakeConfig,
} from "@/lib/operations";

const input = "h-12 w-full rounded-xl border border-border bg-white px-3 text-sm outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/8";

export default function BorrowerIntakePage() {
  const { slug } = useParams<{ slug: string }>();
  const [config, setConfig] = useState<PublicIntakeConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reference, setReference] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { getPublicIntakeConfig(slug).then(setConfig).catch((reason: { detail?: string }) => setError(reason.detail ?? "Mitra tidak ditemukan")); }, [slug]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!config) return; setBusy(true); setError(null);
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const result = await submitPublicApplication(slug, {
        branch_id: values.branch_id,
        product_id: values.product_id,
        borrower: { full_name: values.full_name, phone: values.phone },
        asset: { category_code: values.category_code, brand: values.brand || null, model: values.model || null, condition_grade: values.condition_grade, indicative_value: Number(values.indicative_value) },
        requested_amount: Number(values.requested_amount),
        requested_tenor_days: Number(values.requested_tenor_days),
        purpose: values.purpose,
        priority: "normal",
        consent_document_version: config.consent_version,
        submit: true,
      });
      setReference(result.application_id);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (reason) { setError((reason as { detail?: string }).detail ?? "Pengajuan gagal dikirim"); }
    finally { setBusy(false); }
  }

  if (error && !config) return <ErrorState message={error} />;
  if (!config) return <LoadingState label="Membuka portal nasabah" />;
  if (reference) return <main className="grid min-h-screen place-items-center px-5"><section className="max-w-lg rounded-[32px] border border-border bg-surface p-8 text-center shadow-[var(--pg-shadow-lg)]"><span className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-success/10 text-success"><CheckCircle2 className="h-8 w-8" /></span><h1 className="mt-5 text-3xl font-bold">Pengajuan terkirim</h1><p className="mt-3 text-sm leading-6 text-muted-foreground">Tim {config.partner.name} akan memeriksa data dan aset. Nilai final selalu ditentukan oleh penaksir manusia.</p><p className="mt-5 rounded-xl bg-surface-soft p-3 font-mono text-xs text-primary">Referensi: {reference}</p></section></main>;
  const product = config.loan_products[0];
  if (!product || !config.branches.length || !config.asset_categories.length) return <ErrorState message="Mitra belum membuka konfigurasi produk untuk pengajuan online." />;

  return <main className="min-h-screen bg-background">
    <section className="pg-section-dark relative overflow-hidden px-5 py-12 sm:py-16"><div className="mx-auto max-w-5xl"><div><Image src="/privgadai-logo-light.svg" alt="PrivGadai" width={390} height={190} className="h-14 w-auto" priority /><p className="-mt-1 pl-1 text-[10px] uppercase tracking-[0.18em] text-blue-200/70">Portal nasabah</p></div><div className="mt-10 max-w-2xl"><span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-blue-100"><Sparkles className="h-3.5 w-3.5" /> {config.partner.name}</span><h1 className="mt-5 text-4xl font-bold tracking-[-0.05em] sm:text-5xl">Ajukan pembiayaan dengan agunan secara transparan.</h1><p className="mt-4 max-w-xl text-sm leading-7 text-blue-100/70">Isi satu pengajuan aset. Mitra berizin melakukan review, appraisal manusia, penawaran, dan custody.</p></div></div></section>
    <section className="mx-auto grid max-w-5xl gap-6 px-5 py-10 lg:grid-cols-[minmax(0,1fr)_300px]">
      <form onSubmit={submit} className="space-y-5 rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-md)] sm:p-7">
        <div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-primary">Form pengajuan</p><h2 className="mt-2 text-2xl font-bold">Data nasabah dan aset</h2></div>
        {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <div className="grid gap-3 sm:grid-cols-2"><Field label="Nama lengkap"><input name="full_name" required className={input} /></Field><Field label="Nomor telepon"><input name="phone" required minLength={8} className={input} /></Field></div>
        <div className="grid gap-3 sm:grid-cols-2"><Field label="Cabang tujuan"><select name="branch_id" className={input}>{config.branches.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select></Field><Field label="Produk"><select name="product_id" className={input}>{config.loan_products.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select></Field></div>
        <div className="grid gap-3 sm:grid-cols-2"><Field label="Kategori barang"><select name="category_code" className={input}>{config.asset_categories.map((x) => <option key={x.id} value={x.code}>{x.name}</option>)}</select></Field><Field label="Kondisi awal"><select name="condition_grade" className={input}><option value="A">Sangat baik</option><option value="B">Baik</option><option value="C">Cukup</option></select></Field></div>
        <div className="grid gap-3 sm:grid-cols-2"><Field label="Merek"><input name="brand" className={input} /></Field><Field label="Model / tipe"><input name="model" className={input} /></Field></div>
        <div className="grid gap-3 sm:grid-cols-3"><Field label="Nilai indikatif"><input name="indicative_value" type="number" min="1" required className={input} /></Field><Field label="Dana diminta"><input name="requested_amount" type="number" min={product.min_amount} max={product.max_amount} required className={input} /></Field><Field label="Tenor"><select name="requested_tenor_days" className={input}>{product.allowed_tenors_days.map((day) => <option key={day} value={day}>{day} hari</option>)}</select></Field></div>
        <Field label="Tujuan penggunaan dana"><textarea name="purpose" required className="min-h-24 w-full rounded-xl border border-border bg-white p-3 text-sm outline-none focus:border-primary" /></Field>
        <label className="flex items-start gap-3 rounded-xl bg-surface-soft p-4 text-xs leading-5"><input type="checkbox" required className="mt-1" /><span>Saya menyetujui pemrosesan data dan pemeriksaan pengajuan sesuai dokumen versi {config.consent_version}.</span></label>
        <button disabled={busy} className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary text-sm font-bold text-white disabled:opacity-50"><PackageSearch className="h-4 w-4" /> {busy ? "Mengirim..." : "Kirim pengajuan"}</button>
      </form>
      <aside className="space-y-4"><Info icon={ShieldCheck} title="Mitra terpisah" text="Pengajuan hanya masuk ke tenant mitra yang tampil di halaman ini." /><Info icon={LockKeyhole} title="Keputusan manusia" text="Nilai indikatif bukan keputusan final. Appraisal dan offer memerlukan persetujuan petugas." /><Info icon={CheckCircle2} title="Jejak proses" text="Status dan perpindahan agunan dicatat dalam Collateral Passport." /></aside>
    </section>
  </main>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="grid gap-1.5 text-xs font-semibold"><span>{label}</span>{children}</label>; }
function Info({ icon: Icon, title, text }: { icon: typeof ShieldCheck; title: string; text: string }) { return <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><Icon className="h-5 w-5 text-primary" /><h3 className="mt-4 text-sm font-bold">{title}</h3><p className="mt-2 text-xs leading-5 text-muted-foreground">{text}</p></article>; }
