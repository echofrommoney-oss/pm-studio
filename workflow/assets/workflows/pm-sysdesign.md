---
description: 系統設計工作流（SA/SD）：先和使用者討論技術選型，再產出專案級 ARCHITECTURE.md（含工作台讀取的 stack 與 services）
---

# 系統設計工作流（SA/SD）

> `ARCHITECTURE.md` 是整個產品的技術總藍圖，放在專案根目錄，一個專案一份，永遠是最新版。
> **技術選型每個案子都不同，一律先討論、使用者決定後才寫。** 沒有預設組合。

## 觸發方式

- 使用者說「系統設計」「架構」「SA」「SD」「技術選型」「用什麼技術」
- 工作台按「系統 → 系統設計」
- 要寫技術規格或開始開發，但專案沒有 `ARCHITECTURE.md`，或它沒有 `stack`／`services`

## 第一輪：技術選型討論（不寫檔）

### 1. 蒐集條件

讀 `PRODUCT.md`、所有 PRD、`DESIGN.md`，看專案裡有沒有既有程式。整理影響選型的條件，已知的直接寫，未知的列成問題：

- 要做哪些部分：APP（iOS／Android）、網站（哪幾個、給誰用）、後端
- 原生能力：推播、相機、定位、地圖、藍牙、背景執行、離線
- 資料：關聯複雜度、即時同步、檔案與影音、搜尋、報表
- 規模與效能：預期用戶數、尖峰、地區
- 整合：金流、第三方登入、既有系統、政府或醫療等法規
- 團隊：使用者自己或合作工程師熟悉的語言與框架、之後誰維護
- 時程與預算：上線時間、每月雲端費用上限

### 2. 提出選項

每個部分（有的才列）提出 **2–3 個選項**，每個選項寫：

- 適合的理由（對照上面的條件）
- 代價與風險（學習成本、費用、鎖定廠商、效能、招募難度）
- **工作台支援程度**：
  - **專屬面板**：Supabase（資料庫、帳號、測試信箱、API 測試、建置進度）、Flutter（手機外框預覽、熱重載、模擬器、DevTools）、Next.js（網站預覽、自動判斷頁面進度）
  - **通用支援**：其他任何能在本機用指令啟動的技術。可以啟動、看日誌、網頁預覽（桌機／平板／手機尺寸）、自訂後端的 API 測試台；建置進度靠程式裡的標記
- 最後給一個**建議組合**與一句理由。

支援程度只是參考，**不能因為工作台支援就推薦不適合的技術**。

### 3. 請使用者決定

以編號問題作為本輪最後的回覆並結束，例如：

1. APP：選 A／B／C？
2. 後端：選 A／B？
3. 還有沒補上的條件（例如預算、誰來維護）？

使用者可能只回「照建議」，也可能改其中一項。**使用者沒有明確決定前，不寫 `ARCHITECTURE.md`、不寫任何程式。**

## 第二輪：寫 `ARCHITECTURE.md`

### 開頭：stack 與 services（工作台讀這段）

```yaml
---
stack:
  app: flutter            # 使用者決定的技術，一律小寫英文名稱
  web: nextjs
  backend: supabase
services:
  - id: backend           # 英文、數字、連字號
    role: backend         # app | web | backend
    label: 本機後端         # 工作台顯示的名稱
    adapter: supabase     # supabase | flutter | nextjs | vite | expo | generic
  - id: app
    role: app
    label: 呼嚕 APP
    adapter: flutter
    dir: app              # 程式資料夾（相對專案根目錄）
  - id: admin
    role: web
    label: 管理後台
    adapter: nextjs
    dir: web/admin
  - id: api               # 通用支援的範例：自建 API
    role: backend
    label: 通知服務
    adapter: generic
    dir: server
    install: uv sync                                  # 安裝套件（第一次啟動前自動跑）
    run: uv run uvicorn main:app --port {port}        # 啟動開發伺服器；{port} 由工作台分配
    ready: Uvicorn running                            # 輸出出現這段文字就算啟動完成
    url: http://127.0.0.1:{port}                      # 預覽／API 測試用的網址
    openapi: /openapi.json                            # 有的話，API 測試台會列出端點
    tools: [uv, python -m pytest]                     # 允許 Claude 執行的指令開頭
    depends_on: [backend]                             # 啟動前要先開好的服務（例如 API 要等資料庫）
    auth:                                             # 讓 API 測試台能自動登入（自建後端才需要）
      login: POST /auth/login                         # 登入 API
      body: {"email": "{email}", "password": "{password}"}   # 帳密的 JSON 範本
      token: data.accessToken                         # 回應中 token 的位置；用 cookie 登入就寫 cookie
      header: "Authorization: Bearer {token}"          # 送出時加的標頭（預設就是這個）
      accounts:                                       # 示範資料裡已存在的測試帳號（只限本機示範資料）
        - email: demo1@example.com
          password: demo1234
          role: owner
    test: uv run pytest --junitxml=reports/junit.xml  # 跑測試的指令
    test_report: reports/junit.xml                    # 測試報告（JUnit XML；可用 * 萬用字元或資料夾）
    env:                                              # 啟動時帶入的環境變數
      DATABASE_URL: "{SUPABASE_DB_URL}"
---
```

