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
LANGUAGES = ("zh-TW", "en")
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
        text = f"{_strip_analogy_marks(_localized(first.get('title'), language))} {body}"
    else:
        raw = version.get("raw")
        entries = raw.get("entries", []) if isinstance(raw, dict) else []
        text = " ".join(entry for entry in entries if isinstance(entry, str))
    text = _strip_prose_only(_strip_analogy_marks(text))
    if len(text) <= 150:
        return text
    # Reserve one character for the ellipsis; prefer a complete sentence, then
    # punctuation or whitespace. Never cut an unbroken English word or URL.
    for pattern in (r"[。！？]|[.!?](?=\s|$)", r"[，、；：]|[,;:](?=\s|$)|\s+"):
        ends = [match.end() for match in re.finditer(pattern, text) if match.end() <= 149]
        if ends:
            return text[:ends[-1]].rstrip() + "…"
    return "…"


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
    """⟦⟧ 是給渲染器辨識比喻的機器標記，不是讀者可見的內文。"""
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
ANALOGY_RE = re.compile(r"⟦(.*?)⟧", re.DOTALL)
ANALOGY_ICON = (
    '<svg class="log-analogy-icon" viewBox="0 0 24 24" aria-hidden="true">'
    '<circle cx="12" cy="12" r="9"></circle>'
    '<path d="M12 8v5M12 16.5v.01"></path></svg>'
)


def _render_prose(text: str) -> str:
    """把散文與 ⟦比喻⟧ 分開渲染，並容忍未成對的標記。"""
    blocks = []
    cursor = 0
    for match in ANALOGY_RE.finditer(text):
        before = _strip_analogy_marks(text[cursor : match.start()])
        if before:
            blocks.append(f'<p class="log-prose-text">{_render_inline_code(before)}</p>')
        analogy = _strip_analogy_marks(match.group(1)).strip()
        if analogy:
            blocks.append(
                f'<aside class="log-analogy" role="note">{ANALOGY_ICON}'
                f"<span>{_render_inline_code(analogy)}</span></aside>"
            )
        cursor = match.end()
    prose = _strip_analogy_marks(text[cursor:])
    if prose:
        blocks.append(f'<p class="log-prose-text">{_render_inline_code(prose)}</p>')
    return "".join(blocks)


def _render_body(text: str) -> str:
    blocks = []
    cursor = 0
    for match in FENCED_CODE_RE.finditer(text):
        prose = re.sub(r"\r?\n$", "", text[cursor:match.start()])
        if prose:
            blocks.append(_render_prose(prose))
        blocks.append(
            '<pre class="log-code-block"><code>'
            f"{escape(_strip_analogy_marks(match.group(1)))}"
            "</code></pre>"
        )
        cursor = match.end()
        if text.startswith("\r\n", cursor):
            cursor += 2
        elif text.startswith("\n", cursor):
            cursor += 1
    prose = text[cursor:]
    if prose:
        blocks.append(_render_prose(prose))
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
                        f'<pre lang="en">{escape(str(item.get("original", "")))}</pre></details>'
                    )
                blocks.append(
                    '<article class="log-item-card">'
                    f'<h3 class="log-item-title">{escape(title)}</h3>'
                    f"{_render_body(body)}{original}</article>"
                )
        return "\n".join(blocks) or "<p>沒有可用的整理內容。</p>"

    raw = version.get("raw")
    entries = raw.get("entries", []) if isinstance(raw, dict) else []
    return "\n".join(
        '<article class="log-item-card"><pre class="log-code-block" lang="en">'
        f"{escape(_strip_analogy_marks(entry))}</pre></article>"
        for entry in entries
        if isinstance(entry, str)
    ) or "<p>沒有可用的原始更新內容。</p>"


