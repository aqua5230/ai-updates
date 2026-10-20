#!/usr/bin/env python3
"""Fetch official changelogs and store immutable per-version raw records."""

from __future__ import annotations

import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw"
USER_AGENT = "aqua5230/ai-updates"
MAX_ATTEMPTS = 3
BACKOFF_BASE = 1.0
GITHUB_API_PREFIX = "https://api.github.com/"
CLAUDE_CHANGELOG_URL = (
    "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
)
CLAUDE_RELEASES_URL = "https://api.github.com/repos/anthropics/claude-code/releases"
CODEX_RELEASES_URL = "https://api.github.com/repos/openai/codex/releases"
GH_CLI_RELEASES_URL = "https://api.github.com/repos/cli/cli/releases"
AGY_CHANGELOG_URL = (
    "https://raw.githubusercontent.com/google-antigravity/antigravity-cli/"
    "main/CHANGELOG.md"
)
USAGE_CHANGELOG_URL = "https://raw.githubusercontent.com/aqua5230/usage/main/CHANGELOG.md"
GROK_CHANGELOG_URL = "https://x.ai/changelog/build"
# x.ai 直接抓會回 403，改經 Jina Reader 轉成 Markdown 再解析。
GROK_READER_URL = f"https://r.jina.ai/{GROK_CHANGELOG_URL}"
MUSE_CHANGELOG_URL = "https://dev.meta.ai/docs/muse-code/changelog"
MUSE_VERSION = re.compile(r"^\d+(\.\d+)+$")
VERSION_HEADING = re.compile(r"^##\s+\[?[vV]?([^\]\s]+)\]?(?:\s|$)")
KEEPACHANGELOG_HEADING = re.compile(
    r"^##\s+\[([^\]]+)\]\s*-\s*(\d{4}-\d{2}-\d{2})\s*$"
)
GROK_HEADING = re.compile(r"^##\s+Grok Build\s+(\S+)\s*$")
GROK_DATE_LINE = re.compile(
    r"^((?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r" \d{1,2}, \d{4})\b"
)
VERSION_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RELEASE_BODY_STOP_HEADINGS = {
    "## changelog",
    "## what's changed",
    "## new contributors",
}
_last_request_url: str | None = None


def _request(
    url: str,
    *,
    attempts: int = MAX_ATTEMPTS,
    backoff: float = BACKOFF_BASE,
    sleep: Any = time.sleep,
) -> bytes:
    global _last_request_url
    _last_request_url = url
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if url.startswith(GITHUB_API_PREFIX) and (token := os.environ.get("GITHUB_TOKEN")):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        headers=headers,
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as err:
            if err.code not in {429, 500, 502, 503, 504} or attempt == attempts:
                raise
        except urllib.error.URLError:
            if attempt == attempts:
                raise
        except (TimeoutError, ConnectionError):
            if attempt == attempts:
                raise
        except http.client.IncompleteRead:
            # 大回應（codex releases 單頁約 27MB）被中途截斷時丟這個例外，它不是
            # URLError／ConnectionError 的子類，不列在這裡就不會重試，每日排程
            # 因此連紅四次（2026-09-10 查 GitHub Action 歷史）。
            if attempt == attempts:
                raise
        sleep(backoff * (2 ** (attempt - 1)))
    raise RuntimeError("unreachable")


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


def parse_keepachangelog(text: str) -> list[tuple[str, str, list[str]]]:
    """Parse Keep a Changelog version headings, dates, and bullet text."""
    versions: list[tuple[str, str, list[str]]] = []
    version: str | None = None
    period: str | None = None
    entries: list[str] = []
    current: list[str] | None = None

    def finish_entry() -> None:
        nonlocal current
        if current:
            entries.append("\n".join(current).strip())
        current = None

    def finish_version() -> None:
        finish_entry()
        if version and period and entries:
            versions.append((version, period, entries.copy()))
        entries.clear()

    for line in text.splitlines():
        match = KEEPACHANGELOG_HEADING.match(line)
        if match:
            finish_version()
            version, period = match.groups()
            continue
        if line.startswith("## "):
            finish_version()
            version = None
            period = None
            continue
        if version is None:
            continue
        if line.startswith(("- ", "* ")):
            finish_entry()
            current = [line[2:].strip()]
        elif current is not None and (line.startswith("  ") or not line.strip()):
            if line.strip():
                current.append(line.strip())
    finish_version()
    return versions


