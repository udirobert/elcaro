import Anthropic from "@anthropic-ai/sdk";
import type { ClientOptions } from "@anthropic-ai/sdk";

import {
  ELCARO_GATEWAY_URL,
  type ElcaroClientOptions,
  elcaroHeaders,
} from "./index.js";

export interface ElcaroAnthropicOptions
  extends ElcaroClientOptions,
    Omit<ClientOptions, "apiKey" | "baseURL" | "defaultHeaders"> {}

/**
 * Drop-in `Anthropic` client pointed at the Elcaro Gateway.
 *
 *   new ElcaroAnthropic({ elcaroKey: "elk_…", upstreamKey: "sk-ant-…" })
 *
 * `apiKey` stays the upstream key (it rides the Anthropic-native
 * `x-api-key` header, which the gateway accepts); the Elcaro key goes
 * in `x-elcaro-key`.
 */
export class ElcaroAnthropic extends Anthropic {
  constructor(opts: ElcaroAnthropicOptions = {}) {
    const { elcaroKey, upstreamKey, baseURL, headers, ...rest } = opts;
    super({
      apiKey: upstreamKey ?? "unused-upstream-key",
      baseURL: baseURL ?? ELCARO_GATEWAY_URL,
      defaultHeaders: elcaroHeaders({ elcaroKey, upstreamKey, headers }),
      ...rest,
    });
  }
}
