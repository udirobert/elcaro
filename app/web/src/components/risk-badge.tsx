import type { RiskLevel } from "@/lib/types";
import { RISK_COLORS } from "@/lib/constants";

interface RiskBadgeProps {
  score: number;
  level: RiskLevel;
}

export function RiskBadge({ score, level }: RiskBadgeProps) {
  const colorClasses = RISK_COLORS[level] || RISK_COLORS.safe;

  return (
    <div className="flex items-center gap-4">
      {/* Score number */}
      <div className={`text-4xl font-mono font-bold ${colorClasses.split(" ")[0]}`}>
        {score.toFixed(2)}
      </div>

      {/* Level badge */}
      <span
        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border ${colorClasses}`}
      >
        {level}
      </span>

      {/* Visual bar */}
      <div className="flex-1 max-w-48 h-2 rounded-full bg-card-border overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            level === "safe"
              ? "bg-safe"
              : level === "low"
                ? "bg-low"
                : level === "suspicious"
                  ? "bg-suspicious"
                  : "bg-dangerous"
          }`}
          style={{ width: `${Math.min(score * 100, 100)}%` }}
        />
      </div>
    </div>
  );
}
