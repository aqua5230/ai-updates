---
version: alpha
name: AI Updates
description: AI 工具更新速報的「深海琥珀」版面規格；首頁、版本頁與 404 共用字級、控制項及色票。
colors:
  background: "#F3F6FA"
  sidebar: "#F3F6FA"
  card: "#FFFFFF"
  code: "rgba(29,78,216,.08)"
  soft-surface: "#E8EEF6"
  border: "#D5DFEE"
  item-rule: "#D5DFEE"
  text: "#334155"
  text-bright: "#091526"
  muted: "#4E6078"
  primary: "#1D4ED8"
  on-primary: "#FFFFFF"
  primary-soft: "rgba(29,78,216,.08)"
  link: "#0369A1"
  tag-new: "#047857"
  tag-fix: "#BE123C"
  tag-perf: "#B45309"
  background-dark: "#040B16"
  sidebar-dark: "#040B16"
  card-dark: "#0B1628"
  code-dark: "rgba(56,189,248,.12)"
  soft-surface-dark: "#070F1E"
  border-dark: "#1B2D48"
  text-dark: "#CBD5E1"
  text-bright-dark: "#F8FAFC"
  muted-dark: "#8FA0B8"
  primary-dark: "#38BDF8"
  on-primary-dark: "#04111F"
  primary-soft-dark: "rgba(56,189,248,.12)"
  link-dark: "#60A5FA"
  tag-new-dark: "#34D399"
  tag-fix-dark: "#FB7185"
  tag-perf-dark: "#FBBF24"
  tool-surface: "#E8EEF6"
  analogy-text: "#334155"
  analogy-start: "rgba(217,119,6,.06)"
  analogy-border: "#D97706"
  analogy-label: "#B45309"
  inline-code-fill: "rgba(29,78,216,.08)"
  inline-code-border: "rgba(29,78,216,.2)"
  tool-surface-dark: "#070F1E"
  analogy-text-dark: "#CBD5E1"
  analogy-start-dark: "rgba(245,158,11,.08)"
  analogy-border-dark: "#F59E0B"
  analogy-label-dark: "#F59E0B"
  inline-code-fill-dark: "rgba(56,189,248,.12)"
  inline-code-border-dark: "rgba(56,189,248,.25)"
typography:
  display:
    fontFamily: Plus Jakarta Sans
    fontSize: 3rem
    fontWeight: 700
    lineHeight: 1.1
  serial:
    fontFamily: Geist Mono
    fontSize: 1.125rem
    fontWeight: 600
    lineHeight: 1.4
  title:
    fontFamily: Plus Jakarta Sans
    fontSize: 1.375rem
    fontWeight: 600
    lineHeight: 1.4
  heading:
    fontFamily: Plus Jakarta Sans
    fontSize: 1.125rem
    fontWeight: 600
  body-lead:
    fontFamily: Plus Jakarta Sans
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.75
  body:
    fontFamily: Plus Jakarta Sans
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.75
  ui:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.8125rem
    fontWeight: 500
  label:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.75rem
    fontWeight: 500
  caption:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.6875rem
    fontWeight: 500
  analogy:
    fontFamily: Plus Jakarta Sans
    fontSize: 0.9375rem
    fontWeight: 400
    lineHeight: 1.7
rounded:
  sm: 4px
  md: 8px
  code: 12px
  soft: 14px
  card: 14px
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
    padding: 24px 28px
  analogy:
    textColor: "{colors.text}"
    typography: "{typography.analogy}"
    rounded: 0 8px 8px 0
    padding: 12px 16px
  badge-new:
    textColor: "{colors.tag-new}"
    typography: "{typography.ui}"
    rounded: "{rounded.full}"
  badge-fix:
    textColor: "{colors.tag-fix}"
    typography: "{typography.ui}"
    rounded: "{rounded.full}"
  badge-perf:
    textColor: "{colors.tag-perf}"
    typography: "{typography.ui}"
    rounded: "{rounded.full}"
  filter-chip:
    backgroundColor: "{colors.soft-surface}"
    typography: "{typography.ui}"
    rounded: "{rounded.full}"
    height: 32px
  filter-chip-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
  tab-button:
    typography: "{typography.ui}"
    rounded: "{rounded.md}"
    height: 44px
  tab-button-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
  tool-button-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.ui}"
    rounded: "{rounded.md}"
    height: 44px
  search-input:
    backgroundColor: "{colors.card}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    height: 44px
  small-button:
    typography: "{typography.ui}"
    rounded: 6px
    height: 32px
---
# AI Updates 設計規格

## 方向與顏色

風格名稱「深海琥珀」。深色底為 `#040B16`，卡片為實心 `#0B1628`；淺色底為 `#F3F6FA`，卡片為白色。卡片靠色階、細框與內外陰影分層。頁面頂端保留一道高度 120px 的淡青色徑向漸層，深色透明度 .16，淺色 .10。所有寬度都不使用背景模糊。

四組主題分別是預設深色、系統淺色、手動淺色、手動深色。`--text-color` 用於正文，`--text-bright` 用於標題，`--muted-color` 用於日期與輔助文字，`--link-color` 用於連結。選中工具、分頁、篩選與開關共用 `--accent-color`；深色為 `#38BDF8`，文字為 `#04111F`，淺色為 `#1D4ED8`，文字為白色。`--selected-gradient` 的起訖同色。分類標籤底色用各分類色的 12%。

