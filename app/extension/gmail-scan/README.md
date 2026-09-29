# Elcaro IPI Guard — Gmail extension

One-click scan of the open Gmail message for **indirect prompt injection**,
routed through Telegraph miners. Season II Track 3 (W3).

Open a message → click the violet **Scan** button in the thread toolbar → get
SAFE / CAUTION / BLOCK with a risk score, the techniques that fired, and a
plain-language instruction on what to do next. No build step, no account, no
wallet.

## Load it

1. Chrome → `chrome://extensions` → enable **Developer mode**.
2. **Load unpacked** → select `app/extension/gmail-scan/`.
3. Open Gmail and open a message. The **Scan** button appears in the thread
   toolbar (a `MutationObserver` re-mounts it as Gmail re-renders; reload the
   tab if it is missing).
4. Click the toolbar icon for the status card, the rail picker, and how-to.

## What the user sees

- **Instant feedback.** The overlay opens the moment you click Scan, with an
  animated progress bar while the miner works. Nothing spins silently.
- **A verdict, not a score.** Each band carries a one-line next action —
  *"Don't act on this message. It contains instructions aimed at an AI agent."*
  A proportional risk meter sits under the header, and flagged techniques
  render as chips rather than a comma-joined string.
- **SAFE gets out of the way** — it dismisses itself after 8s. CAUTION and
  BLOCK stay until dismissed, by button, click-outside, or `Escape`.
- **Failures explain themselves.** Every error is a human headline plus an
  explanation, with the infra code (e.g. `PAYER_NOT_CONFIGURED`) tucked behind
  a **Details** disclosure. Retryable errors get a **Scan again** button.
- **The toolbar badge** carries the result (`!` red, `?` amber, cleared for
  SAFE) so the verdict registers even when the overlay is off-screen.
- **Re-scanning is free.** Verdicts are cached in the service worker for 5
  minutes, so clicking Scan twice on the same message costs one $0.01 ask, not
  two. Cached verdicts say so.

## Rails (`background.js`)

| Rail | Endpoint | Counts for judging | Payment |
|---|---|---|---|
| `engine` (default) | `<bridge>/api/engine-ask` `{query}` → `POST /engine/v1/ask` | **yes** — auto-routed | x402 answered **server-side by the bridge** (EIP-3009 `exact` scheme, Base Sepolia USDC, $0.01/ask) |
| `direct` | `POST /engine/v1/ask/8848` `{method, endpoint, payload}` | no — names miner 8848 | unpaid in the extension; 402 surfaces as *"Direct mode can't pay for scans — switch to Engine"* (dev fallback) |

The bridge (`app/web/src/app/api/engine-ask/route.ts`) is the extension's path
to counted traffic: it forwards the query to the engine and signs the x402
`exact` challenge with the payer key, so the extension itself needs no wallet.
The envelope shape was verified against the live devnode on 29 Sep 2026 — a
well-formed but unfunded signature returns upstream's *"payment required"*,
while malformed headers return *"Invalid payment"*.

`background.js` owns everything the user should never have to think about: a
20s client timeout (under the server's 30s upstream timeout, so the user gets
our copy and a retry rather than a spinner that never resolves), the verdict
cache, badge state, and a single `ERROR_COPY` map from infra error codes to
human sentences. `content.js` renders whatever `ui` object it is handed and
never sees an HTTP status or an env var name.

## Bridge configuration

Netlify env vars for `app/web`. **Testnet key only** — it signs USDC payments.

| Var | Default | Purpose |
|---|---|---|
| `TELEGRAPH_X402_KEY` | — | Payer private key on Base Sepolia; must hold testnet USDC. Unset → `502 PAYER_NOT_CONFIGURED`, and the popup status card reads "Not switched on yet". |
| `TELEGRAPH_BRIDGE_TOKEN` | — | Optional shared secret; when set, requests must carry `x-bridge-token`. |
| `TELEGRAPH_BRIDGE_DAILY_CAP` | `40` | Per-instance daily ask backstop. In-memory, so a guardrail, not a ceiling. |
| `TELEGRAPH_BRIDGE_EXTENSION_IDS` | — | Comma-separated Chrome extension ids allowed to use the bridge. **Set this.** |
| `TELEGRAPH_BRIDGE_ALLOW_ANY_EXTENSION` | `1` | `0` closes the bridge to non-pinned extension ids without naming one. |
| `TELEGRAPH_BRIDGE_ALLOW_NO_ORIGIN` | `0` | `1` re-allows requests with no `Origin` header (server-to-server callers). |

### Origin policy

Every ask spends $0.01, so the bridge gates on origin first, then token, then
cap. Allowed: the production site, `mail.google.com`, and the extension.

