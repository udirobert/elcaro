import test from "node:test";
import assert from "node:assert/strict";
import { cleanEvents } from "../../../lib/analytics-clean.ts";

test("cleanEvents keeps allowed funnel metadata and strips sensitive props", () => {
  const now = Date.now();
  const [event] = cleanEvents([{
    type: "scan.verdict",
    _ts: now,
    _session: "test-session-123456",
    _page: "/scan?example=remit-swap#fragment",
    risk_level: "dangerous",
    risk_score: 0.91,
    content: "user content must never be stored",
    token: "secret must never be stored",
    key: "secret must never be stored",
  }]);

  assert.ok(event);
  assert.equal(event.event, "scan.verdict");
  assert.equal(event.page, "/scan");
  assert.deepEqual(event.props, { risk_level: "dangerous", risk_score: 0.91 });
  assert.match(event.sessionHash ?? "", /^[a-f0-9]{64}$/);
  assert.notEqual(event.sessionHash, "test-session-123456");
  assert.ok(event.clientTs instanceof Date);
});

test("cleanEvents rejects unknown event types", () => {
  assert.equal(cleanEvents([{ type: "scan.content", content: "x" }]).length, 0);
  assert.equal(cleanEvents([{ type: "admin.raw_ip", ip: "1.1.1.1" }]).length, 0);
});

test("cleanEvents caps a flush at twenty events", () => {
  const events = Array.from({ length: 25 }, () => ({
    type: "landing.viewed",
    _ts: Date.now(),
    _session: "test-session-123456",
    _page: "/",
  }));
  assert.equal(cleanEvents(events).length, 20);
});
