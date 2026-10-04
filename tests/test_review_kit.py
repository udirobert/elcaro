from __future__ import annotations

import csv
import json
from pathlib import Path

from swarm import review_kit


def test_prepare_kits_contains_only_assigned_files(tmp_path: Path, monkeypatch):
    swarm_packet = tmp_path / "swarm" / "review-v1"
    molt_packet = tmp_path / "moltverse" / "review-v1"
    for packet in (swarm_packet, molt_packet):
        packet.mkdir(parents=True)
        for reviewer in ("a", "b"):
            with (packet / f"reviewer-{reviewer}.csv").open("w", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "sample_id",
                        "source",
                        "channel",
                        "actor",
                        "time",
                        "text",
                        "label",
                        "notes",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "sample_id": f"{packet.name}-{reviewer}-1",
                        "source": "test",
                        "channel": "chan",
                        "actor": "actor",
                        "time": "2026-01-01T00:00:00Z",
                        "text": "hello",
                        "label": "",
                        "notes": "",
                    }
                )
        (packet / "review-guidance.txt").write_text("rubric")
        (packet / "answer-key.json").write_text('{"secret": true}')

    monkeypatch.setattr(review_kit, "PACKETS", (swarm_packet, molt_packet))
    out = tmp_path / "kits"
    manifests = review_kit.prepare_kits(out, port=3030)

    assert len(manifests) == 2
    for reviewer in ("a", "b"):
        kit = out / f"reviewer-{reviewer}"
        assert (kit / "start-review").stat().st_mode & 0o111
        names = {p.name for p in (kit / "packet").iterdir()}
        assert names == {
            f"moltverse-reviewer-{reviewer}.csv",
            "moltverse-review-guidance.txt",
            f"swarm-reviewer-{reviewer}.csv",
            "swarm-review-guidance.txt",
        }
        assert not list(kit.rglob("answer-key.json"))
        manifest = json.loads((kit / "kit-manifest.json").read_text())
        assert manifest["reviewer"] == reviewer
        assert all("answer-key" not in item["file"] for item in manifest["files"])


def test_validate_csv_counts_labels(tmp_path: Path):
    path = tmp_path / "done.csv"
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "sample_id",
                "source",
                "channel",
                "actor",
                "time",
                "text",
                "label",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "sample_id": "x",
                "source": "s",
                "channel": "c",
                "actor": "a",
                "time": "t",
                "text": "u",
                "label": "uncertain",
                "notes": "ambiguous",
            }
        )
    assert review_kit.validate_csv(path) == {"rows": 1, "labeled": 1, "uncertain": 1}
