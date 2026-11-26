import OpenAI from "openai";
import type { ClientOptions } from "openai";

import {
  ELCARO_OPENAI_BASE_URL,
  type ElcaroClientOptions,
  elcaroHeaders,
  resolveElcaroKey,
} from "./index.js";

export interface ElcaroOpenAIOptions extends ElcaroClientOptions, Omit<ClientOptions, "apiKey" | "baseURL" | "defaultHeaders"> {}

/**
 * Drop-in `OpenAI` client pointed at the Elcaro Gateway.
 *
 *   new ElcaroOpenAI({ elcaroKey: "elk_…", upstreamKey: "sk-…" })
 *
 * `Authorization: Bearer <elcaroKey>` doubles as the Elcaro key (the
 * gateway accepts it in place of x-elcaro-key); the real provider key
 * travels untouched in `x-upstream-key`.
 */
export class ElcaroOpenAI extends OpenAI {
  constructor(opts: ElcaroOpenAIOptions = {}) {
    const { elcaroKey, upstreamKey, baseURL, headers, ...rest } = opts;
    super({
      apiKey: resolveElcaroKey(elcaroKey),
      baseURL: baseURL ?? ELCARO_OPENAI_BASE_URL,
      defaultHeaders: elcaroHeaders({ elcaroKey, upstreamKey, headers }),
      ...rest,
    });
  }
}
