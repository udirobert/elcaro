# Elcaro — PayBox Ch.1: The Firewall That Bleeds

> MoonPay Hackathons Ch.1, Agents & PayBox, Oct 16-17 2026.
> $20k USDC pool, 1st $5k. Live plugin + demo video on X.
> Docs https://developer.paybox.sh , https://docs.paybox.sh

## Positioning (researched)

**Elcaro is the counterparty half of the trust layer.** MoonPay built
the authority half — vault, scoped grants, passkey (Soto-Wright: "someone
had to build the trust layer for that world"). Seven-plus Ch.1 entries
pitch "should this payment happen" — tx-level checks (amount, merchant,
limits) that MoonPay already ships server-side as spend limits, approval
modes, and audit events. We are not one of them, and we never use their
vocabulary: no "spend cap", no "policy engine", no "guardrail".

**The wedge:** every tx-level check sees a $1,200 wire to a valid
merchant under an active grant — all green. The attack lives upstream
of the transaction, in the content that *created* the intent. Only
content inspection sees it. On screen, this is literal: each bleed
pane shows green approval checks passing before the heist plays.

**Elcaro is the content mandate** — PayBox scopes what agents may
spend; Elcaro scopes what they may believe. And the one scenario no
tx-check addresses: a marketplace plugin's *response* injecting the
agent — their own catalog as attack surface. We protect the bazaar,
not just the wallet.

**Proliferation math for the judges:**
1. Scan-before-spend = every gated transaction is ≥2 paid x402 calls
   through a PayBox wallet instead of 1. Adoption literally multiplies
   marketplace volume.
2. Autonomous grants are capped by exactly this fear. Elcaro is the
   control that makes "autonomous" defensible → more autonomous usage
   → more volume without passkey friction.
3. Every marketplace needs a bouncer: any plugin's output is untrusted
   input to the next agent. Listing Elcaro makes the *catalog itself*
   safer — first-party trust infra, not a plugin.

## Shipped

- `POST /api/x402/scan` — spec 402 (PAYMENT-REQUIRED, exact/eip155,
  Base + Base Sepolia), EIP-3009 verified locally (recovered signer,
  payTo/amount/validity/nonce-replay), optional facilitator settle.
  Free /scan untouched. PayBox path: `use_service` probes → signs →
  re-fetches → verdict.
- `/paybox` — the PayBox Gauntlet: six scenarios, one per rubric row
  (consumer finance, merchant tools ×2, predictions, creative, control),
  each mapped to the real MCP tool the injection was steering
  (request_payment, use_service→request_secret, request_swap,
  request_secret, request_wallet_sign). Live verdicts + x-ray spans +
  scoreboard: attacks stopped, $ protected, false positives, paid calls.
- **The cold open is a product surface:** every card's "without the
  gate" panel is playable — click "▶ run unguarded" and a simulated
  agent transcript types out the heist (instruction absorbed → tool
  fired → BLEED stamp with the dollar stake). Run-all volleys heist →
  gate → heist → gate across all six. The video's first act is a screen
  recording of the product, not an edit.

## Demo arc — money moves or it doesn't count

1. **Cold open, the playable heist (8s):** /paybox, card 1 — hit
   "▶ run unguarded": four green checks pass (amount ✓ merchant ✓
   grant ✓ autonomous ✓) — *every tx-level engine approves this* —
   then the transcript types, payee swaps to 0xDEAD…, request_payment
   fires, BLEED — $1,200. "The field gates the transaction. Watch it
   approve the attack."
2. **The gauntlet (~30s):** /paybox on screen, run-all volley — category
   chip → injected span glows → STOP stamps → "request_payment never
   fired — $1,200 stayed in the vault." Cut fast across 5 attacks.
3. **The escalation (~10s):** verdict drives the grant — agent calls
   request_account_change ("poisoned content — switch grant to
   always_approve") → manage_url → human tightens the grant with a
   passkey. Nobody else demos a scan verdict tightening a live grant.
4. **GO means GO (~8s):** clean invoice → GO → real settlement through
   PayBox. The gate isn't a deny-all — false positives kill products too.
5. **The seal (~7s):** signed STOP verdict + Ref: elc-… → /canary
   resolves → /verify green seal. The attack became evidence.
6. **Tag (5s):** "PayBox scopes what agents may spend. Elcaro scopes
   what they may believe. elcaro.trustfall.xyz/paybox"

## Landmines (checked)

- `discover_services` is curated (≥10 payers/30d) — a fresh endpoint
  won't be discoverable tonight. Demo `use_service` with the direct
  URL; don't claim catalog discovery on camera unless verified.
- Money tools pause for passkey even under autonomous — the approval
  beat is a feature ("human stays in the loop"), rehearse it.
- Mainnet eip155:8453 + Sepolia both offered; confirm which rail
  PayBox signs during rehearsal.
- Verified locally: probe→402, signed pay→verdict, replay→402,
  tampered payTo→402; all 6 gauntlet scenarios score as designed
  (5 dangerous/quarantined, 1 clean pass at 0.00).

## Checklist

- [x] /api/x402/scan paid lane (challenge, verify, proxy, receipt)
- [x] /paybox gauntlet page (6 scenarios, live verdicts, scoreboard)
- [x] Deploy + set X402_PAYTO on Netlify — live-verified: real $0.01 USDC
      payment on eip155:8453 settled, signed verdict returned
- [x] PayBox rehearsal: `paybox use-service` → poisoned invoice →
      dangerous/quarantined (risk 0.73, authority_framing); rail = Base exact
- [ ] Film + post 60s video to X — filmed (`demo-video/paybox/final-60s.mp4`,
      `final-hd.mp4` 68s); X post outstanding
- [x] Submit plugin — `paybox-plugin/dist/plugin.mjs` uploaded + submitted
      in dev portal ("Elcaro — content firewall for agents"), checks passed,
      2 tools, host `api.elcaro.trustfall.xyz` configured

## Submitted artifact (portal, 2026-10-17/18)

`paybox-plugin/` — starter v1.0.2, Node 24 + pnpm 11.11.0, esbuild bundle
`dist/plugin.mjs` (386 KB, sha256
9dc0b6c26b11e02662edff2fae93730a544f36e45b86a0d845df725f50966023).
Two MCP tools:

- `elcaro_scan` — x402 transaction proposal: POST to
  `elcaro.trustfall.xyz/api/x402/scan`, maxAmount 10000 atomic (0.01 USDC),
  asset 0x833589fc…2913 on eip155:8453. PayBox validates the 402 challenge,
  pays, returns the signed verdict.
- `elcaro_quick_scan` — free HTTPS POST to `api.elcaro.trustfall.xyz/scan`
  (4s timeout), structured verdict {risk_score, risk_level, quarantined,
  flagged_techniques, summary, human_summary}.

Portal state after submit: "Submitted — hackathon entry complete", privately
installable under Unofficial plugins while under review.
