---
version: alpha
name: AI_UPDATES.LOG
description: AI 工具更新速報的清爽科技站介面規格；首頁、版本頁與 404 共用字級、控制項及色票。
colors:
  background: "oklch(0.975 0.003 240)"
  sidebar: "oklch(1 0 0)"
  card: "oklch(1 0 0)"
  code: "oklch(0.955 0.004 240)"
  soft-surface: "oklch(0.96 0.003 240)"
  border: "oklch(0.905 0.006 240)"
  text: "oklch(0.34 0.012 240)"
  text-bright: "oklch(0.18 0.008 240)"
  muted: "oklch(0.43 0.01 240)"
  primary: "oklch(0.18 0.008 240)"
  on-primary: "oklch(1 0 0)"
  link: "oklch(0.37 0.05 240)"
  tag-new: "oklch(0.43 0.01 240)"
  tag-fix: "oklch(0.43 0.01 240)"
  tag-perf: "oklch(0.43 0.01 240)"
  background-dark: "oklch(0.18 0.005 240)"
  sidebar-dark: "oklch(0.22 0.005 240)"
  card-dark: "oklch(0.25 0.005 240)"
  code-dark: "oklch(0.30 0.005 240)"
  soft-surface-dark: "oklch(0.30 0.005 240)"
  border-dark: "oklch(0.36 0.005 240)"
  text-dark: "oklch(0.86 0.005 240)"
  text-bright-dark: "oklch(0.97 0.003 240)"
  muted-dark: "oklch(0.73 0.005 240)"
  primary-dark: "oklch(0.96 0.003 240)"
  on-primary-dark: "oklch(0.18 0.005 240)"
  link-dark: "oklch(0.84 0.025 240)"
  tag-new-dark: "oklch(0.73 0.005 240)"
  tag-fix-dark: "oklch(0.73 0.005 240)"
  tag-perf-dark: "oklch(0.73 0.005 240)"
typography:
  display:
    fontFamily: Inter
    fontSize: 4rem
    fontWeight: 500
  title:
    fontFamily: Inter
    fontSize: 1.375rem
    fontWeight: 600
    lineHeight: 1.5
  heading:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: 500
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
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: 500
  label:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: 500
  caption:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: 500
rounded:
  sm: 4px
  md: 8px
  code: 10px
  soft: 12px
  card: 16px
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
    rounded: "{rounded.card}"
    padding: 1.75rem
  card-compact:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
    padding: 1.75rem
  badge-new:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
  badge-fix:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
  badge-perf:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
  filter-chip:
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    height: 32px
  filter-chip-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
  tab-button:
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    height: 44px
  tab-button-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
  tool-button-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.ui}"
    rounded: "{rounded.full}"
    height: 44px
  small-button:
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    height: 32px
---

# AI_UPDATES.LOG 設計規格

## Overview

清爽科技站使用冷灰白頁底、白色側欄與卡片、近黑文字。Inter 承載標題、導覽與中文內文；等寬字只用在數字和程式碼。工具、分頁與篩選的選中狀態都是近黑實心膠囊配白字。深色模式用近黑中性底、略亮的卡片與近白膠囊。

## Colors

- 淺色四層：頁底 `--bg-color`、白色 `--sidebar-bg`／`--card-bg`、淡灰 `--soft-surface`、程式碼底 `--code-bg`。
- 深色底與卡片的色相約 240、彩度 0.005；卡片和軟底逐層變亮。深色沒有可見卡片陰影。
- `--text-color` 放內文；`--text-bright` 放標題；`--muted-color` 放日期、序號、徽章與輔助文字。連結使用 `--link-color`。
- `--tag-new`、`--tag-fix`、`--tag-perf` 三者在各主題完全相同，更新類型不靠顏色區分。
- `:root` 與 `[data-theme="dark"]` 同色；`@media(prefers-color-scheme:light)` 與 `[data-theme="light"]` 同色。文字與所處底色的 WCAG 對比至少 4.5:1，改完用 axe 的 `color-contrast` 驗。含字的控制項不用 `opacity` 淡化。
- 顏色一律寫 token，要半透明就用 `color-mix(in srgb,var(--token) N%,transparent)`，不寫死 `rgba()`／`#hex`。

