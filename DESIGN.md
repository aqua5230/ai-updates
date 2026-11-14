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
  tag-perf: "#6D28D9"
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
  tag-perf-dark: "#A78BFA"
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
    fontFamily: Plus Jakarta Sans
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
    backgroundColor: transparent
    rounded: 0
    borderTop: "1px solid {colors.border}"
    padding: 2rem 0 1.5rem
  analogy:
    textColor: "{colors.text}"
    typography: "{typography.analogy}"
    rounded: 0
    padding: 12px 16px
  badge-new:
    textColor: "{colors.tag-new}"
    typography: "{typography.ui}"
    rounded: 0
    backgroundColor: transparent
    border: 0
  badge-fix:
    textColor: "{colors.tag-fix}"
    typography: "{typography.ui}"
    rounded: 0
    backgroundColor: transparent
    border: 0
  badge-perf:
    textColor: "{colors.tag-perf}"
    typography: "{typography.ui}"
    rounded: 0
    backgroundColor: transparent
    border: 0
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
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.text-bright}"
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

風格名稱「深海琥珀」。深色底為 `#040B16`，淺色底為 `#F3F6FA`。更新卡以細線分隔，形成連續內容，不加底色、圓角或陰影。歷史摺疊區塊保留實心底色、外框與陰影。頁面頂端不放光暈。所有寬度都不使用背景模糊。

四組主題分別是預設深色、系統淺色、手動淺色、手動深色。`--text-color` 用於正文，`--text-bright` 用於標題，`--muted-color` 用於日期與輔助文字，`--link-color` 用於連結。選中工具使用 `--accent-glow` 淡底、標題亮色 `--text-bright` 與 `--text-color` 版本號，不加邊線或內陰影線；藍色主要留給選中工具、篩選膠囊與連結（switch 開關「開」的軌道用 `--text-bright`、圓鈕用 `--bg-color`）。`--selected-gradient` 的起訖同色。「最新版本／歷史版本」頁籤是次一層的切換，選中時用 `--accent-glow` 淡底配 `--text-bright` 文字，不和選中工具搶實心色。新功能、問題修復、效能優化標籤用各分類色文字，不加圓點、外框或底色。琥珀色只留給比喻框，效能優化標籤用紫色。

## 字體與中文排版

Plus Jakarta Sans 承載標題、導覽、序號、日期與英文內文（序號與日期使用等寬數字 `tabular-nums`）；Geist Mono 用於工具版本號、程式碼與搜尋快捷鍵。中文依序使用 PingFang TC、Noto Sans TC、Microsoft JhengHei，再回退系統字型。本機字型分 latin 與 latin-ext，使用 `font-display:swap`；可變字重分別為 200–800 與 100–900。

字級限用七個 `--fs-*`：`--fs-2xs` 11px、`--fs-xs` 12px、`--fs-sm` 13px、`--fs-base` 15px、`--fs-md` 16px、`--fs-lg` 18px、`--fs-xl` 22px。11px 只用於工具版本號與搜尋快捷鍵等非中文文字。中文字最小 12px；含中文的元素不加字距、不套大寫。首頁標題顯示「工具名＋空格＋版本號」。標題保留 `clamp()` 寫法，桌機為 3rem，600px 以下為 2rem；字重 700、行距 1.1，使用等寬數字，既有字距不變。卡片標題用最接近原型 20px 的既有 22px token（共用值）、600、行距 1.4。正文 16px、400、行距 1.75；比喻 15px、400、行距 1.7；標籤和小按鈕 13px、500。

## 版面與元件

