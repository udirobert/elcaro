import { ScanForm } from "@/components/scan-form";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Scan",
  description:
    "Paste what your agent retrieved. Hidden instructions get caught before it acts.",
};

export default function ScanPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader active="scan" />

      {/* Main content — generous space, the textarea is the hero */}
      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8">
        <ScanForm />
      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
