"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, FileText, PackageSearch, UserRound } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  createApplication,
  listAssetCategories,
  listBranches,
  listLoanProducts,
  type AssetCategoryItem,
  type BranchItem,
  type LoanProductItem,
} from "@/lib/operations";

const input = "h-11 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/8";

export default function NewApplicationPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [masters, setMasters] = useState<{ branches: BranchItem[]; categories: AssetCategoryItem[]; products: LoanProductItem[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([listBranches(), listAssetCategories(), listLoanProducts()])
      .then(([branches, categories, products]) => setMasters({ branches, categories, products }))
      .catch((reason: { detail?: string }) => setError(reason.detail ?? "Master data belum dapat dimuat"));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!masters) return;
    setBusy(true);
    setError(null);
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const result = await createApplication({
        branch_id: values.branch_id,
        product_id: values.product_id,
        borrower: { full_name: values.full_name, phone: values.phone, customer_reference: values.customer_reference || null },
        asset: {
          category_code: values.category_code,
          brand: values.brand || null,
          model: values.model || null,
          condition_grade: values.condition_grade,
          indicative_value: Number(values.indicative_value),
        },
        requested_amount: Number(values.requested_amount),
        requested_tenor_days: Number(values.requested_tenor_days),
        purpose: values.purpose,
        priority: values.priority,
        consent_document_version: "PRIV-2026.1",
        submit: true,
      });
      router.push(`/orgs/${slug}/loans/applications/${result.application_id}`);
    } catch (reason) {
      setError((reason as { detail?: string }).detail ?? "Pengajuan gagal dibuat");
      setBusy(false);
    }
  }

  if (!masters && !error) return <LoadingState label="Menyiapkan formulir pengajuan" />;
  if (!masters) return <ErrorState message={error ?? "Master data belum tersedia"} />;
  if (!masters.branches.length || !masters.categories.length || !masters.products.length) {
    return <ErrorState message="Lengkapi cabang, kategori agunan, dan produk pinjaman di Master Data sebelum membuat pengajuan." actionHref={`/orgs/${slug}/master-data`} actionLabel="Buka Master Data" />;
  }
  const defaultProduct = masters.products[0];

  return <div className="mx-auto max-w-5xl space-y-6">
    <header><Link href={`/orgs/${slug}/loans/applications`} className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-primary"><ArrowLeft className="h-4 w-4" /> Kembali ke inbox</Link><p className="mt-5 text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Borrower intake</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Pengajuan gadai baru</h1><p className="mt-2 text-sm text-muted-foreground">Data persetujuan, nasabah, produk, dan identitas aset dicatat dalam satu transaksi tenant.</p></header>
    {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
    <form onSubmit={submit} className="space-y-5">
      <Section icon={UserRound} title="Identitas nasabah" description="Kontak ditampilkan dalam bentuk tersamarkan setelah tersimpan.">
        <div className="grid gap-3 md:grid-cols-2"><Field label="Nama lengkap"><input name="full_name" required className={input} /></Field><Field label="Nomor telepon"><input name="phone" required minLength={8} className={input} /></Field></div>
        <Field label="Referensi nasabah (opsional)"><input name="customer_reference" className={input} placeholder="Otomatis bila dikosongkan" /></Field>
      </Section>
      <Section icon={FileText} title="Produk dan kebutuhan dana" description="Batas nominal dan tenor divalidasi terhadap produk tenant.">
        <div className="grid gap-3 md:grid-cols-2"><Field label="Cabang"><select name="branch_id" className={input}>{masters.branches.map((x) => <option key={x.id} value={x.id}>{x.code} · {x.name}</option>)}</select></Field><Field label="Produk"><select name="product_id" className={input}>{masters.products.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select></Field></div>
        <div className="grid gap-3 md:grid-cols-3"><Field label="Dana diminta"><input name="requested_amount" type="number" required min={Number(defaultProduct.min_amount)} max={Number(defaultProduct.max_amount)} className={input} /></Field><Field label="Tenor"><select name="requested_tenor_days" className={input}>{defaultProduct.allowed_tenors_days.map((day) => <option key={day} value={day}>{day} hari</option>)}</select></Field><Field label="Prioritas"><select name="priority" className={input}><option value="normal">Normal</option><option value="high">Tinggi</option><option value="urgent">Urgent</option></select></Field></div>
        <Field label="Tujuan penggunaan"><textarea name="purpose" required className="min-h-24 w-full rounded-xl border border-border bg-background p-3 text-sm outline-none focus:border-primary" /></Field>
      </Section>
      <Section icon={PackageSearch} title="Barang jaminan" description="Nilai awal tetap harus dikonfirmasi oleh penaksir manusia.">
        <div className="grid gap-3 md:grid-cols-2"><Field label="Kategori"><select name="category_code" className={input}>{masters.categories.map((x) => <option key={x.id} value={x.code}>{x.name}</option>)}</select></Field><Field label="Nilai indikatif"><input name="indicative_value" type="number" required min="1" className={input} /></Field></div>
        <div className="grid gap-3 md:grid-cols-3"><Field label="Merek"><input name="brand" className={input} /></Field><Field label="Model"><input name="model" className={input} /></Field><Field label="Kondisi awal"><select name="condition_grade" className={input}><option value="A">A · Sangat baik</option><option value="B">B · Baik</option><option value="C">C · Cukup</option></select></Field></div>
      </Section>
      <label className="flex items-start gap-3 rounded-2xl border border-success/20 bg-success/5 p-4 text-xs leading-5"><input required type="checkbox" className="mt-1" /><CheckCircle2 className="h-5 w-5 shrink-0 text-success" /><span>Nasabah telah membaca dan menyetujui pemrosesan data, verifikasi kredit, serta versi persetujuan PRIV-2026.1.</span></label>
      <button disabled={busy} className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-white disabled:opacity-50">{busy ? "Menyimpan..." : "Buat dan kirim pengajuan"}<ArrowRight className="h-4 w-4" /></button>
    </form>
  </div>;
}

function Section({ icon: Icon, title, description, children }: { icon: typeof UserRound; title: string; description: string; children: React.ReactNode }) { return <section className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><div className="flex gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-surface-blue text-primary"><Icon className="h-5 w-5" /></span><div><h2 className="font-bold">{title}</h2><p className="mt-1 text-xs text-muted-foreground">{description}</p></div></div><div className="mt-5 space-y-3">{children}</div></section>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="grid gap-1.5 text-xs font-semibold text-foreground"><span>{label}</span>{children}</label>; }
