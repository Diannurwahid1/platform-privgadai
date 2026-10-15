"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, MapPin, PackageCheck, Phone, Truck } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { listFieldTasks, transitionPickup, type FieldTaskItem } from "@/lib/operations";

export default function FieldWorkspacePage() {
  const { slug } = useParams<{ slug: string }>();
  const [tasks, setTasks] = useState<FieldTaskItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const load = useCallback(() => listFieldTasks().then(setTasks), []);
  useEffect(() => { load().catch((reason: { detail?: string }) => setError(reason.detail ?? "Tugas pickup gagal dimuat")); }, [load]);
  async function move(task: FieldTaskItem, status: "in_transit" | "received") {
    setBusy(task.id); setError(null);
    try { await transitionPickup(task.id, status); await load(); } catch (reason) { setError((reason as { detail?: string }).detail ?? "Status tugas gagal diubah"); }
    finally { setBusy(null); }
  }
  if (error && !tasks) return <ErrorState message={error} />;
  if (!tasks) return <LoadingState label="Memuat tugas petugas lapangan" />;
  return <div className="mx-auto max-w-5xl space-y-6">
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Field agent workspace</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Tugas pickup</h1><p className="mt-2 text-sm text-muted-foreground">Workspace mobile untuk serah terima awal dan pelacakan barang.</p></div><span className="inline-flex items-center gap-2 rounded-full border border-success/25 bg-success/8 px-3 py-2 text-xs font-bold text-success"><Truck className="h-4 w-4" /> {tasks.length} tugas</span></header>
    {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    <section className="grid gap-4 lg:grid-cols-2">{tasks.map((task) => <article key={task.id} className="rounded-[var(--pg-radius-lg)] border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><div className="flex items-start justify-between gap-3"><div><p className="font-mono text-xs font-bold text-primary">{task.assignment_code}</p><h2 className="mt-2 text-lg font-bold">{task.asset_label}</h2><p className="mt-1 text-xs text-muted-foreground">{task.application_no} · {task.branch_name}</p></div><span className="rounded-full bg-surface-blue px-3 py-1.5 text-[10px] font-bold uppercase text-primary">{task.status.replaceAll("_", " ")}</span></div><div className="mt-5 space-y-3 rounded-2xl bg-surface-soft p-4 text-xs"><p className="flex items-center gap-2 font-semibold"><PackageCheck className="h-4 w-4 text-primary" /> {task.borrower_name}</p><p className="flex items-center gap-2 text-muted-foreground"><Phone className="h-4 w-4" /> {task.phone_masked}</p><p className="flex items-start gap-2 text-muted-foreground"><MapPin className="mt-0.5 h-4 w-4 shrink-0" /> {task.pickup_address}</p></div><div className="mt-4 flex gap-2">{task.status === "assigned" && <button disabled={busy === task.id} onClick={() => move(task, "in_transit")} className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-primary text-xs font-bold text-white"><Truck className="h-4 w-4" /> Mulai pickup</button>}{task.status === "in_transit" && <button disabled={busy === task.id} onClick={() => move(task, "received")} className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-success text-xs font-bold text-white"><CheckCircle2 className="h-4 w-4" /> Serahkan ke mitra</button>}<Link href={`/orgs/${slug}/applications/${task.application_id}`} className="grid h-11 w-11 place-items-center rounded-xl border border-border"><ArrowRight className="h-4 w-4" /></Link></div></article>)}</section>
    {!tasks.length && <div className="rounded-[var(--pg-radius-lg)] border border-dashed border-border bg-surface p-12 text-center"><Truck className="mx-auto h-10 w-10 text-muted-foreground/40" /><p className="mt-3 font-bold">Belum ada tugas pickup</p><p className="mt-1 text-xs text-muted-foreground">Tugas muncul setelah offer diterima dan pickup ditugaskan.</p></div>}
  </div>;
}
