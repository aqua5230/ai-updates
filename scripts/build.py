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
# Google's rich results test rejects a SoftwareApplication without two of offers,
# aggregateRating, applicationCategory and operatingSystem; a third-party digest can
# only vouch for the last two. Sourced from each tool's changelog and README.
TOOL_OPERATING_SYSTEMS = {
    "claude_code": "macOS, Windows, Linux",
    "codex": "macOS, Windows, Linux",
    "agy": "macOS, Windows, Linux",
    "usage": "macOS, Windows",
    "gh_cli": "macOS, Windows, Linux",
}
# Single source of truth for build outputs; add new outputs only here.
BUILD_OUTPUTS = (
    "ai_updates.json",
    "daily.json",
    "docs/data.json",
    "docs/search-index.json",
    "docs/index.html",
    "docs/404.html",
    "docs/feed.xml",
    "docs/feed",
    "docs/sitemap.xml",
    "docs/robots.txt",
    "docs/llms.txt",
    "docs/history",
    "docs/v",
)
SITE_URL = "https://aqua5230.github.io/ai-updates/"
GOATCOUNTER_SCRIPT = (
    '<script data-goatcounter="https://lollapalooza.goatcounter.com/count" '
    'async src="//gc.zgo.at/count.js"></script>'
)
LANGUAGES = ("zh-TW", "en")
HISTORY_PAGE_SIZE = 10
ENTERPRISE_CARD_RE = re.compile(
    r"managed settings|managed polic|gateway|(?<!non-)enterprise|organization|"
    r"\badmin|identity provider|\bSSO\b|OTLP|^\[Claude Tag\]",
    re.IGNORECASE,
)
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


def _is_enterprise_card(item: dict[str, Any]) -> bool:
    lines = [line for line in item.get("original", "").splitlines() if line.strip()]
    matches = sum(bool(ENTERPRISE_CARD_RE.search(line)) for line in lines)
    return bool(lines) and matches * 5 >= len(lines) * 3


def _page_url(tool_id: str, version: str) -> str:
    return f"{SITE_URL}v/{tool_id}/{version}/"


def _localized(value: Any, language: str) -> str:
    return value.get(language, "") if isinstance(value, dict) else ""


def _curated_items(version: dict[str, Any]) -> list[dict[str, Any]]:
    curated = version.get("curated")
    if not isinstance(curated, dict):
        return []
    return [item for item in curated.get("items", []) if isinstance(item, dict)]


def _headline(version: dict[str, Any], language: str) -> str:
    items = _curated_items(version)
    if not items:
        return ""
    title = _strip_analogy_marks(_localized(items[0].get("title"), language)).replace("`", "")
    limit = 30 if language == "zh-TW" else 60
    if len(title) <= limit:
        return title
    if language == "zh-TW":
        cut = max((title.rfind(mark, 0, limit + 1) for mark in "，、：；"), default=-1)
        return title[:cut] if cut > 0 else title[:limit]
    cut = max(title.rfind(", ", 0, limit + 1), title.rfind(" ", 0, limit + 1))
    return title[:cut].rstrip(", ") if cut > 0 else title[:limit]


