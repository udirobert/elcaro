export type ContentType =
  | "email"
  | "search_result"
  | "webpage"
  | "document"
  | "code"
  | "chat_message"
  | "system_prompt";

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
  // Evasion normalizations applied before detection (core/normalize.py).
  // Optional — responses from older miners predate the field.
  normalizations_applied?: string[];
  // SERV Reasoning observability — populated when the miner has been
  // configured with SERV_API_KEY + SERV_ENABLED=1. Optional for the same
  // backward-compatibility reasons as the fields above.
  serv_available?: boolean;
  serv_attempted?: boolean;
  serv_used?: boolean;
  // The raw SERV LLM score before blending with the rule score. Present
  // when serv_used=true. Used by the UI to show the delta:
  // "SERV saw X, rules saw Y, final is Z" — the upsell signal.
  serv_rule_score_before?: number;
  // Approximate SERV cost for this scan when serv_used=true. All values in
  // USDC (USD-pegged). None when SERV was not used or cost could not be
  // estimated. Keys: input_tokens, output_tokens, input_cost_usdc,
  // output_cost_usdc, total_usdc.
  serv_cost?: { input_tokens?: number; output_tokens?: number; input_cost_usdc?: number; output_cost_usdc?: number; total_usdc?: number } | null;
}

export interface ScanRequest {
  content: string;
  content_type: ContentType;
  deep_analysis?: boolean;
  // Progressive-enhancement toggle: when true, ask the miner to consult SERV
  // Reasoning for borderline / deep-analysis cases. Default off — the free
  // fast path is unaffected when SERV is not configured.
  serv_enabled?: boolean;
}

export interface ScanError {
  error: string;
  detail?: string;
}

// ── Vulnerability analyzer ────────────────────────────────────────────────────
export interface VulnerabilityClassScore {
  letter: string;
  name: string;
  score: number; // 0 = hardened, 100 = gullible
  findings: string[];
}

export interface VulnerabilityResult {
  gullibility_score: number;
  classes: VulnerabilityClassScore[];
  protective_patterns_found: string[];
  missing_patterns: string[];
  recommendations: string[];
  prompt_length: number;
}

export interface SimulatedSpecimen {
  id: string;
  letter: string;
  label: string;
  note: string;
  content: string;
  content_type: string;
  is_injection: boolean;
  hijacked: boolean;
  simulated_response: string;
  evaluator_note: string;
  confidence: number;
}

export interface SandboxResult {
  gullibility_score: number;
  specimens: SimulatedSpecimen[];
  injections_caught: number;
  false_positives: number;
  simulation_mode: string;
  // Whether SERV is configured and LLM simulation was used.
  serv_available: boolean;
  total_input_tokens: number;
  total_output_tokens: number;
  estimated_cost_usdc: number;
  pattern_analysis_gullibility: number | null;
  recommendations: string[];
}
