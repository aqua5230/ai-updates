---
version: alpha
name: AI Updates
description: AI 工具更新速報的藍色柔光版面規格；首頁、版本頁與 404 共用字級、控制項及色票。
colors:
  background: "#ffffff"
  sidebar: "#ffffff"
  card: "rgb(255 255 255 / 70%)"
  code: "#f6f9fc"
  soft-surface: "#f6f9fc"
  border: "#d8e3ee"
  item-rule: "#e5edf5"
  text: "#425466"
  text-bright: "#061b31"
  muted: "#586a82"
  primary: "#2563eb"
  on-primary: "#ffffff"
  primary-soft: "#eff6ff"
  link: "#2156ca"
  tag-new: "#087a56"
  tag-fix: "#b13f43"
  tag-perf: "#925b08"
  serial-start: "#1575a2"
  serial-mid: "#2563c9"
  serial-end: "#4158bc"
  background-dark: "#0a2540"
  sidebar-dark: "#0a2540"
  card-dark: "rgb(10 37 64 / 69%)"
  code-dark: "#102e4e"
  soft-surface-dark: "#173b62"
  border-dark: "#31516f"
  text-dark: "#bed0e4"
  text-bright-dark: "#ffffff"
  muted-dark: "#aac0d8"
  primary-dark: "#2563eb"
  on-primary-dark: "#ffffff"
  primary-soft-dark: "#243f75"
  link-dark: "#93c5fd"
  tag-new-dark: "#85d9bc"
  tag-fix-dark: "#ffa99e"
  tag-perf-dark: "#f9cf82"
  serial-start-dark: "#50c7f1"
  serial-mid-dark: "#4dacf6"
  serial-end-dark: "#6d9aff"
typography:
  display:
    fontFamily: Inter
    fontSize: 6rem
    fontWeight: 300
    lineHeight: 1
  serial:
    fontFamily: Inter
    fontSize: 2.25rem
    fontWeight: 300
    lineHeight: 1
  title:
    fontFamily: Inter
    fontSize: 1.75rem
    fontWeight: 600
    lineHeight: 1.4
  heading:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: 600
  body-lead:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.8
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
  code: 12px
  soft: 14px
  card: 20px
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
    padding: 2rem
  analogy:
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.soft}"
    padding: 1rem
  badge-new:
    textColor: "{colors.tag-new}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
  badge-fix:
    textColor: "{colors.tag-fix}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
  badge-perf:
    textColor: "{colors.tag-perf}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
  filter-chip:
    backgroundColor: "{colors.soft-surface}"
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
  search-input:
    backgroundColor: "{colors.card}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    height: 44px
  small-button:
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    height: 32px
---
# AI Updates 設計規格

## 方向與顏色

網站用藍色柔光背景、固定側欄與瑞士網格。主內容保留足夠留白，更新卡片與歷史卡片使用同一種毛玻璃表面。淺色卡有淡藍邊框；深色卡靠亮度與半透明邊框分層。四組主題色分別是預設深色、系統淺色、手動淺色、手動深色；上方 YAML 的值直接對應 CSS。

`--text-color` 用於正文，`--text-bright` 用於標題，`--muted-color` 用於日期與輔助文字，`--link-color` 用於連結。藍色漸層的選中狀態使用 `--selected-gradient`，文字使用 `--accent-contrast`。`--serial-1/2/3` 專供大序號，淺色與深色各色標對卡片底至少 3:1。內文和控制項文字對比至少 4.5:1。

## 字體與中文排版

Inter 承載標題、導覽和中文內文；JetBrains Mono 只用在程式碼。字級限用七個 `--fs-*`：`--fs-2xs` 11px、`--fs-xs` 12px、`--fs-sm` 13px、`--fs-base` 15px、`--fs-md` 16px、`--fs-lg` 18px、`--fs-xl` 22px。版本大標、更新標題和大序號可用 `clamp()` 隨寬度縮放。中文字最小 12px；含中文的元素不加字距、不套大寫。長段中文行距 1.7～1.9。英文專用字距只寫在 `:lang(en)` 規則。

## 版面與元件

- 桌機側欄固定 280px，主內容最多 880px；內容區沒有左右直導引線。卡片內是 64px 序號欄、20px 欄距與正文欄；序號下放類型膠囊。1023px 以下改成單欄，600px 以下縮小內距。
- 更新卡與歷史手風琴卡使用 20px 圓角、`--glass-fill`、`--glass-border` 與 `--glass-shadow`。手機不使用卡片的 `backdrop-filter`，保留相同填色和邊框。卡片 hover 不位移。
- 比喻框是 14px 圓角的淡藍漸層區塊，內文行距 1.8。原始 CHANGELOG 使用 12px 圓角、有框的程式碼底。行內程式碼 4px，搜尋框 8px，一般小按鈕 8px，選中工具、分頁、篩選與徽章使用完整膠囊。
- 側欄 Usage App 卡片使用可見的 `--border-color`；搜尋框、搜尋結果、分享選單與回到頂端按鈕也延續毛玻璃外觀。點擊區使用 `--control-sm` 32px、`--control-md` 36px、`--control-lg` 44px；手機控制項至少 44px。
- 版本頁與 404 共用 `scripts/build.py` 的 `PAGE_CSS`、四組主題色、背景光暈與卡片。版本大標用 Inter 細字重。404 以一般連結與按鈕導回首頁、RSS 和工具頁。

## 保留的互動

工具清單依資料順序固定；切換工具或版本不重排清單。搜尋至少輸入兩字後才載入索引，結果最多 30 筆。篩選 chip 顯示數量；0 筆類型停用，已選中的仍可取消。企業／團隊向開關預設關閉，與類型篩選獨立。保留語言、主題、RSS、分享、歷史展開、錨點、回到頂端與跳到主要內容連結。

跨頁導覽用 `@view-transition`；支援 `animation-timeline:view()` 時卡片可輕微進場。`prefers-reduced-motion: reduce` 會停用轉場和進場。首頁 CSS 與 `PAGE_CSS` 的字級和主題變數須同步；改完執行 `python3 scripts/build.py` 與 `python3 -m pytest -q`。
