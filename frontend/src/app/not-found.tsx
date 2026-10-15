import { ErrorState } from "@/components/page-state";

export default function NotFound() {
  return (
    <ErrorState
      title="Page not found"
      message="Halaman PrivGadai ini belum tersedia."
      actionHref="/dashboard"
      actionLabel="Go to dashboard"
    />
  );
}
