#!/usr/bin/env python3
"""產生繁中版本分享卡；任何失敗都不阻斷建置。"""

from __future__ import annotations

import os
import re
from html import escape
from pathlib import Path
from string import Template
from tempfile import TemporaryDirectory
from typing import Any

try:
    from .build import (
        ROOT,
        TOOLS,
        _curated_items,
        _load_and_validate_data,
        _localized,
        _period_end_date,
        _strip_analogy_marks,
        _version_key,
    )
except ImportError:
    from build import (
        ROOT,
        TOOLS,
        _curated_items,
        _load_and_validate_data,
        _localized,
        _period_end_date,
        _strip_analogy_marks,
        _version_key,
    )

HTML = Template('''<!doctype html><meta charset="utf-8"><style>
@font-face{font-family:'Inter';font-weight:300 700;src:url($font_url) format("woff2")}
*{box-sizing:border-box}html,body{margin:0;width:1200px;height:630px;overflow:hidden}
body{font-family:"Inter","PingFang TC","Noto Sans TC",sans-serif}
.card{width:1200px;height:630px;position:relative;overflow:hidden;background:#fff;
background-image:radial-gradient(ellipse 560px 380px at 95% 0%,
rgb(37 99 235 / .14),transparent 70%),radial-gradient(ellipse 420px 300px at 70% 0%,
rgb(21 117 162 / .10),transparent 70%);padding:64px 88px;color:#425466}
.eyebrow{display:flex;align-items:center;gap:14px;font-size:26px;
font-weight:700;color:#061b31}
.eyebrow::before{content:"";width:14px;height:14px;border-radius:50%;background:#3b82f6}
.chip{margin-top:44px;display:inline-flex;gap:14px;align-items:baseline;padding:10px 22px;
border-radius:14px;background:#eff6ff;color:#2563eb;font-size:28px;font-weight:700}
.chip span{color:#586a82;font-weight:500;font-size:22px}
.title{margin-top:34px;font-size:${title_size}px;line-height:1.25;color:#061b31;
font-weight:700;max-width:1000px;text-wrap:balance}
.ana{position:absolute;left:88px;right:88px;bottom:118px;font-size:28px;line-height:1.5;
color:#586a82;border-top:1.5px solid #d8e3ee;padding-top:18px}
.ana b{color:#2563eb;font-size:20px;letter-spacing:.08em;margin-right:12px}
.url{position:absolute;right:88px;bottom:60px;font-size:20px;color:#586a82}
</style><div class="card"><div class="eyebrow">AI Updates</div>
<div class="chip">$tool $version<span>$date</span></div>
<div class="title">$title</div>$analogy_block
<div class="url">aqua5230.github.io/ai-updates/</div></div>
''')


def select_cards(
    loaded: dict[str, tuple[dict[str, Any], dict[str, Any]]],
) -> list[dict[str, Any]]:
    cards = []
    for tool_id, name in TOOLS:
        _, curated = loaded.get(tool_id, ({}, {}))
        versions = [
            version for version, record in curated.items()
            if _curated_items({"curated": record})
        ]
        for version in sorted(versions, key=_version_key, reverse=True)[:3]:
            cards.append({
                "id": tool_id, "name": name, "version": version, "curated": curated[version],
            })
    return cards


def card_title(card: dict[str, Any]) -> str:
    items = _curated_items(card)
    if not items:
        return ""
    title = _strip_analogy_marks(_localized(items[0].get("title"), "zh-TW")).replace("`", "")
    if len(title) <= 40:
        return title
    cut = max(title[:40].rfind(mark) for mark in "，、：；")
    return title[:cut] if cut > 0 else title[:40]


def truncate_analogy(text: str) -> str:
    text = text.replace("`", "")
    if len(text) > 58:
        cut = max(text[:58].rfind(mark) for mark in "，、")
        text = text[:cut] if cut > 20 else text[:58]
    return text if text.endswith("。") else text + "。"


def card_analogy(card: dict[str, Any]) -> str:
    for item in _curated_items(card):
        match = re.search(r"⟦(.*?)⟧", _localized(item.get("body"), "zh-TW"), re.DOTALL)
        if match and match.group(1).strip():
            return truncate_analogy(match.group(1))
    return ""


def title_markup(title: str) -> str:
    """2026-10-01：中文自動換行會切斷詞，標題在第一個逗號後手動換行。"""
    head, mark, tail = title.partition("，")
    if mark and len(head) >= 4 and len(tail) >= 4:
        return f"{escape(head)}，<br>{escape(tail)}"
    return escape(title)


def card_html(card: dict[str, Any], title_size: int) -> str:
    analogy = card_analogy(card)
    block = f'<div class="ana"><b>白話比喻</b>{escape(analogy)}</div>' if analogy else ""
    return HTML.substitute(
        font_url=escape((ROOT / "docs/fonts/inter-latin.woff2").as_uri()),
        tool=escape(card["name"]), version=escape(card["version"]),
        date=escape(_period_end_date(card["curated"]["period"])),
        title=title_markup(card_title(card)), title_size=escape(str(title_size)),
        analogy_block=block,
    )


def card_path(card: dict[str, Any]) -> Path:
    return ROOT / "docs" / "og" / card["id"] / f'{card["version"]}.jpg'


def screenshot_card(page: Any, card: dict[str, Any]) -> str:
    """2026-10-01：逐張隔離失敗，先寫暫存檔再換成正式檔。"""
    output = card_path(card)
    temporary = output.with_suffix(".jpg.tmp")
    status, reason = "fail", ""
    try:
        if output.exists():
            status, reason = "skip-exists", "已存在"
        else:
            with TemporaryDirectory() as directory:
                source = Path(directory) / "card.html"
                for size in (64, 56, 48):
                    source.write_text(card_html(card, size), encoding="utf-8")
                    page.goto(source.as_uri())
                    page.evaluate("async () => { await document.fonts.ready; }")
                    fits = page.evaluate('''() => {
                        const title = document.querySelector('.title');
                        const bottom = title.getBoundingClientRect().bottom;
                        const ana = document.querySelector('.ana');
                        return ana ? ana.getBoundingClientRect().top - bottom >= 16 : bottom <= 540;
                    }''')
                    if fits:
                        output.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(temporary), type="jpeg", quality=75)
                        os.replace(temporary, output)
                        status, reason = "ok", f"字級 {size}px"
                        break
                else:
                    status, reason = "skip-nofit", "三個字級皆不合格"
    except Exception as exc:
        reason = str(exc)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError as exc:
            status, reason = "fail", f"暫存檔清理失敗：{exc}"
    print(f'card {card["id"]}/{card["version"]} {status}: {reason}')
    return status


def main() -> int:
    counts = {"ok": 0, "skip": 0, "fail": 0}
    try:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("make_cards: playwright 未安裝，略過")
            return 0
        cards = select_cards(_load_and_validate_data())
        pending = []
        for card in cards:
            if card_path(card).exists():
                print(f'card {card["id"]}/{card["version"]} skip-exists: 已存在')
                counts["skip"] += 1
            else:
                pending.append(card)
        if pending:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page(viewport={"width": 1200, "height": 630})
                    for card in pending:
                        status = screenshot_card(page, card)
                        counts["skip" if status.startswith("skip-") else status] += 1
                finally:
                    browser.close()
    except Exception as exc:
        counts["fail"] += 1
        print(f"make_cards: fail: {exc}")
    finally:
        print(f'make_cards: ok={counts["ok"]} skip={counts["skip"]} fail={counts["fail"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
