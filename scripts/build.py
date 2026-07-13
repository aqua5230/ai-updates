#!/usr/bin/env python3
"""Build compatibility and history feeds from raw and curated records."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TOOLS = (
    ("claude_code", "Claude Code"),
    ("codex", "Codex"),
    ("agy", "Antigravity"),
)


def _load_versions(layer: str, tool_id: str) -> dict[str, dict[str, Any]]:
    directory = DATA / layer / tool_id
    versions: dict[str, dict[str, Any]] = {}
    if not directory.exists():
        return versions
    for path in directory.glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("version") != path.stem:
            raise ValueError(f"invalid version record: {path}")
        versions[path.stem] = value
    return versions


def _version_key(version: str) -> tuple[tuple[int, int | str], ...]:
    parts = re.findall(r"\d+|[A-Za-z]+", version)
    return tuple((0, int(part)) if part.isdigit() else (1, part.lower()) for part in parts)


def is_placeholder(raw: dict[str, Any], version: str) -> bool:
    """Return whether a raw release contains no content beyond its version label."""
    entries = raw.get("entries")
    if not isinstance(entries, list) or any(not isinstance(entry, str) for entry in entries):
        return False

    nonempty_entries = {entry.strip() for entry in entries if entry.strip()}
    if not nonempty_entries:
        return True

    normalized_version = re.sub(r"^(?:rust[-_])?v(?=\d)", "", version.casefold())
    for entry in nonempty_entries:
        match = re.fullmatch(r"release\s+(.+)", entry, flags=re.IGNORECASE)
        if match is None:
            return False
        entry_version = re.sub(r"\s+", "", match.group(1).casefold())
        entry_version = re.sub(r"^(?:rust[-_])?v(?=\d)", "", entry_version)
        if entry_version != normalized_version:
            return False
    return True


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build() -> None:
    generated_at = date.today().isoformat()
    app_tools: list[dict[str, Any]] = []
    history_tools: list[dict[str, Any]] = []
    daily_tools: list[dict[str, Any]] = []
    for tool_id, name in TOOLS:
        raw = _load_versions("raw", tool_id)
        curated = _load_versions("curated", tool_id)
        curated_latest = sorted(curated, key=_version_key, reverse=True)[:3]
        if curated_latest:
            app_tools.append(
                {"id": tool_id, "name": name, "versions": [curated[v] for v in curated_latest]}
            )

        all_versions = sorted(set(raw) | set(curated), key=_version_key, reverse=True)
        visible_versions = [
            version
            for version in all_versions
            if version in curated or not is_placeholder(raw[version], version)
        ]
        history_tools.append(
            {
                "id": tool_id,
                "name": name,
                "versions": [
                    {"version": version, "raw": raw.get(version), "curated": curated.get(version)}
                    for version in visible_versions
                ],
            }
        )

        daily_versions: list[dict[str, Any]] = []
        for version in visible_versions[:3]:
            if version in curated:
                daily_versions.append({**curated[version], "curated": True})
            else:
                record = raw[version]
                daily_versions.append(
                    {
                        "version": version,
                        "period": record["period"],
                        "items": [{"original": entry} for entry in record["entries"]],
                        "curated": False,
                    }
                )
        daily_tools.append({"id": tool_id, "name": name, "versions": daily_versions})

    _write(ROOT / "ai_updates.json", {"generated_at": generated_at, "tools": app_tools})
    _write(ROOT / "docs" / "data.json", {"generated_at": generated_at, "tools": history_tools})
    _write(ROOT / "daily.json", {"generated_at": generated_at, "tools": daily_tools})


if __name__ == "__main__":
    build()
