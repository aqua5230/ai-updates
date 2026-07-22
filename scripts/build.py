#!/usr/bin/env python3
"""Build compatibility and history feeds from raw and curated records."""

from __future__ import annotations

import json
import re
import shutil
from datetime import date
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
SITE_URL = "https://aqua5230.github.io/ai-updates/"
LANGUAGES = ("zh-TW", "en", "zh-CN", "ja", "ko")


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


def _description(version: dict[str, Any]) -> str:
    items = _curated_items(version)
    if items:
        first = items[0]
        return f"{_localized(first.get('title'), 'zh-TW')} {_localized(first.get('body'), 'zh-TW')}"[:150]
    raw = version.get("raw")
    entries = raw.get("entries", []) if isinstance(raw, dict) else []
    return " ".join(entry for entry in entries if isinstance(entry, str))[:150]


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


def _render_items(version: dict[str, Any], language: str) -> str:
    items = _curated_items(version)
    if items:
        blocks = []
        for item in items:
            title = _localized(item.get("title"), language)
            body = _localized(item.get("body"), language)
            original = item.get("original", "")
            if title or body:
                blocks.append(
                    f"<article><h3>{escape(title)}</h3>{_render_body(body)}"
                    f"<details><summary>Original changelog</summary><pre>{escape(str(original))}</pre></details></article>"
                )
        return "\n".join(blocks) or "<p>沒有可用的整理內容。</p>"

    raw = version.get("raw")
    entries = raw.get("entries", []) if isinstance(raw, dict) else []
    return "\n".join(f"<article><pre>{escape(entry)}</pre></article>" for entry in entries if isinstance(entry, str)) or "<p>沒有可用的原始更新內容。</p>"


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
        "datePublished": period,
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
            f'<section lang="{language}"><h2>{escape(language)}</h2>{_render_items(version, language)}</section>'
            for language in LANGUAGES
        )
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
            sitemap_entries.append(f"  <url><loc>{escape(url)}</loc><lastmod>{escape(period)}</lastmod></url>")
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


def build() -> None:
    generated_at = date.today().isoformat()
    app_tools: list[dict[str, Any]] = []
    history_tools: list[dict[str, Any]] = []
    daily_tools: list[dict[str, Any]] = []
    for tool_id, name in TOOLS:
        raw = _load_versions("raw", tool_id)
        curated = _load_versions("curated", tool_id)
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
    _write_static_pages(history_tools)
    _write_static_summary(history_tools)


if __name__ == "__main__":
    build()
