---
description: 後端開發工作流：依 ARCHITECTURE.md 選定的後端技術，在本機實作資料、權限、API、排程與示範資料
---

# 後端開發工作流

> 後端用什麼技術，由 `ARCHITECTURE.md` 的 `stack.backend` 與 `services`（role: backend）決定，本檔不預設。
> 下半部是**後端為 Supabase 時**的專屬做法；其他技術照「通用規則」。

## 通用規則（任何後端技術）

### 前置

1. `ARCHITECTURE.md` 要有 role 為 backend 的服務。沒有或沒有 stack → 先走 `pm-sysdesign.md` 和使用者討論選型，**不可自行選技術**。
2. 本需求有技術規格且開頭有 `manifest`。沒有 → 先走 `pm-spec.md`。
3. 讀 `ARCHITECTURE.md` 第 3 節（權限表）、第 4 節（資料模型）、第 5 節（後端慣例）。

### 絕對不做

- **不啟動開發伺服器或本機資料庫**（由工作台負責；它們的啟動指令已封鎖）。需要時請使用者在右欄按啟動。
- 不連任何遠端或正式環境：不部署、不推送資料庫、不設定雲端金鑰。
- 不修改已經套用過的資料庫遷移；要改結構就新增遷移。
- 不把金鑰寫進程式或提交進 git；列在 `.env.example` 並說明用途。

### 做法

1. 依 Spec 的 `manifest`（`tables`、`endpoints`、`functions`…）與內文實作，和現況比對，只做缺的或不一致的。
2. 權限照 `ARCHITECTURE.md` 的角色 × 資料表，**預設拒絕**，逐條開放。
3. 準備示範資料（明顯是示範的內容，例如「示範飼主一」、`demo1@example.com`），涵蓋主要情境與邊界。
4. **建置進度的判斷**（非 Supabase 時）：
   - 每支 API 的處理函式旁加註解標記，和 manifest 的 `endpoints` 一字不差：
     ```
     # pm-endpoint: GET /pets/{id}
     ```
   - 框架能產生 OpenAPI 文件時，在 `ARCHITECTURE.md` 的服務寫 `openapi` 路徑（請使用者按「系統設計」補），工作台的 API 測試台就能列出所有端點。
   - OpenAPI 要寫完整：每支 API 的路徑與查詢參數、請求內容的 schema（必填欄位、enum、格式，能給 example 更好）、回應 schema、需要登入的標 `security`。工作台用它在建置進度顯示實際定義，並在 API 測試台自動帶入參數與範例內容。
   - 需要登入的後端：確認 `ARCHITECTURE.md` 的服務有 `auth` 設定（登入 API、token 位置），並在 `accounts` 列出 seed 裡的示範帳號；沒有就請使用者按「系統設計」補上。
5. 用該技術的方式寫測試並執行（指令須在 `services` 的 `tools` 裡）。

### 完成

1. 請使用者在右欄「後端」啟動服務，列出建議在 API 測試台試的請求（方法、路徑、內容、需要的標頭）。
2. 實作和 Spec 有出入 → 不自己改 Spec，在回覆中說明，請使用者決定後走「變更」。
3. `python3 scripts/pm_sync.py commit 需求名 -m "[需求名] 後端：一句話摘要"`。

---

## 後端為 Supabase 時

> 右欄「後端」分頁有專屬面板：資料庫、帳號與身分切換、測試信箱、檔案、後端函式立即執行、API 測試、建置進度。

### 前置（缺一不可）

1. `ARCHITECTURE.md` 的 services 有 `adapter: supabase` 的服務。
2. 本需求有技術規格 `[需求名]/技術規格/[需求名]-spec.md`，開頭有 `manifest`。沒有 → 先走 `pm-spec.md`。
3. 本機 Supabase 在跑：執行 `supabase status`。沒在跑 → **不要自己啟動**，在回覆中請使用者按工作台上方的「Supabase」燈號啟動，然後結束本輪。
4. 讀 `supabase/migrations/` 既有的遷移檔，了解現況。

### 絕對不做（Supabase）

- 不碰任何遠端專案：不執行 `supabase link`、`supabase db push`、`supabase functions deploy`、`supabase secrets set`（工作台也已封鎖）。
- 不修改已經套用過的遷移檔；要改結構就新增一個遷移檔。
- 不把金鑰寫進程式碼或提交進 git。
- 沒有使用者同意，不執行 `supabase db reset`：它會清掉本機所有測試資料，包括使用者在工作台建立的測試帳號。需要時在回覆中說明原因，請使用者在「後端」分頁按「重置測試資料」。