- 桌機側欄固定 280px，主內容最多 880px；內容區沒有左右直導引線。卡片表頭一列放序號、標題與類型標籤；601px 以上正文與原文區向右縮排 2.75rem，對齊標題，比喻框前的文字整段當導言、不拆出第一句。600px 以下改成序號、類型標籤一列，標題自成一列。首頁正文最大寬度 42rem，版本頁不限。
- 更新卡只有 `1px solid var(--border-color)` 上分隔線，無底色、圓角或陰影；各尺寸內距皆為 `2rem 0 1.5rem`，外距為 0，滑過不變。歷史摺疊區塊保留 14px 圓角、`--card-bg`、`--border-color` 與 `--glass-shadow`；標頭與內容各用 24px 28px 內距，1023px 以下 20px。歷史內容沿用細線分隔。首頁不播放卡片進場動畫。
- 比喻框用琥珀色 3px 左線、無底色、0 圓角、12px 16px 內距與 16px 上下間距。深色左線 `#F59E0B`，淺色 `#D97706`。偽元素依 `:lang()` 顯示「比喻」或「Analogy」，12px、600；後接的第一段不加分隔線或上內距。
- 行內程式碼無外框（`border:0`），用 `--inline-code-fill` 底色與 `--text-bright` 文字（滑過底色略深，不用藍色外框），4px 圓角、1px 5px 內距，字級用最接近原型 14px 的既有 13px token（`--inline-code-border` 變數保留不刪）。「原始 CHANGELOG」展開後去框、去底色與圓角，改用 `--font-ui`、`--fs-base`、行距 1.7、`--muted-color`，左側加 `2px solid var(--border-color)` 細線、左內距 `1rem`、上下內距 `0`，並保留原文換行。展開指示（原始 CHANGELOG、歷史版本、版本頁原文）一律用 6px 線條箭頭：右框線加下框線轉 -45°，收合朝右、展開朝下。
- 工具清單與頁籤用透明外框、無底色。工具清單內距 4px，桌機 1024px 以上改為 0，左右外距 -14px；1024px 以上側欄底部拿掉可見的「語言：」標籤與下拉選單，將語言、深淺色、複製 RSS 收成一排三顆 36px 圖示按鈕（間距 8px、靠左，沿用 1023px 以下標題列按鈕樣式與圖示，並保留 `<select>` 的 `aria-label` 與按鈕 `aria-label`、`title`），Usage App 推廣縮成一行（圖示＋「Usage App」＋「New」），確保 800px 視窗高度完整顯示。頁籤內距 0、下方間距 1.25rem；桌機頁籤最小高度 36px、上下內距 .3rem。1023px 以下標題列、工具清單、主內容與頁尾共用 `--gutter` 左右邊線：主內容置中時跟著置中，至少 24px，600px 以下 20px，480px 以下 16px；工具清單和搜尋框間距 32px。工具清單左右 3rem 淡出遮罩只作用在內容，透明邊框範圍保持完整；可捲動方向顯示 28px 圓形線條箭頭按鈕，貼齊外框內側並垂直置中，每次捲動清單寬度的 70%，減少動態效果時直接捲動。搜尋框各寬度皆顯示左側 16px 放大鏡線條圖示。工具按鈕與頁籤為 8px 圓角。分類標籤用純彩色文字（無圓點），篩選按鈕維持有框膠囊且保留類型色圓點。「最新發布」為純文字（無綠點）。
- 主要控制列只有搜尋框與篩選膠囊保留可見外框；工具清單與頁籤去框（桌機 1024px 以上側欄底部三顆圖示按鈕沿用標題列按鈕有框樣式）。版本列的複製與分享按鈕在非複製成功狀態下無框、無底色，使用輔助文字色；滑過用淡藍底與亮色文字；601px 以上兩顆按鈕垂直中心對齊版本大標題（`h2.version-num`）。搜尋結果、分享選單與回到頂端按鈕保留既有外框與實心卡片色。搜尋框與搜尋結果不加陰影。複製、分享與程式碼複製按鈕為 6px 圓角；程式碼區塊「複製」按鈕無外框與底色，只留 `--muted-color` 文字（`--fs-xs`、500），滑過或聚焦時變 `--text-bright`，點擊區至少 32px 高（`--control-sm`），「已複製」狀態亦無框無底；版本分享列（含歷史列）的複製連結與分享文字前各放 14px 鏈結與分享線條圖示，間距 6px；600px 以下只有首頁版本列的兩顆按鈕隱藏文字、保留 18px 圖示與無障礙標籤，歷史列文字維持顯示。首頁手機標題獨占首列，同步日期在第三列，分享操作靠右跨第二、三列；搜尋框下方間距 1rem，主內容底部內距於 600px 以下縮為 `1rem`（使「上一版」底部到頁尾 Usage App 頂端距離為 40px）。回到頂端、手機主題按鈕與通知為 8px。點擊區使用 `--control-sm` 32px、`--control-md` 36px、`--control-lg` 44px；手機控制項至少 44px。
- 版本頁與 404 共用 `scripts/build.py` 的 `PAGE_CSS`、四組主題與細線分隔的更新卡。版本大標用 Plus Jakarta Sans、700、等寬數字。404 透過連結導回首頁、RSS 和工具頁。

