---
description: 後端開發工作流：依技術規格在本機 Supabase 建資料表、權限、檔案儲存、後端函式、排程與示範資料
---

# 後端開發工作流（Supabase）

> 依 `ARCHITECTURE.md` 與需求的技術規格，在**本機** Supabase 實作後端。
> 使用者會在工作台右欄「後端」分頁即時看到資料表、帳號、檔案，並用 API 測試台手動試。

## 觸發方式

- 使用者說「後端」「資料庫」「API」「建表」「權限」「排程」
- 工作台按「後端」

## 前置（缺一不可）

1. 專案根目錄有 `ARCHITECTURE.md`。沒有 → 先走 `pm-sysdesign.md`。
2. 本需求有技術規格 `[需求名]/技術規格/[需求名]-spec.md`，開頭有 `manifest`。沒有 → 先走 `pm-spec.md`。
3. 本機 Supabase 在跑：執行 `supabase status`。沒在跑 → **不要自己啟動**，在回覆中請使用者按工作台上方的「Supabase」燈號啟動，然後結束本輪。
4. 讀 `supabase/migrations/` 既有的遷移檔，了解現況。

## 絕對不做

- 不碰任何遠端專案：不執行 `supabase link`、`supabase db push`、`supabase functions deploy`、`supabase secrets set`（工作台也已封鎖）。
- 不修改已經套用過的遷移檔；要改結構就新增一個遷移檔。
- 不把金鑰寫進程式碼或提交進 git。
- 沒有使用者同意，不執行 `supabase db reset`：它會清掉本機所有測試資料，包括使用者在工作台建立的測試帳號。需要時在回覆中說明原因，請使用者在「後端」分頁按「重置測試資料」。

## 步驟

### 一、對照 Spec 列出要做的

從 Spec 的 `manifest` 與內文整理：資料表（欄位、型別、限制、關聯）、RLS 規則（依 `ARCHITECTURE.md` 第 3 節權限表）、bucket、資料庫函式、Edge Function、排程。和現況比對，只做缺的或不一致的。

### 二、資料表與權限：遷移檔

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

### 三、後端函式

- 簡單的資料操作寫成資料庫函式（RPC），放在遷移檔裡。
- 要呼叫第三方服務、要金鑰、要複雜邏輯的寫成 Edge Function：
  ```bash
  supabase functions new 函式名
  ```
  在 `supabase/functions/函式名/index.ts` 實作（Deno + TypeScript）。檢查呼叫者身分（`Authorization` 標頭）；錯誤格式依 `ARCHITECTURE.md`。第三方金鑰從環境變數讀，並在 `supabase/functions/.env.example` 列出變數名稱。

### 四、示範資料

`supabase/seed.sql`：讓使用者在工作台能直接看到、操作的示範資料。

- 用明顯是示範的內容：飼主叫「示範飼主一」、信箱用 `demo1@example.com`，不要像真人。
- 涵蓋 Spec 的主要情境與邊界（例如「疫苗已過期」「疫苗三天後到期」各一筆）。
- 示範帳號要登入用的話，在 seed 裡建立 `auth.users` 並在回覆中列出帳密；或請使用者在「後端 → 帳號」分頁建立測試帳號。
- seed 只在重置時套用。改了 seed，請使用者按「重置測試資料」。

### 五、型別

```bash
supabase gen types typescript --local > supabase/types/database.ts
```

APP 與前端之後會用到。

### 六、自我檢查

1. `supabase status` 正常。
2. 本需求 `manifest` 列的每張表、每個函式都已存在（工作台「後端 → 建置進度」會顯示）。
3. 用最小權限思考 RLS：列出「A 角色能不能讀到 B 的資料」這類關鍵情境，在回覆中寫出你預期的結果，請使用者用「後端 → 帳號」切換身分、在 API 測試台驗證。
4. 能寫測試就寫：`supabase/tests/*.sql`（pgTAP），`supabase test db` 執行。完整的自動測試在 QA 階段。

### 七、完成

1. 實作與 Spec 有出入（例如發現 Spec 的欄位不可行）→ **不要自己改 Spec**。在回覆中說明，請使用者決定後走「變更」。
2. `python3 scripts/pm_sync.py commit 需求名 -m "[需求名] 後端：一句話摘要"`。
3. 回覆使用者：建了什麼（表、函式、bucket、排程）、示範帳號、建議他在右欄試哪幾個操作、還沒做的。

## 使用者回報問題時

使用者說「這支 API 回 403」「註冊後資料沒寫進去」→ 讀工作台「後端 → 日誌」提到的錯誤、看遷移與 policy，找出原因再修。修完說明原因與修法。
