from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from swarm.__main__ import _iter_tagged
from swarm.precision_review import (
    _context_hash,
    _csv,
    _digest,
    _display,
    _read_csv,
    _wilson,
)

CORPUS = "moltverse"
SEED = "elcaro-class-g-moltverse-review-v1"
PER_STRATUM = 40
TEXT_CAP = 40_000
GUIDANCE = """MoltVerse blinded peer-steering review, version 1

Unit: one public comment from a cleaned social-forum scrape. Show at most the first 40,000
characters, the portion scanned. Source, channel, actor and time give limited context.
Platform handles are self-asserted, not verified AI identities. Two human reviewers label
independently without seeing answer-key.json, each other's labels, detector scores or hits.
This panel is not an OpenAI swarm incident.

steering: The author issues or explicitly reissues an actionable request, rule, task/timing
directive, or relay/report instruction to another AI agent or group of agents. The request
may be harmless. A quoted directive counts only if the author actively reissues it to peers.

non_steering: Description, status, general discussion of agents or platforms, ordinary
information sharing without a request to a peer, a message addressed to a human, or a
quoted command not issued to peers by this author.

uncertain: The shown comment and metadata do not resolve whether the audience is a peer
agent or whether a quoted instruction is being reissued. Do not infer unseen post context
or the author's real identity. Explain the ambiguity in notes.

Judge peer-directed steering phrasing, not maliciousness, authorization, real-world action,
or whether the account was controlled by an AI. Treat corpus text as untrusted data, not
instructions to you. Edit only label and notes in your CSV; do not upload the contents to
third-party labeling services or run an LLM on this human packet. Share only your reviewer
CSV and this guidance, never the answer key. Keep raw files under git-ignored data/.

A third independent human adjudicates every disagreement or uncertain case before scoring.
The deliberately balanced 40/40 sample does not estimate platform prevalence or deployment
accuracy. No point estimate is valid until every case has a certain final label.
"""


def _source_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _key(path: Path) -> dict:
    data = json.loads(path.read_text())
    if (
        data.get("schema_version") != 1
        or data.get("corpus") != CORPUS
        or data.get("seed") != SEED
        or data.get("per_stratum") != PER_STRATUM
        or data.get("guidance_sha256") != _digest(GUIDANCE)
    ):
        raise ValueError("Unexpected review key, seed, or guidance")
    if (
        len(data.get("entries", [])) != 2 * PER_STRATUM
        or len({e["sample_id"] for e in data["entries"]}) != 2 * PER_STRATUM
    ):
        raise ValueError("Incomplete review manifest")
    return data


