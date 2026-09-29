// Elcaro IPI Guard — popup.
//
// Two jobs: show whether the scan service is actually live (so a user who gets
// a failure knows whether to retry or to wait), and let them pick a rail. The
// status card is the payoff of GET /api/engine-ask — without a payer wallet
// configured the scans can't work, and saying so up front beats a cryptic
// overlay mid-thread.

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

function renderRail(rail) {
  $("rail").value = rail;
  $("railHint").textContent = RAIL_HINTS[rail] || RAIL_HINTS.engine;
}

chrome.storage.local.get(["rail"], ({ rail }) => renderRail(rail || "engine"));

$("rail").addEventListener("change", (e) => {
  chrome.storage.local.set({ rail: e.target.value });
  renderRail(e.target.value);
});

renderStatus();