## Typography

CSS 裡的字級一律寫 `var(--fs-*)`，共七級：

| token | 值 | 用在哪 |
|---|---|---|
| `--fs-2xs` | 11px | 英文與數字：版本小字、計數 |
| `--fs-xs` | 12px | 標籤、按鈕、篩選 chip、說明文字 |
| `--fs-sm` | 13px | 工具名稱、日期、比喻框、程式碼 |
| `--fs-base` | 15px | 卡片內文 |
| `--fs-md` | 16px | 導言、歷史展開內的卡片標題、緊湊卡標題 |
| `--fs-lg` | 18px | 歷史版本標題、版本頁段落標題 |
| `--fs-xl` | 22px | 最新版本卡片標題 |

- 唯一字級例外是版本號大標的 `clamp()`；行內程式碼、程式碼框與比喻框也使用 `--fs-*`。
- 中文排版照 W3C clreq：會換行的中文內文與說明文字，行距（`line-height`）落在 1.5～2.0；中文不加字距（密排），字距只寫在 `:lang(en)` 規則裡；中文最小用 `--fs-xs`（12px），`--fs-2xs` 只給英文與數字；介面文字的冒號跟著語言走（繁中全形「：」）。`font` 簡寫會把行距重設成 `normal`，簡寫後面要明寫 `line-height`。
- 標題層級：外層標題一定比裡面的標題大。歷史版本標題用 `--fs-lg`，所以展開內容的卡片標題用 `--fs-md`。
- 頁面標題順序不跳級：`h1`（logo 或頁名）→ `h2`（版本號，歷史分頁用隱藏的 `h2`）→ `h3`（卡片標題）。
- 字體自架在 `docs/fonts/`（Inter、JetBrains Mono 可變字型，latin 與 latin-ext 子集，OFL 授權），`font-display:swap`，不再連 Google Fonts。

## Layout

- 桌機側欄固定 280px；主內容使用寬鬆內距，最寬 1100px。版本頁正文最寬 46rem。
- 1023px 以下工具列橫向捲動、觸控控制項至少 44px；600px 以下主內容縮小內距。頁面不出現整頁橫向捲軸。
- 首頁卡片的序號是徽章前的小灰字；沒有時間軸軌道與圓點。版本頁使用相同卡片、字體、比喻框與程式碼框。
- 搜尋結果、分享選單、歷史手風琴、企業／團隊開關與卡片錨點沿用既有互動。

## Elevation & Depth

淺色卡片使用極淡、範圍較大的陰影；hover 只改陰影，不移動卡片。深色卡片靠底色亮度分層，陰影 token 是透明。分享選單可用陰影表示浮在內容上方。卡片進場只動 `translate`。

## Shapes

- 16px：更新卡片與歷史版本卡。
- 12px：比喻框、原始 CHANGELOG 區、側欄 Usage App 卡。
- 10px：搜尋框、結果面板與程式碼框。
- 8px：設定與一般小按鈕。
- 4px：行內程式碼。
- 999px：工具、分頁、篩選 chip、最新發布標記。

## Components

