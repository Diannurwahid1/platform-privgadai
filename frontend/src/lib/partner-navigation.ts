import {
  BarChart3,
  BadgeDollarSign,
  BookOpenCheck,
  Boxes,
  Building2,
  ClipboardCheck,
  ClipboardList,
  ContactRound,
  IdCard,
  FileCheck2,
  FileSearch,
  HandCoins,
  LayoutDashboard,
  PackageSearch,
  ReceiptText,
  MessagesSquare,
  Scale,
  ScrollText,
  Settings,
  ShieldAlert,
  Truck,
  Users,
} from "lucide-react";

export type PartnerNavItem = {
  id: string;
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  match?: "exact" | "section";
  aliases?: string[];
  exactAliases?: string[];
  excludes?: string[];
};

export type PartnerNavGroup = { id: string; label: string; items: PartnerNavItem[] };

export function buildPartnerNavigation(slug: string): PartnerNavGroup[] {
  const root = `/orgs/${slug}`;
  return [
    { id: "overview", label: "Overview", items: [
      { id: "overview", label: "Ringkasan", href: `${root}/overview`, aliases: [root], icon: LayoutDashboard, match: "exact" },
    ] },
    { id: "customers", label: "Customers", items: [
      { id: "customers", label: "Debitur & CRM", href: `${root}/customers`, icon: ContactRound, match: "section", excludes: [`${root}/customers/kyc`] },
      { id: "customer-kyc", label: "KYC & CDD", href: `${root}/customers/kyc`, icon: IdCard, match: "section" },
    ] },
    { id: "loans", label: "Loans", items: [
      { id: "applications", label: "Pengajuan", href: `${root}/loans/applications`, aliases: [`${root}/applications`], icon: ClipboardList, match: "section" },
      { id: "appraisals", label: "Penaksiran", href: `${root}/loans/appraisals`, icon: Scale, match: "section" },
    ] },
    { id: "collateral", label: "Collateral", items: [
      { id: "passports", label: "Passport & Custody", href: `${root}/collateral/passports`, exactAliases: [`${root}/collateral`], icon: PackageSearch, match: "section" },
      { id: "pickups", label: "Pickup Lapangan", href: `${root}/collateral/pickups`, aliases: [`${root}/field`], icon: Truck, match: "section" },
      { id: "inventory", label: "Stock Opname", href: `${root}/collateral/inventory`, aliases: [`${root}/inventory`], icon: Boxes, match: "section" },
    ] },
    { id: "finance", label: "Finance", items: [
      { id: "teller", label: "Teller & Cash", href: `${root}/finance/teller`, exactAliases: [`${root}/finance`], icon: BadgeDollarSign, match: "section" },
      { id: "payments", label: "Payments", href: `${root}/finance/payments`, icon: ReceiptText, match: "section" },
      { id: "collections", label: "Collections", href: `${root}/finance/collections`, icon: HandCoins, match: "section" },
      { id: "ledger", label: "General Ledger", href: `${root}/finance/general-ledger`, icon: BookOpenCheck, match: "section" },
      { id: "reconciliation", label: "Reconciliation", href: `${root}/finance/reconciliation`, icon: FileSearch, match: "section" },
    ] },
    { id: "reports", label: "Reports", items: [
      { id: "financial", label: "Financial & BI", href: `${root}/reports/financial`, exactAliases: [`${root}/reports`], icon: BarChart3, match: "section" },
      { id: "regulatory", label: "OJK & SLIK", href: `${root}/reports/regulatory`, icon: FileCheck2, match: "section" },
    ] },
    { id: "compliance", label: "Compliance", items: [
      { id: "exceptions", label: "Exceptions", href: `${root}/compliance/exceptions`, icon: ShieldAlert, match: "section" },
      { id: "complaints", label: "Complaints", href: `${root}/compliance/complaints`, icon: MessagesSquare, match: "section" },
      { id: "approvals", label: "Approvals", href: `${root}/compliance/approvals`, icon: ClipboardCheck, match: "section" },
      { id: "audit", label: "Audit Event", href: `${root}/compliance/audit`, aliases: [`${root}/audit-log`], icon: ScrollText, match: "section" },
    ] },
    { id: "management", label: "Management", items: [
      { id: "master", label: "Master Data", href: `${root}/management/master-data`, aliases: [`${root}/master-data`], icon: Building2, match: "section" },
      { id: "members", label: "Tim & Akses", href: `${root}/management/team-access`, aliases: [`${root}/members`], icon: Users, match: "section" },
      { id: "settings", label: "Pengaturan", href: `${root}/management/settings`, aliases: [`${root}/settings`], icon: Settings, match: "section" },
    ] },
  ];
}

export function isPartnerNavItemActive(item: PartnerNavItem, pathname: string) {
  if (item.excludes?.some((candidate) => pathname === candidate || pathname.startsWith(`${candidate}/`))) return false;
  if (item.exactAliases?.includes(pathname)) return true;
  return [item.href, ...(item.aliases ?? [])].some((candidate) =>
    item.match === "exact" ? pathname === candidate : pathname === candidate || pathname.startsWith(`${candidate}/`),
  );
}
