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
//
// This worker also owns everything the user should never have to think about:
// request timeouts, a short verdict cache (a re-scan of the same message is
// instant and free), toolbar badge state, and the single mapping from
// infrastructure error codes to human copy. The content script renders what
// `ui` it is handed and does not know what an x402 challenge is.

// Where the bridge lives. Override for local dev:
//   chrome.storage.local.set({ bridge: "http://localhost:3000" })
const DEFAULT_BRIDGE = "https://elcaro.trustfall.xyz";

const DIRECT_URL =
  "https://devnode.telegraphprotocol.com/engine/v1/ask/8848";

// Under the server's 30s upstream timeout, so the user gets our copy and a
// Retry button rather than a spinner that never resolves.
const ASK_TIMEOUT_MS = 20_000;
const STATUS_TIMEOUT_MS = 5_000;

// Verdict cache. Scans cost $0.01 each, and re-clicking Scan on the message you
// just scanned should be instant and free. Keyed by rail + content hash, TTL
// CACHE_TTL_MS, bounded to CACHE_MAX entries (oldest evicted first).
const CACHE_TTL_MS = 5 * 60 * 1000;
const CACHE_MAX = 50;
const verdictCache = new Map();

// code -> what the user is told. Keep this the only place infra strings get
// translated; the overlay never sees a status code or an env var name.
const ERROR_COPY = {
  PAYER_NOT_CONFIGURED: {
    headline: "Scans are temporarily unavailable",
    detail:
      "Elcaro is still switching its scan service on. Your message was not sent anywhere and nothing was charged.",
    tone: "warn",
    retryable: true,
  },
  PAYMENT_REJECTED: {
    headline: "Scans are temporarily unavailable",
    detail:
      "The Elcaro service that pays for scans is out of testnet funds. Your message was not sent anywhere.",
    tone: "warn",
    retryable: true,
  },
  CAP_REACHED: {
    headline: "Today's scan budget is used up",
    detail:
      "Scans are paid per request, and today's shared budget is spent. Nothing was charged — try again tomorrow.",
    tone: "warn",
    retryable: true,
  },
  FORBIDDEN_ORIGIN: {
    headline: "This extension can't scan",
    detail:
      "The Elcaro service only accepts its published extension. Reinstall it from the official source.",
    tone: "error",
    retryable: false,
  },
  FORBIDDEN_TOKEN: {
    headline: "This extension can't scan",
    detail:
      "The Elcaro service rejected this extension's credentials. Reinstall it from the official source.",
    tone: "error",
    retryable: false,
  },
  PAYMENT_REQUIRED: {
    headline: "Direct mode can't pay for scans",
    detail:
      "Scans are paid per request, and only Engine mode goes through the payment path. Switch to Engine mode in the extension popup.",
    tone: "error",
    retryable: false,
  },
  QUERY_TOO_LARGE: {
    headline: "That message is too long to scan",
    detail: "Try it on a shorter message — long threads get truncated.",
    tone: "error",
    retryable: false,
  },
  UPSTREAM_TIMEOUT: {
    headline: "That took too long",
    detail: "The Elcaro service didn't answer in time. Your message wasn't scanned.",
    tone: "warn",
    retryable: true,
  },
  UPSTREAM_UNREACHABLE: {
    headline: "Can't reach the Elcaro service",
    detail: "Check your connection and try again.",
    tone: "warn",
    retryable: true,
  },
  TIMEOUT: {
    headline: "That took too long",
    detail: "The Elcaro service didn't answer in 20 seconds. Your message wasn't scanned.",
    tone: "warn",
    retryable: true,
  },
  NETWORK: {
    headline: "Can't reach the Elcaro service",
    detail: "Check your connection and try again.",
    tone: "warn",
    retryable: true,
  },
  BAD_REQUEST: { headline: "Nothing to scan", detail: "Open a message first.", tone: "error", retryable: false },
  INVALID_JSON: { headline: "Nothing to scan", detail: "Open a message first.", tone: "error", retryable: false },
};

const DEFAULT_ERROR = {
  headline: "Scan failed",
  detail: "Something went wrong on the way to the Elcaro service. Nothing was charged.",
  tone: "error",
  retryable: true,
};

function copyFor(code, fallbackMessage) {
  return ERROR_COPY[code] || { ...DEFAULT_ERROR, detail: fallbackMessage || DEFAULT_ERROR.detail };
}

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

async function bridgeBase() {
  const { bridge = DEFAULT_BRIDGE } = await chrome.storage.local.get("bridge");
  return bridge.replace(/\/+$/, "");
}

function failWith(ui, code, extra) {
  const err = new Error(ui.headline);
  err.ui = { ...ui, code: code || null };
  if (extra) err.ui.detail_extra = extra;
  return err;
}

