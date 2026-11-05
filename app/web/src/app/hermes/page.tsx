import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Elcaro for Hermes — the agent flight recorder",
  description:
    "Runtime prompt-injection defense for Hermes agents: every tool result scanned before the model sees it, quarantined content replaced in place, and a hash-chained, signed threat log with canary provenance — a flight recorder no prompt could produce.",
};

function HookStep({ name, role }: { name: string; role: string }) {
  return (
    <div className="rounded-lg border border-border px-4 py-3 space-y-1">
      <p className="font-mono text-xs text-violet">{name}</p>
      <p className="text-xs text-ink-muted leading-relaxed">{role}</p>
    </div>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="space-y-1.5">
      <h3 className="text-sm font-bold text-ink">{title}</h3>
      <p className="text-sm text-ink-muted leading-relaxed">{body}</p>
    </div>
  );
}

// Static reproduction of the Desktop threat-log pane — the same rows the
// plugin renders live, so the page doubles as catalog screenshot material.
function PaneMock() {
  return (
    <div className="rounded-xl border border-border bg-[#161617] p-4 space-y-2 font-mono text-[11px] leading-relaxed">
      <div className="flex items-center justify-between">
        <span className="text-[#ededec] font-semibold text-xs">
          Elcaro threat log
        </span>
        <span className="rounded border border-[#46a758] px-1.5 py-0.5 text-[10px] font-semibold text-[#46a758]">
          chain ✓ 214
        </span>
      </div>
      <p className="text-[#8b8b8e]">3 quarantined / 41 scanned · 38 signed · 1 propagation</p>
      <p className="text-[#e5484d]">◉ honeypot sprung — 1 exfiltration attempt caught</p>
      <div className="rounded border border-[#8e4ec6] px-2 py-1 text-[#8e4ec6]">
        ⚡ 1 propagation edge — an injection resurfaced across tool calls
      </div>
      <div className="space-y-1.5 pt-1">
        <div className="rounded border border-[#e5484d] px-2 py-1.5 space-y-0.5">
          <div className="flex items-center justify-between">
            <span className="text-[#ededec]">read_file</span>
            <span className="flex items-center gap-1.5">
              <span className="text-[#8b8b8e]">14:02:11</span>
              <span className="rounded border border-[#e5484d] px-1.5 py-0.5 text-[10px] font-semibold text-[#e5484d]">
                dangerous 1.00
              </span>
            </span>
          </div>
          <p className="text-[#8b8b8e]">HONEYPOT · decoy_exfiltration · signed</p>
        </div>
        <div className="rounded border border-[#3a3a3d] border-l-[3px] border-l-[#8e4ec6] px-2 py-1.5 space-y-0.5">
          <div className="flex items-center justify-between">
            <span className="text-[#8e4ec6]">⚡ propagation</span>
            <span className="text-[#8b8b8e]">14:02:09</span>
          </div>
          <p className="text-[#8b8b8e]">
            canary elcaro:ipi:7f3a… minted by 9c1e44ab21… (scored 0.91) resurfaced
            in write_file
          </p>
        </div>
        <div className="rounded border border-[#3a3a3d] px-2 py-1.5 space-y-0.5">
          <div className="flex items-center justify-between">
            <span className="text-[#ededec]">browser_navigate</span>
            <span className="flex items-center gap-1.5">
              <span className="text-[#8b8b8e]">14:01:58</span>
              <span className="rounded border border-[#e5484d] px-1.5 py-0.5 text-[10px] font-semibold text-[#e5484d]">
                dangerous 0.91
              </span>
            </span>
          </div>
          <p className="text-[#8b8b8e]">
            quarantined · authority_framing, delimiter_escape · signed
          </p>
        </div>
      </div>
      <p className="border-t border-[#3a3a3d] pt-2 text-[#8b8b8e]">
        ▸ signed receipts (38) — clean scans, verifiable offline
      </p>
    </div>
  );
}

