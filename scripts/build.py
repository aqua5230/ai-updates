#!/usr/bin/env python3
"""Build compatibility and history feeds from raw and curated records."""

from __future__ import annotations

import json
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from email.utils import format_datetime
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TOOLS = (
    ("claude_code", "Claude Code"),
    ("codex", "Codex"),
    ("agy", "Antigravity"),
    ("usage", "Usage"),
    ("gh_cli", "GitHub CLI"),
)
# Single source of truth for build outputs; add new outputs only here.
BUILD_OUTPUTS = (
    "ai_updates.json",
    "daily.json",
    "docs/data.json",
    "docs/index.html",
    "docs/feed.xml",
    "docs/sitemap.xml",
    "docs/robots.txt",
    "docs/llms.txt",
    "docs/history",
    "docs/v",
)
SITE_URL = "https://aqua5230.github.io/ai-updates/"
LANGUAGES = ("zh-TW", "en", "zh-CN", "ja", "ko")
PLACEHOLDER_PREFIXES = (
    "bug fixes and reliability improvements",
    "no user-facing changes",
    "published a version-only release",
)

# Curated records that predate the spec: their originals do not line up with the
# raw entries, or their period disagrees with the raw record. The data is left as
# it is; the check exists to keep new and edited records honest. A full dry-run
# (2026-08-31) cleared 297 of the 319 curated files, leaving these 22. A version
# that starts failing does not belong here — fix the data instead.
LEGACY_COVERAGE_EXEMPT = frozenset({
    "agy/1.0.14", "agy/1.0.16", "agy/1.1.1",
    "claude_code/2.1.197", "claude_code/2.1.202", "claude_code/2.1.206", "claude_code/2.1.207",
    "codex/0.140.0", "codex/0.141.0", "codex/0.142.0", "codex/0.142.2", "codex/0.142.3",
    "codex/0.143.0", "codex/0.144.0", "codex/0.144.1",
    "usage/0.5.0", "usage/0.6.1", "usage/0.6.3",
    "usage/0.11.16", "usage/0.15.7", "usage/0.16.0", "usage/0.28.1",
})


def _load_versions(layer: str, tool_id: str) -> dict[str, dict[str, Any]]:
    directory = DATA / layer / tool_id
    versions: dict[str, dict[str, Any]] = {}
    if not directory.exists():
        return versions
    for path in directory.glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        _validate_record(path, layer, value)
        if value["version"] != path.stem:
            raise ValueError(f"{path}: version must match filename")
        versions[path.stem] = value
    return versions


def _validate_record(path: Path, layer: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{path}: record must be an object")

    required = ("version", "period")
    if layer == "raw":
        required += ("source_url", "fetched_at", "entries")
    else:
        required += ("items",)
    for field in required:
        if field not in value:
            raise ValueError(f"{path}: missing {field}")

    for field in required:
        if field in {"entries", "items"}:
            continue
        if not isinstance(value[field], str):
            raise ValueError(f"{path}: {field} must be a string")

    if layer == "raw":
        entries = value["entries"]
        if not isinstance(entries, list) or any(not isinstance(entry, str) for entry in entries):
            raise ValueError(f"{path}: entries must be a list[str]")
        return

    # An empty items list is legitimate: maintenance-only releases have nothing worth rewriting.
    items = value["items"]
    if not isinstance(items, list):
        raise ValueError(f"{path}: items must be a list[dict]")
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: items[{index}] must be a dict")
        for field in ("title", "body"):
            localized = item.get(field)
            if not isinstance(localized, dict):
                raise ValueError(f"{path}: items[{index}].{field} must be a dict")
            for language in LANGUAGES:
                text = localized.get(language)
                if not isinstance(text, str) or not text.strip():
                    raise ValueError(
                        f"{path}: items[{index}].{field}.{language} must be a non-empty string"
                    )
        original = item.get("original")
        if not isinstance(original, str) or not original.strip():
            raise ValueError(f"{path}: items[{index}].original must be a non-empty string")


def _version_key(version: str) -> tuple[Any, ...]:
    core, separator, prerelease = version.partition("-")
    core_key = tuple(int(part) for part in core.split("."))
    if not separator:
        return core_key, 1, ()

    prerelease_key = tuple(
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in prerelease.split(".")
    )
    return core_key, 0, prerelease_key


def _period_end_date(period: str) -> str:
    match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})(?:\s*~\s*(?:(\d{4})-)?(\d{2})-(\d{2}))?", period
    )
    if match is None:
        raise ValueError(f"invalid period for ISO publication date: {period}")
    start = date.fromisoformat(match.group(1))
    if match.group(3) is None:
        return start.isoformat()
    end = date(int(match.group(2) or start.year), int(match.group(3)), int(match.group(4)))
    return end.isoformat()


