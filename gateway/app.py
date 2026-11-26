"""Elcaro Gateway — the drop-in proxy (docs/roadmap-gateway.md §2).

A customer adopts Elcaro by changing one base URL: their OpenAI/Anthropic
client points here instead of the provider, the Gateway scans the untrusted
parts of the request (tool results, retrieved content), applies the shared
policy engine (C1), forwards to the key's allowlisted upstream, and returns
the provider-shaped response plus Elcaro metadata.

Endpoints (§2.2):
    POST /v1/chat/completions   OpenAI-compatible chat (SERV, OpenAI,
                              OpenRouter, HF upstreams)
    POST /v1/messages           Anthropic-compatible chat (Anthropic upstream)
    GET  /v1/models             passthrough model listing
    GET  /health                liveness
    GET  /metrics               per-key + aggregate counters
    GET  /incidents/{id}        autopsy for a flagged part
    GET  /pubkey, POST /verify  receipt trust anchor (same scheme as the miner)

Deploy configuration (env — Dev C's deploy lane wires these):
    ELCARO_SIGNING_KEY            Ed25519 key for x-elcaro-receipt (unsigned when unset)
    ELCARO_GATEWAY_PRICE_USDC     per-request charge recorded in usage events (default 0);
                                  when >0 it also sets the pay-per-call offer amount
    ELCARO_UPSTREAM_<NAME>_URL    add/override an upstream allowlist entry
    SERV_*                        same engine env as the miner (deep_analysis second pass)

    x402 pay-per-call (C3, docs/x402-gateway.md) — armed only when a payTo
    resolves AND a server-side upstream credential is configured:
    X402_PAYTO / TELEGRAPH_X402_KEY   payTo resolution (explicit address wins)
    X402_SCAN_AMOUNT                  atomic USDC per call (default 10000 = $0.01)
    X402_FACILITATOR_URL              settlement endpoint (best-effort post-serve;
                                      unset → verified_local, nothing settles)
    ELCARO_PAYPERCALL_UPSTREAM        upstream for paid calls (default "serv")
    ELCARO_PAYPERCALL_MODE            policy mode for paid calls (default quarantine)
    ELCARO_UPSTREAM_KEY_<NAME>        server-held credential for paid calls
                                      (SERV_API_KEY fallback when upstream=serv)

Run:  uvicorn gateway.app:app
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTasks

from core import x402
from core.autopsy import summarize as summarize_autopsy
from core.policy import FLAG_THRESHOLD, Mode, PartVerdict, PolicyResult, Provider, apply_policy
from core.signing import VerdictSigner, canonical_verdict_payload, sha256_hex, verify_verdict
from core.usage import KeyConfig, UsageEvent, emit_usage, get_key, record_settlement
from gateway.blocks import anthropic_block_response, openai_block_response, provider_error
from gateway.upstream import (
    ROUTE_PATHS,
    extract_keys,
    load_upstreams,
    resolve_upstream,
    upstream_headers,
)

# ── Bounds & defaults ─────────────────────────────────────────────────────────

MAX_BODY_BYTES = 2 * 1024 * 1024  # §2.5 bound — 413 beyond this
UPSTREAM_TIMEOUT = httpx.Timeout(120.0, connect=15.0)
_ANTHROPIC_UPSTREAM = "anthropic"
_SERV_UPSTREAM = "serv"

_UNTRUSTED_HDR_RE = re.compile(r"^msg:(\d+)$")
_PART_PATH_RE = re.compile(r"^messages\[(\d+)\](?:\.content\[(\d+)\])?$")

_ACTION_ORDER = {"none": 0, "warned": 1, "quarantined": 2, "blocked": 3, "bypassed": 4}


# ── Metrics ───────────────────────────────────────────────────────────────────


@dataclass
class KeyMetrics:
    """Per-key counters — the metering preview until C2's Neon sink lands."""

    requests: int = 0
    parts_scanned: int = 0
    actions: dict[str, int] = field(default_factory=dict)
    verdicts: dict[str, int] = field(default_factory=dict)

    def record(self, action: str, verdict: str | None, parts: int) -> None:
        self.requests += 1
        self.parts_scanned += parts
        self.actions[action] = self.actions.get(action, 0) + 1
        if verdict is not None:
            self.verdicts[verdict] = self.verdicts.get(verdict, 0) + 1