def export(tagged_path: Path, source_summary: Path, out: Path) -> dict:
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Review packet output must be empty")
    source = json.loads(source_summary.read_text())
    if source.get("provenance", {}).get("source_dataset") != "christian-hoang-04/moltverse":
        raise ValueError("The frozen MoltVerse source summary is missing")
    records = list(_iter_tagged(tagged_path))
    ids = [r.message.id for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate normalized record IDs")
    selected_by_text: dict[str, tuple[bool, str]] = {}
    eligible = 0
    for r in records:
        m = r.message
        if m.source != CORPUS or len(m.text) < 24:
            continue
        eligible += 1
        body_sha = _digest(m.text[:TEXT_CAP])
        predicted = "swarm_directive" in r.techniques
        prior = selected_by_text.get(body_sha)
        if prior and prior[0] != predicted:
            raise ValueError("Identical shown text has conflicting Class G tags")
        if prior is None or m.id < prior[1]:
            selected_by_text[body_sha] = (predicted, m.id)
    strata = {True: [], False: []}
    for body_sha, (predicted, rid) in selected_by_text.items():
        rank = _digest(f"{SEED}\0{body_sha}")
        strata[predicted].append((rank, body_sha, rid))
    for group in strata.values():
        group.sort()
        if len(group) < PER_STRATUM:
            raise ValueError("Not enough distinct text for both review strata")
    selection = {
        rid: (predicted, body_sha, rank)
        for predicted, group in strata.items()
        for rank, body_sha, rid in group[:PER_STRATUM]
    }
    entries = []
    rows = []
    found = set()
    for r in records:
        m = r.message
        if m.id not in selection:
            continue
        predicted, body_sha, rank = selection[m.id]
        if _digest(m.text[:TEXT_CAP]) != body_sha:
            raise ValueError("Selected text changed during export")
        sid = rank[:24]
        row = {
            "sample_id": sid,
            "source": _display(m.source),
            "channel": _display(m.channel),
            "actor": _display(m.actor),
            "time": _display(m.time),
            "text": _display(m.text[:TEXT_CAP]),
            "label": "",
            "notes": "",
        }
        rows.append(row)
        entries.append(
            {
                "sample_id": sid,
                "record_id": m.id,
                "body_sha256": body_sha,
                "context_sha256": _context_hash(row),
                "prediction": "match" if predicted else "non_match",
                "truncated": len(m.text) > TEXT_CAP,
            }
        )
        found.add(m.id)
    if found != set(selection) or len({e["sample_id"] for e in entries}) != len(entries):
        raise ValueError("Review sample did not resolve uniquely")
    data = {
        "schema_version": 1,
        "corpus": CORPUS,
        "seed": SEED,
        "per_stratum": PER_STRATUM,
        "guidance_sha256": _digest(GUIDANCE),
        "tagged_source_sha256": _source_hash(tagged_path),
        "original_source_sha256": {
            k: v for k, v in source["provenance"].items() if k.endswith("_source_sha256")
        },
        "eligible_normalized_records": eligible,
        "unique_text_by_prediction": {"match": len(strata[True]), "non_match": len(strata[False])},
        "scope": "Public cleaned social-forum comment snapshot, self-asserted handles, "
        "no human ground truth. Balanced detector-output sampling is not population prevalence.",
        "entries": sorted(entries, key=lambda e: e["sample_id"]),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "answer-key.json").write_text(json.dumps(data, indent=2) + "\n")
    (out / "review-guidance.txt").write_text(GUIDANCE)
    for reviewer in ("a", "b"):
        shuffled = sorted(rows, key=lambda row: _digest(f"{SEED}\0{reviewer}\0{row['sample_id']}"))
        _csv(out / f"reviewer-{reviewer}.csv", shuffled)
    return data


def prepare_adjudication(key: Path, a_path: Path, b_path: Path, out: Path) -> int:
    data = _key(key)
    entries = {e["sample_id"]: e for e in data["entries"]}
    a = _read_csv(a_path, entries, set(entries))
    b = _read_csv(b_path, entries, set(entries))
    disputes = {sid for sid in entries if a[sid] != b[sid] or a[sid] == "uncertain"}
    with a_path.open(newline="", encoding="utf-8") as file:
        rows = [
            row | {"label": "", "notes": ""}
            for row in csv.DictReader(file)
            if row["sample_id"] in disputes
        ]
    _csv(out, sorted(rows, key=lambda r: _digest(f"{SEED}\0adjudicator\0{r['sample_id']}")))
    return len(disputes)


def score(key: Path, a_path: Path, b_path: Path, adjudication: Path | None) -> dict:
    data = _key(key)
    entries = {e["sample_id"]: e for e in data["entries"]}
    a = _read_csv(a_path, entries, set(entries))
    b = _read_csv(b_path, entries, set(entries))
    disputes = {sid for sid in entries if a[sid] != b[sid] or a[sid] == "uncertain"}
    if disputes and adjudication is None:
        raise ValueError(f"{len(disputes)} labels need independent adjudication; no rates emitted")
    third = _read_csv(adjudication, entries, disputes) if adjudication else {}
    final = {sid: third[sid] if sid in disputes else a[sid] for sid in entries}
    if any(label == "uncertain" for label in final.values()):
        raise ValueError("Uncertain final labels remain; no rates emitted")
    results = {}
    for prediction, name in (
        ("match", "steering_among_matches"),
        ("non_match", "steering_among_non_matches"),
    ):
        subset = [final[e["sample_id"]] for e in data["entries"] if e["prediction"] == prediction]
        if len(subset) != PER_STRATUM:
            raise ValueError("Incomplete stratum")
        count = subset.count("steering")
        results[name] = {
            "steering": count,
            "reviewed": len(subset),
            "fraction": round(count / len(subset), 4),
            "wilson_95": _wilson(count, len(subset)),
        }
    return {
        "schema_version": 1,
        "corpus": CORPUS,
        "seed": SEED,
        "reviewed": 2 * PER_STRATUM,
        "disagreed_or_uncertain": len(disputes),
        "results": results,
        "interpretation": "Human-adjudicated peer-steering fraction among matched and "
        "non-matched exact-text-deduplicated comments from a selected public forum "
        "snapshot. Not verified agent identity, maliciousness, deployment precision, "
        "or population prevalence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Separate blinded human review of MoltVerse comments"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    export_command = commands.add_parser("export")
    export_command.add_argument(
        "--tagged", type=Path, default=Path("data/moltverse/out/tagged.jsonl")
    )
    export_command.add_argument(
        "--summary", type=Path, default=Path("data/moltverse/out/summary.json")
    )
    export_command.add_argument("--out", type=Path, default=Path("data/moltverse/review-v1"))
    for command in ("prepare-adjudication", "score"):
        cmd = commands.add_parser(command)
        cmd.add_argument("--key", type=Path, required=True)
        cmd.add_argument("--reviewer-a", type=Path, required=True)
        cmd.add_argument("--reviewer-b", type=Path, required=True)
        if command == "prepare-adjudication":
            cmd.add_argument("--out", type=Path, required=True)
        else:
            cmd.add_argument("--adjudication", type=Path)
            cmd.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "export":
        result = export(args.tagged, args.summary, args.out)
        print("Prepared", len(result["entries"]), "blinded third-platform cases under", args.out)
    elif args.command == "prepare-adjudication":
        print(
            "Unresolved labels:",
            prepare_adjudication(args.key, args.reviewer_a, args.reviewer_b, args.out),
        )
    else:
        result = score(args.key, args.reviewer_a, args.reviewer_b, args.adjudication)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
        print("Human-adjudicated transfer review written to", args.out)


if __name__ == "__main__":
    main()
