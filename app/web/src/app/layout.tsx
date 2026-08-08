import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Elcaro — see what your agent can't",
  description:
    "Indirect prompt injection detection for AI agents. Scan content before your agent processes it.",
  openGraph: {
    title: "Elcaro — see what your agent can't",
    description:
      "Detect hidden instructions in content retrieved by AI agents.",
    type: "website",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${mono.variable}`}>
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
