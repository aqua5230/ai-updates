# AI Updates

English | [繁體中文](README.zh-TW.md)

AI Updates tracks the official changelogs for Claude Code, Codex, Antigravity, Grok Build, Muse Code, Usage, and GitHub CLI. It preserves immutable source records, supports AI-written plain-language updates in Traditional Chinese (zh-TW) and English (en), each fact-checked against the official text by a second AI model, and publishes feeds for a static website and compatible applications.

## Website

https://aqua5230.github.io/ai-updates/

## Sources

| Tool | Official source |
| --- | --- |
| Claude Code | [Anthropic Claude Code changelog](https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md) |
| Codex | [OpenAI Codex releases](https://api.github.com/repos/openai/codex/releases) |
| Antigravity | [Antigravity CLI changelog](https://raw.githubusercontent.com/google-antigravity/antigravity-cli/main/CHANGELOG.md) (falls back to local `scripts/sync_agy.py` if public source is unavailable) |
| Grok Build | [Grok Build changelog](https://x.ai/changelog/build) (fetched through [Jina Reader](https://jina.ai/reader/) because x.ai blocks direct requests) |
| Muse Code | [Muse Code changelog](https://dev.meta.ai/docs/muse-code/changelog) (no release dates on the page; the date a version is first fetched is used) |
| Usage | [Usage changelog](https://raw.githubusercontent.com/aqua5230/usage/main/CHANGELOG.md) |
| GitHub CLI | [GitHub CLI releases](https://api.github.com/repos/cli/cli/releases) |

## How It Works

`data/raw/` stores daily imports of official changelog entries. Records are written per version and are never overwritten. `data/curated/` holds fact-checked, plain-language versions of those entries in Traditional Chinese and English.

`scripts/build.py` combines both layers into generated artifacts:

- `ai_updates.json`: compatibility feed for the legacy application, containing up to three latest curated versions per tool.
- `daily.json`: daily feed containing up to three latest versions per tool; it uses curated content when available and otherwise retains the official source text with `curated: false`.
- `docs/data.json`: version index for the static website; complete raw and curated history for each tool is stored in `docs/history/<tool_id>.json` so the homepage does not need to load the full history at once.

## Repository Layout

```text
data/
  raw/<tool_id>/<version>.json       # Immutable official source records
  curated/<tool_id>/<version>.json   # Fact-checked zh-TW and en records
  badge_overrides.json               # Card badges fixed by hand where the rule misjudges
docs/
  index.html                         # GitHub Pages site
  data.json                          # Generated website version index
  history/<tool_id>.json             # Generated full history per tool
  v/                                 # Generated per-version static pages
  feed.xml                           # Generated RSS feed
  sitemap.xml                        # Generated sitemap
  robots.txt                         # Generated robots.txt
  llms.txt                           # Generated LLM reference file
scripts/
  fetch.py                           # Fetch official changelogs
  build.py                           # Build generated feeds
  make_cards.py                      # Generate zh-TW per-version sharing cards
  sync_agy.py                        # Import local Antigravity CLI changelog output
.github/workflows/
  daily.yml                          # Daily fetch and review-issue workflow
  sync-usage.yml                     # Compatibility-feed sync workflow
ai_updates.json                      # Generated compatibility feed
daily.json                           # Generated daily feed
tests/                               # Test suite
```

## Local Development

Requires Python 3.13. The repository's runtime scripts use only the Python standard library.

```bash
python3 scripts/fetch.py
python3 scripts/build.py
uv run ruff check scripts tests
uv run pytest -q
```

The test suite builds into a temporary directory and never writes to the working tree, so the two commands above are safe to run in any order.

If the public Antigravity source is unavailable, import changelog output from an installed CLI instead:

```bash
python3 scripts/sync_agy.py
```

This command runs `agy changelog`; existing version records are not overwritten.

## Curation Workflow

1. The daily workflow opens an issue for each newly imported version.
2. A local scheduled job has an AI model write the zh-TW and en plain-language `items` in `data/curated/<tool>/<version>.json`. A model from a different family then checks each card against `original` and the findings are fixed, for up to several rounds.
3. Only versions that pass lint, the fact check, `python3 scripts/build.py`, and `pytest` are committed; the issue is then closed.
4. Versions that still fail keep their issue open for a person to take over.

Curated content must accurately reflect the official entries. The `original` field retains the original English text.

## Automation

- `daily.yml` runs daily, fetches official changelogs, opens review issues for newly discovered versions, builds generated feeds, and commits changed source and feed files.
- `sync-usage.yml` synchronized `ai_updates.json` to `aqua5230/usage` for apps older than 0.27. It has been disabled since 2026-10-16, so usage keeps its last synced copy; `gh workflow enable sync-usage.yml` resumes it.

## Related Project

[aqua5230/usage](https://github.com/aqua5230/usage) is the primary consumer of the compatibility feed.

## Maintainer Notes

If re-enabled, `sync-usage.yml` requires a fine-grained personal access token named `USAGE_SYNC_TOKEN`.

1. In GitHub, open **Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Set the resource owner to `aqua5230`, choose **Only select repositories**, and select `aqua5230/usage`.
3. Grant only **Contents: Read and write** repository permission.
4. Add the token as the `USAGE_SYNC_TOKEN` Actions secret in this repository under **Settings → Secrets and variables → Actions**.

Do not store the token in repository files or workflows. Replace it when it expires.
