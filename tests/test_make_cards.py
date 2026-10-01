from __future__ import annotations

import builtins
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import make_cards as cards


def record(title="標題", body="開場⟦比喻⟧結尾"):
    return {
        "period": "2026-09-29 ~ 10-01",
        "items": [{"title": {"zh-TW": title}, "body": {"zh-TW": body}}],
    }


def card(version="1.0.0", title="標題", body="開場⟦比喻⟧結尾"):
    return {"id": "codex", "name": "Codex", "version": version, "curated": record(title, body)}


class FakePage:
    def __init__(self, fits=(True,), fail=False):
        self.fits = iter(fits)
        self.fail = fail
        self.sizes = []
        self.screenshots = []
        self.font_waits = 0

    def goto(self, url):
        html = Path(url.removeprefix("file://")).read_text()
        self.sizes.append(int(re.search(r"font-size:(\d+)px;line-height:1.25", html)[1]))

    def evaluate(self, script):
        if "document.fonts.ready" in script:
            self.font_waits += 1
            return None
        assert "top - bottom >= 16" in script
        assert "bottom <= 540" in script
        return next(self.fits)

    def screenshot(self, **kwargs):
        self.screenshots.append(kwargs)
        Path(kwargs["path"]).write_bytes(b"jpeg")
        if self.fail:
            self.fail = False
            raise RuntimeError("screenshot failed")


def test_select_latest_three_curated():
    versions = {f"1.{n}.0": record() if n < 4 else {"items": []} for n in range(6)}
    versions["1.3.0-rc.1"] = record()
    selected = cards.select_cards({"codex": ({}, versions), "agy": ({}, {})})
    assert [c["version"] for c in selected] == ["1.3.0", "1.3.0-rc.1", "1.2.0"]
    assert all(c["name"] == "Codex" for c in selected)
    assert cards.select_cards({}) == []


@pytest.mark.parametrize("text,expected", [
    ("短`比喻`", "短比喻。"),
    ("字" * 58, "字" * 58 + "。"),
    ("字" * 57 + "。", "字" * 57 + "。"),
    ("字" * 70, "字" * 58 + "。"),
    ("字" * 30 + "，" + "後" * 40, "字" * 30 + "。"),
    ("字" * 21 + "、" + "後" * 40, "字" * 21 + "。"),
    ("字" * 20 + "，" + "後" * 40, "字" * 20 + "，" + "後" * 37 + "。"),
    ("已有句號。", "已有句號。"),
])
def test_analogy_truncation(text, expected):
    assert cards.truncate_analogy(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("⟦`標題`⟧", "標題"),
    ("字" * 40, "字" * 40),
    ("字" * 50, "字" * 40),
    ("字" * 25 + "：" + "後" * 20, "字" * 25),
    ("字" * 40 + "，後", "字" * 40),
])
def test_title_truncation(text, expected):
    assert cards.card_title(card(title=text)) == expected


def test_html_escapes_all_text_and_omits_analogy():
    value = card(title="A < B & `C`", body="沒有比喻")
    value["name"] = '工具 < & "'
    html = cards.card_html(value, 64)
    assert "A &lt; B &amp; C" in html
    assert "工具 &lt; &amp; &quot;" in html
    assert '<div class="ana">' not in html
    assert "2026-10-01" in html
    assert (cards.ROOT / "docs/fonts/inter-latin.woff2").as_uri() in html
    value["curated"]["items"].append(record(body="⟦A < B & `C`⟧")["items"][0])
    assert '<div class="ana"><b>白話比喻</b>A &lt; B &amp; C。</div>' in cards.card_html(value, 48)


def test_existing_card_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "ROOT", tmp_path)
    path = cards.card_path(card())
    path.parent.mkdir(parents=True)
    path.write_bytes(b"old")
    page = FakePage()
    assert cards.screenshot_card(page, card()) == "skip-exists"
    assert path.read_bytes() == b"old"
    assert not page.sizes


def test_nofit_never_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "ROOT", tmp_path)
    page = FakePage((False, False, False))
    assert cards.screenshot_card(page, card()) == "skip-nofit"
    assert page.sizes == [64, 56, 48]
    assert page.font_waits == 3
    assert not page.screenshots
    assert not cards.card_path(card()).exists()


