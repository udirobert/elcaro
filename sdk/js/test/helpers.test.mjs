import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  ELCARO_GATEWAY_URL,
  elcaroHeaders,
  untrusted,
  untrustedHeader,
  verdictFromHeaders,
} from "../dist/index.js";

describe("elcaroHeaders", () => {
  it("carries the elcaro key + upstream key", () => {
    const h = elcaroHeaders({ elcaroKey: "elk_a", upstreamKey: "sk-b" });
    assert.equal(h["x-elcaro-key"], "elk_a");
    assert.equal(h["x-upstream-key"], "sk-b");
  });

  it("omits x-upstream-key when unset (gateway's own upstream env applies)", () => {
    const h = elcaroHeaders({ elcaroKey: "elk_a" });
    assert.equal(h["x-elcaro-key"], "elk_a");
    assert.ok(!("x-upstream-key" in h));
  });

  it("throws a helpful error with no key", () => {
    const saved = process.env.ELCARO_API_KEY;
    delete process.env.ELCARO_API_KEY;
    assert.throws(() => elcaroHeaders({}), /ELCARO_API_KEY/);
    if (saved !== undefined) process.env.ELCARO_API_KEY = saved;
  });

  it("reads ELCARO_API_KEY from env", () => {
    const saved = process.env.ELCARO_API_KEY;
    process.env.ELCARO_API_KEY = "elk_env"; // pragma: allowlist secret
    assert.equal(elcaroHeaders({})["x-elcaro-key"], "elk_env");
    if (saved === undefined) delete process.env.ELCARO_API_KEY;
    else process.env.ELCARO_API_KEY = saved;
  });
});

describe("untrusted markers (§2.4)", () => {
  it("builds the msg: header vocabulary", () => {
    assert.equal(untrustedHeader(0, 2), "msg:0,2");
  });

  it("marks a content part the gateway strips before forwarding", () => {
    assert.deepEqual(untrusted("doc body"), {
      type: "text",
      text: "doc body",
      elcaro: { untrusted: true },
    });
  });
});

describe("verdictFromHeaders (§2.7)", () => {
  it("parses the full header set", () => {
    const h = new Headers({
      "x-elcaro-verdict": "dangerous",
      "x-elcaro-action": "quarantined",
      "x-elcaro-scanned": "3",
      "x-elcaro-receipt": "b64sig",
      "x-elcaro-cost-usdc": "0.010000",
      "x-elcaro-incident": "https://gateway.elcaro.trustfall.xyz/i/abc",
    });
    assert.deepEqual(verdictFromHeaders(h), {
      verdict: "dangerous",
      action: "quarantined",
      scanned: 3,
      receipt: "b64sig",
      costUsdc: "0.010000",
      incident: "https://gateway.elcaro.trustfall.xyz/i/abc",
    });
  });

  it("returns undefineds for absent headers", () => {
    const v = verdictFromHeaders(new Headers());
    assert.equal(v.action, undefined);
    assert.equal(v.scanned, undefined);
  });
});

describe("exports", () => {
  it("advertises the production gateway URL", () => {
    assert.equal(ELCARO_GATEWAY_URL, "https://gateway.elcaro.trustfall.xyz");
  });
});
