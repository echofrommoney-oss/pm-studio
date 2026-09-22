---
description: 設計方向與設計品質工作流：為每個產品建立 PRODUCT.md / DESIGN.md，並在原型前後套用設計層（impeccable、hallmark、pencilplaybook、gsap、ui-ux-pro-max、design-md-chrome）
---

# 設計方向與設計品質工作流

> 這條工作流回答一件事：**這個產品的介面應該長什麼樣、怎麼確保原型不像 AI 模板。**
> 它不產 PRD、不畫流程圖；那些在 `pm-prd.md`。它產出並維護兩份專案級檔案，並在原型前後插入設計關卡。
>
> 工作室做的產品方向差異很大，所以**每個產品專案各自決定風格**，沒有預設行業配色。所有判斷以本專案的 `PRODUCT.md` 與 `DESIGN.md` 為準。

## 設計層的六個工具各管什麼

安裝器會把它們放進 `.claude/skills/`（Claude Code 自動載入，用 `/skill名` 或直接描述即可觸發）。上游 skill 保持英文原文以便追更新；本檔是繁體中文的接線說明。

| 工具 | 位置 | 職責 | 何時用 |
|---|---|---|---|
| **impeccable** | `.claude/skills/impeccable/` | 產品事實（`init` → `PRODUCT.md`）、設計系統紀錄（`document` → `DESIGN.md`）、深度評審（`critique`）、技術稽核（`audit`）、分項修正（`typeset`/`layout`/`colorize`/`animate`…）、最後潤色（`polish`） | 專案第一次設定；原型完成後的評審與修正 |
| **hallmark** | `.claude/skills/hallmark/` | 反 AI 模板的建構規則、21 種主題與 21 種版面巨觀結構、`study` 從網址或截圖抽取設計 DNA、`audit` 打分、`redesign` 換骨架 | 決定風格方向；原型完成後快速打分；想換一種長相 |
| **ui-ux-pro-max** | `.claude/skills/ui-ux-pro-max/` | 本機可搜尋的資料庫：79 種 UI 風格、192 組產品配色與推理、74 組字型配對、119 條 UX 準則、25 種圖表、17 組 GSAP 預設 | 不確定要什麼風格時先查；選字型、選配色、選圖表型別 |
| **gsap-core / gsap-timeline / gsap-scrolltrigger / gsap-performance / gsap-plugins / gsap-utils** | `.claude/skills/gsap-*/` | GSAP 官方用法（免費含全部外掛） | 原型需要動效、轉場、捲動連動時 |
| **pencilplaybook** | `.claude/skills/pencilplaybook/` | Pencil 高保真設計的感知心理學規則與 7 組色彩預設（disabled 40%、hover 8% 亮度差、暗底文字不用純白…） | 走 `pm-prd.md` §3.5 Pencil 路線時必讀 |
| **design-md-chrome** | Chrome 擴充功能（人工安裝，見 `設計層/chrome-extension/`） | 在瀏覽器裡一鍵從任何網站抽出 `DESIGN.md`（字型、色彩、間距、圓角、陰影、動效） | 使用者看到喜歡的網站時，自己抓完丟進專案 |

## 兩份專案級檔案

| 檔案 | 內容 | 誰產生 | 誰讀 |
|---|---|---|---|
| `PRODUCT.md`（專案根目錄） | 平台、使用者、產品目的、定位、營運情境、能力與限制、品牌承諾、證據、產品原則 | `impeccable init`（一次） | impeccable 每個命令；`pm-prd.md` 步驟一追問時可引用 |
| `DESIGN.md`（專案根目錄） | 色彩 token、字型、字級、間距、圓角、陰影、動效、元件慣例；frontmatter 為機器可讀 token | `hallmark study` 或 design-md-chrome 抽取 → 整理；或原型定稿後 `impeccable document` 回寫 | **所有原型與 Pencil 繪製都以它為準**；pencilplaybook 的 token map 從這裡取值 |

`PRODUCT.md` 描述「這是什麼產品、給誰用」，一個專案只寫一次；`DESIGN.md` 描述「長什麼樣」，可以迭代。**兩者都用繁體中文撰寫**（impeccable 寫出來若是英文，翻譯後保留其 schema 註解行，例如 `<!-- impeccable:product-schema 1 -->`）。

## 觸發方式

- 使用者說「設計方向」「風格」「DESIGN.md」「這個產品要長什麼樣」「照 xxx 網站的感覺」
- `pm-prd.md` 步驟三開工前發現專案沒有 `DESIGN.md`（見該檔 §3.0）
- 原型完成後使用者說「檢查原型」「評審設計」「不像 AI 做的嗎」
- 使用者說「加動效」「高保真」

## 流程 A：專案首次設定（每個產品一次）

```
檢查專案根目錄
    ├─ 沒有 PRODUCT.md → A1
    └─ 沒有 DESIGN.md  → A2
```

### A1 產品事實 → PRODUCT.md

