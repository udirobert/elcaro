import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { PageHeader } from "@/components/page-header";
import { CanaryResolver } from "@/components/canary-resolver";

export const metadata: Metadata = {
  title: "Canary resolver",
  description:
    "Resolve an elc- canary token to the scan that minted it — trap-street provenance for relayed quarantine notices.",
};

export default function CanaryPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      <SiteHeader active="canary" />

      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8 space-y-8">
        <PageHeader
          eyebrow="Provenance · trap streets"
          title="Found a Ref: elc- token?"
        >
          <p className="text-base text-ink-muted leading-relaxed max-w-lg">
            Every quarantine notice Elcaro serves carries a unique canary ref,
            and the specimen kit stamps one per fetch. Paste a token to see
            which scan minted it — the verdict signature authenticates the
            JSON; this traces the relayed text.
          </p>
        </PageHeader>

        <CanaryResolver />

        <div className="text-xs text-ink-faint leading-relaxed space-y-2 border-t border-border pt-6">
          <p>
            <span className="font-semibold text-ink-muted">What a hit means:</span>{" "}
            the token was minted inside a genuine quarantine notice — the
            shown score, level, and techniques are the original verdict, and
            only the content&apos;s SHA-256 is on record (never the content).
          </p>
          <p>
            <span className="font-semibold text-ink-muted">What a miss means:</span>{" "}
            forged, minted by another deployment, or older than the
            registry&apos;s memory. Worth flagging in your pipeline logs —
            but it proves nothing on its own. Trap streets trace copies, not
            ideas: an agent that paraphrases a notice drops the token.
          </p>
        </div>
      </div>

      <SiteFooter />
    </main>
  );
}