## 保留的互動

工具清單依資料順序固定；切換工具或版本不重排清單。搜尋至少輸入兩字後才載入索引，結果最多 30 筆。篩選 chip 顯示數量並帶類型色圓點；0 筆類型直接隱藏（`hidden`），已選中的仍顯示以便取消；隱藏後若只剩一顆且未選中，整排膠囊連同右側分隔線一併隱藏，只留開關。分類 chip 右側以分隔線隔開三個 switch 開關，標籤只寫內容名稱、由開關狀態表達顯示與否：企業／團隊向（附篇數，0 篇時隱藏）、比喻，預設開；全部原文，預設關。切換工具、語言或版本後重新計算。600px 以下開關文字不折行（放不下時整顆開關換列；繁中 390px 起為一列），站名與工具列之間不留下距、主內容不留上內距。只有比喻開關記在 localStorage。版本日期旁顯示「網站同步」日期；最新版本最後一則下方拿掉「v… 的更新到這裡」，改為靠左無框的「上一版」兩行文字連結（601px 以上縮排 2.75rem 對齊正文，第一行 `← 上一版 v…`／`← Previous v…` 滑過變 `--link-color`，第二行顯示 `日期 · 首則標題` 並單行省略；首則標題來自 `data.json` 中最新版下一筆的 `first_title`（繁中、英文各一，只有這一筆帶），缺時才用已載入的歷史或搜尋索引，點擊區至少 44px 高；版本頁上一版箭頭朝左 `←`、下一版朝右 `→`）。英文術語後的全形括號白話解釋用 `--muted-color` 淡化。1023px 以下標題列右上依序放語言切換、複製 RSS 與深淺色三顆同尺寸按鈕，間距 8px；標題與可換行副標預留按鈕區，頁尾重複的語言、深淺色與 RSS 控制區（`.sidebar-meta`）在 1023px 以下以 CSS 隱藏（DOM 仍保留 `#language` 供切換語言使用），只保留 Usage App 推廣；側欄不顯示「產生日期」。

桌機 1400px 以上，最新版本分頁右側顯示固定目錄，捲動時標示目前這則；可見卡片少於 3 則時（含篩選後）不顯示固定目錄與手機目錄按鈕，歷史分頁不顯示。卡片序號是按鈕，複製版本靜態頁的 `#card-N` 連結（N 是原始序號，篩選後仍對得上）；卡片序號與目錄序號改用 `--muted-color`，滑過、聚焦及目前這則改用 `--text-bright`。行內程式碼點擊或按 Enter 複製，提示用畫面底部的小浮標，並寫入 `#sr-status`。側欄工具有新版本時亮小圓點：第一次造訪只記錄不亮，看過即消失。快捷鍵：`/` 搜尋、`j`／`k` 上下一則、`o` 展開原文；輸入框內、組字中、帶 Ctrl／Cmd／Alt 時不攔。站內目錄與快捷鍵用 `scrollIntoView`，不改網址 hash。保留語言、主題、RSS、分享、歷史展開、錨點、回到頂端與跳到主要內容連結。

跨頁導覽用 `@view-transition`；版本頁支援 `animation-timeline:view()` 時卡片可輕微進場，首頁維持靜態。`prefers-reduced-motion: reduce` 會停用轉場和進場。首頁 CSS 與 `PAGE_CSS` 的字級和主題變數須同步；改完執行 `python3 scripts/build.py` 與 `python3 -m pytest -q`。
