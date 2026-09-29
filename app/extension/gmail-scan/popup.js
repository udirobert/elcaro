// Elcaro IPI Guard — popup.
//
// Three jobs, in order of what a user actually needs:
//   1. Is the scan service live? (a user about to hit a failure should know first)
//   2. What has it caught for me today?
//   3. Which rail am I on, and does that matter?
//
// The history in (2) is read from chrome.storage.local and never leaves the
// machine — the same stance as the site's /supervise page. It is clearable,
// because a history you cannot erase is not private, it is just stored.

const $ = (id) => document.getElementById(id);

const RAIL_HINTS = {
  engine:
    "Goes through Telegraph's auto-router, so a miner is chosen for the job and " +
    "the scan counts toward the network. This is the one to use.",
  direct:
    "Names our miner (8848) explicitly. Useful while developing, but it " +
    "bypasses routing, doesn't count, and can't pay for itself.",
};

// status -> { state, title, body }
function statusView(reply) {
  if (!reply || !reply.ok) {
    return {
      state: "down",
      title: "Can't reach the Elcaro service",
      body:
        "Check your connection. Scans will keep failing until the service is " +
        "reachable — nothing is charged in the meantime.",
    };
  }
  const s = reply.status || {};
  if (!s.payerConfigured) {
    return {
      state: "off",
      title: "Not switched on yet",
      body:
        "Scans are paid per request and Elcaro's paying wallet isn't set up " +
        "yet. Scans will say so in Gmail rather than fail silently.",
    };
  }
  const left = s.asksRemaining;
  const budget =
    typeof left === "number"
      ? ` ${left} of ${s.dailyCap} scans left today on this instance.`
      : "";
  return {
    state: "live",
    title: "Live — scans are counted",
    body: `Routed through Telegraph miners, ${s.costPerAskUsd ?? 0.01} per scan.${budget}`,
  };
}

function renderStatus() {
  const card = $("status");
  $("statusTitle").textContent = "Checking service…";
  $("statusBody").textContent = "One moment.";
  card.dataset.state = "checking";

  chrome.runtime
    .sendMessage({ type: "elcaro:status" })
    .then((reply) => {
      const v = statusView(reply);
      card.dataset.state = v.state;
      $("statusTitle").textContent = v.title;
      $("statusBody").textContent = v.body;
    })
    .catch(() => {
      card.dataset.state = "down";
      $("statusTitle").textContent = "Can't reach the Elcaro service";
      $("statusBody").textContent = "Check your connection and reopen this popup.";
    });
}

const BANDS = [
  ["safe", "Clear"],
  ["caution", "Caution"],
  ["block", "Blocked"],
];

function renderHistory(summary) {
  const n = summary && summary.today ? summary.today : 0;
  const tally = (summary && summary.tally) || {};
  $("todayCount").innerHTML = "";

  if (!n) {
    const label = document.createElement("span");
    label.textContent = "Nothing scanned yet";
    $("todayCount").appendChild(label);
    $("todayBlocked").textContent = "";
    $("todayLegend").innerHTML = "";
    $("todayBar").hidden = true;
    $("todayFoot").hidden = !(summary && summary.stored);
    $("todayStored").textContent = summary && summary.stored
      ? `${summary.stored} older scan${summary.stored === 1 ? "" : "s"} kept`
      : "";
    return;
  }

  const label = document.createElement("span");
  label.appendChild(document.createTextNode("Today "));
  const em = document.createElement("em");
  em.textContent = `${n} scan${n === 1 ? "" : "s"}`;
  label.appendChild(em);
  $("todayCount").appendChild(label);

  $("todayBlocked").textContent = tally.block ? `${tally.block} blocked` : "all clear";
  $("todayBlocked").style.color = tally.block ? "#b91c1c" : "#15803d";

  $("todayBar").hidden = false;
  const parts = $("todayBar").children;
  BANDS.forEach(([key], i) => {
    parts[i].style.width = (n ? ((tally[key] || 0) / n) * 100 : 0) + "%";
  });

  $("todayLegend").innerHTML = "";
  for (const [key, name] of BANDS) {
    if (!tally[key]) continue;
    const s = document.createElement("span");
    const b = document.createElement("b");
    b.textContent = String(tally[key]);
    s.appendChild(b);
    s.appendChild(document.createTextNode(" " + name.toLowerCase()));
    $("todayLegend").appendChild(s);
  }

  $("todayFoot").hidden = !(summary && summary.stored);
  $("todayStored").textContent = summary && summary.stored
    ? `${summary.stored} kept locally`
    : "";
}

function loadHistory() {
  chrome.runtime
    .sendMessage({ type: "elcaro:history" })
    .then((reply) => renderHistory(reply && reply.summary))
    .catch(() => renderHistory(null));
}

$("clearHistory").addEventListener("click", () => {
  chrome.runtime
    .sendMessage({ type: "elcaro:clear-history" })
    .then(loadHistory)
    .catch(() => {});
});

function renderRail(rail) {
  $("rail").value = rail;
  $("railHint").textContent = RAIL_HINTS[rail] || RAIL_HINTS.engine;
}

chrome.storage.local.get(["rail"], ({ rail }) => renderRail(rail || "engine"));

$("rail").addEventListener("change", (e) => {
  chrome.storage.local.set({ rail: e.target.value });
  renderRail(e.target.value);
});

// Show the shortcut this platform actually has, rather than assuming macOS.
if (!/Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)) {
  $("kbd").textContent = "Alt+S";
}

renderStatus();
loadHistory();
