from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts import build as build_script
from scripts.build import build, is_placeholder

ROOT = Path(__file__).resolve().parents[1]


def normalize_payload(payload: Any) -> list[dict[str, Any]] | None:
    """Golden validator copied from usage/analyzer/ai_updates_loader.py::_normalize_payload."""
    if not isinstance(payload, dict):
        return None
    raw_tools = payload.get("tools")
    if not isinstance(raw_tools, list):
        return None
    tools: list[dict[str, Any]] = []
    for raw_tool in raw_tools:
        if not isinstance(raw_tool, dict):
            continue
        if not all(isinstance(raw_tool.get(key), str) for key in ("id", "name")):
            continue
        raw_versions = raw_tool.get("versions")
        if not isinstance(raw_versions, list):
            continue
        versions: list[dict[str, Any]] = []
        for raw_version in raw_versions:
            if not isinstance(raw_version, dict):
                continue
            if not all(isinstance(raw_version.get(key), str) for key in ("version", "period")):
                continue
            raw_items = raw_version.get("items")
            if not isinstance(raw_items, list):
                continue
            items: list[dict[str, Any]] = []
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    continue
                title = raw_item.get("title")
                body = raw_item.get("body")
                original = raw_item.get("original")
                if not isinstance(title, dict) or not isinstance(body, dict):
                    continue
                if not all(
                    isinstance(key, str) and isinstance(value, str)
                    for key, value in title.items()
                ):
                    continue
                if not all(
                    isinstance(key, str) and isinstance(value, str)
                    for key, value in body.items()
                ):
                    continue
                if not isinstance(original, str):
                    continue
                items.append({"title": title, "body": body, "original": original})
            if not items:
                continue
            versions.append(
                {
                    "version": raw_version["version"],
                    "period": raw_version["period"],
                    "items": items,
                }
            )
        if not versions:
            continue
        tools.append({"id": raw_tool["id"], "name": raw_tool["name"], "versions": versions})
    return tools or None


def test_build_outputs_pass_golden_validator() -> None:
    build()
    payload = json.loads((ROOT / "ai_updates.json").read_text(encoding="utf-8"))
    normalized = normalize_payload(payload)

    assert normalized is not None
    assert len(normalized) == 3
    assert all(len(tool["versions"]) <= 3 for tool in normalized)
    assert (ROOT / "docs" / "data.json").is_file()
    assert (ROOT / "daily.json").is_file()


def test_is_placeholder_accepts_empty_and_version_only_entries() -> None:
    assert is_placeholder({"entries": ["  ", "\n"]}, "0.145.0-alpha.4")
    assert is_placeholder(
        {"entries": ["Release rust-v0.145.0-alpha.4", " release 0.145.0-ALPHA.4 "]},
        "0.145.0-alpha.4",
    )
    assert is_placeholder(
        {
            "entries": [
                "Published a version-only release with no merged pull request changes since "
                "rust-v0.144.3."
            ]
        },
        "0.144.3",
    )
    assert is_placeholder(
        {
            "entries": [
                "Published a version-only release with no merged pull request changes since "
                "`rust-v0.144.2`."
            ]
        },
        "0.144.3",
    )
    assert not is_placeholder(
        {"entries": ["Release 0.144.1", "Fixed standalone installs."]}, "0.144.1"
    )


def test_build_filters_placeholder_versions(tmp_path: Path, monkeypatch: Any) -> None:
    data = tmp_path / "data"
    raw_dir = data / "raw" / "codex"
    raw_dir.mkdir(parents=True)
    records = {
        "0.3.0": ["Release 0.3.0"],
        "0.2.0": ["Actual release notes"],
        "0.1.0": ["Release 0.1.0"],
    }
    for version, entries in records.items():
        (raw_dir / f"{version}.json").write_text(
            json.dumps({"version": version, "period": "2026-07-13", "entries": entries}),
            encoding="utf-8",
        )
    monkeypatch.setattr(build_script, "ROOT", tmp_path)
    monkeypatch.setattr(build_script, "DATA", data)
    monkeypatch.setattr(build_script, "TOOLS", (("codex", "Codex"),))

    build_script.build()

    history = json.loads((tmp_path / "docs" / "data.json").read_text(encoding="utf-8"))
    daily = json.loads((tmp_path / "daily.json").read_text(encoding="utf-8"))
    assert [item["version"] for item in history["tools"][0]["versions"]] == ["0.2.0"]
    assert [item["version"] for item in daily["tools"][0]["versions"]] == ["0.2.0"]


def test_build_keeps_curated_placeholder_versions(tmp_path: Path, monkeypatch: Any) -> None:
    data = tmp_path / "data"
    raw_dir = data / "raw" / "codex"
    curated_dir = data / "curated" / "codex"
    raw_dir.mkdir(parents=True)
    curated_dir.mkdir(parents=True)
    raw = {"version": "0.3.0", "period": "2026-07-13", "entries": ["Release 0.3.0"]}
    curated = {"version": "0.3.0", "period": "2026-07-13", "items": []}
    (raw_dir / "0.3.0.json").write_text(json.dumps(raw), encoding="utf-8")
    (curated_dir / "0.3.0.json").write_text(json.dumps(curated), encoding="utf-8")
    monkeypatch.setattr(build_script, "ROOT", tmp_path)
    monkeypatch.setattr(build_script, "DATA", data)
    monkeypatch.setattr(build_script, "TOOLS", (("codex", "Codex"),))

    build_script.build()

    history = json.loads((tmp_path / "docs" / "data.json").read_text(encoding="utf-8"))
    daily = json.loads((tmp_path / "daily.json").read_text(encoding="utf-8"))
    assert [item["version"] for item in history["tools"][0]["versions"]] == ["0.3.0"]
    assert daily["tools"][0]["versions"][0]["curated"] is True
