import { ScanForm } from "@/components/scan-form";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { EXAMPLES } from "@/lib/constants";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Scan",
  description:
    "Paste what your agent retrieved. Hidden instructions get caught before it acts.",
};

// ?example=<id> deep-links a preset — prefilled, never auto-scanned.
// Unknown, missing or ambiguous values render the normal blank scanner.
export default async function ScanPage({
  searchParams,
}: {
  searchParams: Promise<{ example?: string | string[] }>;
}) {
  const { example } = await searchParams;
  const preset =
    typeof example === "string"
      ? EXAMPLES.find((item) => item.id === example)
      : undefined;

  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader active="scan" />

      {/* Main content — generous space, the textarea is the hero */}
      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8">
        <ScanForm key={preset?.id ?? "blank"} initialExample={preset} />
      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
