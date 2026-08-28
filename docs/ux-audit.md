# UX Audit — Adaptive & Agentic Lenses

> Date: 2026-08-28 · Status: audit complete. R1 (MCP server), R2 (agent-legible layer), R3 (relay contract), R5 (signed verdicts), R4 (correction surface), R6 (reviewer mode), R7 (threshold replay), and R8 (content-type-aware notices) are implemented. Remaining: the P2 agentic-web items (R9–R12).
> Scope: the whole product surface — web app (`app/web`), miner API, Python middleware (`app/middleware.py`), quarantine policy (`core/quarantine.py`), Kiro guard hook (`.kiro/hooks/`) — audited through two lenses:
>
> - **Adaptive UX** — the interface responds to who the user is, what they've done, and the current risk state.
> - **Agentic UX** — AI agents are first-class users of the product (API consumers, site visitors, tool callers), and humans supervise what agents do with it.
>
> Companion docs: `growth-loops.md` (growth design + guardrails), `technique-reference.md` (detection taxonomy).

## TL;DR — the five moves that matter most

| # | Move | Lens | Why first |
|---|---|---|---|
| 1 | Ship an MCP server (`scan_content`, `explain_verdict`) and add it to /integrate as Option 04 | Agentic | MCP is the default agent-integration path and it's the only major one missing. Tool descriptions double as distribution copy. |
| 2 | Split the quarantine notice into agent-instruction + human-summary (the "relay contract") | Both | Every quarantine ends with an agent explaining to a human why content was blocked. That handoff is undesigned today. Small schema change, outsized trust win. |
| 3 | Make verdicts verifiable — sign them, or ship a `/verify` endpoint | Agentic | Elcaro's own notice format is spoofable by the very attackers it detects (§4, BG4). The product must model the trustworthy patterns it sells. |
| 4 | Add a "report this verdict" correction surface on every result | Adaptive | Adaptive systems without correction loops drift and lose trust silently; reports feed `eval/` directly. |
| 5 | Agent-legible site layer: `llms.txt`, specimen discovery, WebMCP-ready scan form | Agentic | An agent fetching /scan today gets an empty client-rendered form. `/specimen/raw` is the only natively agent-consumable artifact. Cheap, immediate. |

Everything else is sequencing. Full roadmap in §6.

## 1. Frame — three user classes, one product

Elcaro doesn't have one user. It has three, and they experience different products:

1. **The evaluator** (human) — lands on the site, runs the Gauntlet, pastes a scan, judges credibility. Serves: acquisition and trust.
2. **The supervisor** (human) — the developer who wired Elcaro into their agent and now lives with its decisions: reviewing quarantines, tuning thresholds, answering "why did my agent refuse to read that email?" Serves: retention and trust-at-scale.
3. **The agent** (machine) — consumes `safe_content`, verdict JSON, quarantine notices, specimen pages. Its "experience" is copy and schema. Serves: protection itself.

The audit's core claim: **today's surfaces are designed for the evaluator, the API serves the agent, and almost nothing serves the supervisor.** Adaptive UX is how one interface serves many humans well; agentic UX is how the product treats agents as users rather than pipes. The two lenses meet in a single artifact — the quarantine notice, which is simultaneously the product's most-seen output, its agent-facing copy, and the trigger for the agent→human handoff.

One more thing is unique to Elcaro: **the threat model is the agentic web.** Every design choice on agent-facing surfaces is also a demonstration of the product's thesis. Elcaro doesn't just serve agents — it must exemplify how sites should treat them.

## 2. Current-state inventory

What exists today, mapped against the three user classes. ✓ = well served · ~ = partially · — = not served.

