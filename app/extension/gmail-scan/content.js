// Elcaro IPI Guard — Gmail content script.
// Finds the open message body, offers a floating "Scan" action, and renders
// the verdict band as an overlay. Gmail's DOM is obfuscated and reshuffles its
// class names; the extraction below is deliberately defensive and is the part
// most likely to need iteration after first load. Structure: overlay skeleton
// now, extraction tuning next, then composed multi-miner checkpoint.

(() => {
  if (window.__elcaroIpiGuard) return; // re-injection guard
  window.__elcaroIpiGuard = true;

  const CONTENT_TYPE = "email";
  let button = null;

  function activeMessageBody() {
    // The open message lives in an adB/.aB class-less region; walk up from the
    // selection first, then fall back to the last opened message container.
    const sel = window.getSelection();
    let host = null;
    if (sel && sel.rangeCount > 0) {
      let n = sel.anchorNode;
      if (n && n.nodeType === Node.TEXT_NODE) n = n.parentNode;
      for (let i = 0; n && i < 12; i++, n = n.parentNode) {
        if (n.matches && n.matches(".ii.gt, div[role='main'] .a3s")) {
          host = n;
          break;
        }
      }
    }
    if (!host) {
      const bodies = document.querySelectorAll(".ii.gt div, .a3s.aiL");
      host = bodies[bodies.length - 1] || null;
    }
    return host ? (host.innerText || "").trim() : "";
  }

  function bandStyle(band) {
    switch (band) {
      case "BLOCK":
        return { bg: "#7f1d1d", fg: "#fff", label: "BLOCK" };
      case "CAUTION":
        return { bg: "#92400e", fg: "#fff", label: "CAUTION" };
      case "SAFE":
        return { bg: "#14532d", fg: "#fff", label: "SAFE" };
      default:
        return { bg: "#374151", fg: "#fff", label: "UNKNOWN" };
    }
  }

  function showOverlay(state) {
    dismissOverlay();
    const ov = document.createElement("div");
    ov.id = "elcaro-ipi-overlay";
    ov.style.cssText = [
      "position:fixed",
      "top:16px",
      "right:16px",
      "z-index:99999",
      "max-width:360px",
      "font:12.5px/1.5 ui-sans-serif,system-ui,sans-serif",
      "background:#fff",
      "border:1px solid #d5d5dd",
      "border-radius:12px",
      "box-shadow:0 8px 30px rgba(0,0,0,.18)",
      "overflow:hidden",
    ].join(";");

    const head = document.createElement("div");
    const s = bandStyle(state.band);
    head.style.cssText =
      "padding:10px 14px;color:" + s.fg + ";background:" + s.bg +
      ";font-weight:700;letter-spacing:.04em;display:flex;justify-content:space-between;align-items:center";
    head.textContent = "Elcaro · " + s.label;

    const meta = document.createElement("span");
    meta.style.cssText = "font-weight:400;font-size:11px;opacity:.85";
    meta.textContent =
      state.rail === "engine" ? "engine rail · counted" : "direct rail";
    head.appendChild(meta);

    const body = document.createElement("div");
    body.style.cssText = "padding:10px 14px 12px;color:#1a1a2e";

    if (state.error) {
      const p = document.createElement("p");
      p.style.cssText = "margin:0 0 6px;font-weight:600;color:#7f1d1d";
      p.textContent = state.error;
      body.appendChild(p);
      if (state.hint) {
        const h = document.createElement("p");
        h.style.cssText = "margin:0;color:#6b6b7b";
        h.textContent = state.hint;
        body.appendChild(h);
      }
    } else {
      const score = document.createElement("p");
      score.style.cssText = "margin:0 0 4px;font-weight:600";
      score.textContent =
        "Injection risk: " +
        (state.riskScore === null ? "n/a" : state.riskScore.toFixed(2)) +
        (state.riskLevel ? "  ·  " + state.riskLevel : "");
      body.appendChild(score);

      if (state.summary) {
        const p = document.createElement("p");
        p.style.cssText = "margin:0 0 6px";
        p.textContent = state.summary.slice(0, 280);
        body.appendChild(p);
      }
      if (state.techniques && state.techniques.length) {
        const p = document.createElement("p");
        p.style.cssText = "margin:0;color:#6b6b7b;font-size:11.5px";
        p.textContent = "Techniques: " + state.techniques.join(", ");
        body.appendChild(p);
      }
    }

    const close = document.createElement("button");
    close.textContent = "Dismiss";
    close.style.cssText =
      "margin:0 14px 12px;padding:4px 10px;border:1px solid #d5d5dd;" +
      "border-radius:8px;background:#fff;font:inherit;font-size:11.5px;cursor:pointer";
    close.addEventListener("click", dismissOverlay);

    ov.appendChild(head);
    ov.appendChild(body);
    ov.appendChild(close);
    document.documentElement.appendChild(ov);
  }

  function dismissOverlay() {
    const old = document.getElementById("elcaro-ipi-overlay");
    if (old) old.remove();
  }

  function setLoading(on) {
    if (!button) return;
    button.disabled = on;
    button.textContent = on ? "Scanning…" : "Scan";
  }

  async function scan() {
    const content = activeMessageBody();
    setLoading(true);
    if (!content) {
      showOverlay({
        band: "UNKNOWN",
        error: "No open message found.",
        hint: "Open a message, then click Scan again.",
      });
      setLoading(false);
      return;
    }
    const { rail = "engine" } = await chrome.storage.local.get("rail");
    try {
      const resp = await chrome.runtime.sendMessage({
        type: "elcaro:scan",
        content: content.slice(0, 60000), // miner MAX_BODY_SIZE is 256 KiB
        contentType: CONTENT_TYPE,
        rail,
      });
      if (resp.ok) {
        showOverlay({ ...resp.result, error: null });
      } else if (resp.code === "PAYMENT_REQUIRED") {
        showOverlay({
          band: "UNKNOWN",
          error: "Engine rail needs x402 payment.",
          hint:
            "The first call returns HTTP 402 with a PAYMENT-REQUIRED challenge. " +
            "Wire the x402 wallet client (Telegraph-examples, x402:engine-ask) into background.js next.",
        });
      } else {
        showOverlay({ band: "UNKNOWN", error: resp.error });
      }
    } catch (e) {
      showOverlay({ band: "UNKNOWN", error: String(e.message || e) });
    }
    setLoading(false);
  }

  function mountButton() {
    if (button && document.contains(button)) return;
    // Toolbar anchor: Gmail's per-conversation action row. If not found yet,
    // retry — Gmail loads its UI asynchronously.
    const anchor =
      document.querySelector("div[gh='tm'] .G-tF") ||
      document.querySelector("div[role='main'] .G-atb");
    if (!anchor) return;
    button = document.createElement("button");
    button.textContent = "Scan";
    button.title = "Scan this message for prompt injection (Elcaro)";
    button.style.cssText =
      "margin:0 8px;padding:4px 12px;border:1px solid #7c3aed;border-radius:14px;" +
      "background:#7c3aed;color:#fff;font:12px/1.4 ui-sans-serif,system-ui,sans-serif;" +
      "font-weight:600;cursor:pointer";
    button.addEventListener("click", scan);
    anchor.appendChild(button);
  }

  // Gmail re-renders its toolbar as you navigate; watch for it.
  const observer = new MutationObserver(() => mountButton());
  observer.observe(document.body, { childList: true, subtree: true });
  mountButton();
})();
