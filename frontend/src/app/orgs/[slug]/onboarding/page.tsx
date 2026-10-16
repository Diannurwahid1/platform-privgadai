"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowRight,
  Boxes,
  Building2,
  Check,
  ChevronDown,
  CircleAlert,
  Database,
  Landmark,
  ListChecks,
  LockKeyhole,
  Plus,
  ShieldCheck,
  UserRoundCog,
} from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { useOrgContext } from "@/lib/org-context";
import { listMembers, type Member } from "@/lib/orgs";
import {
  createAssetCategory,
  createBranch,
  createCustodyLocation,
  createLoanProduct,
  createStaffAssignment,
  listAssetCategories,
  listBranches,
  listCustodyLocations,
  listLoanProducts,
  listStaffAssignments,
  type AssetCategoryItem,
  type BranchItem,
  type LoanProductItem,
  type MasterItem,
  type StaffAssignmentItem,
} from "@/lib/operations";

type SetupData = {
  branches: BranchItem[];
  categories: AssetCategoryItem[];
  products: LoanProductItem[];
  locations: MasterItem[];
  staff: StaffAssignmentItem[];
  members: Member[];
};

type SetupKey = "branch" | "category" | "product" | "custody" | "staff";

const fieldClass =
  "h-11 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none transition focus:border-primary/60 focus:ring-4 focus:ring-primary/8";

const workflows = [
  ["01", "Registrasi & KYC", "Rekam nasabah, foto KTP, persetujuan, OCR, dan keputusan CDD."],
  ["02", "Pengajuan", "Pilih produk, cabang, agunan, tenor, dan nilai yang diminta."],
  ["03", "Penaksiran", "Penaksir memeriksa bukti, kondisi, pembanding, LTV, dan rekomendasi."],
  ["04", "Approval & penawaran", "Maker dan checker memutuskan serta menerbitkan penawaran."],
  ["05", "Pencairan & custody", "Teller mencairkan, custodian menerima barang, segel, dan passport."],
  ["06", "Servicing", "Kelola angsuran, pelunasan, perpanjangan, lelang, dan pengembalian agunan."],
];

