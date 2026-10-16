"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarClock, ChevronRight, CopyPlus, Database, FileDiff, Filter, History, Plus, RefreshCw, Search, ShieldCheck, X } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  applyDueConfigurations, cloneConfiguration, createConfiguration, getConfiguration,
  listConfigurations, previewConfiguration, submitConfiguration, updateConfiguration,
  type ConfigurationPreview, type ConfigurationVersion,
} from "@/lib/operations";

const domains = ["institution", "product", "pricing", "appraisal", "workflow", "custody", "document", "accounting", "regulatory", "access", "integration", "notification", "security"];
const dateTime = (value: string | null) => value ? new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
const inputDate = (date = new Date()) => new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
const pretty = (value: unknown) => value === undefined ? "Tidak diset" : JSON.stringify(value, null, 2);
type FormState = { domain: string; config_key: string; effective_from: string; change_summary: string; payload: string };
const emptyForm = (): FormState => ({ domain: "product", config_key: "", effective_from: inputDate(), change_summary: "", payload: "{\n  \"enabled\": true\n}" });

export default function SettingsPage() {
  const [items, setItems] = useState<ConfigurationVersion[] | null>(null);
  const [selected, setSelected] = useState<ConfigurationVersion | null>(null);
  const [preview, setPreview] = useState<ConfigurationPreview | null>(null);
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("all");
  const [status, setStatus] = useState("all");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setItems(await listConfigurations()); }
    catch (failure) { setError((failure as { detail?: string }).detail ?? "Register konfigurasi gagal dimuat"); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => (items ?? []).filter((item) => {
    const text = `${item.domain} ${item.config_key} ${item.change_summary}`.toLowerCase();
    return (domain === "all" || item.domain === domain) && (status === "all" || item.status === status) && text.includes(query.toLowerCase());
  }), [items, domain, status, query]);

  async function open(item: ConfigurationVersion) {
    setBusy(item.id); setError(null);
    try {
      const [detail, impact] = await Promise.all([getConfiguration(item.id), previewConfiguration(item.id)]);
      setSelected(detail); setPreview(impact);
      setForm({ domain: detail.domain, config_key: detail.config_key, effective_from: inputDate(new Date(detail.effective_from)), change_summary: detail.change_summary, payload: JSON.stringify(detail.payload, null, 2) });
    } catch (failure) { setError((failure as { detail?: string }).detail ?? "Detail konfigurasi gagal dimuat"); }
    finally { setBusy(null); }
  }

  function parsePayload() {
    const parsed = JSON.parse(form.payload) as unknown;
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error("Payload harus berupa JSON object.");
    return parsed as Record<string, unknown>;
  }

  async function save() {
    if (!form.config_key.trim() || form.change_summary.trim().length < 10) { setError("Key dan ringkasan perubahan minimal 10 karakter wajib diisi."); return; }
    setBusy("save"); setError(null); setNotice(null);
    try {
      const data = { effective_from: new Date(form.effective_from).toISOString(), change_summary: form.change_summary.trim(), payload: parsePayload() };
      const result = selected?.status === "draft" ? await updateConfiguration(selected.id, data) : await createConfiguration({ ...data, domain: form.domain, config_key: form.config_key.trim() });
      setNotice(result.message); setShowForm(false); await load();
      const detail = await getConfiguration(result.id); setSelected(detail); setPreview(await previewConfiguration(result.id));
    } catch (failure) { setError(failure instanceof SyntaxError ? "Payload bukan JSON yang valid." : (failure as { detail?: string; message?: string }).detail ?? (failure as Error).message ?? "Konfigurasi gagal disimpan"); }
    finally { setBusy(null); }
  }

  async function submit() {
    if (!selected) return;
    const reason = window.prompt("Alasan bisnis untuk approval (minimal 10 karakter):");
    if (!reason || reason.trim().length < 10) return;
    await execute("submit", () => submitConfiguration(selected.id, reason.trim()));
  }

  async function clone() {
    if (!selected) return;
    const summary = window.prompt("Ringkasan versi baru / alasan rollback (minimal 10 karakter):");
    if (!summary || summary.trim().length < 10) return;
    await execute("clone", () => cloneConfiguration(selected.id, new Date().toISOString(), summary.trim()));
  }

  async function execute(key: string, action: () => Promise<{ id: string; message: string }>) {
    setBusy(key); setError(null);
    try {
      const result = await action(); setNotice(result.message); await load();
      const detail = await getConfiguration(result.id); setSelected(detail); setPreview(await previewConfiguration(result.id));
    } catch (failure) { setError((failure as { detail?: string }).detail ?? "Tindakan konfigurasi gagal"); }
    finally { setBusy(null); }
  }

  async function applyDue() {
    setBusy("due"); setError(null);
    try { const result = await applyDueConfigurations(); setNotice(result.message); await load(); }
    catch (failure) { setError((failure as { detail?: string }).detail ?? "Aktivasi versi terjadwal gagal"); }
    finally { setBusy(null); }
  }

  if (!items) return error ? <ErrorState message={error} /> : <LoadingState label="Memuat configuration control" />;
  const counters = { effective: items.filter((item) => item.status === "effective").length, draft: items.filter((item) => item.status === "draft").length, pending: items.filter((item) => item.status === "pending_approval").length, scheduled: items.filter((item) => item.status === "approved").length };

  return <div className="space-y-5">
    <header className="flex flex-col gap-4 border-b border-border pb-5 xl:flex-row xl:items-end xl:justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Management · Controlled configuration</p><h1 className="mt-2 text-3xl font-bold tracking-[-0.045em]">Configuration workbench</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Kebijakan tenant terversi, bertanggal efektif, memiliki checksum, preview dampak, maker-checker, dan histori perubahan.</p></div><div className="flex flex-wrap gap-2"><button onClick={() => void applyDue()} disabled={busy !== null} className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-xs font-bold"><RefreshCw className="h-4 w-4" />Aktifkan jatuh tempo</button><button onClick={() => { setSelected(null); setPreview(null); setForm(emptyForm()); setShowForm(true); }} className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white"><Plus className="h-4 w-4" />Draft baru</button></div></header>
    {notice && <Alert tone="success" text={notice} close={() => setNotice(null)} />}
    {error && <Alert tone="danger" text={error} close={() => setError(null)} />}
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric icon={Database} label="Versi efektif" value={counters.effective} tone="blue" /><Metric icon={FileDiff} label="Draft" value={counters.draft} tone="slate" /><Metric icon={ShieldCheck} label="Menunggu checker" value={counters.pending} tone="amber" /><Metric icon={CalendarClock} label="Terjadwal" value={counters.scheduled} tone="green" /></section>
    {showForm && <Editor form={form} setForm={setForm} editing={selected?.status === "draft"} busy={busy === "save"} onClose={() => setShowForm(false)} onSave={() => void save()} />}
    <section className="grid gap-5 2xl:grid-cols-[minmax(0,1.4fr)_minmax(380px,0.8fr)]">
      <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="grid gap-3 border-b border-border p-4 lg:grid-cols-[1fr_180px_170px]"><div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari domain, key, atau ringkasan…" className="h-10 w-full rounded-xl border border-border bg-background pl-10 pr-3 text-sm" /></div><select value={domain} onChange={(event) => setDomain(event.target.value)} className="h-10 rounded-xl border border-border bg-background px-3 text-xs font-semibold"><option value="all">Semua domain</option>{domains.map((value) => <option key={value}>{value}</option>)}</select><select value={status} onChange={(event) => setStatus(event.target.value)} className="h-10 rounded-xl border border-border bg-background px-3 text-xs font-semibold"><option value="all">Semua status</option>{["draft", "pending_approval", "approved", "effective", "superseded", "rejected"].map((value) => <option key={value}>{value}</option>)}</select></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[820px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Configuration</th><th className="px-5 py-3">Versi</th><th className="px-5 py-3">Efektif</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Checksum</th><th className="px-5 py-3"></th></tr></thead><tbody className="divide-y divide-border">{filtered.map((item) => <tr key={item.id} className={`hover:bg-surface-soft/70 ${selected?.id === item.id ? "bg-surface-blue" : ""}`}><td className="px-5 py-4"><p className="text-[10px] font-bold uppercase tracking-wider text-primary">{item.domain}</p><p className="mt-1 font-mono text-xs font-bold">{item.config_key}</p><p className="mt-1 max-w-sm truncate text-xs text-muted-foreground">{item.change_summary}</p></td><td className="px-5 py-4 font-mono font-bold">v{item.version}</td><td className="px-5 py-4 text-xs">{dateTime(item.effective_from)}</td><td className="px-5 py-4"><Status value={item.status} /></td><td className="px-5 py-4 font-mono text-[10px] text-muted-foreground">{item.checksum_sha256.slice(0, 12)}…</td><td className="px-5 py-4"><button disabled={busy === item.id} onClick={() => void open(item)} className="grid h-9 w-9 place-items-center rounded-lg border border-border text-muted-foreground hover:text-primary"><ChevronRight className="h-4 w-4" /></button></td></tr>)}</tbody></table>{!filtered.length && <div className="px-6 py-14 text-center text-sm text-muted-foreground"><Filter className="mx-auto mb-3 h-7 w-7" />Tidak ada versi pada filter ini.</div>}</div>
      </div>
      <Detail item={selected} preview={preview} busy={busy} onEdit={() => setShowForm(true)} onSubmit={() => void submit()} onClone={() => void clone()} />
    </section>
  </div>;
}