def parse_grok_changelog(text: str) -> list[tuple[str, str, list[str]]]:
    """Parse the Grok Build changelog page; each heading follows its own date line."""
    versions: list[tuple[str, str, list[str]]] = []
    version: str | None = None
    period: str | None = None
    last_date: str | None = None
    entries: list[str] = []

    def finish_version() -> None:
        if version and period and entries:
            versions.append((version, period, entries.copy()))
        entries.clear()

    for line in text.splitlines():
        if match := GROK_DATE_LINE.match(line):
            last_date = datetime.strptime(match.group(1), "%B %d, %Y").date().isoformat()
        elif match := GROK_HEADING.match(line):
            finish_version()
            version, period = match.group(1), last_date
        elif version and line.startswith(("- ", "* ")):
            entries.append(line[2:].strip())
    finish_version()
    return versions


class _MuseChangelogParser(HTMLParser):
    """Read only the official docs article, excluding navigation and the outline."""

    def __init__(self) -> None:
        super().__init__()
        self.versions: list[tuple[str, list[str]]] = []
        self.in_article = False
        self.heading: list[str] | None = None
        self.version: str | None = None
        self.entries: list[str] = []
        self.entry: list[str] | None = None

    def _finish_version(self) -> None:
        if self.version is not None:
            self.versions.append((self.version, self.entries))
        self.version = None
        self.entries = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "article" and dict(attrs).get("data-docs-article") == "true":
            self.in_article = True
        if not self.in_article:
            return
        if tag == "h2":
            self._finish_version()
            self.heading = []
        elif tag == "li" and self.version is not None:
            self.entry = []
        elif tag == "code" and self.entry is not None:
            self.entry.append("`")
        elif tag == "br" and self.entry is not None:
            self.entry.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if not self.in_article:
            return
        if tag == "h2" and self.heading is not None:
            heading = " ".join("".join(self.heading).split())
            self.version = heading if MUSE_VERSION.fullmatch(heading) else None
            self.heading = None
        elif tag == "code" and self.entry is not None:
            self.entry.append("`")
        elif tag == "li" and self.entry is not None:
            self.entries.append(" ".join("".join(self.entry).split()))
            self.entry = None
        elif tag == "article":
            self._finish_version()
            self.in_article = False

    def handle_data(self, data: str) -> None:
        if not self.in_article:
            return
        if self.heading is not None:
            self.heading.append(data)
        elif self.entry is not None:
            self.entry.append(data)


def parse_muse_changelog(text: str) -> list[tuple[str, list[str]]]:
    parser = _MuseChangelogParser()
    parser.feed(text)
    parser.close()
    return parser.versions


_RELEASE_TAG_PREFIX = re.compile(r"^(?:rust-v|v)")


def _normalize_release_tag(tag: str) -> str | None:
    """Strip a known version prefix and return None for non-version tags.

    GitHub releases sometimes carry unrelated one-off tags (asset drops,
    other release tracks) that happen to start with "v"; a bare
    removeprefix("v") mangles those into garbage instead of skipping them.
    """
    version = _RELEASE_TAG_PREFIX.sub("", tag, count=1)
    if not version or not version[0].isdigit():
        return None
    return version


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
        version = _normalize_release_tag(tag)
        if version is None:
            continue
        entries = _release_body_entries(body)
        if entries:
            releases.append(
                {
                    "version": version,
                    "period": published_at[:10],
                    "source_url": html_url,
                    "entries": entries,
                }
            )
    return releases


def _release_body_entries(body: str) -> list[str]:
    lines: list[str] = []
    for line in body.splitlines():
        if line.strip().lower() in RELEASE_BODY_STOP_HEADINGS:
            break
        lines.append(line)
    body = "\n".join(lines)

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
    version = record["version"]
    if (
        not isinstance(version, str)
        or not VERSION_COMPONENT.fullmatch(version)
        or version in {".", ".."}
        or ".." in version
    ):
        raise ValueError(f"invalid version for {tool_id}: {version!r}")
    path = RAW_ROOT / tool_id / f"{version}.json"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"NEW {tool_id} {version}")
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


def fetch_claude(count: int = 20) -> int:
    dates = _release_dates(CLAUDE_RELEASES_URL)
    records = _markdown_records(fetch_text(CLAUDE_CHANGELOG_URL), CLAUDE_CHANGELOG_URL, dates)
    selected = [record for record in records if record["version"] in dates][:count]
    if not selected:
        raise ValueError("Claude changelog versions could not be matched to release dates")
    return sum(_write_raw("claude_code", record) for record in selected)


