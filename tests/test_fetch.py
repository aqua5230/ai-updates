from __future__ import annotations

import json
from pathlib import Path

from scripts import fetch
from scripts.sync_agy import parse_agy_changelog

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_claude_changelog_fixture() -> None:
    text = (FIXTURES / "claude_changelog.md").read_text(encoding="utf-8")

    assert fetch.parse_markdown_changelog(text) == [
        ("2.1.207", ["Added a visible feature.", "Fixed a bug."]),
        ("2.1.206", ["Improved startup time."]),
    ]


def test_parse_codex_releases_fixture() -> None:
    payload = json.loads((FIXTURES / "codex_releases.json").read_text(encoding="utf-8"))

    assert fetch.parse_github_releases(payload) == [
        {
            "version": "0.144.1",
            "period": "2026-07-10",
            "source_url": "https://github.com/openai/codex/releases/tag/rust-v0.144.1",
            "entries": ["Added one feature.", "Fixed one defect."],
        }
    ]


def test_parse_agy_changelog() -> None:
    assert parse_agy_changelog("1.2.3:\n· Added one thing.\n· Fixed another.\n") == [
        ("1.2.3", ["Added one thing.", "Fixed another."])
    ]


def test_raw_record_is_never_overwritten(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(fetch, "RAW_ROOT", tmp_path)
    record = {
        "version": "1.0.0",
        "period": "2026-07-13",
        "source_url": "https://example.invalid/changelog",
        "fetched_at": "2026-07-13",
        "entries": ["Original"],
    }
    assert fetch._write_raw("tool", record)
    record["entries"] = ["Changed"]
    assert not fetch._write_raw("tool", record)
    assert json.loads((tmp_path / "tool" / "1.0.0.json").read_text())["entries"] == [
        "Original"
    ]