def _validate_curated_coverage(
    tool_id: str,
    raw_versions: dict[str, dict[str, Any]],
    curated_versions: dict[str, dict[str, Any]],
) -> None:
    for version, curated in curated_versions.items():
        raw = raw_versions.get(version)
        if raw is None or f"{tool_id}/{version}" in LEGACY_COVERAGE_EXEMPT:
            continue
        # A placeholder release has nothing worth rewriting, so an empty curated
        # items list legitimately leaves its raw entry uncovered.
        if is_placeholder(raw, version):
            continue

        curated_path = DATA / "curated" / tool_id / f"{version}.json"
        if curated["period"] != raw["period"]:
            raise ValueError(
                f"{curated_path}: period {curated['period']!r} does not match "
                f"raw period {raw['period']!r}"
            )

        # Split both sides by line: a release body with no bullets falls back to
        # one multi-line entry, which no single original line could ever equal.
        raw_lines = {
            line.strip()
            for entry in raw["entries"]
            for line in entry.splitlines()
            if line.strip()
        }
        original_lines = {
            line.strip()
            for item in curated["items"]
            for line in item["original"].splitlines()
            if line.strip()
        }
        missing_lines = raw_lines - original_lines
        if missing_lines:
            raise ValueError(
                f"{curated_path}: raw entries not covered by original: "
                f"{sorted(missing_lines)!r}"
            )
        extra_lines = original_lines - raw_lines
        if extra_lines:
            raise ValueError(
                f"{curated_path}: original contains lines absent from raw entries: "
                f"{sorted(extra_lines)!r}"
            )


def _validate_version_metadata(
    layer: str, tool_id: str, versions: dict[str, dict[str, Any]]
) -> None:
    for version, record in versions.items():
        path = DATA / layer / tool_id / f"{version}.json"
        try:
            _version_key(version)
        except ValueError as error:
            raise ValueError(f"{path}: invalid version {version!r}") from error
        try:
            _period_end_date(record["period"])
        except ValueError as error:
            raise ValueError(f"{path}: invalid period {record['period']!r}") from error


def _load_and_validate_data() -> dict[
    str, tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]
]:
    loaded = {}
    for tool_id, _ in TOOLS:
        raw = _load_versions("raw", tool_id)
        curated = _load_versions("curated", tool_id)
        _validate_version_metadata("raw", tool_id, raw)
        _validate_version_metadata("curated", tool_id, curated)
        _validate_curated_coverage(tool_id, raw, curated)
        loaded[tool_id] = (raw, curated)
    _validate_static_summary_marker()
    return loaded


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
        if entry.casefold().startswith(PLACEHOLDER_PREFIXES):
            continue

        match = re.fullmatch(r"release\s+(.+)", entry, flags=re.IGNORECASE)
        if match is not None:
            entry_version = re.sub(r"\s+", "", match.group(1).casefold())
            entry_version = re.sub(r"^(?:rust[-_])?v(?=\d)", "", entry_version)
            if entry_version != normalized_version:
                return False
            continue

        if re.fullmatch(
            r"no\s+user-facing\s+changes\s+in\s+this\s+(?:patch\s+)?release\.?",
            entry,
            flags=re.IGNORECASE,
        ):
            continue

        match = re.fullmatch(
            r"published\s+a\s+version-only\s+release\s+with\s+no\s+merged\s+pull\s+request"
            r"\s+changes\s+since\s+`?\s*([a-z0-9._\s-]+?)\s*`?\s*\.",
            entry,
            flags=re.IGNORECASE,
        )
        if match is None:
            return False
        referenced_version = re.sub(r"\s+", "", match.group(1).casefold())
        referenced_version = re.sub(r"^(?:rust[-_])?v(?=\d)", "", referenced_version)
        if re.fullmatch(r"\d+(?:[._-][a-z0-9]+)+", referenced_version) is None:
            return False
    return True


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _page_url(tool_id: str, version: str) -> str:
    return f"{SITE_URL}v/{tool_id}/{version}/"


def _localized(value: Any, language: str) -> str:
    return value.get(language, "") if isinstance(value, dict) else ""


def _curated_items(version: dict[str, Any]) -> list[dict[str, Any]]:
    curated = version.get("curated")
    if not isinstance(curated, dict):
        return []
    return [item for item in curated.get("items", []) if isinstance(item, dict)]


