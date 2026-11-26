import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";

import {
  ELCARO_GATEWAY_URL,
  ELCARO_OPENAI_BASE_URL,
  type ElcaroClientOptions,
  elcaroHeaders,
  resolveElcaroKey,
} from "./index.js";

/**
 * Vercel AI SDK providers backed by the Elcaro Gateway — same drop-in
 * pattern as the official factories:
 *
 *   const elcaro = createElcaroOpenAI({ elcaroKey, upstreamKey });
 *   generateText({ model: elcaro("gpt-5"), … });
 */
export function createElcaroOpenAI(opts: ElcaroClientOptions = {}) {
  const { elcaroKey, upstreamKey, baseURL, headers } = opts;
  return createOpenAI({
    apiKey: resolveElcaroKey(elcaroKey),
    baseURL: baseURL ?? ELCARO_OPENAI_BASE_URL,
    headers: elcaroHeaders({ elcaroKey, upstreamKey, headers }),
  });
}

export function createElcaroAnthropic(opts: ElcaroClientOptions = {}) {
  const { elcaroKey, upstreamKey, baseURL, headers } = opts;
  return createAnthropic({
    apiKey: upstreamKey ?? resolveElcaroKey(elcaroKey),
    baseURL: `${baseURL ?? ELCARO_GATEWAY_URL}/v1`,
    headers: elcaroHeaders({ elcaroKey, upstreamKey, headers }),
  });
}
