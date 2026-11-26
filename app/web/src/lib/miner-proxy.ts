/**
 * Shared forwarding contract between the public Next API routes and the
 * miner. ELCARO_INTERNAL_PROXY_TOKEN must be configured in BOTH Netlify and
 * the miner's VPS env. Without it the miner correctly treats these routes as
 * ordinary untrusted clients.
 */

export function clientIpFromRequest(request: Request): string | null {
  // Netlify's platform header is preferable to client-influenced XFF entries.
  const netlifyIp = request.headers.get("x-nf-client-connection-ip")?.trim();
  if (netlifyIp) return netlifyIp;
  const xff = request.headers.get("x-forwarded-for");
  if (xff) {
    const first = xff.split(",")[0]?.trim();
    if (first) return first;
  }
  return request.headers.get("x-real-ip")?.trim() || null;
}

export function minerForwardHeaders(
  request: Request,
  { premium }: { premium: boolean },
): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = process.env.ELCARO_INTERNAL_PROXY_TOKEN?.trim();
  if (!token) return headers;

  headers["x-elcaro-internal-token"] = token;
  headers["x-elcaro-premium"] = premium ? "1" : "0";
  const clientIp = clientIpFromRequest(request);
  if (clientIp) headers["x-elcaro-client-ip"] = clientIp;
  return headers;
}

export function rateLimitPassthroughHeaders(minerResponse: Response): HeadersInit {
  const headers = new Headers({ "cache-control": "no-store" });
  const retryAfter = minerResponse.headers.get("retry-after");
  const limit = minerResponse.headers.get("x-ratelimit-limit");
  const remaining = minerResponse.headers.get("x-ratelimit-remaining");
  if (retryAfter) headers.set("retry-after", retryAfter);
  if (limit) headers.set("x-ratelimit-limit", limit);
  if (remaining) headers.set("x-ratelimit-remaining", remaining);
  return headers;
}