def _description(version: dict[str, Any], language: str = "zh-TW") -> str:
    items = _curated_items(version)
    if items:
        first = items[0]
        body = _strip_prose_only(_strip_analogy_marks(_localized(first.get("body"), language)))
        return f"{_localized(first.get('title'), language)} {body}"[:150]
    raw = version.get("raw")
    entries = raw.get("entries", []) if isinstance(raw, dict) else []
    return " ".join(entry for entry in entries if isinstance(entry, str))[:150]


def _rss_pub_date(period: str) -> str:
    published = datetime.fromisoformat(_period_end_date(period)).replace(tzinfo=UTC)
    return format_datetime(published, usegmt=True)


def _write_rss_feed(history_tools: list[dict[str, Any]]) -> None:
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "AI Updates"
    ET.SubElement(channel, "link").text = SITE_URL
    ET.SubElement(channel, "description").text = "Plain-language updates for AI developer tools."
    ET.SubElement(channel, "language").text = "en"

    for tool in history_tools:
        versions = tool.get("versions", [])
        if not versions:
            continue
        version = versions[0]
        version_name = str(version["version"])
        url = _page_url(str(tool["id"]), version_name)
        period = str((version.get("curated") or version.get("raw") or {}).get("period", ""))
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"{tool['name']} {version_name}"
        ET.SubElement(item, "link").text = url
        ET.SubElement(item, "pubDate").text = _rss_pub_date(period)
        ET.SubElement(item, "description").text = _description(version, "en")

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(ROOT / "docs" / "feed.xml", encoding="utf-8", xml_declaration=True)


ANALOGY_MARKS = str.maketrans("", "", "⟦⟧")


def _strip_analogy_marks(text: str) -> str:
    """⟦⟧ 是給主站前端抓比喻用的機器標記，不是內文。靜態頁與 RSS 沒有比喻框，照散文顯示但要脫記號。"""
    return text.translate(ANALOGY_MARKS)


def _strip_prose_only(text: str) -> str:
    """meta description 與 RSS 摘要要單行散文：拿掉三反引號程式碼框，換行壓成空白。

    設定型與指令型卡片會用程式碼框放可照抄的 JSON 或指令，前 150 字截斷剛好切在框裡時，
    分享預覽與搜尋結果會出現一段裸的三反引號（2026-09-03 發現，當時 claude_code/2.1.216
    與 gh_cli/2.99.0 都已中招）。頁面內文照原樣渲染程式碼框，只有摘要需要剝掉。
    """
    without_fences = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    return re.sub(r"\s+", " ", without_fences).strip()


def _render_inline_code(text: str) -> str:
    parts = re.split(r"(`[^`]+`)", text)
    return "".join(
        f"<code>{escape(part[1:-1])}</code>"
        if part.startswith("`") and part.endswith("`")
        else escape(part)
        for part in parts
    )


FENCED_CODE_RE = re.compile(
    r"^[ \t]*```[ \t]*[A-Za-z0-9_+-]*[ \t]*\r?\n([\s\S]*?)\r?\n^[ \t]*```[ \t]*(?=\r?$)",
    re.MULTILINE,
)


def _render_body(text: str) -> str:
    text = _strip_analogy_marks(text)
    blocks = []
    cursor = 0
    for match in FENCED_CODE_RE.finditer(text):
        prose = re.sub(r"\r?\n$", "", text[cursor:match.start()])
        if prose:
            blocks.append(f"<p>{_render_inline_code(prose)}</p>")
        blocks.append(f'<pre class="code-block"><code>{escape(match.group(1))}</code></pre>')
        cursor = match.end()
        if text.startswith("\r\n", cursor):
            cursor += 2
        elif text.startswith("\n", cursor):
            cursor += 1
    prose = text[cursor:]
    if prose:
        blocks.append(f"<p>{_render_inline_code(prose)}</p>")
    return "".join(blocks)


def _render_items(
    version: dict[str, Any], language: str, *, include_original: bool = True
) -> str:
    items = _curated_items(version)
    if items:
        blocks = []
        for item in items:
            title = _localized(item.get("title"), language)
            body = _localized(item.get("body"), language)
            if title or body:
                original = ""
                if include_original:
                    original = (
                        "<details><summary>Original changelog</summary>"
                        f"<pre>{escape(str(item.get('original', '')))}</pre></details>"
                    )
                blocks.append(f"<article><h3>{escape(title)}</h3>{_render_body(body)}{original}</article>")
        return "\n".join(blocks) or "<p>沒有可用的整理內容。</p>"

    raw = version.get("raw")
    entries = raw.get("entries", []) if isinstance(raw, dict) else []
    return "\n".join(f"<article><pre>{escape(entry)}</pre></article>" for entry in entries if isinstance(entry, str)) or "<p>沒有可用的原始更新內容。</p>"


