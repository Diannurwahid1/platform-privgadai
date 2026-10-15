"use client";

import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  BadgeDollarSign,
  Bell,
  Building2,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  PackageSearch,
  Scale,
  ScrollText,
  Search,
  Settings,
  ShieldAlert,
  Truck,
  Users,
  Warehouse,
} from "lucide-react";
import { logout, me, type User } from "@/lib/auth";
import { switchOrg } from "@/lib/orgs";
import { OrgContextProvider, useOrgContext } from "@/lib/org-context";
import { ErrorState, LoadingState } from "@/components/page-state";
import { cn } from "@/lib/utils";
import type { ApiError } from "@/lib/api";

type NavItem = {
  label: string;
  href: string | null;
  icon: typeof LayoutDashboard;
  badge?: string;
};

function OrgChrome({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useParams<{ slug: string }>();
  const slug = params?.slug as string;
  const { org, error, loading } = useOrgContext();
  const [user, setUser] = useState<User | null>(null);
  const [chromeError, setChromeError] = useState<string | null>(null);

  useEffect(() => {
    me()
      .then(setUser)
      .catch((err: ApiError) => {
        if (err.status === 401) router.replace("/login");
        else setChromeError(err.detail ?? "Gagal memuat profil");
      });
  }, [router]);

  async function handleLogout() {
    try {
      await logout();
    } finally {
      router.replace("/login");
    }
  }

  if (chromeError || error) {
    return (
      <ErrorState
        message={chromeError ?? error ?? "Gagal membuka workspace mitra"}
        actionHref="/dashboard"
        actionLabel="Kembali ke daftar mitra"
      />
    );
  }

  if (loading || !org || !user) {
    return <LoadingState label="Menyiapkan ruang operasi PrivGadai" />;
  }

  const mainNav: NavItem[] = [
    { label: "Ringkasan", href: `/orgs/${slug}`, icon: LayoutDashboard },
    {
      label: "Pengajuan",
      href: `/orgs/${slug}/applications`,
      icon: ClipboardList,
      badge: "8",
    },
    { label: "Penaksiran", href: null, icon: Scale, badge: "2" },
    { label: "Barang Jaminan", href: null, icon: PackageSearch },
    { label: "Pickup", href: null, icon: Truck },
    { label: "Custody", href: null, icon: Warehouse },
    { label: "Settlement", href: null, icon: BadgeDollarSign },
    { label: "Exception", href: null, icon: ShieldAlert, badge: "1" },
    {
      label: "Audit",
      href: `/orgs/${slug}/audit-log`,
      icon: ScrollText,
    },
  ];
  const supportNav: NavItem[] = [
    { label: "Tim & akses", href: `/orgs/${slug}/members`, icon: Users },
    { label: "Pengaturan mitra", href: `/orgs/${slug}/settings`, icon: Settings },
  ];

  function renderNav(items: NavItem[]) {
    return items.map((item) => {
      const Icon = item.icon;
      const active =
        item.href !== null &&
        (pathname === item.href ||
          (item.href.endsWith("/applications") &&
            pathname.startsWith(item.href)));

      if (!item.href) {
        return (
          <div
            key={item.label}
            className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-500"
            title="Modul berikutnya dalam blueprint"
          >
            <Icon className="h-[18px] w-[18px]" />
            <span className="flex-1">{item.label}</span>
            <span className="rounded-full border border-white/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider">
              segera
            </span>
          </div>
        );
      }

      return (
        <Link
          key={item.label}
          href={item.href}
          className={cn(
            "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
            active
              ? "bg-blue-500/20 text-white shadow-[inset_0_0_0_1px_rgba(109,161,255,0.18)]"
              : "text-slate-300 hover:bg-white/7 hover:text-white",
          )}
        >
          <Icon
            className={cn(
              "h-[18px] w-[18px]",
              active ? "text-blue-300" : "text-slate-500 group-hover:text-slate-300",
            )}
          />
          <span className="flex-1">{item.label}</span>
          {item.badge && (
            <span className="min-w-5 rounded-full bg-white/10 px-1.5 py-0.5 text-center text-[10px] font-semibold text-slate-300">
              {item.badge}
            </span>
          )}
        </Link>
      );
    });
  }

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[248px] flex-col overflow-hidden bg-[linear-gradient(165deg,var(--pg-navy-950),var(--pg-navy-850)_58%,#0b3470)] text-white shadow-[var(--pg-shadow-lg)] lg:flex">
        <div className="flex h-[76px] items-center gap-3 border-b border-white/10 px-5">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[linear-gradient(135deg,var(--pg-blue-500),var(--pg-cyan-400))] font-black text-[var(--pg-navy-950)] shadow-lg">
            P
          </div>
          <div>
            <p className="text-[17px] font-bold tracking-[-0.04em]">PrivGadai</p>
            <p className="text-[10px] uppercase tracking-[0.2em] text-blue-200/60">
              Partner Operations
            </p>
          </div>
        </div>

        <div className="border-b border-white/10 px-4 py-4">
          <button className="flex w-full items-center gap-3 rounded-xl border border-white/10 bg-white/6 px-3 py-3 text-left">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-blue-400/15 text-blue-300">
              <Building2 className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold">{org.name}</p>
              <p className="mt-0.5 truncate text-[10px] text-slate-400">
                Semua cabang · Pilot
              </p>
            </div>
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Operasional
          </p>
          {renderNav(mainNav)}
        </nav>

        <div className="space-y-1 border-t border-white/10 px-3 py-4">
          {renderNav(supportNav)}
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-400 transition hover:bg-white/7 hover:text-white"
          >
            <LogOut className="h-[18px] w-[18px]" />
            Keluar
          </button>
        </div>
      </aside>

      <div className="lg:pl-[248px]">
        <header className="sticky top-0 z-30 border-b border-border bg-[color:var(--pg-glass)] backdrop-blur-xl">
          <div className="flex h-[76px] items-center gap-4 px-4 sm:px-6 lg:px-8">
            <Link href={`/orgs/${slug}`} className="flex items-center gap-2 lg:hidden">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary font-black text-white">
                P
              </span>
              <span className="font-bold tracking-tight">PrivGadai</span>
            </Link>
            <div className="relative hidden max-w-md flex-1 md:block">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                aria-label="Cari pengajuan atau barang jaminan"
                placeholder="Cari pengajuan, nasabah, atau aset..."
                className="h-10 w-full rounded-full border border-border bg-surface pl-10 pr-4 text-sm outline-none transition focus:border-primary/50 focus:ring-4 focus:ring-primary/8"
              />
            </div>
            <div className="ml-auto flex items-center gap-2">
              <button
                aria-label="Notifikasi"
                className="relative grid h-10 w-10 place-items-center rounded-full border border-border bg-surface text-muted-foreground shadow-[var(--pg-shadow-sm)]"
              >
                <Bell className="h-[18px] w-[18px]" />
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-destructive ring-2 ring-white" />
              </button>
              <div className="hidden items-center gap-3 rounded-full border border-border bg-surface py-1.5 pl-1.5 pr-4 shadow-[var(--pg-shadow-sm)] sm:flex">
                <div className="grid h-8 w-8 place-items-center rounded-full bg-surface-blue text-xs font-bold text-primary">
                  {(user.full_name ?? user.email).slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <p className="max-w-36 truncate text-xs font-semibold">
                    {user.full_name ?? "Operator Mitra"}
                  </p>
                  <p className="text-[10px] capitalize text-muted-foreground">
                    {org.role} · Semua cabang
                  </p>
                </div>
              </div>
            </div>
          </div>
          <nav className="flex gap-1 overflow-x-auto border-t border-border/70 px-4 py-2 lg:hidden">
            {mainNav
              .filter((item) => item.href)
              .map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.label}
                    href={item.href!}
                    className={cn(
                      "flex shrink-0 items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold",
                      active
                        ? "bg-primary text-primary-foreground"
                        : "bg-surface text-muted-foreground",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {item.label}
                  </Link>
                );
              })}
          </nav>
        </header>

        <main className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>

        <footer className="border-t border-border px-6 py-5 text-center text-[11px] text-muted-foreground">
          PrivGadai · Data operasional tenant terisolasi · Aktivitas penting diaudit
        </footer>
      </div>
    </div>
  );
}

export default function OrgLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const params = useParams<{ slug: string }>();
  const slug = params?.slug as string;
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    switchOrg(slug)
      .then(() => setReady(true))
      .catch((err: ApiError) => {
        if (err.status === 401) router.replace("/login");
        else if (err.status === 403 || err.status === 404)
          router.replace("/dashboard");
        else setError(err.detail ?? "Gagal mengaktifkan konteks mitra");
      });
  }, [slug, router]);

  if (error) return <ErrorState message={error} actionHref="/dashboard" />;
  if (!ready) return <LoadingState label="Mengaktifkan konteks mitra dan cabang" />;

  return (
    <OrgContextProvider slug={slug}>
      <OrgChrome>{children}</OrgChrome>
    </OrgContextProvider>
  );
}

