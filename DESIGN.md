---
version: alpha
name: AI Updates
description: AI 工具更新速報的暖紙色版面規格；首頁、版本頁與 404 共用字級、控制項及色票。
colors:
  background: "#EEEBE6"
  sidebar: "#EEEBE6"
  card: "#F4F2EE"
  code: "#EEEBE6"
  soft-surface: "#EEEBE6"
  border: "#D9D5CF"
  item-rule: "#D9D5CF"
  text: "#141414"
  text-bright: "#141414"
  muted: "#6E6A65"
  primary: "#E5484D"
  on-primary: "#F1EEE8"
  primary-soft: "#F4F2EE"
  link: "#141414"
  tag-new: "#D97757"
  tag-fix: "#4E5560"
  tag-perf: "#5FAE8C"
  serial-start: "#8A857F"
  selected: "#141414"
  selected-dark: "#F1EEE8"
  signal-red: "#E5484D"
  moon-yellow: "#F2C14E"
  background-dark: "#121419"
  sidebar-dark: "#121419"
  card-dark: "#1A1E27"
  code-dark: "#121419"
  soft-surface-dark: "#121419"
  border-dark: "#2A2F3B"
  text-dark: "#F1EEE8"
  text-bright-dark: "#F1EEE8"
  muted-dark: "#A29E98"
  primary-dark: "#E5484D"
  on-primary-dark: "#141414"
  primary-soft-dark: "#1A1E27"
  link-dark: "#F1EEE8"
  tag-new-dark: "#D97757"
  tag-fix-dark: "#A29E98"
  tag-perf-dark: "#5FAE8C"
  serial-start-dark: "#6B7180"
typography:
  display:
    fontFamily: Space Grotesk
    fontSize: 6rem
    fontWeight: 500
    lineHeight: 1.05
  serial:
    fontFamily: Space Grotesk
    fontSize: 2.25rem
    fontWeight: 500
    lineHeight: 1
  title:
    fontFamily: Inter
    fontSize: 1.75rem
    fontWeight: 500
    lineHeight: 1.4
  heading:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: 500
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
    fontSize: 0.75rem
    fontWeight: 500
rounded:
  sm: 4px
  md: 8px
  code: 12px
  soft: 14px
  card: 26px
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
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
  badge-fix:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
  badge-perf:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
  filter-chip:
    backgroundColor: transparent
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    height: 32px
  filter-chip-active:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
  tab-button:
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    height: 44px
  tab-button-active:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
  tool-button-active:
    backgroundColor: "{colors.selected}"
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

網站用暖紙色背景、固定側欄與瑞士網格。主內容保留足夠留白，更新卡片與歷史卡片使用實心表面。淺色用暖灰邊框；深色用炭黑底與灰色邊框分層。背景沒有光暈，元件不加陰影或毛玻璃。四組主題色分別是預設深色、系統淺色、手動淺色、手動深色；上方 YAML 的值直接對應 CSS。

`--text-color` 用於正文，`--text-bright` 用於標題，`--muted-color` 用於日期與輔助文字，`--link-color` 用於連結。實心膠囊的選中狀態使用 `--selected-gradient`（保留既有名稱，值為單色），文字使用 `--accent-contrast`。`--serial-1` 專供大序號；類型徽章只在圓點上顯示類型色，文字與邊框用中性色。最新發布用紅點加文字，月亮圖示用黃色。

## 字體與中文排版

Inter 承載標題、導覽和中文內文；數字用 Space Grotesk，字重 500，日期維持 400。JetBrains Mono 只用在程式碼。Space Grotesk 的 400、500 字重以本機字型載入，不新增預載。字級限用七個 `--fs-*`：`--fs-2xs` 12px、`--fs-xs` 12px、`--fs-sm` 13px、`--fs-base` 15px、`--fs-md` 16px、`--fs-lg` 18px、`--fs-xl` 22px。版本大標、更新標題和大序號可用 `clamp()` 隨寬度縮放。中文字最小 12px；含中文的元素不加字距、不套大寫。長段中文行距 1.7～1.9。英文專用字距寫在 `:lang(en)` 規則；純數字的版本與序號可用負字距。內文保留原有換行設定，句末標點可懸掛在行尾。行內程式碼用 inline-block（行內區塊），可在過長時斷行；不用禁止換行。側欄短文在空格與標點後斷行，文字靠左。

## 版面與元件

- 桌機側欄固定 280px，主內容最多 880px；內容區沒有左右直導引線。卡片內是 64px 序號欄、20px 欄距與正文欄；序號下放類型膠囊。1023px 以下改成單欄，600px 以下縮小內距。
- 更新卡、歷史手風琴卡、Usage App 卡片與搜尋結果使用 26px 圓角、`--glass-fill` 與 `--glass-border`；兩個變數保留既有名稱，值為實心卡片色與一般邊框色。桌機與手機都不使用毛玻璃。卡片 hover 不位移。
- 比喻框是 14px 圓角的暖紙色實心區塊，內文行距 1.8。原始 CHANGELOG 使用 12px 圓角、有框的程式碼底。行內程式碼 4px，搜尋框 8px，一般小按鈕 8px，選中工具、分頁、篩選與徽章使用完整膠囊。
- 側欄 Usage App 卡片使用可見的 `--border-color`；搜尋框、搜尋結果、分享選單與回到頂端按鈕也使用實心表面。點擊區使用 `--control-sm` 32px、`--control-md` 36px、`--control-lg` 44px；手機控制項至少 44px。
- 版本頁與 404 共用 `scripts/build.py` 的 `PAGE_CSS`、四組主題色與實心卡片。版本大標用 Space Grotesk，字重 500。404 以一般連結與按鈕導回首頁、RSS 和工具頁。

## 保留的互動

工具清單依資料順序固定；切換工具或版本不重排清單。搜尋至少輸入兩字後才載入索引，結果最多 30 筆。篩選 chip 顯示數量；0 筆類型停用，已選中的仍可取消。企業／團隊向開關預設關閉，與類型篩選獨立。保留語言、主題、RSS、分享、歷史展開、錨點、回到頂端與跳到主要內容連結。

跨頁導覽用 `@view-transition`；支援 `animation-timeline:view()` 時卡片可輕微進場。`prefers-reduced-motion: reduce` 會停用轉場和進場。首頁 CSS 與 `PAGE_CSS` 的字級和主題變數須同步；改完執行 `python3 scripts/build.py` 與 `python3 -m pytest -q`。
