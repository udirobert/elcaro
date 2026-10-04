import type { Metadata } from "next";
import { VulnerableSection } from "@/components/vulnerable-section";

export const metadata: Metadata = {
  title: "Is Your Agent Gullible?",
  description:
    "Paste your agent's system prompt. We'll score how easy it is to hijack with indirect prompt injection — and show you exactly which technique classes it leaves open.",
};

export default function AuditPage() {
  return <VulnerableSection />;
}
