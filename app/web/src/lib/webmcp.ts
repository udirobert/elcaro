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
  getTools?(): Promise<ModelContextTool[]>;
  executeTool?(tool: ModelContextTool | string, inputJson: string, options?: { signal?: AbortSignal }): Promise<unknown>;
}

/** Testing-only surface exposed by `chrome://flags/#enable-webmcp-testing`. */
export interface TestingModelContextToolInfo {
  name: string;
  title?: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
  annotations?: ToolAnnotations;
}

export interface TestingModelContext {
  getTools(): Promise<TestingModelContextToolInfo[]>;
  executeTool?(
    name: string,
    input: string | Record<string, unknown>,
    options?: { signal?: AbortSignal }
  ): Promise<unknown>;
  ontoolchange?: ((event: Event) => void) | null;
}

export interface WebMcpDebugCall {
  name: string;
  input: Record<string, unknown>;
  output: unknown;
  duration: number;
  ts: number;
  error?: string;
}

export interface WebMcpDebugState {
  live: boolean;
  registered: boolean;
  tools: string[];
  log: WebMcpDebugCall[];
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
    modelContextTesting?: TestingModelContext;
  }
  interface Window {
    __ELCARO_WEBMCP_DEBUG__?: WebMcpDebugState;
  }
}

export {};
