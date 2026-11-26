# Tangem Build Night: what reaches the signer?

Thu 26 Nov 2026 · Encode Hub London · 20:00 demos. Workshop proposal, not a new product commitment.

**Decision: go as a Gateway field test, not as a wallet build.** The customer is the developer connecting an agent to tools. Tangem gives that developer a visible consequence: an approval appearing on a phone. Elcaro protects what the agent reads; Tangem and the cardholder decide what gets signed. Neither a clean scan nor a signed Elcaro receipt means a swap is safe.

## Attendee path (browser)

Three preset cases deep-link straight into the scanner — each fills the document without sending it. Choose **Scan**, inspect the evidence, then load the clean variant and **Scan** again. This is the app's regular content scan, not a Gateway receipt demonstration or a wallet connection. The supplier-invoice and tool-description URLs only work once this build is deployed to the public site; locally they work now at `localhost:3000`.

- [Market note](https://elcaro.trustfall.xyz/scan?example=tangem-market-note) — a third-party report with a planted instruction (harmless PINEAPPLE tell); matches the terminal rehearsal.
- [Supplier invoice](https://elcaro.trustfall.xyz/scan?example=tangem-supplier-invoice) — an emailed invoice that could make an unpaid bill look paid.
- [Tool description](https://elcaro.trustfall.xyz/scan?example=tangem-tool-description) — a synthetic `tools/list` descriptor whose wording could sound like a confirmation.

References: [Tangem MCP portal](https://mcp.tangem.com/), [MCP tool schema](https://modelcontextprotocol.io/specification/2025-06-18/server/tools). Material inspiration only (not source data): [Retro Loops](https://github.com/rauchg/retro-loops) (grainy dithered fields, via Codrops) and [Glass Material](https://tympanus.net/codrops/hub/tag/glass/) (frosted-glass preview, Codrops Creative Hub).

## Stage beats

1. **Terminal, offline:** `.venv/bin/python -m examples.gateway_wallet_boundary --auto` — a real local Gateway scans the marked note, blocks it, then passes the clean note to a simulated model. Both receipts verify. No servers, no keys, no wallet.
2. **Browser:** the attendee links above — for a mixed audience, open on **Supplier invoice** (the relatable stakes: "Would you mark this $480 bill paid?"), then switch to **Tool description** with the case buttons at the top; the market note stays as the terminal-paired case. Guided walkthrough per case: scan the marked version, load the clean variant, scan again — switching cases clears the stale verdict.
3. **Optional (off-projector only):** paired terminal + Tangem tool discovery, below.

## Presenter cues

1. **Spoken opener (10s):** lead with the loaded case's headline — for the invoice, "Would you mark this $480 bill paid?" Signing stays with the cardholder; the card still-life in the endpoint strip is a diagram, not a real approval.
2. **Optional discovery beat:** "Discover Tangem MCP" makes one credential-free browser GET of Tangem's *public protected-resource* metadata (resource name + auth server) — **not tools/list, not pairing, nothing signed**. If wifi fails: "Unavailable · wallet not connected," move on — the Inspect button always works.
3. **Story → evidence:** the Inspect button ("Inspect the invoice/descriptor/market note") reveals the real scan surface — nothing was sent yet. Then prediction ("Did the user ask for this, or did the source?") and Scan for the first real verdict.
4. **The one-line change:** after the quarantine, "Now watch — only the last line changes," then Load the clean variant and Scan for the second real verdict. The case buttons above switch scenarios without losing the frame — picking a new case never scans on its own.
5. **Close:** "The words were in the document. The authority wasn't."
6. **Keep the counter honest, out loud:** "0 requests this turn" counts the *model* call. No phone, no card, no notification was involved anywhere in this demo. Say that before anyone asks — the room will otherwise assume the cardholder was protected, which is the one claim this build cannot make. The catalog leg is optional, off-projector, and still unverified.

## Paired option — Tangem tool discovery (off-projector)

*Boundary: the browser page's "Discover Tangem MCP" fetches only public protected-resource metadata — it never calls `tools/list`. The authenticated catalog here and cardholder signing are separate things: scanner, catalog, signing — three separate steps.*

```bash
uv sync --locked --python 3.12 --extra mcp
.venv/bin/python -m examples.gateway_wallet_boundary --tangem-catalog
```

Run interactively (drop `--auto`): the terminal pauses before asking Tangem `tools/list` — capability **discovery**, not wallet access. `initialize` + `tools/list` only; **no `tools/call`, no wallet writes, no QR on stage**. After the clean turn's receipt verifies, the same `after_verdict` gate that held on the flagged note dispatches `examples/tangem_catalog.py` via the pinned bridge; the returned catalog is re-scanned through the same Gateway before the simulated model would see it — a refusal is a valid outcome. The terminal shows a measured catalog count and per-leg dispatch deltas; the model stays simulated and executes nothing.

**Status: the first authenticated pairing attempt failed — the catalog is not yet verified.** Tangem's issuer metadata advertises CIMD but no public registration endpoint; pairing may need a workshop-provided client registration and we do not promise the OAuth flow is repaired. If the workshop supplies an authorized client metadata document and fixed callback port, set `TANGEM_CLIENT_METADATA_URL` (plain https, host+path, no query) + `TANGEM_CALLBACK_PORT` (1024–65535); unset → the bridge's default flow. Keep tokens, QR codes and account details off the projector — the bridge's stderr is discarded so auth URLs never reach the transcript. If pairing fails on stage, the offline command above is the whole demo.

## The 90-second demo

1. **0–15s — Set the boundary.** The user asked for a summary, not a trade. The synthetic third-party market note is retrieved tool content, not a user instruction.
2. **15–45s — Show the stop.** Press Enter in the [stage example](../examples/gateway_wallet_boundary.py). The note tries to make the agent say PINEAPPLE. Measured on this build: verdict dangerous, risk 0.92, techniques `authority_framing` + `delimiter_confusion`, provider-shaped refusal (`finish_reason=content_filter`), **zero requests to the simulated model**, receipt `/verify` valid. There is no wallet transport in this example; this counter does not measure phone notifications.
3. **45–75s — Show the control.** Fresh turn, same note minus the planted line. Measured: scanned and allowed (`action=none`, `finish_reason=stop`), one upstream request forwarded byte-identical, receipt verified — scanned, not skipped. Then the optional discovery leg: the terminal asks Tangem `tools/list` — which tools exist, not wallet access — and scans the descriptions. If that leg isn't verified, stop at the two receipts.
4. **75–90s — Hand it to a developer.** Show the change they can make in their own agent: route the model call through the Gateway and identify retrieved content as untrusted. Show a scan receipt verified by the Gateway's `/verify` if signing is configured. The receipt attests to the scan, not to wallet dispatch or settlement.

## Before spending the evening

- Start with the [Gateway quickstart](../examples/gateway_raw.py), not OAuth. Rehearse both notes under the same policy. The Gateway sits on the model request, not on the Tangem MCP connection. Use the same host path for both turns; inspect its dispatch trace before claiming the phone was protected. On scan errors or ambiguous results stop, never forward by default.
- Spend at most 10 minutes on the optional handoff. Workshop lead: `https://mcp.tangem.org/mcp` (public portal: https://mcp.tangem.com/). **Authenticated pairing is not yet confirmed** — confirm pairing and request capabilities via the official workshop host and its authenticated `tools/list`; do not assume tool names, notification behavior or a supported swap. Keep tokens, QR codes and account details off the projector. No general-purpose write tool for audience input.
- If the handoff isn't observable or pairing fails, end at the Gateway verdict and verified receipt if available. A clearly labeled recording can illustrate Tangem separately. If offline, run `examples.gateway_wallet_boundary` — an offline in-process Gateway is available, so the rehearsal still produces a real scan and a verifiable receipt with the model simulated; label it **scanner + receipt only** and do not claim phone interception or live Tangem integration on that basis.

## What we keep

The deliverable is a reusable clean/flagged tool-result example and a short integration note for the [Gateway adoption path](roadmap-gateway.md), not a Tangem service. Ask one attendee to reproduce a first scanned call using the [under-five-minute launch goal](openserv-dolphin-launch.md); record where they get stuck. Ask Tangem which request details the human actually sees and whether their host exposes a pre-model tool-result boundary. Report observations separately from feature requests.

The [PayBox Gauntlet](paybox-ch1.md) already demonstrates why a plausible payment can originate in untrusted content. Do not build another portfolio assistant, approval UI, signer, transaction simulator, address-history scorer or intent validator for this event. Cut the swap before the clean control. If success requires a new wallet product or displaces the Gateway quickstart, skip the integration.

## First authorized tool: operator handoff (off-projector)

Goal: after the catalog leg verifies, review which tools the *server itself*
declares read-only before anyone considers a first call. An annotation is a
hint, not authorization — the operator picks a single tool only after reading
its real `tools/list` schema with the organizers. **No `tools/call` until the
name, argument schema, effect and output display rules are confirmed.**

1. **Preflight (before launching):** confirm the workshop client metadata
   document is live and correct —

   ```bash
   url=https://elcaro.trustfall.xyz/.well-known/tangem-workshop-client.json
   callback=http://localhost:3334/oauth/callback
   curl -fsS "$url" | .venv/bin/python -c \
     'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("client_id")==sys.argv[1] and d.get("redirect_uris")==[sys.argv[2]] else "Client metadata mismatch; stop before pairing.")' \
     "$url" "$callback"
   ```

   It must return JSON with the exact `client_id` and `redirect_uris` you will
   register — check both fields before continuing. **As of this runbook the
   URL returns 404**; if it still does, stop and ask the organizers rather
   than guessing at another identity. Do not launch the flow without it.

2. **Authorized review:** with the workshop-supplied metadata URL and fixed
   callback port:

   ```bash
   TANGEM_CLIENT_METADATA_URL=https://elcaro.trustfall.xyz/.well-known/tangem-workshop-client.json \
   TANGEM_CALLBACK_PORT=3334 \
   .venv/bin/python -m examples.gateway_wallet_boundary \
     --tangem-catalog --review-catalog --auto
   ```

   Pairing happens in the operator's own browser/phone on the **demo wallet
   only** — no screen sharing, no secrets on the projector (bridge stderr is
   discarded). After the clean catalog scan verifies, the terminal prints
   *server-declared read-only candidate names* — names only, never
   descriptions, wallet values or raw errors. If it prints none, stop and ask
   the organizers; do not pick a tool by name alone.

3. **The first call itself is deferred** until the returned tool name,
   argument schema, effect and output display rules are verified with the
   organizers. The demo wallet holds no funds to risk; still treat it as real.
   For the recorded comparison, replay the marked catalog **locally** — no
   second live call, no wallet data scanned on stage.

## Product decisions

- **Scan stays honest:** every browser verdict comes from a real local scan
  of synthetic specimens — never canned scores, never wallet data.
- **Integrate is the developer path:** the docs page links the specimen to
  the agent-side check; it does not create sessions or call tools.
- **The authenticated connector stays local to the operator.** Credentials,
  pairing and tokens never enter the browser app or the demo transcript.
- **First future approved call** happens only after verifying the returned
  tool name, argument schema, effect and output display rules; scan the
  descriptor, then scan the result. Replays are labeled local — no second
  live call.