def fetch_codex(count: int = 20) -> int:
    records: list[dict[str, Any]] = []
    for page in range(1, 11):
        # 單頁 100 筆約 31MB，下載中斷機率高；只需要 count 筆就只拉 count 筆。
        payload = fetch_json(f"{CODEX_RELEASES_URL}?per_page={min(count, 100)}&page={page}")
        records.extend(parse_github_releases(payload))
        if not payload or len(records) >= count:
            break
    selected = records[:count]
    if not selected:
        raise ValueError("Codex releases contained no versions")
    fetched_at = datetime.now(UTC).date().isoformat()
    for record in selected:
        record["fetched_at"] = fetched_at
    return sum(_write_raw("codex", record) for record in selected)


def fetch_agy() -> int:
    records = _markdown_records(fetch_text(AGY_CHANGELOG_URL), AGY_CHANGELOG_URL)
    if not records:
        raise ValueError("Antigravity changelog contained no versions")
    return sum(_write_raw("agy", record) for record in records)


def fetch_usage(count: int = 20) -> int:
    today = date.today().isoformat()
    records = [
        {
            "version": version,
            "period": period,
            "source_url": USAGE_CHANGELOG_URL,
            "fetched_at": today,
            "entries": entries,
        }
        for version, period, entries in parse_keepachangelog(fetch_text(USAGE_CHANGELOG_URL))
    ]
    selected = records[:count]
    if not selected:
        raise ValueError("Usage changelog contained no versions")
    return sum(_write_raw("usage", record) for record in selected)


def fetch_gh_cli(count: int = 20) -> int:
    records: list[dict[str, Any]] = []
    for page in range(1, 11):
        payload = fetch_json(f"{GH_CLI_RELEASES_URL}?per_page=100&page={page}")
        records.extend(parse_github_releases(payload))
        if not payload or len(records) >= count:
            break
    selected = records[:count]
    if not selected:
        raise ValueError("GitHub CLI releases contained no versions")
    fetched_at = datetime.now(UTC).date().isoformat()
    for record in selected:
        record["fetched_at"] = fetched_at
    return sum(_write_raw("gh_cli", record) for record in selected)


def fetch_grok_build(count: int = 15) -> int:
    # Grok 幾乎一天一版；原本只抓 5 版，10/15～10/19 的空窗漏掉 1.0.53～1.0.57，改抓 15 版。
    today = date.today().isoformat()
    records = [
        {
            "version": version,
            "period": period,
            "source_url": GROK_CHANGELOG_URL,
            "fetched_at": today,
            "entries": entries,
        }
        for version, period, entries in parse_grok_changelog(fetch_text(GROK_READER_URL))
    ]
    selected = records[:count]
    if not selected:
        raise ValueError("Grok Build changelog contained no versions")
    return sum(_write_raw("grok_build", record) for record in selected)


def fetch_muse_code() -> int:
    versions = parse_muse_changelog(fetch_text(MUSE_CHANGELOG_URL))
    if not versions:
        raise ValueError("Muse Code changelog contained no versions")
    versions.sort(key=lambda item: tuple(map(int, item[0].split("."))), reverse=True)
    existing = [
        tuple(map(int, path.stem.split(".")))
        for path in (RAW_ROOT / "muse_code").glob("*.json")
        if MUSE_VERSION.fullmatch(path.stem)
    ]
    if existing:
        latest = max(existing)
        selected = [item for item in versions if tuple(map(int, item[0].split("."))) > latest]
    else:
        selected = versions[:1]
    today = date.today().isoformat()
    return sum(
        _write_raw("muse_code", {
            "version": version,
            "period": today,
            "source_url": MUSE_CHANGELOG_URL,
            "fetched_at": today,
            "entries": entries,
        })
        for version, entries in selected
    )


def main() -> int:
    failures: list[tuple[str, str | None, Exception]] = []
    for tool_id, fetcher in (
        ("claude_code", fetch_claude),
        ("codex", fetch_codex),
        ("agy", fetch_agy),
        ("grok_build", fetch_grok_build),
        ("muse_code", fetch_muse_code),
        ("usage", fetch_usage),
        ("gh_cli", fetch_gh_cli),
    ):
        try:
            fetcher()
        except (
            OSError,
            http.client.HTTPException,
            UnicodeDecodeError,
            ValueError,
            json.JSONDecodeError,
            urllib.error.URLError,
        ) as exc:
            failures.append((tool_id, _last_request_url, exc))
    for tool_id, url, exc in failures:
        print(f"fetch failed: {tool_id} {url}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
