"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, BriefcaseBusiness, CalendarClock, Copy, FileCheck2, Landmark, PackageSearch, Plus, Printer, ShieldCheck, UserRound } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { getCustomerDetail, type CustomerDetail } from "@/lib/operations";

const idr = (value: unknown) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));
const date = (value: unknown) => value ? new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(String(value))) : "—";
const labels: Record<string, string> = { submitted: "Diajukan", under_review: "Dalam review", appraisal: "Penaksiran", offered: "Ditawarkan", accepted: "Disetujui", active: "Aktif", settled: "Lunas", normal: "Normal" };

export default function CustomerDetailPage() {
  const params = useParams<{ slug: string; id: string }>();
  const slug = params.slug;
  const [data, setData] = useState<CustomerDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("overview");
  const tabs = useMemo(() => [
    ["overview", "Ringkasan"], ["identity", "Identitas & KYC"], ["facilities", `Pengajuan & Pinjaman (${data?.applications.length ?? 0})`],
    ["collateral", "Agunan"], ["consent", `Consent (${data?.consents.length ?? 0})`], ["activity", "Aktivitas"],
  ], [data]);

  useEffect(() => {
    getCustomerDetail(params.id).then(setData).catch((reason: { detail?: string }) => setError(reason.detail ?? "Detail debitur gagal dimuat"));
  }, [params.id]);

  if (error) return <ErrorState message={error} actionHref={`/orgs/${slug}/customers`} actionLabel="Kembali ke daftar debitur" />;
  if (!data) return <LoadingState label="Menyusun profil debitur 360°" />;

  return <div className="space-y-5">
    <Link href={`/orgs/${slug}/customers`} className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-primary"><ArrowLeft className="h-4 w-4" /> Debitur & CRM</Link>
    <section className="rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
      <div className="flex flex-col gap-5 p-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex min-w-0 gap-4">
          <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-surface-blue text-primary"><UserRound className="h-7 w-7" /></span>
          <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h1 className="truncate text-2xl font-bold tracking-tight">{data.full_name}</h1><Status label={data.profile.internal_watchlist ? "Watchlist" : (labels[data.profile.risk_status] ?? data.profile.risk_status)} alert={data.profile.internal_watchlist || data.profile.risk_status === "high"} /></div><p className="mt-1 font-mono text-xs text-primary">{data.customer_reference}</p><p className="mt-2 text-xs text-muted-foreground">Terdaftar {date(data.created_at)} · {data.phone_masked}</p></div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => navigator.clipboard.writeText(data.customer_reference)} className="inline-flex h-10 items-center gap-2 rounded-xl border border-border px-3 text-xs font-semibold"><Copy className="h-4 w-4" /> Salin CIF</button>
          <button type="button" onClick={() => window.print()} className="inline-flex h-10 items-center gap-2 rounded-xl border border-border px-3 text-xs font-semibold"><Printer className="h-4 w-4" /> Cetak ringkasan</button>
          <Link href={`/orgs/${slug}/loans/applications/new`} className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-white"><Plus className="h-4 w-4" /> Pengajuan baru</Link>
        </div>
      </div>
      <div className="flex gap-1 overflow-x-auto border-t border-border px-4 pt-2">{tabs.map(([value, label]) => <button key={value} type="button" onClick={() => setTab(value)} className={`shrink-0 border-b-2 px-3 py-3 text-xs font-semibold ${tab === value ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>{label}</button>)}</div>
    </section>

    {tab === "overview" && <Overview data={data} slug={slug} />}
    {tab === "identity" && <Identity data={data} />}
    {tab === "facilities" && <Facilities data={data} slug={slug} />}
    {tab === "collateral" && <Collateral data={data} slug={slug} />}
    {tab === "consent" && <Consent data={data} />}
    {tab === "activity" && <Activity data={data} slug={slug} />}
  </div>;
}

function Overview({ data, slug }: { data: CustomerDetail; slug: string }) {
  return <>
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Metric label="Pengajuan" value={String(data.summary.application_count)} icon={BriefcaseBusiness} />
      <Metric label="Pinjaman aktif" value={String(data.summary.active_loan_count)} icon={Landmark} />
      <Metric label="Total outstanding" value={idr(data.summary.total_outstanding)} icon={CalendarClock} />
      <Metric label="Agunan" value={String(data.summary.collateral_count)} icon={PackageSearch} />
      <Metric label="Collection terbuka" value={String(data.summary.open_collection_count)} icon={ShieldCheck} alert={data.summary.open_collection_count > 0} />
    </section>
    <section className="grid gap-4 xl:grid-cols-[1.45fr_1fr]">
      <Panel title="Fasilitas terbaru" subtitle="Pengajuan dan rekening terakhir milik debitur">
        <div className="divide-y divide-border">{data.applications.slice(0, 5).map((item) => <Link key={item.id} href={`/orgs/${slug}/loans/applications/${item.id}`} className="grid gap-2 py-3 first:pt-0 last:pb-0 sm:grid-cols-[1fr_140px_150px] sm:items-center"><div><p className="font-mono text-xs font-semibold text-primary">{item.application_no}</p><p className="mt-1 text-sm font-medium">{item.asset?.label ?? "Aset belum dicatat"}</p></div><span className="text-xs text-muted-foreground">{item.branch_code} · {labels[item.status] ?? item.status}</span><span className="text-right text-sm font-semibold">{idr(item.requested_amount)}</span></Link>)}</div>
        {!data.applications.length && <Empty text="Belum ada pengajuan untuk debitur ini." />}
      </Panel>
      <Panel title="Kontrol data" subtitle="Kelengkapan minimum untuk proses operasional">
        <Check label="Identitas nasional" done={Boolean(data.profile.national_id_masked)} detail={data.profile.national_id_masked ?? "Belum tersedia"} />
        <Check label="Kode DATI II" done={Boolean(data.profile.dati_ii_code)} detail={data.profile.dati_ii_code ?? "Perlu dipetakan"} />
        <Check label="Subjek SLIK" done={Boolean(data.profile.slik_subject_code)} detail={data.profile.slik_subject_code ?? "Perlu dipetakan"} />
        <Check label="Consent tersimpan" done={data.consents.length > 0} detail={`${data.consents.length} bukti consent`} />
      </Panel>
    </section>
  </>;
}

function Identity({ data }: { data: CustomerDetail }) {
  return <section className="grid gap-4 xl:grid-cols-2"><Panel title="Identitas dan referensi" subtitle="Data sensitif ditampilkan sesuai masking akses"><Definition label="Nama lengkap" value={data.full_name} /><Definition label="Nomor identitas" value={data.profile.national_id_masked ?? "Belum tersedia"} /><Definition label="Telepon" value={data.phone_masked} /><Definition label="DATI II" value={data.profile.dati_ii_code ?? "Belum dipetakan"} /><Definition label="Kode subjek SLIK" value={data.profile.slik_subject_code ?? "Belum dipetakan"} /></Panel><Panel title="Profil risiko" subtitle="Status dan catatan yang dipakai pada proses keputusan"><Definition label="Status risiko" value={labels[data.profile.risk_status] ?? data.profile.risk_status} /><Definition label="Watchlist internal" value={data.profile.internal_watchlist ? "Ya" : "Tidak"} /><Definition label="Status koreksi" value={data.profile.correction_status} /><Definition label="Catatan" value={data.profile.risk_notes ?? data.profile.watchlist_reason ?? "Tidak ada catatan"} /></Panel></section>;
}

function Facilities({ data, slug }: { data: CustomerDetail; slug: string }) {
  return <Panel title="Pengajuan dan pinjaman" subtitle="Nilai, status, saldo, dan jatuh tempo per fasilitas"><div className="overflow-x-auto"><table className="w-full min-w-[820px] text-left text-sm"><thead className="border-b border-border text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="py-3">Nomor</th><th>Cabang</th><th>Status</th><th className="text-right">Diminta</th><th className="text-right">Outstanding</th><th>Jatuh tempo</th></tr></thead><tbody className="divide-y divide-border">{data.applications.map((item) => <tr key={item.id}><td className="py-4"><Link className="font-mono text-xs font-semibold text-primary" href={`/orgs/${slug}/loans/applications/${item.id}`}>{item.application_no}</Link></td><td>{item.branch_code}</td><td>{labels[item.loan?.status ?? item.status] ?? item.loan?.status ?? item.status}</td><td className="text-right font-medium">{idr(item.requested_amount)}</td><td className="text-right font-medium">{idr((item.loan?.outstanding_principal ?? 0) + (item.loan?.outstanding_fee ?? 0))}</td><td>{date(item.loan?.due_at)}</td></tr>)}</tbody></table></div>{!data.applications.length && <Empty text="Belum ada fasilitas." />}</Panel>;
}

function Collateral({ data, slug }: { data: CustomerDetail; slug: string }) {
  const assets = data.applications.filter((item) => item.asset);
  return <section className="grid gap-4 lg:grid-cols-2">{assets.map((item) => <Link key={item.id} href={`/orgs/${slug}/loans/applications/${item.id}`} className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)] hover:border-primary/30"><div className="flex items-start gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-surface-blue text-primary"><PackageSearch className="h-5 w-5" /></span><div className="min-w-0"><p className="font-semibold">{item.asset?.label}</p><p className="mt-1 font-mono text-[11px] text-primary">{item.asset?.asset_code}</p></div><Status label={String(item.asset?.collateral_status).replaceAll("_", " ")} /></div><div className="mt-4 grid grid-cols-2 gap-3 text-xs"><Definition label="Kategori" value={item.asset?.category ?? "—"} /><Definition label="Nilai indikatif" value={idr(item.asset?.indicative_value)} /></div></Link>)}{!assets.length && <Empty text="Belum ada agunan tercatat." />}</section>;
}

function Consent({ data }: { data: CustomerDetail }) {
  return <Panel title="Consent dan dokumen" subtitle="Versi, kanal, serta waktu persetujuan"><div className="divide-y divide-border">{data.consents.map((item) => <div key={String(item.id)} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0"><span className="grid h-9 w-9 place-items-center rounded-lg bg-emerald-50 text-emerald-700"><FileCheck2 className="h-4 w-4" /></span><div className="flex-1"><p className="text-sm font-semibold">{String(item.consent_type)}</p><p className="mt-1 text-xs text-muted-foreground">Versi {String(item.document_version)} · {String(item.channel)}</p></div><time className="text-xs text-muted-foreground">{date(item.accepted_at)}</time></div>)}</div>{!data.consents.length && <Empty text="Belum ada bukti consent." />}</Panel>;
}

function Activity({ data, slug }: { data: CustomerDetail; slug: string }) {
  return <Panel title="Aktivitas bisnis" subtitle="Perubahan status dari seluruh pengajuan debitur"><div className="relative ml-2 border-l border-border pl-6">{data.activity.map((item) => <div key={String(item.id)} className="relative pb-6 last:pb-0"><span className="absolute -left-[29px] top-1 h-2.5 w-2.5 rounded-full border-2 border-surface bg-primary" /><div className="flex flex-col gap-1 sm:flex-row sm:justify-between"><div><p className="text-sm font-semibold">{labels[String(item.to_status)] ?? String(item.to_status).replaceAll("_", " ")}</p><p className="mt-1 text-xs text-muted-foreground">{String(item.note ?? "Perubahan status operasional")}</p><Link href={`/orgs/${slug}/loans/applications/${String(item.application_id)}`} className="mt-1 inline-block font-mono text-[11px] text-primary">Buka pengajuan</Link></div><time className="text-xs text-muted-foreground">{date(item.occurred_at)}</time></div></div>)}</div>{!data.activity.length && <Empty text="Belum ada aktivitas bisnis." />}</Panel>;
}

function Panel({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) { return <section className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="font-bold">{title}</h2><p className="mt-1 text-xs text-muted-foreground">{subtitle}</p><div className="mt-5 space-y-3">{children}</div></section>; }
function Metric({ label, value, icon: Icon, alert = false }: { label: string; value: string; icon: typeof Landmark; alert?: boolean }) { return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className={`h-4 w-4 ${alert ? "text-destructive" : "text-primary"}`} /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 truncate text-lg font-bold tabular-nums">{value}</p></article>; }
function Status({ label, alert = false }: { label: string; alert?: boolean }) { return <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-semibold ${alert ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{label}</span>; }
function Check({ label, detail, done }: { label: string; detail: string; done: boolean }) { return <div className="flex items-center gap-3 rounded-xl bg-surface-soft p-3"><span className={`grid h-7 w-7 place-items-center rounded-lg ${done ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}><ShieldCheck className="h-4 w-4" /></span><div><p className="text-xs font-semibold">{label}</p><p className="mt-0.5 text-[11px] text-muted-foreground">{detail}</p></div></div>; }
function Definition({ label, value }: { label: string; value: string }) { return <div><dt className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</dt><dd className="mt-1 text-sm font-medium">{value}</dd></div>; }
function Empty({ text }: { text: string }) { return <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">{text}</div>; }
