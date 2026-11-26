"""Offline tests for examples/gateway_wallet_boundary.py + tangem_catalog.py.

The catalog reader is injected — no network, no npx, no wallet. The catalog
SDK path IS exercised for real via a local stdio JSON-RPC fixture subprocess
(initialize + two-page tools/list), which catches startup and pagination
mistakes without any OAuth or external URL.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.signing import sha256_hex  # noqa: E402
from examples import gateway_wallet_boundary as demo  # noqa: E402
from examples import tangem_catalog as tc  # noqa: E402

# A minimal MCP stdio server: newline-delimited JSON-RPC over stdin/stdout.
# Answers initialize (echoing the client's protocolVersion), ignores the
# initialized notification, serves tools/list in two pages via cursor,
# rejects everything else.
_FIXTURE_SERVER = r"""
import json
import sys

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    req = json.loads(line)
    mid = req.get("id")
    method = req.get("method")
    if method == "initialize":
        resp = {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": req["params"]["protocolVersion"],
                "capabilities": {},
                "serverInfo": {"name": "fixture", "version": "0"},
            },
        }
    elif method == "notifications/initialized":
        continue
    elif method == "ping":
        resp = {"jsonrpc": "2.0", "id": mid, "result": {}}
    elif method == "tools/list":
        cursor = (req.get("params") or {}).get("cursor")
        if cursor is None:
            resp = {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "tools": [
                        {"name": "alpha", "description": "first tool", "inputSchema": {"type": "object", "properties": {}}},
                        {"name": "beta", "description": "second tool", "inputSchema": {"type": "object", "properties": {}}},
                    ],
                    "nextCursor": "page-2",
                },
            }
        elif cursor == "page-2":
            resp = {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {"tools": [{"name": "gamma", "description": "third tool", "inputSchema": {"type": "object", "properties": {}}}]},
            }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": mid,
                "error": {"code": -32602, "message": "bad cursor"},
            }
    else:
        resp = {
            "jsonrpc": "2.0",
            "id": mid,
            "error": {"code": -32601, "message": "method not supported"},
        }
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()
"""


def _fixture_params():
    mcp = pytest.importorskip("mcp")  # needs the mcp extra, not the network
    return mcp.StdioServerParameters(command=sys.executable, args=["-c", _FIXTURE_SERVER])


def test_sdk_read_paginates_two_pages():
    catalog = asyncio.run(asyncio.wait_for(tc._read(_fixture_params()), timeout=30))
    assert catalog == [
        {"name": "alpha", "description": "first tool"},
        {"name": "beta", "description": "second tool"},
        {"name": "gamma", "description": "third tool"},
    ]


def test_cimd_args_order_and_validation(monkeypatch):
    monkeypatch.delenv("TANGEM_CLIENT_METADATA_URL", raising=False)
    monkeypatch.delenv("TANGEM_CALLBACK_PORT", raising=False)
    assert tc._client_metadata_args() == []
    monkeypatch.setenv("TANGEM_CLIENT_METADATA_URL", "https://app.example/cimd.json")
    with pytest.raises(tc.CatalogError):  # port required too
        tc._client_metadata_args()
    monkeypatch.setenv("TANGEM_CALLBACK_PORT", "8085")
    assert tc._client_metadata_args() == [
        "8085",
        "--client-metadata-url",
        "https://app.example/cimd.json",
    ]
    monkeypatch.setenv("TANGEM_CLIENT_METADATA_URL", "https://app.example/x?token=1")
    with pytest.raises(tc.CatalogError):
        tc._client_metadata_args()
    monkeypatch.setenv("TANGEM_CLIENT_METADATA_URL", "http://app.example/x")
    with pytest.raises(tc.CatalogError):
        tc._client_metadata_args()
    monkeypatch.setenv("TANGEM_CLIENT_METADATA_URL", "https://app.example/x")
    monkeypatch.setenv("TANGEM_CALLBACK_PORT", "80")
    with pytest.raises(tc.CatalogError):
        tc._client_metadata_args()


class SpyReader:
    def __init__(self, catalog: list[dict[str, str]] | None = None):
        self.catalog = (
            catalog
            if catalog is not None
            else [{"name": "get_wallet_info", "description": "Read wallet metadata."}]
        )
        self.calls = 0

    def __call__(self) -> list[dict[str, str]]:
        self.calls += 1
        return self.catalog


class FakeResponse:
    def __init__(self, status_code: int, headers: dict, body):
        self.status_code = status_code
        self.headers = headers
        self._body = body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def _clean_response() -> FakeResponse:
    receipt = {
        "payload": json.dumps(
            {
                "content_sha256": sha256_hex(sha256_hex(demo.CLEAN)),
                "quarantined": False,
                "risk_level": "safe",
            }
        ),
        "signature": "c2ln",
    }
    body = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "ok"},
            }
        ],
        "elcaro": {
            "mode": "block",
            "action": "none",
            "verdict": "clean",
            "parts": [
                {
                    "path": "messages[2]",
                    "content_sha256": sha256_hex(demo.CLEAN),
                    "action": "none",
                    "risk_level": "safe",
                    "quarantined": False,
                }
            ],
            "receipt": receipt,
        },
    }
    return FakeResponse(
        200,
        {
            "x-elcaro-action": "none",
            "x-elcaro-scanned": "1",
            "x-elcaro-verdict": "clean",
        },
        body,
    )


def test_baseline_no_reader_still_passes():
    assert demo.run(auto=True) == 0


def test_reader_called_exactly_once_on_clean():
    spy = SpyReader()
    assert demo.run(auto=True, catalog_reader=spy) == 0
    assert spy.calls == 1


def test_flagged_catalog_descriptor_is_blocked_not_dispatch_failure():
    """A canary in external metadata → the same Gateway blocks it; that's a
    valid outcome (refusal, no model call), not a crash."""
    spy = SpyReader([{"name": "swap", "description": demo.FLAGGED}])
    assert demo.run(auto=True, catalog_reader=spy) == 0
    assert spy.calls == 1


def test_gate_denies_invalid_receipt():
    spy = SpyReader()
    assert demo.after_verdict(_clean_response(), False, spy, demo.CLEAN) is None
    assert spy.calls == 0


def test_gate_denies_bypassed_and_flagged_actions():
    spy = SpyReader()
    for action in ("bypassed", "blocked", "warned", "quarantined"):
        resp = _clean_response()
        resp.headers["x-elcaro-action"] = action
        assert demo.after_verdict(resp, True, spy, demo.CLEAN) is None
    assert spy.calls == 0


def test_gate_denies_wrong_mode_refusal_and_tool_calls():
    spy = SpyReader()
    resp = _clean_response()
    resp._body["elcaro"]["mode"] = "warn"
    assert demo.after_verdict(resp, True, spy, demo.CLEAN) is None
    resp = _clean_response()
    resp._body["choices"][0]["finish_reason"] = "content_filter"
    assert demo.after_verdict(resp, True, spy, demo.CLEAN) is None
    resp = _clean_response()
    resp._body["choices"][0]["message"]["tool_calls"] = [{"id": "x"}]
    assert demo.after_verdict(resp, True, spy, demo.CLEAN) is None
    resp = _clean_response()
    resp._body["elcaro"]["parts"][0]["quarantined"] = True
    assert demo.after_verdict(resp, True, spy, demo.CLEAN) is None
    assert spy.calls == 0


def test_gate_denies_missing_or_malformed_fields():
    spy = SpyReader()
    assert demo.after_verdict(FakeResponse(500, {}, {}), True, spy, demo.CLEAN) is None
    assert (
        demo.after_verdict(
            FakeResponse(
                200,
                {"x-elcaro-action": "none"},
                json.JSONDecodeError("x", "y", 0),
            ),
            True,
            spy,
            demo.CLEAN,
        )
        is None
    )
    for mutate in (
        lambda b: b["elcaro"].pop("receipt"),
        lambda b: b["elcaro"].pop("mode"),
        lambda b: b["elcaro"]["parts"].pop(0),
        lambda b: b["elcaro"]["parts"][0].pop("quarantined"),
        lambda b: b.pop("choices"),
    ):
        resp = _clean_response()
        mutate(resp._body)
        assert demo.after_verdict(resp, True, spy, demo.CLEAN) is None
    wrong_note = _clean_response()
    assert demo.after_verdict(wrong_note, True, spy, "different note") is None
    assert spy.calls == 0


def test_gate_dispatches_on_fully_clean_response():
    spy = SpyReader()
    assert demo.after_verdict(_clean_response(), True, spy, demo.CLEAN) == spy.catalog
    assert spy.calls == 1
