from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from html import unescape
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
    monkeypatch.setattr(
        build_script,
        "TOOL_OPERATING_SYSTEMS",
        {"alpha": "macOS", "beta": "Linux"},
    )
    return records


def test_site_payload_splits_history_without_losing_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = _configure_build(tmp_path, monkeypatch)
    for number in range(10, 0, -1):
        version = f"0.{number}.0"
        raw = _raw(version, [f"Alpha {number}"])
        records["alpha"].append({"version": version, "raw": raw, "curated": None})
        (tmp_path / "data" / "raw" / "alpha" / f"{version}.json").write_text(
            json.dumps(raw), encoding="utf-8"
        )
    old_history = tmp_path / "docs" / "history"
    old_history.mkdir()
    (old_history / "alpha.json").write_text("stale", encoding="utf-8")
    build_script.build()

    payload = json.loads((tmp_path / "docs" / "data.json").read_text(encoding="utf-8"))
    assert payload["history_page_size"] == build_script.HISTORY_PAGE_SIZE
    assert len(payload["tools"]) == len(records)
    assert not (old_history / "alpha.json").exists()
    for tool in payload["tools"]:
        assert all(set(version) == {"version", "period"} for version in tool["versions"])
        assert "raw" not in tool["versions"][0]
        assert "curated" not in tool["versions"][0]

        page_size = build_script.HISTORY_PAGE_SIZE
        pages = (len(records[tool["id"]]) + page_size - 1) // page_size
        parts = [
            json.loads((old_history / tool["id"] / f"{number}.json").read_text(encoding="utf-8"))
            for number in range(1, pages + 1)
        ]
        assert len(list((old_history / tool["id"]).glob("*.json"))) == pages
        assert all(part["id"] == tool["id"] and part["name"] == tool["name"] for part in parts)
        assert [part["page"] for part in parts] == list(range(1, pages + 1))
        assert all(part["pages"] == pages for part in parts)
        assert [len(part["versions"]) for part in parts] == [
            min(page_size, len(records[tool["id"]]) - index * page_size)
            for index in range(pages)
        ]
        assert [version for part in parts for version in part["versions"]] == records[tool["id"]]
        assert tool["latest"] == records[tool["id"]][0]


