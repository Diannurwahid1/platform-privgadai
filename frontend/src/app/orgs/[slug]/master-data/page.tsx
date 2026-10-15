"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Boxes, Building2, Database, Plus, ShieldCheck, Users, type LucideIcon } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  createAssetCategory,
  createBranch,
  createLoanProduct,
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

type Masters = {
  branches: BranchItem[];
  categories: AssetCategoryItem[];
  products: LoanProductItem[];
  locations: MasterItem[];
  staff: StaffAssignmentItem[];
};

const field = "h-10 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none focus:border-primary";

export default function MasterDataPage() {
  const [data, setData] = useState<Masters | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [branches, categories, products, locations, staff] = await Promise.all([
      listBranches(),
      listAssetCategories(),
      listLoanProducts(),
      listCustodyLocations(),
      listStaffAssignments(),
    ]);
    setData({ branches, categories, products, locations, staff });
  }, []);

  useEffect(() => {
    load().catch((reason: { detail?: string }) => setError(reason.detail ?? "Master data gagal dimuat"));
  }, [load]);

  async function submit(kind: "branch" | "category" | "product", event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (kind === "branch") await createBranch(values);
      if (kind === "category")
        await createAssetCategory({ ...values, requires_serial_number: values.requires_serial_number === "on" });
      if (kind === "product")
        await createLoanProduct({
          ...values,
          min_amount: Number(values.min_amount),
          max_amount: Number(values.max_amount),
          max_ltv_percent: Number(values.max_ltv_percent),
          service_fee_percent: Number(values.service_fee_percent),
          allowed_tenors_days: String(values.allowed_tenors_days)
            .split(",")
            .map(Number),
        });
      event.currentTarget.reset();
      setMessage("Master data berhasil disimpan.");
      await load();
    } catch (reason) {
      setError((reason as { detail?: string }).detail ?? "Master data gagal disimpan");
    }
  }

  if (!data && !error) return <LoadingState label="Memuat master tenant" />;
  if (!data) return <ErrorState message={error ?? "Master data gagal dimuat"} />;

  const summary: Array<{ label: string; value: number; icon: LucideIcon }> = [
    { label: "Cabang", value: data.branches.length, icon: Building2 },
    { label: "Kategori", value: data.categories.length, icon: Boxes },
    { label: "Produk", value: data.products.length, icon: Database },
    { label: "Lokasi custody", value: data.locations.length, icon: ShieldCheck },
    { label: "Penugasan staf", value: data.staff.length, icon: Users },
  ];

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Tenant configuration</p>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Master data operasional</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Cabang, produk, kategori agunan, custody, dan penugasan staf tersimpan per tenant.
          </p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full border border-success/25 bg-success/8 px-3 py-2 text-xs font-semibold text-success">
          <ShieldCheck className="h-4 w-4" /> Tenant scope aktif
        </span>
      </header>

      {(error || message) && (
        <div className={`rounded-xl border px-4 py-3 text-sm ${error ? "border-red-200 bg-red-50 text-red-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
          {error ?? message}
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {summary.map(({ label, value, icon: Icon }) => (
          <article key={label} className="rounded-2xl border border-border bg-surface p-4 shadow-[var(--pg-shadow-sm)]">
            <Icon className="h-5 w-5 text-primary" />
            <p className="mt-4 text-2xl font-bold">{value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{label}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-3">
        <MasterPanel title="Cabang" items={data.branches.map((x) => [x.code, x.name, x.city])}>
          <form onSubmit={(e) => submit("branch", e)} className="grid gap-2">
            <div className="grid grid-cols-2 gap-2"><input name="code" required placeholder="Kode" className={field} /><input name="city" required placeholder="Kota" className={field} /></div>
            <input name="name" required placeholder="Nama cabang" className={field} />
            <input name="address" placeholder="Alamat" className={field} />
            <SaveButton />
          </form>
        </MasterPanel>
        <MasterPanel title="Kategori agunan" items={data.categories.map((x) => [x.code, x.name, x.requires_serial_number ? "Serial wajib" : "Tanpa serial"])}>
          <form onSubmit={(e) => submit("category", e)} className="grid gap-2">
            <input name="code" required placeholder="Kode kategori" className={field} />
            <input name="name" required placeholder="Nama kategori" className={field} />
            <input name="description" placeholder="Deskripsi" className={field} />
            <label className="flex items-center gap-2 text-xs text-muted-foreground"><input type="checkbox" name="requires_serial_number" /> Nomor seri wajib</label>
            <SaveButton />
          </form>
        </MasterPanel>
        <MasterPanel title="Produk pinjaman" items={data.products.map((x) => [x.code, x.name, `LTV ${x.max_ltv_percent}%`])}>
          <form onSubmit={(e) => submit("product", e)} className="grid gap-2">
            <div className="grid grid-cols-2 gap-2"><input name="code" required placeholder="Kode" className={field} /><input name="name" required placeholder="Nama" className={field} /></div>
            <div className="grid grid-cols-2 gap-2"><input name="min_amount" type="number" required placeholder="Minimum" className={field} /><input name="max_amount" type="number" required placeholder="Maksimum" className={field} /></div>
            <div className="grid grid-cols-2 gap-2"><input name="max_ltv_percent" type="number" required placeholder="LTV %" className={field} /><input name="service_fee_percent" type="number" required placeholder="Fee %" className={field} /></div>
            <input name="allowed_tenors_days" required defaultValue="30,60,90" placeholder="Tenor: 30,60,90" className={field} />
            <SaveButton />
          </form>
        </MasterPanel>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <ListPanel title="Lokasi custody" items={data.locations.map((x) => [x.code, x.name, x.is_active ? "Aktif" : "Nonaktif"])} />
        <ListPanel title="Penugasan staf" items={data.staff.map((x) => [x.user_name, x.branch_name, x.operational_role.replaceAll("_", " ")])} />
      </section>
    </div>
  );
}

function SaveButton() {
  return <button className="mt-1 inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-white"><Plus className="h-4 w-4" /> Tambah</button>;
}

function MasterPanel({ title, items, children }: { title: string; items: string[][]; children: React.ReactNode }) {
  return <article className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="font-bold">{title}</h2><div className="my-4 max-h-52 space-y-2 overflow-auto">{items.map((item) => <Row key={item.join("-")} item={item} />)}</div><div className="border-t border-border pt-4">{children}</div></article>;
}

function ListPanel({ title, items }: { title: string; items: string[][] }) {
  return <article className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="font-bold">{title}</h2><div className="mt-4 space-y-2">{items.map((item) => <Row key={item.join("-")} item={item} />)}</div></article>;
}

function Row({ item }: { item: string[] }) {
  return <div className="flex items-center gap-3 rounded-xl bg-surface-soft px-3 py-2.5 text-xs"><strong className="w-24 truncate text-primary">{item[0]}</strong><span className="flex-1 font-medium">{item[1]}</span><span className="text-muted-foreground">{item[2]}</span></div>;
}
