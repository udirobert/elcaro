import type { Metadata } from "next";
import { RedteamRunner } from "@/components/redteam-runner";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";

export const metadata: Metadata = {
  title: "The Red Team",
  description:
    "Elcaro attacks itself — watch an evolutionary adversarial searcher mutate the attack corpus and hunt for bypasses against the live detection engine.",
};

export default function RedteamPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader active="redteam" />

      {/* Main content */}
      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8">
        <RedteamRunner />
      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
