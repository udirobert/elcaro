import type { Metadata } from "next";

import { KeyManager } from "@/components/key-manager";
import { PageHeader } from "@/components/page-header";
import { SiteFooter, SiteHeader } from "@/components/site-chrome";
import { AnalyticsPageView } from "@/components/analytics-page-view";

export const metadata: Metadata = {
  title: "API keys",
  description:
    "Mint, track, and revoke Elcaro Gateway keys. Keys are bearer tokens — the raw key is shown once and only its hash is stored.",
};

export default function KeysPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      <AnalyticsPageView event="keys.viewed" />
      <SiteHeader />

      <div className="flex-1 max-w-2xl mx-auto w-full px-6 py-14 space-y-10">
        <PageHeader eyebrow="Gateway · keys" title="API keys">
          <p className="text-base text-ink-muted leading-relaxed max-w-lg">
            Gateway calls authenticate with an{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-sm text-ink-muted">
              elk_
            </code>{" "}
            key in{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-sm text-ink-muted">
              x-elcaro-key
            </code>
            . Mint one below — it works with the URL-swap SDKs on{" "}
            <a href="/integrate" className="text-violet underline underline-offset-2 hover:text-violet/80 transition-colors">
              /integrate
            </a>
            .
          </p>
        </PageHeader>

        <KeyManager />
      </div>

      <SiteFooter />
    </main>
  );
}