def _render_originals(version: dict[str, Any]) -> str:
    # summary 逐則標上卡片標題：整段都寫「Original changelog」時，讀者分不出哪一則對應哪張卡。
    return "\n".join(
        '<details class="log-howto original-entry">'
        f'<summary>Original changelog<span class="original-entry-title">'
        f'{escape(_localized(item.get("title"), "zh-TW"))}</span></summary>'
        f'<pre class="log-code-block" lang="en">{escape(str(item.get("original", "")))}</pre>'
        "</details>"
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
        "@type": "TechArticle",
        "headline": f"{name} {version_name}",
        "datePublished": _period_end_date(period),
        "description": description,
        "inLanguage": list(LANGUAGES) if items else ["en"],
        "url": _page_url(tool_id, version_name),
        "about": {
            "@type": "SoftwareApplication",
            "name": name,
            "softwareVersion": version_name,
            "releaseNotes": "；".join(release_notes),
        },
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
            f'<section class="language-section" lang="{language}">'
            f'<h2>{"繁體中文" if language == "zh-TW" else "English"}</h2>'
            f'{_render_items(version, language, include_original=False)}</section>'
            for language in LANGUAGES
        )
        language_sections += (
            f'\n<section class="language-section"><h2>原始 CHANGELOG</h2>'
            f"{_render_originals(version)}</section>"
        )
    else:
        language_sections = (
            '<section class="language-section"><h2>Original changelog</h2>'
            f'{_render_items(version, "zh-TW")}</section>'
        )
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
  <meta property="og:locale" content="zh_TW">
  <meta property="og:locale:alternate" content="en_US">
  <meta property="og:title" content="{escape(title, quote=True)}">
  <meta property="og:description" content="{escape(description, quote=True)}">
  <meta property="og:url" content="{escape(url, quote=True)}">
  <meta property="og:image" content="{SITE_URL}og-image.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;500;600;700&family=Newsreader:wght@600&display=swap" rel="stylesheet">
  <script type="application/ld+json">{json_ld}</script>
  <style>
    :root{{color-scheme:light dark;--bg-color:oklch(0.176285 0.014021 258.357);--sidebar-bg:oklch(0.220223 0.015700 256.816);--text-color:oklch(0.856908 0.014132 247.992);--text-bright:oklch(0.970342 0.010275 247.932);--accent-color:oklch(0.715252 0.151810 253.306);--accent-contrast:oklch(0.176285 0.014021 258.357);--accent-glow:oklch(0.715252 0.151810 253.306 / .2);--border-color:oklch(0.270223 0.014885 252.310);--muted-color:oklch(0.662473 0.018141 250.922);--card-bg:oklch(0.245223 0.015700 256.816);--code-bg:oklch(0.159628 0.020332 265.576);--tag-new:oklch(0.695081 0.180928 145.621);--tag-fix:oklch(0.665118 0.204594 26.960);--tag-perf:oklch(0.719551 0.140145 79.915);interpolate-size:allow-keywords}}
    @media(prefers-color-scheme:light){{:root{{--bg-color:oklch(0.940 0.005 247.858);--sidebar-bg:oklch(0.975 0.004 247.858);--text-color:oklch(0.371696 0.039156 257.287);--text-bright:oklch(0.207682 0.039824 265.755);--accent-color:oklch(0.546150 0.215208 262.881);--accent-contrast:oklch(1 0 0);--accent-glow:oklch(0.546150 0.215208 262.881 / .15);--border-color:oklch(0.900 0.010 255.508);--muted-color:oklch(0.520 0.040717 257.417);--card-bg:oklch(0.995 0.002 247.858);--code-bg:oklch(0.968260 0.006854 247.896);--tag-new:oklch(0.527299 0.137103 150.069);--tag-fix:oklch(0.577099 0.215157 27.325);--tag-perf:oklch(0.555283 0.145505 48.998)}}}}
    :root[data-theme="light"]{{color-scheme:light;--bg-color:oklch(0.940 0.005 247.858);--sidebar-bg:oklch(0.975 0.004 247.858);--text-color:oklch(0.371696 0.039156 257.287);--text-bright:oklch(0.207682 0.039824 265.755);--accent-color:oklch(0.546150 0.215208 262.881);--accent-contrast:oklch(1 0 0);--accent-glow:oklch(0.546150 0.215208 262.881 / .15);--border-color:oklch(0.900 0.010 255.508);--muted-color:oklch(0.520 0.040717 257.417);--card-bg:oklch(0.995 0.002 247.858);--code-bg:oklch(0.968260 0.006854 247.896);--tag-new:oklch(0.527299 0.137103 150.069);--tag-fix:oklch(0.577099 0.215157 27.325);--tag-perf:oklch(0.555283 0.145505 48.998)}}
    :root[data-theme="dark"]{{color-scheme:dark;--bg-color:oklch(0.176285 0.014021 258.357);--sidebar-bg:oklch(0.220223 0.015700 256.816);--text-color:oklch(0.856908 0.014132 247.992);--text-bright:oklch(0.970342 0.010275 247.932);--accent-color:oklch(0.715252 0.151810 253.306);--accent-contrast:oklch(0.176285 0.014021 258.357);--accent-glow:oklch(0.715252 0.151810 253.306 / .2);--border-color:oklch(0.270223 0.014885 252.310);--muted-color:oklch(0.662473 0.018141 250.922);--card-bg:oklch(0.245223 0.015700 256.816);--code-bg:oklch(0.159628 0.020332 265.576);--tag-new:oklch(0.695081 0.180928 145.621);--tag-fix:oklch(0.665118 0.204594 26.960);--tag-perf:oklch(0.719551 0.140145 79.915)}}
    *{{box-sizing:border-box}}html,body{{max-width:100%;overflow-x:clip}}body{{min-width:0;margin:0;background:var(--bg-color);color:var(--text-color);font:400 16px/1.6 "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
    a{{color:var(--accent-color)}}a:focus-visible,summary:focus-visible{{outline:2px solid var(--accent-color);outline-offset:3px;border-radius:3px}}.page-shell{{width:min(100% - 2rem,68rem);margin:0 auto;padding:3rem 0 2rem;overflow-wrap:anywhere;word-break:break-word}}.page-header{{padding:0 0 2rem;border-bottom:1px solid var(--border-color);margin-bottom:2rem}}.site-kicker{{margin:0 0 .5rem;color:var(--accent-color);font:700 .75rem "JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono",monospace;letter-spacing:.08em;text-transform:uppercase}}h1,h2,h3{{color:var(--text-bright);line-height:1.3;text-wrap:balance}}h1{{margin:0;font:600 clamp(2rem,5vw,3.25rem)/1.2 "Newsreader",Georgia,serif;letter-spacing:-.02em}}.release-period{{margin:.75rem 0 0;color:var(--muted-color);font:.85rem "JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono",monospace}}.language-section{{margin:0 0 2.5rem}}.language-section>h2{{margin:0 0 1rem;font:700 1rem/1.4 "JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono",monospace;color:var(--muted-color);letter-spacing:.06em;text-transform:uppercase}}
    .log-item-card{{min-width:0;background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;padding:1.5rem;margin:0 0 1.25rem;transition:border-color .2s ease}}.log-item-card:hover{{border-color:var(--accent-color)}}.log-item-title{{margin:0 0 .75rem;font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:1.35rem;font-weight:650;letter-spacing:-.01em;line-height:1.4;text-wrap:pretty}}.log-prose-text{{margin:.5rem 0 0;font-size:.95rem;line-height:1.6;white-space:pre-line}}.log-prose-text:first-of-type{{margin-top:0}}code{{font:.9em "JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono",monospace;background:var(--code-bg);border-radius:4px;padding:.1em .35em;overflow-wrap:anywhere;word-break:break-word}}pre{{max-width:100%;margin:0;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word}}.log-code-block{{max-width:100%;margin:.75rem 0 0;padding:.75rem;overflow-x:auto;color:var(--text-color);background:var(--code-bg);border:1px solid var(--border-color);border-radius:6px;font:.85rem/1.5 "JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono",monospace}}.log-code-block code{{padding:0;background:transparent;font:inherit}}.log-analogy{{display:flex;gap:.55rem;align-items:flex-start;margin:.75rem 0;padding:.65rem .85rem;background:color-mix(in srgb,var(--accent-color) 8%,transparent);border-left:3px solid var(--accent-color);border-radius:0 6px 6px 0;font-size:.92rem;line-height:1.55}}.log-analogy-icon{{width:15px;height:15px;flex-shrink:0;margin-top:.15rem;color:var(--accent-color);fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}}.log-howto{{margin:0;border:1px solid var(--border-color);border-radius:6px;background:var(--bg-color)}}.original-entry{{margin:0 0 .6rem;background:var(--card-bg)}}.original-entry summary{{display:flex;flex-wrap:wrap;align-items:baseline;gap:.25rem .6rem;list-style:none}}.original-entry summary::-webkit-details-marker{{display:none}}.original-entry summary::before{{content:"▸";flex:0 0 auto;color:var(--accent-color);transition:transform .2s ease}}.original-entry[open] summary::before{{transform:rotate(90deg)}}.original-entry-title{{color:var(--text-bright);font:600 .85rem/1.4 "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}.log-howto summary{{padding:.65rem .85rem;cursor:pointer;color:var(--muted-color);font:.8rem "JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono",monospace}}.log-howto[open] summary{{border-bottom:1px solid var(--border-color);color:var(--text-bright)}}.log-howto .log-code-block{{margin:.75rem}}
    footer{{border-top:1px solid var(--border-color);padding-top:1.5rem}}footer nav{{display:flex;flex-wrap:wrap;gap:.75rem 1rem}}footer a{{font:.8rem "JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono",monospace}}@media(max-width:480px){{.page-shell{{width:min(100% - 1.5rem,68rem);padding-top:1.5rem}}.page-header{{padding-bottom:1.5rem;margin-bottom:1.5rem}}.language-section{{margin-bottom:2rem}}.log-item-card{{padding:1rem}}.log-item-title{{font-size:1.1rem}}.log-analogy{{padding:.5rem .65rem;font-size:.86rem}}.log-code-block{{padding:.65rem}}}}@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}}}
  </style>
  <script>try{{var t=localStorage.getItem("ai-updates-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
  <div class="page-shell"><header class="page-header"><p class="site-kicker">AI_UPDATES.LOG</p><h1>{escape(name)} {escape(version_name)}</h1><p class="release-period">發布日期：{escape(period)}</p></header><main>{language_sections}</main><footer><nav aria-label="版本導覽"><a href="{SITE_URL}#{tool_id}/{version_name}">回到互動版</a>{previous_link}{next_link}</nav></footer></div>
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
        "以繁體中文與英文提供 AI 工具更新紀錄的白話重寫。",
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
            llms_sections.append(f"- [{tool['name']} {version_name}]({url})")
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
            curated = next((v for v in tool["versions"] if _curated_items(v)), None)
            excerpt = ""
            if curated is not None:
                first = _curated_items(curated)[0]
                title = _strip_analogy_marks(_localized(first.get("title"), "zh-TW"))
                body = _strip_analogy_marks(_localized(first.get("body"), "zh-TW"))
                sentence = re.split(r"(?<=[。！？!?])|(?<=\.)\s+", body, maxsplit=1)[0]
                # 反引號是 Markdown 語法，摘要是給讀者與爬蟲讀的散文，不該原樣露出。
                title = title.replace("`", "")
                sentence = sentence.replace("`", "")
                # 摘要取自最新「已策展」的版本，未必是上面那個版號；相同時就不重複標。
                label = "摘要"
                if str(curated["version"]) != str(latest["version"]):
                    label = f'摘要（{escape(str(curated["version"]))}）'
                excerpt = (
                    f'<p>{label}：'
                    f'<strong>{escape(title)}</strong> {escape(sentence)}</p>'
                )
            links.append(
                f'<li><a href="{escape(_page_url(str(tool["id"]), str(latest["version"])), quote=True)}">'
                f'{escape(str(tool["name"]))} {escape(str(latest["version"]))}</a>{excerpt}</li>'
            )
    summary = "<!-- STATIC-SUMMARY:START -->\n  <noscript><section><h1>AI 工具更新速報</h1><p>最新版本：</p><ul>" + "".join(links) + "</ul></section></noscript>\n  <!-- STATIC-SUMMARY:END -->"
    if len(summary) > 2000:
        raise ValueError("STATIC-SUMMARY exceeds 2000 characters with curated excerpts")
    updated, count = re.subn(
        r"<!-- STATIC-SUMMARY:START -->.*?<!-- STATIC-SUMMARY:END -->", lambda _: summary, index, flags=re.DOTALL
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