| Surface | Evaluator | Supervisor | Agent | What it does now |
|---|---|---|---|---|
| Home `/` | ✓ | — | — | Live-catch hero demo, trust chips (live `/metrics`, Kiro dogfood, on-chain), taxonomy grid, journey-aware closing CTA (`adaptive-cta.tsx`) |
| Scan `/scan` | ✓ | ~ | — | Paste → verdict; content-type whisper from paste shape; first-visit onboarding; findings with progressive disclosure; risk-conditioned "your move"; copy-as-curl; share-as-link; localStorage history |
| Gauntlet `/gauntlet` | ✓ | — | ~ | 8 canned payloads against the live engine, honest scorecard (shows misses), share copy; marks journey state |
| Specimen kit `/specimen` + `/raw` | ✓ | — | ✓ | The "EICAR file for prompt injection": inert marked specimens at a fixed URL; `/raw` is plain UTF-8, no JS — explicitly agent-consumable |
| Integrate `/integrate` | ✓ | ✓ | ~ | Three paths (Direct API, Python middleware, Telegraph miner 8848) + five operating rules (scan-before-act, email highest-risk, 0.5 block / 0.3 flag, explicit `content_type`, log quarantines) |
| Share links `/scan#v=…` | ✓ | ~ | — | Verdict encoded in URL fragment; nothing stored server-side; disclosure shown. The privacy stance is itself a trust artifact |
| Miner API `POST /scan`, `GET /metrics` | ~ | ~ | ✓ | Structured verdicts (indicators, TTPs, remediation, `safe_content`, `quarantined`); CORS-open; no auth/rate story, no discoverability layer |
| Middleware + quarantine policy | — | ✓ | ✓ | `app/middleware.py`: replace / block / warn modes. `core/quarantine.py`: single source of truth for threshold + notice text, shared by engine, middleware, and web |
| Kiro guard hook | — | ✓ | ✓ | Dogfooding: the agent that built the firewall is guarded by it. Told quietly on the home page, verifiable in `.kiro/hooks/` |
| Discovery (robots, sitemap) | ✓ | — | — | `robots.ts` speaks to search crawlers only. No `llms.txt`, no tool manifest, no agent-facing description of the product anywhere on the site |

Read the last column top to bottom: agent support exists exactly where the team built it deliberately (`/specimen/raw`, the API, the middleware) and nowhere else. That pattern — deliberate pockets, no system — is what §3 and §4 generalize.

## 3. Adaptive lens — findings

### Strengths (keep, and extend)

- **A1 · Journey-aware CTAs are real and shipped.** `adaptive-cta.tsx` reads actual visitor state (fresh / ran-gauntlet / has-scanned, via localStorage) and changes the closing pitch to match. SSR-safe, motion-aware. This is genuine adaptive UX, not a mockup.
- **A2 · Risk-conditioned guidance.** `next-steps.tsx` doesn't stop at the alarm — it adapts the recommendation to the verdict ("Block it" / "Flag it" / "Process it — but log it"), using the same 0.5/0.3 thresholds the integration docs teach. Doctrine and UI agree, which is rarer than it should be.
- **A3 · Progressive disclosure with intent.** Findings arrive collapsed, expand per-card or all at once; the summary is suppressed when safe; full-content evidence is shown *only* in the safe case (where "we checked, found nothing" is the signal). Detail appears where the decision needs it.
- **A4 · The provenance whisper.** `scan-form.tsx` guesses email/code from the paste shape and suggests `content_type` — adaptation that quietly teaches one of the five integration rules.
- **A5 · Motion and onboarding adapt.** `useReducedMotion` everywhere that matters; first-visit onboarding keyed to empty history and dismissed on first interaction.

### Gaps

