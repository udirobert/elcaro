import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";

const satoshi = localFont({
  src: [
    { path: "../../public/fonts/satoshi-400.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/satoshi-500.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/satoshi-700.woff2", weight: "700", style: "normal" },
    { path: "../../public/fonts/satoshi-900.woff2", weight: "900", style: "normal" },
  ],
  variable: "--font-satoshi",
  display: "swap",
  preload: true,
  fallback: ["system-ui", "sans-serif"],
});

const mono = JetBrains_Mono({
  variable: "--font-mono-src",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

// metadataBase drives all absolute OG/Twitter image URLs. Priority:
//   1. NEXT_PUBLIC_APP_URL — set it (e.g. https://elcaro.trustfall.xyz) once the
//      custom domain is live so every shared link points at the real domain.
//   2. NEXT_PUBLIC_URL — a Netlify-injected env var, auto-prefixed with https://.
//   3. https://elcaro.netlify.app — the current live deploy URL, so OG images
//      resolve correctly TODAY with zero configuration. (The old metadataBase
//      pointed at elcaro.trustfall.xyz, which doesn't resolve yet → blank
//      previews in every tweet/Slack/LinkedIn share.)
const appUrl =
  process.env.NEXT_PUBLIC_APP_URL ||
  (process.env.NEXT_PUBLIC_URL
    ? `https://${process.env.NEXT_PUBLIC_URL}`
    : "https://elcaro.netlify.app");

export const metadata: Metadata = {
  metadataBase: new URL(appUrl),
  title: {
    default: "Elcaro — see what your agent can't",
    template: "%s · Elcaro",
  },
  description:
    "Detect indirect prompt injection in content retrieved by AI agents. Scan emails, search results, documents, and web pages before your agent processes them.",
  openGraph: {
    title: "Elcaro — see what your agent can't",
    description:
      "Prompt injection detection for autonomous agents. Six technique classes. Sub-10ms response. Open source.",
    type: "website",
    siteName: "Elcaro",
    locale: "en_US",
    url: appUrl,
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
  other: {
    webmcp: "/.well-known/webmcp.json",
  },
};

interface LayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: LayoutProps) {
  return (
    <html lang="en" className={`${satoshi.variable} ${mono.variable}`}>
      <body className="min-h-dvh bg-canvas text-ink font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
