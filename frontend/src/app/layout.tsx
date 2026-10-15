import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PrivGadai",
  description: "Ruang kerja operasional untuk lembaga pergadaian berizin",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="id"
      data-theme="light"
      data-scroll-behavior="smooth"
      suppressHydrationWarning
    >
      <body
        className="min-h-screen bg-background text-foreground antialiased"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
