// jsdom smoke test for the popup.
//
// The popup has no failure mode louder than a null element: every `$("id")`
// that does not exist throws and the whole panel goes blank. This renders it
// against stubbed service-worker replies — live, not-switched-on, and
// unreachable — plus a scan history, and asserts what the user should read.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { JSDOM } from "jsdom";

const HERE = dirname(fileURLToPath(import.meta.url));
const DIR = join(HERE, "..", "gmail-scan");

let failures = 0;
function assert(cond, label) {
  if (cond) console.log("  ok:", label);
  else {
    failures += 1;
    console.error("  FAIL:", label);
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const LIVE = {
  ok: true,
  status: {
    payerConfigured: true,
    dailyCap: 40,
    asksUsed: 3,
    asksRemaining: 37,
    costPerAskUsd: 0.01,
  },
};

const HISTORY = {
  ok: true,
  summary: {
    today: 9,
    tally: { safe: 7, caution: 1, block: 1, unknown: 0 },
    blockedToday: 1,
    stored: 24,
    recent: [],
  },
};

async function render(name, { status = LIVE, history = HISTORY, rail = "engine" } = {}) {
  console.log(`\n${name}`);
  const dom = new JSDOM(readFileSync(join(DIR, "popup.html"), "utf8"), {
    runScripts: "outside-only",
    pretendToBeVisual: true,
    url: "https://mail.google.com/",
  });
  const { window } = dom;
  const cleared = { n: 0 };
  const store = { rail };
  window.chrome = {
    storage: {
      local: {
        // popup.js uses the callback form of chrome.storage.local.get, so the
        // mock has to honour the callback or the panel never initialises.
        get: (_keys, cb) => {
          const out = { rail: store.rail };
          if (typeof cb === "function") cb(out);
          return Promise.resolve(out);
        },
        set: async () => {},
      },
    },
    runtime: {
      sendMessage: async (msg) => {
        if (msg.type === "elcaro:status") return status;
        if (msg.type === "elcaro:history") return history;
        if (msg.type === "elcaro:clear-history") {
          cleared.n += 1;
          return { ok: true };
        }
        return { ok: false };
      },
    },
  };
  const errors = [];
  window.addEventListener("error", (e) => errors.push(e.message));
  try {
    window.eval(readFileSync(join(DIR, "popup.js"), "utf8"));
  } catch (e) {
    errors.push(e.message);
  }
  await sleep(60);
  return { window, document: window.document, errors, cleared, store };
}

{
  const { document, errors } = await render("popup: service live, with history");
  assert(errors.length === 0, "popup.js runs without throwing: " + (errors[0] || ""));
  assert(
    document.getElementById("status").dataset.state === "live",
    "status card reads live",
  );
  assert(
    document.getElementById("statusTitle").textContent.includes("counted"),
    "live status says scans are counted",
  );
  assert(
    document.getElementById("statusBody").textContent.includes("37 of 40"),
    "live status shows the remaining daily budget",
  );

  const today = document.getElementById("today").textContent;
  assert(today.includes("9 scans"), "today panel counts the day's scans");
  assert(today.includes("1 blocked"), "today panel surfaces the blocked count");
  assert(
    document.getElementById("todayBlocked").textContent.includes("blocked"),
    "blocked count is coloured as a headline, not buried",
  );
  const widths = [...document.getElementById("todayBar").children].map((i) => i.style.width);
  assert(
    widths[0] === (7 / 9) * 100 + "%" && widths[2] === (1 / 9) * 100 + "%",
    "the bar is proportional to the tally: " + widths.join(" / "),
  );
  assert(
    document.getElementById("railHint").textContent.includes("auto-router"),
    "the engine rail explains itself",
  );
  assert(document.getElementById("kbd").textContent.length > 0, "shortcut is shown");
}

{
  const { document, errors } = await render("popup: payer not configured", {
    status: { ok: true, status: { payerConfigured: false } },
  });
  assert(errors.length === 0, "renders cleanly in the not-switched-on state");
  assert(
    document.getElementById("status").dataset.state === "off",
    "status card reads as not switched on",
  );
  assert(
    document.getElementById("statusTitle").textContent.includes("Not switched on"),
    "the unconfigured state is named plainly",
  );
}

{
  const { document, errors } = await render("popup: service unreachable", {
    status: { ok: false, status: null },
  });
  assert(errors.length === 0, "renders cleanly when the bridge is unreachable");
  assert(
    document.getElementById("status").dataset.state === "down",
    "unreachable state is distinct from unconfigured",
  );
}

{
  const { document, errors, cleared } = await render("popup: first ever use", {
    history: { ok: true, summary: { today: 0, tally: {}, blockedToday: 0, stored: 0, recent: [] } },
  });
  assert(errors.length === 0, "renders cleanly with no history at all");
  assert(
    document.getElementById("todayCount").textContent.includes("Nothing scanned"),
    "empty state invites the first scan instead of showing zeroes",
  );
  assert(
    document.getElementById("todayBar").hidden,
    "no empty bar is drawn",
  );
  assert(
    document.getElementById("todayFoot").hidden,
    "no clear-history control before there is history to clear",
  );
  assert(
    document.getElementById("clearHistory") !== null,
    "clear-history control exists for the populated case",
  );
}

{
  const { document, cleared } = await render("popup: clearing history");
  document.getElementById("clearHistory").click();
  await sleep(40);
  assert(cleared.n === 1, "Clear history asks the worker to erase it");
}

console.log(
  failures === 0 ? "\nALL ASSERTIONS PASSED" : `\n${failures} ASSERTION(S) FAILED`,
);
process.exit(failures === 0 ? 0 : 1);
