import { redirect } from "next/navigation";

export default async function LegacyFinancePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  redirect(`/orgs/${slug}/finance/teller`);
}
