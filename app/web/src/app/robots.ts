import type { MetadataRoute } from "next";

const appUrl =
  process.env.NEXT_PUBLIC_APP_URL ||
  (process.env.NEXT_PUBLIC_URL
    ? `https://${process.env.NEXT_PUBLIC_URL}`
    : "https://elcaro.netlify.app");

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/scan", "/integrate"],
        // API routes are not pages — no value crawling them
        disallow: ["/api/"],
      },
    ],
    sitemap: `${appUrl}/sitemap.xml`,
  };
}
