"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ClipboardList, Home, IdCard, PlusCircle } from "lucide-react";
import type { ReactNode } from "react";
import { borrowerFetch, type BorrowerMe } from "@/lib/borrower";
import s from "./borrower.module.css";

export function Brand() {
  return <Link href="/borrower" className={s.brand}><Image src="/privgadai-logo-dark.svg" alt="PrivGadai" width={185} height={70} priority /></Link>;
}

export function Shell({ children, me }: { children: ReactNode; me?: BorrowerMe | null }) {
  const router = useRouter();
  const pathname = usePathname();
  async function logout() {
    try { await borrowerFetch("/logout", { method: "POST" }); } finally { router.push("/borrower"); router.refresh(); }
  }
  return <div className={s.root}>
    <header className={s.top}><Brand /><nav className={s.nav}>
      <Link href="/borrower">Beranda</Link>
      {me && <Link href="/borrower/kyc">KYC</Link>}
      {me && <Link href="/borrower/apply">Ajukan gadai</Link>}
      {me ? <button className={s.account} onClick={logout} title="Keluar dari akun borrower">{me.full_name.split(" ")[0]} · Keluar</button> : <Link href="/login" title="Masuk sebagai petugas">Portal petugas</Link>}
    </nav></header>{children}
    {me && <nav className={s.mobileNav} aria-label="Navigasi borrower">
      <Link className={pathname === "/borrower" ? s.mobileActive : ""} href="/borrower"><Home size={19} />Beranda</Link>
      <Link className={pathname === "/borrower/kyc" ? s.mobileActive : ""} href="/borrower/kyc"><IdCard size={19} />KYC</Link>
      <Link className={pathname === "/borrower/apply" ? s.mobileActive : ""} href="/borrower/apply"><PlusCircle size={19} />Ajukan</Link>
      <Link className={pathname.startsWith("/borrower/applications/") ? s.mobileActive : ""} href="/borrower#applications"><ClipboardList size={19} />Status</Link>
    </nav>}
  </div>;
}

export function Mascot({ className = "" }: { className?: string }) {
  return <Image src="/brand/privgadai-mascot-wave.png" alt="Maskot robot PrivGadai menyapa" width={500} height={755} className={className} priority />;
}

export function Footer() { return <footer className={s.footer}>PrivGadai · Layanan PT Murah Gadai Jogja · Estimasi awal selalu ditinjau petugas.</footer>; }

export function ErrorBox({ message }: { message: string | null }) { return message ? <div role="alert" className={s.error}>{message}</div> : null; }

export function Status({ value }: { value: string }) {
  const labels: Record<string, string> = { submitted: "Baru masuk", under_review: "Sedang ditinjau", appraisal: "Penaksiran", offered: "Penawaran tersedia", accepted: "Penawaran diterima", active: "Pinjaman aktif", settled: "Lunas", SUCCESS: "Estimasi tersedia", NEEDS_REVIEW: "Perlu pemeriksaan", UNSUPPORTED: "Menunggu penaksir" };
  return <span className={s.status}>{labels[value] ?? value.replaceAll("_", " ")}</span>;
}
