import type { Metadata } from "next";
import Link from "next/link";
import { IntegrateForm } from "@/components/integrate-form";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";

export const metadata: Metadata = {
  title: "Integrate",
  description:
    "Add Elcaro to your agent's retrieval pipeline. Direct API, Python middleware, or Telegraph routing — five lines of code.",
};

const CODE_API = `curl -X POST https://api.elcaro.trustfall.xyz/scan \\
  -H "Content-Type: application/json" \\
  -d '{
    "content": "<the content your agent retrieved>",
    "content_type": "email"
  }'`;

const CODE_MIDDLEWARE = `# NOTE: the Python SDK isn't on PyPI yet — these imports assume
# you've cloned the repo so app/ and core/ are importable from your
# project root (starter in app/middleware.py). To call Elcaro without
# a repo checkout, use the Direct API in Option 01 instead.
from app.middleware import ElcaroMiddleware
from core import ContentType

# Point at the live miner or run locally
guard = ElcaroMiddleware(
    miner_url="https://api.elcaro.trustfall.xyz"
)

# In your agent's retrieval step
result = await guard.scan(retrieved_content, ContentType.EMAIL)

if result.is_safe():
    agent.process(result.safe_content)
else:
    agent.warn(f"Blocked: {result.reason}")`;

const CODE_TELEGRAPH = `# The miner is registered on Telegraph as id 8848.
# Any Telegraph client can route to it directly:

POST https://devnode.telegraphprotocol.com/engine/v1/ask/8848
Content-Type: application/json
x-payment: <x402 USDC payment>

{
  "method": "POST",
  "endpoint": "/scan",
  "payload": {
    "content": "<retrieved content>",
    "content_type": "email"
  }
}`;

const PRINCIPLES = [
  {
    rule: "Scan before act, not after.",
    why: "The injection has already influenced the agent if you scan the output. The only safe point is between retrieval and reasoning.",
  },
  {
    rule: "Treat email as highest-risk.",
    why: "Untrusted sender, structured enough to carry injection reliably, real-world consequences. Email content should always be scanned — no exceptions.",
  },
  {
    rule: "Threshold at 0.5 to block, 0.3 to flag.",
    why: "Score ≥ 0.5 is suspicious or dangerous — quarantine it. Score ≥ 0.3 warrants a second look but not necessarily a full block. Never let score 0.7+ through.",
  },
  {
    rule: "Pass content_type explicitly.",
    why: "Elcaro weights risk by content provenance. An email scores differently than code from your own repo. The default is 'document' — be specific.",
  },
  {
    rule: "Log every quarantined result.",
    why: "The flagged_techniques and indicators fields are structured and machine-readable. Log them — they're the audit trail that proves your agent was protected.",
  },
];

function CodeBlock({ code, language = "bash" }: { code: string; language?: string }) {
  return (
    <div className="rounded-xl bg-ink text-canvas font-mono text-xs leading-relaxed overflow-x-auto">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/10">
        <span className="text-[10px] text-white/40 uppercase tracking-widest">
          {language}
        </span>
      </div>
      <pre className="p-4 whitespace-pre overflow-x-auto">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function Section({
  number,
  title,
  children,
}: {
  number: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-3">
        <span className="text-xs font-mono text-ink-faint">{number}</span>
        <h2 className="text-lg font-bold text-ink">{title}</h2>
      </div>
      {children}
    </div>
  );
}

export default function IntegratePage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader active="integrate" />

      <div className="flex-1 max-w-2xl mx-auto w-full px-6 py-14 space-y-16">

        {/* Hero */}
        <div className="space-y-4">
          <h1 className="text-3xl font-black tracking-tight text-ink">
            Add Elcaro to your agent
          </h1>
          <p className="text-base text-ink-muted leading-relaxed max-w-lg">
            One scan call between your agent&apos;s retrieval step and its
            reasoning loop. Under 2ms. No API key. Works today.
          </p>
          <div className="flex items-center gap-3 pt-1">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-safe bg-safe-bg px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-safe" />
              Live on Telegraph Protocol
            </span>
            <span className="text-xs text-ink-faint font-mono">
              id 8848 · registrationId 145
            </span>
          </div>
        </div>

        {/* Option 1 — Direct API */}
        <Section number="01" title="Direct API call">
          <p className="text-sm text-ink-muted leading-relaxed">
            No SDK, no signup. POST the content your agent just retrieved and
            get a structured verdict back. Works from any language or runtime.
          </p>
          <CodeBlock code={CODE_API} language="bash" />
          <p className="text-xs text-ink-faint leading-relaxed">
            Returns{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              risk_score
            </code>
            ,{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              risk_level
            </code>
            ,{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              flagged_techniques
            </code>
            , and a full{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              indicators
            </code>{" "}
            array with matched text, confidence, MITRE TTPs, and
            remediation. Structured for machine consumption — log it or act on
            it.
          </p>
        </Section>

        {/* Option 2 — Python middleware */}
        <Section number="02" title="Python middleware (5 lines)">
          <p className="text-sm text-ink-muted leading-relaxed">
            Drop-in wrapper for Python agents. Wraps your retrieval step,
            quarantines high-risk content, and returns a{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              ScanResult
            </code>{" "}
            with{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              is_safe()
            </code>{" "}
            and the original or sanitised content.
          </p>
          <CodeBlock code={CODE_MIDDLEWARE} language="python" />
          <p className="text-xs text-ink-faint leading-relaxed">
            Three quarantine modes:{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              replace
            </code>{" "}
            (default — substitutes a structured notice),{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              block
            </code>{" "}
            (returns empty content), or{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              warn
            </code>{" "}
            (passes through with a warning appended). Source in{" "}
            <a
              href="https://github.com/udirobert/elcaro/blob/main/app/middleware.py"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-ink transition-colors"
            >
              app/middleware.py
            </a>
            .
          </p>
        </Section>

        {/* Option 3 — Telegraph */}
        <Section number="03" title="Via Telegraph Protocol">
          <p className="text-sm text-ink-muted leading-relaxed">
            If you&apos;re already building on{" "}
            <a
              href="https://telegraphprotocol.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-ink transition-colors"
            >
              Telegraph
            </a>
            , Elcaro is a registered miner. Route to it directly by id, or let
            Telegraph&apos;s auto-router pick it for{" "}
            <code className="font-mono bg-surface border border-border px-1 rounded text-ink-muted">
              CONTENT_MODERATION
            </code>{" "}
            intents. Payment is per-request in USDC via x402.
          </p>
          <CodeBlock code={CODE_TELEGRAPH} language="http" />
        </Section>

        {/* Best practices */}
        <Section number="04" title="Five rules for safe agent pipelines">
          <div className="space-y-0 divide-y divide-border">
            {PRINCIPLES.map((p, i) => (
              <div key={i} className="py-4 grid grid-cols-[1fr_1.4fr] gap-8 items-start">
                <p className="text-sm font-semibold text-ink leading-snug">
                  {p.rule}
                </p>
                <p className="text-sm text-ink-muted leading-relaxed">
                  {p.why}
                </p>
              </div>
            ))}
          </div>
        </Section>

        {/* Email capture */}
        <IntegrateForm />

        {/* Path back into the product — don't end on a form */}
        <p className="text-center text-sm text-ink-muted">
          Want to see it work first?{" "}
          <Link
            href="/gauntlet"
            className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80 transition-colors"
          >
            See it catch something →
          </Link>
        </p>

      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
