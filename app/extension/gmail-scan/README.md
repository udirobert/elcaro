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
| `engine` (default) | `<bridge>/api/engine-ask` `{query}` → `POST /engine/v1/ask` | **yes** — auto-routed | x402 answered **server-side by the bridge** (EIP-3009 exact scheme, Base Sepolia USDC, $0.01/ask) |
| `direct` | `POST /engine/v1/ask/8848` `{method, endpoint, payload}` | no — names the miner | unpaid in the extension; 402 surfaces in the overlay (dev fallback) |

The bridge (`app/web/src/app/api/engine-ask/route.ts`) is the extension's
path to counted traffic: it forwards the query to the engine and signs the
x402 `exact` challenge with the payer key, so the extension itself needs no
wallet. Envelope shape verified against the live devnode on 29 Sep 2026 — a
well-formed but unfunded signature returns upstream's "payment required",
while malformed headers return "Invalid payment".

Bridge configuration (Netlify env vars, **testnet key only** — it signs
USDC payments):

| Var | Purpose |
|---|---|
| `TELEGRAPH_X402_KEY` | Payer private key on Base Sepolia; must hold testnet USDC. Unset → bridge returns 502 `PAYER_NOT_CONFIGURED`. |
| `TELEGRAPH_BRIDGE_TOKEN` | Optional shared secret; when set, requests must carry `x-bridge-token`. |
| `TELEGRAPH_BRIDGE_DAILY_CAP` | Per-instance daily ask backstop (default 40). In-memory, so treat as a guardrail, not a ceiling. |

Origin allowlist inside the route: the production site, `mail.google.com`,
and `chrome-extension://` (any extension id — tighten if the published one
is the only consumer). The rail preference is set in the popup and persisted
in `chrome.storage.local`; `chrome.storage.local.set({bridge})` overrides the
bridge base URL for local development.

## Banding

Exactly as the `/integrate` page prescribes: `risk_score ≥ 0.5` → BLOCK,
`≥ 0.3` → CAUTION, else SAFE. The engine rail's answer is normalized
(`risk_score`/`confidence`, `risk_level`/`label`) so either rail renders.

## Roadmap (mirrors docs/telegraph-season-2.md W3)

- [x] Engine rail payment path — bridge answers the x402 exact challenge
      server-side; extension needs no wallet. Remaining: fund a testnet payer
      wallet and set `TELEGRAPH_X402_KEY` in Netlify to light the rail up.
- [ ] Gmail extraction hardening — `.ii.gt` / `.a3s` heuristics will need
      iteration; test with plain, quoted, and HTML-heavy mail
- [ ] Compose ≥ 3 miners (IPI + URL/domain reputation + sender signals from the
      live catalog) into the Truvian-style SAFE / CAUTION / BLOCK decision
- [ ] Outlook web + the "agent reads email" checkpoint (same verdict via
      middleware / MCP)
- [ ] Publish (CWS), track installs / weekly actives / scans — organic only;
      scripted traffic is explicitly not counted by Telegraph
