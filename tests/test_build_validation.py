from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import build as build_script

LANGUAGES = ("zh-TW", "en")


def _raw(version: str, period: str = "2026-07-08") -> dict[str, Any]:
    return {
        "version": version,
        "period": period,
        "source_url": "https://example.test/releases",
        "fetched_at": "2026-07-08T00:00:00Z",
        "entries": ["Official entry"],
    }


def _curated(version: str, period: str = "2026-07-08") -> dict[str, Any]:
    return {
        "version": version,
        "period": period,
        "items": [
            {
                "title": {language: "Title" for language in LANGUAGES},
                "body": {language: "Body" for language in LANGUAGES},
                "original": "Official entry",
            }
        ],
    }


def _configure_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    data = tmp_path / "data"
    raw_dir = data / "raw" / "codex"
    curated_dir = data / "curated" / "codex"
    raw_dir.mkdir(parents=True)
    curated_dir.mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.html").write_text(
        "<!-- STATIC-SUMMARY:START --><!-- STATIC-SUMMARY:END -->", encoding="utf-8"
    )
    monkeypatch.setattr(build_script, "ROOT", tmp_path)
    monkeypatch.setattr(build_script, "DATA", data)
    monkeypatch.setattr(build_script, "TOOLS", (("codex", "Codex"),))
    return raw_dir, curated_dir


def _write_pair(
    raw_dir: Path,
    curated_dir: Path,
    raw: dict[str, Any],
    curated: dict[str, Any],
) -> None:
    version = raw["version"]
    (raw_dir / f"{version}.json").write_text(json.dumps(raw), encoding="utf-8")
    (curated_dir / f"{version}.json").write_text(
        json.dumps(curated), encoding="utf-8"
    )


def test_version_key_orders_stable_and_prereleases() -> None:
    versions = [
        "0.143.0-alpha.38",
        "0.143.0-beta.1",
        "0.143.0-alpha.3.1",
        "0.143.0",
        "0.143.0-rc.1",
        "0.144.0",
        "2.1.218",
        "0.28.21",
        "1.1.6",
    ]

    assert sorted(versions, key=build_script._version_key, reverse=True) == [
        "2.1.218",
        "1.1.6",
        "0.144.0",
        "0.143.0",
        "0.143.0-rc.1",
        "0.143.0-beta.1",
        "0.143.0-alpha.38",
        "0.143.0-alpha.3.1",
        "0.28.21",
    ]


def test_coverage_rejects_raw_entry_missing_from_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    raw = _raw("1.0.0")
    raw["entries"] = ["Official entry", "Missing entry"]
    _write_pair(raw_dir, curated_dir, raw, _curated("1.0.0"))

    with pytest.raises(ValueError, match="raw entries not covered by original.*Missing entry"):
        build_script._load_and_validate_data()


def test_coverage_rejects_original_line_absent_from_raw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    curated = _curated("1.0.0")
    curated["items"][0]["original"] = "Official entry\nInvented entry"
    _write_pair(raw_dir, curated_dir, _raw("1.0.0"), curated)

    with pytest.raises(
        ValueError, match="original contains lines absent from raw entries.*Invented entry"
    ):
        build_script._load_and_validate_data()


def test_coverage_accepts_multiline_original_matching_raw_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    raw = _raw("1.0.0")
    raw["entries"] = ["First entry", "Second entry"]
    curated = _curated("1.0.0")
    curated["items"][0]["original"] = "  First entry  \n\nSecond entry"
    _write_pair(raw_dir, curated_dir, raw, curated)

    build_script._load_and_validate_data()


def test_coverage_rejects_period_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    _write_pair(
        raw_dir,
        curated_dir,
        _raw("1.0.0", "2026-07-08"),
        _curated("1.0.0", "2026-07-09"),
    )

    with pytest.raises(ValueError, match="period.*does not match raw period"):
        build_script._load_and_validate_data()


def test_coverage_skips_legacy_exempt_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    monkeypatch.setattr(build_script, "TOOLS", (("agy", "Antigravity"),))
    raw = _raw("1.0.14", "2026-07-08")
    raw["entries"] = ["Raw only"]
    curated = _curated("1.0.14", "2026-07-09")
    curated["items"][0]["original"] = "Curated only"
    _write_pair(raw_dir, curated_dir, raw, curated)

    build_script._load_and_validate_data()


def test_build_rejects_invalid_period_without_changing_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    _write_pair(
        raw_dir,
        curated_dir,
        _raw("1.0.0"),
        _curated("1.0.0", "bad"),
    )
    output_paths = [
        tmp_path / "ai_updates.json",
        tmp_path / "daily.json",
        tmp_path / "docs" / "data.json",
    ]
    for index, path in enumerate(output_paths):
        path.write_text(f"sentinel {index}\n", encoding="utf-8")
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in output_paths
    }

    with pytest.raises(ValueError, match=r"curated/codex/1\.0\.0\.json: invalid period 'bad'"):
        build_script.build()

    after = {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in output_paths
    }
    assert after == before


