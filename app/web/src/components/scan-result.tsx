import type { ScanResponse } from "@/lib/types";
import { RiskBadge } from "./risk-badge";
import { TechniquePill } from "./technique-pill";
import { IndicatorCard } from "./indicator-card";

interface ScanResultProps {
  result: ScanResponse;
}

export function ScanResult({ result }: ScanResultProps) {
  const isQuarantined = result.risk_score >= 0.5;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Risk score section */}
      <div className="border border-card-border rounded-xl bg-card p-6">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted mb-4">
          Risk Assessment
        </h3>
        <RiskBadge score={result.risk_score} level={result.risk_level} />

        {/* Techniques */}
        {result.flagged_techniques.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {result.flagged_techniques.map((technique) => (
              <TechniquePill key={technique} technique={technique} />
            ))}
          </div>
        )}

        {/* Latency */}
        <p className="mt-3 text-xs text-muted font-mono">
          Scanned in {result.latency_ms}ms
        </p>
      </div>

      {/* Indicators */}
      {result.indicators.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted mb-3">
            Detection Indicators ({result.indicators.length})
          </h3>
          <div className="space-y-2">
            {result.indicators.map((indicator, i) => (
              <IndicatorCard key={`${indicator.technique_name}-${i}`} indicator={indicator} />
            ))}
          </div>
        </div>
      )}

      {/* Quarantine decision */}
      <div
        className={`border rounded-xl p-4 ${
          isQuarantined
            ? "border-dangerous/30 bg-dangerous/5"
            : "border-safe/30 bg-safe/5"
        }`}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{isQuarantined ? "🚫" : "✅"}</span>
          <span className={`text-sm font-semibold ${isQuarantined ? "text-dangerous" : "text-safe"}`}>
            {isQuarantined
              ? "Content would be QUARANTINED"
              : "Content is safe to process"}
          </span>
        </div>
        {isQuarantined && (
          <p className="mt-2 text-xs text-muted">
            Risk score {result.risk_score.toFixed(2)} exceeds the 0.50 threshold.
            An agent using Elcaro middleware would block this content before processing.
          </p>
        )}
      </div>
    </div>
  );
}
