export type ContentType =
  | "email"
  | "search_result"
  | "webpage"
  | "document"
  | "code"
  | "chat_message";

export type RiskLevel = "safe" | "low" | "suspicious" | "dangerous";

export type Severity = "info" | "low" | "medium" | "high" | "critical";

export type TechniqueClass =
  | "authority_framing"
  | "delimiter_confusion"
  | "task_reframing"
  | "obfuscation"
  | "placement_salience"
  | "conditional_trigger";

export interface TTPReference {
  framework: string;
  technique_id: string;
  technique_name: string;
  tactic: string;
}

export interface EvidenceContext {
  matched_text: string;
  context_before: string;
  context_after: string;
  char_offset: number;
}

export interface DetectionIndicator {
  technique_class: TechniqueClass;
  technique_name: string;
  severity: Severity;
  confidence: number;
  evidence: EvidenceContext;
  location: string;
  explanation: string;
  remediation: string;
  ttps: TTPReference[];
}

export interface ScanResponse {
  risk_score: number;
  risk_level: RiskLevel;
  flagged_techniques: TechniqueClass[];
  indicators: DetectionIndicator[];
  summary: string;
  content_type: ContentType;
  deep_analysis_used: boolean;
  latency_ms: number;
  // Populated by the engine (core/quarantine.py). Optional because responses
  // from older miners and stale localStorage history predate these fields.
  safe_content?: string;
  quarantined?: boolean;
  // Relay contract (what the agent should quote to its user) and verdict
  // signing (present when the miner has ELCARO_SIGNING_KEY configured).
  human_summary?: string;
  scanned_at?: number;
  signature?: string;
  key_id?: string;
}

export interface ScanRequest {
  content: string;
  content_type: ContentType;
  deep_analysis?: boolean;
}

export interface ScanError {
  error: string;
  detail?: string;
}
