#!/usr/bin/env python3
"""Fetch official changelogs and store immutable per-version raw records."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw"
USER_AGENT = "aqua5230/ai-updates"
CLAUDE_CHANGELOG_URL = (
    "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
)
CLAUDE_RELEASES_URL = "https://api.github.com/repos/anthropics/claude-code/releases"
CODEX_RELEASES_URL = "https://api.github.com/repos/openai/codex/releases"
AGY_CHANGELOG_URL = (
    "https://raw.githubusercontent.com/google-antigravity/antigravity-cli/"
    "main/CHANGELOG.md"
)
VERSION_HEADING = re.compile(r"^##\s+\[?[vV]?([^\]\s]+)\]?(?:\s|$)")


def _request(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def fetch_text(url: str) -> str:
    return _request(url).decode("utf-8")


def fetch_json(url: str) -> Any:
    return json.loads(_request(url))


def parse_markdown_changelog(text: str) -> list[tuple[str, list[str]]]:
    """Parse level-two version headings and preserve top-level bullet text."""
    versions: list[tuple[str, list[str]]] = []
    version: str | None = None
    entries: list[str] = []
    current: list[str] | None = None

    def finish_entry() -> None:
        nonlocal current
        if current:
            entries.append("\n".join(current).strip())
        current = None

    def finish_version() -> None:
        finish_entry()
        if version and entries:
            versions.append((version, entries.copy()))
        entries.clear()

    for line in text.splitlines():
        match = VERSION_HEADING.match(line)
        if match:
            finish_version()
            version = match.group(1).rstrip(":")
            continue
        if version is None:
            continue
        if line.startswith(("- ", "* ")):
            finish_entry()
            current = [line[2:].strip()]
        elif current is not None and (line.startswith("  ") or not line.strip()):
            if line.strip():
                current.append(line.strip())
        elif line.startswith("## "):
            finish_version()
            version = None
    finish_version()
    return versions


def parse_github_releases(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("GitHub releases response is not a list")
    releases: list[dict[str, Any]] = []
    for release in payload:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        tag = release.get("tag_name")
        body = release.get("body")
        published_at = release.get("published_at")
        html_url = release.get("html_url")
        if not all(isinstance(value, str) for value in (tag, body, published_at, html_url)):
            continue
        entries = _release_body_entries(body)
        if entries:
            releases.append(
                {
                    "version": tag.removeprefix("rust-v").removeprefix("v"),
                    "period": published_at[:10],
                    "source_url": html_url,
                    "entries": entries,
                }
            )
    return releases


def _release_body_entries(body: str) -> list[str]:
    entries: list[str] = []
    current: list[str] | None = None
    for line in body.splitlines():
        if line.startswith(("- ", "* ")):
            if current:
                entries.append("\n".join(current).strip())
            current = [line[2:].strip()]
        elif current is not None and line.startswith("  "):
            current.append(line.strip())
    if current:
        entries.append("\n".join(current).strip())
    if entries:
        return entries
    stripped = body.strip()
    return [stripped] if stripped else []


def _release_dates(url: str) -> dict[str, str]:
    payload = fetch_json(f"{url}?per_page=100")
    if not isinstance(payload, list):
        raise ValueError("GitHub releases response is not a list")
    dates: dict[str, str] = {}
    for release in payload:
        if not isinstance(release, dict):
            continue
        tag = release.get("tag_name")
        published = release.get("published_at")
        if isinstance(tag, str) and isinstance(published, str):
            dates[tag.removeprefix("v")] = published[:10]
    return dates


def _write_raw(tool_id: str, record: dict[str, Any]) -> bool:
    path = RAW_ROOT / tool_id / f"{record['version']}.json"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"NEW {tool_id} {record['version']}")
    return True


def _markdown_records(
    text: str, source_url: str, dates: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    today = date.today().isoformat()
    return [
        {
            "version": version,
            "period": (dates or {}).get(version, today),
            "source_url": source_url,
            "fetched_at": today,
            "entries": entries,
        }
        for version, entries in parse_markdown_changelog(text)
    ]


def fetch_claude(days: int = 30) -> int:
    dates = _release_dates(CLAUDE_RELEASES_URL)
    cutoff = date.today() - timedelta(days=days)
    records = _markdown_records(fetch_text(CLAUDE_CHANGELOG_URL), CLAUDE_CHANGELOG_URL, dates)
    dated = [record for record in records if record["version"] in dates]
    selected = [
        record for record in dated if date.fromisoformat(record["period"]) >= cutoff
    ]
    if not selected:
        raise ValueError("Claude changelog versions could not be matched to release dates")
    return sum(_write_raw("claude_code", record) for record in selected)


def fetch_codex(days: int = 30) -> int:
    cutoff = date.today() - timedelta(days=days)
    records: list[dict[str, Any]] = []
    for page in range(1, 11):
        payload = fetch_json(f"{CODEX_RELEASES_URL}?per_page=100&page={page}")
        page_records = parse_github_releases(payload)
        records.extend(page_records)
        page_is_old = page_records and (
            date.fromisoformat(page_records[-1]["period"]) < cutoff
        )
        if not payload or page_is_old:
            break
    selected = [record for record in records if date.fromisoformat(record["period"]) >= cutoff]
    if not selected:
        raise ValueError("Codex releases contained no versions from the last 30 days")
    fetched_at = datetime.now(UTC).date().isoformat()
    for record in selected:
        record["fetched_at"] = fetched_at
    return sum(_write_raw("codex", record) for record in selected)


def fetch_agy() -> int:
    records = _markdown_records(fetch_text(AGY_CHANGELOG_URL), AGY_CHANGELOG_URL)
    if not records:
        raise ValueError("Antigravity changelog contained no versions")
    return sum(_write_raw("agy", record) for record in records)


def main() -> int:
    try:
        fetch_claude()
        fetch_codex()
        fetch_agy()
    except (
        OSError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
        urllib.error.URLError,
    ) as exc:
        print(f"fetch failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