def test_smaller_font_and_atomic_screenshot(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "ROOT", tmp_path)
    page = FakePage((False, True))
    assert cards.screenshot_card(page, card()) == "ok"
    assert page.sizes == [64, 56]
    assert page.screenshots == [{
        "path": str(cards.card_path(card()).with_suffix(".jpg.tmp")),
        "type": "jpeg", "quality": 75,
    }]
    assert cards.card_path(card()).read_bytes() == b"jpeg"
    assert not list(tmp_path.rglob("*.tmp"))


def test_missing_playwright_returns_zero(monkeypatch, capsys):
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name.startswith("playwright"):
            raise ImportError("missing")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    assert cards.main() == 0
    assert capsys.readouterr().out.splitlines() == [
        "make_cards: playwright 未安裝，略過", "make_cards: ok=0 skip=0 fail=0",
    ]


class FakeBrowser:
    def __init__(self, page):
        self.page = page
        self.closed = False

    def new_page(self, **kwargs):
        assert kwargs == {"viewport": {"width": 1200, "height": 630}}
        return self.page

    def close(self):
        self.closed = True


class FakePlaywright:
    def __init__(self, browser):
        self.browser = browser
        self.chromium = self

    def launch(self, **kwargs):
        assert kwargs == {"headless": True}
        return self.browser

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def install_fake(monkeypatch, browser):
    monkeypatch.setitem(sys.modules, "playwright.sync_api", SimpleNamespace(
        sync_playwright=lambda: FakePlaywright(browser),
    ))


def test_single_failure_does_not_stop_next_card(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cards, "ROOT", tmp_path)
    monkeypatch.setattr(cards, "_load_and_validate_data", lambda: {
        "codex": ({}, {"2.0.0": record(), "1.0.0": record()}),
    })
    browser = FakeBrowser(FakePage((True, True), fail=True))
    install_fake(monkeypatch, browser)
    assert cards.main() == 0
    assert not cards.card_path(card("2.0.0")).exists()
    assert cards.card_path(card()).exists()
    assert not list(tmp_path.rglob("*.tmp"))
    assert browser.closed
    output = capsys.readouterr().out
    assert "card codex/2.0.0 fail: screenshot failed" in output
    assert "card codex/1.0.0 ok:" in output
    assert output.endswith("make_cards: ok=1 skip=0 fail=1\n")


def test_data_failure_returns_zero(monkeypatch, capsys):
    install_fake(monkeypatch, FakeBrowser(FakePage()))

    def broken():
        raise ValueError("bad data")

    monkeypatch.setattr(cards, "_load_and_validate_data", broken)
    assert cards.main() == 0
    assert "make_cards: fail: bad data" in capsys.readouterr().out


def test_main_existing_cards_never_launch_browser(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cards, "ROOT", tmp_path)
    monkeypatch.setattr(cards, "_load_and_validate_data", lambda: {
        "codex": ({}, {"1.0.0": record()}),
    })
    path = cards.card_path(card())
    path.parent.mkdir(parents=True)
    path.write_bytes(b"old")

    def unexpected_launch():
        pytest.fail("existing cards must not launch a browser")

    monkeypatch.setitem(sys.modules, "playwright.sync_api", SimpleNamespace(
        sync_playwright=unexpected_launch,
    ))
    assert cards.main() == 0
    assert capsys.readouterr().out.endswith("make_cards: ok=0 skip=1 fail=0\n")


def test_script_import_path_without_playwright(monkeypatch, capsys):
    import runpy

    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name.startswith("playwright"):
            raise ImportError("missing")
        return original(name, *args, **kwargs)

    monkeypatch.syspath_prepend(str(cards.ROOT / "scripts"))
    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(cards.ROOT / "scripts/make_cards.py"), run_name="__main__")
    assert result.value.code == 0
    assert "make_cards: playwright 未安裝，略過" in capsys.readouterr().out


def test_title_markup_breaks_after_first_comma_only_when_both_sides_are_long() -> None:
    assert cards.title_markup("全螢幕捲動效能升級，長對話不再卡頓") == (
        "全螢幕捲動效能升級，<br>長對話不再卡頓"
    )
    assert cards.title_markup("預設模型升級，快") == "預設模型升級，快"
    assert cards.title_markup("沒有逗號的標題") == "沒有逗號的標題"
    assert cards.title_markup("A < B，C & D 都不能原樣輸出") == (
        "A &lt; B，<br>C &amp; D 都不能原樣輸出"
    )