export default function HermesPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      <SiteHeader active="hermes" />

      <div className="flex-1 max-w-5xl mx-auto w-full px-6 py-10 space-y-14">
        <PageHeader eyebrow="Hermes plugin · runtime guard" title="Scanner → enforcement → flight recorder.">
          <p className="max-w-2xl text-sm text-ink-muted leading-relaxed">
            Hermes agents browse the web, read files, and run commands —
            everything those tools return is untrusted. The elcaro plugin
            scans every tool result before it reaches the model, replaces
            quarantined content in place, and writes a hash-chained,
            Ed25519-signed trail of every verdict. Detection is a feature;
            the trail is the product.
          </p>
        </PageHeader>

        <section className="grid gap-10 lg:grid-cols-2 lg:items-start">
          <div className="space-y-5">
            <h2 className="text-lg font-bold text-ink">
              Enforcement happens inside the turn
            </h2>
            <div className="space-y-2">
              <HookStep
                name="transform_tool_result"
                role="Primary lever. Every tool result is scanned before it's appended to conversation; quarantined content is swapped for a signed [CONTENT QUARANTINED] notice — the injection never reaches the model."
              />
              <HookStep
                name="pre_tool_call"
                role="The args lane. write_file / terminal arguments are scanned too, so a model pasting fetched content into a heredoc can't smuggle the payload past the result scan — or persist poison into the repo."
              />
              <HookStep
                name="pre_llm_call"
                role="Backstop. A once-per-turn summary of new quarantines so the agent doesn't retry the fetch or work around withheld content."
              />
            </div>
          </div>
          <PaneMock />
        </section>

        <section className="space-y-6">
          <h2 className="text-lg font-bold text-ink">
            What no prompt or skill could produce
          </h2>
          <div className="grid gap-x-10 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
            <Feature
              title="Provenance edges"
              body="When a canary minted by an earlier scan resurfaces inside new content — another tool result, another session, a write_file payload — the log records an edge: token → origin scan → this scan. The pane shows the injection's propagation path, not just its arrival."
            />
            <Feature
              title="Decoy honeypot"
              body="A service-credentials.env bait file with an installation-unique ELCARO-DECOY-* marker sits in the plugin data dir. The marker inside any scanned result or tool-args payload is a deterministic 1.00 quarantine — proof of exfiltration-in-progress, zero false positives."
            />
            <Feature
              title="Tamper-evident log"
              body="Every entry carries prev_hash → entry_hash over the canonical verdict. /elcaro verify and the pane's chain badge recompute the whole chain — a flight recorder that notices when someone edits the tape."
            />
            <Feature
              title="Signed receipts"
              body="When a signing key is configured, every verdict — including clean scans — is Ed25519-signed over content SHA, score, and timestamp. 'The agent acted because elcaro signed off' becomes a verifiable artifact."
            />
            <Feature
              title="Time-shifted verdicts"
              body="elcaro_explain reads the same log as a forensic tool: identical bytes scored differently across time means enforcement changed; the same source hashing differently means the page changed."
            />
            <Feature
              title="/elcaro calibrate"
              body="Replays the seeded attack & benign corpus in-session — run the attack against yourself and watch the scores land, live in the pane."
            />
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-bold text-ink">Commands</h2>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left text-sm">
              <tbody className="divide-y divide-border">
                {[
                  ["/elcaro", "recent verdicts & quarantine count, in-session"],
                  ["/elcaro <index>", "explain a logged verdict — including its verdict history"],
                  ["/elcaro calibrate", "replay the seeded attack corpus against yourself"],
                  ["/elcaro verify", "recompute the hash chain — tamper check"],
                  ["hermes elcaro log|status|calibrate|verify", "the same trail from the CLI"],
                ].map(([cmd, desc]) => (
                  <tr key={cmd}>
                    <td className="px-4 py-2.5 font-mono text-xs text-ink whitespace-nowrap">
                      {cmd}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-ink-muted">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-ink-faint">
            Fully local: deterministic engine, sub-10 ms verdicts, no network
            by default. Content never leaves the box — only its SHA-256 is
            logged.{" "}
            <a
              href="https://github.com/udirobert/elcaro/tree/main/hermes-plugin"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-ink transition-colors"
            >
              Source →
            </a>
          </p>
        </section>
      </div>

      <SiteFooter />
    </main>
  );
}
