import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import * as z from "zod/v4";
import { x402OutputSchema, proposeX402 } from "./paybox.js";

const PROTOCOL_VERSION = "2026-07-28";
const FREE_SCAN_URL = "https://api.elcaro.trustfall.xyz/scan";
const PAID_SCAN_URL = "https://elcaro.trustfall.xyz/api/x402/scan";
const MAX_CONTENT = 48_000;

const contentType = z
  .enum(["email", "web_page", "document", "message", "code", "search_result", "other"])
  .describe("What kind of retrieved content is being scanned.");

const scanArgs = z
  .object({
    content: z.string().min(1).max(MAX_CONTENT).describe("Untrusted content an agent retrieved and is about to act on."),
    content_type: contentType,
  })
  .strict();

const verdictSchema = z
  .object({
    risk_score: z.number(),
    risk_level: z.string(),
    quarantined: z.boolean(),
    flagged_techniques: z.array(z.string()),
    summary: z.string(),
    human_summary: z.string(),
  })
  .strict();

function createServer() {
  const server = new McpServer(
    { name: "elcaro", version: "1.0.0" },
    { supportedProtocolVersions: [PROTOCOL_VERSION] },
  );

  server.registerTool(
    "elcaro_scan",
    {
      title: "Paid injection scan (x402)",
      description:
        "Scan untrusted retrieved content for indirect prompt injection before an agent acts on it — emails, search results, documents, web pages, tool outputs. Proposes a $0.01 USDC x402 payment on Base to Elcaro's paid scan lane; the signed verdict is returned through the PayBox request. Use before payments, sends, sign-ins, or any action the content could be steering.",
      inputSchema: scanArgs,
      outputSchema: x402OutputSchema,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    async ({ content, content_type }) =>
      proposeX402({
        chain: "eip155:8453",
        url: PAID_SCAN_URL,
        method: "POST",
        body: { content, content_type },
        maxAmount: "10000",
      }),
  );

  server.registerTool(
    "elcaro_quick_scan",
    {
      title: "Instant injection scan (free)",
      description:
        "Free triage scan of untrusted content for indirect prompt injection. Returns a risk score, verdict, quarantine flag and flagged techniques. Use elcaro_scan for the signed, paid verdict when money is about to move.",
      inputSchema: scanArgs,
      outputSchema: verdictSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async ({ content, content_type }) => {
      const res = await fetch(FREE_SCAN_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, content_type }),
        signal: AbortSignal.timeout(4000),
      });
      if (!res.ok) throw new Error(`Elcaro scan failed: HTTP ${res.status}`);
      const body = await res.json();
      const verdict = verdictSchema.parse({
        risk_score: body.risk_score ?? 0,
        risk_level: body.risk_level ?? "unknown",
        quarantined: body.quarantined ?? false,
        flagged_techniques: Array.isArray(body.flagged_techniques) ? body.flagged_techniques.slice(0, 20).map(String) : [],
        summary: String(body.summary ?? ""),
        human_summary: String(body.human_summary ?? body.summary ?? ""),
      });
      return {
        content: [{ type: "text" as const, text: verdict.human_summary }],
        structuredContent: verdict,
      };
    },
  );

  return server;
}

serveStdio(createServer, { legacy: "reject" });
