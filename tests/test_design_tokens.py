from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FONT_DECLARATION = re.compile(r"(?<![-\w])(font-size|font)\s*:\s*([^;}]+)")
LITERAL_SIZE = re.compile(r"(?<![\w.#-])(?:\d*\.)?\d+(?:rem|px)(?![\w%])")
TOKEN_DEFINITION = re.compile(r"(--(?:fs|control)-[\w-]+):([^;}]+)")


def index_css() -> str:
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    return html[html.index("<style>") : html.index("</style>")]


def version_page_css() -> str:
    source = (ROOT / "scripts" / "build.py").read_text(encoding="utf-8")
    start = source.index("<style>")
    return source[start : source.index("</style>", start)].replace("{{", "{").replace("}}", "}")


def token_definitions(css: str) -> dict[str, str]:
    return dict(TOKEN_DEFINITION.findall(css))


def literal_font_sizes(css: str) -> list[str]:
    hits = []
    for prop, value in FONT_DECLARATION.findall(css):
        if "clamp(" in value:
            continue
        hits.extend(f"{prop}:{value.strip()}" for _ in LITERAL_SIZE.findall(value))
    return hits


def test_both_stylesheets_share_the_same_tokens() -> None:
    index_tokens = token_definitions(index_css())
    assert index_tokens == token_definitions(version_page_css())
    assert sorted(name for name in index_tokens if name.startswith("--fs-")) == [
        "--fs-2xs",
        "--fs-base",
        "--fs-lg",
        "--fs-md",
        "--fs-sm",
        "--fs-xl",
        "--fs-xs",
    ]


def test_font_sizes_only_use_tokens() -> None:
    assert literal_font_sizes(index_css()) == []
    assert literal_font_sizes(version_page_css()) == []


def test_literal_font_size_is_detected() -> None:
    assert literal_font_sizes(".a{font-size:.73rem}.b{font:700 12px Inter}") == [
        "font-size:.73rem",
        "font:700 12px Inter",
    ]
    assert (
        literal_font_sizes(
            ".a{font-size:var(--fs-sm)}.b{font:.9em mono}.c{font-size:clamp(1rem,2vw,2rem)}"
        )
        == []
    )
