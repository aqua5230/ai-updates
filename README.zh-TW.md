# AI Updates

[English](README.md) | 繁體中文

AI Updates 追蹤 Claude Code、Codex、Antigravity、Grok Build、Muse Code、Usage 與 GitHub CLI 的官方 changelog。它保存不可覆寫的官方原文紀錄，提供 AI 改寫的繁中與英文白話速報（zh-TW、en），每則都由另一個 AI 模型對照官方原文查核，並產出靜態網站與相容應用程式使用的資料 feed。

## 網站

https://aqua5230.github.io/ai-updates/

## 來源

| 工具 | 官方來源 |
| --- | --- |
| Claude Code | [Anthropic Claude Code changelog](https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md) |
| Codex | [OpenAI Codex releases](https://api.github.com/repos/openai/codex/releases) |
| Antigravity | [Antigravity CLI changelog](https://raw.githubusercontent.com/google-antigravity/antigravity-cli/main/CHANGELOG.md)（公開來源不可用時退回本機 `scripts/sync_agy.py`） |
| Grok Build | [Grok Build changelog](https://x.ai/changelog/build)（x.ai 擋直接抓取，經 [Jina Reader](https://jina.ai/reader/) 轉抓） |
| Muse Code | [Muse Code changelog](https://dev.meta.ai/docs/muse-code/changelog)（官方頁沒有發布日期，用第一次抓到的日期） |
| Usage | [Usage changelog](https://raw.githubusercontent.com/aqua5230/usage/main/CHANGELOG.md) |
| GitHub CLI | [GitHub CLI releases](https://api.github.com/repos/cli/cli/releases) |

## 運作方式

`data/raw/` 保存每天匯入的官方 changelog 項目。紀錄以版本為單位寫入，永不覆寫。`data/curated/` 保存這些項目經查核後的繁中與英文白話版本。

`scripts/build.py` 合併兩個資料層，產出以下檔案：

- `ai_updates.json`：供舊版應用程式使用的相容 feed；每個工具最多收錄三個最新的已審版本。
- `daily.json`：每日 feed；每個工具最多收錄三個最新版本。有白話版本時使用白話內容，否則保留官方原文並標示 `curated: false`。
- `docs/data.json`：供靜態網站使用的版本索引；每個工具的完整 raw／curated 歷史放在 `docs/history/<tool_id>.json`，避免網頁首頁一次載入全部歷史。

## 儲存庫結構

```text
data/
  raw/<tool_id>/<version>.json       # 不可覆寫的官方原文紀錄
  curated/<tool_id>/<version>.json   # 經查核的繁中與英文紀錄
  badge_overrides.json               # 規則判錯時手動指定的卡片標籤
docs/
  index.html                         # GitHub Pages 網站
  data.json                          # 產出的網站版本索引
  history/<tool_id>.json             # 產出的各工具完整歷史
  v/                                 # 產出的每版靜態頁
  feed.xml                           # 產出的 RSS feed
  sitemap.xml                        # 產出的網站地圖
  robots.txt                         # 產出的 robots.txt
  llms.txt                           # 產出的 LLM 說明檔
scripts/
  fetch.py                           # 抓取官方 changelog
  build.py                           # 建立產出 feed
  make_cards.py                      # 產生每版繁中分享卡
  sync_agy.py                        # 匯入本機 Antigravity CLI changelog 輸出
.github/workflows/
  daily.yml                          # 每日抓取與審核 issue workflow
  sync-usage.yml                     # 相容 feed 同步 workflow
ai_updates.json                      # 產出的相容 feed
daily.json                           # 產出的每日 feed
tests/                               # 測試套件
```

## 本機開發

需要 Python 3.13。儲存庫的執行期腳本只使用 Python 標準函式庫。

```bash
python3 scripts/fetch.py
python3 scripts/build.py
uv run ruff check scripts tests
uv run pytest -q
```

測試會 build 到暫存目錄，不會寫入工作區，所以上面兩個指令用什麼順序跑都安全。

若 Antigravity 公開來源無法使用，可改由已安裝的 CLI 匯入 changelog 輸出：

```bash
python3 scripts/sync_agy.py
```

此指令會執行 `agy changelog`；既有版本紀錄不會被覆寫。

## 審核流程

1. 每日 workflow 會為每個新匯入的版本建立 issue。
2. 本機排程由 AI 模型在 `data/curated/<tool>/<version>.json` 寫入繁中與英文白話 `items`，再由不同家族的模型對照 `original` 逐卡查核，依查核意見修改，最多數輪。
3. 通過 lint、查核、`python3 scripts/build.py` 與 `pytest` 的版本才提交，並關閉 issue。
4. 仍未通過的版本保留 issue，由人工接手。

白話內容必須準確反映官方項目。`original` 欄位保留原始英文文字。

## 自動化

- `daily.yml` 每日執行，抓取官方 changelog、為新版本建立審核 issue、建立產出 feed，並提交變更的原文與 feed 檔案。
- `sync-usage.yml` 原本把 `ai_updates.json` 同步至 `aqua5230/usage`，供 0.27 以前的舊版 app 讀取。2026-10-16 起停用，usage 保留最後一次同步的檔案；要恢復就跑 `gh workflow enable sync-usage.yml`。

## 相關專案

[aqua5230/usage](https://github.com/aqua5230/usage) 是相容 feed 的主要使用者。

## 維護者注意事項

重新啟用時，`sync-usage.yml` 需要名為 `USAGE_SYNC_TOKEN` 的 fine-grained personal access token。

1. 在 GitHub 開啟 **Settings → Developer settings → Personal access tokens → Fine-grained tokens**。
2. 將 resource owner 設為 `aqua5230`，選擇 **Only select repositories**，並選取 `aqua5230/usage`。
3. 只授予 **Contents: Read and write** repository permission。
4. 在本儲存庫的 **Settings → Secrets and variables → Actions** 將 token 新增為 `USAGE_SYNC_TOKEN` Actions secret。

不要將 token 寫入儲存庫檔案或 workflow。到期時應更換。