def test_build_rejects_missing_curated_language_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    (raw_dir / "1.0.0.json").write_text(json.dumps(_raw("1.0.0")), encoding="utf-8")
    curated = _curated("1.0.0")
    del curated["items"][0]["body"]["en"]
    (curated_dir / "1.0.0.json").write_text(json.dumps(curated), encoding="utf-8")

    with pytest.raises(ValueError, match=r"1\.0\.0\.json.*body\.en"):
        build_script.build()

    assert not (tmp_path / "ai_updates.json").exists()
    assert not (tmp_path / "daily.json").exists()
    assert not (tmp_path / "docs" / "data.json").exists()


def test_build_checks_static_summary_marker_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    (tmp_path / "docs" / "index.html").write_text("no marker", encoding="utf-8")
    (raw_dir / "1.0.0.json").write_text(json.dumps(_raw("1.0.0")), encoding="utf-8")
    (curated_dir / "1.0.0.json").write_text(
        json.dumps(_curated("1.0.0")), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="STATIC-SUMMARY"):
        build_script.build()

    assert not (tmp_path / "ai_updates.json").exists()
    assert not (tmp_path / "daily.json").exists()
    assert not (tmp_path / "docs" / "data.json").exists()


def test_build_uses_period_end_date_for_static_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    period = "2026-07-08 ~ 07-11"
    (raw_dir / "1.0.0.json").write_text(json.dumps(_raw("1.0.0", period)), encoding="utf-8")
    (curated_dir / "1.0.0.json").write_text(
        json.dumps(_curated("1.0.0", period)), encoding="utf-8"
    )

    build_script.build()

    page = (tmp_path / "docs" / "v" / "codex" / "1.0.0" / "index.html").read_text(
        encoding="utf-8"
    )
    sitemap = (tmp_path / "docs" / "sitemap.xml").read_text(encoding="utf-8")
    assert '"datePublished": "2026-07-11"' in page
    assert "<lastmod>2026-07-11</lastmod>" in sitemap
    assert "發布日期：2026-07-08 ~ 07-11" in page


def test_badge_treats_reverted_lines_as_fixes() -> None:
    original = "Fixed a crash\nReverted the 2.1.281 denial message change"
    assert build_script._badge_for(original, "提示訊息回歸既有設計")[0] == "fix"


def test_badge_reads_no_longer_and_instead_of_as_fixes() -> None:
    original = (
        "Restarting after a model switch no longer reverts to the previous model\n"
        "Pasted images over 50 MB are rejected instead of being dropped silently\n"
        "`grok -p --effort` warns when the model ignores the flag"
    )
    assert build_script._badge_for(original, "模型切換重啟不回彈")[0] == "fix"


def test_badge_keeps_title_when_card_adds_or_changes_behavior() -> None:
    added = "Added a Rex terminal mode\nInline tags no longer break line layout"
    changed = "Changed the limit to 8,192 characters instead of bytes"
    perf = "Startup no longer re-downloads the pricing table, cutting idle CPU"
    assert build_script._badge_for(added, "終端機支援 Rex")[0] == "new"
    assert build_script._badge_for(changed, "上限改採字元計")[0] == "new"
    assert build_script._badge_for(perf, "閒置效能提升")[0] == "perf"


def test_card_badges_use_zh_title_and_overrides() -> None:
    def item(zh: str, en: str) -> dict:
        return {"title": {"zh-TW": zh, "en": en}, "original": "Sessions keep their order"}

    curated = {"items": [
        item("工作階段可直接改名", "Fix session names"),
        item("保留未提交修改", "Keeps edits"),
        item("排序修正", "Order kept"),
    ]}
    assert build_script._card_badges(None, curated, {}) == ["new", "new", "fix"]
    assert build_script._card_badges(None, curated, {"3": "perf"}) == ["new", "new", "perf"]
    with pytest.raises(ValueError, match="out of range"):
        build_script._card_badges(None, curated, {"4": "new"})


def test_build_rejects_badge_overrides_for_unknown_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_dir, curated_dir = _configure_build(tmp_path, monkeypatch)
    _write_pair(raw_dir, curated_dir, _raw("1.0.0"), _curated("1.0.0"))
    (tmp_path / "data" / "badge_overrides.json").write_text(
        '{"codex/9.9.9": {"1": "new"}}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="unknown versions"):
        build_script.build()
