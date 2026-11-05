"""Tool handlers — elcaro_scan / elcaro_quick_scan / elcaro_explain.

Handlers always return a JSON string and never raise: the model gets a
usable result either way.
"""

from __future__ import annotations

import json
from typing import Any

from . import engine, threatlog


def _verdict_json(verdict: Any, full: bool) -> dict[str, Any]:
    level = getattr(verdict.risk_level, "value", str(verdict.risk_level))
    techniques = [t.value if hasattr(t, "value") else str(t) for t in verdict.flagged_techniques]
    out: dict[str, Any] = {
        "risk_score": round(float(verdict.risk_score), 4),
        "risk_level": level,
        "quarantined": bool(verdict.quarantined),
        "flagged_techniques": techniques,
        "summary": getattr(verdict, "summary", ""),
        "human_summary": getattr(verdict, "human_summary", "") or getattr(verdict, "summary", ""),
    }
    if full:
        out["indicators"] = [
            {
                "technique": ind.technique_name,
                "severity": getattr(ind.severity, "value", str(ind.severity)),
                "confidence": round(float(ind.confidence), 3),
                "location": ind.location,
                "explanation": ind.explanation,
                "matched_text": ind.evidence.matched_text[:200],
                "remediation": ind.remediation,
            }
            for ind in getattr(verdict, "indicators", [])[:10]
        ]
        out["normalizations_applied"] = list(getattr(verdict, "normalizations_applied", []) or [])
        out["latency_ms"] = getattr(verdict, "latency_ms", None)
        if getattr(verdict, "quarantined", False):
            out["safe_content"] = getattr(verdict, "safe_content", "")
    return out


def elcaro_scan(args: dict, **kwargs) -> str:
    """Full verdict with evidence trail, for high-stakes decisions."""
    content = (args or {}).get("content", "")
    if not content.strip():
        return json.dumps({"error": "No content provided"})
    try:
        verdict = engine.scan(content, (args or {}).get("content_type", "document"), deep=True)
        threatlog.append(
            tool_name="elcaro_scan",
            verdict=verdict,
            task_id=str(kwargs.get("task_id") or ""),
            session_id=str(kwargs.get("session_id") or ""),
            surface="on_demand",
        )
        return json.dumps(_verdict_json(verdict, full=True))
    except Exception as e:
        return json.dumps({"error": f"scan failed: {e}"})


def elcaro_quick_scan(args: dict, **kwargs) -> str:
    """Triage verdict — score, level, quarantine flag only."""
    content = (args or {}).get("content", "")
    if not content.strip():
        return json.dumps({"error": "No content provided"})
    try:
        verdict = engine.scan(content, (args or {}).get("content_type", "document"))
        return json.dumps(_verdict_json(verdict, full=False))
    except Exception as e:
        return json.dumps({"error": f"scan failed: {e}"})


def elcaro_explain(args: dict, **kwargs) -> str:
    """Human-readable breakdown of a threat-log verdict."""
    index = (args or {}).get("index", 0)
    try:
        index = int(index)
    except (TypeError, ValueError):
        index = 0
    events = threatlog.read_tail(50)
    if not events:
        return json.dumps(
            {
                "message": "No elcaro verdicts logged yet — nothing has been scanned "
                "or quarantined in this installation.",
            }
        )
    if index < 0 or index >= len(events):
        return json.dumps({"error": f"index out of range — {len(events)} event(s) logged"})
    e = events[-1 - index]
    techniques = e.get("flagged_techniques") or []
    explanation = [
        f"Tool '{e.get('tool_name')}' produced content scored {e.get('risk_score')} "
        f"({e.get('risk_level')}) at {e.get('ts')}.",
        f"Quarantined: {e.get('quarantined')}. Techniques: {', '.join(techniques) or 'none'}.",
        f"Surface: {e.get('surface')}. Signature: "
        f"{'ed25519/' + (e.get('key_id') or '?') if e.get('signature') else 'unsigned'}.",
        "Only the content's SHA-256 is logged — the verdict is verifiable "
        "without the original text.",
    ]

    # Forensic layer: propagation edges and time-shifted verdicts turn the
    # single entry into a trail.
    out: dict[str, Any] = {"event": e}
    if e.get("type") == "edge":
        for edge in e.get("edges") or []:
            origin = (edge.get("origin_sha256") or "?")[:12]
            explanation.append(
                f"Propagation: canary {edge.get('token')} minted by content "
                f"{origin}… (scored {edge.get('origin_score')}) resurfaced "
                "inside this scan — the injection traveled between tool calls."
            )

    sha = e.get("content_sha256")
    if sha:
        prior = [
            {
                "ts": p.get("ts"),
                "risk_score": p.get("risk_score"),
                "risk_level": p.get("risk_level"),
                "quarantined": p.get("quarantined"),
            }
            for p in events[: len(events) - 1 - index]
            if p.get("content_sha256") == sha and p.get("type") != "edge"
        ]
        if prior:
            out["history"] = prior
            first, last = prior[0], prior[-1]
            explanation.append(
                f"This exact content (SHA-256 {sha[:12]}…) was scanned "
                f"{len(prior)} time(s) before: "
                f"{first['risk_score']} ({first['risk_level']}) at {first['ts']} … "
                f"{last['risk_score']} ({last['risk_level']}) at {last['ts']}. "
                "A moved score on identical bytes means enforcement changed; "
                "a moved hash on the same source means the page changed."
            )
        # Same source, different bytes — the strongest tamper signal.
        siblings = [
            p
            for p in events[: len(events) - 1 - index]
            if p.get("tool_name") == e.get("tool_name")
            and p.get("content_sha256")
            and p.get("content_sha256") != sha
            and p.get("type") != "edge"
        ]
        if siblings:
            drift = siblings[-1]
            explanation.append(
                f"Earlier content from '{e.get('tool_name')}' hashed "
                f"{(drift.get('content_sha256') or '')[:12]}… and scored "
                f"{drift.get('risk_score')} — the source changed between scans."
            )

    out["explanation"] = "\n".join(explanation)
    return json.dumps(out)
