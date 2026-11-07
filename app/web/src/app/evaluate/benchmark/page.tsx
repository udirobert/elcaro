import type { Metadata } from "next";
import { BenchmarkResults } from "@/components/benchmark-results";

export const metadata: Metadata = {
  title: "The IPI Benchmark",
  description:
    "24 indirect-prompt-injection tasks, three deployment conditions, ~2,200 transcripts across frontier and Cohere models: labels don't transfer, the automated warning defends — and a LoRA repair arm proves you can't train it out.",
};

export default function BenchmarkPage() {
  return <BenchmarkResults />;
}
