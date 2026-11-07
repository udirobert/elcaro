import type { Metadata } from "next";
import { BenchmarkResults } from "@/components/benchmark-results";

export const metadata: Metadata = {
  title: "The IPI Benchmark",
  description:
    "24 indirect-prompt-injection tasks, two deployment conditions, ~1,300 transcripts: frontier models fall for concealed attacks when content isn't explicitly labeled untrusted — and the Elcaro scanner misses the same newest surfaces.",
};

export default function BenchmarkPage() {
  return <BenchmarkResults />;
}