// Cheap FNV-1a: enough to key a cache, and it never puts message text in a map
// key we might ever log.
function contentKey(content, rail) {
  let h = 0x811c9dc5;
  for (let i = 0; i < content.length; i++) {
    h ^= content.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return rail + ":" + content.length + ":" + h.toString(16);
}

function cacheGet(key) {
  const hit = verdictCache.get(key);
  if (!hit) return null;
  if (Date.now() - hit.at > CACHE_TTL_MS) {
    verdictCache.delete(key);
    return null;
  }
  return hit.result;
}

function cachePut(key, result) {
  verdictCache.set(key, { at: Date.now(), result });
  while (verdictCache.size > CACHE_MAX) {
    verdictCache.delete(verdictCache.keys().next().value);
  }
}

async function askEngine(content, contentType) {
  const base = await bridgeBase();
  let resp;
  try {
    resp = await fetch(base + "/api/engine-ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: buildQuery(content, contentType) }),
      signal: AbortSignal.timeout(ASK_TIMEOUT_MS),
    });
  } catch (e) {
    const timedOut = e instanceof Error && e.name === "TimeoutError";
    throw failWith(
      copyFor(timedOut ? "TIMEOUT" : "NETWORK"),
      timedOut ? "TIMEOUT" : "NETWORK",
    );
  }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const code = data.code || (resp.status === 402 ? "PAYMENT_REQUIRED" : null);
    throw failWith(copyFor(code, data.error), code, data.upstream);
  }
  return data;
}

// Direct rail payload per the miner's registered schema. NOTE: unpaid — kept
// for development; will surface the 402 challenge in the overlay.
async function askDirect(content, contentType) {
  let resp;
  try {
    resp = await fetch(DIRECT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        method: "POST",
        endpoint: "/scan",
        payload: { content, content_type: contentType },
      }),
      signal: AbortSignal.timeout(ASK_TIMEOUT_MS),
    });
  } catch (e) {
    const timedOut = e instanceof Error && e.name === "TimeoutError";
    throw failWith(
      copyFor(timedOut ? "TIMEOUT" : "NETWORK"),
      timedOut ? "TIMEOUT" : "NETWORK",
    );
  }
  if (resp.status === 402) {
    const challenge = await resp.text().catch(() => "");
    const err = failWith(copyFor("PAYMENT_REQUIRED"), "PAYMENT_REQUIRED");
    err.challenge = challenge.slice(0, 2000);
    throw err;
  }
  if (!resp.ok) {
    throw failWith(copyFor(null, "direct ask failed: HTTP " + resp.status), null);
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
    techniques: Array.isArray(data.flagged_techniques) ? data.flagged_techniques : [],
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

// Toolbar badge: the user gets feedback even when the overlay is off-screen.
async function setBadge(text, color) {
  try {
    await chrome.action.setBadgeText({ text: text || "" });
    if (text) await chrome.action.setBadgeBackgroundColor({ color });
  } catch {
    /* action API unavailable in some contexts; the overlay is the real UI */
  }
}

const BAND_BADGE = {
  BLOCK: ["!", "#b91c1c"],
  CAUTION: ["?", "#b45309"],
  UNKNOWN: ["?", "#4b5563"],
  SAFE: ["", "#15803d"],
};

async function announceBand(b) {
  const [text, color] = BAND_BADGE[b] || BAND_BADGE.UNKNOWN;
  await setBadge(text, color);
  if (b === "SAFE") setTimeout(() => chrome.action.setBadgeText({ text: "" }).catch(() => {}), 6000);
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "elcaro:status") {
    (async () => {
      try {
        const base = await bridgeBase();
        const resp = await fetch(base + "/api/engine-ask", {
          signal: AbortSignal.timeout(STATUS_TIMEOUT_MS),
        });
        const data = await resp.json().catch(() => ({}));
        sendResponse({ ok: resp.ok, status: data });
      } catch {
        sendResponse({ ok: false, status: null });
      }
    })();
    return true;
  }

  if (msg?.type !== "elcaro:scan") return; // async sendResponse used below

  (async () => {
    const { content, contentType, rail } = msg;
    const key = contentKey(content || "", rail);
    const cached = cacheGet(key);
    if (cached) {
      await announceBand(cached.band);
      sendResponse({ ok: true, result: { ...cached, cached: true } });
      return;
    }

    await setBadge("···", "#7c3aed");
    try {
      const data =
        rail === "direct"
          ? await askDirect(content, contentType)
          : await askEngine(content, contentType);
      const result = normalize(data, rail);
      result.band = band(result);
      cachePut(key, result);
      await announceBand(result.band);
      sendResponse({ ok: true, result });
    } catch (e) {
      await setBadge("!", "#b91c1c");
      sendResponse({
        ok: false,
        ui: e.ui || copyFor(null, String(e.message || e)),
        code: (e.ui && e.ui.code) || e.code || null,
        challenge: e.challenge || null,
      });
    }
  })();

  return true; // keep the message channel open for the async reply
});
