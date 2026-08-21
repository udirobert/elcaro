# Growth Loops — Viral Hooks & Engagement Design

> Date: 2026-08-21 · Context: pre-submission push (Kiro deadline Aug 23, Telegraph Sep 7)
> Status: design proposal — nothing here is implemented yet; awaiting greenlight.

## TL;DR

Elcaro's frontend currently has a **linear funnel** (land → scan → integrate) with
no loop. Three additions turn it into a growth engine, ranked by
impact-per-effort under the deadline:

1. **The Gauntlet** (new `/gauntlet` route) — a one-click adversarial test that
   runs six canned injections through the live engine and renders a shareable
   scorecard. Zero-input virality: no pasting, instant drama, demonstrates the
   whole taxonomy.
2. **Shareable verdicts** — "Share this scan" on results, encoded in the URL
   fragment (no backend, no stored content — privacy-preserving by construction).
3. **Live proof strip** on the home page — real stats from the miner's `/metrics`
   endpoint: scans served, median latency. Social proof that's *true*.

Plus one narrative addition: surface the **guard-hook dogfooding story**
("the agent that built this firewall is guarded by it") on the landing page.

## Why security products are uniquely viral

VirusTotal, Have I Been Pwned, and Shodan all grew the same way:

- **Fear + curiosity**: "is *my* stuff vulnerable?" is an itch that must be
  scratched — the click is impulsive, not considered.
- **Proof by demonstration**: the product's value is *visible in one interaction*
  — a scan is its own demo.
- **Shareable verdicts**: a result ("you were pwned", "this file is clean") is a
  natural social artifact — people share status, and each share is a new top-of-
  funnel visitor who scans *their* stuff.

Elcaro has the first two. It's missing the third — scan results are
localStorage-only, the loop never closes.

```
        ┌────────────────────────────────────────────┐
        │                                            │
        ▼                                            │
visitor → lands → scans own content → verdict → SHARE ─┘
                    │                                │
                    └→ developer → /integrate → middleware → team asks
                       "what is this?" → more visitors
```

## Feature 1 — The Gauntlet (`/gauntlet`)

**Concept.** A fixed, curated set of injections — one per taxonomy class A–F —
plus two clean controls. One button: "Run the Gauntlet". All payloads scan in
sequence (with the existing scan-beam animation), each verdict lands as a card,
and the finale is a scorecard: "6/6 injections caught · 0/2 clean flagged ·
median 3ms". Share text is pre-written: *"Elcaro caught all 6 classes of
indirect prompt injection in under 10ms. Can your agent's defenses? → link"*

**Why it's the money feature.**
- **Zero input friction** — no pasting means no cold-start problem; the visitor
  is three seconds from the "wow".
- **It *is* the benchmark** — detection quality is the product's core claim, and
  the Gauntlet proves it live rather than asserting it.
- **Built for the demo video** — the sequence (beam sweep → verdict cascade →
  scorecard) is 45 seconds of compelling footage.
- **Challenge framing invites comparison** — "can your agent's defenses do
  this?" is a taunt that travels. Security Twitter loves a scoreboard.
- **Honest by design** — the payloads run through the *live* miner; if a
  detection misses, the scorecard shows it. That honesty is itself a trust
  signal (and the eval/ suite keeps us calibrated).

**Design notes.**
- Payloads are the existing `EXAMPLES` plus one crafted sample per missing
  class — reuse `scanContent`, `ScanResult`, `RiskMeter`, `IndicatorAnnotation`.
- Sequential scans (150ms stagger) so the animation reads as a *volley*, not a
  wall — drama over throughput.
- Scorecard is a distinct visual moment (full-width, big numerals) — designed
  to be the screenshot.
- Route is linked from the home page CTA row ("Try a scan" / "Run the Gauntlet")
  and from scan results after a dangerous verdict ("See all six attack
  classes →").

**Effort:** ~half a day (one route, one component, no backend changes).

## Feature 2 — Shareable verdicts

**Concept.** After any scan, "Share this verdict" builds a URL:
`elcaro.trustfall.xyz/scan#v=<base64url(json)>`. The scan page reads the
fragment on load and renders the shared verdict above the (empty) input.

**Why URL-fragment encoding, not a database.**
- **Privacy by construction** — nothing is stored server-side; the miner is
  stateless by design (and must stay so: it's an on-chain-registered service).
  The content lives only in the link the user chooses to share.
- **Zero backend** — no storage service, no retention policy, no PII surface.
  For a security product, "we don't store your scans" is a *feature* to say
  out loud.
- **Trade-off to flag in the UI** — the shared URL contains the scanned text.
  Show a one-line disclosure on the share action: "The link contains your
  pasted content — share only what you're comfortable making visible."
  An alternative "verdict-only" share mode (score + techniques, content
  replaced by a truncated preview) covers the cautious case.

**Effort:** ~2 hours (encode/decode helpers + a shared-verdict banner).

## Feature 3 — Live proof strip

**Concept.** A slim band on the home page, under the hero:
`<live counter> scans served · median 3ms · last scan just now` — fetched from
the miner's existing `GET /metrics` (already public, already CORS-open).

**Why.** Social proof that can't be faked (it's the production counter), it
makes the product feel *alive*, and it deepens the "working product, not demo"
positioning. The number ticking up during judging week is quiet but powerful.

**Design notes.** Fetch client-side after hydration (metrics change per
request), render with the same `animate-count-in` token as the risk meter.
Guard against unavailability — the strip hides itself if `/metrics` is slow.

**Effort:** ~1 hour.

## Feature 4 — Guard-hook narrative on the landing page

The landing page doesn't yet tell the dogfooding story — the strongest brand
moment we have. Add one quiet block under the taxonomy:

> **Drinks its own medicine.** Elcaro was built in Kiro — and a Kiro hook runs
> every web page the building agent retrieves through Elcaro before it reads
> it. The agent that built the firewall is guarded by it.

Small, true, memorable — and it links the repo (`.kiro/hooks/`) for the
skeptical. **Effort:** ~20 minutes.

## Sequencing under the deadline

| Order | Item | Why |
|---|---|---|
| Now | Guard-hook block + live proof strip | ~1.5h total, home-page polish before the video |
| Then | The Gauntlet | The demo-video centerpiece; needs the most build time |
| If time | Shareable verdicts | Post-deadline value too (Telegraph Track 3 opens ~Aug 31) |
| Later | "Protected by Elcaro" embed badge, community injection submissions ("The Gauntlet grows") | Post-hackathon; needs moderation tooling |

## Guardrails (non-negotiable for a security product)

- **Never store scanned content server-side** — metrics stay aggregate (already
  true); the miner stays stateless (on-chain contract depends on it).
- **Shares are opt-in and disclosed** — the user decides what leaves their
  browser, and knows exactly what's in the link.
- **No fake numbers** — the proof strip reads the real /metrics; the Gauntlet
  runs the real engine. If a miss shows, it shows. Credibility is the product.

## Rejected ideas (and why)

- **Public leaderboard of "agent security scores"** — needs a scoring
  methodology we can't defend yet; invites gaming.
- **Auto-tweet scan results** — oversteps the trust boundary; security scans
  are often of *embarrassing* content.
- **Referral/gamified rewards** — wrong register for a security tool; erodes
  the sober-brand positioning that makes the product credible.
