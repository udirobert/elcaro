import type { Metadata } from "next";
import { GauntletRunner } from "@/components/gauntlet-runner";

export const metadata: Metadata = {
  title: "The Gauntlet",
  description:
    "Nine payloads, one click: watch Elcaro catch all seven classes of indirect prompt injection — live, against the production engine.",
};

export default function GauntletPage() {
  return <GauntletRunner />;
}
