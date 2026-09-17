import { NextResponse } from "next/server";

const TAVILY_API_KEY = process.env.TAVILY_API_KEY;
const TAVILY_EXTRACT_URL = "https://api.tavily.com/extract";

// A URL-content-extraction provider. Kept as a narrow interface so a second
// provider (Parallel) can be added as an alternative without touching the
// route's request/response contract — same pluggable-provider shape as
// core/serv_reasoner.py / core/jev_reasoner.py on the Python side.
interface ExtractResult {
  content: string;
  provider: "tavily";
  creditsUsed?: number;
}

class ExtractError extends Error {
  status: number;
  constructor(message: string, status = 502) {
    super(message);
    this.status = status;
  }
}

async function extractWithTavily(url: string): Promise<ExtractResult> {
  if (!TAVILY_API_KEY) {
    throw new ExtractError("URL fetching is not configured on this deployment.", 501);
  }

  let response: Response;
  try {
    response = await fetch(TAVILY_EXTRACT_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${TAVILY_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        urls: url,
        format: "markdown",
        extract_depth: "basic",
        timeout: 15,
        include_usage: true,
      }),
      signal: AbortSignal.timeout(20_000),
    });
  } catch (err) {
    throw new ExtractError(
      err instanceof Error ? `Fetch provider unreachable: ${err.message}` : "Fetch provider unreachable",
      502
    );
  }

  if (!response.ok) {
    throw new ExtractError(`Fetch provider returned HTTP ${response.status}`, 502);
  }

  const data = await response.json();
  const failed = data?.failed_results?.[0];
  if (failed) {
    throw new ExtractError(`Could not extract that URL: ${failed.error || "unknown error"}`, 422);
  }

  const result = data?.results?.[0];
  if (!result?.raw_content) {
    throw new ExtractError("Fetch provider returned no content for that URL.", 422);
  }

  return {
    content: result.raw_content,
    provider: "tavily",
    creditsUsed: data?.usage?.credits ?? undefined,
  };
}

function isFetchableUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

// Lets the client know whether to show the "Fetch page content" affordance
// at all, without leaking whether a request will actually be attempted.
export async function GET() {
  return NextResponse.json({ available: Boolean(TAVILY_API_KEY) });
}

export async function POST(request: Request) {
  let body: { url?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  const url = typeof body.url === "string" ? body.url.trim() : "";
  if (!url || !isFetchableUrl(url)) {
    return NextResponse.json(
      { error: "Provide a valid http:// or https:// URL" },
      { status: 400 }
    );
  }

  try {
    const result = await extractWithTavily(url);
    return NextResponse.json({
      content: result.content,
      provider: result.provider,
      credits_used: result.creditsUsed ?? null,
      source_url: url,
    });
  } catch (err) {
    if (err instanceof ExtractError) {
      return NextResponse.json({ error: err.message }, { status: err.status });
    }
    return NextResponse.json({ error: "Unexpected error fetching URL" }, { status: 500 });
  }
}
