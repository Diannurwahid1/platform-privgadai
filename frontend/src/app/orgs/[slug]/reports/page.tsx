import { redirect } from "next/navigation";

export default async function LegacyReportsPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  redirect(`/orgs/${slug}/reports/financial`);
}
