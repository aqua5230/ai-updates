from __future__ import annotations

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
