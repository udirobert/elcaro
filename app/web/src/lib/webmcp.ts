/**
 * Minimal WebMCP types (W3C WebML CG draft).
 * https://webmachinelearning.github.io/webmcp/
 */

export interface ToolAnnotations {
  readOnlyHint?: boolean;
  untrustedContentHint?: boolean;
}

export interface ModelContextTool {
  name: string;
  title?: string;
  description: string;
  inputSchema?: Record<string, unknown>;
  execute: (
    input: Record<string, unknown>,
    options?: { signal?: AbortSignal }
  ) => Promise<unknown>;
  annotations?: ToolAnnotations;
}

export interface ModelContext {
  registerTool(
    tool: ModelContextTool,
    options?: { signal?: AbortSignal; exposedTo?: string[] }
  ): Promise<void>;
}

export function getModelContext(): ModelContext | null {
  if (typeof document === "undefined") return null;
  const ctx = document.modelContext ?? navigator.modelContext;
  if (ctx && typeof ctx.registerTool === "function") return ctx;
  return null;
}

/** Agents receive a JSON string (spec completion result is string-or-null). */
export function toolResult(payload: unknown): string {
  return JSON.stringify(payload, null, 2);
}

declare global {
  interface Document {
    modelContext?: ModelContext;
  }
  interface Navigator {
    modelContext?: ModelContext;
  }
}

export {};
