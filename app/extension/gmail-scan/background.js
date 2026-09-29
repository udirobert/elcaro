// Elcaro IPI Guard — background service worker (MV3).
//
// Two rails, matching app/telegraph.py's distinction:
//
//   engine (default) — POST /engine/v1/ask  { "query": "<natural language>" }
//     Auto-routed: the engine classifies the query to an intent and picks the
//     miner. This is the rail that counts for Telegraph miner judging. It is
//     x402-paid (jobBasePrice is separate; per-call it's the miner's floor,
//     0.01 USDC for miner 8848), so the FIRST call returns 402 with a
//     PAYMENT-REQUIRED challenge. This skeleton surfaces that response instead
//     of paying: wiring an x402 wallet client
//     (github.com/telegraphprotocol/Telegraph-examples, x402:engine-ask) is the
//     next step.
//
//   direct — POST /engine/v1/ask/8848 { method, endpoint, payload }
//     Same protocol host, but names the miner. Works without routing, still
//     x402-paid, and does NOT count as miner volume. Kept as the fallback and
//     for local development.

const ENGINE_URL = "https://devnode.telegraphprotocol.com/engine/v1/ask";
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
  const resp = await fetch(ENGINE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: buildQuery(content, contentType) }),
  });
  if (resp.status === 402) {
    const challenge = await resp.text().catch(() => "");
    const err = new Error(
      "402 payment required by the engine rail — an x402 wallet client must answer the PAYMENT-REQUIRED challenge before this rail works."
    );
    err.code = "PAYMENT_REQUIRED";
    err.challenge = challenge.slice(0, 2000);
    throw err;
  }
  if (!resp.ok) {
    throw new Error("engine ask failed: HTTP " + resp.status);
  }
  return resp.json();
}

// Direct rail payload per the miner's registered schema.
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
      "402 payment required by the direct rail — an x402 wallet client must answer the PAYMENT-REQUIRED challenge before this rail works."
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
        challenge: e.challenge || null,
      });
    }
  })();

  return true; // keep the message channel open for the async reply
});
