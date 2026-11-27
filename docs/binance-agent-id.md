# Binance Agent ID Hackathon — instruction-safety evidence memory

> **Status:** assessed — **declined for this cycle / watchlist** (decided
> 2026-11-27).
> **Recommendation:** do not enter. Mission fit is genuinely high, but novelty
> is squeezed from both sides (runtime scanners like TollWarden/Sunglasses on
> one side, hash-pinned evidence registries like skillreg on the other), the
> remaining wedge is packaging rather than a missing capability, the hardest
> requirement (30 genuine Agent ID interactions) is a distribution problem
> engineering cannot solve, and the entry would displace higher-EV work:
> OpenServ win conversion, onboarding/conversion measurement, paid-lane
> validation, the Gmail extension, and the Phase 2 benchmark. Reconsider only
> if a credible partner can bring 20–30+ real Agent ID holders quickly, a
> BNB ecosystem team explicitly wants the integration, or a sharper answer
> emerges to "why is this meaningfully different from TollWarden + skillreg +
> the existing BNB safety registries".
> **Deadline:** December 9, 2026, 08:00 UTC.
> **Official announcement:** <https://www.binance.com/en/support/announcement/detail/95f5dbe0ea674a48a739b59e046648bf>
> **Readable mirror of the full text:** <https://binancehub.co.kr/en/notice/290513/>

## Opportunity

Binance Wallet × BNB Chain are running a 60,000 USDC Agent ID hackathon. The relevant target is the **Agent Application Innovation Award** (29,000 USDC across ten prizes), not the Pioneer volume leaderboard.

Innovation eligibility requires:

- a live product;
- smart contracts deployed on BNB Chain, verified and open-sourced on BscScan;
- active use of Agent ID;
- at least **30 distinct Agent ID addresses interacting with the submitted contract(s) during the submission window**.

Existing projects are eligible, but only in-window activity counts. Judging is weighted: **Agent ID application depth 30%**, practicality/feasibility 25%, product completion 25%, innovation 20%.