export default function OnboardingPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const { org, role } = useOrgContext();
  const [data, setData] = useState<SetupData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [open, setOpen] = useState<SetupKey | null>(null);

  const load = useCallback(async () => {
    const [branches, categories, products, locations, staff, members] = await Promise.all([
      listBranches(),
      listAssetCategories(),
      listLoanProducts(),
      listCustodyLocations(),
      listStaffAssignments(),
      listMembers(slug),
    ]);
    setData({ branches, categories, products, locations, staff, members });
  }, [slug]);

  useEffect(() => {
    load().catch((reason: { detail?: string }) =>
      setError(reason.detail ?? "Status setup tenant gagal dimuat."),
    );
  }, [load]);

  const steps = useMemo(() => {
    if (!data) return [];
    return [
      { key: "tenant", label: "Tenant aktif", done: Boolean(org), count: 1 },
      { key: "branch", label: "Cabang", done: data.branches.length > 0, count: data.branches.length },
      { key: "category", label: "Kategori agunan", done: data.categories.length > 0, count: data.categories.length },
      { key: "product", label: "Produk gadai", done: data.products.length > 0, count: data.products.length },
      { key: "custody", label: "Lokasi custody", done: data.locations.length > 0, count: data.locations.length },
      {
        key: "staff",
        label: "Tim & maker-checker",
        done: data.members.length >= 2 && data.staff.length >= 2,
        count: data.staff.length,
      },
    ];
  }, [data, org]);

  useEffect(() => {
    if (!data || open) return;
    const next = steps.find((step) => !step.done && step.key !== "tenant");
    if (next) setOpen(next.key as SetupKey);
  }, [data, open, steps]);

  if (!data && !error) return <LoadingState label="Memeriksa kesiapan operasional tenant" />;
  if (!data) return <ErrorState message={error ?? "Setup tenant gagal dimuat."} />;

  const editable = role === "owner" || role === "admin";
  const completed = steps.filter((step) => step.done).length;
  const percent = Math.round((completed / steps.length) * 100);
  const ready = completed === steps.length;

  async function run(label: string, action: () => Promise<unknown>, success: string) {
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      await action();
      await load();
      setMessage(success);
      return true;
    } catch (reason) {
      setError((reason as { detail?: string }).detail ?? "Data setup gagal disimpan.");
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function submit(kind: SetupKey, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    const saved = await run(kind, async () => {
      if (kind === "branch") await createBranch(values);
      if (kind === "category") {
        await createAssetCategory({
          ...values,
          requires_serial_number: values.requires_serial_number === "on",
        });
      }
      if (kind === "product") {
        await createLoanProduct({
          ...values,
          min_amount: Number(values.min_amount),
          max_amount: Number(values.max_amount),
          max_ltv_percent: Number(values.max_ltv_percent),
          service_fee_percent: Number(values.service_fee_percent),
          allowed_tenors_days: String(values.allowed_tenors_days).split(",").map(Number),
          agreement_type: "pawn",
        });
      }
      if (kind === "custody") await createCustodyLocation(values);
      if (kind === "staff") await createStaffAssignment(values);
    }, "Data setup berhasil disimpan dan status kesiapan diperbarui.");
    if (saved) form.reset();
  }

  return (
    <div className="space-y-7">
      <section className="overflow-hidden rounded-[28px] border border-border bg-[linear-gradient(135deg,#071a35_0%,#0d3471_58%,#1857b7_100%)] text-white shadow-[var(--pg-shadow-lg)]">
        <div className="grid gap-8 p-6 sm:p-8 xl:grid-cols-[1fr_360px] xl:items-center">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-blue-100">
                <ListChecks className="h-3.5 w-3.5" /> Setup operasional
              </span>
              <span className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-1.5 text-[10px] font-bold text-emerald-100">
                Tenant terisolasi · {org?.name}
              </span>
            </div>
            <h1 className="mt-5 max-w-3xl text-3xl font-bold tracking-[-0.045em] sm:text-4xl">
              Siapkan PrivGadai sebelum transaksi pertama
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-blue-100/80">
              Ikuti urutan ini agar cabang, produk, tempat penyimpanan, dan pemisahan tugas tersedia saat pengajuan mulai diproses.
            </p>
          </div>
          <div className="rounded-2xl border border-white/15 bg-white/10 p-5 backdrop-blur-sm">
            <div className="flex items-end justify-between">
              <div><p className="text-xs text-blue-100/70">Kesiapan tenant</p><p className="mt-1 text-3xl font-bold">{percent}%</p></div>
              <span className="text-xs font-semibold text-blue-100">{completed} dari {steps.length} selesai</span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/15"><div className="h-full rounded-full bg-emerald-400 transition-all" style={{ width: `${percent}%` }} /></div>
            <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-blue-50/85">
              {ready ? <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /> : <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />}
              {ready ? "Konfigurasi minimum dan maker-checker telah siap." : "Selesaikan item yang belum siap sebelum operasional penuh."}
            </p>
          </div>
        </div>
      </section>

      {(error || message) && (
        <div role="status" className={`rounded-2xl border px-4 py-3 text-sm ${error ? "border-red-200 bg-red-50 text-red-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
          {error ?? message}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="space-y-3">
          <div className="mb-4">
            <h2 className="text-lg font-bold">Checklist kesiapan</h2>
            <p className="mt-1 text-sm text-muted-foreground">Isi satu per satu. Status diperbarui dari data master tenant.</p>
          </div>

          <DoneRow icon={Landmark} title="Tenant dan ruang kerja" detail={`${org?.name} · peran Anda ${role}`} />

          <SetupRow icon={Building2} title="1. Cabang operasional" detail="Menentukan unit kerja, kas, transaksi, dan cakupan petugas." done={data.branches.length > 0} count={`${data.branches.length} cabang`} open={open === "branch"} onToggle={() => setOpen(open === "branch" ? null : "branch")}>
            <SetupForm editable={editable} onSubmit={(event) => submit("branch", event)} busy={busy === "branch"}>
              <div className="grid gap-3 sm:grid-cols-2"><Field label="Kode cabang"><input name="code" required placeholder="JKT-01" className={fieldClass} /></Field><Field label="Kota"><input name="city" required placeholder="Jakarta" className={fieldClass} /></Field></div>
              <Field label="Nama cabang"><input name="name" required placeholder="Cabang Jakarta Pusat" className={fieldClass} /></Field>
              <Field label="Alamat"><input name="address" placeholder="Alamat lengkap cabang" className={fieldClass} /></Field>
            </SetupForm>
          </SetupRow>

          <SetupRow icon={Boxes} title="2. Kategori agunan" detail="Aturan data barang seperti emas, elektronik, atau kendaraan." done={data.categories.length > 0} count={`${data.categories.length} kategori`} open={open === "category"} onToggle={() => setOpen(open === "category" ? null : "category")}>
            <SetupForm editable={editable} onSubmit={(event) => submit("category", event)} busy={busy === "category"}>
              <div className="grid gap-3 sm:grid-cols-2"><Field label="Kode kategori"><input name="code" required placeholder="EMAS" className={fieldClass} /></Field><Field label="Nama kategori"><input name="name" required placeholder="Emas dan logam mulia" className={fieldClass} /></Field></div>
              <Field label="Deskripsi"><input name="description" placeholder="Dokumen dan atribut pemeriksaan" className={fieldClass} /></Field>
              <label className="flex items-center gap-2 text-xs text-muted-foreground"><input type="checkbox" name="requires_serial_number" /> Nomor seri wajib dicatat</label>
            </SetupForm>
          </SetupRow>

          <SetupRow icon={Database} title="3. Produk gadai" detail="Batas pembiayaan, LTV, tenor, dan biaya yang ditawarkan." done={data.products.length > 0} count={`${data.products.length} produk`} open={open === "product"} onToggle={() => setOpen(open === "product" ? null : "product")}>
            <SetupForm editable={editable} onSubmit={(event) => submit("product", event)} busy={busy === "product"}>
              <div className="grid gap-3 sm:grid-cols-2"><Field label="Kode produk"><input name="code" required placeholder="GADAI-REG" className={fieldClass} /></Field><Field label="Nama produk"><input name="name" required placeholder="Gadai Reguler" className={fieldClass} /></Field></div>
              <div className="grid gap-3 sm:grid-cols-2"><Field label="Pembiayaan minimum"><input name="min_amount" type="number" min="1" required defaultValue="500000" className={fieldClass} /></Field><Field label="Pembiayaan maksimum"><input name="max_amount" type="number" min="1" required defaultValue="100000000" className={fieldClass} /></Field></div>
              <div className="grid gap-3 sm:grid-cols-3"><Field label="LTV maksimum %"><input name="max_ltv_percent" type="number" min="1" max="100" required defaultValue="85" className={fieldClass} /></Field><Field label="Biaya layanan %"><input name="service_fee_percent" type="number" min="0" max="100" step="0.01" required defaultValue="1" className={fieldClass} /></Field><Field label="Tenor hari"><input name="allowed_tenors_days" required defaultValue="30,60,90,120" className={fieldClass} /></Field></div>
            </SetupForm>
          </SetupRow>

          <SetupRow icon={LockKeyhole} title="4. Vault dan custody" detail="Lokasi fisik penyimpanan serta dasar chain of custody agunan." done={data.locations.length > 0} count={`${data.locations.length} lokasi`} open={open === "custody"} onToggle={() => setOpen(open === "custody" ? null : "custody")}>
            {data.branches.length ? <SetupForm editable={editable} onSubmit={(event) => submit("custody", event)} busy={busy === "custody"}>
              <div className="grid gap-3 sm:grid-cols-2"><Field label="Cabang"><select name="branch_id" required className={fieldClass}>{data.branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.code} · {branch.name}</option>)}</select></Field><Field label="Jenis lokasi"><select name="location_type" className={fieldClass}><option value="branch_vault">Vault cabang</option><option value="central_vault">Vault pusat</option><option value="temporary">Penyimpanan sementara</option></select></Field></div>
              <div className="grid gap-3 sm:grid-cols-2"><Field label="Kode lokasi"><input name="code" required placeholder="VAULT-JKT-01" className={fieldClass} /></Field><Field label="Nama lokasi"><input name="name" required placeholder="Vault Utama JKT-01" className={fieldClass} /></Field></div>
            </SetupForm> : <DependencyNote text="Buat cabang terlebih dahulu sebelum menentukan lokasi custody." />}
          </SetupRow>

          <SetupRow icon={UserRoundCog} title="5. Tim dan maker-checker" detail="Minimal dua pengguna dan dua penugasan operasional untuk pemisahan tugas." done={data.members.length >= 2 && data.staff.length >= 2} count={`${data.members.length} anggota · ${data.staff.length} penugasan`} open={open === "staff"} onToggle={() => setOpen(open === "staff" ? null : "staff")}>
            {data.branches.length ? <>
              <SetupForm editable={editable} onSubmit={(event) => submit("staff", event)} busy={busy === "staff"}>
                <div className="grid gap-3 sm:grid-cols-3"><Field label="Anggota"><select name="user_id" required className={fieldClass}>{data.members.map((member) => <option key={member.user_id} value={member.user_id}>{member.full_name ?? member.email}</option>)}</select></Field><Field label="Cabang"><select name="branch_id" required className={fieldClass}>{data.branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.code} · {branch.name}</option>)}</select></Field><Field label="Peran operasional"><select name="operational_role" className={fieldClass}><option value="ops_admin">Admin operasi</option><option value="branch_manager">Kepala cabang</option><option value="loan_officer">Petugas kredit</option><option value="reviewer">Reviewer</option><option value="appraiser">Penaksir</option><option value="custodian">Custodian</option><option value="finance">Finance</option><option value="auditor">Auditor</option></select></Field></div>
              </SetupForm>
              <div className="mt-3 flex flex-col gap-3 rounded-xl bg-amber-50 p-4 text-xs text-amber-900 sm:flex-row sm:items-center sm:justify-between"><span><strong>Pemisahan tugas:</strong> undang pengguna kedua lalu berikan peran reviewer atau kepala cabang.</span><Link href={`/orgs/${slug}/management/team-access`} className="shrink-0 font-bold text-primary">Kelola tim <ArrowRight className="ml-1 inline h-3.5 w-3.5" /></Link></div>
            </> : <DependencyNote text="Buat cabang terlebih dahulu sebelum menugaskan petugas." />}
          </SetupRow>
        </section>

        <aside className="space-y-4 xl:sticky xl:top-24 xl:self-start">
          <section className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
            <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-surface-blue text-primary"><ShieldCheck className="h-5 w-5" /></span><div><h2 className="font-bold">Langkah berikutnya</h2><p className="text-xs text-muted-foreground">Setelah konfigurasi dasar</p></div></div>
            <div className="mt-5 space-y-2">
              {steps.map((step) => <div key={step.key} className="flex items-center gap-3 rounded-xl bg-surface-soft px-3 py-2.5 text-xs"><span className={`grid h-6 w-6 place-items-center rounded-full ${step.done ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>{step.done ? <Check className="h-3.5 w-3.5" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}</span><span className="flex-1 font-semibold">{step.label}</span><span className="text-muted-foreground">{step.count}</span></div>)}
            </div>
            <Link href={`/orgs/${slug}/overview`} className={`mt-5 flex h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-bold ${ready ? "bg-primary text-white" : "border border-border bg-background text-foreground"}`}>Masuk dashboard <ArrowRight className="h-4 w-4" /></Link>
            {!ready && <p className="mt-3 text-center text-[11px] leading-5 text-muted-foreground">Dashboard tetap dapat dibuka untuk melihat data. Transaksi nyata sebaiknya dimulai setelah semua kontrol siap.</p>}
          </section>
          <section className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
            <h2 className="font-bold">Butuh pengaturan rinci?</h2>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">Master Data memuat daftar lengkap. Tim & Akses digunakan untuk undangan, role tenant, dan pergantian anggota.</p>
            <div className="mt-4 grid gap-2"><Link className="rounded-xl border border-border px-3 py-2.5 text-xs font-bold hover:bg-surface-soft" href={`/orgs/${slug}/management/master-data`}>Buka Master Data</Link><Link className="rounded-xl border border-border px-3 py-2.5 text-xs font-bold hover:bg-surface-soft" href={`/orgs/${slug}/management/team-access`}>Buka Tim & Akses</Link></div>
          </section>
        </aside>
      </div>

      <section className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)] sm:p-6">
        <div className="max-w-2xl"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Peta kerja harian</p><h2 className="mt-2 text-xl font-bold">Bagaimana transaksi gadai diproses</h2><p className="mt-2 text-sm text-muted-foreground">Gunakan urutan ini sebagai panduan setelah master data siap.</p></div>
        <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{workflows.map(([number, title, description]) => <article key={number} className="rounded-2xl border border-border bg-surface-soft p-4"><div className="flex items-start gap-3"><span className="font-mono text-xs font-bold text-primary">{number}</span><div><h3 className="text-sm font-bold">{title}</h3><p className="mt-1.5 text-xs leading-5 text-muted-foreground">{description}</p></div></div></article>)}</div>
      </section>
    </div>
  );
}

