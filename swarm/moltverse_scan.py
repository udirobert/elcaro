from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from swarm.scan import scan_messages, summarize
from swarm.schema import SwarmMessage

DATASET = "christian-hoang-04/moltverse"
SOURCE = "moltverse"


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _rows(path: Path):
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            if line.strip():
                yield line_number, json.loads(line)


def _time(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Comment timestamp missing or not text")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Comment timestamp not ISO-parseable") from exc
    if stamp.tzinfo is None:
        raise ValueError("Comment timestamp has no timezone")
    return stamp.astimezone(UTC).isoformat()


def load_comment_messages(data_dir: Path) -> tuple[list[SwarmMessage], dict]:
    posts_path = data_dir / "moltverse_posts.jsonl"
    comments_path = data_dir / "moltverse_comments.jsonl"
    posts: set[str] = set()
    for _, row in _rows(posts_path):
        url = row.get("url")
        if not isinstance(url, str) or not url or url in posts:
            raise ValueError("Missing or duplicated parent post URL")
        posts.add(url)
    messages = []
    seen = set()
    source_rows = 0
    for line_number, row in _rows(comments_path):
        source_rows += 1
        url, author, text = row.get("post_url"), row.get("author"), row.get("text")
        if not isinstance(url, str) or url not in posts:
            raise ValueError("Comment post URL has no parent")
        if not isinstance(author, str) or not author or not isinstance(text, str):
            raise ValueError("Missing commenter handle or comment text")
        raw_timestamp = row.get("timestamp")
        stamp = _time(raw_timestamp)
        body = json.dumps(
            [url, author, raw_timestamp, text], ensure_ascii=False, separators=(",", ":")
        )
        digest = hashlib.sha256(body.encode()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        messages.append(
            SwarmMessage(
                id=f"moltverse:{digest[:24]}",
                source=SOURCE,
                channel=url,
                actor=author,
                ip16=None,
                time=stamp,
                text=text,
                meta={
                    "original_timestamp": raw_timestamp,
                    "source_line": line_number,
                    "post_author": row.get("post_author"),
                    "submolt": row.get("submolt"),
                    "provenance": "cleaned_public_scrape_self_asserted_handle",
                },
            )
        )
    messages.sort(key=lambda m: (m.time, m.id))
    return messages, {
        "source_dataset": DATASET,
        "scope": "Cleaned Moltbook public scrape, comments only; actor handles are unverified and "
        "not proof of AI identity; no human steering or maliciousness labels.",
        "posts_source_sha256": _digest(posts_path),
        "comments_source_sha256": _digest(comments_path),
        "source_post_rows": len(posts),
        "source_comment_rows": source_rows,
        "duplicate_comment_context_rows_removed": source_rows - len(messages),
        "normalized_comment_records": len(messages),
    }


def scan_dataset(data_dir: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Output directory must be empty to avoid overwriting frozen results")
    messages, provenance = load_comment_messages(data_dir)
    tagged = scan_messages(messages, workers=1)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "tagged.jsonl").open("w", encoding="utf-8") as file:
        for record in tagged:
            file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    report = {
        "schema_version": 1,
        "provenance": provenance,
        "scan": summarize(tagged),
        "interpretation": "A rule-transfer observation on a separate public forum snapshot, "
        "not a labeled peer-steering benchmark. Scrape selection and unverified authorship "
        "prevent independent-agent or intent claims. No LLMs, provider API calls, graph "
        "inference, or public payload export.",
    }
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local-only Class G transfer scan on MoltVerse comments"
    )
    parser.add_argument("--data", type=Path, default=Path("data/moltverse"))
    parser.add_argument("--out", type=Path, default=Path("data/moltverse/out"))
    args = parser.parse_args()
    report = scan_dataset(args.data, args.out)
    print("Local transfer scan saved to", args.out)
    print("Normalized comment records:", report["provenance"]["normalized_comment_records"])
    print("Class G-tagged records (unlabeled):", report["scan"]["directive_flagged"])


if __name__ == "__main__":
    main()