- **AG1 · No expertise adaptation.** Journey state is three buckets; a security researcher and a first-time founder get identical depth. The reviewer who clicks "Expand all" on every verdict is telling the product something, and the product isn't listening. → *Reviewer mode* (R6): persist disclosure preference, default findings to expanded for repeat expanders, and say so when it flips.
- **AG2 · No correction surface.** There is no way to say "this verdict was wrong." A detector that over-flags loses trust faster than one that misses — and without a report path, over-flagging is invisible to the team and `eval/` gains no labeled adversarial samples from real use. → *Report this verdict* (R4).
- **AG3 · Quarantine copy doesn't adapt.** `core/quarantine.py` emits one template regardless of `content_type`. The relay instruction for a blocked *email* ("tell the user you couldn't read it, and why") differs from blocked *code*. One-size copy is a missed chance to be useful at the exact moment the product matters most. → R8.
- **AG4 · No ambient posture.** Every scan is a discrete event; nothing in the visual language expresses "watching, all clear." Fine for a demo — but the supervisor surfaces (R10) will need a calm-mode vocabulary the current tokens don't define. The miner-status dot is the only ambient element that exists. Define calm/loud tokens now, spend them later.
- **AG5 · Threshold doctrine is told, not felt.** "0.5 blocks, 0.3 flags" is asserted on /integrate but the user can't *see* what moving it does. → *Threshold replay* (R7): re-score the user's own session history (already in localStorage) at candidate thresholds — "at 0.3, two of your last 20 scans change verdict." Free, private, client-side, and it turns doctrine into intuition.

## 4. Agentic lens — findings

### Strengths

- **B1 · `safe_content` is designed agent-facing copy, single-sourced.** `core/quarantine.py` exists precisely so the engine, the middleware, and the web playground render the same notice. "Three consumers must agree" is exactly the right instinct — and rare. Most products would let three copies drift.
- **B2 · The Specimen Kit is natively agent-consumable.** `/specimen/raw` is plain UTF-8, no JavaScript, "readable by any HTTP client." It is the one page on the site designed for a machine reader — proof the team can do this when it decides to.
- **B3 · Verdicts are structured by construction.** Indicators, TTPs, remediation, confidence, evidence offsets — an agent consumes a verdict as JSON, never by scraping prose.
- **B4 · Copy-as-curl bridges the audiences.** Every human verdict page hands over the exact agent-facing call that produced it, replayable in a terminal. The demo and the API are the same product, visibly.
- **B5 · Dogfooding with receipts.** The Kiro guard hook screens everything the building agent retrieves. The strongest agentic-UX story available — already true, already (quietly) on the site.

### Gaps

- **BG1 · No MCP server.** /integrate offers Direct API, Python middleware, and Telegraph — but MCP is the default integration path for agent frameworks now, and Elcaro isn't on it. The scan tool is a perfect fit: one input schema, structured output, zero ambient state. Tool *descriptions* are UX copy for the model choosing tools, and double as distribution via MCP registries. → R1.
- **BG2 · The site is agent-invisible.** An agent fetching `/scan` receives an empty client-rendered form. `robots.ts` addresses search crawlers only; there is no `llms.txt`, no machine-readable API description outside the GitHub README, no way for an agent to discover the specimen kit or the scan endpoint. → R2.
- **BG3 · WebMCP posture is undefined.** WebMCP (W3C Web Machine Learning Community Group draft, first published Aug 2025, Microsoft/Google-authored — a draft in active development, *not* a standard) lets sites expose JavaScript functions or HTML `<form>` elements as agent-callable tools with natural-language descriptions and JSON schemas. Elcaro's scan form *is a form* — the declarative path fits it exactly. Don't ship against a draft; do keep the form's semantics tool-declarable (stable field names, labels, submit contract) so declaring it later is trivial. Position: track, prepare, be an early exemplar when browsers land it. → R9.
- **BG4 · Verdicts are spoofable — the exemplar problem.** The quarantine notice (`[CONTENT QUARANTINED BY ELCARO — …]`) is an authority-framed string: precisely the pattern class (`authority_framing`) the detector itself flags. An attacker who knows the format can inject a fake "[ELCARO SCAN: SAFE]" into content to lull a pipeline, or a fake quarantine notice to teach agents to ignore real ones. By Elcaro's own doctrine, unsigned in-band notices are untrusted. The product's own output fails its own sniff test. → R5: structured/JSON `safe_content` for machine consumers, signed verdicts with a public `/verify`, and at minimum documented guidance that in-band notices are display text, not trust signals. Sharpest finding in this audit — fixing it is simultaneously a security fix and a brand asset ("our verdicts are signed").
- **BG5 · The agent→human handoff is undesigned.** When content is quarantined, the agent must explain to its human what happened. Today it receives machine-register prose ("Risk score: 0.95, level: dangerous. Flagged techniques: authority_framing.") and must paraphrase — and paraphrase loses fidelity at exactly the moment fidelity matters. → R3, the *relay contract*: every verdict carries a `human_summary` — one or two sentences written for the end user, designed to be quoted verbatim. ("Elcaro blocked this email: it contains a fake system instruction trying to redirect password resets. The sender is not your system administrator.") The cheapest high-leverage UX change in this audit.
- **BG6 · warn-mode salience is unexamined.** The middleware's "warn" mode *prepends* its warning, then lets the injected content follow. Elcaro's own taxonomy (`placement_salience`) says document edges carry instruction weight — so prefix is defensible — but the warning then competes with an injection adversarially optimized against exactly such warnings. Nobody has tested agent compliance either way. → R11: dogfood the taxonomy with a prefix/suffix/sandwich experiment in `eval/`, and publish the result.

