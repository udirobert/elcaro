import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { LeadForm } from "@/components/lead-form";
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
      <SiteHeader active="supervise" />

      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8 space-y-8">
        <PageHeader eyebrow="Local session · nothing leaves this browser" title="Session watch">
          <p className="text-base text-ink-muted leading-relaxed max-w-lg">
            What your agent was shielded from this session — scan count,
            quarantine rate, techniques detected. Calm when safe, loud when not.
          </p>
        </PageHeader>

        <SessionWatch />

        {/* E4 — the fleet probe. Session watch covers one browser; the
            paid shape is one watch across every agent you run, with
            canary-traced propagation and incident reconstruction on top.
            The waitlist is the demand signal. */}
        <div className="border-t border-border pt-8">
          <LeadForm
            formName="fleet-waitlist"
            heading="Running more than one agent?"
            body="Session watch covers this browser. Fleet watch is the same calm surface across every agent you operate — quarantine rate per agent, canary-traced propagation between them, and incident reconstruction when something gets through. Join the list; we'll reach out when fleet mode opens."
            ctaLabel="Join waitlist"
          />
        </div>
      </div>

      <SiteFooter />
    </main>
  );
}