def test_search_index_contains_curated_cards_and_unique_code_keywords(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = _configure_build(tmp_path, monkeypatch)
    first = records["alpha"][0]
    first["curated"]["items"][0]["body"]["zh-TW"] = "使用 `/effort` 和 `same`"
    first["curated"]["items"][0]["body"]["en"] = "Use `/effort` and `same`"
    first["raw"]["entries"][0] = "Alpha `original` first"
    first["curated"]["items"][0]["original"] = "Alpha `original` first"
    first["curated"]["items"][0]["body"]["en"] += " `" + "x" * 41 + "`"
    (tmp_path / "data" / "raw" / "alpha" / "2.0.0.json").write_text(
        json.dumps(first["raw"]), encoding="utf-8"
    )
    (tmp_path / "data" / "curated" / "alpha" / "2.0.0.json").write_text(
        json.dumps(first["curated"]), encoding="utf-8"
    )
    build_script.build()

    path = tmp_path / "docs" / "search-index.json"
    raw_index = path.read_text(encoding="utf-8")
    index = json.loads(raw_index)
    expected_count = sum(
        len(version["curated"]["items"])
        for versions in records.values() for version in versions if version["curated"]
    )
    assert len(index["cards"]) == expected_count
    assert raw_index == json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    assert [card[:3] for card in index["cards"]] == [
        ["alpha", "2.0.0", 1], ["alpha", "2.0.0", 2], ["beta", "3.0.0", 1]
    ]
    assert index["cards"][0][3:5] == ["zh-TW title 1", "en title 1"]
    assert index["cards"][0][5] == "/effort same original"
    assert index["cards"][1][5] == ""


def test_enterprise_card_threshold_and_site_numbers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert build_script._is_enterprise_card({"original": "Enterprise\nplain\nSSO\nplain\nGateway"})
    assert not build_script._is_enterprise_card(
        {"original": "Enterprise\nplain\nplain\nplain\nGateway"}
    )
    assert not build_script._is_enterprise_card({"original": "Hide for non-enterprise accounts"})
    assert not build_script._is_enterprise_card({"original": ""})
    assert not build_script._is_enterprise_card({"original": "  \n\t"})
    assert build_script._is_enterprise_card({"original": "\n[Claude Tag] settings\n"})

    records = _configure_build(tmp_path, monkeypatch)
    first = records["alpha"][0]
    first["raw"]["entries"][1] = "Enterprise settings"
    first["curated"]["items"][1]["original"] = "Enterprise settings"
    (tmp_path / "data" / "raw" / "alpha" / "2.0.0.json").write_text(
        json.dumps(first["raw"]), encoding="utf-8"
    )
    (tmp_path / "data" / "curated" / "alpha" / "2.0.0.json").write_text(
        json.dumps(first["curated"]), encoding="utf-8"
    )
    build_script.build()
    payload = json.loads((tmp_path / "docs" / "data.json").read_text(encoding="utf-8"))
    assert payload["tools"][0]["versions"][0]["enterprise"] == [2]
    assert "enterprise" not in payload["tools"][0]["versions"][1]
    assert "enterprise" not in payload["tools"][1]["versions"][0]


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


def test_english_pages_and_language_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = _configure_build(tmp_path, monkeypatch)
    build_script.build()
    pages = tmp_path / "docs" / "v"
    zh = (pages / "alpha" / "2.0.0" / "index.html").read_text(encoding="utf-8")
    en = (pages / "alpha" / "2.0.0" / "en" / "index.html").read_text(encoding="utf-8")
    assert not (pages / "alpha" / "1.0.0" / "en").exists()
    assert (pages / "beta" / "3.0.0" / "en" / "index.html").exists()
    zh_url = build_script._page_url("alpha", "2.0.0")
    en_url = f"{zh_url}en/"
    for page in (zh, en):
        for language, url in (("zh-TW", zh_url), ("en", en_url), ("x-default", zh_url)):
            assert f'<link rel="alternate" hreflang="{language}" href="{url}">' in page
    raw_page = (pages / "alpha" / "1.0.0" / "index.html").read_text(encoding="utf-8")
    assert 'hreflang=' not in raw_page
    assert f'<a href="{en_url}" hreflang="en" lang="en">English</a>' in zh
    assert f'<a href="{zh_url}" hreflang="zh-TW" lang="zh-TW">繁體中文</a>' in en
    assert '<html lang="en">' in en
    assert f'<link rel="canonical" href="{en_url}">' in en
    assert '<meta property="og:locale" content="en_US">' in en
    assert '<meta property="og:locale:alternate" content="zh_TW">' in en
    assert '<section class="language-section" lang="en"><h2>Release notes</h2>' in en
    assert '<h2>Original changelog</h2>' in en
    assert '<section class="language-section" lang="zh-TW">' not in en
    assert 'zh-TW title' not in en
    assert 'zh-TW body' not in en
    assert 'aria-label="Page path"' in en
    assert 'Released: 2026-07-25' in en
    assert 'aria-label="Version navigation"' in en
    assert 'aria-label="Back to top" title="Back to top"' in en
    assert "Back to interactive view" in en
    assert 'Previous version</a>' not in en
    assert 'Next version</a>' not in en
    assert len(re.findall(r'id="card-\d+"', en)) == len(records["alpha"][0]["curated"]["items"])
    expected_title = "Alpha 2.0.0: en title 1 | Plain-language release notes"
    expected_description = "en body 1"
    assert f"<title>{expected_title}</title>" in en
    assert f'<meta name="description" content="{expected_description}">' in en
    assert f'<meta property="og:title" content="{expected_title}">' in en
    assert f'<meta name="twitter:title" content="{expected_title}">' in en
    assert f'"headline": "{expected_title}"' in en
    assert f'"description": "{expected_description}"' in en
    assert '"inLanguage": "en"' in en
    sitemap = ET.parse(tmp_path / "docs" / "sitemap.xml").getroot()
    locs = [entry.findtext("{*}loc") for entry in sitemap]
    assert en_url in locs
    assert f'{build_script._page_url("beta", "3.0.0")}en/' in locs
    assert f'{build_script._page_url("alpha", "1.0.0")}en/' not in locs
    llms = (tmp_path / "docs" / "llms.txt").read_text(encoding="utf-8")
    assert f"- [Alpha 2.0.0]({zh_url}) · [English]({en_url})" in llms
    assert f"- [Alpha 1.0.0]({build_script._page_url('alpha', '1.0.0')})\n" in llms


def test_english_page_neighbors_and_escaped_title() -> None:
    versions = [
        {"version": number, "raw": _raw(number, ["Original"]),
         "curated": _curated(number, ["Original"])}
        for number in ("3.0.0", "2.0.0", "1.0.0")
    ]
    versions[0]["curated"] = None
    versions[1]["curated"]["items"][0]["title"]["en"] = "A < B & C"
    page = build_script._render_static_page(
        {"id": "claude_code", "name": "Claude Code"}, 1, versions, "en"
    )
    previous_url = build_script._page_url("claude_code", "1.0.0") + "en/"
    assert f'<a href="{previous_url}">Previous version</a>' in page
    assert "Next version</a>" not in page
    assert "A &lt; B &amp; C" in page
    assert "A < B & C" not in page.split("<script type=\"application/ld+json\">")[0]
    assert "Plain-language release notes" in page.split("</title>")[0]
    assert 'id="card-1"' in page
    versions[1]["curated"]["items"][0]["title"]["en"] = "Long " * 20
    long_page = build_script._render_static_page(
        {"id": "claude_code", "name": "Claude Code"}, 1, versions, "en"
    )
    assert "Plain-language release notes" not in long_page.split("</title>")[0]
    single = build_script._render_static_page(
        {"id": "claude_code", "name": "Claude Code"}, 0, [versions[1]], "en"
    )
    assert "Previous version</a>" not in single
    assert "Next version</a>" not in single


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


def test_feeds_include_visible_versions_in_date_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_build(tmp_path, monkeypatch)
    tools = []
    for tool_id, name in build_script.TOOLS:
        versions = []
        for number in range(25):
            period = (date(2026, 9, 28) - timedelta(days=number)).isoformat()
            version = f"1.{number}.0"
            raw = _raw(version, [f"Raw `{tool_id}` {number}"])
            raw["period"] = period
            curated = None
            if number == 1:
                curated = _curated(version, ["Original"])
                curated["period"] = period
                curated["items"][0]["title"]["en"] = "⟦New `feature`⟧"
                curated["items"][0]["body"]["en"] = "First `sentence`. Second sentence."
            versions.append({"version": version, "raw": raw, "curated": curated})
        tools.append({"id": tool_id, "name": name, "versions": versions})
    stale = tmp_path / "docs" / "feed" / "stale.xml"
    stale.parent.mkdir()
    stale.write_text("old", encoding="utf-8")
    build_script._write_rss_feed(tools)

    assert not stale.exists()
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for tool_id, name in build_script.TOOLS:
        channel = ET.parse(tmp_path / "docs" / "feed" / f"{tool_id}.xml").getroot().find("channel")
        assert channel is not None
        assert channel.findtext("title") == f"AI Updates · {name}"
        assert channel.find("atom:link", ns).get("href") == (
            f"{build_script.SITE_URL}feed/{tool_id}.xml"
        )
        items = channel.findall("item")
        assert len(items) == 20
        assert [item.findtext("title") for item in items] == [
            f"{name} 1.{number}.0" for number in range(20)
        ]
        assert items[1].findtext("description") == "New feature: First sentence. Second sentence."
        assert "`" not in items[0].findtext("description")

    channel = ET.parse(tmp_path / "docs" / "feed.xml").getroot().find("channel")
    assert channel is not None
    assert channel.find("atom:link", ns).get("href") == f"{build_script.SITE_URL}feed.xml"
    items = channel.findall("item")
    assert len(items) == 30
    assert [item.findtext("title") for item in items] == [
        f"{name} 1.{number}.0"
        for number in range(15)
        for _, name in build_script.TOOLS
    ]


def test_headline_limits_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_build(tmp_path, monkeypatch)
    version = {
        "version": "2.0.0",
        "raw": _raw("2.0.0", ["Raw update"]),
        "curated": _curated("2.0.0", ["Raw update"]),
    }
    first = version["curated"]["items"][0]
    first["title"]["zh-TW"] = "前面有重點，" + "長" * 35
    first["title"]["en"] = "New feature, " + "word " * 15
    first["body"]["zh-TW"] = "先用 `設定` 完成" + "設" * 50 + "。後面這句不該出現。"
    assert build_script._headline(version, "zh-TW") == "前面有重點"
    assert build_script._headline(version, "en") == (
        "New feature, word word word word word word word word word"
    )
    first["title"]["zh-TW"] = "長" * 35
    first["title"]["en"] = "x" * 65
    assert build_script._headline(version, "zh-TW") == "長" * 30
    assert build_script._headline(version, "en") == "x" * 60
    first["title"]["zh-TW"] = ""
    assert build_script._headline(version, "zh-TW") == ""
    first["title"]["zh-TW"] = "⟦" + "長" * 30 + "⟧"
    page = build_script._render_static_page(
        {"id": "alpha", "name": "Alpha"}, 0, [version]
    )
    title = unescape(re.search(r"<title>(.*?)</title>", page).group(1))
    assert title == f"Alpha 2.0.0：{'長' * 30}｜更新白話速報"
    assert "`" not in re.search(r'<meta name="description" content="([^"]*)"', page).group(1)
    lead = "先用 設定 完成" + "設" * 50 + "。"
    assert f'content="{lead}"' in page
    assert '<meta property="og:title" content="' + title + '">' in page
    assert '<meta name="twitter:title" content="' + title + '">' in page
    assert f'<meta property="og:description" content="{lead}">' in page
    assert f'<meta name="twitter:description" content="{lead}">' in page
    assert '"headline": "' + title + '"' in page
    assert f'"description": "{lead}"' in page
    second = "第二句補上" + "長" * 50 + "。"
    first["body"]["zh-TW"] = "很短。" + second + "第三句不該出現。"
    assert build_script._description(version, "zh-TW") == "很短。" + second

    version["version"] = "very-long-version-name-that-removes-the-suffix"
    page = build_script._render_static_page(
        {"id": "alpha", "name": "Alpha"}, 0, [version]
    )
    title = unescape(re.search(r"<title>(.*?)</title>", page).group(1))
    assert title == f"Alpha {version['version']}：{'長' * 30}"
    assert "｜更新白話速報" not in page


def test_card_ids_keep_curated_positions_and_raw_fallback() -> None:
    version = {
        "version": "1.0.0",
        "raw": _raw("1.0.0", ["Raw `entry`"]),
        "curated": _curated("1.0.0", ["First", "Skipped", "Third"]),
    }
    version["curated"]["items"][1]["title"] = {"zh-TW": "", "en": ""}
    version["curated"]["items"][1]["body"] = {"zh-TW": "", "en": ""}
    zh = build_script._render_items(version, "zh-TW", card_ids=True)
    en = build_script._render_items(version, "en")
    assert re.findall(r'id="card-(\d+)"', zh) == ["1", "3"]
    assert 'id="card-' not in en

    version["curated"] = None
    assert build_script._headline(version, "zh-TW") == ""
    assert build_script._description(version) == "Raw `entry`"
    assert 'id="card-' not in build_script._render_items(version, "zh-TW", card_ids=True)


def test_long_lead_uses_existing_truncation_rule() -> None:
    version = {"curated": _curated("1.0.0", ["Original"])}
    first = version["curated"]["items"][0]
    first["body"]["zh-TW"] = "甲" * 140 + "，" + "乙" * 30 + "。後句。"
    description = build_script._description(version)
    assert description == "甲" * 140 + "，…"
    assert len(description) <= 150


def test_feed_with_one_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_build(tmp_path, monkeypatch)
    version = {"version": "1.0.0", "raw": _raw("1.0.0", ["Only release"]), "curated": None}
    build_script._write_rss_feed([{"id": "alpha", "name": "Alpha", "versions": [version]}])
    channel = ET.parse(tmp_path / "docs" / "feed" / "alpha.xml").getroot().find("channel")
    assert channel is not None
    assert len(channel.findall("item")) == 1


def test_goatcounter_script_is_in_every_page_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = build_script.GOATCOUNTER_SCRIPT
    versions = [{"version": "1.0.0", "raw": _raw("1.0.0", ["Original"]), "curated": None}]
    version_page = build_script._render_static_page(
        {"id": "claude_code", "name": "Claude Code"}, 0, versions, "zh-TW"
    )
    assert script in version_page
    (tmp_path / "docs").mkdir()
    monkeypatch.setattr(build_script, "ROOT", tmp_path)
    build_script._write_not_found_page()
    assert script in (tmp_path / "docs" / "404.html").read_text(encoding="utf-8")
    index_path = Path(__file__).resolve().parents[1] / "docs" / "index.html"
    assert script in index_path.read_text(encoding="utf-8")