def _truncate_description(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    # Reserve one character for the ellipsis; prefer a complete sentence, then
    # punctuation or whitespace. Never cut an unbroken English word or URL.
    for pattern in (r"[。！？]|[.!?](?=\s|$)", r"[，、；：]|[,;:](?=\s|$)|\s+"):
        ends = [match.end() for match in re.finditer(pattern, text) if match.end() <= limit - 1]
        if ends:
            return text[:ends[-1]].rstrip() + "…"
    return "…"


def _description(
    version: dict[str, Any], language: str = "zh-TW", limit: int = 150
) -> str:
    items = _curated_items(version)
    if items:
        first = items[0]
        rest = _localized(first.get("body"), language)
        stop = SENTENCE_STOP.get(language, ".")
        # 只有一句很短的引子（例如「AI 人才市場迎來了一次大擴編。」）給不出資訊，
        # 補上下一句，直到夠長或碰到比喻框為止。
        floor = 50 if language == "zh-TW" else 100
        text = ""
        while rest and not rest.lstrip().startswith("⟦"):
            cut = _first_sentence_end(rest, stop)
            text += rest[: cut + 1] if cut != -1 else rest
            rest = rest[cut + 1 :] if cut != -1 else ""
            if len(_strip_analogy_marks(text).replace("`", "").strip()) >= floor:
                break
    else:
        raw = version.get("raw")
        entries = raw.get("entries", []) if isinstance(raw, dict) else []
        text = " ".join(entry for entry in entries if isinstance(entry, str))
    text = _strip_prose_only(_strip_analogy_marks(text))
    if items:
        text = text.replace("`", "")
    return _truncate_description(text, limit)


def _rss_pub_date(period: str) -> str:
    published = datetime.fromisoformat(_period_end_date(period)).replace(tzinfo=UTC)
    return format_datetime(published, usegmt=True)


def _write_rss_feed(history_tools: list[dict[str, Any]]) -> None:
    feed_root = ROOT / "docs" / "feed"
    shutil.rmtree(feed_root, ignore_errors=True)
    feed_root.mkdir(parents=True)
    tool_order = {tool_id: index for index, (tool_id, _) in enumerate(TOOLS)}
    all_entries = []
    for tool in history_tools:
        entries = []
        for version in tool.get("versions", []):
            period = str((version.get("curated") or version.get("raw") or {}).get("period", ""))
            entries.append((_period_end_date(period), tool, version, period))
        entries.sort(key=lambda entry: entry[0], reverse=True)
        all_entries.extend(entries)
        _write_feed(
            feed_root / f"{tool['id']}.xml",
            f"AI Updates · {tool['name']}",
            f"{SITE_URL}feed/{tool['id']}.xml",
            entries[:20],
        )
    all_entries.sort(
        key=lambda entry: (entry[0], -tool_order[str(entry[1]["id"])]), reverse=True
    )
    _write_feed(ROOT / "docs" / "feed.xml", "AI Updates", f"{SITE_URL}feed.xml", all_entries[:30])


def _write_feed(
    path: Path, title: str, url: str,
    entries: list[tuple[str, dict[str, Any], dict[str, Any], str]],
) -> None:
    rss = ET.Element("rss", {"version": "2.0", "xmlns:atom": "http://www.w3.org/2005/Atom"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = SITE_URL
    ET.SubElement(
        channel,
        "atom:link",
        {"href": url, "rel": "self", "type": "application/rss+xml"},
    )
    ET.SubElement(channel, "description").text = "Plain-language updates for AI developer tools."
    ET.SubElement(channel, "language").text = "en"

    if entries:
        ET.SubElement(channel, "lastBuildDate").text = _rss_pub_date(entries[0][3])

    for _, tool, version, period in entries:
        version_name = str(version["version"])
        url = _page_url(str(tool["id"]), version_name)
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"{tool['name']} {version_name}"
        ET.SubElement(item, "link").text = url
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = url
        ET.SubElement(item, "pubDate").text = _rss_pub_date(period)
        lead = _description(version, "en", 200).replace("`", "")
        curated_items = _curated_items(version)
        headline = (
            _strip_prose_only(_strip_analogy_marks(_localized(curated_items[0].get("title"), "en")))
            .replace("`", "")
            if curated_items else f"{tool['name']} {version_name}"
        )
        summary = f"{headline}: {lead}" if headline else lead
        ET.SubElement(item, "description").text = _truncate_description(summary, 200)

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


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
SENTENCE_STOP = {"zh-TW": "。", "zh-CN": "。", "ja": "。", "en": ".", "ko": "."}
BADGE_LABELS = {
    "zh-TW": {"new": "新功能", "fix": "問題修復", "perf": "效能優化"},
    "en": {"new": "FEATURE", "fix": "BUGFIX", "perf": "PERF"},
}

def _first_sentence_end(text: str, stop: str) -> int:
    in_code = False
    for index, character in enumerate(text):
        if character == "`":
            in_code = not in_code
            continue
        if not in_code and character == stop:
            return index
    return -1


def _split_analogy(text: str) -> tuple[str, str | None, str]:
    start = text.find("⟦")
    if start == -1:
        return text, None, ""
    end = text.find("⟧", start + 1)
    if end == -1:
        return text, None, ""
    return text[:start], text[start + 1 : end], text[end + 1 :]


def _render_plain_prose(text: str) -> str:
    return f'<p class="log-prose-text">{_render_inline_code(text)}</p>'


def _render_lead_prose(text: str, language: str) -> str:
    stop = SENTENCE_STOP.get(language, ".")
    cut = _first_sentence_end(text, stop)
    if cut != -1 and "```" in text[: cut + 1]:
        cut = -1
    if cut == -1:
        return _render_plain_prose(text)
    lead = f'<p class="log-lead-text">{_render_inline_code(text[: cut + 1])}</p>'
    rest = text[cut + 1 :].strip()
    return lead + (_render_plain_prose(rest) if rest else "")


def _render_prose_block(text: str, with_lead: bool, language: str) -> str:
    before, analogy, after = _split_analogy(text)
    blocks = []
    if before:
        blocks.append(_render_lead_prose(before, language) if with_lead else _render_plain_prose(before))
    if analogy:
        blocks.append(
            f'<aside class="log-analogy" role="note">'
            f"<span>{_render_inline_code(analogy.strip())}</span></aside>"
        )
    rest = after.strip() if after else ""
    if rest:
        blocks.append(
            _render_lead_prose(rest, language) if with_lead and not before else _render_plain_prose(rest)
        )
    return "".join(blocks)


def _badge_from_title(text: str) -> tuple[str, str]:
    lower = text.lower()
    if re.search(r"fix|bug|修|修復|修复|直|해결", lower):
        return "fix", "bugfix"
    if re.search(r"perf|效能|性能|省|優化|优化|改善|성능", lower):
        return "perf", "perf"
    return "new", "feature"


def _classify_entry(line: str) -> str:
    text = re.sub(r"^[*`\s]+", "", line.strip().lower())
    prefix = re.match(r"^(feat|fix|perf|chore|docs|refactor|build|ci|test|style)(\([^)]*\))?!?:", text)
    if prefix:
        return {"fix": "fix", "perf": "perf", "feat": "new"}.get(prefix.group(1), "?")
    if re.match(r"^(fixed|fixes|fix)\b", text):
        return "fix"
    if re.match(r"^(added|add|adds|introduced|introduces|new)\b", text):
        return "new"
    if re.match(r"^(improved|improves|optimiz|optimis)\w*\b", text):
        return "perf" if re.search(
            r"performance|faster|speed|latency|memory|startup|slow|jank|lag|cpu|throughput|responsive", text
        ) else "new"
    return "?"


def _badge_for(original: str, title: str) -> tuple[str, str]:
    kinds = {_classify_entry(line) for line in original.split("\n") if line.strip()}
    if len(kinds) == 1 and "?" not in kinds:
        kind = next(iter(kinds))
        if kind == "fix":
            return "fix", "bugfix"
        if kind == "perf":
            return "perf", "perf"
        return "new", "feature"
    return _badge_from_title(title or "")


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
                f'<aside class="log-analogy" role="note">'
                f"<span>{_render_inline_code(analogy)}</span></aside>"
            )
        cursor = match.end()
    prose = _strip_analogy_marks(text[cursor:])
    if prose:
        blocks.append(f'<p class="log-prose-text">{_render_inline_code(prose)}</p>')
    return "".join(blocks)


def _render_body(text: str, language: str = "zh-TW") -> str:
    blocks = []
    cursor = 0
    for match in FENCED_CODE_RE.finditer(text):
        prose = re.sub(r"\r?\n$", "", text[cursor:match.start()])
        if prose:
            blocks.append(_render_prose_block(prose, True, language))
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
        blocks.append(_render_prose_block(prose, True, language))
    return "".join(blocks)


def _render_items(
    version: dict[str, Any], language: str, *, include_original: bool = True,
    card_ids: bool = False,
) -> str:
    items = _curated_items(version)
    if items:
        blocks = []
        for number, item in enumerate(items, 1):
            title = _localized(item.get("title"), language)
            body = _localized(item.get("body"), language)
            if title or body:
                original_text = item.get("original")
                original_text = original_text if isinstance(original_text, str) else ""
                badge_type, _ = _badge_for(original_text, title)
                original = ""
                if include_original:
                    original = (
                        '<details class="log-howto"><summary>Original changelog</summary>'
                        f'<pre class="log-code-block" lang="en">{escape(str(item.get("original", "")))}</pre></details>'
                    )
                card_id = f' id="card-{number}"' if card_ids else ""
                blocks.append(
                    f'<article class="log-item-card tier-{badge_type}"{card_id}>'
                    '<div class="log-item-header">'
                    f'<span class="log-badge badge-{badge_type}">'
                    f"{escape(BADGE_LABELS[language][badge_type])}</span>"
                    f'<h3 class="log-item-title">{escape(title)}</h3></div>'
                    f"{_render_body(body, language)}{original}</article>"
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


def _render_originals(version: dict[str, Any], language: str = "zh-TW") -> str:
    # summary 逐則標上卡片標題：整段都寫「Original changelog」時，讀者分不出哪一則對應哪張卡。
    return "\n".join(
        '<details class="log-howto original-entry">'
        f'<summary>Original changelog<span class="original-entry-title">'
        f'{escape(_localized(item.get("title"), language))}</span></summary>'
        f'<pre class="log-code-block" lang="en">{escape(str(item.get("original", "")))}</pre>'
        "</details>"
        for item in _curated_items(version)
    )


PAGE_CSS = """\
  <style>
    @view-transition{navigation:auto}
    @font-face{font-family:"Inter";font-style:normal;font-weight:400 700;font-display:swap;src:url(__ASSETS__fonts/inter-latin-ext.woff2) format("woff2");unicode-range:U+100-2BA,U+2BD-2C5,U+2C7-2CC,U+2CE-2D7,U+2DD-2FF,U+304,U+308,U+329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
    @font-face{font-family:"Inter";font-style:normal;font-weight:400 700;font-display:swap;src:url(__ASSETS__fonts/inter-latin.woff2) format("woff2");unicode-range:U+0-FF,U+131,U+152-153,U+2BB-2BC,U+2C6,U+2DA,U+2DC,U+304,U+308,U+329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
    @font-face{font-family:"JetBrains Mono";font-style:normal;font-weight:400 700;font-display:swap;src:url(__ASSETS__fonts/jetbrains-mono-latin-ext.woff2) format("woff2");unicode-range:U+100-2BA,U+2BD-2C5,U+2C7-2CC,U+2CE-2D7,U+2DD-2FF,U+304,U+308,U+329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
    @font-face{font-family:"JetBrains Mono";font-style:normal;font-weight:400 700;font-display:swap;src:url(__ASSETS__fonts/jetbrains-mono-latin.woff2) format("woff2");unicode-range:U+0-FF,U+131,U+152-153,U+2BB-2BC,U+2C6,U+2DA,U+2DC,U+304,U+308,U+329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
    :root{--fs-2xs:.6875rem;--fs-xs:.75rem;--fs-sm:.8125rem;--fs-base:.9375rem;--fs-md:1rem;--fs-lg:1.125rem;--fs-xl:1.375rem;--control-sm:32px;--control-md:36px;--control-lg:44px;--bg-color:#0a2540;--sidebar-bg:#0a2540;--card-bg:#0f3056;--code-bg:#102e4e;--soft-surface:#173b62;--border-color:#31516f;--text-color:#bed0e4;--text-bright:#ffffff;--muted-color:#aac0d8;--accent-color:#2563eb;--accent-contrast:#ffffff;--accent-glow:#243f75;--link-color:#93c5fd;--tag-new:#85d9bc;--tag-fix:#ffa99e;--tag-perf:#f9cf82;--item-rule:rgb(255 255 255 / 10%);--chip-bg:#173b62;--analogy-text:#bed0e4;--analogy-start:oklch(0.51 0.16 255 / .22);--analogy-end:oklch(0.55 0.10 205 / .16);--analogy-border:rgb(255 255 255 / 12%);--badge-bg:rgb(255 255 255 / 6%);--glow-wash-1:rgb(34 211 238 / 27%);--glow-wash-2:rgb(56 140 255 / 29%);--glow-wash-3:rgb(99 102 241 / 38%);--glass-fill:rgb(10 37 64 / 69%);--glass-border:rgb(255 255 255 / 18%);--glass-shadow:0 12px 36px rgb(0 12 34 / 18%);--selected-gradient:linear-gradient(110deg,#2563eb,#0369a1);--serial-1:#50c7f1;--serial-2:#4dacf6;--serial-3:#6d9aff;--font-ui:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:dark}
    @media (prefers-color-scheme:light){

    :root{--bg-color:#ffffff;--sidebar-bg:#ffffff;--card-bg:#ffffff;--code-bg:#f6f9fc;--soft-surface:#f6f9fc;--border-color:#d8e3ee;--text-color:#425466;--text-bright:#061b31;--muted-color:#586a82;--accent-color:#2563eb;--accent-contrast:#ffffff;--accent-glow:#eff6ff;--link-color:#2156ca;--tag-new:#087a56;--tag-fix:#b13f43;--tag-perf:#925b08;--item-rule:#e5edf5;--chip-bg:#f6f9fc;--analogy-text:#425466;--analogy-start:oklch(0.77 0.11 255 / .16);--analogy-end:oklch(0.80 0.09 205 / .13);--analogy-border:#d8e3ee;--badge-bg:#ffffff;--glow-wash-1:rgb(34 211 238 / 17%);--glow-wash-2:rgb(56 140 255 / 15%);--glow-wash-3:rgb(99 102 241 / 18%);--glass-fill:rgb(255 255 255 / 70%);--glass-border:#d8e3ee;--glass-shadow:0 10px 28px rgb(10 37 64 / 8%);--selected-gradient:linear-gradient(110deg,#2563eb,#0369a1);--serial-1:#1575a2;--serial-2:#2563c9;--serial-3:#4158bc;--font-ui:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light}

    }
    :root[data-theme="light"]{--bg-color:#ffffff;--sidebar-bg:#ffffff;--card-bg:#ffffff;--code-bg:#f6f9fc;--soft-surface:#f6f9fc;--border-color:#d8e3ee;--text-color:#425466;--text-bright:#061b31;--muted-color:#586a82;--accent-color:#2563eb;--accent-contrast:#ffffff;--accent-glow:#eff6ff;--link-color:#2156ca;--tag-new:#087a56;--tag-fix:#b13f43;--tag-perf:#925b08;--item-rule:#e5edf5;--chip-bg:#f6f9fc;--analogy-text:#425466;--analogy-start:oklch(0.77 0.11 255 / .16);--analogy-end:oklch(0.80 0.09 205 / .13);--analogy-border:#d8e3ee;--badge-bg:#ffffff;--glow-wash-1:rgb(34 211 238 / 17%);--glow-wash-2:rgb(56 140 255 / 15%);--glow-wash-3:rgb(99 102 241 / 18%);--glass-fill:rgb(255 255 255 / 70%);--glass-border:#d8e3ee;--glass-shadow:0 10px 28px rgb(10 37 64 / 8%);--selected-gradient:linear-gradient(110deg,#2563eb,#0369a1);--serial-1:#1575a2;--serial-2:#2563c9;--serial-3:#4158bc;--font-ui:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light}
    :root[data-theme="dark"]{--bg-color:#0a2540;--sidebar-bg:#0a2540;--card-bg:#0f3056;--code-bg:#102e4e;--soft-surface:#173b62;--border-color:#31516f;--text-color:#bed0e4;--text-bright:#ffffff;--muted-color:#aac0d8;--accent-color:#2563eb;--accent-contrast:#ffffff;--accent-glow:#243f75;--link-color:#93c5fd;--tag-new:#85d9bc;--tag-fix:#ffa99e;--tag-perf:#f9cf82;--item-rule:rgb(255 255 255 / 10%);--chip-bg:#173b62;--analogy-text:#bed0e4;--analogy-start:oklch(0.51 0.16 255 / .22);--analogy-end:oklch(0.55 0.10 205 / .16);--analogy-border:rgb(255 255 255 / 12%);--badge-bg:rgb(255 255 255 / 6%);--glow-wash-1:rgb(34 211 238 / 27%);--glow-wash-2:rgb(56 140 255 / 29%);--glow-wash-3:rgb(99 102 241 / 38%);--glass-fill:rgb(10 37 64 / 69%);--glass-border:rgb(255 255 255 / 18%);--glass-shadow:0 12px 36px rgb(0 12 34 / 18%);--selected-gradient:linear-gradient(110deg,#2563eb,#0369a1);--serial-1:#50c7f1;--serial-2:#4dacf6;--serial-3:#6d9aff;--font-ui:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:dark}
    *{box-sizing:border-box}
    html,body{max-width:100%;overflow-x:clip}
    body{min-width:0;margin:0;background:var(--bg-color);color:var(--text-color);font:400 var(--fs-md)/1.6 "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;position:relative;isolation:isolate}
    body::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(ellipse 47vw 41vh at 64% 12%,var(--glow-wash-1),transparent 76%),radial-gradient(ellipse 48vw 48vh at 81% 20%,var(--glow-wash-2),transparent 76%),radial-gradient(ellipse 48vw 43vh at 98% 5%,var(--glow-wash-3),transparent 78%)}
    a{color:var(--link-color)}
    a:focus-visible,summary:focus-visible{outline:2px solid var(--accent-color);outline-offset:3px;border-radius:3px}
    .page-shell{width:min(100% - 2rem,46rem);margin:0 auto;padding:4rem 0 5rem;overflow-wrap:anywhere;word-break:break-word;position:relative;z-index:1}
    .page-header{padding:0 0 2rem;border-bottom:0;margin-bottom:2.5rem}
    .breadcrumb{margin:0 0 .5rem;font:500 var(--fs-xs)/1.5 "Inter",sans-serif;line-height:1.5}
    .breadcrumb ol{display:flex;flex-wrap:wrap;align-items:center;margin:0;padding:0;list-style:none}
    .breadcrumb li{display:flex;align-items:center;min-height:var(--control-sm);color:var(--muted-color)}
    .breadcrumb li+li::before{content:"/" / "";margin:0 .5rem}
    .breadcrumb a{display:inline-flex;align-items:center;min-height:var(--control-sm);color:var(--link-color);text-decoration:none}
    .breadcrumb a:hover{text-decoration:underline}
    h1,h2,h3{color:var(--text-bright);line-height:1.3;text-wrap:balance}
    h1{margin:0;font:500 var(--fs-xl)/1.3 "Inter",sans-serif;font-weight:300}
    .version-heading{font-size:clamp(2.75rem,5vw,4.5rem);line-height:1.05;font-weight:300}
    .release-period{margin:.75rem 0 0;color:var(--muted-color);font:400 var(--fs-xs)/1.5 "Inter",sans-serif;line-height:1.5}
    .language-section{margin:0 0 2.5rem}
    .language-section>h2{margin:0 0 1rem;font:500 var(--fs-lg)/1.5 "Inter",sans-serif;color:var(--muted-color)}
    .language-section:lang(en)>h2{letter-spacing:.06em}
    .log-item-card{min-width:0;background:var(--glass-fill);border:1px solid var(--glass-border);border-radius:20px;padding:2rem;margin:0 0 1.25rem;transition:box-shadow .2s ease;box-shadow:var(--glass-shadow);backdrop-filter:blur(20px) saturate(1.4);-webkit-backdrop-filter:blur(20px) saturate(1.4);animation:none}
    .log-item-card:hover{border-color:var(--glass-border);transform:none;box-shadow:var(--glass-shadow);background:var(--glass-fill)}
    .log-item-card.tier-fix{padding:2rem}
    .log-item-card.tier-fix .log-item-title{font-size:var(--fs-md)}
    .log-item-header{display:flex;align-items:baseline;gap:.45rem .75rem;margin-bottom:1rem;flex-wrap:wrap;flex-direction:row}
    .log-badge{display:inline-flex;align-items:center;gap:0;font:500 var(--fs-xs)/1.5 "Inter",sans-serif;padding:.18rem .65rem;border-radius:999px;border:1px solid currentColor;background:var(--badge-bg);color:var(--muted-color);margin-top:0;width:max-content;font-size:var(--fs-xs);font-weight:600}
    .log-badge.badge-new{color:var(--tag-new);font-weight:600;padding:.18rem .65rem;border:1px solid currentColor;border-radius:999px;background:var(--badge-bg);font-size:var(--fs-xs)}
    .log-badge.badge-fix{color:var(--tag-fix);font-weight:600;padding:.18rem .65rem;border:1px solid currentColor;border-radius:999px;background:var(--badge-bg);font-size:var(--fs-xs)}
    .log-badge.badge-perf{color:var(--tag-perf);font-weight:600;padding:.18rem .65rem;border:1px solid currentColor;border-radius:999px;background:var(--badge-bg);font-size:var(--fs-xs)}
    .badge-new{background:var(--badge-bg);color:var(--muted-color);border:1px solid currentColor}
    .badge-fix{background:var(--badge-bg);color:var(--muted-color);border:1px solid currentColor}
    .badge-perf{background:var(--badge-bg);color:var(--muted-color);border:1px solid currentColor}
    .log-item-title{margin:0;font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:var(--fs-xl);font-weight:600;line-height:1.4;text-wrap:pretty;flex-basis:100%}
    .log-item-title:lang(en){letter-spacing:normal}
    .log-lead-text{margin:0 0 .5rem;font:400 var(--fs-md)/1.7 "Inter",sans-serif;color:var(--text-color);white-space:pre-line;line-height:1.8}
    .log-prose-text{margin:.5rem 0 0;font-size:var(--fs-base);line-height:1.8;white-space:pre-line;color:var(--text-color)}
    .log-prose-text:first-of-type{margin-top:0;color:var(--text-color)}
    code{font:var(--fs-sm)/1.5 "JetBrains Mono",monospace;background:var(--code-bg);border-radius:4px;padding:.1em .35em;overflow-wrap:anywhere;word-break:break-word;line-height:1.5}
    pre{max-width:100%;margin:0;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word}
    .log-code-block{max-width:100%;margin:.75rem 0 0;padding:.75rem;overflow-x:auto;color:var(--text-color);background:var(--code-bg);border:0;border-radius:10px;font:var(--fs-sm)/1.5 "JetBrains Mono",monospace}
    .log-code-block code{padding:0;background:transparent;font:inherit}
    .log-analogy{display:flex;gap:.55rem;align-items:flex-start;border-left:0;border-radius:14px;padding:1rem 1.25rem;margin:1.5rem 0;font-size:var(--fs-base);line-height:1.8;color:var(--text-color);background:linear-gradient(120deg,var(--analogy-start),var(--analogy-end));border:1px solid var(--analogy-border)}
    .log-howto{margin:0;border:0;border-radius:6px;background:var(--soft-surface)}
    .original-entry{margin:0 0 .6rem;background:var(--code-bg);border:1px solid var(--border-color);border-radius:12px;overflow:hidden}
    .original-entry summary{display:flex;flex-wrap:wrap;align-items:baseline;gap:.25rem .6rem;list-style:none;padding:.65rem .85rem}
    .original-entry summary::-webkit-details-marker{display:none}
    .original-entry summary::before{content:"▸";flex:0 0 auto;color:var(--accent-color);transition:transform .2s ease}
    .original-entry[open] summary::before{transform:rotate(90deg)}
    .original-entry-title{color:var(--text-bright);font:500 var(--fs-sm)/1.6 "Inter",sans-serif}
    .log-howto summary{padding:.65rem .85rem;cursor:pointer;color:var(--muted-color);font:500 var(--fs-xs)/1.5 "Inter",sans-serif;line-height:1.5;min-height:var(--control-sm)}
    .log-howto[open] summary{border-bottom:1px solid var(--border-color);color:var(--text-bright)}
    .log-howto .log-code-block{margin:.75rem}
    footer{border-top:1px solid var(--border-color);padding-top:1.5rem}
    footer nav{display:flex;flex-wrap:wrap;gap:.75rem 1rem}
    footer a{font:var(--fs-sm)/1.5 "Inter",sans-serif;line-height:1.5}
    .back-to-top{position:fixed;right:calc(1rem + env(safe-area-inset-right));bottom:calc(1rem + env(safe-area-inset-bottom));z-index:20;display:grid;place-items:center;width:var(--control-lg);height:var(--control-lg);padding:0;border:1px solid var(--glass-border);border-radius:999px;background:var(--glass-fill);color:var(--text-bright);cursor:pointer;box-shadow:var(--glass-shadow);backdrop-filter:blur(20px) saturate(1.4);-webkit-backdrop-filter:blur(20px) saturate(1.4)}
    .back-to-top:hover,.back-to-top:focus-visible{background:color-mix(in srgb,var(--accent-color) 15%,var(--card-bg))}
    .back-to-top[hidden]{display:none}
    @media (max-width:1023px){

    .log-howto summary,.breadcrumb a,footer a{min-height:var(--control-lg)}
    .log-howto summary,footer a{display:flex;align-items:center}
    .log-item-card{backdrop-filter:none;-webkit-backdrop-filter:none}

    }
    @media (max-width:480px){

    .page-shell{width:min(100% - 1.5rem,46rem);padding:1.5rem 0 4rem}
    .page-header{padding-bottom:1.5rem;margin-bottom:2.5rem;border-bottom:0}
    .language-section{margin-bottom:2rem}
    .log-item-card{padding:1.3rem}
    .log-item-title{font-size:var(--fs-xl);font-weight:600;line-height:1.5;flex-basis:100%}
    .log-analogy{padding:1rem 1.25rem;font-size:var(--fs-base);border-left:0;border-radius:14px;background:linear-gradient(120deg,var(--analogy-start),var(--analogy-end));color:var(--analogy-text);margin:1.25rem 0;line-height:1.8;border:1px solid var(--analogy-border)}
    .log-code-block{padding:.65rem;font:var(--fs-sm)/1.5 "JetBrains Mono",monospace;border-radius:10px;border:0;background:var(--code-bg)}
    .back-to-top{right:calc(.75rem + env(safe-area-inset-right));bottom:calc(.75rem + env(safe-area-inset-bottom));border-radius:8px;color:var(--text-bright);border:1px solid var(--border-color)}
    .version-heading{font-size:clamp(3.5rem,12vw,4.5rem)}

    }
    @media (prefers-reduced-motion:reduce){

    @view-transition{navigation:none}
    ::view-transition-old(root),::view-transition-new(root){animation:none!important}
    .language-section .log-item-card{animation:none!important;opacity:1!important;translate:none!important}
    *,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}

    }
    @supports (animation-timeline:view()){

    @keyframes card-enter{from{translate:0 12px}
    to{translate:0 0}}
    .language-section .log-item-card{animation:card-enter linear both;animation-timeline:view();animation-range:entry 0% entry 35%}

    }
    .error-tools{margin-top:1.5rem}
    .error-actions{display:flex;flex-wrap:wrap;gap:.75rem;margin:1.5rem 0 0}
    .error-actions a{display:inline-flex;align-items:center;min-height:var(--control-lg);padding:.6rem 1rem;border-radius:999px;border:1px solid var(--border-color);text-decoration:none;background:var(--glass-fill);color:var(--text-bright)}
    .error-actions a:first-child{background:var(--selected-gradient);color:var(--accent-contrast);border-color:transparent}
    .error-tools p{margin:0 0 .5rem;color:var(--muted-color);font:600 var(--fs-xs)/1.5 var(--font-ui)}
    .error-tools ul{display:flex;flex-wrap:wrap;gap:.5rem 1rem;margin:0;padding:0;list-style:none}
    .error-tools a{font:500 var(--fs-sm)/1.5 var(--font-ui);display:inline-flex;align-items:center;min-height:var(--control-md);padding:.35rem .75rem;border:1px solid var(--border-color);border-radius:999px;text-decoration:none;background:var(--glass-fill)}
    .error-tools a:hover{background:var(--accent-glow);border-color:var(--accent-color)}
  </style>"""


def _render_static_page(
    tool: dict[str, Any], index: int, versions: list[dict[str, Any]],
    language: str = "zh-TW",
) -> str:
    version = versions[index]
    version_name = str(version["version"])
    tool_id = str(tool["id"])
    name = str(tool["name"])
    period = str((version.get("curated") or version.get("raw") or {}).get("period", ""))
    english = language == "en"
    description = _description(version, language)
    assets = "../../../../" if english else "../../../"
    page_css = PAGE_CSS.replace("__ASSETS__", assets)
    release_notes = []
    items = _curated_items(version)
    if items:
        release_notes = [
            _localized(item.get("title"), language)
            for item in items
            if _localized(item.get("title"), language)
        ]
    if english:
        title = f"{name} {version_name}: {_headline(version, 'en')}"
        suffixed = f"{title} | Plain-language release notes"
        if len(suffixed) <= 70:
            title = suffixed
    else:
        title = f"{name} {version_name} 更新白話速報"
    if items and not english:
        headline = _headline(version, "zh-TW")
        if headline:
            title = f"{name} {version_name}：{headline}｜更新白話速報"
            if len(title) > 60:
                title = f"{name} {version_name}：{headline}"
    zh_url = _page_url(tool_id, version_name)
    en_url = f"{zh_url}en/"
    url = en_url if english else zh_url
    alternate_links = ""
    language_link = ""
    if items:
        alternate_links = (
            f'  <link rel="alternate" hreflang="zh-TW" href="{escape(zh_url, quote=True)}">\n'
            f'  <link rel="alternate" hreflang="en" href="{escape(en_url, quote=True)}">\n'
            f'  <link rel="alternate" hreflang="x-default" href="{escape(zh_url, quote=True)}">\n'
        )
        language_link = (
            f'<a href="{escape(zh_url, quote=True)}" hreflang="zh-TW" lang="zh-TW">繁體中文</a>'
            if english else
            f'<a href="{escape(en_url, quote=True)}" hreflang="en" lang="en">English</a>'
        )
    site = {"@type": "Organization", "name": "AI Updates", "url": SITE_URL}
    structured_data = [
        {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": title,
            "datePublished": _period_end_date(period),
            "description": description,
            "inLanguage": "en" if english else (list(LANGUAGES) if items else ["en"]),
            "url": url,
            "image": f"{SITE_URL}og-image.png",
            "author": site,
            "publisher": site,
            "about": {
                "@type": "SoftwareApplication",
                "name": name,
                "applicationCategory": "DeveloperApplication",
                "operatingSystem": TOOL_OPERATING_SYSTEMS[tool_id],
                "softwareVersion": version_name,
                "releaseNotes": ("; " if english else "；").join(release_notes),
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "AI Updates", "item": SITE_URL},
                {"@type": "ListItem", "position": 2, "name": name, "item": f"{SITE_URL}#{tool_id}"},
                {"@type": "ListItem", "position": 3, "name": version_name},
            ],
        },
    ]
    json_ld = json.dumps(structured_data, ensure_ascii=False).replace("</", "<\\/")
    def neighbor_link(neighbor_index: int, label: str) -> str:
        if not 0 <= neighbor_index < len(versions):
            return ""
        neighbor = versions[neighbor_index]
        if english and not _curated_items(neighbor):
            return ""
        neighbor_url = _page_url(tool_id, str(neighbor["version"]))
        if english:
            neighbor_url += "en/"
        return f'<a href="{escape(neighbor_url, quote=True)}">{label}</a>'

    previous_link = neighbor_link(index + 1, "Previous version" if english else "上一版")
    next_link = neighbor_link(index - 1, "Next version" if english else "下一版")
    if english:
        language_sections = (
            '<section class="language-section" lang="en"><h2>Release notes</h2>'
            f'{_render_items(version, "en", include_original=False, card_ids=True)}</section>'
            '<section class="language-section"><h2>Original changelog</h2>'
            f'{_render_originals(version, "en")}</section>'
        )
    elif items:
        language_sections = "\n".join(
            f'<section class="language-section" lang="{language}">'
            f'<h2>{"繁體中文" if language == "zh-TW" else "English"}</h2>'
            f'{_render_items(version, language, include_original=False, card_ids=language == "zh-TW")}</section>'
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
    return f'''<!doctype html>
<html lang="{language}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description, quote=True)}">
  <link rel="canonical" href="{escape(url, quote=True)}">
{alternate_links}  <meta name="robots" content="max-image-preview:large">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="AI Updates">
  <meta property="og:locale" content="{'en_US' if english else 'zh_TW'}">
  <meta property="og:locale:alternate" content="{'zh_TW' if english else 'en_US'}">
  <meta property="og:title" content="{escape(title, quote=True)}">
  <meta property="og:description" content="{escape(description, quote=True)}">
  <meta property="og:url" content="{escape(url, quote=True)}">
  <meta property="og:image" content="{SITE_URL}og-image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{'AI Updates: Plain-language AI tool release notes for Claude Code, Codex, Antigravity, Usage, and GitHub CLI' if english else 'AI Updates：AI 工具更新速報，追蹤 Claude Code、Codex、Antigravity、Usage、GitHub CLI 官方更新'}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(title, quote=True)}">
  <meta name="twitter:description" content="{escape(description, quote=True)}">
  <meta name="twitter:image" content="{SITE_URL}og-image.png">
  <meta name="twitter:image:alt" content="{'AI Updates: Plain-language AI tool release notes for Claude Code, Codex, Antigravity, Usage, and GitHub CLI' if english else 'AI Updates：AI 工具更新速報，追蹤 Claude Code、Codex、Antigravity、Usage、GitHub CLI 官方更新'}">
  <link rel="icon" href="{assets}favicon.svg" type="image/svg+xml">
  <link rel="preload" href="{assets}fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="{assets}fonts/jetbrains-mono-latin.woff2" as="font" type="font/woff2" crossorigin>
  <script type="application/ld+json">{json_ld}</script>
{page_css}
  <script>try{{var t=localStorage.getItem("ai-updates-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}}catch(e){{}}</script>
  {GOATCOUNTER_SCRIPT}
</head>
<body>
  <div class="page-shell"><header class="page-header"><nav class="breadcrumb" aria-label="{'Page path' if english else '頁面路徑'}"><ol><li><a href="{SITE_URL}">AI Updates</a></li><li><a href="{SITE_URL}#{tool_id}">{escape(name)}</a></li><li aria-current="page">{escape(version_name)}</li></ol></nav><h1 class="version-heading">{escape(name)} {escape(version_name)}</h1><p class="release-period">{'Released: ' if english else '發布日期：'}{escape(period)}</p></header><main>{language_sections}</main><footer><nav aria-label="{'Version navigation' if english else '版本導覽'}"><a href="{SITE_URL}#{tool_id}/{version_name}">{'Back to interactive view' if english else '回到互動版'}</a>{previous_link}{next_link}{language_link}</nav></footer></div><button class="back-to-top" id="back-to-top" type="button" aria-label="{'Back to top' if english else '回到頂端'}" title="{'Back to top' if english else '回到頂端'}" hidden><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button>
  <script>const backToTop=document.getElementById("back-to-top"),reducedMotion=matchMedia("(prefers-reduced-motion: reduce)");function updateBackToTop(){{backToTop.hidden=scrollY<=innerHeight*2}}addEventListener("scroll",updateBackToTop,{{passive:true}});updateBackToTop();backToTop.addEventListener("click",()=>scrollTo({{top:0,behavior:reducedMotion.matches?"auto":"smooth"}}));</script>
</body>
</html>
'''


def _write_not_found_page() -> None:
    """GitHub Pages 對不存在的網址回傳這一頁；版本號打錯時不會掉到平台的通用 404。"""
    page_css = PAGE_CSS.replace("__ASSETS__", SITE_URL)
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>找不到頁面 · AI 工具更新速報</title>
  <meta name="description" content="這個網址不存在或已經失效。回到 AI 工具更新速報首頁，查看五個工具的最新版本與歷史紀錄。">
  <meta name="robots" content="noindex, follow">
  <link rel="icon" href="{SITE_URL}favicon.svg" type="image/svg+xml">
  <link rel="alternate" type="application/rss+xml" title="AI Updates" href="{SITE_URL}feed.xml">
  <link rel="preload" href="{SITE_URL}fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="{SITE_URL}fonts/jetbrains-mono-latin.woff2" as="font" type="font/woff2" crossorigin>
{page_css}
  <script>try{{var t=localStorage.getItem("ai-updates-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}}catch(e){{}}</script>
  {GOATCOUNTER_SCRIPT}
</head>
<body>
  <div class="page-shell"><header class="page-header"><nav class="breadcrumb" aria-label="頁面路徑"><ol><li><a href="{SITE_URL}">AI Updates</a></li><li aria-current="page">404</li></ol></nav><h1 class="version-heading">404</h1><p class="release-period">找不到這個頁面 · Page not found</p></header><main><div class="log-item-card"><p class="log-prose-text">這個網址不存在，或是版本號打錯了。首頁列出五個工具的最新版本，每個工具都能往回翻完整的歷史紀錄。</p><p class="log-prose-text" lang="en">This page does not exist. The home page lists the latest release for all five tools, each with its full version history.</p><nav class="error-tools" aria-label="工具導覽"><p>工具導覽</p><ul><li><a href="{SITE_URL}#claude_code">Claude Code</a></li><li><a href="{SITE_URL}#codex">Codex</a></li><li><a href="{SITE_URL}#agy">Antigravity</a></li><li><a href="{SITE_URL}#usage">Usage</a></li><li><a href="{SITE_URL}#gh_cli">GitHub CLI</a></li></ul></nav><div class="error-actions"><a href="{SITE_URL}">回到首頁</a><a href="{SITE_URL}feed.xml">訂閱 RSS</a></div></div></main></div>
</body>
</html>
"""
    (ROOT / "docs" / "404.html").write_text(html, encoding="utf-8")


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
            llms_line = f"- [{tool['name']} {version_name}]({url})"
            if _curated_items(version):
                en_path = path.parent / "en" / "index.html"
                en_path.parent.mkdir(parents=True, exist_ok=True)
                en_path.write_text(_render_static_page(tool, index, versions, "en"), encoding="utf-8")
                en_url = f"{url}en/"
                sitemap_entries.append(
                    f"  <url><loc>{escape(en_url)}</loc><lastmod>{escape(lastmod)}</lastmod></url>"
                )
                llms_line += f" · [English]({en_url})"
                page_count += 1
            llms_sections.append(llms_line)
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
    search_cards: list[list[Any]] = []
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
        for version in history_tool["versions"]:
            if not version["curated"]:
                continue
            for number, item in enumerate(version["curated"]["items"], 1):
                snippets = re.findall(
                    r"(?<!`)`([^`\n]+)`(?!`)",
                    " ".join((item["body"]["zh-TW"], item["body"]["en"], item["original"])),
                )
                keywords = " ".join(dict.fromkeys(text for text in snippets if len(text) <= 40))
                search_cards.append([
                    tool_id, version["version"], number,
                    item["title"]["zh-TW"], item["title"]["en"], keywords,
                ])
        latest = next(
            (version for version in history_tool["versions"] if version["curated"]),
            history_tool["versions"][0] if history_tool["versions"] else None,
        )
        site_versions = []
        for version in history_tool["versions"]:
            summary = {
                "version": version["version"],
                "period": (version["curated"] or version["raw"] or {}).get("period", ""),
            }
            if version["curated"]:
                enterprise = [
                    number for number, item in enumerate(version["curated"]["items"], 1)
                    if _is_enterprise_card(item)
                ]
                if enterprise:
                    summary["enterprise"] = enterprise
            site_versions.append(summary)
        site_tools.append(
            {
                "id": tool_id,
                "name": name,
                "latest": latest,
                "versions": site_versions,
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
    _write(
        ROOT / "docs" / "data.json",
        {"generated_at": generated_at, "history_page_size": HISTORY_PAGE_SIZE, "tools": site_tools},
    )
    search_path = ROOT / "docs" / "search-index.json"
    search_path.write_text(
        json.dumps(
            {"generated_at": generated_at, "cards": search_cards},
            ensure_ascii=False, separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    history_root = ROOT / "docs" / "history"
    if history_root.exists():
        shutil.rmtree(history_root)
    history_root.mkdir(parents=True)
    for history_tool in history_tools:
        versions = history_tool["versions"]
        pages = (len(versions) + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE
        for index in range(pages):
            page = index + 1
            _write(
                history_root / history_tool["id"] / f"{page}.json",
                {
                    "id": history_tool["id"],
                    "name": history_tool["name"],
                    "page": page,
                    "pages": pages,
                    "versions": versions[index * HISTORY_PAGE_SIZE:page * HISTORY_PAGE_SIZE],
                },
            )
    _write(ROOT / "daily.json", {"generated_at": generated_at, "tools": daily_tools})
    _write_static_pages(history_tools)
    _write_not_found_page()
    _write_static_summary(history_tools)


if __name__ == "__main__":
    build()
