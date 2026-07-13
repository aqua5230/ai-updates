# ai-updates 專案規格（真相來源，工人動工前必讀）

## 這是什麼

把 usage 專案（`~/Developer/usage`）裡的「AI 工具更新速報」內容管線拆成獨立專案：

1. **每天自動**抓四個 AI 工具的官方 changelog 原文，逐版本存檔（永久歷史紀錄）。
2. 提供一個 **GitHub Pages 靜態網頁**，顯示最新速報＋每工具的完整更新歷史，支援五語。
3. 白話速報（五語改寫）仍走「人審後合入」，不全自動——原文層每天自動更新，白話層審核後上。
4. 合入後自動把 `ai_updates.json` **同步回 usage repo**（aqua5230/usage main），讓已發佈的舊版 app 繼續吃到新內容（app 讀 `https://raw.githubusercontent.com/aqua5230/usage/main/ai_updates.json`，schema 不能變）。
5. 供 usage app 的「AI 更新日報」面板吃的每日 feed：`daily.json`——每工具最新幾個版本，有白話用白話、還沒審的用原文逐字（標 `curated: false`），保證每天自動有新內容。

## 四個工具與官方來源

| id | 顯示名 | 原文來源 |
|---|---|---|
| `claude_code` | Claude Code | `https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md` |
| `codex` | Codex | GitHub releases API：`https://api.github.com/repos/openai/codex/releases` |
| `agy` | Antigravity | 本機 `agy changelog`（純文字，格式：`版本號:` 開頭、每則 `· ` 開頭）。CI 上若找得到官方公開來源（網頁或 API）就用；找不到就做 `scripts/sync_agy.py`（本機跑 `agy changelog` 解析後落檔 commit），CI 只處理前兩個工具。 |
| `usage` | Usage | `https://raw.githubusercontent.com/aqua5230/usage/main/CHANGELOG.md` |

## 目錄結構

```
ai-updates/
  data/raw/<tool_id>/<version>.json      # 自動：官方原文逐字，永不刪
  data/curated/<tool_id>/<version>.json  # 人審：五語白話 items（app schema 的 items）
  ai_updates.json                        # build 產物：app 吃的檔（curated 最新 N 版/工具）
  docs/                                  # GitHub Pages 靜態網頁（index.html + data.json）
  scripts/fetch.py                       # 抓原文 → data/raw/，發現新版本回報
  scripts/build.py                       # data/ → ai_updates.json + docs/data.json
  scripts/sync_agy.py                    # 本機跑：agy changelog → data/raw/agy/
  .github/workflows/daily.yml            # 每日 cron：fetch → 有新版 build+commit＋開 issue 提醒
  .github/workflows/sync-usage.yml       # ai_updates.json 變動時，用 PAT 推單檔到 aqua5230/usage
  drafts/                                # 網頁視覺草案（agy 產，選定後併入 docs/）
```

## Schema 鐵則

- `ai_updates.json` 必須通過 usage 的 `analyzer/ai_updates_loader.py::_normalize_payload` 驗證（頂層 `{"generated_at": str, "tools": [...]}`；tool＝`{id, name, versions:[{version, period, items:[{title:{5語}, body:{5語}, original:str}]}]}`）。改 schema＝破壞所有已發佈 app，禁止。
- 五語 key：`zh-TW` `zh-CN` `en` `ja` `ko`。
- `data/raw` 檔：`{"version": str, "period": str, "source_url": str, "fetched_at": ISO日期, "entries": [str, ...]}`，entries 逐字原文。
- Antigravity 顯示名是 **Antigravity**，不是 agy（id 可留 `agy`）。

## 白話層（curated）

curated 內容由維護者離線撰寫與審核後合入；本 repo 只定義資料格式（見 Schema 鐵則），不包含撰寫方法。

## usage 端後續改動（另案，在 usage repo 做，不歸本 repo 工人管）

- 新增「AI 更新日報」面板（更換面板選單）：吃本 repo 的 `daily.json`（raw URL＋本機快取），每天自動有新內容。
- HTML 報告裡的 `_render_ai_updates_section` 區塊整個移除（功能獨立成面板＋網頁後，報告不再重複）。
- `ai_updates.json` 同步回 usage repo 仍要做：**只為了已發佈的舊版 app**（它們還在渲染報告區塊）。

## 網頁需求

- **視覺已定案：`drafts/draft2.html`（開發者 changelog timeline 風）是權威視覺依據**——正式 `docs/index.html` 照它復刻版面、配色、字體、間距，只把內嵌假資料換成讀 `docs/data.json`＋補五語切換；不得憑文字描述重新發明視覺。
- 靜態、無後端；資料來自同 repo 的 `docs/data.json`（build 產）。
- 首屏：四工具最新版速報（白話卡片，item 之間明確視覺分隔）。
- 歷史：每工具可展開／切換的版本 timeline，白話版沒有的舊版本顯示原文。
- 五語切換（跟 usage 同五語），預設跟瀏覽器語言。
- 響應式（responsive），手機可讀。
