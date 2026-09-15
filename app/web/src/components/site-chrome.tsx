import Link from "next/link";
import { MinerStatus } from "./miner-status";

// Shared site chrome — one source of truth for the header and footer so
// every route has identical wayfinding. Pages pass their `active` key for
// highlighting (kept as a prop so pages stay server-rendered).

export type NavKey =
  | "scan"
  | "gauntlet"
  | "vulnerable"
  | "redteam"
  | "specimen"
  | "supervise"
  | "integrate"
  | "for-agents";

const NAV_ITEMS: { key: NavKey; href: string; label: string }[] = [
  { key: "scan", href: "/scan", label: "Scan" },
  { key: "gauntlet", href: "/gauntlet", label: "Gauntlet" },
  { key: "vulnerable", href: "/vulnerable", label: "Vulnerable" },
  { key: "redteam", href: "/redteam", label: "Red team" },
  { key: "specimen", href: "/specimen", label: "Specimen" },
  { key: "supervise", href: "/supervise", label: "Supervise" },
  { key: "integrate", href: "/integrate", label: "Integrate" },
  { key: "for-agents", href: "/for-agents", label: "For agents" },
];

export function SiteHeader({ active }: { active?: NavKey }) {
  return (
    <header className="px-6 py-5 flex flex-wrap items-center justify-between gap-y-3">
      <Link
        href="/"
        className="text-sm font-bold tracking-tight text-ink hover:text-ink-muted transition-colors shrink-0"
      >
        elcaro
      </Link>
      <div className="flex items-center flex-wrap justify-end gap-x-4 gap-y-2">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.key}
            href={item.href}
            aria-current={active === item.key ? "page" : undefined}
            className={`text-xs whitespace-nowrap transition-colors ${
              active === item.key
                ? "text-ink font-semibold"
                : "text-ink-faint hover:text-ink"
            }`}
          >
            {item.label}
          </Link>
        ))}
        <MinerStatus />
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-border px-6 py-8 text-center">
      <p className="text-xs text-ink-faint">
        Open source ·{" "}
        <a
          href="https://github.com/udirobert/elcaro"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-ink transition-colors underline underline-offset-2"
        >
          GitHub
        </a>
        {" "}· Live as a miner on{" "}
        <a
          href="https://telegraphprotocol.com"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-ink transition-colors underline underline-offset-2"
        >
          Telegraph Protocol
        </a>
      </p>
    </footer>
  );
}
