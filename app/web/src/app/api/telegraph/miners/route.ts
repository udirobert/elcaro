import { NextResponse } from "next/server";

// Live catalog from the Telegraph node — free discovery, no x402.
// Track 3 requires using Telegraph miners; this is the source of truth
// for who is actually routable, not a hardcoded list.
const ENGINE_URL =
  process.env.TELEGRAPH_ENGINE_URL || "https://devnode.telegraphprotocol.com";

export async function GET(request: Request) {
  const intent =
    new URL(request.url).searchParams.get("intent") || "CONTENT_MODERATION";

  try {
    const res = await fetch(
      `${ENGINE_URL.replace(/\/$/, "")}/api/miners?intent=${encodeURIComponent(intent)}`,
      {
        cache: "no-store",
        headers: { "User-Agent": "elcaro-web/0.1 (telegraph-catalog)" },
      }
    );

    if (!res.ok) {
      return NextResponse.json(
        { error: "Catalog unavailable", detail: await res.text() },
        { status: 503 }
      );
    }

    const data = await res.json();
    const miners = Array.isArray(data)
      ? data
      : data.miners || data.data || [];

    return NextResponse.json({
      intent,
      source: `${ENGINE_URL}/api/miners`,
      miners: miners.map(
        (m: {
          id?: string;
          slug?: string;
          name?: string;
          activation_status?: string;
          endpoints?: { path?: string; method?: string }[];
        }) => ({
          id: m.id,
          slug: m.slug,
          name: m.name,
          activation_status: m.activation_status,
          endpoints: (m.endpoints || []).map((e) => ({
            path: e.path,
            method: e.method,
          })),
        })
      ),
    });
  } catch {
    return NextResponse.json(
      { error: "Catalog unreachable" },
      { status: 503 }
    );
  }
}
