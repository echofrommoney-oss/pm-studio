# PM Workflow Skill

PM Workflow 是一套面向產品經理的通用工作流，用來把一句需求描述逐步落成可評審、可截圖、可持續迭代的產品交付物。核心流程適用於不同業務領域和產品形態。

## Core Features

- **PRD 生產**：輸出可直接評審的 HTML PRD。章節順序固定為 專案資訊 → 需求背景 → 需求目標 → 需求概述 → 業務流程圖 → 互動流程圖 → 詳細方案 → 資料埋點 → 時序圖，**按需求大小裁剪**——核心骨架（專案資訊 / 需求背景 / 需求目標 / 詳細方案）恆定保留；**只呈現最新版本，不設版本記錄、不留修改痕跡**，其餘 7 個按需省略；不設獨立的「異常與邊界」章（邊界一律進對應功能的【邊界說明】）；裁剪前會先列出保留/省略哪些章節並徵得確認。
- **先複製骨架，再跑校驗**：`assets/templates/prd-content.html` 提供帶正確類名、固定表頭、`colgroup`、`.desc-block` 結構和 `data-preview` 佔位的正文骨架，寫 PRD 從複製它開始而不是從零手寫；交付前跑 `assets/scripts/validate_prd.py` 做機械校驗（核心章節、表頭列數、編號連續、每行 `data-preview`、描述列分塊與硬換行、埋點命名、正文樣式位置等），紅了先修再交。
- **需求目標 / 需求背景 / 需求概述有固定寫法**：需求目標寫"使用者結果 + 衡量口徑"的五列表，沒有真實基線寫「待基線確認」、不編數；需求背景三段式（誰·什麼場景·什麼問題 → 影響 → 證據）；需求概述帶「本期範圍 / 本期不做什麼」範圍塊，把確認階段說過的"不做"釘進文件，並承載跨頁共享的規則表；正文末尾集中一份「待後續確認的產品口徑」清單。
- **詳細方案結構化分塊**：一行 = 一個介面或一個狀態變體；描述列固定用【頁面元素】【互動說明】（每格必出）+【功能邏輯】【邊界說明】【資料與內容規則】【前置條件與權限】【文案規範】【策略說明】（按需出）。按需塊用一個問題判定該不該寫——"把這一頁刪掉，這條規則還成立嗎"：仍成立的是跨頁鏈路規則，上提到需求概述的規則表只寫一次，各格只引用，不再逐頁抄；不寫"無"、不寫"同上"；每條獨立成段；硬性禁止描述列出現任何技術介面表述（API / 參數 / 欄位 key / 錯誤碼）。
- **互動流程圖（Screen Flow）**：可裁剪章節，把所有核心介面拼成一整張帶跳轉箭頭的畫布——介面節點用縮放 iframe 引真實原型頁（原型改動自動同步），箭頭一律直角折線（Manhattan 路由），帶狀態機圖例與縮放/拖曳控制元件，可整張匯出 PNG。**零遮擋是硬指標**：先按幾何下限（同排 ≥70px、上下排 ≥200px、畫布留白 ≥30px、迴流軌道錯峰）擺位，再用內建 `auditFlow()` 檢測標籤壓節點 / 標籤重疊 / 連線穿節點 / 越界並迴圈修復到通過，匯出按鈕在審計未過時直接攔截；推薦用內容反推畫布尺寸，讓越界從根上消失。
- **時序圖**：可裁剪章節（研發/測試向，置於正文最後），產出**可複製的 Mermaid 原始碼文字塊**（端側編排 `sequenceDiagram` + 關鍵物件 `stateDiagram-v2`），研發照文字寫邏輯、測試照文字寫用例。
- **右側雙欄互動原型預覽**：PRD 內建可切頁原型 dock，**預設收起**（開啟 PRD 是乾淨的閱讀態，點「雙欄預覽」才展開，iframe 首次展開才載入），支援滾動聯動 scroll-spy——左側正文滾到某模組，右側預覽自動跟隨切頁，並提供 －/％/＋/適配 縮放控制元件放大檢視細節。
- **全文件可編輯 + 撤銷重做 + 一鍵複製**：正文全篇 `contenteditable`、全表增刪行、列寬/行高拖曳；`⌘Z / Ctrl+Z` 撤銷、`⌘⇧Z / Ctrl+Y` 重做，文字、增刪行、刪表、尺寸調整共用一個撤銷棧（刪掉的行/表恢復後按鈕和手柄仍可用，新編輯清空重做分支，不承諾跨重新整理保留）；左下角「📋 一鍵複製全文」按鈕；右下角「💾 儲存並通知AI」按鈕抓取 `outerHTML` 經系統檔案控制代碼物理覆蓋原 PRD 檔案，AI 後續讀取磁碟即可按使用者手寫改動同步原型和流程圖。
- **一鍵複製全文自動帶原型圖**：右側原型/流程圖 iframe 複製時經本地匯出服務轉成內聯 base64 圖片（首次生成、之後按檔案修改時間快取命中秒出）；服務不可用或部分頁生成失敗會在提示裡如實說明缺了幾張，不靜默丟圖；圖片預設 2000px / 品質 0.9，兼顧清晰度與體積。
- **互動原型**：輸出單檔案 HTML 原型，支援 hash 跳轉、平鋪預覽、iframe 嵌入和真實渲染 PNG 匯出。
- **流程圖**：輸出 Mermaid 流程圖 HTML，並單獨匯出高畫質截圖到 `流程圖截圖/`。視覺固定為"淺底 · 細描邊 · 深字 · 直角連線"（`theme:'base'` + 固定 `themeVariables`，`curve:'linear'`），與 PRD、互動流程圖共用同一套主色與頁面外殼，不再使用 Mermaid 預設主題的實心色塊。
- **需求挖掘**：把使用者訪談、公開評論、客服與社群回饋一起聚類，輸出需求洞察報告；不模擬資料。
- **設計方向與設計關卡**：每個專案自己的 `PRODUCT.md` / `DESIGN.md`；原型前載入 hallmark 與 impeccable 規則，原型後打分與修正（`pm-design.md`）。
- **技術規格**：給工程師的交接 Spec（資料模型、狀態、介面、權限、邊界、非功能），Markdown（`pm-spec.md`）。
- **原型驗證**：產出可用性測試腳本，整理測試結果，結論經變更管理落回文件（`pm-validate.md`）。
- **變更管理**：需求一改，PRD、流程圖、原型、驗證腳本、Spec、驗收清單、上線文件一起改到一致，只留最新版（`pm-change.md`）；`scripts/pm_sync.py` 標出落後的文件並重新匯出截圖。
- **上線包**：版本說明、上線檢查清單、落地頁、App Store／Google Play 上架文案、定價方案（`pm-launch.md`）。
- **驗收清單**：輸出可瀏覽器勾選的驗收 checklist，方便聯調和上線前回歸。
- **資料分析**：輸出帶表格、指標、圖表和結論的資料分析報告。
- **Pencil 可選增強**：保留 Pencil MCP 配置示例，用於需要高保真設計稿時接入。

