import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: {
    default: "Elcaro — see what your agent can't",
    template: "%s · Elcaro",
  },
  description:
    "Detect indirect prompt injection in content retrieved by AI agents. Scan emails, search results, documents, and web pages before your agent processes them.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://elcaro.trustfall.xyz"
  ),
  openGraph: {
    title: "Elcaro — see what your agent can't",
    description:
      "Prompt injection detection for autonomous agents. Six technique classes. Sub-10ms response. Open source.",
    type: "website",
    siteName: "Elcaro",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Elcaro — see what your agent can't",
    description:
      "Detect hidden instructions in content your AI agent retrieves.",
    creator: "@udirobert",
  },
  keywords: [
    "prompt injection",
    "indirect prompt injection",
    "AI safety",
    "agent security",
    "content scanning",
    "LLM security",
    "Telegraph Protocol",
  ],
  authors: [{ name: "udirobert", url: "https://github.com/udirobert" }],
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={mono.variable}>
      <head>
        <link
          href="https://api.fontshare.com/v2/css?f=satoshi@400,500,700,900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-dvh bg-canvas text-ink">{children}</body>
    </html>
  );
}
