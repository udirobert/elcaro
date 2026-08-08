import Link from "next/link";
import { ScanForm } from "@/components/scan-form";

export default function ScanPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Minimal header */}
      <header className="px-6 py-5 flex items-center justify-between">
        <Link
          href="/"
          className="text-sm font-bold tracking-tight text-ink hover:text-violet transition-colors"
        >
          elcaro
        </Link>
        <span className="text-xs text-ink-faint font-mono">
          v0.1
        </span>
      </header>

      {/* Main content — generous space, the textarea is the hero */}
      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8">
        <ScanForm />
      </div>
    </main>
  );
}
