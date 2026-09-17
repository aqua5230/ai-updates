---
version: alpha
name: AI_UPDATES.LOG
description: AI 工具更新速報的介面規格。首頁 docs/index.html 與版本頁模板 scripts/build.py 共用同一套 token。
colors:
  background: "oklch(0.940 0.005 247.858)"
  sidebar: "oklch(0.975 0.004 247.858)"
  card: "oklch(0.995 0.002 247.858)"
  code: "oklch(0.968260 0.006854 247.896)"
  border: "oklch(0.900 0.010 255.508)"
  text: "oklch(0.371696 0.039156 257.287)"
  text-bright: "oklch(0.207682 0.039824 265.755)"
  muted: "oklch(0.520 0.040717 257.417)"
  primary: "oklch(0.484000 0.215208 262.881)"
  on-primary: "oklch(1 0 0)"
  tag-new: "oklch(0.472000 0.137103 150.069)"
  tag-fix: "oklch(0.473000 0.215157 27.325)"
  tag-perf: "oklch(0.501000 0.145505 48.998)"
  background-dark: "oklch(0.176285 0.014021 258.357)"
  sidebar-dark: "oklch(0.220223 0.015700 256.816)"
  card-dark: "oklch(0.245223 0.015700 256.816)"
  code-dark: "oklch(0.159628 0.020332 265.576)"
  border-dark: "oklch(0.270223 0.014885 252.310)"
  text-dark: "oklch(0.856908 0.014132 247.992)"
  text-bright-dark: "oklch(0.970342 0.010275 247.932)"
  muted-dark: "oklch(0.662473 0.018141 250.922)"
  primary-dark: "oklch(0.715252 0.151810 253.306)"
  on-primary-dark: "oklch(0.176285 0.014021 258.357)"
  tag-new-dark: "oklch(0.695081 0.180928 145.621)"
  tag-fix-dark: "oklch(0.719000 0.204594 26.960)"
  tag-perf-dark: "oklch(0.719551 0.140145 79.915)"
typography:
  display:
    fontFamily: JetBrains Mono
    fontSize: 2.25rem
    fontWeight: 700
  title:
    fontFamily: Inter
    fontSize: 1.375rem
    fontWeight: 650
    lineHeight: 1.4
  heading:
    fontFamily: JetBrains Mono
    fontSize: 1.125rem
    fontWeight: 700
  body-lead:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.7
  body:
    fontFamily: Inter
    fontSize: 0.9375rem
    fontWeight: 400
    lineHeight: 1.8
  ui:
    fontFamily: JetBrains Mono
    fontSize: 0.8125rem
    fontWeight: 500
  label:
    fontFamily: JetBrains Mono
    fontSize: 0.75rem
    fontWeight: 700
  caption:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: 700
rounded:
  sm: 4px
  md: 6px
  lg: 8px
  full: 999px
spacing:
  2xs: 0.25rem
  xs: 0.5rem
  sm: 0.75rem
  md: 1rem
  lg: 1.5rem
  xl: 2rem
components:
  card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.lg}"
    padding: 1.5rem
  card-compact:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.lg}"
    padding: 1rem
  badge-new:
    textColor: "{colors.tag-new}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
  filter-chip:
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    height: 32px
  tab-button:
    typography: "{typography.ui}"
    rounded: "{rounded.sm}"
    height: 44px
  tab-button-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
  tool-button-active:
    textColor: "{colors.text-bright}"
    typography: "{typography.ui}"
    rounded: "{rounded.md}"
    height: 44px
  small-button:
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    height: 32px
---

# AI_UPDATES.LOG 設計規格

## Overview

像一份整理過的終端機日誌：等寬字標出結構（logo、版本號、標籤、按鈕），比例字承載內文。畫面安靜、扁平，只有一個藍色強調色；綠、紅、橘三個標籤色只用來分辨「新功能／問題修復／效能優化」。深色與淺色兩套主題地位相同，任何改動都要兩套一起看。

## Colors

- **background / sidebar / card**：三層底色由深到淺（淺色主題）或由暗到亮（深色主題），靠亮度差分層，不靠陰影。
- **text / text-bright / muted**：內文、標題、次要資訊三級。muted 只用在日期、序號、輔助說明。
- **primary**（CSS 變數 `--accent-color`）：唯一的互動色，用在選中的分頁、選中的工具、連結、時間軸圓點。
- **tag-new / tag-fix / tag-perf**：只用於更新類型標籤與篩選 chip，不拿來裝飾。
- 淺色值寫在 `:root[data-theme="light"]` 與 `@media(prefers-color-scheme:light)`，深色值寫在 `:root` 與 `:root[data-theme="dark"]`，名稱加 `-dark` 的 token 對應深色主題。
- 所有文字對背景的對比度至少 4.5:1（WCAG AA），調色時只動 OKLCH 的亮度，不動色相與彩度，改完用 axe 的 `color-contrast` 驗。