Agent ID is a non-transferable ERC-721 on BNB Chain:
`0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F`. The basic check is
`balanceOf(wallet) > 0`; the registry also exposes `handleOf(address)` and
`ownerOfHandle(string)` for identity-aware use. See
[SPACE ID's Agent ID docs](https://docs.space.id/agent-id).

## Research-backed thesis

Elcaro should **not** build another generic contract-safety registry. That lane is already occupied. The defensible wedge is narrower and closer to our core mission:

> **Before an agent mints, approves, pays, installs a skill, or follows project instructions, scan what the content told it to do — then let Agent ID holders turn scan-backed detections into a public evidence memory other agents can query. The detector is the input; the product is identity-bound provenance for warnings.**

Three research findings support that positioning:

1. **The threat is real and specific to agentic crypto.** Binance's own
   [Agentic Wallet skill](https://raw.githubusercontent.com/binance/binance-skills-hub/main/skills/binance-web3/binance-agentic-wallet/SKILL.md)
   warns that token names, symbols, and all on-chain data may contain prompt
   injection, that ingested content is never user confirmation, and that agents
   must not bypass checks. Zscaler-reported campaigns covered by
   [SecurityWeek](https://www.securityweek.com/prompt-injection-attacks-trick-ai-agents-into-making-crypto-payments)
   already use indirect prompt injection in websites and manipulated search
   results to push agents toward fraudulent payments and crypto platforms.
2. **Binance's payment and wallet controls are complementary, not sufficient.**
   Binance Agentic Wallet's x402 payment skill is live on BNB Chain, Base, and
   Solana, with sanctions screening, transaction monitoring, and transaction
   limits ([Binance blog](https://www.binance.com/en/blog/ecosystem/969044993833612571)).
   Those controls constrain the execution of a payment; they do not establish
   whether the text that caused the agent to propose the payment was malicious.
   Elcaro sits upstream of the wallet boundary.
3. **The Agent ID population is large, but the active agent economy is tiny.**
   The independent BAS index reported 271,705 Agent ID holders when checked on
   November 27, but only 1,146 linked ERC-8004 agents, 1,148 holders with
   indexed activity, and 4 with commerce activity
   (<https://www.agent.bas.io/agent/api/binance-agent-id/general>).
   So the 30-interaction requirement is plausible, but holder count is not the
   same as reachable, genuine users. Distribution remains the main execution
   risk — without being impossible.

## Competitive reality

The opportunity is **not** differentiated if described only as an "Agent Safety
Oracle" or "safety-report registry". It is also **not enough** to say Elcaro
scans instructions rather than contracts: instruction scanning already exists.

### Direct and adjacent instruction-safety products

| Project | Existing overlap | Remaining gap |
|---|---|---|
| [TollWarden](https://github.com/tollwarden/tollwarden) | x402 payment firewall; scans the content that caused a payment decision, detects prompt-injected payees, returns `allow`/`flag`/`block`, signs verdicts with Ed25519, exposes counterparty reputation/report APIs, and publishes a detector benchmark | Base/CDP-centric rather than BNB/Agent ID; shared reputation appears service-hosted rather than an immutable community evidence layer; BUSL-licensed and early |
| [Sunglasses](https://sunglasses.dev/documentations) | Open-source input firewall for text, files, tool output, web content, API responses, and agent handoffs before an agent acts | No crypto-payment provenance, Agent ID identity, or public on-chain warning memory |
| [`asale-ai/agent-firewall`](https://github.com/asale-ai/agent-firewall) / [`neharikasrivastav/agent-firewall`](https://github.com/neharikasrivastav/agent-firewall) | MCP/agent firewalls scanning tool outputs, hidden Unicode, injection phrases, credential exfiltration, session taint, and risky actions | Runtime enforcement products, not shared evidence networks or Agent ID reputation systems |
| [Cisco skill-scanner](https://github.com/cisco-ai-defense/skill-scanner/), [Husk](https://husk.zone/), [STSS](https://github.com/kenhuangus/stss) | Scan agent skills for prompt injection, credential theft, malicious code, exfiltration, and supply-chain risk; some produce signed attestations | Artifact/supply-chain scanners rather than arbitrary page/payment-instruction scanning |
| [skillreg](https://github.com/kon-rad/skillreg) | Signed, immutable, hash-pinned agent-skill versions with community `clean`/`warn`/`malicious` ratings; each user chooses which raters to trust | Strong evidence-registry analogue, but scoped to skills rather than arbitrary content/payment decisions, and not Agent ID-native |
| [LobSec](https://lobsec.org/) / [Phylax](https://github.com/praxi-labs/phylax-subnet) | Scan agents, skills, plugins, contracts, packages, or MCP servers and issue signed or on-chain attestations | Attest agents/artifacts/code hashes rather than individual untrusted content artifacts encountered before payment or approval |

Most of these projects are early, but they validate the problem and raise the
innovation bar. Elcaro cannot credibly claim novelty merely for detecting
prompt injection in agent-read content.

### Crowded BNB contract/mint-safety cluster

The original generic "safety oracle" lane is also already occupied inside the
hackathon ecosystem:

| Project | Overlap |
|---|---|
| [AgentGuard](https://boltbook.fun/alphapedia/agentguard?lang=en) | Agent ID-gated on-chain safety verdicts for contracts, with aggregate `check()` reads and seeded audit evidence |
| [Mint Guardian](https://github.com/ls4825783/mint-guardian) | Agent ID-gated reports and endorsements for BSC free mints |
| [Preflight](https://github.com/idrfxvdr/preflight) | Falsifiable safety claims backed by Agent ID, with settlement over time |
| [AgentProof](https://github.com/belski21-growl/AgentProof) | Agent ID-gated attestations and evidence hashes for security-verified free-mint contracts |
| [MultiScreenAI Safety Pack](https://www.multiscreenai.com/agents) | Paid MCP/REST token, scam-link, and deployer checks on BNB Chain over x402/B402 |

### Remaining wedge

The defensible wedge is therefore narrower:

> **Agent ID-bound, BNB-native public evidence memory for instruction-safety
> verdicts.** The innovation is not the detector; it is the identity-weighted,
> queryable provenance layer that lets one agent's validated detection become
> another agent's pre-action warning.

That memory can cover hidden instructions in project pages, mint instructions,
README/skill files, shared prompts, x402 resource descriptions, and other text
an agent reads before acting. It must be positioned as evidence-backed signal,
not a guarantee or a generic contract-risk score.

## Strategic fit

| Elcaro goal | Fit | Notes |
|---|---:|---|
| Protect what agents read before they act | **High** | Direct vertical expression of the core mission. |
| Signed, evidence-backed verdicts | **High** | Reports can anchor scan hashes and signed-verdict evidence rather than opinions. |
| Competitive novelty | **Medium-low** | Detection alone is already covered by TollWarden, Sunglasses, agent firewalls, and skill scanners; novelty depends on the Agent ID-bound public evidence memory. |
| Gateway adoption | **Low-medium** | Not inherently a Gateway integration; must expose query/scan through the existing API/MCP surfaces rather than become a detached demo. |
| Paid agent-native usage | **Medium, later** | BNB x402 is real, but not MVP. Payment complexity is separable from the hackathon requirement. |
| Feedback loop | **Medium** | Useful only if reports/corroborations become reviewable labels and regression specimens. |
| Roadmap focus | **Mixed** | Acceptable as a time-boxed distribution experiment; unacceptable if it becomes another standalone event project. |

This must remain consistent with
[roadmap-gateway.md](roadmap-gateway.md): event work should use the existing
scanning/Gateway/evidence surfaces, not create a new product beside them.

## Recommended scope — smallest credible entry

1. **Ownerless public evidence-memory contract.** Append-only reports:
   subject hash, subject type, verdict, scan/evidence hash, scanner version,
   evidence URI, reporter identity, timestamp. No token, no staking, no
   payments in the contract, no owner-editable verdicts.
2. **Agent ID as reputation identity, not just a login gate.** Key reports by
   the reporter's Agent ID identity (token id or handle hash) and enforce one
   report per identity per exact subject. Multiple holders can then naturally
   corroborate or contradict one another; trust aggregation should happen in
   the querier, not through owner-controlled scoring. Reverse resolution may be
   used for display. Do not provide a name→wallet lookup feature.
3. **Exact-version semantics.** Bind reports to an exact content/instruction
   hash and timestamp. Do not smear a verdict across mutable URLs, new skill
   versions, or unrelated artifacts. A changed page is a new subject requiring
   fresh evidence.
4. **Scan input stays safe.** Accept pasted content or text extracted through
   the existing third-party extraction path. Do not fetch arbitrary URLs from
   the Elcaro server; that preserves the current SSRF boundary.
5. **Publish evidence, not raw content.** Anchor scan hash + signed verdict
   metadata + a redacted evidence URI. Do not put user content or sensitive
   payloads on-chain.
6. **Query surface.** Small UI plus REST/MCP lookup: an agent can ask whether a
   project/page/instruction artifact already has anchored warnings, who
   reported them, what evidence hash they committed to, and whether other
   Agent ID holders corroborate or dispute them. Registry output and evidence
   URIs must remain untrusted data, never instructions to the querying agent.
7. **Judge path.** Malicious project/skill/payment instruction → Elcaro scan →
   signed quarantine verdict → Agent ID holder anchors warning → second agent
   queries the warning and refuses the action. The demo must make the shared
   memory/provenance layer obvious, not just show that Elcaro can scan text.

## Explicitly out of scope for the hackathon MVP

- BNB x402 payment integration. It does not help the 30-contract-interaction
  requirement and adds unnecessary cryptographic/facilitator work.
- Contract audits, token-risk scores, honeypot simulation, trading signals, or
  claims that a contract is "safe".
- Server-side fetching of arbitrary URLs.
- Owner-editable labels, token incentives, referrals, streaks, badges, or
  volume manipulation.
- Any attempt to bypass user confirmation, collect credentials, or implement a
  QR/pairing-code login flow.
- Using "Binance" or "BNB" as the product brand. The product remains Elcaro;
  "on BNB Chain" is descriptive only.
- Positioning prompt-injection scanning itself as novel. TollWarden,
  Sunglasses, agent firewalls, and skill scanners already cover parts of that
  detection surface.

## Why x402 is deferred

BNB Chain x402/B402 is real: Binance's
[Agentic Payments docs](https://developers.binance.com/en/docs/products/onchainpay-x402/introduction)
list U/USD1 with EIP-3009 and Permit2 paths, while Binance-Peg USDT/USDC use
Permit2. That is materially different from Elcaro's current Base-only,
six-decimal EIP-3009 implementation in `core/x402.py` and
[docs/x402-gateway.md](x402-gateway.md). BSC stablecoins use 18 decimals, and
USDT/USDC require a Permit2 flow. Supporting that correctly is a separate
payments project, not a hackathon MVP dependency.

TollWarden also already occupies much of the general x402 payment-firewall
lane on Base, including payment-provenance scanning, signed verdicts, and
counterparty reporting. That is another reason not to make "we scan x402" the
innovation claim. If BNB x402 is ever added, it should complement the evidence
memory rather than clone a payment firewall.

If added later, prefer the official B402/x402 client or facilitator integration
over ad-hoc modification of the current verifier, and only after the report
contract + query path + distribution plan are already working.

## Go / no-go gate

Enter only if all five are true within 48 hours of starting:

1. **Focus:** the current conversion/deploy work is either finished or
   deliberately deferred; this does not silently displace it.
2. **Technical proof:** scan → signed verdict → contract report → query works
   end-to-end in a local/test deployment.
3. **Distribution proof:** there is a credible path to 50+ genuine Agent ID
   interactions, with at least 10–15 concrete holders/partners/communities
   identified. No fabricated accounts or paid volume.
4. **Scope proof:** the entry does not depend on x402, contract auditing, or
   new detector work.
5. **Differentiation proof:** the demo and submission make the Agent ID-bound
   public evidence memory obviously central. If the demo still reads as merely
   "another prompt-injection scanner" or "another safety registry", skip.

If any gate fails, skip the hackathon and keep this as a watchlist opportunity.

**Outcome (2026-11-27):** declined. Gates 1, 3, and 5 failed: the entry would
displace higher-EV conversion/extension/benchmark work, no concrete Agent ID
holder distribution path was identified, and the differentiation case against
TollWarden + skillreg + the BNB safety-registry cluster was not strong enough
to carry a 30%-weighted "Agent ID application depth" score. The analysis above
is retained because the evidence-memory design remains the right shape if the
opportunity is ever revisited.

## Open questions

- Which exact artifact identifiers should the contract support first:
  content hash, x402 resource hash, skill/repository hash, or all three? A URL
  should probably be metadata, not the primary subject, because pages mutate.
- Should dispute be an explicit verdict type, or is a contradictory report
  from another Agent ID sufficient for the MVP?
- Can we use the existing evidence/redaction format as the evidence URI without
  exposing user-submitted content?
- Which Binance/Agent ID communities or adjacent hackathon projects provide a
  legitimate distribution path?
- Does Binance count only direct wallet transactions, or also account-abstraction
  / meta-transaction patterns, as holder interaction? Assume direct wallet
  interaction unless confirmed otherwise.

## Sources checked 2026-11-27

- Binance Agent ID Hackathon announcement and rules:
  <https://binancehub.co.kr/en/notice/290513/>
- SPACE ID Agent ID resolution and contract interface:
  <https://docs.space.id/agent-id>
- Binance Agentic Wallet skill security policy:
  <https://raw.githubusercontent.com/binance/binance-skills-hub/main/skills/binance-web3/binance-agentic-wallet/SKILL.md>
- Binance Agentic Wallet x402 payment skill:
  <https://www.binance.com/en/blog/ecosystem/969044993833612571>
- Binance Agentic Payments / B402 supported assets and methods:
  <https://developers.binance.com/en/docs/products/onchainpay-x402/introduction>
- PayAI BSC x402 network notes:
  <https://docs.payai.network/x402/supported-networks>
- BAS Agent ID index:
  <https://www.agent.bas.io/agent/api/binance-agent-id/general>
- SecurityWeek on prompt-injection crypto-payment campaigns:
  <https://www.securityweek.com/prompt-injection-attacks-trick-ai-agents-into-making-crypto-payments>
- TollWarden x402 payment firewall and benchmark:
  <https://github.com/tollwarden/tollwarden> ·
  <https://tollwarden.com/guides/prompt-injection-benchmark>
- Sunglasses input-firewall documentation:
  <https://sunglasses.dev/documentations>
- skillreg immutable agent-skill registry:
  <https://github.com/kon-rad/skillreg>
- Agent-skill scanning/attestation references:
  <https://github.com/cisco-ai-defense/skill-scanner/> ·
  <https://husk.zone/> ·
  <https://github.com/kenhuangus/stss> ·
  <https://lobsec.org/> ·
  <https://github.com/praxi-labs/phylax-subnet>