@dataclass
class GatewayMetrics:
    """In-memory counters — per-key for metering, aggregate for ops (§2.2)."""

    total_requests: int = 0
    total_errors: int = 0
    per_key: dict[str, KeyMetrics] = field(default_factory=dict)
    latencies_ms_elcaro: deque = field(default_factory=lambda: deque(maxlen=1000))
    latencies_ms_upstream: deque = field(default_factory=lambda: deque(maxlen=1000))
    started_at: float = field(default_factory=time.time)

    def record(self, key_id: str, action: str, verdict: str | None, parts: int) -> None:
        self.per_key.setdefault(key_id, KeyMetrics()).record(action, verdict, parts)

    @staticmethod
    def _pct(lat: deque) -> dict:
        s = sorted(lat)
        n = len(s)
        if not n:
            return {"p50": 0, "p90": 0, "p99": 0, "avg": 0, "samples": 0}
        return {
            "p50": round(s[n // 2], 2),
            "p90": round(s[int(n * 0.9)], 2),
            "p99": round(s[int(n * 0.99)], 2),
            "avg": round(sum(s) / n, 2),
            "samples": n,
        }

    def to_dict(self) -> dict:
        return {
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "latency_ms": {
                "elcaro": self._pct(self.latencies_ms_elcaro),
                "upstream": self._pct(self.latencies_ms_upstream),
            },
            "per_key": {
                kid: {
                    "requests": m.requests,
                    "parts_scanned": m.parts_scanned,
                    "actions": dict(m.actions),
                    "verdicts": dict(m.verdicts),
                }
                for kid, m in sorted(self.per_key.items())
            },
        }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _worst_action(parts: list[PartVerdict]) -> str:
    return max((p.action for p in parts), key=lambda a: _ACTION_ORDER.get(a, 0), default="none")


def _verdict_label(result: PolicyResult) -> str:
    """Map a PolicyResult to the §2.7 header vocabulary."""
    if result.blocked or any(p.scan.quarantined for p in result.parts):
        return "dangerous"
    if any(p.scan.risk_score >= FLAG_THRESHOLD for p in result.parts):
        return "suspicious"
    return "clean"


def _parse_untrusted_header(value: str) -> set[str]:
    """``x-elcaro-untrusted: msg:0,2`` → {'messages[0]', 'messages[2]'} (§2.4)."""
    paths = set()
    for token in value.split(","):
        token = token.strip()
        m = _UNTRUSTED_HDR_RE.match(token)
        if not m:
            raise ValueError(f"invalid x-elcaro-untrusted token {token!r} — expected msg:<index>")
        paths.add(f"messages[{m.group(1)}]")
    return paths


def _part_text(messages: list[dict], path: str) -> str | None:
    """Recover the pre-rewrite text for a PartVerdict path (autopsy input)."""
    m = _PART_PATH_RE.match(path)
    if not m:
        return None
    try:
        msg = messages[int(m.group(1))]
        content = msg.get("content")
        if m.group(2) is not None:
            block = content[int(m.group(2))]
            return block.get("text") if isinstance(block, dict) else None
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    except (IndexError, TypeError, AttributeError):
        return None
    return None


def _inject_serv_tools(body: dict, shadow_hint: str | None) -> None:
    """§2.6: ensure serv_prompt_guard (and optional shadow agent) are declared.

    Only runs on the OpenAI-dialect route headed for the SERV upstream.
    Never adds serv_prompt_guard_legacy — SERV rejects it alongside the
    modern tool, so a caller-declared legacy suppresses injection of both.
    """
    tools = body.setdefault("tools", [])
    declared = {t.get("function", {}).get("name") for t in tools if isinstance(t, dict)}
    if "serv_prompt_guard" not in declared and "serv_prompt_guard_legacy" not in declared:
        tools.append(
            {
                "type": "function",
                "function": {"name": "serv_prompt_guard"},
            }
        )
    if shadow_hint and "serv_shadow_agent" not in declared:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "serv_shadow_agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hint": {"type": "string", "default": shadow_hint},
                            "max_iterations": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 10,
                                "default": 3,
                            },
                        },
                    },
                },
            }
        )


def _part_summary(part: PartVerdict) -> dict:
    """The per-part verdict surface for the ``elcaro`` body object."""
    scan = part.scan
    return {
        "path": part.path,
        "content_type": part.content_type.value,
        "content_sha256": part.content_sha256,
        "action": part.action,
        "risk_score": scan.risk_score,
        "risk_level": scan.risk_level.value,
        "quarantined": scan.quarantined,
        "flagged_techniques": [t.value for t in scan.flagged_techniques],
        "summary": scan.human_summary,
        "indicators": [
            {
                "technique": ind.technique_name,
                "severity": ind.severity.value,
                "explanation": ind.explanation,
            }
            for ind in scan.indicators
        ],
    }


