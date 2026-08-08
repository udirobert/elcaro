export type ContentType =
  | "email"
  | "search_result"
  | "webpage"
  | "document"
  | "code"
  | "chat_message";

export type RiskLevel = "safe" | "low" | "suspicious" | "dangerous";

export type TechniqueClass =
  | "authority_framing"
  | "delimiter_confusion"
  | "task_reframing"
  | "obfuscation"
  | "placement_salience"
  | "conditional_trigger";

export interface DetectionIndicator {
  technique_class: TechniqueClass;
  technique_name: string;
  confidence: number;
  matched_text: string;
  location: string;
  explanation: string;
}

export interface ScanResponse {
  risk_score: number;
  risk_level: RiskLevel;
  flagged_techniques: TechniqueClass[];
  indicators: DetectionIndicator[];
  content_type: ContentType;
  deep_analysis_used: boolean;
  latency_ms: number;
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
