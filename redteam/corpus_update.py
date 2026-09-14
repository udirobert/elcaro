"""Feed confirmed bypasses back into eval/corpus.json.

Each unique trophy becomes a new positive test case (id RT001, RT002, …)
so the WASM eval — and every future redteam run — measures the engine
against attacks we discovered, not only the ones we wrote down.

    python -m redteam.corpus_update <journal.jsonl> [--corpus eval/corpus.json]

expected_techniques is inherited from the seed case — the payload's true
class — not from the ops used to evade it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from redteam.corpus import CORPUS_PATH
from redteam.journal import Journal, unique_trophies


def append_trophies(
    journal_path: Path | str,
    corpus_path: Path | str = CORPUS_PATH,
    prefix: str = "RT",
) -> int:
    """Append new positive cases for each unique trophy. Returns count added."""
    corpus_path = Path(corpus_path)
    corpus = json.loads(corpus_path.read_text())
    seeds_by_id = {c["id"]: c for c in corpus}
    existing_contents = {c["content"] for c in corpus}
    next_n = 1 + sum(1 for c in corpus if c["id"].startswith(prefix))

    added = 0
    for t in unique_trophies(Journal.read(journal_path)):
        if t["content"] in existing_contents:
            continue
        seed = seeds_by_id.get(t.get("seed_id"), {})
        corpus.append(
            {
                "id": f"{prefix}{next_n:03d}",
                "content": t["content"],
                "content_type": t["content_type"],
                "is_injection": True,
                "expected_techniques": seed.get("expected_techniques", []),
                "description": (
                    f"redteam-discovered bypass of {t.get('seed_id')} "
                    f"via {'/'.join(t.get('ops', []))} (score {t.get('risk_score')})"
                ),
            }
        )
        existing_contents.add(t["content"])
        next_n += 1
        added += 1

    if added:
        corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=False) + "\n")
    return added


def main() -> None:
    p = argparse.ArgumentParser(prog="redteam.corpus_update")
    p.add_argument("journal", help="path to a run journal (.jsonl)")
    p.add_argument("--corpus", default=str(CORPUS_PATH))
    args = p.parse_args()
    n = append_trophies(args.journal, args.corpus)
    print(f"[corpus] appended {n} new test case(s) to {args.corpus}")


if __name__ == "__main__":
    main()