def _render_originals(version: dict[str, Any]) -> str:
    return "\n".join(
        "<article><details><summary>Original changelog</summary>"
        f"<pre>{escape(str(item.get('original', '')))}</pre></details></article>"
        for item in _curated_items(version)
    )


def _render_static_page(
    tool: dict[str, Any], index: int, versions: list[dict[str, Any]]
) -> str:
    version = versions[index]
    version_name = str(version["version"])
    tool_id = str(tool["id"])
    name = str(tool["name"])
    period = str((version.get("curated") or version.get("raw") or {}).get("period", ""))
    description = _description(version)
    release_notes = []
    items = _curated_items(version)
    if items:
        release_notes = [
            _localized(item.get("title"), "zh-TW")
            for item in items
            if _localized(item.get("title"), "zh-TW")
        ]
    structured_data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "softwareVersion": version_name,
        "datePublished": _period_end_date(period),
        "releaseNotes": "；".join(release_notes),
    }
    json_ld = json.dumps(structured_data, ensure_ascii=False).replace("</", "<\\/")
    previous_link = (
        f'<a href="{escape(_page_url(tool_id, str(versions[index + 1]["version"])), quote=True)}">上一版</a>'
        if index + 1 < len(versions)
        else ""
    )
    next_link = (
        f'<a href="{escape(_page_url(tool_id, str(versions[index - 1]["version"])), quote=True)}">下一版</a>'
        if index > 0
        else ""
    )
    if items:
        language_sections = "\n".join(
            f'<section lang="{language}"><h2>{escape(language)}</h2>'
            f'{_render_items(version, language, include_original=False)}</section>'
            for language in LANGUAGES
        )
        language_sections += f"\n<section><h2>原始 CHANGELOG</h2>{_render_originals(version)}</section>"
    else:
        language_sections = f'<section><h2>Original changelog</h2>{_render_items(version, "zh-TW")}</section>'
    title = f"{name} {version_name} 更新白話速報"
    url = _page_url(tool_id, version_name)
    return f'''<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description, quote=True)}">
  <link rel="canonical" href="{escape(url, quote=True)}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{escape(title, quote=True)}">
  <meta property="og:description" content="{escape(description, quote=True)}">
  <meta property="og:url" content="{escape(url, quote=True)}">
  <meta property="og:image" content="{SITE_URL}og-image.png">
  <script type="application/ld+json">{json_ld}</script>
  <style>:root{{color-scheme:light dark}}body{{font:16px/1.65 system-ui,sans-serif;max-width:54rem;margin:auto;padding:2rem}}article{{border-bottom:1px solid #999;padding:1rem 0}}article p{{white-space:pre-line}}h1,h2,h3{{line-height:1.25}}code{{font:.9em "JetBrains Mono",monospace;color:#f0f6fc;background:#0d1117;border-radius:4px;padding:.1em .35em;overflow-wrap:anywhere;word-break:break-word}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}pre.code-block{{font:.85em/1.5 "JetBrains Mono",monospace;color:#f0f6fc;background:#0d1117;border-radius:6px;padding:.75rem}}pre.code-block code{{font:inherit;background:transparent;padding:0}}a{{color:LinkText}}nav{{display:flex;gap:1rem;flex-wrap:wrap}}</style>
</head>
<body>
  <header><h1>{escape(name)} {escape(version_name)}</h1><p>發布日期：{escape(period)}</p></header>
  <main>{language_sections}</main>
  <footer><nav><a href="{SITE_URL}#{tool_id}/{version_name}">回到互動版</a>{previous_link}{next_link}</nav></footer>
</body>
</html>
'''