Extension origins are `chrome-extension://<id>`, and the id is assigned per
install — so "any `chrome-extension://`" is a standing invitation to anyone who
can install *an* extension. `TELEGRAPH_BRIDGE_EXTENSION_IDS` pins the
published id(s):

```bash
TELEGRAPH_BRIDGE_EXTENSION_IDS=abcdefghijklmnopqrstuvwxyzabcdef
```

Unset means the unpacked-dev convenience (any id) still holds, but
`GET /api/engine-ask` reports `"extensionPinned": false` so the gap is visible
rather than silent. `TELEGRAPH_BRIDGE_ALLOW_ANY_EXTENSION=0` hard-closes it
without naming an id. Requests with no `Origin` are refused unless
`TELEGRAPH_BRIDGE_ALLOW_NO_ORIGIN=1`, which closes the "curl from anywhere
burns the budget" hole.

### `GET /api/engine-ask` — status

Read-only, `no-store`, leaks no secrets (booleans and counters only). The popup
polls it to render the status card, so a user who is about to hit a failure
learns *before* clicking whether the service is live.

```json
{
  "ok": true,
  "payerConfigured": false,
  "tokenRequired": false,
  "extensionPinned": true,
  "dailyCap": 40, "asksUsed": 3, "asksRemaining": 37,
  "costPerAskUsd": 0.01
}
```

### Error codes

Every failure is `{ error, code }` with a stable `code` — the extension renders
copy off the code, so infra strings never reach the overlay.

`FORBIDDEN_ORIGIN` (403) · `FORBIDDEN_TOKEN` (403) · `INVALID_JSON` (400) ·
`BAD_REQUEST` (400) · `QUERY_TOO_LARGE` (413) · `CAP_REACHED` (429) ·
`PAYER_NOT_CONFIGURED` (502) · `PAYMENT_REJECTED` (502, envelope fine but the
payer could not settle — usually an empty testnet wallet) ·
`CHALLENGE_UNREADABLE` (502) · `NO_PAYMENT_OPTION` (502) ·
`UPSTREAM_TIMEOUT` / `UPSTREAM_UNREACHABLE` (504).

## Manifest permissions

```json
"host_permissions": [
  "https://elcaro.trustfall.xyz/*",        // the bridge (engine rail)
  "https://devnode.telegraphprotocol.com/*" // direct rail only
]
```

`api.elcaro.trustfall.xyz` is deliberately **not** granted — the extension
never talks to the miner API directly, only to the bridge and (in dev mode) the
Telegraph node. Least privilege.

## Banding

Exactly as the `/integrate` page prescribes: `risk_score ≥ 0.5` → BLOCK,
`≥ 0.3` → CAUTION, else SAFE. The engine rail's answer is normalized
(`risk_score`/`confidence`, `risk_level`/`label`) so either rail renders.

## Tests

`app/extension/tests/` drives `content.js` in jsdom against a Gmail-shaped
fixture — button mount, extraction, the progress state, each band's copy, the
error path, `Escape`/Dismiss, and a guard that no env var name or protocol
jargon leaks into the overlay.

```bash
cd app/extension/tests && npm install && npm test
```

It has already earned its keep: it caught the message body being read with
`innerText` only, which jsdom (and some other engines) do not implement, so
every scan shipped an empty message.

## Local dev overrides

```js
// point the engine rail at a local bridge
chrome.storage.local.set({ bridge: "http://localhost:3000" });
// use the direct rail
chrome.storage.local.set({ rail: "direct" });
```

With a local bridge, also set `TELEGRAPH_BRIDGE_ALLOW_NO_ORIGIN=1` if you are
testing from a non-browser client — browser fetches always send an `Origin`.

## Roadmap (mirrors docs/telegraph-season-2.md W3)

- [x] Engine rail payment path — bridge answers the x402 exact challenge
      server-side; extension needs no wallet. **Remaining: fund a testnet payer
      wallet and set `TELEGRAPH_X402_KEY` + `TELEGRAPH_BRIDGE_EXTENSION_IDS`
      in Netlify to light the rail up.**
- [x] Pinned extension origin, operator status endpoint, honest error copy
- [x] UX pass: progress state, risk meter, per-band next action, retry, badge,
      verdict cache
- [ ] Gmail extraction hardening — `.ii.gt` / `.a3s` heuristics will need
      iteration; test with plain, quoted, and HTML-heavy mail
- [ ] Compose ≥ 3 miners (IPI + URL/domain reputation + sender signals from the
      live catalog) into the SAFE / CAUTION / BLOCK decision
- [ ] Outlook web + the "agent reads email" checkpoint (same verdict via
      middleware / MCP)
- [ ] Publish (CWS) — then pin `TELEGRAPH_BRIDGE_EXTENSION_IDS` to the
      published id, and track installs / weekly actives / scans. Organic only;
      scripted traffic is explicitly not counted by Telegraph
