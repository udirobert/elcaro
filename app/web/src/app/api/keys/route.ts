import { NextRequest, NextResponse } from "next/server";

import { issueKey, keyInfo, meteringConfigured, revokeKey } from "@/lib/keys";

/**
 * Self-service Elcaro key management for /keys.
 *
 *   POST   { label? }        → mints a key, returns the raw key ONCE
 *   GET    ?key=<raw>        → config + 30d usage (raw key is the auth)
 *   DELETE ?key=<raw>        → revoke (owner proves possession)
 *
 * Raw keys never persist — only sha256(raw) reaches Neon (contract C2).
 * 503 when no metering DSN is configured.
 */

function unavailable() {
  return NextResponse.json(
    { error: "Key service not configured (no metering DSN)" },
    { status: 503 }
  );
}

export async function POST(req: NextRequest) {
  if (!meteringConfigured()) return unavailable();
  let label = "";
  try {
    const body = await req.json();
    if (typeof body?.label === "string") label = body.label.slice(0, 120);
  } catch {
    // empty body is fine — label is optional
  }
  const minted = await issueKey(label);
  if (!minted) {
    return NextResponse.json({ error: "Key issuance failed" }, { status: 502 });
  }
  return NextResponse.json(
    { key: minted.rawKey, key_id: minted.keyId, prefix: minted.prefix },
    { status: 201 }
  );
}

export async function GET(req: NextRequest) {
  if (!meteringConfigured()) return unavailable();
  const key = req.nextUrl.searchParams.get("key") ?? "";
  if (!key.startsWith("elk_")) {
    return NextResponse.json({ error: "pass ?key=elk_…" }, { status: 400 });
  }
  const info = await keyInfo(key);
  if (!info) {
    return NextResponse.json({ error: "Unknown or revoked key" }, { status: 404 });
  }
  return NextResponse.json({
    key_id: info.keyId,
    prefix: info.prefix,
    label: info.label,
    mode: info.mode,
    upstream: info.upstream,
    deep_analysis: info.deepAnalysis,
    created_at: info.createdAt,
    usage_30d: info.usage30d,
  });
}

export async function DELETE(req: NextRequest) {
  if (!meteringConfigured()) return unavailable();
  const key = req.nextUrl.searchParams.get("key") ?? "";
  if (!key.startsWith("elk_")) {
    return NextResponse.json({ error: "pass ?key=elk_…" }, { status: 400 });
  }
  const revoked = await revokeKey(key);
  if (revoked === null) {
    return NextResponse.json({ error: "Revoke failed" }, { status: 502 });
  }
  if (!revoked) {
    return NextResponse.json({ error: "Unknown or revoked key" }, { status: 404 });
  }
  return NextResponse.json({ revoked: true });
}
