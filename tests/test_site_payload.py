from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import build as build_script

LANGUAGES = ("zh-TW", "en")


def _raw(version: str, entries: list[str]) -> dict[str, Any]:
    return {
        "version": version,
        "period": "2026-07-25",
        "source_url": f"https://example.test/{version}",
        "fetched_at": "2026-07-25T00:00:00Z",
        "entries": entries,
    }


def _curated(version: str, originals: list[str]) -> dict[str, Any]:
    return {
        "version": version,
        "period": "2026-07-25",
        "items": [
            {
                "title": {language: f"{language} title {index}" for language in LANGUAGES},
                "body": {language: f"{language} body {index}" for language in LANGUAGES},
                "original": original,
            }
            for index, original in enumerate(originals, 1)
        ],
    }


def _configure_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, list[dict[str, Any]]]:
    records = {
        "alpha": [
            {
                "version": "2.0.0",
                "raw": _raw("2.0.0", ["Alpha first", "Alpha second"]),
                "curated": _curated("2.0.0", ["Alpha first", "Alpha second"]),
            },
            {
                "version": "1.0.0",
                "raw": _raw("1.0.0", ["Alpha old"]),
                "curated": None,
            },
        ],
        "beta": [
            {
                "version": "3.0.0",
                "raw": _raw("3.0.0", ["Beta first"]),
                "curated": _curated("3.0.0", ["Beta first"]),
            }
        ],
    }
    for tool_id, versions in records.items():
        raw_dir = tmp_path / "data" / "raw" / tool_id
        curated_dir = tmp_path / "data" / "curated" / tool_id
        raw_dir.mkdir(parents=True)
        curated_dir.mkdir(parents=True)
        for version in versions:
            name = str(version["version"])
            (raw_dir / f"{name}.json").write_text(
                json.dumps(version["raw"]), encoding="utf-8"
            )
            if version["curated"] is not None:
                (curated_dir / f"{name}.json").write_text(
                    json.dumps(version["curated"]), encoding="utf-8"
                )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text(
        "<!-- STATIC-SUMMARY:START --><!-- STATIC-SUMMARY:END -->",
        encoding="utf-8",
    )
    monkeypatch.setattr(build_script, "ROOT", tmp_path)
    monkeypatch.setattr(build_script, "DATA", tmp_path / "data")
    monkeypatch.setattr(
        build_script,
        "TOOLS",
        (("alpha", "Alpha"), ("beta", "Beta")),
    )
    return records


def test_site_payload_splits_history_without_losing_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = _configure_build(tmp_path, monkeypatch)
    build_script.build()

    payload = json.loads((tmp_path / "docs" / "data.json").read_text(encoding="utf-8"))
    assert len(payload["tools"]) == len(records)
    for tool in payload["tools"]:
        assert all(set(version) == {"version", "period"} for version in tool["versions"])
        assert "raw" not in tool["versions"][0]
        assert "curated" not in tool["versions"][0]

        history_path = tmp_path / "docs" / "history" / f"{tool['id']}.json"
        assert history_path.is_file()
        history = json.loads(history_path.read_text(encoding="utf-8"))
        expected = {
            "id": tool["id"],
            "name": tool["name"],
            "versions": records[tool["id"]],
        }
        assert history == expected
        assert tool["latest"] == expected["versions"][0]


def test_static_page_renders_originals_once_and_keeps_all_languages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = _configure_build(tmp_path, monkeypatch)
    build_script.build()

    page = (
        tmp_path / "docs" / "v" / "alpha" / "2.0.0" / "index.html"
    ).read_text(encoding="utf-8")
    curated = records["alpha"][0]["curated"]
    assert curated is not None
    assert page.count("Original changelog") == len(curated["items"])
    for item in curated["items"]:
        assert page.count(item["original"]) == 1
        for language in LANGUAGES:
            assert item["title"][language] in page
            assert item["body"][language] in page


def test_static_page_and_feed_strip_analogy_markers() -> None:
    """⟦⟧ 是給主站前端抓比喻用的機器標記（PLAYBOOK 鐵則 5），靜態頁與 RSS 沒有比喻框，
    不准漏到讀者眼前。"""
    html = build_script._render_body("開場。⟦像把書籤夾回原頁。⟧收尾。")

    assert "⟦" not in html and "⟧" not in html
    assert "像把書籤夾回原頁。" in html

    version = {
        "curated": {
            "items": [{"title": {"zh-TW": "標題"}, "body": {"zh-TW": "開場。⟦像書籤。⟧收尾。"}}]
        }
    }
    description = build_script._description(version)

    assert "⟦" not in description and "⟧" not in description
