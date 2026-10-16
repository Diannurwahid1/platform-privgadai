"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { logout, me, type User } from "@/lib/auth";
import { listMembers, listOrgs, switchOrg, type OrgSummary } from "@/lib/orgs";
import {
  listAssetCategories,
  listBranches,
  listCustodyLocations,
  listLoanProducts,
  listStaffAssignments,
} from "@/lib/operations";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  EmptyState,
  ErrorState,
  FeatureBadge,
  LoadingState,
  PageHeader,
} from "@/components/page-state";
import type { ApiError } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [orgs, setOrgs] = useState<OrgSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [opening, setOpening] = useState(false);

  useEffect(() => {
    Promise.all([me(), listOrgs()])
      .then(([u, list]) => {
        setUser(u);
        setOrgs(list);
        if (list.length === 1) {
          setOpening(true);
          switchOrg(list[0].slug)
            .then(async () => {
              const [branches, categories, products, locations, staff, members] = await Promise.all([
                listBranches(),
                listAssetCategories(),
                listLoanProducts(),
                listCustodyLocations(),
                listStaffAssignments(),
                listMembers(list[0].slug),
              ]);
              const ready = Boolean(
                branches.length && categories.length && products.length && locations.length &&
                staff.length >= 2 && members.length >= 2,
              );
              router.replace(ready ? `/orgs/${list[0].slug}/overview` : `/orgs/${list[0].slug}/onboarding`);
            })
            .catch((err: ApiError) => {
              setOpening(false);
              setError(err.detail ?? "Tenant gagal dibuka.");
            });
        }
      })
      .catch((err: ApiError) => {
        if (err.status === 401) {
          router.replace("/login");
        } else {
          setError(err.detail ?? "Daftar tenant gagal dimuat.");
        }
      });
  }, [router]);

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // ignore
    }
    router.replace("/login");
  }

  if (error) {
    return (
      <ErrorState message={error} actionHref="/login" actionLabel="Kembali ke login" />
    );
  }

  if (!user || !orgs || opening) {
    return <LoadingState label={opening ? "Membuka panduan setup tenant" : "Memuat tenant"} />;
  }

  return (
    <motion.main
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="mx-auto max-w-5xl space-y-8 px-6 py-12"
    >
      <PageHeader
        eyebrow="Ruang kerja tenant"
        title={`Selamat datang, ${user.full_name ?? user.email}`}
        description="Pilih organisasi untuk melanjutkan setup dan pekerjaan operasional pergadaian."
        actions={
          <>
            <Link
              href="/orgs/new"
              className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
            >
              Tenant baru
            </Link>
            <Button onClick={handleLogout} variant="secondary">
              Keluar
            </Button>
          </>
        }
      />

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-muted-foreground">
          Organisasi Anda
        </h2>

        {orgs.length === 0 ? (
          <EmptyState
            title="Belum ada tenant"
            description="Buat tenant pertama, lalu PrivGadai akan memandu setup cabang, produk gadai, agunan, custody, dan tim."
            action={
              <Link
                href="/orgs/new"
                className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
              >
                Buat tenant pertama
              </Link>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {orgs.map((org) => (
              <Link key={org.id} href={`/orgs/${org.slug}/onboarding`} className="block">
                <Card className="group cursor-pointer transition hover:border-primary/50 hover:bg-muted/65">
                  <CardHeader className="flex flex-row items-start justify-between pb-0">
                    <div>
                      <CardTitle className="text-xl">{org.name}</CardTitle>
                      <p className="mt-1 font-mono text-xs text-muted-foreground">
                        {org.slug}
                      </p>
                    </div>
                    <FeatureBadge>{org.role}</FeatureBadge>
                  </CardHeader>
                  <CardContent className="pt-4 text-sm text-muted-foreground">
                    <p>
                      Buka setup dan ruang operasi <span className="ml-1">-&gt;</span>
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>
    </motion.main>
  );
}
