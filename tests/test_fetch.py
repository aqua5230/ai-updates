from __future__ import annotations

import http.client
import io
import json
import urllib.error
from pathlib import Path

import pytest

from scripts import fetch
from scripts.sync_agy import parse_agy_changelog

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_claude_changelog_fixture() -> None:
    text = (FIXTURES / "claude_changelog.md").read_text(encoding="utf-8")

    assert fetch.parse_markdown_changelog(text) == [
        ("2.1.207", ["Added a visible feature.", "Fixed a bug."]),
        ("2.1.206", ["Improved startup time."]),
    ]


def test_parse_keepachangelog_stops_at_non_version_heading() -> None:
    text = """## [1.2.3] - 2026-07-13
- Shipped one feature.

## Migration notes
- This is guidance, not a release entry.
"""

    assert fetch.parse_keepachangelog(text) == [
        ("1.2.3", "2026-07-13", ["Shipped one feature."])
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


def test_parse_github_releases_skips_non_version_tags() -> None:
    payload = [
        {
            "tag_name": "python-v0.154.0",
            "body": "- Added a Python SDK feature.",
            "published_at": "2026-09-10T00:00:00Z",
            "html_url": "https://github.com/openai/codex/releases/tag/python-v0.154.0",
            "draft": False,
        },
        {
            "tag_name": "voice-cygwin-108b38cf67cbb731",
            "body": "- Unrelated asset drop.",
            "published_at": "2026-09-10T00:00:00Z",
            "html_url": "https://github.com/openai/codex/releases/tag/voice-cygwin-108b38cf67cbb731",
            "draft": False,
        },
        {
            "tag_name": "rust-v0.154.0",
            "body": "- Added a real feature.",
            "published_at": "2026-09-10T00:00:00Z",
            "html_url": "https://github.com/openai/codex/releases/tag/rust-v0.154.0",
            "draft": False,
        },
    ]

    assert fetch.parse_github_releases(payload) == [
        {
            "version": "0.154.0",
            "period": "2026-09-10",
            "source_url": "https://github.com/openai/codex/releases/tag/rust-v0.154.0",
            "entries": ["Added a real feature."],
        }
    ]


def test_parse_grok_changelog_fixture() -> None:
    text = (FIXTURES / "grok_changelog.md").read_text(encoding="utf-8")

    assert fetch.parse_grok_changelog(text) == [
        (
            "1.0.52",
            "2026-10-11",
            [
                "Added support for OSC 7501 and the Rex terminal",
                "HTTP hooks to `localhost` work, and bad hook URLs are reported at load time",
            ],
        ),
        ("1.0.51", "2026-10-09", ["Memory is only an on or off switch (`[memory] enabled`)"]),
    ]


def test_parse_gh_cli_releases_fixture() -> None:
    payload = json.loads((FIXTURES / "gh_cli_releases.json").read_text(encoding="utf-8"))

    assert fetch.parse_github_releases(payload) == [
        {
            "version": "2.63.0",
            "period": "2026-07-11",
            "source_url": "https://github.com/cli/cli/releases/tag/v2.63.0",
            "entries": ["Added one command.", "Fixed one issue."],
        },
        {
            "version": "2.62.0",
            "period": "2026-07-04",
            "source_url": "https://github.com/cli/cli/releases/tag/v2.62.0",
            "entries": ["Improved one workflow."],
        },
    ]


def test_parse_muse_changelog_fixture() -> None:
    text = (FIXTURES / "muse_changelog.html").read_text(encoding="utf-8")

    assert fetch.parse_muse_changelog(text) == [
        ("1.4.10", ["Added `/blender` to reconstruct reference images as editable Blender scenes"]),
        ("1.4.9", [
            "`--disable-request-user-input` (TUI, `muse exec`, `muse serve`) withholds "
            "`request_user_input` from the main conversation (side chats keep it), so an "
            "unattended run never stops to wait on a question; a call naming it gets an "
            "unavailable-tool error instead. `--yolo` implies the flag on the TUI and `muse exec`"
        ]),
    ]


def test_parse_muse_changelog_excludes_non_versions_and_navigation() -> None:
    text = """<nav><h2>9.0.0</h2><ul><li>Sidebar</li></ul></nav>
<article data-docs-article="true">
<h2><a><span>1.2.3</span></a></h2><h3>New</h3>
<ul><li>  Use <code>muse   exec</code> &amp;\n continue. </li></ul>
<h3>Fixes</h3><ul><li>Fixed <strong>startup</strong>.</li></ul>
<h2>1.0.x</h2><ul><li>Not a numeric version</li></ul>
<h2>0.1.x</h2><ul><li>Also not a numeric version</li></ul>
</article><aside><nav aria-label="On this page"><ul><li>1.2.3</li></ul></nav></aside>"""

    assert fetch.parse_muse_changelog(text) == [
        ("1.2.3", ["Use `muse exec` & continue.", "Fixed startup."]),
    ]


@pytest.mark.parametrize(
    ("existing", "expected"),
    [
        (None, ["1.4.10"]),
        ("1.4.8", ["1.4.10", "1.4.9"]),
        ("1.4.9", ["1.4.10"]),
        ("1.4.10", []),
    ],
)
def test_fetch_muse_code_selects_new_versions(tmp_path, monkeypatch, existing, expected) -> None:
    text = (FIXTURES / "muse_changelog.html").read_text(encoding="utf-8")
    urls = []

    def fetch_text(url):
        urls.append(url)
        return text

    monkeypatch.setattr(fetch, "RAW_ROOT", tmp_path)
    monkeypatch.setattr(fetch, "fetch_text", fetch_text)
    directory = tmp_path / "muse_code"
    directory.mkdir()
    (directory / "9.0.x.json").write_text("ignored")
    if existing:
        (directory / f"{existing}.json").write_text("immutable")

    assert fetch.fetch_muse_code() == len(expected)
    assert urls == [fetch.MUSE_CHANGELOG_URL]
    assert {p.stem for p in directory.glob("*.json")} == {
        "9.0.x", *expected, *([existing] if existing else []),
    }
    entries = dict(fetch.parse_muse_changelog(text))
    for version in expected:
        assert json.loads((directory / f"{version}.json").read_text()) == {
            "version": version,
            "period": fetch.date.today().isoformat(),
            "fetched_at": fetch.date.today().isoformat(),
            "source_url": fetch.MUSE_CHANGELOG_URL,
            "entries": entries[version],
        }
    if existing:
        assert (directory / f"{existing}.json").read_text() == "immutable"


def test_fetch_muse_code_rejects_empty_changelog(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(fetch, "RAW_ROOT", tmp_path)
    monkeypatch.setattr(fetch, "fetch_text", lambda url: "<html></html>")

    with pytest.raises(ValueError, match="^Muse Code changelog contained no versions$"):
        fetch.fetch_muse_code()
    assert not list(tmp_path.iterdir())


def test_fetch_grok_build_defaults_to_fifteen_versions(tmp_path, monkeypatch) -> None:
    text = "October 19, 2026\n" + "".join(
        f"## Grok Build 1.0.{patch}\n* Release {patch}\n" for patch in range(62, 46, -1)
    )
    monkeypatch.setattr(fetch, "RAW_ROOT", tmp_path)
    monkeypatch.setattr(fetch, "fetch_text", lambda url: text)

    assert fetch.fetch_grok_build() == 15
    assert {path.stem for path in (tmp_path / "grok_build").glob("*.json")} == {
        f"1.0.{patch}" for patch in range(48, 63)
    }


def test_release_body_entries_ignores_changelog_pr_list() -> None:
    body = """## New Features
- Added a faster installer.
- Added compact release metadata.

## Changelog
- #31667 fix: parse compact release metadata in installer @efrazer-oai
- #31668 fix: another generated changelog item @someone
- #31669 chore: one more generated changelog item @someone
"""

    assert fetch._release_body_entries(body) == [
        "Added a faster installer.",
        "Added compact release metadata.",
    ]


def test_release_body_entries_stops_at_whats_changed() -> None:
    body = """## Security
A security vulnerability has been fixed.

## Support worktrees in `pr checkout`
Users can now check out a pull request into a git worktree.

## Add semantic search to `search issues`
The command now supports semantic search.

## What's Changed
* Add --worktree flag to gh pr checkout by @tidy-dev
* Set GH_EXTENSION=1 when gh invokes an extension by @williammartin
"""

    entries = fetch._release_body_entries(body)

    assert entries == [
        """## Security
A security vulnerability has been fixed.

## Support worktrees in `pr checkout`
Users can now check out a pull request into a git worktree.

## Add semantic search to `search issues`
The command now supports semantic search."""
    ]
    assert "Add --worktree flag" not in entries[0]


def test_release_body_entries_keeps_codex_categories_before_changelog() -> None:
    body = """## New Features

- Added a configurable grace period for discovering tools from optional MCP servers.
- Extensions can now inspect or replace MCP tool results before they reach the model.
- Plugin catalogs now combine per-repository configuration.

## Bug Fixes

- Preserved restored permission profiles across TUI turns.

## Chores

- Added telemetry for escalated stdin reviews.

## Changelog

- #41183 Account subagent token usage toward root goal budgets @copyberry
"""

    assert fetch._release_body_entries(body) == [
        "Added a configurable grace period for discovering tools from optional MCP servers.",
        "Extensions can now inspect or replace MCP tool results before they reach the model.",
        "Plugin catalogs now combine per-repository configuration.",
        "Preserved restored permission profiles across TUI turns.",
        "Added telemetry for escalated stdin reviews.",
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


@pytest.mark.parametrize("version", ["../evil", "a/b"])
def test_write_raw_rejects_unsafe_version(
    tmp_path: Path, monkeypatch, version: str
) -> None:
    monkeypatch.setattr(fetch, "RAW_ROOT", tmp_path)
    record = {"version": version}

    with pytest.raises(ValueError) as exc_info:
        fetch._write_raw("tool", record)

    assert "tool" in str(exc_info.value)
    assert version in str(exc_info.value)


@pytest.mark.parametrize("version", ["1.2.3", "0.143.0-alpha.38"])
def test_write_raw_accepts_safe_versions(
    tmp_path: Path, monkeypatch, version: str
) -> None:
    monkeypatch.setattr(fetch, "RAW_ROOT", tmp_path)

    assert fetch._write_raw("tool", {"version": version})
    assert (tmp_path / "tool" / f"{version}.json").exists()


def test_main_continues_after_single_fetcher_failure(monkeypatch, capsys) -> None:
    calls: list[str] = []
    failure = urllib.error.URLError("offline")

    def fail() -> int:
        calls.append("claude_code")
        fetch._last_request_url = "https://example.invalid/claude"
        raise failure

    def succeed(tool_id: str) -> int:
        calls.append(tool_id)
        return 0

    monkeypatch.setattr(fetch, "fetch_claude", fail)
    monkeypatch.setattr(fetch, "fetch_codex", lambda: succeed("codex"))
    monkeypatch.setattr(fetch, "fetch_agy", lambda: succeed("agy"))
    monkeypatch.setattr(fetch, "fetch_grok_build", lambda: succeed("grok_build"))
    monkeypatch.setattr(fetch, "fetch_muse_code", lambda: succeed("muse_code"))
    monkeypatch.setattr(fetch, "fetch_usage", lambda: succeed("usage"))
    monkeypatch.setattr(fetch, "fetch_gh_cli", lambda: succeed("gh_cli"))

    assert fetch.main() == 1
    assert calls == ["claude_code", "codex", "agy", "grok_build", "muse_code", "usage", "gh_cli"]
    assert capsys.readouterr().err == (
        "fetch failed: claude_code https://example.invalid/claude: <urlopen error offline>\n"
    )


def test_main_continues_after_truncated_download(monkeypatch) -> None:
    calls: list[str] = []

    def truncated() -> int:
        calls.append("codex")
        raise http.client.IncompleteRead(b"partial", 32_000_000)

    def succeed(tool_id: str) -> int:
        calls.append(tool_id)
        return 0

    monkeypatch.setattr(fetch, "fetch_claude", lambda: succeed("claude_code"))
    monkeypatch.setattr(fetch, "fetch_codex", truncated)
    monkeypatch.setattr(fetch, "fetch_agy", lambda: succeed("agy"))
    monkeypatch.setattr(fetch, "fetch_grok_build", lambda: succeed("grok_build"))
    monkeypatch.setattr(fetch, "fetch_muse_code", lambda: succeed("muse_code"))
    monkeypatch.setattr(fetch, "fetch_usage", lambda: succeed("usage"))
    monkeypatch.setattr(fetch, "fetch_gh_cli", lambda: succeed("gh_cli"))

    assert fetch.main() == 1
    assert calls == ["claude_code", "codex", "agy", "grok_build", "muse_code", "usage", "gh_cli"]


def test_request_retries_connection_reset_then_succeeds(monkeypatch) -> None:
    outcomes: list[ConnectionResetError | io.BytesIO] = [
        ConnectionResetError(104, "Connection reset by peer"),
        ConnectionResetError(104, "Connection reset by peer"),
        io.BytesIO(b"response"),
    ]
    calls = []
    delays = []

    def urlopen(*args, **kwargs):
        calls.append((args, kwargs))
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)

    assert fetch._request("https://example.invalid", sleep=delays.append) == b"response"
    assert len(calls) == 3
    assert delays == [1.0, 2.0]


def test_request_retries_incomplete_read_then_succeeds(monkeypatch) -> None:
    """大回應被中途截斷丟的是 http.client.IncompleteRead，不是 ConnectionError。"""
    outcomes: list[BaseException | io.BytesIO] = [
        http.client.IncompleteRead(b"partial", 27206124),
        io.BytesIO(b"response"),
    ]
    calls = []
    delays = []

    def urlopen(*args, **kwargs):
        calls.append((args, kwargs))
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)

    assert fetch._request("https://example.invalid", sleep=delays.append) == b"response"
    assert len(calls) == 2
    assert delays == [1.0]


def test_request_does_not_retry_non_retryable_http_error(monkeypatch) -> None:
    error = urllib.error.HTTPError("https://example.invalid", 404, "Not Found", None, None)
    calls = []

    def urlopen(*args, **kwargs):
        calls.append((args, kwargs))
        raise error

    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)

    with pytest.raises(urllib.error.HTTPError) as exc_info:
        fetch._request("https://example.invalid", sleep=lambda _: None)

    assert exc_info.value is error
    assert len(calls) == 1


def test_request_retries_retryable_http_error_then_succeeds(monkeypatch) -> None:
    error = urllib.error.HTTPError(
        "https://example.invalid", 503, "Service Unavailable", None, None
    )
    outcomes: list[urllib.error.HTTPError | io.BytesIO] = [error, io.BytesIO(b"response")]
    calls = []

    def urlopen(*args, **kwargs):
        calls.append((args, kwargs))
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)

    assert fetch._request("https://example.invalid", sleep=lambda _: None) == b"response"
    assert len(calls) == 2


def test_request_raises_last_exception_after_retries(monkeypatch) -> None:
    errors = [
        ConnectionResetError(104, "Connection reset by peer"),
        ConnectionResetError(104, "Connection reset by peer"),
        ConnectionResetError(104, "Connection reset by peer"),
    ]
    expected_error = errors[-1]
    calls = []
    delays = []

    def urlopen(*args, **kwargs):
        calls.append((args, kwargs))
        raise errors.pop(0)

    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)

    with pytest.raises(ConnectionResetError) as exc_info:
        fetch._request("https://example.invalid", sleep=delays.append)

    assert exc_info.value is expected_error
    assert len(calls) == 3
    assert delays == [1.0, 2.0]
