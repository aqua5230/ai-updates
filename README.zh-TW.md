# AI Updates

[English](README.md) | 繁體中文

AI Updates 追蹤 Claude Code、Codex 與 Antigravity 的官方 changelog。它保存不可覆寫的官方原文紀錄，支援經人工審核的五語白話速報（zh-TW、zh-CN、en、ja、ko），並產出靜態網站與相容應用程式使用的資料 feed。

## 網站

https://aqua5230.github.io/ai-updates/

## 來源

| 工具 | 官方來源 |
| --- | --- |
| Claude Code | [Anthropic Claude Code changelog](https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md) |
| Codex | [OpenAI Codex releases](https://api.github.com/repos/openai/codex/releases) |
| Antigravity | [Antigravity CLI changelog](https://raw.githubusercontent.com/google-antigravity/antigravity-cli/main/CHANGELOG.md) |

## 運作方式

`data/raw/` 保存每天匯入的官方 changelog 項目。紀錄以版本為單位寫入，永不覆寫。`data/curated/` 保存這些項目經人工審核後的五語白話版本。

`scripts/build.py` 合併兩個資料層，產出三個檔案：

- `ai_updates.json`：供舊版應用程式使用的相容 feed；每個工具最多收錄三個最新的已審版本。
- `daily.json`：每日 feed；每個工具最多收錄三個最新版本。有白話版本時使用白話內容，否則保留官方原文並標示 `curated: false`。
- `docs/data.json`：供靜態網站使用的完整歷史，保留 raw 與 curated 紀錄。

## 儲存庫結構

```text
data/
  raw/<tool_id>/<version>.json       # 不可覆寫的官方原文紀錄
  curated/<tool_id>/<version>.json   # 人工審核的五語紀錄
docs/
  index.html                         # GitHub Pages 網站
  data.json                          # 產出的網站資料
scripts/
  fetch.py                           # 抓取官方 changelog
  build.py                           # 建立產出 feed
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
pytest
```

若 Antigravity 公開來源無法使用，可改由已安裝的 CLI 匯入 changelog 輸出：

```bash
python3 scripts/sync_agy.py
```

此指令會執行 `agy changelog`；既有版本紀錄不會被覆寫。

## 審核流程

1. 每日 workflow 會為每個新匯入的版本建立 issue。
2. 建立 `data/curated/<tool>/<version>.json`，寫入經審核的五語白話 `items`。
3. 執行 `python3 scripts/build.py` 與 `pytest`。
4. 建立 pull request，審核後合併。

白話內容必須準確反映官方項目。`original` 欄位保留原始英文文字。

## 自動化

- `daily.yml` 每日執行，抓取官方 changelog、為新版本建立審核 issue、建立產出 feed，並提交變更的原文與 feed 檔案。
- `sync-usage.yml` 在 `main` 上的 `ai_updates.json` 變更時執行，並將該檔案同步至 `aqua5230/usage`。

## 相關專案

[aqua5230/usage](https://github.com/aqua5230/usage) 是相容 feed 的主要使用者。

## 維護者注意事項

`sync-usage.yml` 需要名為 `USAGE_SYNC_TOKEN` 的 fine-grained personal access token。

1. 在 GitHub 開啟 **Settings → Developer settings → Personal access tokens → Fine-grained tokens**。
2. 將 resource owner 設為 `aqua5230`，選擇 **Only select repositories**，並選取 `aqua5230/usage`。
3. 只授予 **Contents: Read and write** repository permission。
4. 在本儲存庫的 **Settings → Secrets and variables → Actions** 將 token 新增為 `USAGE_SYNC_TOKEN` Actions secret。

不要將 token 寫入儲存庫檔案或 workflow。到期時應更換。