1. 執行 impeccable 的 `init`（讀 `.claude/skills/impeccable/SKILL.md` 與 `reference/init.md`）。它會檢視專案、只問**缺少的重要事實**，寫出 `PRODUCT.md`。
2. 若專案裡已有 PRD 或需求檔，先讀它們，把已知答案帶進去，不要重複問使用者。
3. 寫完後以繁體中文重寫內容（保留 schema 註解與段落標題的語意），並給使用者看一遍確認。

### A2 風格方向 → DESIGN.md

先問使用者一個問題，**只問一個**：

> 這個產品的介面，你心裡有參考對象嗎？
> 1. 有網址或截圖 → 貼給我
> 2. 有幾個形容詞（例如「安靜、專業」「活潑、消費向」「工具感、資訊密」）→ 說出來
> 3. 都沒有 → 我先查資料庫給你三個方向選

依回答走：

- **有網址／截圖**：用 hallmark 的 `study <網址或截圖>` 抽取設計 DNA（巨觀結構、字型配對、色彩錨點）。它會拒絕像素級複製與付費模板，這是對的，照它的做法。把結果寫進 `DESIGN.md`。
  - 若使用者是用 design-md-chrome 自己抓的檔案，直接把它存成專案根目錄 `DESIGN.md`，再用 hallmark `study` 的視角補上巨觀結構與主題選擇（擴充功能抽的是 token，不含版面策略）。
- **有形容詞**：用 ui-ux-pro-max 查（`python3 .claude/skills/ui-ux-pro-max/scripts/search.py "<形容詞 + 產品類型>" --domain style -n 3`，再查 `--domain color`、`--domain typography`），整理成三個方向，每個方向一句話說明適合誰、附主色與字型配對，請使用者選一個。選定後再對照 hallmark 的 21 種主題挑最接近的一個記進 `DESIGN.md`。
- **都沒有**：同上，但查詢詞用 `PRODUCT.md` 裡的產品類型與使用者描述。

`DESIGN.md` 至少要有：

```markdown
---
name: <產品名> 設計系統
theme: <hallmark 主題名，或自訂>
macrostructure: <hallmark 巨觀結構編號與名稱，例如 05-workbench>
colors: { primary: "...", surface: "...", text: "...", muted: "...", success: "...", warning: "...", danger: "..." }
fonts: { display: "...", body: "...", mono: "..." }
radius: { sm: 4px, md: 8px, lg: 12px }
motion: { intensity: 1-10, easing: "...", duration-base: "...ms" }
density: 1-10
---

# <產品名> 設計系統

## 這個產品的視覺個性（三個詞）
## 色彩：何時用主色、何時用中性色、狀態色的語意
## 字型：字級階梯、字重用法、中文字型 fallback（PingFang TC / Noto Sans TC）
## 版面：巨觀結構、間距節奏、卡片與分隔線的使用邊界
## 動效：允許的動作與禁止的動作
## 元件慣例：按鈕、輸入框、表格、空狀態、錯誤狀態
## 明確禁止（本產品不要出現的東西）
```

**中文字型**是每個專案都要處理的：西文字型配對照 ui-ux-pro-max 或 hallmark 給的，中文一律補 `"PingFang TC","Noto Sans TC","Microsoft JhengHei"` fallback，並在 DESIGN.md 記錄。

寫完 `DESIGN.md` 後，用 hallmark 的規則自查一次：主題是否成立、有沒有落入它列的模板慣性。

## 流程 B：原型開工前（每個需求）

`pm-prd.md` 步驟三 §3.0 會呼叫這裡：

1. 讀 `DESIGN.md`。原型的色彩、字型、圓角、間距、動效**全部取自它**，不另外發明。
2. 讀 hallmark 的 SKILL.md 建構規則（不是 audit，是 build 那一段）與它指定主題的參考檔。原型的版面骨架依 `DESIGN.md` 記的巨觀結構，不要每個需求都長一樣。
3. 讀 impeccable 的 `reference/craft-floor.md`——它是動筆前的品質底線清單（對比度、間距節奏、字級、動效克制、狀態齊全、瀏覽器預設樣式改寫）。照做，不用在回覆裡逐條宣讀。
4. 決定介面模式（impeccable 的四種）：**Persuade**（使用者要做決定，例如落地頁、定價）、**Operate**（使用者要完成任務，例如後台、工具、設定）、**Read**（使用者要理解，例如說明、文件）、**Experience**（作品本身就是內容）。不同模式的原型密度與表達強度不同，在原型 HTML 的註解裡記下本需求採用哪一種。
5. 需要動效時，讀對應的 `gsap-*` skill，用 GSAP（CDN `https://cdnjs.cloudflare.com/ajax/libs/gsap/…`）而不是手寫關鍵影格；尊重 `prefers-reduced-motion`。

## 流程 C：原型完成後（設計關卡）

`pm-prd.md` §3.6 一致性自查之後，加做設計關卡：

