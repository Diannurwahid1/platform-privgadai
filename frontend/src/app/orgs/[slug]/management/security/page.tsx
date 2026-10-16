"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, KeyRound, Laptop2, LockKeyhole, ShieldCheck, Smartphone, TriangleAlert } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/page-state";
import {
  activateMfa,
  getSecurityOverview,
  listAuthSessions,
  listSecurityEvents,
  revokeAuthSession,
  setupMfa,
  stepUpAuthentication,
  type AuthSessionItem,
  type SecurityEventItem,
  type SecurityOverview,
} from "@/lib/auth";

type Data = { overview: SecurityOverview; sessions: AuthSessionItem[]; events: SecurityEventItem[] };

export default function SecurityCenterPage() {
  const [data, setData] = useState<Data | null>(null);
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const load = useCallback(async () => {
    const [overview, sessions, events] = await Promise.all([
      getSecurityOverview(),
      listAuthSessions(),
      listSecurityEvents(),
    ]);
    setData({ overview, sessions, events });
  }, []);
  useEffect(() => { load().catch((reason: { detail?: string }) => setError(reason.detail ?? "Security Center gagal dimuat")); }, [load]);
  const activeSessions = useMemo(() => data?.sessions.filter((item) => item.is_active).length ?? 0, [data]);

  async function execute(key: string, action: () => Promise<unknown>, message: string) {
    setBusy(key); setError(null); setNotice(null);
    try { await action(); setNotice(message); await load(); }
    catch (reason) { setError((reason as { detail?: string }).detail ?? "Kontrol keamanan gagal dijalankan"); }
    finally { setBusy(null); }
  }
  async function beginSetup() {
    await execute("setup", async () => { const result = await setupMfa(password); setSetup(result); }, "Secret authenticator dibuat. Verifikasi kode untuk mengaktifkan MFA.");
  }
  async function finishSetup() {
    await execute("activate", async () => { const result = await activateMfa(mfaCode); setRecoveryCodes(result.recovery_codes); setSetup(null); setMfaCode(""); }, "MFA aktif. Simpan recovery code satu kali ini di tempat aman.");
  }
  async function stepUp() {
    await execute("step-up", () => stepUpAuthentication(password, mfaCode), "Step-up aktif selama 10 menit untuk tindakan sensitif.");
  }
  async function revoke(item: AuthSessionItem) {
    await execute(item.id, () => revokeAuthSession(item.id, item.is_current ? "Terminate current session" : "Remote session revoked by user"), item.is_current ? "Sesi saat ini dicabut." : "Sesi perangkat lain dicabut.");
  }

  if (error && !data) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Memuat kontrol keamanan" />;
  return <div className="space-y-6">
    <header className="border-b border-border pb-5"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">Identity assurance</p><div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between"><div><h1 className="text-3xl font-bold tracking-[-0.045em]">Security Center</h1><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Kelola MFA, step-up, perangkat aktif, pencabutan sesi, dan event keamanan akun.</p></div><span className={`rounded-xl px-3 py-2 text-xs font-bold ${data.overview.mfa_enabled ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>{data.overview.mfa_enabled ? "MFA aktif" : "MFA belum aktif"}</span></div></header>
    {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <section className="grid gap-4 md:grid-cols-3"><Metric icon={ShieldCheck} label="MFA" value={data.overview.mfa_enabled ? "Protected" : "Action required"} /><Metric icon={Laptop2} label="Sesi aktif" value={String(activeSessions)} /><Metric icon={KeyRound} label="Recovery code" value={String(data.overview.recovery_codes_remaining)} /></section>
    <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><div className="flex items-center gap-2"><Smartphone className="h-5 w-5 text-primary"/><h2 className="font-bold">Authenticator & step-up</h2></div><p className="mt-2 text-xs leading-5 text-muted-foreground">Tindakan approval dan delegasi di production memerlukan konfirmasi password dan MFA yang masih berlaku.</p><div className="mt-5 space-y-3"><input type="password" value={password} onChange={(event)=>setPassword(event.target.value)} placeholder="Password saat ini" className="h-10 w-full rounded-xl border border-border bg-background px-3 text-sm"/><input value={mfaCode} onChange={(event)=>setMfaCode(event.target.value)} placeholder="Kode 6 digit atau recovery code" className="h-10 w-full rounded-xl border border-border bg-background px-3 font-mono text-sm"/><div className="flex flex-wrap gap-2">{!data.overview.mfa_enabled && <button disabled={busy!==null||!password} onClick={()=>void beginSetup()} className="rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Mulai setup MFA</button>}{setup && <button disabled={busy!==null||mfaCode.length!==6} onClick={()=>void finishSetup()} className="rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50">Verifikasi & aktifkan</button>}<button disabled={busy!==null||!password||(data.overview.mfa_enabled&&!mfaCode)} onClick={()=>void stepUp()} className="rounded-xl border border-primary px-4 py-2.5 text-xs font-bold text-primary disabled:opacity-50">Aktifkan step-up</button></div>{setup && <div className="rounded-xl border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900"><p className="font-bold">Tambahkan ke authenticator</p><p className="mt-2 break-all font-mono">{setup.secret}</p><p className="mt-2 break-all text-[10px]">{setup.otpauth_uri}</p></div>}{recoveryCodes.length>0&&<div className="rounded-xl border border-amber-200 bg-amber-50 p-3"><p className="flex items-center gap-2 text-xs font-bold text-amber-900"><TriangleAlert className="h-4 w-4"/>Recovery code hanya ditampilkan sekali</p><div className="mt-3 grid grid-cols-2 gap-2">{recoveryCodes.map((code)=><code key={code} className="rounded-lg bg-white px-2 py-1.5 text-xs">{code}</code>)}</div></div>}</div></article>
      <article className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="border-b border-border px-5 py-4"><h2 className="font-bold">Session inventory</h2><p className="mt-1 text-xs text-muted-foreground">Session ID divalidasi pada setiap request; revoke berlaku segera.</p></div><div className="divide-y divide-border">{data.sessions.map((item)=><div key={item.id} className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-surface-blue text-primary"><Laptop2 className="h-5 w-5"/></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="text-xs font-bold">{item.ip_address??"IP tidak tersedia"}</p>{item.is_current&&<span className="rounded-md bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700">Perangkat ini</span>}{item.mfa_authenticated&&<span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">MFA</span>}</div><p className="mt-1 truncate text-[10px] text-muted-foreground">{item.user_agent??"User agent tidak tersedia"}</p><p className="mt-1 text-[10px] text-muted-foreground">Terakhir aktif {new Date(item.last_seen_at).toLocaleString("id-ID")}</p></div><span className={`text-xs font-bold ${item.is_active?"text-emerald-700":"text-muted-foreground"}`}>{item.is_active?"Aktif":"Berakhir"}</span>{item.is_active&&<button disabled={busy!==null} onClick={()=>void revoke(item)} className="rounded-lg border border-red-200 px-3 py-2 text-xs font-bold text-red-700 disabled:opacity-50">Cabut</button>}</div>)}</div></article>
    </section>
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]"><div className="flex items-center gap-2 border-b border-border px-5 py-4"><Activity className="h-5 w-5 text-primary"/><div><h2 className="font-bold">Security event explorer</h2><p className="text-xs text-muted-foreground">Login, enrollment, step-up, dan revoke sebagai event bisnis.</p></div></div><div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="border-b border-border bg-surface-soft text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Waktu</th><th className="px-5 py-3">Event</th><th className="px-5 py-3">Outcome</th><th className="px-5 py-3">IP</th><th className="px-5 py-3">Keterangan</th></tr></thead><tbody className="divide-y divide-border">{data.events.map((item)=><tr key={item.id}><td className="px-5 py-4 text-xs">{new Date(item.occurred_at).toLocaleString("id-ID")}</td><td className="px-5 py-4 font-mono text-xs font-bold text-primary">{item.event_type}</td><td className="px-5 py-4"><span className={`rounded-lg px-2 py-1 text-xs font-bold ${item.outcome==="success"?"bg-emerald-50 text-emerald-700":"bg-red-50 text-red-700"}`}>{item.outcome}</span></td><td className="px-5 py-4 text-xs">{item.ip_address??"—"}</td><td className="px-5 py-4 text-xs text-muted-foreground">{item.description}</td></tr>)}</tbody></table>{!data.events.length&&<p className="p-10 text-center text-sm text-muted-foreground">Belum ada security event.</p>}</div></section>
  </div>;
}

function Metric({icon:Icon,label,value}:{icon:typeof LockKeyhole;label:string;value:string}){return <article className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]"><Icon className="h-5 w-5 text-primary"/><p className="mt-4 text-2xl font-bold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{label}</p></article>;}
