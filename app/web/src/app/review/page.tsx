import type { Metadata } from "next";
import { ReviewWorkbench } from "@/components/review-workbench";

export const metadata: Metadata = {
  title: "Blinded review bench",
  description: "Private local-first packet runner for Elcaro human review.",
  robots: { index: false, follow: false },
};

export default function ReviewPage() {
  return <ReviewWorkbench />;
}
