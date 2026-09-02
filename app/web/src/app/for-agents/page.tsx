import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { PageHeader } from "@/components/page-header";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Designing for agents",
  description:
    "How to treat AI agents as first-class users of your website — llms.txt, structured responses, signed data, and test specimens.",
};

function Principle({
  number,
  title,
  body,
  practice,
}: {
  number: string;
  title: string;
  body: string;
  // Proof, not promise — a link to the Elcaro surface that practices the
  // principle. Faint mono line under the body, always visible (hover-only
  // affordances don't exist on touch).
  practice?: { label: string; href: string; external?: boolean };
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline gap-3">
        <span className="text-xs font-mono text-ink-faint">{number}</span>
        <h2 className="text-lg font-bold text-ink">{title}</h2>
      </div>
      <p className="text-sm text-ink-muted leading-relaxed pl-7">{body}</p>
      {practice && (
        <p className="pl-7">
          <Link
            href={practice.href}
            target={practice.external ? "_blank" : undefined}
            rel={practice.external ? "noopener noreferrer" : undefined}
            className="text-[11px] font-mono text-ink-faint hover:text-violet transition-colors"
          >
            we practice this: {practice.label} →
          </Link>
        </p>
      )}
    </div>
  );
}

export default function ForAgentsPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      <SiteHeader active="for-agents" />

      <div className="flex-1 max-w-2xl mx-auto w-full px-6 py-14 space-y-12">
        <PageHeader eyebrow="Agent-first surfaces · elcaro" title="Designing for agents">
          <p className="text-base text-ink-muted leading-relaxed">
            AI agents are becoming a user class alongside humans — they browse,
            retrieve, summarize, and act on web content. But almost no site
            designs for them. Here&apos;s what we&apos;ve learned building Elcaro, and
            what we practice on our own surfaces.
          </p>
        </PageHeader>

        <div className="stagger-children space-y-12">
        <Principle
          number="01"
          title="Publish an llms.txt"
          body="A plain-text file at /llms.txt that tells agents what your product is, what your API does, and how to discover your tools. It's the machine-readable equivalent of a landing page. Ours describes the scan API, the MCP server, the specimen kit, and the quarantine doctrine — all in one fetch."
          practice={{ label: "/llms.txt", href: "/llms.txt" }}
        />

        <Principle
          number="02"
          title="Return structured data, not just HTML"
          body="An agent consuming your API should get JSON with typed fields, not prose to parse. Elcaro's verdicts carry risk_score, risk_level, flagged_techniques with evidence, TTP mappings, and remediation — structured by construction, so agents can act on them without scraping."
          practice={{ label: "POST /scan returns the verdict", href: "/integrate" }}
        />

        <Principle
          number="03"
          title="Sign what you can; treat in-band text as display"
          body="In-band text — content inside the agent's input stream — is spoofable. An attacker can write a fake 'quarantine notice' or 'scan result' into a page. If your product produces text that agents trust, sign it: Ed25519 over a canonical payload, with a public key at a stable URL. The signature is the trust signal; the text is for reading."
          practice={{ label: "GET /pubkey · POST /verify", href: "/integrate" }}
        />

        <Principle
          number="04"
          title="Write copy for the machine reader"
          body="Every piece of text an agent consumes is UX copy for a machine. Elcaro's quarantine notice is two registers: agent instruction and human summary. Write it deliberately, version it, and test it against adversarial readers."
        />

        <Principle
          number="05"
          title="Publish test specimens"
          body="A page of inert, clearly-marked test fixtures at a fixed URL — the 'EICAR file' for your domain. Agents, IDEs, and guard hooks can fetch it to verify detection works end-to-end. Elcaro's specimen kit is plain UTF-8, no JavaScript, and explicitly safe for agents to read."
          practice={{ label: "the specimen kit", href: "/specimen" }}
        />

        <Principle
          number="06"
          title="Expose an MCP server"
          body="The Model Context Protocol is the default integration path for agent frameworks. Expose your core capability as MCP tools with descriptions written for the model choosing tools, not the human reading docs. Tool descriptions are distribution copy."
          practice={{ label: "app/mcp_server.py", href: "https://github.com/udirobert/elcaro/blob/main/app/mcp_server.py", external: true }}
        />

        <Principle
          number="07"
          title="Expose WebMCP tools on the human UI"
          body="WebMCP (W3C WebML Community Group draft, implemented in ChatGPT’s in-app browser and behind chrome://flags/#enable-webmcp-testing) lets a site register JavaScript tools with document.modelContext.registerTool. Elcaro’s /scan playground registers scan_content, load_specimen, list_specimens, explain_verdict, and contrast_intent. The last one is the joint review: the agent declares the action it was about to take; the human sees that next to what the hidden instruction asked for. Stdio MCP remains for IDEs; it is not a substitute. See docs/webmcp.md."
          practice={{ label: "the /scan playground", href: "/scan" }}
        />

        <Principle
          number="08"
          title="Be the demo"
          body="If your product serves agents, your own agent-facing surfaces must model the trustworthy patterns whose absence you detect. Elcaro detects authority framing; its own notices must not be authority-framed spoofs. Elcaro detects in-band injection; its own verdicts must be signed. The product is the demo."
        />

        <div className="space-y-3">
          <div className="flex items-baseline gap-3">
            <span className="text-xs font-mono text-ink-faint">09</span>
            <h2 className="text-lg font-bold text-ink">
              Test your own safety assumptions — then publish the data
            </h2>
          </div>
          <div className="space-y-3 pl-7 text-sm text-ink-muted leading-relaxed">
            <p>
              Elcaro&apos;s warn mode passes dangerous content through with a
              notice prepended. That design rested on an untested assumption:
              that the warning actually stops an agent from following the
              injection. So we tested it. Three injection specimens × three
              warning positions (prefix, suffix, sandwich) × three
              instruction-following models (Qwen3-30B, Mistral-Large,
              Llama-3.3-70B) × three repeats — 81 completions, judged by an
              independent model for actual compliance.
            </p>
            <table className="w-full text-sm font-mono border border-border">
              <thead>
                <tr className="text-ink-faint text-xs">
                  <th className="text-left px-3 py-2 border-b border-border">Warning position</th>
                  <th className="text-left px-3 py-2 border-b border-border">Complied with injection</th>
                  <th className="text-left px-3 py-2 border-b border-border">Rate</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="px-3 py-2 border-b border-border">prefix (default)</td>
                  <td className="px-3 py-2 border-b border-border">0 / 27</td>
                  <td className="px-3 py-2 border-b border-border">0.0%</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 border-b border-border">sandwich</td>
                  <td className="px-3 py-2 border-b border-border">0 / 27</td>
                  <td className="px-3 py-2 border-b border-border">0.0%</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 border-b border-border">suffix</td>
                  <td className="px-3 py-2 border-b border-border">3 / 27</td>
                  <td className="px-3 py-2 border-b border-border">11.1%</td>
                </tr>
              </tbody>
            </table>
            <p>
              The warning suppressed compliance in 78 of 81 cases across all
              three model families. All three failures were the same shape:
              warning placed last, authority-framed injection, and the model
              paraphrased the injected &quot;policy&quot; as fact. Our pre-committed
              decision rule (act only on a ≥25-point gap) doesn&apos;t trigger a
              default change — and prefix, the current default, is already the
              best position. One honest caveat: the pre-committed keyword
              scorer saturated (responses that refused still quoted the
              injection&apos;s words), so the numbers above come from a judge-model
              rescore of the saved responses. Methodology and raw JSON:{" "}
              <a
                href="https://github.com/udirobert/elcaro/blob/main/docs/warn-salience-experiment.md"
                target="_blank"
                rel="noopener noreferrer"
                className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80"
              >
                docs/warn-salience-experiment.md
              </a>{" "}
              and{" "}
              <a
                href="https://github.com/udirobert/elcaro/tree/main/eval/results"
                target="_blank"
                rel="noopener noreferrer"
                className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80"
              >
                eval/results/
              </a>
              .
            </p>
          </div>
        </div>
        </div>

        <div className="border-t border-border pt-8">
          <p className="text-sm text-ink-muted leading-relaxed">
            These principles shape Elcaro&apos;s own surfaces — our{" "}
            <a href="/llms.txt" className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80">
              llms.txt
            </a>
            , our{" "}
            <a href="/scan" className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80">
              WebMCP scan tools
            </a>
            , our{" "}
            <a
              href="https://github.com/udirobert/elcaro/blob/main/app/mcp_server.py"
              target="_blank"
              rel="noopener noreferrer"
              className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80"
            >
              MCP server
            </a>
            , our{" "}
            <a href="/specimen" className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80">
              specimen kit
            </a>
            , and our{" "}
            <a href="/integrate" className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80">
              integration guide
            </a>
            . The full design audit is in{" "}
            <a
              href="https://github.com/udirobert/elcaro/blob/main/docs/ux-audit.md"
              target="_blank"
              rel="noopener noreferrer"
              className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80"
            >
              docs/ux-audit.md
            </a>
            .
          </p>
        </div>
      </div>

      <SiteFooter />
    </main>
  );
}