- 更新卡片白底、無邊框、圓角 16px，內距 1.75rem。一般標題 `--fs-xl`，緊湊卡與歷史展開內標題 `--fs-md`。
- 工具與分頁選中狀態為 `--accent-color` 實心底與 `--accent-contrast` 字；深色主題兩者互換亮暗。分頁和工具都維持 44px 觸控高度。
- 篩選 chip 桌機高 32px、1023px 以下高 44px、字級 `--fs-xs`，選中同樣使用實心膠囊；類型徽章是沒有框與圖示的中性灰小字。企業／團隊徽章與隱藏開關使用同一套中性灰。
- 最新發布標記為實心小膠囊。比喻框使用淡灰底與 12px 圓角，不加左色條。原始 CHANGELOG 摺疊區也用淡灰底與 12px 圓角。
- 版本頁麵包屑用 Inter 小字、深灰連結；版本大標用 Inter 500。404 與版本頁共用 `PAGE_CSS`；404 的圖示和字體使用絕對網址。
- **工具清單**：依資料順序固定排列，點擊不重排。
- **篩選 chip 計數**：標籤後用數字顯示目前版本的各類卡片數，切換工具或版本時同步更新。0 張卡的類型 chip 停用（muted 色），但已選中的仍可點掉。
- **企業／團隊向**：`data.json` 的 `enterprise` 卡片序號標出，徽章放在類型徽章旁；「隱藏企業／團隊向」是獨立開關，預設關、不寫入 localStorage，與類型 chip 互不影響。
- **搜尋框**：放在主內容區最上方、分頁列之上，高度 `--control-lg`、字級 `--fs-base`；第一次聚焦或輸入才載入 `search-index.json`，至少 2 個字元才搜。結果面板貼在輸入框下方、最多 30 筆，第一行（`aria-live="polite"`）顯示筆數，連結到靜態版本頁的 `#card-<n>`（英文介面連到 `/en/`）。按 Esc 收起面板。
- **分享選單**：浮在按鈕下方，不推擠版面；超出視窗時改從左側對齊。
- **側欄設定按鈕**：主題與複製 RSS 按鈕用 16px 行內 SVG 加文字；主題依目前模式顯示太陽或月亮，RSS 固定顯示 RSS 圖示。
- **回到頂端按鈕**：捲過兩個螢幕高才以 fixed 顯示在右下角，44px 正方形、只放箭頭圖示（文字放 `aria-label` 與 `title`），並避開 safe area。
- **跳到主要內容連結**：`<body>` 第一個可聚焦元素，平常藏在視窗上緣外，取得焦點時滑入左上角，高度 `--control-lg`。
- **版本頁麵包屑**：`AI_UPDATES.LOG / 工具名 / 版本號`，連結高度至少 24px（axe `target-size`）。
- **404 錯誤資訊**：保留中英文說明、回首頁和訂閱 RSS；內容卡先顯示 `ERR 404  route not found` 與閃爍方塊游標，再列五個工具的首頁 hash 連結。
- 資料載入前，1023px 以下先保留工具列高度與一個螢幕高的主內容，避免版面跳動（CLS）。

## Do's and Don'ts

- Do：新增字級使用七個 `--fs-*`；控制項高度使用 `--control-sm`（32px）、`--control-md`（36px）、`--control-lg`（44px）。
- Do：中文不加字距；英文需要字距時只寫在 `:lang(en)` 規則。會換行的中文內文行距維持 1.5～2.0。
- Do：改首頁 CSS 時同步改 `scripts/build.py` 的 `PAGE_CSS`，再跑 `python3 scripts/build.py`。
- Do：保留 RSS、skip link、語言與主題切換、搜尋、歷史手風琴、分享、錨點與 `prefers-reduced-motion`。
- Do：跨頁導覽用 `@view-transition{navigation:auto}` 淡入淡出；首頁內切換工具或版本不套轉場。
- Do：`.log-item-card` 在支援 `animation-timeline:view()` 時由下移 12px 滑至原位，範圍 `entry 0% entry 35%`。只動畫獨立的 `translate`，不動 `transform` 與 `opacity`（半透明的字會被 Lighthouse／axe 判成對比不足）；首屏卡片維持完整狀態。
- Do：`prefers-reduced-motion: reduce` 時關閉跨頁轉場、卡片進場及 404 游標閃爍。
- Do：上線前跑 `python3 -m pytest -q`，並用 axe 檢查對比度、標題層級與點擊區；深色、淺色、手機 WebKit 都要截圖看過。
- Don't：讓點擊或載入改變已經在畫面上的內容位置。
- Don't：加彩色類型徽章、徽章圖示、時間軸軌道、卡片 hover 位移或中文大寫字距。
- Don't：寫死字級或把中文縮到 11px。