function SetupRow({ icon: Icon, title, detail, done, count, open, onToggle, children }: { icon: typeof Building2; title: string; detail: string; done: boolean; count: string; open: boolean; onToggle: () => void; children: ReactNode }) {
  return <article className={`overflow-hidden rounded-2xl border bg-surface shadow-[var(--pg-shadow-sm)] ${open ? "border-primary/30" : "border-border"}`}><button type="button" onClick={onToggle} aria-expanded={open} className="flex w-full items-center gap-4 p-4 text-left sm:p-5"><span className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl ${done ? "bg-emerald-50 text-emerald-700" : "bg-surface-blue text-primary"}`}>{done ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}</span><span className="min-w-0 flex-1"><span className="block text-sm font-bold">{title}</span><span className="mt-1 block text-xs leading-5 text-muted-foreground">{detail}</span></span><span className={`hidden rounded-full px-2.5 py-1 text-[10px] font-bold sm:inline-flex ${done ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{done ? "Siap" : "Belum siap"} · {count}</span><ChevronDown className={`h-4 w-4 shrink-0 text-muted-foreground transition ${open ? "rotate-180" : ""}`} /></button>{open && <div className="border-t border-border bg-surface-soft/45 p-4 sm:p-5">{children}</div>}</article>;
}

function DoneRow({ icon: Icon, title, detail }: { icon: typeof Landmark; title: string; detail: string }) {
  return <article className="flex items-center gap-4 rounded-2xl border border-border bg-surface p-4 shadow-[var(--pg-shadow-sm)] sm:p-5"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><Icon className="h-5 w-5" /></span><span className="min-w-0 flex-1"><span className="block text-sm font-bold">{title}</span><span className="mt-1 block truncate text-xs text-muted-foreground">{detail}</span></span><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-700">Siap</span></article>;
}

function SetupForm({ editable, onSubmit, busy, children }: { editable: boolean; onSubmit: (event: FormEvent<HTMLFormElement>) => void; busy: boolean; children: ReactNode }) {
  if (!editable) return <DependencyNote text="Peran owner atau admin diperlukan untuk mengubah konfigurasi ini." />;
  return <form onSubmit={onSubmit} className="space-y-3">{children}<button disabled={busy} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-white disabled:opacity-50"><Plus className="h-4 w-4" />{busy ? "Menyimpan…" : "Simpan dan lanjutkan"}</button></form>;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="grid gap-1.5 text-xs font-semibold text-foreground"><span>{label}</span>{children}</label>;
}

function DependencyNote({ text }: { text: string }) {
  return <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />{text}</div>;
}
