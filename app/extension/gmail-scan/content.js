// Elcaro IPI Guard — Gmail content script.
//
// Mounts a floating "Scan" action in the thread toolbar and renders the verdict
// as an overlay. Two things to keep in mind when editing:
//
//   1. Gmail's DOM is obfuscated and reshuffles its class names. The extraction
//      below (activeMessageBody) is the part most likely to need iteration
//      after first load.
//   2. This file owns presentation only. It never sees an HTTP status or an
//      env var name: background.js hands it either a normalized result or a
//      `ui` object ({ headline, detail, tone, retryable, code }) and we render
//      that. Adding a new failure mode means editing background.js's
//      ERROR_COPY, not this file.

(() => {
  if (window.__elcaroIpiGuard) return; // re-injection guard
  window.__elcaroIpiGuard = true;

  const CONTENT_TYPE = "email";
  const OVERLAY_ID = "elcaro-ipi-overlay";
  const STYLE_ID = "elcaro-ipi-style";
  const SAFE_AUTODISMISS_MS = 8_000;

  let button = null;
  let lastScan = null; // re-runnable by the overlay's Try again button
  let autoDismissTimer = null;

  const TEXT = {
    SAFE: {
      label: "SAFE",
      glyph: "✓",
      bg: "#14532d",
      next: "Nothing hidden found — read it as you normally would.",
    },
    CAUTION: {
      label: "CAUTION",
      glyph: "!",
      bg: "#92400e",
      next: "Something didn't add up. Check the sender and any links before you act.",
    },
    BLOCK: {
      label: "BLOCK",
      glyph: "⛔",
      bg: "#7f1d1d",
      next: "Don't act on this message. It contains instructions aimed at an AI agent.",
    },
    UNKNOWN: {
      label: "NO VERDICT",
      glyph: "?",
      bg: "#374151",
      next: "The miner didn't return a score for this message.",
    },
  };

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
    return host ? (host.innerText || host.textContent || "").trim() : "";
  }

  // Injected once into the page; keeps the animation out of the inline-style
  // soup below.
  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      @keyframes elcaroSweep { 0% { transform: translateX(-100%);} 100% { transform: translateX(320%);} }
      @keyframes elcaroPulse { 0%,100% { opacity:.35;} 50% { opacity:1;} }
      #${OVERLAY_ID} .elcaro-bar span {
        display:block; width:32%; height:100%; border-radius:999px;
        background:linear-gradient(90deg,transparent,#7c3aed,transparent);
        animation:elcaroSweep 1.1s ease-in-out infinite;
      }
      #${OVERLAY_ID} button { font: inherit; }
      #${OVERLAY_ID} .elcaro-btn {
        padding:5px 12px;border-radius:9px;border:1px solid #d5d5dd;background:#fff;
        font-size:11.5px;font-weight:600;color:#1a1a2e;cursor:pointer;
      }
      #${OVERLAY_ID} .elcaro-btn:hover { background:#f4f4f8; }
      #${OVERLAY_ID} .elcaro-btn-primary { background:#7c3aed;border-color:#7c3aed;color:#fff; }
      #${OVERLAY_ID} .elcaro-btn-primary:hover { background:#6d28d9; }
      #${OVERLAY_ID} summary { cursor:pointer; font-size:11px; color:#6b6b7b; }
      #${OVERLAY_ID} pre {
        margin:6px 0 0;padding:8px;background:#f4f4f8;border-radius:8px;
        font-family:ui-monospace,monospace;font-size:10.5px;white-space:pre-wrap;
        word-break:break-word;max-height:140px;overflow:auto;color:#3f3f52;
      }
      #${OVERLAY_ID} .elcaro-glyph { animation:elcaroPulse 1.4s ease-in-out infinite; }
    `;
    (document.head || document.documentElement).appendChild(style);
  }

  function el(tag, css, text) {
    const n = document.createElement(tag);
    if (css) n.style.cssText = css;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function bandStyle(b) {
    return TEXT[b] || TEXT.UNKNOWN;
  }

  function dismissOverlay() {
    if (autoDismissTimer) {
      clearTimeout(autoDismissTimer);
      autoDismissTimer = null;
    }
    const old = document.getElementById(OVERLAY_ID);
    if (old) old.remove();
    document.removeEventListener("keydown", onKeydown, true);
  }

  function onKeydown(e) {
    if (e.key === "Escape") dismissOverlay();
  }

  // --- overlay shells -------------------------------------------------------

  function newOverlay() {
    dismissOverlay();
    ensureStyles();
    const ov = el("div", null);
    ov.id = OVERLAY_ID;
    ov.setAttribute("role", "status");
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
    document.documentElement.appendChild(ov);
    document.addEventListener("keydown", onKeydown, true);
    return ov;
  }

  function header(ov, { label, glyph, bg }, right) {
    const head = el(
      "div",
      "padding:10px 14px;color:#fff;background:" +
        bg +
        ";display:flex;align-items:center;gap:8px;font-weight:700;letter-spacing:.03em",
    );
    head.appendChild(el("span", "font-size:14px;line-height:1", glyph));
    head.appendChild(el("span", null, label));
    if (right) {
      const meta = el("span", "margin-left:auto;font-weight:400;font-size:11px;opacity:.9", right);
      head.appendChild(meta);
    }
    ov.appendChild(head);
    return head;
  }

  function railLabel(state) {
    if (state.rail === "engine") return "engine rail · counted";
    if (state.rail === "direct") return "direct rail";
    return "elcaro";
  }

  // --- states ---------------------------------------------------------------

  function showScanning() {
    const ov = newOverlay();
    header(ov, { label: "Scanning", glyph: "◌", bg: "#4c1d95" }, "engine rail");
    const body = el("div", "padding:12px 14px 14px;color:#1a1a2e");
    body.appendChild(
      el("p", "margin:0 0 8px;color:#6b6b7b", "Checking this message for hidden instructions…"),
    );
    const bar = el("div", "margin:0 14px 4px;height:3px;background:#ece9f7;border-radius:999px;overflow:hidden");
    bar.appendChild(el("span"));
    ov.appendChild(body);
    ov.appendChild(bar);
    const hint = el(
      "p",
      "margin:8px 14px 12px;font-size:11px;color:#8b8b9c",
      "Paid per scan through the Telegraph network — usually a couple of seconds.",
    );
    ov.appendChild(hint);
    return ov;
  }

  /** Score readout + proportional bar. Returns the nodes it needs to fill in. */
  function riskMeter(score, level) {
    const label = el(
      "div",
      "display:flex;justify-content:space-between;font-size:11px;color:#6b6b7b;margin-bottom:4px",
    );
    label.appendChild(el("span", null, "Injection risk"));
    label.appendChild(
      el(
        "span",
        "font-weight:700;color:#1a1a2e",
        score.toFixed(2) + (level ? "  ·  " + level : ""),
      ),
    );
    const fill = el("div", "height:100%;border-radius:999px;width:" + Math.round(score * 100) + "%");
    const track = el("div", "height:6px;background:#eeeef4;border-radius:999px;overflow:hidden");
    track.appendChild(fill);
    const wrap = el("div", "margin:0 0 10px");
    wrap.appendChild(label);
    wrap.appendChild(track);
    return { wrap, fill };
  }

  function showVerdict(state) {
    const ov = newOverlay();
    const s = bandStyle(state.band);
    header(ov, s, railLabel(state) + (state.cached ? " · cached" : ""));

    const body = el("div", "padding:12px 14px 6px;color:#1a1a2e");

    if (state.riskScore !== null && state.riskScore !== undefined) {
      const score = Math.max(0, Math.min(1, state.riskScore));
      const meter = riskMeter(score, state.riskLevel);
      meter.fill.style.background =
        state.band === "BLOCK" ? "#b91c1c" : state.band === "CAUTION" ? "#b45309" : "#15803d";
      body.appendChild(meter.wrap);
    }

    body.appendChild(el("p", "margin:0 0 8px;font-weight:600;color:" + s.bg, s.next));

    if (state.summary) {
      body.appendChild(el("p", "margin:0 0 8px", state.summary.slice(0, 280)));
    }
    if (state.techniques && state.techniques.length) {
      const row = el("div", "margin:0 0 6px;display:flex;flex-wrap:wrap;gap:4px");
      row.appendChild(el("span", "font-size:11px;color:#6b6b7b;align-self:center;margin-right:2px", "Techniques:"));
      for (const t of state.techniques.slice(0, 8)) {
        row.appendChild(
          el(
            "span",
            "font-size:10.5px;background:#f2f0fb;color:#4c1d95;border-radius:999px;padding:2px 8px",
            t,
          ),
        );
      }
      body.appendChild(row);
    }

    ov.appendChild(body);
    appendFooter(ov, { retry: true });

    if (state.band === "SAFE") {
      autoDismissTimer = setTimeout(dismissOverlay, SAFE_AUTODISMISS_MS);
    }
  }

  function showError(state) {
    const ov = newOverlay();
    const ui = state.ui || {
      headline: "Scan failed",
      detail: "Something went wrong.",
      retryable: true,
    };
    const warn = ui.tone !== "error";
    header(
      ov,
      { label: "SCAN UNAVAILABLE", glyph: "⚠", bg: warn ? "#92400e" : "#7f1d1d" },
      "elcaro",
    );
    const body = el("div", "padding:12px 14px 6px;color:#1a1a2e");
    body.appendChild(el("p", "margin:0 0 6px;font-weight:600", ui.headline));
    body.appendChild(el("p", "margin:0 0 4px;color:#4a4a5c", ui.detail));

    // Operator detail, kept out of the way until someone actually wants it.
    const bits = [];
    if (ui.code) bits.push("code: " + ui.code);
    if (state.rail) bits.push("rail: " + state.rail);
    if (state.challenge) bits.push(state.challenge);
    else if (ui.detail_extra) bits.push(String(ui.detail_extra));
    if (bits.length) {
      const det = el("details", "margin:6px 0 0");
      det.appendChild(el("summary", null, "Details"));
      det.appendChild(el("pre", null, bits.join("\n\n")));
      body.appendChild(det);
    }

    ov.appendChild(body);
    appendFooter(ov, { retry: ui.retryable !== false });

    // A non-retryable misconfiguration won't fix itself in 8 seconds, so no
    // auto-dismiss here — the user has to read it.
  }

  function appendFooter(ov, { retry }) {
    const row = el("div", "margin:0 14px 12px;display:flex;gap:8px");
    if (retry && lastScan) {
      const again = el("button", null, "Scan again");
      again.className = "elcaro-btn elcaro-btn-primary";
      again.addEventListener("click", () => scan(lastScan.content));
      row.appendChild(again);
    }
    const close = el("button", null, "Dismiss");
    close.className = "elcaro-btn";
    close.addEventListener("click", dismissOverlay);
    row.appendChild(close);
    ov.appendChild(row);
  }

  // --- scan flow ------------------------------------------------------------

  function setLoading(on) {
    if (!button) return;
    button.disabled = on;
    button.textContent = on ? "Scanning…" : "Scan";
  }

  async function scan(contentOverride) {
    const content = contentOverride === undefined ? activeMessageBody() : contentOverride;
    if (!content) {
      showError({
        ui: {
          headline: "No message open",
          detail: "Open a message in Gmail, then scan it.",
          retryable: false,
        },
      });
      return;
    }
    lastScan = { content };
    showScanning();
    setLoading(true);
    const { rail = "engine" } = await chrome.storage.local.get("rail");
    try {
      const resp = await chrome.runtime.sendMessage({
        type: "elcaro:scan",
        content: content.slice(0, 60000), // miner MAX_BODY_SIZE is 256 KiB
        contentType: CONTENT_TYPE,
        rail,
      });
      if (resp && resp.ok) {
        showVerdict({ ...resp.result, error: null });
      } else {
        showError({ ui: (resp && resp.ui) || null, rail, challenge: resp && resp.challenge });
      }
    } catch (e) {
      showError({
        ui: {
          headline: "The extension lost contact",
          detail: "Reload the page and try again.",
          retryable: true,
        },
      });
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
    button.addEventListener("click", () => scan());
    anchor.appendChild(button);
  }

  // Gmail re-renders its toolbar as you navigate; watch for it.
  const observer = new MutationObserver(() => mountButton());
  observer.observe(document.body, { childList: true, subtree: true });
  mountButton();
})();
