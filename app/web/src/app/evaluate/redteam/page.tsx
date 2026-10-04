import type { Metadata } from "next";
import { RedteamRunner } from "@/components/redteam-runner";

export const metadata: Metadata = {
  title: "The Red Team",
  description:
    "Elcaro attacks itself — watch an evolutionary adversarial searcher mutate the attack corpus and hunt for bypasses against the live detection engine.",
};

export default function RedteamPage() {
  return <RedteamRunner />;
}
