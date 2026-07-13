# AI Updates

English | [繁體中文](README.zh-TW.md)

AI Updates tracks the official changelogs for Claude Code, Codex, and Antigravity. It preserves immutable source records, supports human-reviewed plain-language updates in five languages (zh-TW, zh-CN, en, ja, and ko), and publishes feeds for a static website and compatible applications.

## Website

https://aqua5230.github.io/ai-updates/

## Sources

| Tool | Official source |
| --- | --- |
| Claude Code | [Anthropic Claude Code changelog](https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md) |
| Codex | [OpenAI Codex releases](https://api.github.com/repos/openai/codex/releases) |
| Antigravity | [Antigravity CLI changelog](https://raw.githubusercontent.com/google-antigravity/antigravity-cli/main/CHANGELOG.md) |

## How It Works

`data/raw/` stores daily imports of official changelog entries. Records are written per version and are never overwritten. `data/curated/` holds human-reviewed, plain-language versions of those entries in five languages.

`scripts/build.py` combines both layers into three generated artifacts:

- `ai_updates.json`: compatibility feed for the legacy application, containing up to three latest curated versions per tool.
- `daily.json`: daily feed containing up to three latest versions per tool; it uses curated content when available and otherwise retains the official source text with `curated: false`.
- `docs/data.json`: complete history for the static website, retaining both raw and curated records.

## Repository Layout

```text
data/
  raw/<tool_id>/<version>.json       # Immutable official source records
  curated/<tool_id>/<version>.json   # Human-reviewed five-language records
docs/
  index.html                         # GitHub Pages site
  data.json                          # Generated website data
scripts/
  fetch.py                           # Fetch official changelogs
  build.py                           # Build generated feeds
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
pytest
```

If the public Antigravity source is unavailable, import changelog output from an installed CLI instead:

```bash
python3 scripts/sync_agy.py
```

This command runs `agy changelog`; existing version records are not overwritten.

## Curation Workflow

1. The daily workflow opens an issue for each newly imported version.
2. Create `data/curated/<tool>/<version>.json` with the reviewed five-language plain-language `items`.
3. Run `python3 scripts/build.py` and `pytest`.
4. Open a pull request and merge it after review.

Curated content must accurately reflect the official entries. The `original` field retains the original English text.

## Automation

- `daily.yml` runs daily, fetches official changelogs, opens review issues for newly discovered versions, builds generated feeds, and commits changed source and feed files.
- `sync-usage.yml` runs when `ai_updates.json` changes on `main` and synchronizes that file to `aqua5230/usage`.

## Related Project

[aqua5230/usage](https://github.com/aqua5230/usage) is the primary consumer of the compatibility feed.

## Maintainer Notes

`sync-usage.yml` requires a fine-grained personal access token named `USAGE_SYNC_TOKEN`.

1. In GitHub, open **Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Set the resource owner to `aqua5230`, choose **Only select repositories**, and select `aqua5230/usage`.
3. Grant only **Contents: Read and write** repository permission.
4. Add the token as the `USAGE_SYNC_TOKEN` Actions secret in this repository under **Settings → Secrets and variables → Actions**.

Do not store the token in repository files or workflows. Replace it when it expires.
