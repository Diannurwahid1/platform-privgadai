"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Building2, ChevronDown, ChevronLeft, ChevronRight, ClipboardList, ContactRound, LogOut, Menu, Search, SlidersHorizontal, X } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { logout, me, type User } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { ApiError } from "@/lib/api";
import { OrgContextProvider, useOrgContext } from "@/lib/org-context";
import { switchOrg } from "@/lib/orgs";
import { listApplications, listCustomers, type ApplicationQueueItem, type CustomerListItem } from "@/lib/operations";
import { buildPartnerNavigation, isPartnerNavItemActive } from "@/lib/partner-navigation";

function OrgChrome({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useParams<{ slug: string }>();
  const slug = params?.slug as string;
  const { org, error, loading } = useOrgContext();
  const [user, setUser] = useState<User | null>(null);
  const [chromeError, setChromeError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [globalQuery, setGlobalQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<{ customers: CustomerListItem[]; applications: ApplicationQueueItem[] }>({ customers: [], applications: [] });
  const searchInput = useRef<HTMLInputElement>(null);
  const navGroups = useMemo(() => buildPartnerNavigation(slug), [slug]);
  const activeGroup = navGroups.find((group) => group.items.some((item) => isPartnerNavItemActive(item, pathname)))?.id;
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set(navGroups.map((group) => group.id)));

  useEffect(() => {
    me().then(setUser).catch((err: ApiError) => {
      if (err.status === 401) router.replace("/login");
      else setChromeError(err.detail ?? "Gagal memuat profil");
    });
    setCollapsed(window.localStorage.getItem("privgadai.sidebar.collapsed") === "1");
  }, [router]);

  useEffect(() => {
    setMobileOpen(false);
    if (activeGroup) setOpenGroups((current) => new Set([...current, activeGroup]));
  }, [pathname, activeGroup]);

  useEffect(() => {
    function onShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInput.current?.focus();
        setSearchOpen(true);
      }
      if (event.key === "Escape") setSearchOpen(false);
    }
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, []);

  useEffect(() => {
    const keyword = globalQuery.trim().toLocaleLowerCase("id-ID");
    if (keyword.length < 2) {
      setSearchResults({ customers: [], applications: [] });
      setSearchLoading(false);
      return;
    }
    setSearchLoading(true);
    const timer = window.setTimeout(() => {
      Promise.all([listCustomers(), listApplications(100)])
        .then(([customers, applications]) => {
          setSearchResults({
            customers: customers.filter((item) => [item.full_name, item.customer_reference, item.phone_masked].join(" ").toLocaleLowerCase("id-ID").includes(keyword)).slice(0, 5),
            applications: applications.filter((item) => [item.application_no, item.borrower_name, item.asset_label].join(" ").toLocaleLowerCase("id-ID").includes(keyword)).slice(0, 5),
          });
        })
        .catch(() => setSearchResults({ customers: [], applications: [] }))
        .finally(() => setSearchLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [globalQuery]);

  function toggleCollapsed() {
    setCollapsed((current) => {
      window.localStorage.setItem("privgadai.sidebar.collapsed", current ? "0" : "1");
      return !current;
    });
  }

  function toggleGroup(groupId: string) {
    setOpenGroups((current) => {
      const next = new Set(current);
      if (next.has(groupId)) next.delete(groupId); else next.add(groupId);
      return next;
    });
  }

  async function handleLogout() {
    try { await logout(); } finally { router.replace("/login"); }
  }

  if (chromeError || error) return <ErrorState message={chromeError ?? error ?? "Gagal membuka workspace mitra"} actionHref="/dashboard" actionLabel="Kembali ke daftar mitra" />;
  if (loading || !org || !user) return <LoadingState label="Menyiapkan ruang operasi PrivGadai" />;

  const sidebar = (
    <>
      <div className={cn("flex h-[76px] items-center border-b border-white/10", collapsed ? "justify-center px-2" : "px-5")}>
        {collapsed ? <span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-500 text-sm font-black tracking-[-0.08em]">PG</span> : (
          <div className="min-w-0">
            <Image src="/privgadai-logo-light.svg" alt="PrivGadai" width={500} height={190} className="h-10 w-auto max-w-[178px]" priority />
            <p className="mt-0.5 text-[8px] font-semibold uppercase tracking-[0.24em] text-blue-200/55">Partner Operations</p>
          </div>
        )}
      </div>
      <div className={cn("border-b border-white/10", collapsed ? "px-2 py-3" : "px-3 py-3")}>
        <button type="button" title={collapsed ? `${org.name} · Semua cabang` : undefined} className={cn("flex w-full items-center rounded-xl border border-white/10 bg-white/6 text-left transition hover:bg-white/10", collapsed ? "justify-center p-2.5" : "gap-3 px-3 py-3")}>
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-blue-400/15 text-blue-300"><Building2 className="h-4 w-4" /></span>
          {!collapsed && <span className="min-w-0 flex-1"><span className="block truncate text-xs font-semibold">{org.name}</span><span className="mt-0.5 block truncate text-[10px] text-slate-400">Semua cabang · Pilot</span></span>}
          {!collapsed && <ChevronDown className="h-3.5 w-3.5 text-slate-500" />}
        </button>
      </div>
      <nav className="pg-sidebar-scroll min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-2 py-3" aria-label="Navigasi utama">
        {navGroups.map((group) => {
          const isOpen = collapsed || openGroups.has(group.id);
          return <div key={group.id} className="mb-2">
            {!collapsed && <button type="button" onClick={() => toggleGroup(group.id)} className="flex w-full items-center px-2.5 py-1.5 text-[9px] font-bold uppercase tracking-[0.16em] text-slate-500 hover:text-slate-300" aria-expanded={isOpen}><span className="flex-1 text-left">{group.label}</span><ChevronDown className={cn("h-3 w-3 transition", isOpen ? "rotate-0" : "-rotate-90")} /></button>}
            {isOpen && <div className="space-y-0.5">{group.items.map((item) => {
              const Icon = item.icon;
              const active = isPartnerNavItemActive(item, pathname);
              return <Link key={item.id} href={item.href} title={collapsed ? item.label : undefined} aria-current={active ? "page" : undefined} className={cn("group relative flex items-center rounded-xl text-sm transition", collapsed ? "mx-auto h-10 w-10 justify-center" : "gap-3 px-3 py-2.5", active ? "bg-blue-500/20 font-semibold text-white shadow-[inset_0_0_0_1px_rgba(109,161,255,0.2)]" : "text-slate-300 hover:bg-white/7 hover:text-white")}>
                {active && <span className="absolute left-0 h-5 w-0.5 rounded-full bg-blue-400" />}
                <Icon className={cn("h-[18px] w-[18px] shrink-0", active ? "text-blue-300" : "text-slate-500 group-hover:text-slate-300")} />
                {!collapsed && <span className="min-w-0 flex-1 truncate">{item.label}</span>}
              </Link>;
            })}</div>}
          </div>;
        })}
      </nav>
      <div className="border-t border-white/10 p-2">
        <div className={cn("flex items-center rounded-xl", collapsed ? "justify-center p-1" : "gap-2 px-2 py-2")}>
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white/10 text-xs font-bold">{(user.full_name ?? user.email).slice(0, 2).toUpperCase()}</span>
          {!collapsed && <span className="min-w-0 flex-1"><span className="block truncate text-xs font-semibold">{user.full_name ?? "Operator Mitra"}</span><span className="block truncate text-[10px] capitalize text-slate-400">{org.role} · Semua cabang</span></span>}
          {!collapsed && <button type="button" onClick={handleLogout} aria-label="Keluar" title="Keluar" className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white"><LogOut className="h-4 w-4" /></button>}
        </div>
        <button type="button" onClick={collapsed ? handleLogout : toggleCollapsed} className="mt-1 hidden h-9 w-full items-center justify-center rounded-xl text-slate-400 hover:bg-white/8 hover:text-white lg:flex" aria-label={collapsed ? "Keluar" : "Ciutkan sidebar"} title={collapsed ? "Keluar" : "Ciutkan sidebar"}>
          {collapsed ? <LogOut className="h-4 w-4" /> : <><ChevronLeft className="h-4 w-4" /><span className="ml-2 text-xs">Ciutkan sidebar</span></>}
        </button>
      </div>
    </>
  );

  return <div className="min-h-screen bg-background">
    <aside className={cn("fixed inset-y-0 left-0 z-40 hidden flex-col overflow-hidden bg-[linear-gradient(165deg,var(--pg-navy-950),var(--pg-navy-850)_58%,#0b3470)] text-white shadow-[var(--pg-shadow-lg)] transition-[width] duration-200 lg:flex", collapsed ? "w-[72px]" : "w-[280px]")}>{sidebar}</aside>
    {mobileOpen && <><button type="button" className="fixed inset-0 z-40 bg-slate-950/55 backdrop-blur-sm lg:hidden" aria-label="Tutup menu" onClick={() => setMobileOpen(false)} /><aside className="fixed inset-y-0 left-0 z-50 flex w-[min(320px,88vw)] flex-col overflow-hidden bg-[linear-gradient(165deg,var(--pg-navy-950),var(--pg-navy-850)_58%,#0b3470)] text-white shadow-2xl lg:hidden"><button type="button" onClick={() => setMobileOpen(false)} aria-label="Tutup menu" className="absolute right-3 top-4 z-10 grid h-9 w-9 place-items-center rounded-lg bg-white/8 text-slate-300"><X className="h-5 w-5" /></button>{sidebar}</aside></>}
    <div className={cn("min-w-0 transition-[padding] duration-200", collapsed ? "lg:pl-[72px]" : "lg:pl-[280px]")}>
      <header className="sticky top-0 z-30 border-b border-border bg-[color:var(--pg-glass)] backdrop-blur-xl">
        <div className="flex h-[68px] items-center gap-3 px-4 sm:px-6 lg:px-7">
          <button type="button" onClick={() => { setCollapsed(false); setMobileOpen(true); }} aria-label="Buka menu" className="grid h-10 w-10 place-items-center rounded-xl border border-border bg-surface text-muted-foreground lg:hidden"><Menu className="h-5 w-5" /></button>
          {collapsed && <button type="button" onClick={toggleCollapsed} aria-label="Perluas sidebar" title="Perluas sidebar" className="hidden h-9 w-9 place-items-center rounded-lg border border-border bg-surface text-muted-foreground hover:text-primary lg:grid"><ChevronRight className="h-4 w-4" /></button>}
          <div className="relative hidden max-w-xl flex-1 md:block"><Search className="absolute left-3 top-5 z-10 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input ref={searchInput} value={globalQuery} onChange={(event) => { setGlobalQuery(event.target.value); setSearchOpen(true); }} onFocus={() => setSearchOpen(true)} aria-label="Cari data operasional" placeholder="Cari debitur, pengajuan, kontrak, atau agunan…" className="h-10 w-full rounded-xl border border-border bg-surface pl-10 pr-16 text-sm outline-none transition focus:border-primary/50 focus:ring-4 focus:ring-primary/8" /><kbd className="absolute right-3 top-5 -translate-y-1/2 rounded border border-border bg-surface-soft px-1.5 py-0.5 text-[10px] text-muted-foreground">Ctrl K</kbd>{searchOpen && globalQuery.trim().length >= 2 && <div className="absolute left-0 right-0 top-12 z-50 overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-lg)]"><div className="border-b border-border px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Hasil pencarian lintas modul</div>{searchLoading ? <p className="px-4 py-6 text-center text-xs text-muted-foreground">Mencari…</p> : <div className="max-h-[420px] overflow-y-auto">{searchResults.customers.map((item) => <Link key={`customer-${item.id}`} onClick={() => setSearchOpen(false)} href={`/orgs/${slug}/customers/${item.id}`} className="flex items-center gap-3 border-b border-border/60 px-4 py-3 hover:bg-surface-soft"><ContactRound className="h-4 w-4 text-primary" /><span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{item.full_name}</span><span className="block font-mono text-[10px] text-muted-foreground">{item.customer_reference} · Debitur</span></span></Link>)}{searchResults.applications.map((item) => <Link key={`application-${item.id}`} onClick={() => setSearchOpen(false)} href={`/orgs/${slug}/loans/applications/${item.id}`} className="flex items-center gap-3 border-b border-border/60 px-4 py-3 last:border-0 hover:bg-surface-soft"><ClipboardList className="h-4 w-4 text-primary" /><span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{item.application_no} · {item.borrower_name}</span><span className="block truncate text-[10px] text-muted-foreground">{item.asset_label} · Pengajuan</span></span></Link>)}{!searchResults.customers.length && !searchResults.applications.length && <p className="px-4 py-6 text-center text-xs text-muted-foreground">Tidak ada data yang cocok.</p>}</div>}</div>}</div>
          <div className="ml-auto flex items-center gap-2">
            <div aria-label="Cakupan cabang aktif" className="hidden h-10 items-center gap-2 rounded-xl border border-border bg-surface px-3 text-xs font-semibold text-muted-foreground shadow-[var(--pg-shadow-sm)] sm:flex"><SlidersHorizontal className="h-4 w-4" /> Semua cabang</div>
            <div className="hidden items-center gap-2 rounded-xl border border-border bg-surface py-1.5 pl-1.5 pr-3 shadow-[var(--pg-shadow-sm)] xl:flex"><span className="grid h-8 w-8 place-items-center rounded-lg bg-surface-blue text-xs font-bold text-primary">{(user.full_name ?? user.email).slice(0, 2).toUpperCase()}</span><span><span className="block max-w-36 truncate text-xs font-semibold">{user.full_name ?? "Operator Mitra"}</span><span className="block text-[10px] capitalize text-muted-foreground">{org.role}</span></span></div>
          </div>
        </div>
      </header>
      <main className="min-w-0 px-4 py-5 sm:px-6 lg:px-7 lg:py-7">{children}</main>
      <footer className="border-t border-border px-6 py-4 text-center text-[11px] text-muted-foreground">PrivGadai · Partner Operations · Seluruh tindakan penting mengikuti scope tenant dan cabang</footer>
    </div>
  </div>;
}

export default function OrgLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const params = useParams<{ slug: string }>();
  const slug = params?.slug as string;
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!slug) return;
    switchOrg(slug).then(() => setReady(true)).catch((err: ApiError) => {
      if (err.status === 401) router.replace("/login");
      else if (err.status === 403 || err.status === 404) router.replace("/dashboard");
      else setError(err.detail ?? "Gagal mengaktifkan konteks mitra");
    });
  }, [slug, router]);
  if (error) return <ErrorState message={error} actionHref="/dashboard" />;
  if (!ready) return <LoadingState label="Mengaktifkan konteks mitra dan cabang" />;
  return <OrgContextProvider slug={slug}><OrgChrome>{children}</OrgChrome></OrgContextProvider>;
}
