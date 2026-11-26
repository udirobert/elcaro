import test from "node:test";
import assert from "node:assert/strict";
import { clientIpFromRequest, minerForwardHeaders } from "./miner-proxy.ts";

test("minerForwardHeaders without internal token only sets JSON content type", () => {
  delete process.env.ELCARO_INTERNAL_PROXY_TOKEN;
  const req = new Request("http://localhost/api/scan", {
    headers: { "x-forwarded-for": "203.0.113.10" },
  });
  assert.deepEqual(minerForwardHeaders(req, { premium: true }), {
    "Content-Type": "application/json",
  });
});

test("minerForwardHeaders asserts client IP and premium lane with token", () => {
  process.env.ELCARO_INTERNAL_PROXY_TOKEN = "unit-test-token";
  const req = new Request("http://localhost/api/x402/scan", {
    headers: {
      "x-forwarded-for": "203.0.113.10, 198.51.100.2",
      "x-nf-client-connection-ip": "203.0.113.10",
    },
  });
  assert.deepEqual(minerForwardHeaders(req, { premium: true }), {
    "Content-Type": "application/json",
    "x-elcaro-internal-token": "unit-test-token",
    "x-elcaro-premium": "1",
    "x-elcaro-client-ip": "203.0.113.10",
  });
  assert.equal(clientIpFromRequest(req), "203.0.113.10");
  delete process.env.ELCARO_INTERNAL_PROXY_TOKEN;
});

test("free browser lane explicitly remains non-premium", () => {
  process.env.ELCARO_INTERNAL_PROXY_TOKEN = "unit-test-token";
  const req = new Request("http://localhost/api/scan");
  assert.equal(minerForwardHeaders(req, { premium: false })["x-elcaro-premium"], "0");
  delete process.env.ELCARO_INTERNAL_PROXY_TOKEN;
});
