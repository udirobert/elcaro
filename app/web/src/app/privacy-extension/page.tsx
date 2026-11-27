import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";

export const metadata: Metadata = {
  title: "IPI Guard for Gmail — privacy policy",
  description:
    "Privacy policy for the Elcaro IPI Guard Gmail extension: what is scanned, what is never stored, and what stays on your machine.",
};

const sections: { heading: string; body: string }[] = [
  {
    heading: "What we receive",
    body: "When you click Scan (or press the shortcut), the text of the Gmail message currently open in your browser is sent over HTTPS to the Elcaro scan service (elcaro.trustfall.xyz) for analysis.",
  },
  {
    heading: "What we do with it",
    body: "The text is analyzed in memory for indirect prompt injection techniques and the verdict is returned to your browser. Message content is never written to disk, logged, or stored on the server.",
  },
  {
    heading: "What we never do",
    body: "We do not read your inbox. We do not scan in the background. We do not sell, share, or mine message content. There is no account, no tracking, no analytics, and no advertising.",
  },
  {
    heading: "What stays on your machine",
    body: "Scan history (verdict band, score, date) is kept in your browser's local storage so the popup can show your day at a glance. It never leaves your browser and can be erased at any time from the popup (\u201cClear history\u201d).",
  },
  {
    heading: "Contact",
    body: "github.com/udirobert/elcaro — issues welcome.",
  },
];

export default function PrivacyExtensionPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      <SiteHeader />
      <div className="flex-1 max-w-2xl mx-auto w-full px-6 py-10 space-y-8">
        <div className="space-y-2">
          <p className="text-sm text-ink-muted">Elcaro IPI Guard for Gmail</p>
          <h1 className="text-3xl font-semibold tracking-tight">Privacy policy</h1>
        </div>
        {sections.map((s) => (
          <section key={s.heading} className="space-y-2">
            <h2 className="text-lg font-medium">{s.heading}</h2>
            <p className="text-base text-ink-muted leading-relaxed">{s.body}</p>
          </section>
        ))}
      </div>
      <SiteFooter />
    </main>
  );
}
