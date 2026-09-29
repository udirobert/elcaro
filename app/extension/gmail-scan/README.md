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
- **The toolbar badge** carries the result (`!` red, `?` amber) for six
  seconds, then settles into the day's running count of BLOCKed messages —
  the number someone actually wants to glance at. Zero blocks, no badge.
- **Re-scanning is free.** Verdicts are cached in the service worker for 5
  minutes, so clicking Scan twice on the same message costs one $0.01 ask, not
  two. Cached verdicts say so.
- **Scan without the mouse.** `⌘⇧S` (macOS) / `Alt+S` — rebindable at
  <kbd>chrome://extensions/shortcuts</kbd>. The shortcut lands in the same
  content-script path as a click, so it costs the same and hits the same cache.
- **Today, at a glance.** The popup opens on a proportional bar of the day's
  scans — clear / caution / blocked — with a "Clear history" button.
  History lives in `chrome.storage.local` and never leaves the machine, the
  same stance as the site's `/supervise` page. It is erasable on purpose.
- **Who answered.** When the rail names the miner that handled the ask, the
  overlay credits it (*"engine rail · counted · miner 9002"*).
- **One tip, once.** The first scan mentions the keyboard shortcut; after
  that the overlay never nags.

### What it deliberately does not do

It never trims quoted replies or signatures out of the message before
scanning. It would cut noise and false positives, and it would also be a
bypass: an attacker who wants their instructions ignored just writes
`-----Original Message-----` above them. Everything visible in the thread
goes to the miner.

## Rails (`background.js`)

| Rail | Endpoint | Counts for judging | Payment |
|---|---|---|---|
| `engine` (default) | `<bridge>/api/engine-ask` `{query}` → `POST /engine/v1/ask` | **yes** — auto-routed | x402 answered **server-side by the bridge** (EIP-3009 `exact` scheme, Base Sepolia USDC, $0.01/ask) |
| `direct` | `POST /engine/v1/ask/8848` `{method, endpoint, payload}` | no — names miner 8848 | unpaid in the extension; 402 surfaces as *"Direct mode can't pay for scans — switch to Engine"* (dev fallback) |

### Auto-routing means the miner is not ours

The engine picks a miner per intent, so the miner that answers is not always
Elcaro and its schema is not always ours. A live example: a scan of an email
from `external.com` routes to **TxLens (9002)** on intent `EMAIL_SECURITY`,
which returns a domain-reputation report with `confidence: 0.9` and no
`risk_score` at all.

So `normalize()` distinguishes a **verdict** (a risk score, a risk level, or
flagged techniques) from a **signal** (anything else the router returned).
A signal renders as *"SIGNAL, NOT A VERDICT"* with the intent named — it never
gets banded, and its `confidence` is never displayed as an injection risk.
Showing a domain-reputation confidence as "Injection risk 0.90" would be a lie
told with total confidence.

Worth knowing when reading extension output: a scan that returns a signal has
still been paid for and still counts — the network just routed your question
somewhere you did not expect.

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

### Payer wallet

The bridge signs every ask with one dedicated wallet. It is deliberately **not**
the miner registration key — mixing a registration signer with a payment signer
means one compromise spends both.

| | |
|---|---|
| Address (Base Sepolia, chain 84532) | `0x3aB5CDE666c356B043111AAFDA16aC258E19868F` |
| Pays | USDC `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |
| Per ask | 10000 (6dp) = $0.01 |
| Private key | **not in this repo.** macOS Keychain service `elcaro-telegraph-x402-payer`, mirrored in `~/.config/elcaro/telegraph-x402-payer.env` (0600, dir 0700) |

```bash
# read the key without printing it into a shell that logs history
security find-generic-password -a "$USER" -s elcaro-telegraph-x402-payer -w
```

Funding: send testnet USDC to the address above on **Base Sepolia** (chain
84532) — not Ethereum mainnet. The default `TELEGRAPH_BRIDGE_DAILY_CAP` of 40
asks/day is $0.40/day, so a few dollars of testnet USDC lasts a long time. No
ETH is needed: x402 `exact` transfers are gasless, the facilitator submits them.

Set the key in Netlify (`elcaro` is in the `udirobert` team — `netlify login`
as that account first, then `netlify link`):

```bash
netlify env:set "TELEGRAPH_X402_KEY=$(security find-generic-password -a "$USER" \
  -s elcaro-telegraph-x402-payer -w)" \
  --context production --site 1a5219cc-1d31-45f1-8482-039e086c8020
```

Env var changes only reach the site on the next deploy.

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
  "payerConfigured": true,
  "payerAddress": "0x3aB5CDE666c356B043111AAFDA16aC258E19868F",
  "tokenRequired": false,
  "extensionPinned": true,
  "dailyCap": 40, "asksUsed": 3, "asksRemaining": 37,
  "costPerAskUsd": 0.01
}
```

`payerConfigured: true` with `payerAddress: null` means the key is present but
does not parse — almost always a stray space or newline from a paste. That
distinction is the difference between "not switched on" and "misconfigured",
and it is the reason the key is trimmed on read.

### Error codes

Every failure is `{ error, code }` with a stable `code` — the extension renders
copy off the code, so infra strings never reach the overlay.

`FORBIDDEN_ORIGIN` (403) · `FORBIDDEN_TOKEN` (403) · `INVALID_JSON` (400) ·
`BAD_REQUEST` (400) · `QUERY_TOO_LARGE` (413) · `CAP_REACHED` (429) ·
`PAYER_NOT_CONFIGURED` (502) · `PAYER_KEY_INVALID` (502, the key does not
parse) · `PAYMENT_SIGN_FAILED` (502) · `PAYMENT_REJECTED` (502, envelope fine
but the payer could not settle — usually an empty testnet wallet) ·
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

`app/extension/tests/` drives the extension in jsdom against a Gmail-shaped
fixture and the real popup HTML:

- `content.test.mjs` — button mount, extraction, the progress state, each
  band's copy, the shortcut path, miner attribution, the error path,
  `Escape`/Dismiss, and a guard that no env var name or protocol jargon leaks
  into the overlay.
- `popup.test.mjs` — renders the popup against stubbed worker replies (live,
  not-configured, unreachable, empty history) and asserts what the user
  reads. The popup's loudest failure mode is a null element, so every `$("id")`
  is checked against a rendered panel.

```bash
cd app/extension/tests && npm install && npm test
```

They have already earned their keep: the content test caught the message body
being read with `innerText` only, which jsdom (and some other engines) do not
implement, so every scan shipped an empty message.

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