def _serv_tokens(parts: list[PartVerdict]) -> tuple[int | None, int | None]:
    """Sum second-pass SERV token use across parts (when deep_analysis ran)."""
    in_tok = out_tok = 0
    seen = False
    for p in parts:
        cost = p.scan.serv_cost or {}
        if p.scan.serv_used and cost:
            seen = True
            in_tok += int(cost.get("input_tokens", 0))
            out_tok += int(cost.get("output_tokens", 0))
    return (in_tok, out_tok) if seen else (None, None)


# ── App factory ───────────────────────────────────────────────────────────────

_SIGNER_ENV = object()  # sentinel: resolve VerdictSigner.from_env()


def create_app(
    *,
    engine=None,
    key_lookup=get_key,
    upstreams: dict[str, str] | None = None,
    signer: Any = _SIGNER_ENV,
    http_client_factory=None,
    price_per_request: Decimal | None = None,
    max_body_bytes: int = MAX_BODY_BYTES,
    x402_offers: list[x402.Accept] | None = None,
    x402_nonce_store: x402.NonceStore | None = None,
    x402_facilitator: x402.FacilitatorClient | None = None,
    paypercall_upstream: str | None = None,
    paypercall_upstream_key: str | None = None,
    paypercall_mode: Mode | None = None,
) -> FastAPI:
    """Build the Gateway app.

    Args:
        engine: Detection engine override (tests/benchmarks). Default: the
            env-configured shared engine inside ``apply_policy``.
        key_lookup: raw key -> KeyConfig | None (C2 ``get_key``; Dev C swaps
            the store behind it).
        upstreams: allowlist map; defaults to ``load_upstreams()``.
        signer: VerdictSigner, None to disable receipts, or omit to use
            ``ELCARO_SIGNING_KEY``.
        http_client_factory: returns an ``httpx.AsyncClient`` (tests inject
            a MockTransport client here). Default: one shared client.
        price_per_request: Elcaro charge per proxied request; env
            ``ELCARO_GATEWAY_PRICE_USDC`` when unset.
        max_body_bytes: request body cap (§2.5).
        x402_offers: accept list for the pay-per-call challenge; ``None``
            resolves ``x402.offers()`` from env (``X402_PAYTO`` /
            ``TELEGRAPH_X402_KEY`` + ``X402_SCAN_AMOUNT``), ``[]`` disables
            the x402 lane outright.
        x402_nonce_store: replay guard; default ``InMemoryNonceStore``.
        x402_facilitator: settlement client override (tests); ``None`` →
            ``X402_FACILITATOR_URL`` env, unset → ``verified_local``.
        paypercall_upstream/paypercall_mode: upstream name and policy mode
            for paid calls (env ``ELCARO_PAYPERCALL_UPSTREAM`` /
            ``ELCARO_PAYPERCALL_MODE``; defaults ``serv`` / quarantine).
        paypercall_upstream_key: server-held credential sent upstream on
            paid calls; env ``ELCARO_UPSTREAM_KEY_<NAME>`` then
            ``SERV_API_KEY`` when the upstream is serv.
    """
    upstream_map = upstreams if upstreams is not None else load_upstreams()
    resolved_signer = VerdictSigner.from_env() if signer is _SIGNER_ENV else signer
    price = (
        Decimal(os.environ.get("ELCARO_GATEWAY_PRICE_USDC", "0"))
        if price_per_request is None
        else price_per_request
    )

    # ── x402 pay-per-call resolution (C3) ─────────────────────────────
    # The lane is armed only when it can issue offers AND serve paid calls:
    # a resolvable payTo plus a server-held upstream credential. Otherwise
    # unauthenticated callers keep getting the plain 401.
    if x402_offers is not None:
        x402_offer_list = x402_offers
    else:
        atomic = str(int(price * 1_000_000)) if price > 0 else None
        x402_offer_list = x402.offers(amount=atomic)
    ppc_upstream = paypercall_upstream or os.environ.get(
        "ELCARO_PAYPERCALL_UPSTREAM", _SERV_UPSTREAM
    )
    ppc_upstream_key = (
        paypercall_upstream_key
        or os.environ.get(f"ELCARO_UPSTREAM_KEY_{ppc_upstream.upper()}")
        or (os.environ.get("SERV_API_KEY") if ppc_upstream == _SERV_UPSTREAM else None)
    )
    if paypercall_mode is not None:
        ppc_mode = paypercall_mode
    else:
        try:
            ppc_mode = Mode(os.environ.get("ELCARO_PAYPERCALL_MODE", "quarantine"))
        except ValueError:
            ppc_mode = Mode.QUARANTINE
    nonce_store = x402_nonce_store if x402_nonce_store is not None else x402.InMemoryNonceStore()
    x402_ready = bool(x402_offer_list) and bool(ppc_upstream_key) and ppc_upstream in upstream_map
    client_factory = http_client_factory or (lambda: httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT))
    metrics = GatewayMetrics()
    incidents: OrderedDict[str, dict] = OrderedDict()  # id -> autopsy summary
    _INCIDENT_CAP = 512

    # Shared upstream client (connection reuse keeps Elcaro overhead inside
    # the <15ms p95 budget, §2.5). Created lazily, closed on shutdown.
    _client: httpx.AsyncClient | None = None

    def _get_client() -> httpx.AsyncClient:
        nonlocal _client
        if _client is None:
            _client = client_factory()
        return _client

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        # Dev C's Neon C2 store (contract C2): installs itself as the
        # process-wide usage sink + key store when ELCARO_METERING_DSN (or
        # ELCARO_CANARY_DSN) is set. No DSN → keep the in-memory stubs.
        # A bad DSN raises here and fails the boot — a misconfigured paid
        # lane must never silently run unmetered.
        from metering import install_from_env

        install_from_env()
        yield
        if _client is not None:
            await _client.aclose()

    app = FastAPI(
        lifespan=_lifespan,
        title="Elcaro Gateway",
        description=(
            "Drop-in prompt-injection firewall for OpenAI and Anthropic clients. "
            "Change your base URL; Elcaro scans the untrusted parts of each "
            "request, rewrites or blocks per your key's policy mode, and "
            "forwards to your allowlisted upstream."
        ),
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Error helpers ─────────────────────────────────────────────────────

    def _err(
        status: int, message: str, *, anthropic: bool, err_type: str = "invalid_request_error"
    ) -> JSONResponse:
        metrics.total_errors += 1
        return JSONResponse(
            status_code=status,
            content=provider_error(anthropic, message, err_type, status),
        )

    # ── Receipt + header + incident assembly ──────────────────────────────

    def _receipt(parts: list[PartVerdict], result: PolicyResult) -> dict | None:
        """Build the signed request receipt (payload + signature) or None."""
        if resolved_signer is None:
            return None
        part_hashes = sorted(p.content_sha256 for p in parts)
        techniques = sorted({t.value for p in parts for t in p.scan.flagged_techniques})
        payload = canonical_verdict_payload(
            content_sha256=sha256_hex(":".join(part_hashes)),
            risk_score=max((p.scan.risk_score for p in parts), default=0.0),
            risk_level=result.overall.value,
            quarantined=result.blocked or any(p.action == "quarantined" for p in parts),
            flagged_techniques=techniques,
            scanned_at=int(time.time()),
        )
        sig_hex = resolved_signer.sign(payload)
        return {
            "payload": payload.decode("utf-8"),
            "signature": base64.b64encode(bytes.fromhex(sig_hex)).decode("ascii"),
            "key_id": resolved_signer.key_id,
        }

    def _record_incidents(parts: list[PartVerdict], original_messages: list[dict]) -> str | None:
        """Autopsy every non-none part; return the worst part's incident URL."""
        worst_path: str | None = None
        worst_rank = -1
        for part in parts:
            if part.action == "none":
                continue
            text = _part_text(original_messages, part.path)
            incident_id = part.content_sha256[:16]
            incidents[incident_id] = {
                "path": part.path,
                "action": part.action,
                "content_sha256": part.content_sha256,
                "scan": _part_summary(part),
                "autopsy": summarize_autopsy(part.scan, text or ""),
                "ts": datetime.now(UTC).isoformat(),
            }
            incidents.move_to_end(incident_id)
            if len(incidents) > _INCIDENT_CAP:
                incidents.popitem(last=False)
            rank = _ACTION_ORDER.get(part.action, 0)
            if rank > worst_rank:
                worst_rank, worst_path = rank, incident_id
        return f"/incidents/{worst_path}" if worst_path else None

    def _elcaro_headers(
        *,
        action: str,
        verdict: str | None,
        scanned: int,
        cost: Decimal,
        receipt: dict | None,
        incident_url: str | None,
    ) -> dict[str, str]:
        headers = {
            "x-elcaro-action": action,
            "x-elcaro-scanned": str(scanned),
            "x-elcaro-cost-usdc": str(cost),
        }
        if verdict is not None:
            headers["x-elcaro-verdict"] = verdict
        if receipt is not None:
            headers["x-elcaro-receipt"] = receipt["signature"]
        if incident_url is not None:
            headers["x-elcaro-incident"] = incident_url
        return headers

    def _elcaro_object(
        result: PolicyResult,
        mode: Mode,
        action: str,
        verdict: str,
        receipt: dict | None,
        incident_url: str | None,
    ) -> dict:
        obj = {
            "mode": mode.value,
            "action": action,
            "verdict": verdict,
            "parts": [_part_summary(p) for p in result.parts],
        }
        if receipt is not None:
            obj["receipt"] = receipt
        if incident_url is not None:
            obj["incident"] = incident_url
        return obj

    def _emit_usage(
        *,
        key_id: str,
        route: str,
        provider: Provider,
        upstream: str,
        result: PolicyResult | None,
        action: str,
        t_elcaro_ms: float,
        t_upstream_ms: float,
        charge: Decimal,
        payment: dict | None = None,
    ) -> None:
        in_tok, out_tok = _serv_tokens(result.parts) if result else (None, None)
        payment_fields = (
            {
                # The row starts pending; the post-serve background task
                # rewrites settlement_status (and the tx hash) by event_id.
                "event_id": payment["event_id"],
                "payer_address": payment.get("payer"),
                "payment_network": payment.get("network"),
                "settlement_status": "pending",
            }
            if payment
            else {}
        )
        emit_usage(
            UsageEvent(
                key_id=key_id,
                ts=datetime.now(UTC),
                route=route,
                provider=provider.value,
                upstream=upstream,
                parts_scanned=len(result.parts) if result else 0,
                action=action,
                overall=result.overall.value if result else "unknown",
                latency_ms_elcaro=round(t_elcaro_ms, 2),
                latency_ms_upstream=round(t_upstream_ms, 2),
                serv_input_tokens=in_tok,
                serv_output_tokens=out_tok,
                charge_usdc=charge,
                **payment_fields,
            )
        )

    # ── x402 pay-per-call gate (C3, docs/x402-gateway.md) ─────────────
    #
    # A caller without an Elcaro key gets a 402 challenge instead of a 401
    # when the lane is armed. A verified PAYMENT-SIGNATURE / X-PAYMENT is
    # served on an ephemeral key config — upstream is Elcaro's own
    # credential, the charge is what the payer actually authorized — and
    # settlement is deferred to a background task after the response is
    # built (route.ts order: verify -> serve -> settle).

    def _x402_gate(request: Request, *, is_anthropic: bool):
        """Return a 402/401 Response, or
        (key_cfg, upstream_key, payment, charge, settle_task)."""
        if not x402_ready:
            return _err(
                401,
                "Missing Elcaro key — send it as x-elcaro-key.",
                anthropic=is_anthropic,
                err_type="authentication_error",
            )
        resource = {
            "url": str(request.url),
            "description": "Elcaro gateway pay-per-call",
            "mimeType": "application/json",
        }

        def _challenge(error: str | None = None) -> JSONResponse:
            challenge = x402.challenge_body(resource, x402_offer_list, error)
            return JSONResponse(
                status_code=402,
                content=challenge,
                headers={"PAYMENT-REQUIRED": x402.encode_challenge_header(challenge)},
            )

        raw = request.headers.get("payment-signature") or request.headers.get("x-payment")
        if raw is None:
            return _challenge()
        payment = x402.decode_payment_header(raw)
        if payment is None:
            return _challenge("malformed payment payload")
        result = x402.verify_payment(payment, x402_offer_list, nonce_store)
        if not result.ok:
            return _challenge(result.reason)

        key_cfg = KeyConfig(
            key_id=f"x402:{result.payer}",  # ephemeral id — no api_keys row
            mode=ppc_mode,
            upstream=ppc_upstream,
        )
        # Correlation id shared by the usage row (emitted later in the
        # request) and the post-serve settlement update below.
        event_id = uuid4().hex

        def _settle_and_record() -> None:
            res = x402.settle_via_facilitator(payment, result.accept, x402_facilitator)
            if res.settled:
                status = "settled"
            elif res.detail == "verified_local":
                status = "verified_local"
            else:
                status = "failed"
            record_settlement(event_id, tx_hash=res.tx_hash, status=status)

        settle = BackgroundTasks()
        settle.add_task(_settle_and_record)
        charge = Decimal(result.accept.amount) / Decimal(1_000_000)
        payment_meta = {
            "event_id": event_id,
            "payer": result.payer,
            "network": result.accept.network,
        }
        return key_cfg, ppc_upstream_key, payment, charge, settle, payment_meta

    # ── The shared proxy path ─────────────────────────────────────────────

    async def _proxy(request: Request, *, provider: Provider, route_name: str) -> Response:
        is_anthropic = provider is Provider.ANTHROPIC
        route = f"/v1/{ROUTE_PATHS[route_name]}"

        elcaro_key, upstream_key = extract_keys(request.headers)
        settle_bg: BackgroundTasks | None = None
        payment_meta: dict | None = None
        charge = price
        if elcaro_key is not None:
            key_cfg = key_lookup(elcaro_key)
            if key_cfg is None:
                return _err(
                    401,
                    "Unknown Elcaro key.",
                    anthropic=is_anthropic,
                    err_type="authentication_error",
                )
            if upstream_key is None:
                return _err(
                    401,
                    "Missing upstream credential — Authorization: Bearer, "
                    "x-upstream-key, or x-api-key.",
                    anthropic=is_anthropic,
                    err_type="authentication_error",
                )
        else:
            gate = _x402_gate(request, is_anthropic=is_anthropic)
            if isinstance(gate, Response):
                return gate
            key_cfg, upstream_key, _payment, charge, settle_bg, payment_meta = gate

        body_bytes = await request.body()
        if len(body_bytes) > max_body_bytes:
            return _err(413, "Request body exceeds the 2MB limit.", anthropic=is_anthropic)
        try:
            body = json.loads(body_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _err(400, "Request body is not valid JSON.", anthropic=is_anthropic)
        if not isinstance(body, dict):
            return _err(400, "Request body must be a JSON object.", anthropic=is_anthropic)

        upstream_name = key_cfg.upstream
        base = resolve_upstream(upstream_name, upstream_map)
        if base is None:
            return _err(
                502,
                f"Key upstream {upstream_name!r} is not in the allowlist.",
                anthropic=is_anthropic,
            )
        # Dialect gate: /v1/messages only reaches an Anthropic upstream;
        # /v1/chat/completions only reaches OpenAI-compatible upstreams.
        if is_anthropic != (upstream_name == _ANTHROPIC_UPSTREAM):
            return _err(
                400,
                f"Route {route} does not match upstream {upstream_name!r}.",
                anthropic=is_anthropic,
            )

        mode_raw = request.headers.get("x-elcaro-mode")
        if mode_raw is not None:
            try:
                mode = Mode(mode_raw.strip().lower())
            except ValueError:
                return _err(
                    400,
                    f"Invalid x-elcaro-mode {mode_raw!r} — observe|warn|quarantine|block.",
                    anthropic=is_anthropic,
                )
        else:
            mode = key_cfg.mode

        untrusted_paths: set[str] | None = None
        untrusted_raw = request.headers.get("x-elcaro-untrusted")
        if untrusted_raw:
            try:
                untrusted_paths = _parse_untrusted_header(untrusted_raw)
            except ValueError as exc:
                return _err(400, str(exc), anthropic=is_anthropic)

        messages = body.get("messages")
        if not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages):
            return _err(400, "Request body must contain a messages array.", anthropic=is_anthropic)

        t0 = time.perf_counter()

        # §2.6 — SERV tool injection before scanning (tools are not
        # scanned surface; injection doesn't alter verdicts).
        if not is_anthropic and upstream_name == _SERV_UPSTREAM:
            _inject_serv_tools(body, key_cfg.serv_shadow_hint)

        # ── Policy (C1) — the Elcaro work ─────────────────────────────
        result: PolicyResult | None = None
        bypassed = False
        try:
            result = apply_policy(
                messages,
                provider,
                mode,
                untrusted_paths=untrusted_paths,
                scan_user_messages=key_cfg.scan_user_messages,
                deep_analysis=key_cfg.deep_analysis,
                engine=engine,
            )
        except Exception:  # noqa: BLE001 — fail_open decides the posture (§5)
            if not key_cfg.fail_open:
                return _err(
                    500,
                    "Elcaro scan failed and this key does not fail open.",
                    anthropic=is_anthropic,
                    err_type="api_error",
                )
            bypassed = True

        t_elcaro_ms = (time.perf_counter() - t0) * 1000
        action = "bypassed" if bypassed else _worst_action(result.parts)

        # ── Incidents (autopsy for every flagged part) ────────────────
        incident_url = None
        if result is not None and action != "none":
            incident_url = _record_incidents(result.parts, messages)

        # ── Block mode → endpoint-shaped refusal, no upstream call ────
        if result is not None and result.blocked:
            model = str(body.get("model", "unknown"))
            receipt = _receipt(result.parts, result)
            headers = _elcaro_headers(
                action=action,
                verdict=_verdict_label(result),
                scanned=len(result.parts),
                cost=charge,
                receipt=receipt,
                incident_url=incident_url,
            )
            refusal = (
                anthropic_block_response(model, result.parts)
                if is_anthropic
                else openai_block_response(model, result.parts)
            )
            refusal["elcaro"] = _elcaro_object(
                result, mode, action, _verdict_label(result), receipt, incident_url
            )
            _emit_usage(
                key_id=key_cfg.key_id,
                route=route,
                provider=provider,
                upstream=upstream_name,
                result=result,
                action=action,
                t_elcaro_ms=t_elcaro_ms,
                t_upstream_ms=0.0,
                charge=charge,
                payment=payment_meta,
            )
            metrics.record(key_cfg.key_id, action, _verdict_label(result), len(result.parts))
            metrics.latencies_ms_elcaro.append(t_elcaro_ms)
            return JSONResponse(content=refusal, headers=headers, background=settle_bg)

        # ── Forward (rewritten or bypassed) ───────────────────────────
        if result is not None:
            body["messages"] = result.messages
        payload_out = json.dumps(body).encode()
        url = f"{base}/{ROUTE_PATHS[route_name]}"
        out_headers = upstream_headers(is_anthropic, upstream_key, request.headers)
        client = _get_client()
        streaming = bool(body.get("stream"))

        receipt = _receipt(result.parts, result) if result is not None else None
        verdict = _verdict_label(result) if result is not None else None
        headers = _elcaro_headers(
            action=action,
            verdict=verdict,
            scanned=len(result.parts) if result else 0,
            cost=charge,
            receipt=receipt,
            incident_url=incident_url,
        )

        t_up0 = time.perf_counter()
        try:
            if streaming:
                upstream_req = client.build_request(
                    "POST", url, content=payload_out, headers=out_headers
                )
                upstream_resp = await client.send(upstream_req, stream=True)
            else:
                upstream_resp = await client.post(url, content=payload_out, headers=out_headers)
        except httpx.TimeoutException:
            return _err(504, "Upstream timed out.", anthropic=is_anthropic, err_type="api_error")
        except httpx.HTTPError:
            return _err(502, "Upstream unreachable.", anthropic=is_anthropic, err_type="api_error")
        t_upstream_ms = (time.perf_counter() - t_up0) * 1000

        def _record() -> None:
            _emit_usage(
                key_id=key_cfg.key_id,
                route=route,
                provider=provider,
                upstream=upstream_name,
                result=result,
                action=action,
                t_elcaro_ms=t_elcaro_ms,
                t_upstream_ms=t_upstream_ms,
                charge=charge,
                payment=payment_meta,
            )
            metrics.record(key_cfg.key_id, action, verdict, len(result.parts) if result else 0)
            metrics.latencies_ms_elcaro.append(t_elcaro_ms)
            metrics.latencies_ms_upstream.append(t_upstream_ms)

        if streaming:

            async def _relay():
                try:
                    if upstream_resp.is_stream_consumed:
                        # Buffered transports (test mocks) deliver the body
                        # eagerly — yield it whole.
                        yield upstream_resp.content
                    else:
                        async for chunk in upstream_resp.aiter_raw():
                            yield chunk
                finally:
                    await upstream_resp.aclose()

            _record()
            return StreamingResponse(
                _relay(),
                status_code=upstream_resp.status_code,
                headers=headers,
                media_type=upstream_resp.headers.get("content-type", "text/event-stream").split(
                    ";"
                )[0],
                background=settle_bg,
            )

        # Non-streaming: pass through upstream errors verbatim; on 2xx,
        # splice the elcaro object into the JSON response body (§2.7).
        raw = upstream_resp.content
        content_type = upstream_resp.headers.get("content-type", "")
        if upstream_resp.status_code >= 400 or "application/json" not in content_type:
            _record()
            return Response(
                content=raw,
                status_code=upstream_resp.status_code,
                headers=headers,
                media_type=content_type.split(";")[0] or None,
                background=settle_bg,
            )
        try:
            upstream_json = json.loads(raw)
        except json.JSONDecodeError:
            _record()
            return Response(
                content=raw,
                status_code=upstream_resp.status_code,
                headers=headers,
                media_type="application/json",
                background=settle_bg,
            )
        if isinstance(upstream_json, dict) and result is not None:
            upstream_json["elcaro"] = _elcaro_object(
                result, mode, action, verdict, receipt, incident_url
            )
        _record()
        return JSONResponse(
            content=upstream_json,
            status_code=upstream_resp.status_code,
            headers=headers,
            background=settle_bg,
        )

    # ── Routes ────────────────────────────────────────────────────────────

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Response:
        """OpenAI-compatible chat — policy applied, then upstream."""
        metrics.total_requests += 1
        return await _proxy(request, provider=Provider.OPENAI, route_name="chat_completions")

    @app.post("/v1/messages")
    async def anthropic_messages(request: Request) -> Response:
        """Anthropic-compatible chat — policy applied, then upstream."""
        metrics.total_requests += 1
        return await _proxy(request, provider=Provider.ANTHROPIC, route_name="messages")

    @app.get("/v1/models")
    async def models(request: Request) -> Response:
        """Passthrough model listing — auth + allowlist, no policy surface."""
        metrics.total_requests += 1
        elcaro_key, upstream_key = extract_keys(request.headers)
        if elcaro_key is None:
            return _err(
                401, "Missing Elcaro key.", anthropic=False, err_type="authentication_error"
            )
        key_cfg = key_lookup(elcaro_key)
        if key_cfg is None:
            return _err(
                401, "Unknown Elcaro key.", anthropic=False, err_type="authentication_error"
            )
        if upstream_key is None:
            return _err(
                401,
                "Missing upstream credential.",
                anthropic=False,
                err_type="authentication_error",
            )
        base = resolve_upstream(key_cfg.upstream, upstream_map)
        if base is None:
            return _err(502, "Key upstream is not in the allowlist.", anthropic=False)
        t_up0 = time.perf_counter()
        try:
            resp = await _get_client().get(
                f"{base}/{ROUTE_PATHS['models']}",
                headers=upstream_headers(
                    key_cfg.upstream == _ANTHROPIC_UPSTREAM, upstream_key, request.headers
                ),
            )
        except httpx.HTTPError:
            return _err(502, "Upstream unreachable.", anthropic=False, err_type="api_error")
        _emit_usage(
            key_id=key_cfg.key_id,
            route="/v1/models",
            provider=Provider.OPENAI,
            upstream=key_cfg.upstream,
            result=None,
            action="none",
            t_elcaro_ms=0.0,
            t_upstream_ms=(time.perf_counter() - t_up0) * 1000,
            charge=price,
        )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json").split(";")[0],
        )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "healthy", "service": "elcaro-gateway", "version": "0.1.0"}

    @app.get("/metrics")
    async def metrics_endpoint() -> dict:
        """Per-key and aggregate counters (§2.2) — stats only, no content."""
        return metrics.to_dict()

    @app.get("/incidents/{incident_id}")
    async def incident(incident_id: str) -> JSONResponse:
        """Autopsy report for a flagged part (§2.7), keyed by content-hash
        prefix — the report itself carries extracted indicators, never the
        full payload."""
        entry = incidents.get(incident_id)
        if entry is None:
            return JSONResponse(status_code=404, content={"detail": "Unknown incident."})
        return JSONResponse(content=entry)

    @app.get("/pubkey")
    async def pubkey() -> JSONResponse:
        """The receipt-signing public key — same trust-anchor contract as the
        miner's /pubkey."""
        if resolved_signer is None:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": "This gateway does not sign receipts (ELCARO_SIGNING_KEY not set)."
                },
            )
        return JSONResponse(
            content={
                "algorithm": "ed25519",
                "key_id": resolved_signer.key_id,
                "public_key": resolved_signer.public_key_hex,
                "payload_format": "canonical JSON, sorted keys — see core/signing.py",
            }
        )

    @app.post("/verify")
    async def verify(request: Request) -> JSONResponse:
        """Verify a receipt: ``{"payload": {...}, "signature": "<base64>"}``
        as returned in the elcaro response object's ``receipt`` field."""
        if resolved_signer is None:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "This gateway does not sign receipts (ELCARO_SIGNING_KEY not set)."
                },
            )
        try:
            body = await request.json()
            payload = body["payload"].encode("utf-8")
            signature = base64.b64decode(body["signature"]).hex()
        except Exception:  # noqa: BLE001 — malformed input is a 400
            return JSONResponse(
                status_code=400,
                content={"detail": "Body must be {'payload': {...}, 'signature': '<base64>'}."},
            )
        valid = verify_verdict(payload, signature, resolved_signer.public_key_hex)
        return JSONResponse(
            content={
                "valid": valid,
                "key_id": resolved_signer.key_id,
            }
        )

    return app


# ── Module-level app (uvicorn gateway.app:app) ────────────────────────────────

app = create_app()


__all__ = ["MAX_BODY_BYTES", "app", "create_app"]