### 步驟

#### 一、對照 Spec 列出要做的

從 Spec 的 `manifest` 與內文整理：資料表（欄位、型別、限制、關聯）、RLS 規則（依 `ARCHITECTURE.md` 第 3 節權限表）、bucket、資料庫函式、Edge Function、排程。和現況比對，只做缺的或不一致的。

#### 二、資料表與權限：遷移檔

```bash
supabase migration new 簡短英文描述
```

在產生的 `supabase/migrations/<時間>_<描述>.sql` 寫 SQL，一個遷移檔做一件相關的事：

- `create table public.xxx (...)`：依 `ARCHITECTURE.md` 命名慣例；`id uuid primary key default gen_random_uuid()`、`created_at`、`updated_at timestamptz default now()`。
- 外鍵、`not null`、`check` 限制照 Spec。
- **每張表**：`alter table ... enable row level security;` 加上各角色的 policy。角色判斷用 `auth.uid()` 與使用者資料表或 `auth.jwt()` 裡的角色欄位，方式照 `ARCHITECTURE.md`。
- `updated_at` 用 trigger 自動更新。
- bucket：`insert into storage.buckets (id, name, public) values (...) on conflict do nothing;` 加 `storage.objects` 的 policy。
- 排程：`pg_cron` 的 `cron.schedule(...)`，呼叫資料庫函式或用 `net.http_post` 呼叫 Edge Function。

套用到本機：

```bash
supabase migration up
```

失敗就讀錯誤訊息修遷移檔（**這個還沒套用成功的檔可以改**）再跑一次。

#### 三、後端函式

- 簡單的資料操作寫成資料庫函式（RPC），放在遷移檔裡。
- 要呼叫第三方服務、要金鑰、要複雜邏輯的寫成 Edge Function：
  ```bash
  supabase functions new 函式名
  ```
  在 `supabase/functions/函式名/index.ts` 實作（Deno + TypeScript）。檢查呼叫者身分（`Authorization` 標頭）；錯誤格式依 `ARCHITECTURE.md`。第三方金鑰從環境變數讀，並在 `supabase/functions/.env.example` 列出變數名稱。

#### 四、示範資料

`supabase/seed.sql`：讓使用者在工作台能直接看到、操作的示範資料。

- 用明顯是示範的內容：飼主叫「示範飼主一」、信箱用 `demo1@example.com`，不要像真人。
- 涵蓋 Spec 的主要情境與邊界（例如「疫苗已過期」「疫苗三天後到期」各一筆）。
- 示範帳號要登入用的話，在 seed 裡建立 `auth.users` 並在回覆中列出帳密；或請使用者在「後端 → 帳號」分頁建立測試帳號。
- seed 只在重置時套用。改了 seed，請使用者按「重置測試資料」。

#### 五、型別

```bash
supabase gen types typescript --local > supabase/types/database.ts
```

APP 與前端之後會用到。

#### 六、自我檢查

1. `supabase status` 正常。
2. 本需求 `manifest` 列的每張表、每個函式都已存在（工作台「後端 → 建置進度」會顯示）。
3. 用最小權限思考 RLS：列出「A 角色能不能讀到 B 的資料」這類關鍵情境，在回覆中寫出你預期的結果，請使用者用「後端 → 帳號」切換身分、在 API 測試台驗證。
4. 能寫測試就寫：`supabase/tests/*.sql`（pgTAP），`supabase test db` 執行。完整的自動測試在 QA 階段。

#### 七、完成

1. 實作與 Spec 有出入（例如發現 Spec 的欄位不可行）→ **不要自己改 Spec**。在回覆中說明，請使用者決定後走「變更」。
2. `python3 scripts/pm_sync.py commit 需求名 -m "[需求名] 後端：一句話摘要"`。
3. 回覆使用者：建了什麼（表、函式、bucket、排程）、示範帳號、建議他在右欄試哪幾個操作、還沒做的。

### 使用者回報問題時

使用者說「這支 API 回 403」「註冊後資料沒寫進去」→ 讀工作台「後端 → 日誌」提到的錯誤、看遷移與 policy，找出原因再修。修完說明原因與修法。
