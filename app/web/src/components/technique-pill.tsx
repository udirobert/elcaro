import type { TechniqueClass } from "@/lib/types";
import { TECHNIQUE_LABELS } from "@/lib/constants";

interface TechniquePillProps {
  technique: TechniqueClass;
}

const PILL_COLORS: Record<string, string> = {
  authority_framing: "bg-red-500/15 text-red-400 border-red-500/30",
  delimiter_confusion: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  task_reframing: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  obfuscation: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  placement_salience: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  conditional_trigger: "bg-pink-500/15 text-pink-400 border-pink-500/30",
};

export function TechniquePill({ technique }: TechniquePillProps) {
  const label = TECHNIQUE_LABELS[technique] || technique;
  const colors = PILL_COLORS[technique] || "bg-gray-500/15 text-gray-400 border-gray-500/30";

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium border ${colors}`}
    >
      {label}
    </span>
  );
}
