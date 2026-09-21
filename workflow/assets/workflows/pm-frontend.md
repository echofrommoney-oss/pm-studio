---
description: 前端開發工作流：依 ARCHITECTURE.md 選定的技術，實作網站（管理後台、合作夥伴網頁、官網等），接上本機後端
---

# 前端開發工作流

> 網站用什麼技術，由 `ARCHITECTURE.md` 的 `stack.web` 與 `services`（role: web）決定，本檔不預設。
> 使用者在工作台右欄「前端」分頁選網站、按啟動，用桌機／平板／手機尺寸預覽。

## 觸發方式

- 使用者說「前端」「網站」「後台」「官網」「網頁」
- 工作台按「開發 → 前端」

## 前置

1. `ARCHITECTURE.md` 要有 `services` 裡 role 為 web 的服務。沒有或沒有 stack → 先走 `pm-sysdesign.md` 和使用者討論選型，**不可自行選框架**。
2. 讀 `ARCHITECTURE.md` 第 3 節（角色與權限）、第 6 節（前端慣例），`DESIGN.md`，本需求的原型與技術規格（`manifest` 的 `pages.<服務 id>`）。
3. 先確認要做的是哪一個網站服務（依使用者的話或 Spec 的 pages 鍵判斷）；不確定就問。

## 絕對不做

- **不啟動開發伺服器**（`next dev`、`vite`、`npm run dev` 等，工作台已封鎖）。使用者在右欄按啟動；改程式後多數框架會自動更新畫面。
- 不把後端網址或金鑰寫死；一律讀環境變數。工作台啟動時會寫好（見下方「接後端」）。
- 不手寫色碼與字型；用 `DESIGN.md` 產生的 token。
- 不部署、不連正式環境。

## 建立專案（該服務的資料夾還不存在時）

- 用該框架官方的建立工具，並使用**非互動**參數（例如 `--yes`、`--ts`），在 `ARCHITECTURE.md` 寫的 `dir` 建立。不確定參數就先看 `--help`。
- 多個網站共用元件或型別時，依 `ARCHITECTURE.md` 的決定設定 monorepo（例如 pnpm workspace）；沒寫就各自獨立，不擅自加。
- 建立後若 `ARCHITECTURE.md` 的 services 需要補 `install`／`run`／`url`（通用支援的框架），**在回覆中列出要補的內容，請使用者按「系統設計」更新**，不要自己改 `ARCHITECTURE.md` 的選型段。

## 設計 token

```bash
python3 scripts/pm_tokens.py css --out <網站資料夾>/styles/tokens.css
```

在全站樣式或版面入口載入它；用 CSS 變數（`var(--colors-primary)`）。用 Tailwind 等工具時，在設定裡引用這些變數，不另外寫一套色碼。`DESIGN.md` 改了就重跑。

## 接後端

工作台啟動網站時，依 `services` 的 `env`（內建框架有預設）寫入環境變數檔或帶入環境變數：

- Next.js：`.env.local` 的 `NEXT_PUBLIC_SUPABASE_URL`／`NEXT_PUBLIC_SUPABASE_ANON_KEY`（後端是 Supabase 時）或 `NEXT_PUBLIC_API_URL`
- Vite：`VITE_…`；Expo：`EXPO_PUBLIC_…`；通用：依 `env` 設定

程式只讀這些變數；變數是空的時要顯示清楚的提示（「本機後端沒開，到工作台啟動後重新整理」），不要直接壞掉。

登入類頁面：用「後端 → 帳號」建立的測試帳號測試；依 `ARCHITECTURE.md` 的角色表做權限判斷（例如合作夥伴只能看自己醫院的資料）。

## 頁面

1. 依 `manifest` 的 `pages.<服務 id>` 逐一實作，每頁對應原型的畫面。
2. **建置進度的判斷**：
   - Next.js：工作台自動從 `app/`／`pages/` 資料夾結構判斷，路由寫法和 manifest 一致即可（例如 `/pets/[id]`）。
   - 其他框架：在每頁的程式檔加註解標記，路由和 manifest 一字不差：
     ```
     // pm-page: /pets/[id]
     ```
3. 文案照 PRD 與原型；狀態齊全（載入中、空、錯誤、無權限）；表格與表單可用鍵盤操作、有標籤。
4. 官網類頁面（Persuade 模式）另外遵守 `pm-launch.md` 落地頁的規則：不編造見證與數據、有 meta 與 OG。
5. 響應式：管理後台以桌機為主但平板可用；官網與合作夥伴網頁三種尺寸都要檢查。

## 檢查

依框架跑型別檢查與 lint（例如 `pnpm run lint`、`pnpm exec tsc --noEmit`），要乾淨。

## 完成

1. 請使用者在右欄「前端」選網站、按啟動，列出建議走一遍的頁面與要用的測試帳號。
2. 實作和原型或 Spec 有出入 → 不自己改文件，在回覆中說明，請使用者決定後走「變更」。
3. `python3 scripts/pm_sync.py commit 需求名 -m "[需求名] 前端：一句話摘要"`。
