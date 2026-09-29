// Elcaro IPI Guard — background service worker (MV3).
//
// Two rails:
//
//   engine (default) — POST <bridge>/api/engine-ask { "query": "<nl>" }
//     Auto-routed Telegraph traffic: the bridge forwards to
//     /engine/v1/ask and answers the x402 402 challenge server-side
//     (EIP-3009 exact scheme over Base Sepolia USDC). This is the rail that
//     counts as miner volume. The extension needs no wallet; the bridge holds
//     the paying key and is gated by origin allowlist + optional token + a
//     daily ask cap.
//
//   direct — POST /engine/v1/ask/8848 { method, endpoint, payload }
//     Same protocol host, but names the miner. Works without routing, still
//     x402-paid, and does NOT count as miner volume. Unpaid here: it remains
//     as the development fallback and will surface 402 in the overlay.

// Where the bridge lives. Override for local dev:
//   chrome.storage.local.set({ bridge: "http://localhost:3000" })
const DEFAULT_BRIDGE = "https://elcaro.trustfall.xyz";

const DIRECT_URL =
  "https://devnode.telegraphprotocol.com/engine/v1/ask/8848";

// Question polarity matters: the miner commits its verdict first and the
// scoring modules grade the verdict, so ask a yes/no injection question.
function buildQuery(content, contentType) {
  return (
    "Is the following untrusted " +
    contentType +
    " a prompt-injection attempt? " +
    "Return the injection risk and which techniques fired.\n\n" +
    content
  );
}

async function askEngine(content, contentType) {
  const { bridge = DEFAULT_BRIDGE } = await chrome.storage.local.get("bridge");
  const resp = await fetch(bridge.replace(/\/$/, "") + "/api/engine-ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: buildQuery(content, contentType) }),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(
      data.error || "bridge ask failed: HTTP " + resp.status,
    );
    err.code = data.code || (resp.status === 402 ? "PAYMENT_REQUIRED" : null);
    err.hint =
      resp.status === 502 && data.code === "PAYER_NOT_CONFIGURED"
        ? "The bridge has no payer wallet configured yet (TELEGRAPH_X402_KEY). " +
          "Every paid ask spends $0.01 — set the key deliberately."
        : resp.status === 429
          ? "Bridge daily cap reached — try again later or raise " +
            "TELEGRAPH_BRIDGE_DAILY_CAP."
          : null;
    throw err;
  }
  return data;
}

// Direct rail payload per the miner's registered schema. NOTE: unpaid — kept
// for development; will surface the 402 challenge in the overlay.
async function askDirect(content, contentType) {
  const resp = await fetch(DIRECT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      method: "POST",
      endpoint: "/scan",
      payload: { content, content_type: contentType },
    }),
  });
  if (resp.status === 402) {
    const challenge = await resp.text().catch(() => "");
    const err = new Error(
      "Direct rail is not paid by the extension — the challenge was surfaced " +
        "instead. Use the engine rail for real scans."
    );
    err.code = "PAYMENT_REQUIRED";
    err.challenge = challenge.slice(0, 2000);
    throw err;
  }
  if (!resp.ok) {
    throw new Error("direct ask failed: HTTP " + resp.status);
  }
  return resp.json();
}

// Normalize either rail's answer into the shape the overlay renders.
// The engine rail returns the routed miner's schema; the direct rail returns
// the miner's /scan response verbatim.
function normalize(data, rail) {
  const riskScore =
    typeof data.risk_score === "number"
      ? data.risk_score
      : typeof data.confidence === "number"
        ? data.confidence
        : null;
  return {
    rail,
    riskScore,
    riskLevel: data.risk_level || data.label || null,
    summary: data.summary || data.reason || data.human_summary || "",
    techniques: Array.isArray(data.flagged_techniques)
      ? data.flagged_techniques
      : [],
    quarantined: Boolean(data.quarantined),
    raw: data,
  };
}

// Band exactly like the integrate page prescribes: >=0.5 BLOCK,
// >=0.3 CAUTION, else SAFE (>=0.7 is always BLOCK regardless of label).
function band(result) {
  const s = result.riskScore;
  if (s === null) return "UNKNOWN";
  if (s >= 0.5) return "BLOCK";
  if (s >= 0.3) return "CAUTION";
  return "SAFE";
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "elcaro:scan") return; // async sendResponse used below

  (async () => {
    const { content, contentType, rail } = msg;
    try {
      const data =
        rail === "direct"
          ? await askDirect(content, contentType)
          : await askEngine(content, contentType);
      const result = normalize(data, rail);
      result.band = band(result);
      sendResponse({ ok: true, result });
    } catch (e) {
      sendResponse({
        ok: false,
        error: String(e.message || e),
        code: e.code || null,
        hint: e.hint || null,
        challenge: e.challenge || null,
      });
    }
  })();

  return true; // keep the message channel open for the async reply
});
