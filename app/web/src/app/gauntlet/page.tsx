import Link from "next/link";
import type { Metadata } from "next";
import { GauntletRunner } from "@/components/gauntlet-runner";

export const metadata: Metadata = {
  title: "The Gauntlet",
  description:
    "Eight payloads, one click: watch Elcaro catch all six classes of indirect prompt injection — live, against the production engine.",
};

export default function GauntletPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Minimal header — consistent with /scan */}
      <header className="px-6 py-5 flex items-center justify-between">
        <Link
          href="/"
          className="text-sm font-bold tracking-tight text-ink hover:text-violet transition-colors"
        >
          elcaro
        </Link>
        <div className="flex items-center gap-4">
          <Link
            href="/scan"
            className="text-xs text-ink-faint hover:text-ink transition-colors"
          >
            Scan
          </Link>
          <Link
            href="/integrate"
            className="text-xs text-ink-faint hover:text-ink transition-colors"
          >
            Integrate
          </Link>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8">
        <GauntletRunner />
      </div>
    </main>
  );
}
