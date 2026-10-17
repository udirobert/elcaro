import { PayboxGauntlet } from "@/components/paybox-gauntlet";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "The PayBox Gauntlet",
  description:
    "Six agentic-commerce scenarios — one per PayBox Ch.1 rubric category — where a single injected paragraph steers a real PayBox tool toward the vault. Every gate is a paid call through a PayBox wallet.",
};

export default function PayboxPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      <SiteHeader />

      <div className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">
        <PayboxGauntlet />
      </div>

      <SiteFooter />
    </main>
  );
}
