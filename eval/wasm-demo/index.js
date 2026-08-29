/**
 * Elcaro WASM eval — standalone browser scorer.
 *
 * Loads elcaro_eval.wasm, pulls the IPI corpus out of the module, sends each
 * case to a miner's /scan endpoint from this page (the module itself makes no
 * network calls — WASM can't, and that's the point: scoring runs entirely in
 * the browser), then hands the responses back to the module for scoring.
 *
 * Serve this directory over HTTP so fetch() works, e.g.:
 *   cd eval && python3 -m http.server 8080
 *   open http://localhost:8080/wasm-demo/
 */

const $ = (id) => document.getElementById(id);
const MINER_KEY = "elcaro-eval-miner-url";

let wasm = null;

async function loadWasm() {
  const res = await fetch("../target/wasm32-unknown-unknown/release/elcaro_eval.wasm");
  if (!res.ok) {
    throw new Error(
      `could not fetch elcaro_eval.wasm (${res.status}) — build it first: ` +
        "cargo build --target wasm32-unknown-unknown --release"
    );
  }
  const { instance } = await WebAssembly.instantiateStreaming(res, {});
  wasm = instance.exports;
  return wasm;
}

function readString(ptr, len) {
  return new TextDecoder().decode(new Uint8Array(wasm.memory.buffer, ptr, len));
}

function getCorpus() {
  const ol = wasm.elcaro_alloc(4);
  let ptr = 0;
  let len = 0;
  try {
    ptr = wasm.get_test_cases_ptr(ol);
    len = new Uint32Array(wasm.memory.buffer, ol, 1)[0];
    return JSON.parse(readString(ptr, len));
  } finally {
    if (ptr) wasm.elcaro_dealloc(ptr, len);
    wasm.elcaro_dealloc(ol, 4);
  }
}

function evaluate(responses) {
  const input = new TextEncoder().encode(JSON.stringify(responses));
  const inPtr = wasm.elcaro_alloc(input.length);
  const ol = wasm.elcaro_alloc(4);
  try {
    new Uint8Array(wasm.memory.buffer).set(input, inPtr);
    const outPtr = wasm.evaluate_ptr(inPtr, input.length, ol);
    const outLen = new Uint32Array(wasm.memory.buffer, ol, 1)[0];
    const result = JSON.parse(readString(outPtr, outLen));
    wasm.elcaro_dealloc(outPtr, outLen);
    return result;
  } finally {
    wasm.elcaro_dealloc(inPtr, input.length);
    wasm.elcaro_dealloc(ol, 4);
  }
}

function log(msg, cls = "") {
  const line = document.createElement("div");
  if (cls) line.className = cls;
  line.textContent = msg;
  $("log").appendChild(line);
  $("log").scrollTop = $("log").scrollHeight;
}

async function scanOne(baseUrl, testCase) {
  const res = await fetch(`${baseUrl}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: testCase.content, content_type: testCase.content_type }),
  });
  if (!res.ok) throw new Error(`${baseUrl}/scan returned ${res.status}`);
  return await res.json();
}

async function run() {
  $("log").textContent = "";
  const baseUrl = $("miner-url").value.trim().replace(/\/+$/, "");
  if (!baseUrl) {
    log("Enter a miner base URL first.", "err");
    return;
  }
  localStorage.setItem(MINER_KEY, baseUrl);

  if (!wasm) {
    log("Loading elcaro_eval.wasm…");
    try {
      await loadWasm();
    } catch (e) {
      log(String(e.message || e), "err");
      return;
    }
  }

  const corpus = getCorpus();
  log(`Corpus: ${corpus.length} cases (${wasm.test_case_count()} per module). Scoring ${baseUrl}…`);

  const responses = [];
  let failures = 0;
  for (const tc of corpus) {
    try {
      const resp = await scanOne(baseUrl, tc);
      responses.push({
        risk_score: resp.risk_score ?? 0,
        risk_level: resp.risk_level ?? "unknown",
        flagged_techniques: resp.flagged_techniques ?? [],
        indicators: resp.indicators ?? [],
      });
      log(`${tc.id}  score=${(resp.risk_score ?? 0).toFixed(2)}  expected=${tc.is_injection ? "INJECTION" : "clean"}`);
    } catch (e) {
      failures += 1;
      responses.push({ risk_score: 0, risk_level: "error", flagged_techniques: [], indicators: [] });
      log(`${tc.id}  FAILED: ${e.message}`, "err");
    }
  }

  const result = evaluate(responses);
  log("", "");
  log(`overall_score:       ${result.overall_score.toFixed(3)}`, "score");
  log(`passed:              ${result.passed_cases}/${result.total_cases}`);
  log(`true positive rate:  ${result.true_positive_rate.toFixed(3)}`);
  log(`true negative rate:  ${result.true_negative_rate.toFixed(3)}`);
  log(`false positive rate: ${result.false_positive_rate.toFixed(3)}`);
  log(`technique accuracy:  ${result.technique_accuracy.toFixed(3)}`);
  if (failures > 0) log(`(${failures} request(s) failed — scored as risk_score 0)`, "err");

  $("download").href = URL.createObjectURL(
    new Blob([JSON.stringify(result, null, 2)], { type: "application/json" })
  );
  $("download").hidden = false;
}

window.addEventListener("DOMContentLoaded", () => {
  $("miner-url").value =
    localStorage.getItem(MINER_KEY) || "https://api.elcaro.trustfall.xyz";
  $("run").addEventListener("click", () => run().catch((e) => log(String(e), "err")));
});
