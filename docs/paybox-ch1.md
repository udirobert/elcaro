# Elcaro — PayBox Ch.1: The Firewall That Bleeds

> MoonPay Hackathons Ch.1, Agents & PayBox, Oct 16-17 2026.
> $20k USDC pool, 1st $5k. Live plugin + demo video on X.
> Docs https://developer.paybox.sh , https://docs.paybox.sh

## Positioning (researched)

**Elcaro is the content mandate.** Google's AP2 binds *authorization*
(signed intent/cart mandates — what the agent may spend). Visa, PayPal,
Human Security, NeuralTrust all name prompt injection the #1 killer of
agentic commerce. Nothing binds *the content that shapes what the agent
decides*. PayBox scopes what agents may spend; Elcaro scopes what they
may believe. That is the mandate gap — and MoonPay is the one company
whose autonomous-grant model can't ship safely without it.

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

1. **Cold open, the playable heist (5s):** /paybox, card 1 — hit
   "▶ run unguarded": the transcript types, payee swaps to 0xDEAD…,
   request_payment fires, BLEED — $1,200 stamps red. This IS the
   product; visitors can run it themselves after the video.
2. **The gauntlet (~30s):** /paybox on screen, run-all volley — category
   chip → injected span glows → STOP stamps → "request_payment never
   fired — $1,200 stayed in the vault." Cut fast across 5 attacks.
3. **The escalation (~10s):** verdict drives policy — agent calls
   request_account_change ("poisoned content — switch grant to
   always_approve") → manage_url → human tightens the grant with a
   passkey. Nobody else demos a scan verdict mutating vault policy.
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
- [ ] Deploy + set X402_PAYTO on Netlify (TELEGRAPH_X402_KEY fallback ok)
- [ ] PayBox rehearsal: use_service poisoned → STOP →
      request_account_change; clean → GO — confirm rail + passkey beats
- [ ] Film + post 60s video to X
- [ ] Submit plugin
