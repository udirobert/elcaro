import { ScanForm } from "@/components/scan-form";
import Link from "next/link";

export default function ScanPage() {
  return (
    <main className="flex-1 flex flex-col">
      {/* Header */}
      <header className="border-b border-card-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            elcaro
          </Link>
          <span className="text-xs text-muted font-mono">
            IPI Detection Engine
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 max-w-4xl mx-auto w-full px-6 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight">Content Scanner</h1>
          <p className="mt-2 text-sm text-muted">
            Paste any content below to scan it for indirect prompt injection.
            The detection engine analyses the text for known IPI technique
            patterns and returns a risk assessment.
          </p>
        </div>

        <ScanForm />
      </div>
    </main>
  );
}