## 字體與中文排版

Plus Jakarta Sans 承載標題、導覽與英文內文；Geist Mono 用於序號、日期與程式碼。中文依序使用 PingFang TC、Noto Sans TC、Microsoft JhengHei，再回退系統字型。本機字型分 latin 與 latin-ext，使用 `font-display:swap`；可變字重分別為 200–800 與 100–900。

字級限用七個 `--fs-*`：`--fs-2xs` 11px、`--fs-xs` 12px、`--fs-sm` 13px、`--fs-base` 15px、`--fs-md` 16px、`--fs-lg` 18px、`--fs-xl` 22px。11px 只用於工具版本號與搜尋快捷鍵等非中文文字。中文字最小 12px；含中文的元素不加字距、不套大寫。大版本號保留 `clamp()` 寫法，固定為 3rem、700、行距 1.1，使用等寬數字與 -.03em 字距。卡片標題用最接近原型 20px 的既有 22px token（共用值）、600、行距 1.4。正文 16px、400、行距 1.75；比喻 15px、400、行距 1.7；標籤和小按鈕 13px、500。

## 版面與元件

- 桌機側欄固定 280px，主內容最多 880px；內容區沒有左右直導引線。卡片表頭一列放序號、標題與類型膠囊，正文直接對齊卡片左緣。1023px 以下改成序號、膠囊一列，標題自成一列。
- 更新卡與歷史卡用 14px 圓角、`--card-bg`、`--border-color` 與 `--glass-shadow`（深色 `inset 0 1px 0 0 rgba(255,255,255,.07), 0 8px 24px -4px rgba(0,0,0,.4)`，淺色 `inset 0 1px 0 0 #fff, 0 6px 20px -6px rgba(15,23,42,.12)`）。桌機內距 24px 28px，1023px 以下 20px；歷史卡由標頭與內容各自承接內距。卡片滑過不位移，首頁不播放卡片進場動畫。
- 比喻框用琥珀色 3px 左線、向右淡出的暖色底、`0 8px 8px 0` 圓角、12px 16px 內距與 16px 上下間距。深色左線 `#F59E0B`，淺色 `#D97706`。偽元素依 `:lang()` 顯示「比喻」或「Analogy」，12px、600；後接的第一段加虛線和 12px 上內距。
- 行內程式碼用 `--inline-code-fill`、`--inline-code-border`、`--accent-color`，5px 圓角、2px 6px 內距，字級用最接近原型 14px 的既有 13px token。「原始 CHANGELOG」展開後保留有框的程式碼區塊。
- 工具清單與頁籤外框為 12px 圓角，背景 `--tool-surface`；工具清單內距 4px，手機左右外距 1rem。工具按鈕與頁籤為 8px 圓角。分類標籤與篩選按鈕維持膠囊。「最新發布」為純文字，前置靜態 6px 綠點。
- 搜尋框、搜尋結果、分享選單與回到頂端按鈕使用實心卡片色。搜尋框與搜尋結果不加陰影。複製、分享與程式碼複製按鈕為 6px 圓角；回到頂端、手機主題按鈕與通知為 8px。點擊區使用 `--control-sm` 32px、`--control-md` 36px、`--control-lg` 44px；手機控制項至少 44px。
- 版本頁與 404 共用 `scripts/build.py` 的 `PAGE_CSS`、四組主題、頂端漸層與卡片。版本大標用 Plus Jakarta Sans、700、等寬數字。404 透過連結導回首頁、RSS 和工具頁。

## 保留的互動

工具清單依資料順序固定；切換工具或版本不重排清單。搜尋至少輸入兩字後才載入索引，結果最多 30 筆。篩選 chip 顯示數量並帶類型色圓點；0 筆類型停用，已選中的仍可取消。分類 chip 右側以分隔線隔開三個 switch 開關，一律用正向說法：顯示企業／團隊向（附篇數，0 篇時停用）、顯示比喻，預設開；展開全部原文，預設關。只有比喻開關記在 localStorage。版本日期旁顯示「網站同步」日期；最新版本最後一則下方有「上一版」按鈕。英文術語後的全形括號白話解釋用 `--muted-color` 淡化。1023px 以下標題列右上放深淺色切換鈕。

桌機 1400px 以上，最新版本分頁右側顯示固定目錄，捲動時標示目前這則；歷史分頁不顯示。卡片序號是按鈕，複製版本靜態頁的 `#card-N` 連結（N 是原始序號，篩選後仍對得上）。行內程式碼點擊或按 Enter 複製，提示用畫面底部的小浮標，並寫入 `#sr-status`。側欄工具有新版本時亮小圓點：第一次造訪只記錄不亮，看過即消失。快捷鍵：`/` 搜尋、`j`／`k` 上下一則、`o` 展開原文；輸入框內、組字中、帶 Ctrl／Cmd／Alt 時不攔。站內目錄與快捷鍵用 `scrollIntoView`，不改網址 hash。保留語言、主題、RSS、分享、歷史展開、錨點、回到頂端與跳到主要內容連結。

跨頁導覽用 `@view-transition`；版本頁支援 `animation-timeline:view()` 時卡片可輕微進場，首頁維持靜態。`prefers-reduced-motion: reduce` 會停用轉場和進場。首頁 CSS 與 `PAGE_CSS` 的字級和主題變數須同步；改完執行 `python3 scripts/build.py` 與 `python3 -m pytest -q`。
