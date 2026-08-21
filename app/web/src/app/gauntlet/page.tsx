import type { Metadata } from "next";
import { GauntletRunner } from "@/components/gauntlet-runner";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";

export const metadata: Metadata = {
  title: "The Gauntlet",
  description:
    "Eight payloads, one click: watch Elcaro catch all six classes of indirect prompt injection — live, against the production engine.",
};

export default function GauntletPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader active="gauntlet" />

      {/* Main content */}
      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-8">
        <GauntletRunner />
      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
