# Hackathon Participation

Elcaro is competing in two hackathons. The product is the same; this page
records the submission details for each.

## Ready, Spec, Ship (Kiro) — Aug 1–23, 2026

- **Host:** John Crickett, Angie Jones, Gregor Ojstersek · sponsored by Kiro
- **Challenge:** Build a real-world application using Kiro, spec-driven
- **Status:** Submission due Aug 23, 2026 23:59 UTC · [Event page](https://codingagents.fyi/hackathon/kiro/)
- **Submission:** public repo + `.kiro/` + README + demo video + Google Form

### Rubric (100 pts) → where Elcaro lands

| Criterion | Pts | Position |
|---|---|---|
| Application Quality | 40 | Live product: deterministic engine, 70 tests, deployed at elcaro.trustfall.xyz with a real miner API — no mocked functionality. Product surface: scan playground with quarantine verdicts, the Gauntlet (one-click adversarial benchmark), shareable verdicts, live proof strip |
| Kiro Usage | 20 | Entire codebase built spec-first: `.kiro/steering/` (4 steering docs) + `.kiro/specs/` (4 full requirements→design→task suites, incl. the guard-hook spec authored during the competition window) + a `PostToolUse` **hook** (`askAgent` on web fetches) that scans agent-retrieved content through Elcaro — dogfooding: the agent that built the firewall is guarded by it. Hook fires `[ELCARO GUARD]` 🚨 with risk score and technique breakdown inline. Verified E2E against `/specimen/raw`. + `.kiroignore` |
| Documentation | 20 | Product-first README; this docs/ directory; self-hosting instructions |
| Innovation & Potential | 15 | Novel category (agent runtime security), MITRE ATLAS mapping, live on-chain miner with paid demand |
| Presentation | 5 | Demo video recorded against the live site (hero live-catch → Gauntlet volley with stamps → real-scan quarantine stamp → guard hook firing in the Kiro IDE) |

### Submission checklist

- [x] Public repo (github.com/udirobert/elcaro)
- [x] `.kiro/` directory committed (4 specs incl. kiro-guard, steering, hooks, .kiroignore)
- [x] VPS miner redeployed with current code (safe_content/quarantined fields live, 18/18 checks passed, on-chain YAML hash verified)
- [x] Judges' path verified: live URL primary (elcaro.trustfall.xyz — custom domain live, Let's Encrypt cert provisioned, full `deploy/verify-live.sh` suite 21/21 passed including frontend proxy checks), self-host repo secondary
- [ ] Demo video on YouTube (unlisted OK) — record against the live site; include the guard hook firing in the Kiro IDE
- [ ] Google Form submitted before Aug 23 23:59 UTC
- [x] E2E guard-hook check in the Kiro IDE — fetch https://elcaro.trustfall.xyz/specimen/raw → [ELCARO GUARD] 🚨 risk 1.00 / dangerous, all 6 technique classes (spec `.kiro/specs/kiro-guard/` task 3.2 ✓)

## Telegraph Protocol Hackathon — Season I

- **Status:** Track 1 (Miners) — registered and active
- **Key dates:** T1/T2 close Sep 7, 2026 · Track 3 (Apps) opens ~Aug 31
- Log of every submission iteration: [SUBMISSIONS.md](../SUBMISSIONS.md)

### Miner registration (on-chain, immutable)

| Field | Value |
|---|---|
| Miner ID | `8848` |
| Registration ID | `145` |
| Network | Base Sepolia |
| Registry contract | `0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8` |
| YAML URL | https://api.elcaro.trustfall.xyz/telegraph.yaml |
| Fee address | `0x1e17B4FB12B29045b29475f74E536Db97Ddc5D40` |
| Registered | 2026-08-20 · tx `0x79a908a6ac0b45dad82048e25cb148dc3daf8a841510fbef31b4ad5c006f9d3f` |
| Intents | `CONTENT_MODERATION`, `TEXT_CLASSIFICATION` |
| Pricing | 0.01 USDC per request (x402) — immutable after registration |

Verify the record: `curl -s https://devnode.telegraphprotocol.com/api/miners/145`

### Compatibility notes (do not break the miner)

- The on-chain registration pins the SHA-256 of the YAML served at
  `/telegraph.yaml` — never edit `miner/telegraph.yaml` without
  deregistering/re-registering.
- `ScanResponse` field additions (e.g. `safe_content`, `quarantined`) are
  backward-compatible: the registered `output_schema` only *requires*
  `risk_score`, `risk_level`, `content_type`, and JSON Schema permits
  additional properties. Removing or renaming existing fields is NOT safe.
- `signal_mapping` and `on_chain.fields.source_path` values must continue
  to exist in the response.
