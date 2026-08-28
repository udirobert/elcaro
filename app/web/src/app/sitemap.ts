import type { MetadataRoute } from "next";

const appUrl =
  process.env.NEXT_PUBLIC_APP_URL ||
  (process.env.NEXT_PUBLIC_URL
    ? `https://${process.env.NEXT_PUBLIC_URL}`
    : "https://elcaro.netlify.app");

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: appUrl,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${appUrl}/scan`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.9,
    },
    {
      url: `${appUrl}/integrate`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${appUrl}/for-agents`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.7,
    },
  ];
}
