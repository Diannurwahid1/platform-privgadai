"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, FileLock2, IdCard, ShieldAlert, Upload } from "lucide-react";
import { getCustomerKyc, reviewCustomerKyc, startCustomerKyc, uploadKycDocument, type CustomerKyc } from "@/lib/operations";

const inputClass = "w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/10";
const initial = { nik: "", legal_name: "", birth_place: "", birth_date: "", gender: "male", address: "", province: "", city: "", occupation: "", verification_method: "manual_branch" };

export function CustomerKycWorkspace({ customerId, customerName }: { customerId: string; customerName: string }) {
  const [data, setData] = useState<CustomerKyc | null>(null);
  const [form, setForm] = useState({ ...initial, legal_name: customerName.toUpperCase() });
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const load = useCallback(() => getCustomerKyc(customerId).then(setData).catch((e: { detail?: string }) => setMessage(e.detail ?? "KYC gagal dimuat")), [customerId]);
  useEffect(() => { void load(); }, [load]);
  const latest = data?.verifications[0];

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage(null);
    try {
      const result = await startCustomerKyc(customerId, form);
      const file = (event.currentTarget.elements.namedItem("ktp") as HTMLInputElement).files?.[0];
      if (!file) throw { detail: "Foto sisi depan KTP wajib dipilih" };
      await uploadKycDocument(customerId, result.id, file);
      setShowForm(false); setMessage("Data dan dokumen KTP direkam untuk pemeriksaan checker."); await load();
    } catch (e) { setMessage((e as { detail?: string }).detail ?? "KYC gagal direkam"); }
    finally { setBusy(false); }
  }

  async function decide(decision: "verified" | "rejected" | "needs_information") {
    if (!latest) return;
    const reason = window.prompt("Tuliskan alasan keputusan KYC. Alasan akan masuk audit:");
    if (!reason) return;
    setBusy(true); setMessage(null);
    try { await reviewCustomerKyc(customerId, latest.id, { decision, reason, risk_level: latest.risk_level }); setMessage("Keputusan KYC tersimpan."); await load(); }
    catch (e) { setMessage((e as { detail?: string }).detail ?? "Keputusan gagal disimpan"); }
    finally { setBusy(false); }
  }

  return <section className="rounded-2xl border border-border bg-surface p-5 shadow-[var(--pg-shadow-sm)]">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex items-center gap-2"><IdCard className="h-5 w-5 text-primary" /><h2 className="font-bold">KYC dan Customer Due Diligence</h2></div><p className="mt-1 text-xs text-muted-foreground">Identifikasi KTP, pemeriksaan bukti, risiko, dan keputusan checker.</p></div><button type="button" onClick={() => setShowForm((v) => !v)} className="h-10 rounded-xl bg-primary px-4 text-xs font-bold text-white">{showForm ? "Tutup formulir" : latest ? "Perbarui KYC" : "Mulai KYC"}</button></div>
    {message && <div className="mt-4 rounded-xl border border-primary/20 bg-surface-blue px-4 py-3 text-xs font-medium text-primary">{message}</div>}
    {!showForm && latest && <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_1fr_1.1fr]">
      <Card icon={latest.status === "verified" ? CheckCircle2 : ShieldAlert} title="Status pemeriksaan"><Status value={latest.status} /><p className="mt-2 text-xs text-muted-foreground">Risiko {latest.risk_level} · {latest.verification_method.replaceAll("_", " ")}</p><p className="mt-2 text-xs">{latest.decision_reason ?? "Menunggu keputusan checker."}</p></Card>
      <Card icon={IdCard} title="Identitas KTP"><Line label="NIK" value={latest.national_id_masked} /><Line label="Nama" value={latest.legal_name} /><Line label="Lahir" value={`${latest.birth_place}, ${latest.birth_date}`} /><Line label="Alamat" value={`${latest.address}, ${latest.city}, ${latest.province}`} /></Card>
      <Card icon={FileLock2} title="Bukti terenkripsi"><p className="text-2xl font-bold">{latest.documents.length}</p><p className="text-xs text-muted-foreground">Dokumen privat dan checksum SHA-256</p>{["pending_review", "needs_information"].includes(latest.status) && <div className="mt-4 flex flex-wrap gap-2"><button disabled={busy} onClick={() => decide("verified")} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white">Verifikasi</button><button disabled={busy} onClick={() => decide("needs_information")} className="rounded-lg border border-border px-3 py-2 text-xs font-bold">Minta data</button><button disabled={busy} onClick={() => decide("rejected")} className="rounded-lg bg-red-50 px-3 py-2 text-xs font-bold text-red-700">Tolak</button></div>}<p className="mt-3 text-[11px] text-muted-foreground">Maker tidak dapat menjadi checker pada verifikasi yang sama.</p></Card>
    </div>}
    {!showForm && !latest && <div className="mt-5 rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">Belum ada pemeriksaan KYC. Rekam data sesuai KTP dan unggah bukti sisi depan.</div>}
    {showForm && <form onSubmit={submit} className="mt-5 grid gap-4 border-t border-border pt-5 md:grid-cols-2 xl:grid-cols-3">
      <Field label="NIK 16 digit"><input required inputMode="numeric" pattern="[0-9]{16}" maxLength={16} value={form.nik} onChange={(e) => setForm({ ...form, nik: e.target.value.replace(/\D/g, "") })} className={inputClass} /></Field>
      <Field label="Nama sesuai KTP"><input required value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} className={inputClass} /></Field>
      <Field label="Tempat lahir"><input required value={form.birth_place} onChange={(e) => setForm({ ...form, birth_place: e.target.value })} className={inputClass} /></Field>
      <Field label="Tanggal lahir"><input required type="date" value={form.birth_date} onChange={(e) => setForm({ ...form, birth_date: e.target.value })} className={inputClass} /></Field>
      <Field label="Jenis kelamin"><select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })} className={inputClass}><option value="male">Laki-laki</option><option value="female">Perempuan</option></select></Field>
      <Field label="Pekerjaan"><input value={form.occupation} onChange={(e) => setForm({ ...form, occupation: e.target.value })} className={inputClass} /></Field>
      <Field label="Provinsi"><input required value={form.province} onChange={(e) => setForm({ ...form, province: e.target.value })} className={inputClass} /></Field>
      <Field label="Kabupaten/Kota"><input required value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className={inputClass} /></Field>
      <Field label="Foto sisi depan KTP"><input required name="ktp" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className={inputClass} /></Field>
      <Field label="Alamat lengkap" wide><textarea required value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className={`${inputClass} min-h-24`} /></Field>
      <div className="flex items-end"><button disabled={busy} type="submit" className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-white disabled:opacity-50"><Upload className="h-4 w-4" />{busy ? "Menyimpan…" : "Simpan dan unggah KTP"}</button></div>
    </form>}
  </section>;
}

function Card({ icon: Icon, title, children }: { icon: typeof IdCard; title: string; children: React.ReactNode }) { return <div className="rounded-xl border border-border bg-surface-soft p-4"><div className="flex items-center gap-2"><Icon className="h-4 w-4 text-primary" /><h3 className="text-xs font-bold uppercase tracking-wide">{title}</h3></div><div className="mt-4 space-y-2">{children}</div></div>; }
function Status({ value }: { value: string }) { const ok=value === "verified"; return <span className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-bold ${ok ? "bg-emerald-100 text-emerald-700" : value === "rejected" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>{value.replaceAll("_", " ")}</span>; }
function Line({ label, value }: { label: string; value: string }) { return <div><p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-0.5 text-xs font-medium">{value}</p></div>; }
function Field({ label, wide=false, children }: { label: string; wide?: boolean; children: React.ReactNode }) { return <label className={`space-y-1.5 text-xs font-semibold ${wide ? "md:col-span-2" : ""}`}><span>{label}</span>{children}</label>; }
