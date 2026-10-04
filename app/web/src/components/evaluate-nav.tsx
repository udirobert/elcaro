"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Segmented nav for the /evaluate route family — real links, not client
// state, so each tool keeps its own URL, metadata, and prefetch. Active
// state comes from the pathname; the layout renders this once above the
// child page.

const TOOLS: { href: string; label: string }[] = [
  { href: "/evaluate/gauntlet", label: "Gauntlet" },
  { href: "/evaluate/redteam", label: "Red team" },
  { href: "/evaluate/audit", label: "Prompt audit" },
];

export function EvaluateNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Evaluation tools"
      className="inline-flex rounded-xl border border-border overflow-hidden text-sm"
    >
      {TOOLS.map((t) => {
        const active = pathname === t.href;
        return (
          <Link
            key={t.href}
            href={t.href}
            aria-current={active ? "page" : undefined}
            className={`px-4 py-2 font-semibold transition-colors ${
              active
                ? "bg-ink text-canvas"
                : "bg-surface text-ink-muted hover:text-ink"
            }`}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
