---
version: alpha
name: AI Updates
description: AI 工具更新速報的藍色柔光版面規格；首頁、版本頁與 404 共用主題色。
tokens:
  size:
    --fs-2xs: ".6875rem"
    --fs-xs: ".75rem"
    --fs-sm: ".8125rem"
    --fs-base: ".9375rem"
    --fs-md: "1rem"
    --fs-lg: "1.125rem"
    --fs-xl: "1.375rem"
    --control-sm: "32px"
    --control-md: "36px"
    --control-lg: "44px"
  light:
    --bg-color: "#ffffff"
    --sidebar-bg: "#ffffff"
    --card-bg: "#ffffff"
    --code-bg: "#f6f9fc"
    --soft-surface: "#f6f9fc"
    --border-color: "#d8e3ee"
    --text-color: "#425466"
    --text-bright: "#061b31"
    --muted-color: "#586a82"
    --accent-color: "#2563eb"
    --accent-contrast: "#ffffff"
    --accent-glow: "#eff6ff"
    --link-color: "#2156ca"
    --tag-new: "#087a56"
    --tag-fix: "#b13f43"
    --tag-perf: "#925b08"
    --item-rule: "#e5edf5"
    --chip-bg: "#f6f9fc"
    --analogy-text: "#425466"
    --analogy-start: "oklch(0.77 0.11 255 / .16)"
    --analogy-end: "oklch(0.80 0.09 205 / .13)"
    --analogy-border: "#d8e3ee"
    --badge-bg: "#ffffff"
    --glow-wash-1: "rgb(34 211 238 / 17%)"
    --glow-wash-2: "rgb(56 140 255 / 15%)"
    --glow-wash-3: "rgb(99 102 241 / 18%)"
    --glass-fill: "rgb(255 255 255 / 70%)"
    --glass-border: "#d8e3ee"
    --glass-shadow: "0 10px 28px rgb(10 37 64 / 8%)"
    --selected-gradient: "linear-gradient(110deg,#2563eb,#0369a1)"
    --serial-1: "#1575a2"
    --serial-2: "#2563c9"
    --serial-3: "#4158bc"
    --font-ui: "\"Inter\",-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif"
  dark:
    --bg-color: "#0a2540"
    --sidebar-bg: "#0a2540"
    --card-bg: "#0f3056"
    --code-bg: "#102e4e"
    --soft-surface: "#173b62"
    --border-color: "#31516f"
    --text-color: "#bed0e4"
    --text-bright: "#ffffff"
    --muted-color: "#aac0d8"
    --accent-color: "#2563eb"
    --accent-contrast: "#ffffff"
    --accent-glow: "#243f75"
    --link-color: "#93c5fd"
    --tag-new: "#85d9bc"
    --tag-fix: "#ffa99e"
    --tag-perf: "#f9cf82"
    --item-rule: "rgb(255 255 255 / 10%)"
    --chip-bg: "#173b62"
    --analogy-text: "#bed0e4"
    --analogy-start: "oklch(0.51 0.16 255 / .22)"
    --analogy-end: "oklch(0.55 0.10 205 / .16)"
    --analogy-border: "rgb(255 255 255 / 12%)"
    --badge-bg: "rgb(255 255 255 / 6%)"
    --glow-wash-1: "rgb(34 211 238 / 27%)"
    --glow-wash-2: "rgb(56 140 255 / 29%)"
    --glow-wash-3: "rgb(99 102 241 / 38%)"
    --glass-fill: "rgb(10 37 64 / 69%)"
    --glass-border: "rgb(255 255 255 / 18%)"
    --glass-shadow: "0 12px 36px rgb(0 12 34 / 18%)"
    --selected-gradient: "linear-gradient(110deg,#2563eb,#0369a1)"
    --serial-1: "#50c7f1"
    --serial-2: "#4dacf6"
    --serial-3: "#6d9aff"
    --font-ui: "\"Inter\",-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif"
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