## Typography

CSS 裡的字級一律寫 `var(--fs-*)`，共七級：

| token | 值 | 用在哪 |
|---|---|---|
| `--fs-2xs` | 11px | 版本號小字、New 徽章、產生日期 |
| `--fs-xs` | 12px | 標籤、按鈕、篩選 chip、說明文字 |
| `--fs-sm` | 13px | 工具名稱、分頁按鈕、日期、比喻框 |
| `--fs-base` | 15px | 卡片內文 |
| `--fs-md` | 16px | 導言、歷史展開內的卡片標題、緊湊卡標題 |
| `--fs-lg` | 18px | logo、歷史版本標題 |
| `--fs-xl` | 22px | 最新版本卡片標題 |

- 例外只有兩種：跟著父層縮放的 `em`（行內程式碼、程式碼框、比喻框），以及版本號大標的 `clamp()`。
- 標題層級：外層標題一定比裡面的標題大。歷史版本標題用 `--fs-lg`，所以展開內容的卡片標題用 `--fs-md`。
- 頁面標題順序不跳級：`h1`（logo 或頁名）→ `h2`（版本號，歷史分頁用隱藏的 `h2`）→ `h3`（卡片標題）。
- 字體自架在 `docs/fonts/`（Inter、JetBrains Mono 可變字型，latin 與 latin-ext 子集，OFL 授權），`font-display:swap`，不再連 Google Fonts。

## Layout

- 桌機：左側固定側欄 280px，主內容區左右內距 4rem、最寬 1100px。
- 1023px 以下：側欄拆開，工具列變成單排可橫向捲動，設定區與 Usage App 卡片排到內容後面。
- 600px 以下：隱藏時間軸軌道與序號。
- 版本頁內容欄寬 46rem（內文實寬約 686px），一行約 45 個中文字。
- 間距優先用 `.25rem / .5rem / .75rem / 1rem / 1.5rem / 2rem`。
- 資料載入前，1023px 以下先保留工具列高度與一個螢幕高的主內容，避免版面跳動（CLS）。

## Elevation & Depth

整體扁平。卡片沒有陰影，靠底色與 1px 邊框分層；hover 只換邊框色並上移 2px。唯一的陰影在浮動的分享選單，用來表示它蓋在內容上面。不使用發光（box-shadow 光暈）與漸層背景。

## Shapes

- 4px：小按鈕、分頁按鈕、分頁滑塊、行內程式碼。
- 6px：工具按鈕、程式碼框、原始 CHANGELOG 摺疊區。
- 8px：卡片、歷史版本卡、分頁外框、Usage App 卡片。
- 999px：篩選 chip。
- 巢狀圓角 = 外層圓角 − 內距，例如分頁外框 8px、內距 4px，裡面就是 4px。

## Components

- **控制項高度**只用三級：`--control-sm` 32px（篩選 chip、複製連結／分享、原始 CHANGELOG 標題）、`--control-md` 36px（桌機設定區）、`--control-lg` 44px（工具按鈕、分頁按鈕、1023px 以下的所有設定按鈕）。
- **更新卡片**：一般卡內距 1.5rem、標題 `--fs-xl`；「問題修復」是緊湊卡，內距 1rem、標題 `--fs-md`、hover 不上移。
- **時間軸**：圓點與序號的垂直中心對齊卡片第一行的類型標籤；序號右緣離卡片至少 16px。
- **工具清單**：依資料順序固定排列，點擊不重排；選中的那顆用 accent 淡底加 accent 邊框。
- **分享選單**：浮在按鈕下方，不推擠版面；超出視窗時改從左側對齊。

## Do's and Don'ts

- Do：新增文字用 `--fs-*`，新增按鈕用 `--control-*`。
- Do：改 `docs/index.html` 的樣式時，同步改 `scripts/build.py` 的版本頁模板，再跑 `python3 scripts/build.py`。
- Do：上線前跑 `python3 -m pytest -q`（含 `tests/test_design_tokens.py`），並用 axe 檢查對比度與標題層級。
- Do：深色、淺色、手機 WebKit 都要截圖看過。
- Don't：加光暈、漸層背景、第二個強調色。
- Don't：寫死字級數字（例如 `font-size:.73rem`），測試會擋。
- Don't：讓點擊或載入改變已經在畫面上的內容位置。