規則：

- `supabase`、`flutter`、`nextjs`、`vite`、`expo` 已內建啟動方式，只要 `id`、`role`、`label`、`dir`；需要時可覆寫 `run`、`env`。Flutter 的入口不是 `lib/main.dart` 時（例如分環境的 `lib/main_dev.dart`），加 `target: lib/main_dev.dart`。
- `generic` 必須寫 `run`；有網頁或 API 的要寫 `url`。`run` 必須是**在本機跑、不會連到正式環境**的開發指令。
- `env` 可用的變數：`{port}`、`{SUPABASE_URL}`、`{SUPABASE_ANON_KEY}`、`{SUPABASE_DB_URL}`、`{BACKEND_URL}`（第一個非 Supabase 後端的網址，沒有則為 Supabase 網址）、`{<服務 id 大寫>_URL}`。APP 在 Android 模擬器上執行時，工作台會自動把本機網址換成 `10.0.2.2`。
- `tools` 只列開發需要的指令（安裝、測試、產生程式碼、資料庫遷移）。啟動開發伺服器的指令由工作台負責，會自動禁止 Claude 執行。
- `depends_on`：這個服務需要誰先啟動（資料庫、另一個 API）。工作台啟動它時會自動先開好依賴的服務。
- `auth`：自建後端需要登入時寫。工作台的 API 測試台會用它登入、自動帶 token，過期會自動重新登入；使用者可以在測試台切換身分驗證權限。`accounts` 只能列**本機示範資料**的帳號（和 seed 一致），不可寫任何正式環境的帳密。Supabase 不用寫，它有專屬的帳號面板。
- `test`／`test_report`：QA 分頁用來跑測試、讀結果。報告一律用 **JUnit XML**（幾乎所有測試工具都支援）。Flutter 與 Supabase 已內建，不用寫；其他服務沒寫就無法在 QA 分頁執行。
- 不需要的部分不列（例如沒有網站就沒有 web 服務）。

### 內文

```markdown
# [產品名] 系統設計

> 最後更新 YYYY-MM-DD

## 1. 技術組合
表格：部分｜技術｜程式位置｜用途｜工作台支援（專屬／通用）。每項一句選擇理由（完整的比較過程寫在 git 提交訊息）。

## 2. 系統架構
Mermaid flowchart：使用者端 → 後端 → 第三方服務。每個第三方服務一行：做什麼、在哪一端呼叫、金鑰放哪。

## 3. 角色與權限
| 角色 | 說明 | 從哪登入 |
「角色 × 資料」權限表：每種資料每個角色能 讀／新增／修改／刪除 哪些。這是後端權限規則的來源。

## 4. 資料模型
Mermaid erDiagram；每張表一行：用途、屬於哪個需求、主要欄位。命名慣例依所選技術。

## 5. 後端慣例
資料存取、權限實作方式、遷移、錯誤格式、檔案儲存、排程、API 風格（REST／GraphQL／RPC）。

## 6. APP 與前端慣例
狀態管理、路由、資料存取、設計 token 的產生方式（`scripts/pm_tokens.py`：dart／css／ts）、多語系、時區。

## 7. 環境
本機（工作台）→ 測試 → 正式。環境變數清單（只列名稱與用途，不寫值）。

## 8. 非功能需求
效能、安全、隱私、個資、備份、監控。沒有依據的數字寫「待確認」。

## 9. 待確認
```

## 改選型

使用者之後想換技術（例如網站從 Next.js 換成 Vue）：先用第一輪的方式說明影響（已寫的程式要重做多少、工作台支援會怎麼變），使用者同意後才改，並走 `pm-change.md` 把受影響的技術規格與程式一起處理。

## 完成後

1. 自查：每個 PRD 的主要資料在資料模型裡有落點；每張表在權限表裡有規則；`services` 每一個都說得出怎麼啟動。
2. `python3 scripts/pm_sync.py commit 需求名 -m "[需求名] 系統設計：選用 xxx（理由摘要）"`。
3. 回覆使用者：選了什麼、工作台會出現哪些分頁、下一步（通常是「技術規格」）。
