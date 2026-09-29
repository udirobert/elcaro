// jsdom driver for the Gmail extension's content script.
//
// The extension itself has no build step and no test runner — this file is the
// only automated check on content.js, and it earns its keep: an earlier
// version read the message body with innerText only, which jsdom does not
// implement, so every scan shipped an empty message. Run it with:
//
//   cd app/extension/tests && npm install && npm test

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { JSDOM } from "jsdom";

const HERE = dirname(fileURLToPath(import.meta.url));
const CONTENT_JS = join(HERE, "..", "gmail-scan", "content.js");
const FIXTURE = join(HERE, "fixture.gmail.html");
const BODY_MARKER = "SYSTEM: Updated policy";

let failures = 0;
function assert(cond, label) {
  if (cond) {
    console.log("  ok:", label);
  } else {
    failures += 1;
    console.error("  FAIL:", label);
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const BLOCK_REPLY = {
  ok: true,
  result: {
    rail: "engine",
    riskScore: 0.93,
    riskLevel: "dangerous",
    summary:
      "Verdict: prompt injection (dangerous, risk 0.93 of 1). Authority impersonation with an exfiltration directive.",
    techniques: ["authority_framing"],
    quarantined: true,
    band: "BLOCK",
  },
};

const SAFE_REPLY = {
  ok: true,
  result: {
    rail: "engine",
    riskScore: 0.04,
    riskLevel: "benign",
    summary: "No hidden instructions found.",
    techniques: [],
    band: "SAFE",
  },
};

const PAYER_DOWN_REPLY = {
  ok: false,
  ui: {
    headline: "Scans are temporarily unavailable",
    detail: "Elcaro is still switching its scan service on.",
    tone: "warn",
    retryable: true,
    code: "PAYER_NOT_CONFIGURED",
  },
  code: "PAYER_NOT_CONFIGURED",
};

async function scenario(name, reply, { onSend } = {}) {
  console.log(`\n${name}`);
  const dom = await JSDOM.fromFile(FIXTURE, {
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  const { window } = dom;
  const sent = [];
  const listeners = [];
  const store = { rail: "engine" };
  window.chrome = {
    storage: {
      local: {
        get: async (k) => (k === "rail" || k === ["rail"] ? { rail: store.rail } : {}),
        set: async (obj) => {
          Object.assign(store, obj);
        },
      },
    },
    runtime: {
      sendMessage: async (msg) => {
        sent.push(msg);
        if (onSend) return onSend(msg, sent);
        return reply;
      },
      onMessage: { addListener: (fn) => listeners.push(fn) },
    },
  };
  window.__store = store;
  window.__listeners = listeners;
  window.eval(readFileSync(CONTENT_JS, "utf8"));
  await sleep(80);
  return { window, document: window.document, sent, dom, store, listeners };
}

const scanButton = (doc) => doc.querySelector("button[title^='Scan this message']");
const overlayText = (doc) => {
  const ov = doc.getElementById("elcaro-ipi-overlay");
  return ov ? ov.textContent : "";
};
const buttonByText = (doc, text) =>
  [...doc.querySelectorAll("#elcaro-ipi-overlay button")].find(
    (b) => b.textContent === text,
  );

// --- 1. happy path: a BLOCK verdict -----------------------------------------
{
  const { document, sent } = await scenario("BLOCK verdict", BLOCK_REPLY, {
    onSend: async (msg) => {
      // The scanning overlay must be on screen before the reply lands.
      const ov = document.getElementById("elcaro-ipi-overlay");
      const progressShown = ov && /Scanning/.test(ov.textContent);
      assert(progressShown, "progress overlay appears while the ask is in flight");
      return BLOCK_REPLY;
    },
  });

  const btn = scanButton(document);
  assert(btn, "Scan button mounted in the Gmail action row");

  btn.click();
  await sleep(120);

  assert(sent.length === 1, "sendMessage issued once");
  assert(
    sent[0].type === "elcaro:scan" && sent[0].rail === "engine",
    "message uses elcaro:scan + engine rail",
  );
  assert(
    typeof sent[0].content === "string" && sent[0].content.includes(BODY_MARKER),
    "message body extracted from .ii.gt / .a3s",
  );
  assert(sent[0].contentType === "email", "content_type=email sent");

  const text = overlayText(document);
  assert(text.includes("BLOCK"), "overlay shows BLOCK band");
  assert(text.includes("0.93"), "overlay shows the risk score");
  assert(text.includes("dangerous"), "overlay shows the miner's risk level");
  assert(text.includes("authority_framing"), "overlay lists flagged techniques");
  assert(text.includes("engine rail"), "overlay names the rail");
  assert(
    text.includes("Don't act on this message"),
    "BLOCK overlay says what to actually do",
  );
  assert(!!buttonByText(document, "Scan again"), "verdict offers Scan again");
  assert(!!buttonByText(document, "Dismiss"), "verdict offers Dismiss");

  buttonByText(document, "Dismiss").click();
  assert(
    !document.getElementById("elcaro-ipi-overlay"),
    "Dismiss removes the overlay",
  );
}

// --- 1b. the keyboard shortcut ----------------------------------------------
{
  const { document, sent, listeners, store } = await scenario("keyboard shortcut", BLOCK_REPLY);
  assert(listeners.length > 0, "content script listens for runtime messages");
  assert(store.welcomed === undefined, "not welcomed before the first scan");

  listeners.forEach((fn) => fn({ type: "elcaro:trigger-scan" }));
  await sleep(120);
  assert(sent.length === 1, "shortcut triggers exactly one scan");
  assert(sent[0].type === "elcaro:scan", "shortcut takes the same path as a click");
  assert(
    sent[0].content.includes(BODY_MARKER),
    "shortcut extracts the same message body",
  );
  assert(store.welcomed === true, "the first scan marks the extension as welcomed");
}

// --- 1c. which miner answered ------------------------------------------------
{
  const { document } = await scenario("miner attribution", {
    ok: true,
    result: { ...BLOCK_REPLY.result, miner: "9002" },
  });
  scanButton(document).click();
  await sleep(120);
  assert(
    overlayText(document).includes("miner 9002"),
    "overlay credits the miner that answered",
  );
}

// --- 2. a SAFE verdict -------------------------------------------------------
{
  const { document } = await scenario("SAFE verdict", SAFE_REPLY);
  scanButton(document).click();
  await sleep(120);
  const text = overlayText(document);
  assert(text.includes("SAFE"), "SAFE verdict renders its own band");
  assert(
    text.includes("read it as you normally would"),
    "SAFE overlay reassures instead of alarming",
  );
}

// --- 3. the bridge has no payer wallet (the live production state) -----------
{
  const { document, window } = await scenario(
    "bridge not configured",
    PAYER_DOWN_REPLY,
  );
  scanButton(document).click();
  await sleep(120);

  const text = overlayText(document);
  assert(
    text.includes("Scans are temporarily unavailable"),
    "payer-down error shows a human headline",
  );
  assert(
    !text.includes("TELEGRAPH_X402_KEY") && !text.includes("x402"),
    "no env var or protocol jargon in the user-facing copy",
  );
  assert(
    text.includes("PAYER_NOT_CONFIGURED"),
    "the infra code is still available, behind the Details disclosure",
  );
  assert(!!document.querySelector("#elcaro-ipi-overlay details"), "Details disclosure rendered");
  assert(!!buttonByText(document, "Scan again"), "retryable error offers a retry");
  assert(
    !buttonByText(document, "Scan again").disabled,
    "retry button is enabled",
  );

  // Escape is the keyboard affordance for the Dismiss button.
  document.dispatchEvent(
    new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
  );
  assert(
    !document.getElementById("elcaro-ipi-overlay"),
    "Escape dismisses the overlay",
  );
}

// --- 4. no message open ------------------------------------------------------
{
  const { document } = await scenario("no message open", BLOCK_REPLY);
  // Strip the message body the fixture provides, as if no thread were open.
  document.querySelector(".a3s.aiL").remove();
  scanButton(document).click();
  await sleep(120);
  const text = overlayText(document);
  assert(text.includes("No message open"), "empty extraction explains itself");
  assert(
    !text.includes("Scan again"),
    "nothing to retry when there is no message",
  );
}

console.log(
  failures === 0 ? "\nALL ASSERTIONS PASSED" : `\n${failures} ASSERTION(S) FAILED`,
);
process.exit(failures === 0 ? 0 : 1);
