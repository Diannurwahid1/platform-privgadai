"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, CalendarClock, CheckCircle2, Clock3, HandCoins, MessageSquareText, PackageCheck, ShieldAlert, XCircle } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import { addCollectionNote, createCollectionPromise, getCollectionCase, resolveCollectionPromise, updateCollectionPlan, type CollectionCaseDetail } from "@/lib/operations";

const idr = (value: unknown) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(Number(value ?? 0));
const when = (value: string | null) => value ? new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";

export default function CollectionCasePage() {
  const { slug, id } = useParams<{ slug: string; id: string }>();
  const [data, setData] = useState<CollectionCaseDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [strategy, setStrategy] = useState("reminder");
  const [stage, setStage] = useState("soft_collection");
  const [nextAction, setNextAction] = useState("");
  const [channel, setChannel] = useState("phone");
  const [outcome, setOutcome] = useState("contacted");
  const [note, setNote] = useState("");
  const [noteNextAction, setNoteNextAction] = useState("");
  const [promiseAmount, setPromiseAmount] = useState("");
  const [promiseAt, setPromiseAt] = useState("");
  const [promiseNote, setPromiseNote] = useState("");

  const load = useCallback(async () => {
    try {
      const detail = await getCollectionCase(id); setData(detail); setStrategy(detail.strategy); setStage(detail.stage);
      setNextAction(detail.next_action_at ? detail.next_action_at.slice(0, 16) : "");
    } catch (failure) { setError((failure as { detail?: string }).detail ?? "Detail collection gagal dimuat"); }
  }, [id]);
  useEffect(() => { void load(); }, [load]);

  async function perform(work: () => Promise<unknown>, success: string) {
    setBusy(true); setError(null); setNotice(null);
    try { await work(); setNotice(success); await load(); }
    catch (failure) { setError((failure as { detail?: string }).detail ?? "Aksi collection gagal disimpan"); }
    finally { setBusy(false); }
  }
  if (error && !data) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Memuat collection case" />;

  return <div className="space-y-5">
    <header className="border-b border-border pb-5"><Link href={`/orgs/${slug}/finance/collections`} className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground"><ArrowLeft className="h-4 w-4" />Collection queue</Link><div className="mt-4 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between"><div><div className="flex flex-wrap items-center gap-2"><span className="rounded-lg bg-surface-blue px-2.5 py-1 text-xs font-bold text-primary">{data.aging_bucket}</span><span className="rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800">{data.status.replaceAll("_", " ")}</span><span className="font-mono text-xs text-muted-foreground">{data.loan.account_no}</span></div><h1 className="mt-3 text-3xl font-bold tracking-[-0.045em]">{data.borrower.name}</h1><p className="mt-2 text-sm text-muted-foreground">{data.borrower.phone_masked} · {data.branch.code} {data.branch.name} · {data.loan.application_no}</p></div><div className="text-left xl:text-right"><p className="text-xs text-muted-foreground">Total kewajiban</p><p className="mt-1 text-3xl font-bold">{idr(data.outstanding_amount)}</p><p className="mt-1 text-xs font-semibold text-red-700">{data.days_past_due} hari lewat jatuh tempo</p></div></div></header>
    {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    <section className="grid gap-3 sm:grid-cols-4"><Metric icon={ShieldAlert} label="Outstanding pokok" value={idr(data.loan.outstanding_principal)} /><Metric icon={HandCoins} label="Biaya tertunggak" value={idr(data.loan.outstanding_fee)} /><Metric icon={CalendarClock} label="Tindakan berikutnya" value={when(data.next_action_at)} /><Metric icon={MessageSquareText} label="Kontak terakhir" value={when(data.last_contact_at)} /></section>
    <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <div className="space-y-4">
        <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="font-bold">Strategi dan tahap penanganan</h2><p className="mt-1 text-xs text-muted-foreground">Perubahan menjadi dasar antrean, SLA, dan eskalasi petugas.</p><div className="mt-4 grid gap-3 sm:grid-cols-3"><Field label="Strategi"><select value={strategy} onChange={(event) => setStrategy(event.target.value)} className="control"><option value="reminder">Reminder</option><option value="negotiation">Negotiation</option><option value="field_visit">Field visit</option><option value="legal_review">Legal review</option><option value="collateral_resolution">Collateral resolution</option></select></Field><Field label="Tahap"><select value={stage} onChange={(event) => setStage(event.target.value)} className="control"><option value="soft_collection">Soft collection</option><option value="intensive_collection">Intensive collection</option><option value="pre_legal">Pre legal</option><option value="legal">Legal</option><option value="resolved">Resolved</option></select></Field><Field label="Tindakan berikutnya"><input type="datetime-local" value={nextAction} onChange={(event) => setNextAction(event.target.value)} className="control" /></Field></div><button disabled={busy || !nextAction} onClick={() => void perform(() => updateCollectionPlan(id, { strategy, stage, next_action_at: new Date(nextAction).toISOString() }), "Strategi dan SLA tindakan diperbarui.")} className="mt-4 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Simpan rencana</button></article>
        <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="font-bold">Catat aktivitas penagihan</h2><div className="mt-4 grid gap-3 sm:grid-cols-2"><Field label="Kanal"><select value={channel} onChange={(event) => setChannel(event.target.value)} className="control"><option value="phone">Telepon</option><option value="whatsapp">WhatsApp</option><option value="visit">Kunjungan</option><option value="branch">Cabang</option><option value="email">Email</option></select></Field><Field label="Outcome"><select value={outcome} onChange={(event) => setOutcome(event.target.value)} className="control"><option value="contacted">Terhubung</option><option value="no_answer">Tidak terhubung</option><option value="refused">Menolak</option><option value="dispute">Sengketa</option><option value="promise_to_pay">Janji bayar</option></select></Field><Field label="Tindakan berikutnya"><input type="datetime-local" value={noteNextAction} onChange={(event) => setNoteNextAction(event.target.value)} className="control" /></Field><Field label="Catatan"><input value={note} onChange={(event) => setNote(event.target.value)} className="control" placeholder="Ringkasan percakapan dan bukti" /></Field></div><button disabled={busy || note.length < 3} onClick={() => void perform(() => addCollectionNote(id, { channel, outcome, note, next_action_at: noteNextAction ? new Date(noteNextAction).toISOString() : null }), "Aktivitas penagihan masuk ke timeline.")} className="mt-4 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Catat aktivitas</button></article>
        <article className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border px-5 py-4"><h2 className="font-bold">Timeline aktivitas</h2></div><div className="divide-y divide-border">{data.notes.map((item) => <div key={item.id} className="px-5 py-4"><div className="flex items-center justify-between"><span className="rounded-lg bg-surface-soft px-2 py-1 text-[10px] font-bold uppercase">{item.channel} · {item.outcome.replaceAll("_", " ")}</span><span className="text-xs text-muted-foreground">{when(item.created_at)}</span></div><p className="mt-2 text-sm">{item.note}</p><p className="mt-2 text-xs text-muted-foreground">Tindakan berikutnya: {when(item.next_action_at)}</p></div>)}{!data.notes.length && <p className="px-5 py-10 text-center text-sm text-muted-foreground">Belum ada aktivitas penagihan.</p>}</div></article>
      </div>
      <div className="space-y-4">
        <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><h2 className="font-bold">Promise to pay</h2><p className="mt-1 text-xs text-muted-foreground">Satu janji aktif per kasus; hasilnya harus ditutup sebagai kept, broken, atau cancelled.</p><div className="mt-4 space-y-3"><Field label="Nominal"><input inputMode="numeric" value={promiseAmount} onChange={(event) => setPromiseAmount(event.target.value)} className="control" placeholder="0" /></Field><Field label="Tanggal janji"><input type="datetime-local" value={promiseAt} onChange={(event) => setPromiseAt(event.target.value)} className="control" /></Field><Field label="Dasar janji"><textarea value={promiseNote} onChange={(event) => setPromiseNote(event.target.value)} className="min-h-24 rounded-xl border border-border bg-background p-3 text-sm" placeholder="Pernyataan nasabah dan konteks kesepakatan" /></Field><button disabled={busy || !promiseAmount || !promiseAt || promiseNote.length < 5} onClick={() => void perform(() => createCollectionPromise(id, { amount: Number(promiseAmount), promised_at: new Date(promiseAt).toISOString(), channel, note: promiseNote }), "Promise to pay berhasil dicatat." )} className="w-full rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Catat janji bayar</button></div></article>
        <article className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border px-5 py-4"><h2 className="font-bold">Riwayat janji</h2></div><div className="divide-y divide-border">{data.promises.map((item) => <div key={item.id} className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="font-bold">{idr(item.amount)}</p><p className={`mt-1 text-xs ${item.is_overdue ? "font-semibold text-red-700" : "text-muted-foreground"}`}>Janji {when(item.promised_at)}</p></div><span className="rounded-lg bg-surface-soft px-2 py-1 text-xs font-bold">{item.status}</span></div><p className="mt-3 text-xs text-muted-foreground">{item.note}</p>{item.status === "pending" && <div className="mt-4 flex gap-2"><PromiseButton icon={CheckCircle2} label="Kept" tone="green" onClick={() => resolvePromise(item.id, "kept")} /><PromiseButton icon={XCircle} label="Broken" tone="red" onClick={() => resolvePromise(item.id, "broken")} /></div>}{item.resolution_reason && <p className="mt-3 text-xs">Resolusi: {item.resolution_reason}</p>}</div>)}{!data.promises.length && <p className="px-5 py-10 text-center text-sm text-muted-foreground">Belum ada promise to pay.</p>}</div></article>
        <article className="rounded-2xl border border-border bg-surface p-5"><div className="flex items-center gap-2"><PackageCheck className="h-5 w-5 text-primary" /><h2 className="font-bold">Agunan terkait</h2></div><p className="mt-4 font-mono text-xs text-primary">{data.collateral.asset_code}</p><p className="mt-2 font-semibold">{data.collateral.label}</p><dl className="mt-4 grid grid-cols-2 gap-3 text-xs"><Fact label="Kategori" value={data.collateral.category} /><Fact label="Status custody" value={data.collateral.status} /><Fact label="Nilai indikatif" value={idr(data.collateral.indicative_value)} /><Fact label="Jatuh tempo" value={when(data.due_at)} /></dl></article>
      </div>
    </section>
  </div>;

  function resolvePromise(promiseId: string, resolution: "kept" | "broken") { const resolutionReason = window.prompt(`Alasan status ${resolution}:`); if (resolutionReason) void perform(() => resolveCollectionPromise(id, promiseId, resolution, resolutionReason), `Promise ditutup sebagai ${resolution}.`); }
}

function Metric({ icon: Icon, label, value }: { icon: typeof Clock3; label: string; value: string }) { return <article className="rounded-2xl border border-border bg-surface p-4"><Icon className="h-4 w-4 text-primary" /><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 truncate text-sm font-bold">{value}</p></article>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="grid gap-1.5 text-xs font-semibold text-muted-foreground">{label}{children}</label>; }
function Fact({ label, value }: { label: string; value: string }) { return <div><dt className="text-muted-foreground">{label}</dt><dd className="mt-1 font-semibold">{value}</dd></div>; }
function PromiseButton({ icon: Icon, label, tone, onClick }: { icon: typeof CheckCircle2; label: string; tone: "green" | "red"; onClick: () => void }) { return <button onClick={onClick} className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold ${tone === "green" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}><Icon className="h-4 w-4" />{label}</button>; }