function Editor({ form, setForm, editing, busy, onClose, onSave }: { form: FormState; setForm: (value: FormState) => void; editing: boolean; busy: boolean; onClose: () => void; onSave: () => void }) {
  const set = (key: keyof FormState, value: string) => setForm({ ...form, [key]: value });
  return <section className="rounded-2xl border border-primary/20 bg-surface p-5 shadow-[var(--pg-shadow-md)]"><div className="flex items-start justify-between"><div><h2 className="font-bold">{editing ? `Edit draft ${form.config_key}` : "Buat configuration draft"}</h2><p className="mt-1 text-xs text-muted-foreground">Gunakan object JSON eksplisit. Secret harus berupa reference key, bukan plaintext.</p></div><button onClick={onClose}><X className="h-4 w-4 text-muted-foreground" /></button></div><div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4"><Field label="Domain"><select disabled={editing} value={form.domain} onChange={(event) => set("domain", event.target.value)} className="h-10 rounded-xl border border-border bg-background px-3 text-sm">{domains.map((value) => <option key={value}>{value}</option>)}</select></Field><Field label="Configuration key"><input disabled={editing} value={form.config_key} onChange={(event) => set("config_key", event.target.value.toLowerCase())} placeholder="loan.standard.policy" className="h-10 rounded-xl border border-border bg-background px-3 font-mono text-sm" /></Field><Field label="Mulai efektif"><input type="datetime-local" value={form.effective_from} onChange={(event) => set("effective_from", event.target.value)} className="h-10 rounded-xl border border-border bg-background px-3 text-sm" /></Field><Field label="Ringkasan perubahan"><input value={form.change_summary} onChange={(event) => set("change_summary", event.target.value)} placeholder="Alasan dan dampak bisnis" className="h-10 rounded-xl border border-border bg-background px-3 text-sm" /></Field></div><Field label="Payload JSON"><textarea spellCheck={false} value={form.payload} onChange={(event) => set("payload", event.target.value)} className="min-h-56 rounded-xl border border-border bg-[#0b1220] p-4 font-mono text-xs leading-6 text-slate-100" /></Field><div className="mt-4 flex justify-end gap-2"><button onClick={onClose} className="rounded-xl border border-border px-4 py-2.5 text-xs font-bold">Batal</button><button disabled={busy} onClick={onSave} className="rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Simpan draft</button></div></section>;
}

function Detail({ item, preview, busy, onEdit, onSubmit, onClone }: { item: ConfigurationVersion | null; preview: ConfigurationPreview | null; busy: string | null; onEdit: () => void; onSubmit: () => void; onClone: () => void }) {
  if (!item) return <aside className="grid min-h-80 place-items-center rounded-2xl border border-dashed border-border bg-surface-soft p-8 text-center"><div><FileDiff className="mx-auto h-8 w-8 text-muted-foreground" /><p className="mt-3 text-sm font-semibold">Pilih versi konfigurasi</p><p className="mt-1 text-xs text-muted-foreground">Diff, snapshot, checksum, dan histori approval akan tampil di sini.</p></div></aside>;
  return <aside className="space-y-4"><section className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><div className="flex items-start justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-wider text-primary">{item.domain} · v{item.version}</p><h2 className="mt-1 font-mono text-base font-bold">{item.config_key}</h2><p className="mt-2 text-xs leading-5 text-muted-foreground">{item.change_summary}</p></div><Status value={item.status} /></div><dl className="mt-4 grid grid-cols-2 gap-3 border-y border-border py-4 text-xs"><Fact label="Mulai efektif" value={dateTime(item.effective_from)} /><Fact label="Aktif pada" value={dateTime(item.activated_at)} /><Fact label="Checksum SHA-256" value={`${item.checksum_sha256.slice(0, 16)}…`} mono /><Fact label="Berakhir" value={dateTime(item.effective_until)} /></dl><div className="mt-4 flex flex-wrap gap-2">{item.status === "draft" && <><button onClick={onEdit} className="rounded-lg border border-border px-3 py-2 text-xs font-bold">Edit draft</button><button disabled={busy !== null} onClick={onSubmit} className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-white">Kirim approval</button></>}<button disabled={busy !== null} onClick={onClone} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-bold"><CopyPlus className="h-3.5 w-3.5" />Klon versi baru</button></div></section>
    {preview && <section className="rounded-2xl border border-border bg-surface p-5"><div className="flex items-center justify-between"><div><h3 className="flex items-center gap-2 font-bold"><FileDiff className="h-4 w-4 text-primary" />Impact preview</h3><p className="mt-1 text-xs text-muted-foreground">v{preview.current_version ?? "∅"} → v{preview.candidate_version}</p></div><span className="rounded-lg bg-surface-blue px-2.5 py-1 text-xs font-bold text-primary">{preview.changed_field_count} field</span></div><div className="mt-4 space-y-3">{preview.changes.map((change) => <div key={change.field} className="rounded-xl border border-border p-3"><p className="font-mono text-xs font-bold">{change.field}</p><div className="mt-2 grid gap-2 text-[10px] sm:grid-cols-2"><pre className="overflow-auto rounded-lg bg-red-50 p-2 text-red-800">{pretty(change.before)}</pre><pre className="overflow-auto rounded-lg bg-emerald-50 p-2 text-emerald-800">{pretty(change.after)}</pre></div></div>)}{!preview.changes.length && <p className="text-xs text-muted-foreground">Payload sama dengan versi efektif.</p>}</div></section>}
    <section className="rounded-2xl border border-border bg-surface p-5"><h3 className="flex items-center gap-2 font-bold"><History className="h-4 w-4 text-primary" />Lifecycle event</h3><div className="mt-4 space-y-3">{item.events?.map((event) => <div key={event.id} className="border-l-2 border-primary/30 pl-3"><p className="text-xs font-bold">{event.event_type}</p><p className="mt-1 text-[10px] text-muted-foreground">{dateTime(event.occurred_at)} · {event.from_status ?? "∅"} → {event.to_status ?? "∅"}</p>{event.reason && <p className="mt-1 text-xs text-muted-foreground">{event.reason}</p>}</div>)}{!item.events?.length && <p className="text-xs text-muted-foreground">Belum ada event.</p>}</div></section>
  </aside>;
}

function Alert({ tone, text, close }: { tone: "success" | "danger"; text: string; close: () => void }) { return <div className={`flex items-center justify-between rounded-xl border px-4 py-3 text-xs font-semibold ${tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-800"}`}><span>{text}</span><button onClick={close}><X className="h-4 w-4" /></button></div>; }
function Metric({ icon: Icon, label, value, tone }: { icon: typeof Database; label: string; value: number; tone: "blue" | "slate" | "amber" | "green" }) { const color = { blue: "text-primary bg-surface-blue", slate: "text-slate-600 bg-slate-100", amber: "text-amber-700 bg-amber-50", green: "text-emerald-700 bg-emerald-50" }[tone]; return <article className="rounded-2xl border border-border bg-surface p-4"><span className={`grid h-9 w-9 place-items-center rounded-xl ${color}`}><Icon className="h-4 w-4" /></span><p className="mt-3 text-xs text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></article>; }
function Status({ value }: { value: string }) { const color = value === "effective" ? "bg-emerald-100 text-emerald-700" : value === "pending_approval" || value === "approved" ? "bg-amber-100 text-amber-800" : value === "rejected" ? "bg-red-100 text-red-700" : "bg-surface-soft text-muted-foreground"; return <span className={`whitespace-nowrap rounded-lg px-2.5 py-1 text-[10px] font-bold uppercase ${color}`}>{value.replaceAll("_", " ")}</span>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="mt-4 grid gap-2 text-xs font-semibold text-muted-foreground">{label}{children}</label>; }
function Fact({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) { return <div><dt className="text-[10px] uppercase text-muted-foreground">{label}</dt><dd className={`mt-1 font-semibold ${mono ? "font-mono" : ""}`}>{value}</dd></div>; }
