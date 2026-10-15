"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowRight, BellRing, BookOpenCheck, Building2, Database, FileCheck2, KeyRound, Network, PackageSearch, Scale, Settings2, ShieldCheck, TimerReset, Users } from "lucide-react";

const sections = [
  { id: "institution", title: "Profil lembaga & cabang", description: "Identitas legal, izin, pejabat, kantor, wilayah layanan, dan identitas regulator.", icon: Building2, status: "Perlu review", target: "master-data" },
  { id: "products", title: "Produk, tarif & limit", description: "Produk, tenor, LTV, biaya, denda, threshold, dan tanggal efektif kebijakan.", icon: Scale, status: "Aktif", target: "master-data" },
  { id: "workflow", title: "Workflow, SLA & approval", description: "State transition, guard, assignment, escalation, maker-checker, dan matriks kewenangan.", icon: TimerReset, status: "Baseline", target: null },
  { id: "custody", title: "Custody & inventory", description: "Gudang, rak, kapasitas, movement policy, stock opname, dan release control.", icon: PackageSearch, status: "Aktif", target: "master-data" },
  { id: "accounting", title: "Akuntansi & posting rules", description: "Chart of accounts, jurnal otomatis, period lock, cost center, dan rekonsiliasi.", icon: BookOpenCheck, status: "Aktif", target: "../../finance/general-ledger" },
  { id: "regulatory", title: "OJK & SLIK", description: "Reporter identity, template, code set, kalender, validation rule, dan sign-off.", icon: FileCheck2, status: "Perlu validasi", target: "../../reports/regulatory" },
  { id: "access", title: "Tim, peran & akses", description: "Role, cabang, kategori, authority limit, ABAC, dan separation of duty.", icon: Users, status: "Aktif", target: "team-access" },
  { id: "integrations", title: "Integrasi & webhook", description: "Endpoint, secret reference, retry policy, circuit breaker, dan delivery log.", icon: Network, status: "Belum dikonfigurasi", target: null },
  { id: "notifications", title: "Notifikasi & template", description: "Kanal, penerima, eskalasi, quiet hours, dan template pesan terversi.", icon: BellRing, status: "Baseline", target: null },
  { id: "security", title: "Keamanan & retensi", description: "MFA, session, masking, retention schedule, legal hold, dan akses dokumen.", icon: KeyRound, status: "Perlu review", target: "../compliance/audit" },
] as const;

export default function SettingsPage() {
  const { slug } = useParams<{ slug: string }>();
  function href(target: string) {
    if (target.startsWith("../../")) return `/orgs/${slug}/${target.slice(6)}`;
    if (target.startsWith("../")) return `/orgs/${slug}/${target.slice(3)}`;
    return `/orgs/${slug}/management/${target}`;
  }
  return <div className="space-y-5">
    <header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Management · Configuration control</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Pengaturan operasional</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Pusat konfigurasi tenant untuk kebijakan, proses, regulator, keamanan, dan integrasi. Perubahan penting harus terversi, bertanggal efektif, dan melewati approval.</p></header>
    <section className="grid gap-3 sm:grid-cols-3"><Summary icon={Database} label="Configuration model" value="Versioned" detail="Draft → review → approved → effective" /><Summary icon={ShieldCheck} label="Perubahan sensitif" value="Maker-checker" detail="Konflik kewenangan diperiksa" /><Summary icon={Settings2} label="Scope" value="Tenant & cabang" detail="Tidak ada konfigurasi global terselubung" /></section>
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{sections.map(({ id, title, description, icon: Icon, status, target }) => {
      const body = <><div className="flex items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-surface-blue text-primary"><Icon className="h-5 w-5" /></span><div className="min-w-0 flex-1"><h2 className="font-bold">{title}</h2><span className={`mt-2 inline-flex rounded-lg px-2 py-1 text-[10px] font-semibold ${status === "Aktif" ? "bg-emerald-50 text-emerald-700" : status.includes("Perlu") ? "bg-amber-50 text-amber-800" : "bg-surface-soft text-muted-foreground"}`}>{status}</span></div>{target && <ArrowRight className="h-4 w-4 text-muted-foreground" />}</div><p className="mt-4 text-xs leading-5 text-muted-foreground">{description}</p><div className="mt-4 border-t border-border pt-3 text-[11px] text-muted-foreground">Versi, effective date, owner, approval, dan histori perubahan</div></>;
      return target ? <Link key={id} href={href(target)} className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)] transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-[var(--pg-shadow-md)]">{body}</Link> : <article key={id} className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">{body}</article>;
    })}</section>
  </div>;
}

function Summary({ icon: Icon, label, value, detail }: { icon: typeof Database; label: string; value: string; detail: string }) { return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className="h-4 w-4 text-primary" /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 font-bold">{value}</p><p className="mt-1 text-[11px] text-muted-foreground">{detail}</p></article>; }
