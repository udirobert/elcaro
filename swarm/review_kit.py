"""Prepare private, local-first reviewer launch kits.

Each kit contains only the assigned reviewer CSVs and rubrics. The review page
imports the CSV in the browser, stores labels in that browser's private review
store, and exports the scorer-compatible CSV.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "app" / "web"
DEFAULT_OUT = ROOT / "data" / "review-kits"

PACKETS = (
    ROOT / "data" / "swarm" / "review-v1",
    ROOT / "data" / "moltverse" / "review-v1",
)

KIT_README = """Elcaro blinded review kit

This folder is private review material. It contains only your assigned CSV
files and the two frozen rubric files. It does not contain answer keys,
detector scores, or another reviewer's work.

Start the review bench:

    ./start-review

The script starts a local-only web server and opens a private Chrome profile
at /review. Import only your CSV files from this folder. Your labels are saved
inside this browser profile, so closing the window does not discard work.
When finished, use "Export completed CSV" and send the exported files back by
the agreed private channel.

Label only: steering, non_steering, or uncertain.
Edit only: label and notes.
"""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


PacketFile = tuple[Path, str]


def _packet_files(reviewer: str) -> list[PacketFile]:
    files: list[PacketFile] = []
    for packet_dir in PACKETS:
        corpus = packet_dir.parent.name
        files.extend(
            [
                (packet_dir / f"reviewer-{reviewer}.csv", f"{corpus}-reviewer-{reviewer}.csv"),
                (packet_dir / "review-guidance.txt", f"{corpus}-review-guidance.txt"),
            ]
        )
    missing = [path for path, _ in files if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing review packet files: " + ", ".join(map(str, missing)))
    return files


def _manifest(reviewer: str, kit_dir: Path, files: list[PacketFile]) -> dict:
    entries = []
    for path, archive_name in files:
        data = path.read_bytes()
        entries.append(
            {
                "file": archive_name,
                "source": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    return {
        "schema_version": 1,
        "kind": "elcaro-local-reviewer-kit",
        "reviewer": reviewer,
        "created_utc": datetime.now(UTC).isoformat(),
        "privacy": {
            "server_binding": "127.0.0.1 only",
            "packet_storage": "reviewer browser private profile",
            "uploads": "none",
        },
        "files": entries,
    }


def _start_script(kit_dir: Path, port: int) -> Path:
    script = kit_dir / "start-review"
    script.write_text(
        f"""#!/bin/sh
set -eu
cd "$(dirname "$0")"
export ELCARO_REVIEW_PROFILE="$(pwd)/.chrome-profile"
mkdir -p "$ELCARO_REVIEW_PROFILE"
(
  for _ in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:{port}/review" >/dev/null 2>&1; then
      /usr/bin/open -na "Google Chrome" --args \\
        "--user-data-dir=$ELCARO_REVIEW_PROFILE" \\
        "http://127.0.0.1:{port}/review"
      break
    fi
    sleep 1
  done
) &
cd "{WEB}"
if [ ! -d node_modules/next ]; then
  npm ci
fi
exec npm run dev -- --hostname 127.0.0.1 --port {port}
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _reviewer_readme(reviewer: str, files: list[PacketFile]) -> str:
    packet_names = "\n".join(f"- {archive_name}" for _, archive_name in files)
    return f"{KIT_README}\nAssigned reviewer: {reviewer}\nFiles in this kit:\n{packet_names}\n"


def prepare_kits(out: Path = DEFAULT_OUT, port: int = 3000) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    manifests = []
    for reviewer in ("a", "b"):
        kit = out / f"reviewer-{reviewer}"
        if kit.exists():
            shutil.rmtree(kit)
        packet_dir = kit / "packet"
        packet_dir.mkdir(parents=True)
        files = _packet_files(reviewer)
        for source, archive_name in files:
            shutil.copy2(source, packet_dir / archive_name)
        (kit / "README.txt").write_text(_reviewer_readme(reviewer, files))
        _start_script(kit, port)
        manifest = _manifest(reviewer, kit, files)
        (kit / "kit-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        manifests.append(manifest)
        os.chmod(kit / "kit-manifest.json", stat.S_IRUSR | stat.S_IWUSR)
    return manifests


def validate_csv(path: Path) -> dict[str, int]:
    rows = _read_csv(path)
    labeled = sum(1 for row in rows if row["label"].strip())
    uncertain = sum(1 for row in rows if row["label"].strip() == "uncertain")
    return {"rows": len(rows), "labeled": labeled, "uncertain": uncertain}


def launch(kit_dir: Path, port: int = 3000) -> subprocess.Popen:
    if sys.platform != "darwin":
        raise RuntimeError("Kit browser launch currently expects macOS 'open'")
    profile = kit_dir / ".chrome-profile"
    profile.mkdir(exist_ok=True)
    return subprocess.Popen(  # noqa: S607
        [
            "/usr/bin/open",
            "-na",
            "Google Chrome",
            "--args",
            f"--user-data-dir={profile}",
            f"http://127.0.0.1:{port}/review",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare local-only Elcaro reviewer kits")
    parser.add_argument("reviewer", choices=("a", "b", "all"), nargs="?", default="all")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()
    if args.reviewer == "all":
        manifests = prepare_kits(args.out, args.port)
        print("Prepared", len(manifests), "private reviewer kits under", args.out)
        for manifest in manifests:
            files = ", ".join(item["file"] for item in manifest["files"])
            print(" reviewer", manifest["reviewer"], "files:", files)
    else:
        kit_dir = args.out / "single" / f"reviewer-{args.reviewer}"
        if kit_dir.exists():
            shutil.rmtree(kit_dir)
        packet_dir = kit_dir / "packet"
        packet_dir.mkdir(parents=True)
        files = _packet_files(args.reviewer)
        for source, archive_name in files:
            shutil.copy2(source, packet_dir / archive_name)
        (kit_dir / "README.txt").write_text(_reviewer_readme(args.reviewer, files))
        _start_script(kit_dir, args.port)
        manifest = _manifest(args.reviewer, kit_dir, files)
        (kit_dir / "kit-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print("Prepared reviewer", args.reviewer, "kit under", kit_dir)
    if args.launch:
        if args.reviewer == "all":
            raise ValueError("Choose reviewer a or b when launching a kit")
        kit = args.out / "single" / f"reviewer-{args.reviewer}"
        launch(kit, args.port)
        print("Opened", f"http://127.0.0.1:{args.port}/review", "in a private Chrome profile")


if __name__ == "__main__":
    main()
