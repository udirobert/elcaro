# WebMCP on Elcaro — scan gate

Elcaro’s thesis is that **humans and agents share one verdict**. WebMCP is
how that happens in a browser: the agent does not scrape `/scan`; it calls
tools that fill the same form, run the same `/api/scan` path, and paint the
same risk meter the human is looking at.

This is not a port of `app/mcp_server.py` into the page. Stdio MCP is for
IDEs. WebMCP is for the **site as a co-working surface**.

## Why this use case

Prompt-level “ignore retrieved instructions” fails when the instruction is
*in the document the agent already trusts*. A human watching ChatGPT’s
in-app browser cannot see what the model ingested. A silent `POST /scan`
sidecar does not help them either.

With WebMCP:

1. The agent retrieves untrusted content (email, search snippet, page).
2. It calls `scan_content` **on this origin** before it summarizes or acts.
3. The playground updates: textarea, scan beam, score, matched span.
4. The agent receives structured JSON (`risk_score`, `quarantined`,
   `safe_content`, `human_summary`) and follows the same doctrine as
   `/integrate` (block at ≥ 0.5, review from 0.3, never pass 0.7+).

That pairing — machine-readable verdict + human-visible evidence — is the
thing that was awkward before: either the human pasted into Elcaro and the
agent never saw the result, or the agent called an API and the human saw
nothing.

## Tools (registered on `/scan`)

| Tool | Mutates UI | Purpose |
|---|---|---|
| `scan_content` | yes | Scan retrieved content; fill the form; show the verdict |
| `load_specimen` | yes | Load a labeled playground example into the textarea |
| `list_specimens` | no | Catalog of specimen ids the agent can load |
| `explain_verdict` | no | Doctrine for the **last** on-page verdict (same numbers as MCP) |

Implementation: [`app/web/src/lib/webmcp-register.ts`](../app/web/src/lib/webmcp-register.ts)
(`document.modelContext.registerTool`). Hook:
[`app/web/src/lib/use-webmcp-scan.ts`](../app/web/src/lib/use-webmcp-scan.ts).

`scan_content` is annotated `untrustedContentHint: true` because the return
echoes matched spans from retrieved content. `list_specimens` and
`explain_verdict` are `readOnlyHint: true`.

Feature detect `document.modelContext` (fallback `navigator.modelContext`).
Unregister on unmount via `AbortSignal`. No-op in browsers without WebMCP.

## What we will not do

- Do not wrap `/scan` in a tool that skips the React form. Judges score
  **WebMCP leverage**; a hidden `fetch` is MCP-over-HTTPS.
- Do not invent a second product. Gauntlet stays a human demo; agents use
  specimens on `/scan`.
- Do not farm Telegraph engine volume from these tools. WebMCP hits the
  same Next.js `/api/scan` proxy the textarea uses.

## Challenge logistics

See [hackathons.md](hackathons.md) (WebMCP Challenge). Deadline
**3 Sep 2026 21:00 GMT+1**. Required besides this code: visible `LICENSE`,
live URL, &lt;3 min YouTube with audio in ChatGPT’s in-app browser.

## Test locally

1. `cd app/web && npm run dev`
2. Chrome: `chrome://flags/#enable-webmcp-testing` → enable → open
   `http://localhost:3000/scan`
3. The page should show “Agent connected” when `modelContext` exists.
4. ChatGPT in-app browser: open `https://elcaro.trustfall.xyz/scan` and ask
   the agent to load specimen `authority` then scan it.
