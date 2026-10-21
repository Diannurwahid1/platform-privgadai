"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, CheckCircle2, Fingerprint, RefreshCw, ShieldAlert } from "lucide-react";
import { listCollateralProofs, verifyCollateralProof, type CollateralProof, type ProofVerification } from "@/lib/operations";

const statusLabels: Record<string, string> = {
  pending: "Menunggu relayer", submitted: "Menunggu konfirmasi", confirmed: "Terkonfirmasi",
  verified_on_chain: "Ada di chain", failed: "Perlu pengiriman ulang", reverted: "Transaksi gagal",
};

export function ProofRegister({ applicationId }: { applicationId?: string }) {
  const [proofs, setProofs] = useState<CollateralProof[]>([]);
  const [checks, setChecks] = useState<Record<string, ProofVerification>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setBusy("refresh");
    try { setProofs(await listCollateralProofs(applicationId)); setError(null); }
    catch { setError("Register proof belum dapat dimuat."); }
    finally { setBusy(null); }
  }, [applicationId]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function verify(id: string) {
    setBusy(id);
    try { const result = await verifyCollateralProof(id); setChecks((current) => ({ ...current, [id]: result })); setError(null); }
    catch { setError("Verifikasi chain belum tersedia. Coba lagi."); }
    finally { setBusy(null); }
  }

  return <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[var(--pg-shadow-sm)]">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
      <div className="flex items-start gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-surface-blue text-primary"><Fingerprint className="h-5 w-5" /></span><div><h2 className="font-bold">Proof of Custody · BSC Testnet</h2><p className="mt-1 max-w-2xl text-xs text-muted-foreground">Digest dari event custody dicatat di blockchain. Bukti fisik dan data nasabah tetap diperiksa di sistem internal.</p></div></div>
      <button type="button" onClick={() => void refresh()} disabled={busy !== null} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-primary disabled:opacity-50"><RefreshCw className="h-3.5 w-3.5" />Segarkan</button>
    </div>
    {error && <p role="alert" className="px-5 py-3 text-xs text-red-700">{error}</p>}
    {!proofs.length && <p className="px-5 py-7 text-sm text-muted-foreground">Belum ada proof. Proof dibuat setelah event penyimpanan atau serah terima custody disahkan.</p>}
    <div className="divide-y divide-border">
      {proofs.map((proof) => {
        const check = checks[proof.id];
        return <article key={proof.id} className="flex flex-col gap-3 px-5 py-4 lg:flex-row lg:items-center">
          <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><b className="text-sm">{proof.event_type.replaceAll("_", " ")}</b><span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${proof.status === "confirmed" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{statusLabels[proof.status] ?? proof.status}</span></div><p className="mt-1 truncate font-mono text-[10px] text-muted-foreground">Event {proof.opaque_event_id}</p><p className="mt-1 text-[11px] text-muted-foreground">{proof.block_number ? `Block ${proof.block_number} · ` : ""}Chain ID {proof.chain_id}</p>{check && <p className={`mt-2 inline-flex items-center gap-1 text-xs font-semibold ${check.local_integrity && check.chain_match ? "text-emerald-700" : "text-amber-700"}`}>{check.local_integrity && check.chain_match ? <CheckCircle2 className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}{check.local_integrity && check.chain_match ? "Snapshot dan digest on-chain cocok" : check.chain_error ?? "Proof belum cocok; perlu pemeriksaan"}</p>}</div>
          <div className="flex shrink-0 gap-2"><button type="button" disabled={busy !== null} onClick={() => void verify(proof.id)} className="rounded-lg border border-primary px-3 py-2 text-xs font-bold text-primary disabled:opacity-50">Verifikasi bukti</button>{proof.explorer_url && <a href={proof.explorer_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-xs font-semibold">BscScan <ArrowUpRight className="h-3.5 w-3.5" /></a>}</div>
        </article>;
      })}
    </div>
  </section>;
}