## 5. Design principles

Eight principles distilled from the findings. Ordered: each one constrains everything below it.

1. **Three readers, one story.** Every surface serves the evaluator, the supervisor, and the agent — and never tells them contradictory things. If the docs say "0.5 blocks," the middleware default, the quarantine notice, and the UI must all say 0.5. `core/quarantine.py` already models this for policy; extend the discipline to copy and behavior.
2. **Evidence before assertion.** Never render a verdict without the matched text that caused it. Trust in a security product is earned per-claim. The inline evidence, confidence, and TTP chips are the product working as designed — every future surface inherits this obligation.
3. **Adapt openly.** The interface may adapt to journey, expertise, and risk state — but every adaptation is announced and reversible, and navigational anchors never move. Silent adaptation reads as instability; explained adaptation reads as care.
4. **Calm when safe, loud when not.** Attention is a budget spent only on quarantines. The safe state must stay visible (absence of alarm is information) but quiet, so "dangerous" remains unmissable and the product never cries wolf.
5. **The agent is a reader, not a pipe.** `safe_content`, notices, tool descriptions, and specimen pages are UX copy for a machine reader: written deliberately, versioned deliberately, and tested against adversarial readers. Prose intended for agents is product surface.
6. **Relayable by construction.** Every verdict must survive the agent→human handoff verbatim. Design for the quote: a `human_summary` the agent can repeat word-for-word, at the reading level of someone who didn't run the scan.
7. **Correction is core UX.** "This verdict was wrong" is a first-class action on every result, not a support channel. Correction loops keep detection products calibrated — and keep users bought in when the product is wrong.
8. **Exemplar, not just tool.** Elcaro's own agent-facing surfaces must model the trustworthy patterns whose absence it detects: structured, signed, documented, honest about uncertainty. The product is the demo.

## 6. Prioritized roadmap

**P0 — now (days, no new infrastructure, all independent of each other):**

| ID | Item | Finding | Effort | Principles |
|---|---|---|---|---|
| R1 | **MCP server** — expose `scan_content` + `explain_verdict` as MCP tools; add to /integrate as Option 04; list in a registry. Design note: write tool descriptions for the *model choosing tools*, not the human reading docs — "Scan content an AI agent is about to read for hidden instructions (indirect prompt injection). Returns risk score, verdict, and safe replacement content." | BG1 | S | 5, 1 |
| R2 | **Agent-legible layer** — ship `/llms.txt` (what Elcaro is, the API contract, the specimen kit, the MCP endpoint once R1 lands); link `/specimen/raw` from it. | BG2 | S | 5, 8 |
| R3 | **Relay contract** — add `human_summary` to the verdict schema and split the quarantine notice into agent-instruction + human-summary registers (`core/quarantine.py`, middleware, web result renders it as "what your agent should tell you"). | BG5 | S | 6, 1 |
| R4 | **Correction surface** — "Report a miss / over-flag" on every verdict. Opt-in, content-hashed, no raw content stored; routes to `eval/` as labeled candidates. | AG2 | S–M | 7, 2 |