## Stability Improvements

- **macOS 上點匯出即自動起服務**：不用先雙擊任何東西——點原型頁的「一鍵匯出」或 PRD 的「一鍵複製全文」，服務自己就起來了。靠的是 launchd 的 socket 啟用：連接埠由系統持有，**空閒時本專案零程序**，有請求才拉起、起完自退。隨安裝預設註冊，`bash scripts/install_launcher.sh --uninstall` 可隨時卸掉。
- **一個雙擊入口，Mac / Windows 同源**：Windows 上（以及 macOS 上想手動起時）雙擊專案根的 `啟動原型匯出服務.bat` / `.command`，腳本自己找直譯器、備好執行環境、起服務；保持視窗開著即可導圖。兩個入口都只是薄殼，實際邏輯在 `scripts/start_service.py` 一處。
- **連接埠按專案推導且可自愈**：連接埠由專案路徑確定性推導到 20000–32767（避開系統臨時連接埠段與 Windows 的 Hyper-V/WSL 保留塊），一台機器上多個專案各用各的連接埠、互不搶佔；啟動時連接埠被佔就自動換一個並回寫配置，不會卡死在"連接埠已被使用"。
- **執行環境跨專案共享，不落專案目錄**：Python venv 放在使用者目錄（`~/Library/Application Support/pm-workflow/` / `%LOCALAPPDATA%\pm-workflow\`），避免專案在 OneDrive/iCloud 裡被同步、以及 Windows 路徑超長。截圖引擎優先沿用系統已裝的 Edge / Chrome，**正常情況零下載**，沒有才回落 Playwright 自帶 Chromium。
- **`--doctor` 自檢**：`python3 scripts/start_service.py --doctor`（Windows 用 `py -3`）一次列印直譯器、執行環境、瀏覽器引擎、連接埠實測、配置與代理變數，排查問題不用來回試。
- **自動啟動不留常駐程序**：macOS 的按需啟動器按專案註冊（多個專案互不覆蓋），plist 裡只有 `Sockets`、沒有 `RunAtLoad`/`KeepAlive`，所以它不是守護程序——空閒時 `ps` 裡找不到任何本專案的東西，連接埠卻照樣應答。啟動器連接埠固定不隨自愈漂移，避免註冊資訊過期後自動啟動靜默失效。
- **高畫質匯出**：原型、流程圖、互動流程圖透過 Playwright 真實渲染截圖，不再依賴 `html2canvas` / `html-to-image`。
- **匯出統一走服務**：所有 `.export-btn` 由 `prototype-export-client.js` 攔截交給本地服務，截圖落到所屬需求目錄的一級截圖目錄。
- **相容內網 http 環境**：`navigator.clipboard` / `showSaveFilePicker` 缺失時自動降級（`execCommand` 複製、下載副本儲存），匯出服務按專案相對路徑兜底解析呼叫頁，避免純 http 內網訪問時功能大面積失效。

## 安裝與啟動

### 一、裝進專案（只需一次）

安裝器是 `scripts/initialize.py`，Mac 和 Windows 共用同一份程式碼。三種用法任選：

| 平台 | 做法 |
|---|---|
| macOS / Linux | 在專案目錄執行 `bash /路徑/到/studio-pm-workflow/scripts/init.sh` |
| Windows | 在專案目錄執行 `\路徑\到\studio-pm-workflow\scripts\init.bat`（或在資源管理器裡雙擊它，它會裝到當前目錄） |
| 任意平台 | `python3 /路徑/到/scripts/initialize.py --project .`（Windows 換 `py -3`） |

重複執行是安全的：服務執行時程式碼每次都刷到最新（舊版留在 `.handoff/skill-backups/`），你改過的 workflow 說明書會保留，新版寫到 `.pm-workflow/updates/` 供你對照合併。

### 二、啟動匯出服務

**macOS：什麼都不用做。** 直接開啟原型或 PRD 點匯出，服務會自動啟動（安裝時已註冊按需啟動器）。想手動起也行，雙擊 `啟動原型匯出服務.command` 效果一樣。

**Windows：雙擊 `啟動原型匯出服務.bat`，保持那個視窗開著**，然後開啟原型/流程圖頁點匯出。

首次啟動會自動準備執行環境（裝 Playwright、探測可用瀏覽器），大約一兩分鐘；之後每次都是秒開。

沒裝 Python 的話，入口腳本會停在視窗裡告訴你去 <https://www.python.org/downloads/> 裝 3.9+（Windows 安裝時務必勾選 **Add python.exe to PATH**）。

### 三、出問題時

```bash
python3 scripts/start_service.py --doctor      # Windows: py -3 scripts\start_service.py --doctor
```

一次列印直譯器、執行環境、瀏覽器引擎、連接埠實測、配置狀態和代理變數。

### 四、按需啟動器（僅 macOS，隨安裝預設註冊）

```bash
bash scripts/install_launcher.sh               # 重新註冊（換過連接埠、或裝的時候失敗了）
bash scripts/install_launcher.sh --uninstall   # 解除安裝
```

它讓「點匯出自動起服務」成立，但**不是常駐程序**：plist 裡只給 `Sockets`，連接埠交給 launchd 持有，瀏覽器一連上來才把啟動器拉起，起完服務就自退。空閒時本專案在 `ps` 裡一個程序都沒有。正因為不留常駐，才敢隨安裝預設裝上。

卸掉之後匯出功能照常，只是要先雙擊 `啟動原型匯出服務.command`。裝的時候若因權限等原因註冊失敗，安裝器只會警告、不會中斷，同樣回退到手動雙擊。

Windows 不需要它：服務本體就是你開著的那個視窗，沒有東西需要被拉起。

## Installed Project Shape

安裝後目標專案會獲得（僅建立共享目錄，產物目錄寫需求時按需建立）：

- `.agents/workflows/*.md`：PRD、需求挖掘、驗收清單、資料分析工作流規範。
- `scripts/start_service.py`：服務啟動入口（`--check` / `--serve` / `--doctor`）。
- `scripts/pm_bootstrap.py`：直譯器探測、執行環境準備、瀏覽器引擎探測、子程序拉起。
- `scripts/pm_runtime.py`：專案標識與連接埠推導、配置讀寫、健康檢查。
- `scripts/prototype_server.py`：本地 HTML 服務，提供預覽、截圖匯出、PRD 寫回。
- `scripts/prototype_launcher.py`：輕量 launcher，收到瀏覽器請求後拉起完整服務；macOS 上由 launchd socket 啟用，起完自退。
- `scripts/pm_launchagent.py`：macOS 按需啟動器的註冊/解除安裝/狀態查詢（LaunchAgent plist 的唯一寫入方）。
- `scripts/prototype-export-client.js`：原型/流程圖截圖匯出客戶端。
- `scripts/install_launcher.sh`：macOS 按需啟動器的安裝/解除安裝腳本（安裝時已預設註冊，這裡是重註冊與解除安裝入口）。
- `scripts/pencil-draw-prompt.md`：Pencil 高保真繪製提示詞模板。
- `scripts/prd-content.html`：PRD 正文骨架，寫 PRD 先複製它（源在 skill 的 `assets/templates/`）。
- `scripts/validate_prd.py`：PRD 機械校驗，交付前必跑（源在 skill 的 `assets/scripts/`）。
- `.mcp.json.example`：Pencil MCP 配置示例（需要時複製成 `.mcp.json`）。
- `啟動原型匯出服務.command` / `啟動原型匯出服務.bat`：啟動本地服務的雙擊入口（macOS / Windows）。
- `.pm-workflow/`：本專案的執行配置與安裝清單，已自動寫進 `.gitignore`（含機器相關資訊，不該提交）。

## Output Layout（產物按需求名組織）

產物**按「需求名」分資料夾**：每個需求一個頂層目錄，自己的產物作為子目錄收納其中。任何工作流（需求挖掘 / PRD / 驗收 / 資料分析）開工前先查同名目錄——已存在則沿用，不存在則新建；**誰先開工誰建家**，不假設 PRD 先行。

```
專案根/
├── [需求名]/                  # 一個需求一個頂層目錄
│   ├── 需求文件/[需求名]-PRD.html
│   ├── 原型/[需求名]-prototype.html
│   ├── 流程圖/[需求名]-flow.html + [需求名]-screenflow.html
│   ├── 原型截圖/              # 該需求匯出的 PNG
│   ├── 需求挖掘/ 驗收清單/ 資料分析/   # 用到才建
│   ├── 原型驗證/  技術規格/  上線/
│   └── 素材/（使用者提供的原始材料）
├── scripts/                  # 共享：本地服務與匯出客戶端
├── 啟動原型匯出服務.command     # 共享：macOS 手動啟動（通常不用，點匯出會自動起）
├── 啟動原型匯出服務.bat         # 共享：Windows 雙擊啟動，保持視窗開著
├── .handoff/                 # 共享：會話交接
├── .pm-workflow/             # 共享：執行配置（已 gitignore）
└── .agents/workflows/        # 共享：工作流規範
```

> 匯出服務對新巢狀結構與舊扁平結構均相容：原型/流程圖截圖自動輸出到所屬需求目錄下的 `原型截圖/`、`流程圖截圖/`（舊扁平結構回退到專案根）。

## Repository Scope

這個倉庫只存 skill 本體：

- `SKILL.md`
- `scripts/`
- `assets/workflows/`
- `assets/scripts/`
- `assets/templates/`
- `assets/config/`

不包含任何具體專案的 PRD、原型 HTML、流程圖 HTML、截圖或分享包產物。
