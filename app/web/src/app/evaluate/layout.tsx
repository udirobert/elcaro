import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { EvaluateNav } from "@/components/evaluate-nav";

// Shared chrome for the /evaluate route family — the tab bar lives here so
// each tool stays its own route (own URL, metadata, code split) while the
// proving ground reads as one surface.

export default function EvaluateLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader active="evaluate" />

      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8 space-y-8">
        <div className="page-enter space-y-4">
          <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
            Proving ground · live against the production engine
          </p>
          <EvaluateNav />
        </div>

        {children}
      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
