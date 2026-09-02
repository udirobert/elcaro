import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { SessionWatch } from "@/components/session-watch";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Supervise",
  description:
    "A calm-mode session watch — scan count, quarantine rate, and technique breakdown from your browser's local history.",
  robots: { index: false, follow: false },
};

export default function SupervisePage() {
  return (
    <main className="min-h-dvh flex flex-col">
      <SiteHeader />

      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8 space-y-8">
        <PageHeader eyebrow="Local session · nothing leaves this browser" title="Session watch">
          <p className="text-base text-ink-muted leading-relaxed max-w-lg">
            What your agent was shielded from this session — scan count,
            quarantine rate, techniques detected. Calm when safe, loud when not.
          </p>
        </PageHeader>

        <SessionWatch />
      </div>

      <SiteFooter />
    </main>
  );
}
