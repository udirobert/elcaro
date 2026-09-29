# Elcaro IPI Guard — Gmail extension (skeleton)

One-click scan of the open Gmail message for **indirect prompt injection**,
routed through Telegraph miners. Season II Track 3 (W3) skeleton: the full
checkpoint composes ≥ 3 signals from different Telegraph miners into
SAFE / CAUTION / BLOCK — this skeleton ships the IPI verdict first.

## Load it (no build step)

1. Chrome → `chrome://extensions` → enable **Developer mode**.
2. **Load unpacked** → select this directory (`app/extension/gmail-scan/`).
3. Open Gmail, open a message → violet **Scan** button appears in the thread
   toolbar (MutationObserver mounts it; reload the tab if it's missing).
4. Verdict renders as a fixed overlay: band + risk score + summary.

## Rails (`background.js`)

| Rail | Endpoint | Counts for judging | Payment |
|---|---|---|---|
| `engine` (default) | `POST /engine/v1/ask` `{query}` | **yes** — auto-routed | x402; first call returns **402 + PAYMENT-REQUIRED challenge** |
| `direct` | `POST /engine/v1/ask/8848` `{method, endpoint, payload}` | no — names the miner | x402, same 402 handshake |

The rail preference is set in the popup and persisted in
`chrome.storage.local`. **Neither rail works end-to-end yet**: an x402 wallet
client must answer the 402 challenge. Wire
[Telegraph-examples](https://github.com/telegraphprotocol/Telegraph-examples)
(`x402:engine-ask`) into `background.js` — that is the single blocking step
before real counted traffic flows. The 402 path is already surfaced in the
overlay so the handshake state is visible.

## Banding

Exactly as the `/integrate` page prescribes: `risk_score ≥ 0.5` → BLOCK,
`≥ 0.3` → CAUTION, else SAFE. The engine rail's answer is normalized
(`risk_score`/`confidence`, `risk_level`/`label`) so either rail renders.

## Roadmap (mirrors docs/telegraph-season-2.md W3)

- [ ] x402 wallet client answering the 402 challenge (engine rail, counted)
- [ ] Gmail extraction hardening — `.ii.gt` / `.a3s` heuristics will need
      iteration; test with plain, quoted, and HTML-heavy mail
- [ ] Compose ≥ 3 miners (IPI + URL/domain reputation + sender signals from the
      live catalog) into the Truvian-style SAFE / CAUTION / BLOCK decision
- [ ] Outlook web + the "agent reads email" checkpoint (same verdict via
      middleware / MCP)
- [ ] Publish (CWS), track installs / weekly actives / scans — organic only;
      scripted traffic is explicitly not counted by Telegraph