0. **先看畫面**：用 `python3 scripts/pm_shot.py [需求名]/原型/[需求名]-prototype.html .pm-console/shots/<名稱>.png --size mobile --full` 截圖（網站類用 `--size desktop`），再用 Read 打開 PNG。設計好壞要用看的判斷；只讀程式碼會漏掉「整體很死板」「層次不清楚」這種問題。
1. **hallmark `audit`** 對 `[需求名]/原型/[需求名]-prototype.html` 打分。它輸出的是問題清單，不改檔。
2. 把清單分成兩類：**違反 `DESIGN.md`**（必修）與**品味建議**（列給使用者選）。必修項直接改，改完再 audit 一次。
3. 若使用者要更深的評審，或這個需求是對外的關鍵介面，跑 **impeccable `critique`**（它會用兩個子代理獨立評估再合併；沒有子代理工具時它會標示降級）。critique 最後會問「接下來想改什麼」，把問題原樣轉給使用者。
4. 使用者指名要修某一面向時，用 impeccable 的分項命令：文字階層 → `typeset`、間距節奏 → `layout`、太素 → `colorize` 或 `bolder`、太吵 → `quieter`、動效 → `animate`、文案 → `clarify`、不同裝置 → `adapt`。**每次只跑一個命令**，跑完回到工作台預覽讓使用者看。
5. 交付前一次 **impeccable `polish`**。
6. 每次修改後重新截圖、用 Read 確認，回覆中說明「看到什麼、改了什麼」。

### 畫面死板時的處方

使用者說「太死板」「沒個性」「像範本」時，依序：
1. 截圖看，找出原因：是全部同一種卡片？字級差太小？沒有視覺焦點？大量留白但沒有節奏？插畫佔位像灰色色塊？
2. 讀 impeccable 的 `reference/bolder.md`（拉開層次與對比）與 `reference/delight.md`（加入讓人會心一笑的細節），挑兩三個符合 `DESIGN.md` 的做法。
3. 字型配對或配色太保守時，用 ui-ux-pro-max 查同類型產品的配對（`--domain typography`、`--domain color`）。
4. 動效：依 `DESIGN.md` 的動效強度，用 gsap 做一兩個有意義的小動作（進場、狀態回饋），不是到處都動。
5. 先列給使用者選，選了再改；改完截圖比較前後。

關卡結果在回覆中告訴使用者（audit 分數、修了什麼、哪些建議留給他決定），不另存紀錄檔；使用者明確否決的建議寫進 `.pm-workflow/context/[需求名].md` 的約束段。

## 流程 D：高保真（可選）

走 `pm-prd.md` §3.5 Pencil 路線時：

1. 先讀 `.claude/skills/pencilplaybook/SKILL.md`。它要求先設定畫布解析度（`setup.md`），第一次用時照它的設定精靈走。
2. `set_variables` 的 token map **從 `DESIGN.md` 的 frontmatter 取值**，不要用 pencilplaybook 內建的 7 組預設（那些是沒有 DESIGN.md 時的起點）。
3. 它的感知規則（disabled 40%、hover 至少 8% 亮度差、暗底正文用 `#E2E8F0` 而非純白、56px 以上標題 `-0.03em` 字距）優先於 `pm-prd.md` §3.5 的通用描述。
4. Pencil 匯出的截圖與 HTML 原型共用同一份 `DESIGN.md`，兩邊不一致時以 `DESIGN.md` 為準，改不一致的那一邊。

## 流程 E：原型定稿後回寫設計系統

一個需求的原型定稿、且它引入了新的元件慣例（新的表格樣式、新的空狀態寫法）時，跑 impeccable 的 `document`，讓它從原型程式碼回寫 `DESIGN.md`。這樣下一個需求的原型會沿用，整個產品的介面才會愈做愈一致。

## 插畫佔位

插畫檔還沒到位時，佔位**不是灰色色塊**。佔位要看起來像這個產品的一部分，否則整體會顯得死板：
- 用 `DESIGN.md` 的色票做淡色底（例如主色 8–12% 透明度），加上符合風格的邊框（手繪感就用不規則虛線或圓角較大的描邊）。
- 中間放一句情境說明（「呼嚕在打瞌睡」）與尺寸，字用次要文字色。
- 尺寸與位置要和正式插畫相同，換圖時版面不跳動。

## 邊界與提醒

- **不要在沒有 `DESIGN.md` 的情況下畫原型。** 沒有就先走流程 A2，哪怕只花五分鐘選一個方向。
- **上游 skill 的觸發會互相重疊**（impeccable、hallmark、ui-ux-pro-max 都宣稱管「設計介面」）。本檔已分配職責：方向用 hallmark 與 ui-ux-pro-max，建構底線用 impeccable craft-floor 與 hallmark 規則，評審先 hallmark audit 後 impeccable critique。Claude 依此分工，不要同一件事跑兩套。
- impeccable 的部分命令（`context`、`detect`、`live`）需要它的啟動器第一次執行時下載一個二進位檔；離線環境會失敗，此時它會提示「Context loading did not run」並改讀 `PRODUCT.md`/`DESIGN.md`，照它的降級路徑走即可。
- 所有工具的產出（`PRODUCT.md`、`DESIGN.md`、評審紀錄、給使用者的說明）一律**繁體中文**。上游 skill 內文是英文，讀完用中文回覆。
- 不寫死行業。教育、電商、SaaS 工具、內容媒體、個人品牌的原型都走同一條流程，差異全部落在該專案的 `PRODUCT.md` 與 `DESIGN.md`。
