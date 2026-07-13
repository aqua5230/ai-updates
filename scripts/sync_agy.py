#!/usr/bin/env python3
"""Import the local `agy changelog` output into immutable raw records."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "agy"
SOURCE = "agy changelog"
VERSION_LINE = re.compile(r"^([^\s:]+):\s*$")


def parse_agy_changelog(text: str) -> list[tuple[str, list[str]]]:
    versions: list[tuple[str, list[str]]] = []
    version: str | None = None
    entries: list[str] = []
    for line in text.splitlines():
        match = VERSION_LINE.match(line)
        if match:
            if version and entries:
                versions.append((version, entries))
            version = match.group(1)
            entries = []
        elif version and line.startswith("· "):
            entries.append(line[2:])
    if version and entries:
        versions.append((version, entries))
    return versions


def sync(text: str) -> int:
    parsed = parse_agy_changelog(text)
    if not parsed:
        raise ValueError("agy changelog contained no parseable versions")
    today = date.today().isoformat()
    created = 0
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for version, entries in parsed:
        path = RAW_DIR / f"{version}.json"
        if path.exists():
            continue
        record = {
            "version": version,
            "period": today,
            "source_url": SOURCE,
            "fetched_at": today,
            "entries": entries,
        }
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"NEW agy {version}")
        created += 1
    return created


def main() -> int:
    try:
        result = subprocess.run(
            ["agy", "changelog"], check=True, capture_output=True, text=True
        )
        sync(result.stdout)
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError) as exc:
        print(f"sync failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
