# Tangem Build Night: what reaches the signer?

Thu 26 Nov 2026 · Encode Hub London · 20:00 demos. Workshop proposal, not a new product commitment.

**Decision: go as a Gateway field test, not as a wallet build.** The customer is the developer connecting an agent to tools. Tangem gives that developer a visible consequence: an approval appearing on a phone. Elcaro protects what the agent reads; Tangem and the cardholder decide what gets signed. Neither a clean scan nor a signed Elcaro receipt means a swap is safe.

## Attendee path (browser)

[Try the Tangem market note](https://elcaro.trustfall.xyz/scan?example=tangem-market-note). The link fills in the document without sending it. Choose **Scan**, inspect the evidence, then **Load clean note** and **Scan** again. You can also edit the note yourself. This is the app's regular content scan, not a Gateway receipt demonstration or a wallet connection.

## Stage commands

`uv run python -m examples.gateway_wallet_boundary --auto` runs the two-turn rehearsal offline and in-process: a real local Gateway scan plus signed receipt against a captured mock model — no servers, no keys, no wallet. Without `--auto` it pauses for Enter before each turn. The optional phone leg is **separate, not end-to-end**: this command makes no claim about a phone, a card or a wallet connection.

Optional live capability leg (first pairing **off-projector**):

```bash
uv sync --locked --python 3.12 --extra mcp
.venv/bin/python -m examples.gateway_wallet_boundary --tangem-catalog
```

After the clean turn's receipt verifies, the same `after_verdict` gate that held on the flagged turn dispatches `examples/tangem_catalog.py` → pinned `npx -y mcp-remote@0.17.1 https://mcp.tangem.org/mcp`, `initialize` + `tools/list` only — **no `tools/call`, no wallet writes, no QR on stage**. The returned catalog is external metadata, not the synthetic note: it is re-scanned through the same Gateway as a separate `list_capabilities` tool result before the simulated model would see it, and a refusal there is a valid outcome. The terminal shows a measured catalog count and per-leg dispatch deltas — the model stays simulated and executes nothing.

Pairing nuance: Tangem's issuer metadata advertises CIMD but no public registration endpoint, so pairing may need a workshop-provided client registration. If the workshop supplies an authorized client metadata document and fixed callback port, set `TANGEM_CLIENT_METADATA_URL` (plain https, host+path, no query) + `TANGEM_CALLBACK_PORT` (1024–65535); unset → the bridge's default flow. Keep tokens, QR codes and account details off the projector — the bridge's stderr is discarded so auth URLs never reach the transcript.

## The 90-second demo

1. **0–15s — Set the boundary.** The user asked for a summary, not a trade. The synthetic third-party market note is retrieved tool content, not a user instruction.
2. **15–45s — Show the stop.** Press Enter in the [stage example](../examples/gateway_wallet_boundary.py). The note tries to make the agent say PINEAPPLE. Measured on this build: verdict dangerous, risk 0.92, techniques `authority_framing` + `delimiter_confusion`, provider-shaped refusal (`finish_reason=content_filter`), **zero requests to the simulated model**, receipt `/verify` valid. There is no wallet transport in this example; this counter does not measure phone notifications.
3. **45–75s — Show the control.** Fresh turn, same note minus the planted line. Measured: scanned and allowed (`action=none`, `finish_reason=stop`), one upstream request forwarded byte-identical, receipt verified — scanned, not skipped. Only a separate explicit user request can start the optional wallet leg: check the exact proposed swap in the Tangem app and decline by default. A physical tap is an optional close only for an owner-approved, rehearsed demo-wallet transaction. Say exactly what happened: requested, declined, signed or confirmed.
4. **75–90s — Hand it to a developer.** Show the change they can make in their own agent: route the model call through the Gateway and identify retrieved content as untrusted. Show a scan receipt verified by the Gateway's `/verify` if signing is configured. The receipt attests to the scan, not to wallet dispatch or settlement.

## Before spending the evening

- Start with the [Gateway quickstart](../examples/gateway_raw.py), not OAuth. Rehearse both notes under the same policy. The Gateway sits on the model request, not on the Tangem MCP connection. Use the same host path for both turns; inspect its dispatch trace before claiming the phone was protected. On scan errors or ambiguous results stop, never forward by default.
- Spend at most 10 minutes on the optional handoff. Workshop lead: `https://mcp.tangem.org/mcp` (public portal: https://mcp.tangem.com/). **Authenticated pairing is not yet confirmed** — confirm pairing and request capabilities via the official workshop host and its authenticated `tools/list`; do not assume tool names, notification behavior or a supported swap. Keep tokens, QR codes and account details off the projector. No general-purpose write tool for audience input.
- If the handoff isn't observable or pairing fails, end at the Gateway verdict and verified receipt if available. A clearly labeled recording can illustrate Tangem separately. If offline, run `examples.gateway_wallet_boundary` — an offline in-process Gateway is available, so the rehearsal still produces a real scan and a verifiable receipt with the model simulated; label it **scanner + receipt only** and do not claim phone interception or live Tangem integration on that basis.

## What we keep

The deliverable is a reusable clean/flagged tool-result example and a short integration note for the [Gateway adoption path](roadmap-gateway.md), not a Tangem service. Ask one attendee to reproduce a first scanned call using the [under-five-minute launch goal](openserv-dolphin-launch.md); record where they get stuck. Ask Tangem which request details the human actually sees and whether their host exposes a pre-model tool-result boundary. Report observations separately from feature requests.

The [PayBox Gauntlet](paybox-ch1.md) already demonstrates why a plausible payment can originate in untrusted content. Do not build another portfolio assistant, approval UI, signer, transaction simulator, address-history scorer or intent validator for this event. Cut the swap before the clean control. If success requires a new wallet product or displaces the Gateway quickstart, skip the integration.