def _write_static_pages(history_tools: list[dict[str, Any]]) -> int:
    pages_root = ROOT / "docs" / "v"
    shutil.rmtree(pages_root, ignore_errors=True)
    page_count = 0
    sitemap_entries = [f"  <url><loc>{SITE_URL}</loc></url>"]
    llms_sections = [
        "# AI Updates",
        "五語 AI 工具 changelog 白話翻譯站。",
        "資料每日更新。",
    ]
    for tool in history_tools:
        versions = tool["versions"]
        llms_sections.append(f"\n## {tool['name']}")
        for index, version in enumerate(versions):
            version_name = str(version["version"])
            path = pages_root / str(tool["id"]) / version_name / "index.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_render_static_page(tool, index, versions), encoding="utf-8")
            url = _page_url(str(tool["id"]), version_name)
            period = str((version.get("curated") or version.get("raw") or {}).get("period", ""))
            lastmod = _period_end_date(period)
            sitemap_entries.append(f"  <url><loc>{escape(url)}</loc><lastmod>{escape(lastmod)}</lastmod></url>")
            llms_sections.append(f"- {url}")
            page_count += 1
    (ROOT / "docs" / "sitemap.xml").write_text(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        + "\n".join(sitemap_entries)
        + "\n</urlset>\n",
        encoding="utf-8",
    )
    (ROOT / "docs" / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8")
    (ROOT / "docs" / "llms.txt").write_text("\n".join(llms_sections) + "\n", encoding="utf-8")
    _write_rss_feed(history_tools)
    return page_count


def _write_static_summary(history_tools: list[dict[str, Any]]) -> None:
    index_path = ROOT / "docs" / "index.html"
    if not index_path.exists():
        return
    index = index_path.read_text(encoding="utf-8")
    links = []
    for tool in history_tools:
        if tool["versions"]:
            latest = tool["versions"][0]
            links.append(
                f'<li><a href="{escape(_page_url(str(tool["id"]), str(latest["version"])), quote=True)}">'
                f'{escape(str(tool["name"]))} {escape(str(latest["version"]))}</a></li>'
            )
    summary = "<!-- STATIC-SUMMARY:START -->\n  <noscript><section><h1>AI 工具更新速報</h1><p>最新版本：</p><ul>" + "".join(links) + "</ul></section></noscript>\n  <!-- STATIC-SUMMARY:END -->"
    updated, count = re.subn(
        r"<!-- STATIC-SUMMARY:START -->.*?<!-- STATIC-SUMMARY:END -->", summary, index, flags=re.DOTALL
    )
    if count != 1:
        raise ValueError("docs/index.html must contain exactly one STATIC-SUMMARY marker block")
    index_path.write_text(updated, encoding="utf-8")


def _validate_static_summary_marker() -> None:
    index_path = ROOT / "docs" / "index.html"
    if not index_path.exists():
        return
    index = index_path.read_text(encoding="utf-8")
    count = len(re.findall(r"<!-- STATIC-SUMMARY:START -->.*?<!-- STATIC-SUMMARY:END -->", index, re.DOTALL))
    if count != 1:
        raise ValueError("docs/index.html must contain exactly one STATIC-SUMMARY marker block")


def build() -> None:
    generated_at = date.today().isoformat()
    app_tools: list[dict[str, Any]] = []
    history_tools: list[dict[str, Any]] = []
    site_tools: list[dict[str, Any]] = []
    daily_tools: list[dict[str, Any]] = []
    loaded = _load_and_validate_data()
    for tool_id, name in TOOLS:
        raw, curated = loaded[tool_id]
        curated_latest = sorted(curated, key=_version_key, reverse=True)[:3]
        app_tools.append(
            {"id": tool_id, "name": name, "versions": [curated[v] for v in curated_latest]}
        )

        all_versions = sorted(set(raw) | set(curated), key=_version_key, reverse=True)
        visible_versions = [
            version
            for version in all_versions
            if version in curated or not is_placeholder(raw[version], version)
        ]
        history_tool = {
            "id": tool_id,
            "name": name,
            "versions": [
                {"version": version, "raw": raw.get(version), "curated": curated.get(version)}
                for version in visible_versions
            ],
        }
        history_tools.append(history_tool)
        latest = next(
            (version for version in history_tool["versions"] if version["curated"]),
            history_tool["versions"][0] if history_tool["versions"] else None,
        )
        site_tools.append(
            {
                "id": tool_id,
                "name": name,
                "latest": latest,
                "versions": [
                    {
                        "version": version["version"],
                        "period": (version["curated"] or version["raw"] or {}).get("period", ""),
                    }
                    for version in history_tool["versions"]
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
    _write(ROOT / "docs" / "data.json", {"generated_at": generated_at, "tools": site_tools})
    for history_tool in history_tools:
        _write(
            ROOT / "docs" / "history" / f"{history_tool['id']}.json",
            history_tool,
        )
    _write(ROOT / "daily.json", {"generated_at": generated_at, "tools": daily_tools})
    _write_static_pages(history_tools)
    _write_static_summary(history_tools)


if __name__ == "__main__":
    build()