**P1 — next (weeks):**

| ID | Item | Finding | Effort | Principles |
|---|---|---|---|---|
| R5 | **Verifiable verdicts** — signed verdicts (HMAC or Ed25519) + public `/verify`; interim: structured JSON `safe_content` for machine consumers + docs declaring in-band notices as display text. | BG4 | M | 8, 5 |
| R6 | **Reviewer mode** — persist disclosure preference; default-expanded findings for repeat expanders; announce the flip, one-tap revert. | AG1 | S | 3 |
| R7 | **Threshold replay** — client-side what-if over session history on /integrate ("at 0.3, two of your last 20 scans change verdict"). | AG5 | S | 3, 4 |
| R8 | **Content-type-aware notices** — quarantine copy varies by `content_type` (email vs code vs chat get different relay instructions). Extends R3 — do R3 first. | AG3 | S | 5, 6 |

**P2 — position for the agentic web (track + design now, ship when ready):**

| ID | Item | Finding | Effort | Principles |
|---|---|---|---|---|
| R9 | **WebMCP readiness** — track the W3C WebML CG draft; keep the /scan form tool-declarable (stable names, labels, submit contract); ship declarative tool markup behind a flag when a browser lands an implementation. Calendar-driven by the spec, not by us. | BG3 | S now / M later | 8 |
| R10 | **Supervision surface (concept)** — a calm-mode "watch" view for supervisors. Hard constraint: the miner stays stateless. Design around it: client-side session watch (evolve `scan-history`) + optional operator webhooks (the operator stores; Elcaro never does). | AG4 | L | 4, 1 |
| R11 | **Warn-mode salience experiment** — prefix vs suffix vs sandwich, tested against adversarial injections in `eval/`; publish the result. | BG6 | M | 5, 2 |
| R12 | **"Designing for agents" page** — public guidance on treating agent visitors well (`llms.txt`, structured responses, signed verdicts, specimens). Thought leadership that *is* the threat model. | — | S | 8 |

Sequencing: R1–R4 are small and independent — any order, all before the P1 batch. R8 depends on R3. R9's ship date belongs to the spec, not the roadmap.

## 7. Metrics to watch

- **Adoption** — MCP tool invocations (R1); /integrate completion by option; `llms.txt` fetches (R2).
- **Trust** — verdict share rate; correction-report rate and resolution time (R4); Gauntlet honesty (misses must stay shown, never edited around).
- **Adaptive** — reviewer-mode adoption and stickiness (R6); threshold-replay usage preceding integration (R7).
- **Agentic** — agent-originated API scans (UA-based, approximate); specimen fetches by non-browser agents; WebMCP tool calls when live (R9).
- **Handoff** — qualitative: how integrators actually use `human_summary` (support channels, Discord sampling) after R3 ships.

## 8. Constraints honored

Carried over from `growth-loops.md` and the architecture — every proposal above respects these:

- **The miner stays stateless.** No scan content stored server-side, ever (the on-chain registration depends on it). R4 is content-hash + opt-in; R10 stores nothing on Elcaro infrastructure.
- **Shares stay opt-in and disclosed.**
- **No fake numbers.** Live metrics only; the Gauntlet shows real misses.
- **Sober brand.** No gamification, no leaderboards. Adaptive ≠ playful — adaptation is quiet and always explained.
- **Accessibility and reduced-motion support are existing strengths.** All new surfaces inherit them.





