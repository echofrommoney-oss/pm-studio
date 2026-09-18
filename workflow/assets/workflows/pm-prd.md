---
description: PM需求產出工作流：輸入需求描述，產出PRD+原型+流程圖
---

# PM需求產出工作流

## 觸發方式

當使用者提供一個需求描述時，按以下步驟產出標準化交付物。

---

## 需求目錄歸屬規則（所有步驟的前置約定 · 極度重要）

> **鐵律：產物一律按「需求名」收納到同一個頂層資料夾裡，誰先開工誰負責建這個資料夾，後續步驟一律沿用它，不再另起。**

1. **開工前先查同名目錄**：任何一步（需求採集/PRD/原型/流程圖，乃至需求挖掘、驗收、資料分析）真正落盤前，先看專案根目錄下是否已存在該需求的同名資料夾 `[需求名]/`。
   - **已存在** → 直接沿用，把本步產出放進它對應的子目錄（如 `[需求名]/需求文件/`、`[需求名]/原型/`）。
   - **不存在** → 以需求名新建頂層資料夾 `[需求名]/`，再在其下建本步需要的子目錄。
2. **誰先做誰建家**：本工作流不假設一定先有 PRD。若使用者先做的是需求挖掘或資料分析，則由那一步首次建立 `[需求名]/`；之後做 PRD/原型/流程圖時沿用同一個 `[需求名]/`，所有產物都收在這一個需求目錄內，不重複另建。
3. **子目錄用到才建**：一個需求目錄下的交付物子目錄為 —— `需求挖掘/ 需求文件/ 原型/ 流程圖/ 原型截圖/ 流程圖截圖/ 原型驗證/ 技術規格/ 驗收清單/ 資料分析/ 上線/`，另有放使用者提供之原始材料的 `素材/`（訪談逐字稿、客戶檔案、測試筆記）。**只建立當前步驟實際用到的子目錄**，不預建空資料夾。
4. **交付物只留最新版**：需求目錄裡只放「現在成立的版本」。不建 `v1/ v2/`、不留 `-old`、`-備份`、`-final2` 之類檔名，不在文件裡寫修改紀錄或保留刪除線。舊版的保險由匯出服務自動備份在隱藏目錄 `.handoff/html-backups/`，不是使用者要看的東西。
5. **共享資源不進需求目錄**：`scripts/`、兩個啟動入口（`啟動原型匯出服務.command` / `.bat`）、`.handoff/`、`.pm-workflow/`、`.mcp.json`、`.agents/`、`.claude/`、`PRODUCT.md`、`DESIGN.md` 為所有需求共享，始終留在專案根目錄。
5. **需求名一致性**：同一需求在所有工作流中使用**完全相同**的 `[需求名]`，確保各步產出歸入同一資料夾；命名有歧義時先與使用者確認。

---

## 步驟一：對話式需求採集與確認

採用「靈活對話式」而非固定模板：使用者自由描述需求，AI主動評估、追問、確認。

### 1.1 接收需求

- 使用者可以用**任意形式**輸入需求：一句話、一段描述、截圖、語音轉文字均可
- 不要求使用者填寫固定模板，降低輸入門檻

### 1.2 資訊完整度評估

收到需求後，AI對照以下 **6個關鍵維度** 評估資訊完整度：

| 維度 | 說明 | 重要程度 |
|------|------|----------|
| **問題/背景** | 為什麼要做？現狀資料是什麼？ | ⭐⭐⭐ 必須 |
| **目標** | 做了之後要達成什麼？量化指標？ | ⭐⭐⭐ 必須 |
| **使用者與場景** | 誰在什麼時間、地點和任務場景下使用？ | ⭐⭐⭐ 必須 |
| **現有方案** | 當前做法是什麼？有何不足？ | ⭐⭐ 重要 |
| **業務規則** | 核心規則和限制條件 | ⭐⭐ 重要 |
| **材料** | 埋點字典、設計規範或主色（專案已有 `DESIGN.md` 則不必再問）、已有原型/截圖、參考文件 | ⭐⭐ 重要 |
| **參考/方向** | 競品參考、心中初步方案、設計稿草圖 | ⭐ 加分 |

> **「材料」維度為什麼單獨列：** 埋點章節的欄位名和列舉值必須沿用埋點字典（§2.2 ⑨），主色要麼沿用品牌規範要麼由使用者指定（§2.5 ②），原型列優先用已有高畫質截圖（§2.3）。這些材料**在需求確認階段就該問一次**——否則寫到一半才發現缺字典，只能回頭打斷使用者，或被迫編欄位。
> 追問話術示例：「你手上有沒有①埋點字典②設計規範/主色③現成的原型或介面截圖？有的話發我，沒有我就按規範裡的預設值來，埋點先寫待確認。」

### 1.3 智慧追問或確認

根據評估結果，採取兩種策略：

**資訊不足時 → 追問**
- 只追問缺失的關鍵維度，不重複已有資訊
- 追問控制在 **3-5個問題** 以內，避免資訊轟炸
- 問題要具體，不要問"還有什麼要補充的嗎"這種開放式問題
- 示例：
  > 瞭解了你要最佳化移動端內容發布流程，再確認幾點：
  > 1. 當前提交率大概多少？目標提升到多少？
  > 2. 支援哪些內容型別？（文字/圖片/影片/檔案）
  > 3. 有沒有參考的競品做法？

**資訊充足時 → 反向確認**
- 將理解到的需求**結構化複述**給使用者
- 明確列出：要做什麼、不做什麼、關鍵規則、成功指標
- 請使用者確認無誤後再開始撰寫
- 示例：
  > 和你確認下我的理解：
  > - **目標**：內容發布完成率 60% → 80%
  > - **範圍**：移動端創作者，內容發布場景
  > - **核心改動**：最佳化發布入口+增加草稿提醒機制
  > - **不做**：不改內容審核流程
  > - **產出**：PRD + 原型
  > 以上理解正確嗎？確認後我開始寫。

### 1.3.1 章節裁剪預告（撰寫 PRD 前必做）

> PRD 章節按需求大小裁剪（見 2.2）。在反向確認的同時，AI 必須**根據需求複雜度預判本次 PRD 擬保留/省略哪些章節，並先告知使用者**，確認後再寫。**不得默默省略。**

- 評估方式：核心骨架（專案資訊、需求背景、需求目標、詳細方案）始終保留；其餘 7 個可選章節（需求概述/業務流程圖/互動流程圖/資料埋點/時序圖/上線計劃/附錄）按 2.2 的判斷依據逐一評估留還是省。
- **不要為"章節完整"而新增獨立的異常/邊界章節**——邊界情況一律寫進詳細方案描述列的【邊界說明】（見 §2.3.1），文件級不再設該章。
- 簡單需求直接選定需要的章節並簡要告知即可；只對確有歧義、影響方案取捨的地方提問。使用者已明確要求保留或刪除的章節照辦，不再重複確認。
- 在確認訊息裡附一行「本次章節」說明，例如：
  > 這個需求比較小（僅調整一處文案，無新流程/無新埋點），我打算這樣組織 PRD：
  > - **保留**：專案資訊、需求背景、需求目標、詳細方案
  > - **省略**：業務流程圖（無多步驟流程）、資料埋點（無新事件）、上線計劃（直接全量）
  > 你看這樣可以嗎？或者有哪章你希望保留？
- 使用者若要求保留某章，則照辦；使用者認可後再進入撰寫。
- **產出物聯動**：若省略「業務流程圖」章節，則**不產出** `[需求名]/流程圖/[需求名]-flow.html`（步驟四 4.1–4.5 跳過）；若省略「互動流程圖」章節，則**不產出** `[需求名]/流程圖/[需求名]-screenflow.html`（§4.6 跳過）；兩者都省略則不產出 `[需求名]/流程圖/` 目錄。「時序圖」是 PRD 內的文字章節（Mermaid 原始碼塊，見 §4.7），不產出獨立檔案，省略則整章不寫。其餘可選章節的省略隻影響 PRD 內對應章節，不影響原型產出。

### 1.4 確認後進入下一步

- 使用者確認「沒問題」+ 認可章節組織後，進入PRD撰寫階段
- 本次確認的結論直接寫進 PRD 對應位置（見下表），不另存對話紀錄。只有 PRD 放不下、但後續會話必須知道的東西（使用者的偏好與硬性約束，例如「不要用漸層」「客戶不接受彈窗」），用**覆寫**方式更新隱藏檔 `.pm-workflow/context/[需求名].md`（見 §6.2），它描述的是現況，不是歷史。

> **確認內容 → PRD 落點對映（照這張表搬運，別讓確認過的東西掉在地上）：**

| 1.3 確認時說的 | 寫進 PRD 哪裡 |
|---|---|
| 要做什麼 / 核心改動 | 「三、需求概述」功能清單表 + 「六、詳細方案」各行 |
| 成功指標 / 量化目標 | 「二、需求目標」的 5 列表（無基線寫「待基線確認」） |
| **不做** / 範圍之外 | 「三、需求概述」的**範圍塊**（本期範圍 / 暫不展開）——見 §2.2 ⑤ |
| 背景、現狀資料、證據 | 「一、需求背景」三段式（誰·什麼場景·什麼問題 → 影響 → 證據/來源） |
| 關鍵業務規則、限制條件 | 跨頁共享的 → 「三、需求概述」規則表；單頁的 → 該頁描述列【功能邏輯】 |
| 埋點字典、欄位參考 | 「七、資料埋點」；沒給就寫「待確認」並進結尾待確認清單 |
| 尚不確定 / 待補 / 待某人拍板 | 正文末尾「待後續確認的產品口徑」清單——見 §2.2 ⑧ |
| 章節保留 / 省略清單 | 直接決定 PRD 實際章節（1.3.1），並在交付說明裡複述 |

---

## 步驟二：產出PRD（HTML格式）

### 2.1 格式規範

> **重要：** 輸出格式必須是 **HTML檔案**，而非Markdown。原因：Markdown貼上至Notion 或 Google 文件時會丟失表格格式，HTML經瀏覽器渲染後截圖或複製保留格式效果最佳。

1. 將PRD儲存為 `[需求名]/需求文件/[需求名]-PRD.html`（相對於專案根目錄）
   > **目錄歸屬：** 遵循文件頂部「需求目錄歸屬規則」——先查 `[需求名]/` 是否已存在（可能由先行的需求挖掘/資料分析建立），有則沿用、沒有則新建，PRD 放進其 `需求文件/` 子目錄。
2. HTML中內嵌所有CSS，無需外部依賴，確保離線可用

### 2.2 PRD結構（固定順序，按需求裁剪）

> **先複製骨架，再填內容（極度重要）。** 以 `scripts/prd-content.html`（安裝 skill 時從 `assets/templates/` 裝進專案；未安裝時直接用 skill 目錄裡那份）為起點——裡面已寫好正確的類名、各表表頭、`colgroup` 列寬、`.desc-block` 結構與 `data-preview` 佔位。**不要從零手寫 HTML**：歷史 PRD 的翻車（描述列用 `<br>` 硬換行、表頭列數寫錯、漏 `colgroup`）幾乎全部源於憑記憶重建結構。**寫完必須跑一次 `scripts/validate_prd.py`（見 §5.2），紅了先修再交付。**

**參考結構（自上而下的固定相對順序）：**

```
文件標題（h1.doc-title） → 副標題（p.doc-sub：目標使用者 · 涉及端 · 版本號 · 最後更新日期）
📋 專案資訊
一、需求背景 → 二、需求目標 → 三、需求概述（功能清單）
四、業務流程圖 → 五、互動流程圖 → 六、詳細方案 → 七、資料埋點 → 八、時序圖
（上線計劃、附錄：確有需要時才補，排在最後）
```

**① 核心骨架（任何需求都必出，不可省）：**

| 章節 | 說明 |
|------|------|
| 📋 專案資訊 | 專案名/版本號/最後更新/負責人等文件元資訊，**獨立成表** |
| 一、需求背景 | 為什麼要做（寫法見下方「⑥ 需求背景」） |
| 二、需求目標 | 要達成什麼（寫法見下方「④ 需求目標」） |
| 六、詳細方案（四列表格：一級模組 \| 二級功能 \| 原型 \| 描述） | PRD 核心，絕不省 |

> **PRD 只呈現最新版本（極度重要）。** 不設版本記錄／修訂紀錄章節，不寫「v1.1 新增」「原為…」「（已修改）」，不留刪除線。讀者打開 PRD 看到的就是現在要做的東西；最後更新日期寫在專案資訊與副標題。

**② 按需裁剪（AI 根據需求判斷是否需要，可整章省略）：**

| 章節 | 建議省略的判斷依據 |
|------|----------|
| 三、需求概述（功能清單表格） | 功能點極少（如僅 1-2 個）時可省，直接進詳細方案 |
| 四、業務流程圖（嵌入互動式 iframe） | 無多步驟流程、無分支/狀態流轉的小需求 → 省 |
| 五、互動流程圖（全部核心介面拼成一整張帶箭頭跳轉鏈路圖，嵌入 iframe，見 §4.6） | 核心介面 ≤2 個、或頁面間無跳轉鏈路且無狀態流轉 → 省 |
| 七、資料埋點 | 不涉及新增埋點事件 → 省 |
| 八、時序圖（Mermaid **原始碼文字塊**：端側互動編排總時序 + 關鍵物件狀態圖，研發/測試向，見 §4.7） | 無複雜端側編排的簡單需求（無語音/流式/多端協同/複雜動效狀態機）→ 省 |
| 上線計劃與灰度策略 | 預設不寫；小需求直接全量上線、無灰度 → 不出現 |
| 📎 附錄（名詞解釋/參考資料等） | 預設不寫；沒有非放不可的補充資料 → 不出現 |

> **不新增獨立的異常/邊界章節（極度重要）。** 邊界情況一律寫進詳細方案描述列的【邊界說明】（見 §2.3.1），跟著它所屬的功能走。文件級不設「異常與邊界處理」章。

> **編號說明：** 章節編號跟隨實際保留的章節**連續重排**，不要因為省略了「四、業務流程圖」就讓正文出現"三、五"的跳號。即按保留章節重新順序編號，但順序仍遵循上表自上而下。

> **裁剪須先告知（極度重要）：** AI **不得默默省略章節**。在需求確認階段（步驟一 1.3）必須先列出"本次 PRD 擬保留哪些章節、省略哪些、各自原因"，經使用者確認後再撰寫。詳見 1.3.1。簡單需求直接選定並簡要告知即可，不必逐章徵詢。

**③ 各模組的固定表頭（列名與列數不可改）：**

| 模組 | 固定格式 |
|------|----------|
| 📋 專案資訊 | 獨立**雙列**表格（欄位 \| 值）。常用欄位：專案名稱、版本號、最後更新、文件負責人、需求狀態、目標使用者、涉及端、功能入口、關聯檔案；業務專有欄位按需增行 |
| 三、需求概述（功能清單） | ① 範圍塊（見 ⑤）→ ② 功能清單表：模組 \| 一級功能 \| 說明 → ③ 跨頁共享規則表（按需，見 §2.3.1 ③） |
| 六、詳細方案 | 一級模組 \| 二級功能 \| 原型 \| 描述（詳見 §2.3） |
| 七、資料埋點 | 序號 \| 埋點名 \| 埋點中文名 \| 埋點型別 \| 埋點參數 \| 參數值（詳見 ⑨） |
| 八、時序圖 | 可複製的 Mermaid **原始碼文字塊**，按需（詳見 §4.7） |

> 同一模組跨多行時用 `rowspan` 合併單元格。主色可隨需求、品牌與產品定位調整（見 §2.5），**但表頭文案和列數不能改**。

**④ 需求目標怎麼寫（極易寫歪）：**

- **先寫使用者獲得的結果和業務價值，再寫衡量方式。** 不要用"完成開發""新增入口""上線 XX 功能""跑通並驗證"這類**實現動作/任務清單**替代目標——那是任務，不是目標。
- 能量化的目標寫成一張表，欄位固定為：**使用者結果 \| 衡量指標 \| 統計口徑 \| 預期方向 \| 目標值**。
  - 統計口徑寫清分子分母或觀察方式（如"提交成功次數 / 進入提交流程次數"）。
  - **基線和具體目標值沒有真實資料時留空或寫「待基線確認」，絕不編造**（不許出現"提升 30%"這種拍腦袋數字）。
- 不能直接量化的目標，寫成**可觀察、可驗收的結果**，避免"提升體驗""賦能業務""增強心智"等無判據表述。
- **正反對照（照這個改）：**

  | | 寫法 |
  |---|---|
  | ❌ 反例 | "本期目標是**跑通並驗證**：從內容列表頁進入、權限前置、發布後產出資料報告的完整鏈路；四類審核結果判斷準確；發布引導不重複打擾；異常都有兜底" |
  | ✅ 正例 | 總目標：**讓創作者一次把內容發出去，減少發布中途的放棄**。<br>表：使用者結果=創作者願意把一篇內容寫完併發布 \| 衡量指標=發布完成率 \| 統計口徑=成功發布數 / 進入發布流程數 \| 預期方向=↑ \| 目標值=待基線確認<br>使用者結果=發布過程不再卡頓 \| 衡量指標=平均發布耗時 / 中途退出率 \| 統計口徑=從進入發布到成功的時長中位數 / 退出數 ÷ 進入數 \| 預期方向=↓ / ↓ \| 目標值=待基線確認 |

  > 反例裡的"四類審核結果判斷準確""不重複打擾"是**驗收條件**，不是目標——它們該進 §5.2 檢查清單和描述列的【功能邏輯】/【邊界說明】，不該佔著需求目標這一章。
- 需求背景裡引用資料時，同樣標註事實來源；沒有驗證過的增幅不要寫進文件。

**⑤ 需求概述（功能清單）怎麼寫：**

這一章不只是"功能列表"。按需包含三塊，順序固定：

1. **範圍塊（建議保留）——把"做什麼 / 不做什麼"寫死。** 這是 PRD 裡最能防扯皮的內容，也是步驟一 1.3 反向確認裡"**不做**：xxx"唯一的落地點——**確認完不落進文件，就等於沒確認**。
   - 「本期範圍」：這次交付覆蓋哪些模組/端/場景（1–5 條）。
   - 「不做什麼 / 暫不展開」：明確本次**不做**的相鄰功能，以及**留到後續**的部分（1–5 條）。寫清"為什麼這次不做"（如"依賴 XX 前置能力，本期不涉及"）。
   - 以文字塊或卡片形式呈現皆可；**內容必寫，視覺形態由需求定**。
2. **功能清單表**（表頭固定 `模組 | 一級功能 | 說明`）——本期交付的功能全景。
3. **跨頁共享規則表（按需）**——被多個頁面共用的規則（獎勵檔位、計費口徑、權限矩陣、頻控等），用 `h3` + 小表承載（如 `3.1 簽到獎勵檔位`），供詳細方案各格引用。詳見 §2.3.1 第三步。

> 若省略「需求概述」整章，**範圍塊與共享規則表要挪進「一、需求背景」之後再省**——功能清單表可以省，但"不做什麼"和"共享規則"不能省，它們是詳細方案的前提。

**⑥ 需求背景怎麼寫（三段式）：**

按這個順序寫，一段一句主旨即可，不要寫成流水賬：

1. **誰在什麼場景遇到什麼問題** —— 具體到角色與時機（如"新註冊的創作者，首次發布內容時"），不寫"使用者希望更好用"這類泛化描述。
2. **造成什麼影響** —— 對使用者、對業務各是什麼損失（如"使用者在發布中途放棄，運營看不到內容為什麼沒發出去"）。
3. **證據是什麼** —— 資料、使用者反饋、競品做法、調研結論；**沒有證據就明說"暫無資料支撐，本次基於 XX 判斷"**，不要編。有資料時補一行「事實來源：…」。

**⑦ 一行 = 一個介面（極度重要）：**

詳細方案的一行對應**一個介面或一個狀態變體**，不是"一個操作"、也不是"一個功能包"。判定：**這一行的原型列能不能放出一張對應的圖？** 放不出來說明粒度錯了。

- 一個二級功能若跨多個介面（如"簽到"含 簽到頁 + 簽到成功彈層 + 補籤彈層），**拆成多行**，每行一個介面/狀態，原型列各放各的圖。
- 同一個介面的多個狀態變體（未解鎖/已完成）算**同一行**，在【頁面元素】裡逐狀態說明，原型列放該介面的圖或對應狀態 hash。
- 一級模組用 `rowspan` 覆蓋屬於它的多行；**不要為了少寫幾行把多個介面塞進一格**——那會讓原型列無處可放、評審者也無法按圖核對。

**⑧ 結尾「待後續確認的產品口徑」清單（建議保留）：**

PRD 全篇寫"待確認"的地方（埋點字典未給、文案待定、規則待補、@某人），**在正文最後集中列一份清單**，每條寫：事項 + 卡在誰那裡 + 影響什麼。

- 規範多處要求"沒把握就寫待確認"，但如果散落在各表格裡，評審者要通讀全文才能湊齊——集中列出才算真正"可跟進"。
- 迭代時據此一眼看出哪些問題已關閉、哪些還懸著；關閉的條目不刪，標記「已確認：xxx」。
- 這一章**不佔用章節編號**（不是"九、"），就是正文末尾的一個 `h3` 列表。

**⑨ 資料埋點怎麼寫：**

- 埋點名用**簡短、可理解的英文 snake_case**：`button_click`、`answer_submit`、`report_view`。依據功能含義命名，避免無意義縮寫。
- 通用事件（如 `button_click`）必須有已存在的參數能區分物件；否則加**簡短業務字首**避免歧義（如 `paper_upload_click`）。
- 參數與參數值**優先沿用使用者提供的埋點字典或參考文件**。缺少參考時可以詢問一次；使用者暫未提供就寫「待確認」，**不猜欄位名、不編列舉值**。
- 埋點型別要區分**曝光 / 點選 / 提交結果**等實際觸發點——**點選 ≠ 成功結果**，兩者需要分別埋點時就分兩條。
- 每行六列都要填。參數或參數值暫缺時，在對應格里寫「待確認（使用者提供參考）」，**不要留空格**——空格分不清是"沒有"還是"漏了"（校驗腳本會把空列當錯誤）。

### 2.3 詳細方案表格格式

**必須使用四列表格**，格式如下：

| 一級模組 | 二級功能 | 原型 | 描述 |
|----------|----------|------|------|
| （使用rowspan合併相同模組） | 具體操作 | 高畫質截圖 或 可互動 iframe | 結構化分塊描述，格式見 §2.3.1 |

- 一級模組使用 `rowspan` 合併跨行單元格；單元格類名建議 `td.mod / td.fn / td.proto / td.desc`，便於定位與樣式。
- **原型列兩種形態都合法，按素材實際情況選，不強制把截圖換成 iframe：**
  - **高畫質截圖**：`<img class="proto-shot" src="../原型截圖/xxx.png" alt="…" width="1672" height="941">`，下方可跟一行 `<p class="asset-note"><a href="../原型/[需求名]-prototype.html#page-id">開啟可點選原型</a></p>` 把靜態圖和活原型串起來。**`width`/`height` 寫真實畫素值**（避免載入抖動，也讓 §2.8 複製出圖時尺寸正確）。
  - **可互動 iframe**：等比縮放容器包裹，寫法見 §3.3。
- **每個 `<tr>` 都要帶 `data-preview="<對應原型頁 value>"`**，供 §2.6 ⑧ 的滾動聯動定位（寫在 `<tr>` 上比寫在 `td.mod` 上更穩，合併單元格時不會漏行）。新增行必須同步補這個屬性（見 §5.3 第 15 項）。

#### 2.3.1 描述列結構化分塊（必做）

> 描述列按「頁面」維度寫，採用**固定分塊結構**：塊標題用【】標註，塊內條目編號 `1、2、3…`，塊與塊之間空一行。先把頁面本身說清楚，再說互動，最後按需補規則與邊界。**廢棄舊的 `0、功能說明 / 1、xxx` 鬆散編號敘述法。**

**寫之前先按下面 ①②③ 三步判定該寫哪些塊——不要每格都寫滿：**

> **核心原則：一個塊只寫"屬於這一頁的東西"。** 判斷某條規則該不該進這一格的【功能邏輯】，只問一個問題——**把這一頁刪掉，這條規則還成立嗎？**
> - **仍成立**（規則屬於整條業務鏈路，只是恰好在這頁被觸發）→ **不屬於本頁**，上提到「三、需求概述」的規則表（見 ③），本格最多留一句引用。
> - **不成立**（離開這頁就無從談起）→ **屬於本頁**，寫進對應塊。
>
> **典型的"其實不屬於本頁"的規則**（最容易被每頁抄一遍）：簽到階梯 `1/3/7 天`的獎勵檔位、累計型成長值/積分/額度的增減口徑、獎勵發放與到賬時機、跨端或跨角色的權限矩陣、全域性頻控與限額。**這類規則只在一處寫全（需求概述的規則表），各頁面格不重複抄寫，需要時用一句"獎勵檔位見 3.1 規則表"帶過。**

**① 兩個必出塊**（每格都有，沒有例外）：

| 分塊 | 寫什麼 |
|------|--------|
| 【頁面元素】 | 該頁面**所有**元素自上而下逐一說明：佈局區塊、控制元件、文案、資料展示、入口/懸浮件。要求評審者只讀這一塊就能在腦中還原整個頁面 |
| 【互動說明】 | 逐條描述該頁面的互動行為，統一用「操作 → 結果」句式（點選/長按/滑動/輸入 → 跳轉/彈層/Toast/狀態變化） |

**② 按需塊，逐條對照"本頁是否真的有"再決定寫不寫。判定條件不成立就整塊不出現——不寫"無"，不寫"同前文"，不為了格子整齊補一句湊數。**

| 分塊 | 寫什麼 | 出現條件（**同時滿足**才寫） |
|------|--------|------------------------------|
| 【功能邏輯】 | **僅屬於本頁**的規則：這一頁自己的次數扣減、排序、命中/推薦、優先順序、頻控 | ① 該規則離開本頁就不成立；② 不是跨頁通用的業務鏈路規則（後者上提需求概述規則表） |
| 【邊界說明】 | 該頁面自己的邊界情況逐條窮舉：空態、極值/上限、權限不足、網路異常、超時、重複操作、併發衝突 | 本頁確實存在邊界場景（幾乎每一頁都有，但只寫本頁的，不要說"同其他頁"） |
| 【資料與內容規則】 | 展示內容的產品口徑：資料從哪來（使用者視角）、取數/排序規則、示例資料口徑 | 列表頁、報告頁等**資料驅動**頁面。純操作頁（表單、設定）不寫 |
| 【前置條件與權限】 | 進入本頁/觸發本功能的前置條件：登入態、剩餘額度、地區/語言設定、角色可見性差異 | 本頁有準入門檻或角色差異。**全域性權限矩陣屬於需求概述規則表，不在此重複** |
| 【文案規範】 | 關鍵文案的**確切措辭**：按鈕文字、Toast、空態文案、彈窗標題/正文 | 文案需要精確鎖定時。**逐字文案已在【頁面元素】寫全的，此塊不重複**，只寫需要額外鎖定的動態文案（含變數的、多分支的） |
| 【策略說明】 | 分層/分流、灰度人群、投放與召回條件等策略參數 | 本功能由策略驅動、且策略參數需要產品定值。純展示性描述不寫 |

> **不寫"同前"**。描述列會被單獨複製進評審文件，讀者可能只看這一行。"同上""詳見 1.2"這類指代會讓評審者來回翻頁。
>
> **【功能邏輯】寫得太滿是最常見的兩種走偏**：一是把跨頁共享的鏈路規則每頁抄一遍（該上提）；二是把實現細節寫進來（屬於 ⑤ 的禁令，該刪）。**一個格子同時出現四個以上分塊，就該回頭核一遍——大機率混進了不屬於本頁的內容。**

**③ 跨頁共享規則上提到「三、需求概述」。** 被上提的規則在概述章節用 `h3` + 小表承載（如 `3.1 簽到獎勵檔位`），詳細方案各格只引用不展開。這樣改規則時只改一處，也不會出現三個頁面的數字對不上。

**④ 逐條換行是硬要求（最常見的翻車點）：**
- **每個頁面元素獨立一個編號段落；每段完整互動邏輯獨立一個編號段落。禁止把多個編號拼成一個長段落**（`1、xxx；2、yyy；3、zzz` 擠在一行 = 不合格）。
- HTML 結構固定為 `.desc-block` 容器：塊標題 `<b>【頁面元素】</b>` 之後，**每一條都是獨立的 `<p>` 或 `<li>`**；編號內部還有分支時，另起巢狀列表或新段落，不要用頓號硬接。

```html
<td class="desc">
  <div class="desc-block"><b>【頁面元素】</b>
    <p>1、頂部導航欄：標題"檔案分析"+左側返回按鈕</p>
    <p>2、額度卡片：文案"你的分析剩餘額度"+剩餘次數"8/10"</p>
  </div>
  <div class="desc-block"><b>【互動說明】</b>
    <p>1、點選歷史列表項 → 進入該檔案的分析報告頁</p>
  </div>
</td>
```

**⑤ 硬性禁令（極度重要）：** 描述列**不得出現任何技術介面說明**——不寫 API 名稱、請求參數、欄位 key、錯誤碼、表結構、快取/儲存方案。一律用產品語言表述：寫「上傳成功後當日剩餘額度減 1」，不寫「呼叫 quota/deduct 介面扣減」。技術欄位只允許出現在資料埋點、研發向時序圖等對應章節。

**⑥ 示例（一行描述列的完整形態）：**

```
【頁面元素】
1、頂部導航欄：標題"檔案分析"+左側返回按鈕
2、額度卡片：文案"你的分析剩餘額度"+剩餘次數"8/10"
3、分析歷史列表：每項含檔名稱、狀態標籤、建立日期
4、右下角懸浮上傳按鈕：常駐

【互動說明】
1、點選歷史列表項 → 進入該檔案的分析報告頁
2、點選懸浮上傳按鈕 → 喚起"選擇檔案型別"半屏彈層

【功能邏輯】
1、分析歷史僅展示當前使用者自己的記錄，按建立時間倒序
2、單次分析任務未結束前，再次上傳入口置灰（避免併發消耗額度）

【邊界說明】
1、無歷史記錄 → 展示空態插畫+文案"暫無分析記錄"+上傳引導按鈕
2、剩餘額度為 0 → 上傳按鈕置灰，點選 Toast 提示"今日額度已用完"
3、網路異常 → 列表載入失敗，展示重試按鈕
```

> 注意這個例子**沒寫**"分析扣減 1 次額度"這類規則放在【功能邏輯】裡——那是跨頁共享的計費口徑，正確位置是需求概述的規則表（見 ③），本頁只寫"再次上傳置灰"這種離開本頁就不成立的行為。

> **一致性聯動：** 原型 ↔ PRD 對齊（3.1 第12條、3.6 自查）以【頁面元素】【互動說明】【文案規範】的內容為對照基準；【邊界說明】就是這份 PRD 裡邊界情況的**唯一歸屬地**（不再有文件級異常章節），與時序圖的異常 Note（若保留）保持口徑一致。

### 2.4 寫作風格

- 先圖（原型）後文
- 逐條編號描述互動規則；詳細方案「描述」列一律按 §2.3.1 的【】分塊結構組織
- **極度重要（全文件可編輯）：** PRD **整篇正文**都要能在瀏覽器裡直接改——不再只讓「描述」列可編輯。具體的可編輯範圍、排除項、表格增刪行與行列拖曳，全部由 **§2.7 通用編輯模組** 統一實現並固化為必做項；§2.4 這裡只描述配套的儲存動作。
- **極度重要：** 必須在 HTML 底部插入“懸浮動作面板”，程式碼大綱如下（AI需補全標準JS）：
  1. 編輯變更追蹤：所有可編輯塊的 `blur` 事件，如內容相對 `data-original` 被修改，則為該塊加 `data-changed="true"` 屬性和綠色 `edited-cell` 高亮類（追蹤邏輯由 §2.7 模組統一提供，無需另寫）。
  2. 頁面右下角的懸浮 `.save-btn-container` 區只保留一個按鈕：“儲存並通知AI”。截圖匯出功能已移至原型和流程圖各自的 HTML 中，PRD 不再承載匯出功能。另：**頁面左下角**固定一個「📋 一鍵複製全文」按鈕（實現見 §2.8），與右下角儲存按鈕分居兩側、互不遮擋。
  3. 點選儲存按鈕時，抓取 `document.documentElement.outerHTML` 並呼叫系統的檔案儲存控制代碼直接物理存檔覆蓋當前 PRD HTML 檔案。**因為儲存抓的是 `outerHTML`，§2.7 把列寬/行高寫成 inline px、把編輯寫回 DOM，儲存即自動持久化，無需額外儲存邏輯。**
- 黃色高亮標註關鍵變更點（用 `.alert` 樣式塊）
- **重點靠"適量"標出來，不是靠全段加粗。** 只給關鍵業務規則、門檻數值、關鍵狀態、數量限制和風險點加粗或高亮；整段加粗等於沒有重點。
- 必須覆蓋邊界情況——寫進對應功能的【邊界說明】（§2.3.1），不另起文件級異常章節。
- **不編造資料。** 背景/目標裡引用的數字要麼有出處（補一行「事實來源：…」），要麼寫「待基線確認」；不寫未經驗證的增幅。

### 2.5 版式與表格排版

**① 頁面版式與字型：**
- 正文預設最大寬度 `1400px`；正文容器 `#prdContent` 約 `1336px`。雙欄開啟時右側面板約 `520px`（見 §2.6）。
- 正文、圖表標籤、表單與按鈕**優先使用 `Microsoft YaHei` / 微軟雅黑**，後面跟上通用中文後備字型：
  ```css
  body { font-family: "Microsoft YaHei", "微軟雅黑", "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", sans-serif; }
  ```
  Mac 上通常沒裝微軟雅黑、會落到後備字型——**如實說明即可，不要謊稱"與 Windows 完全一致"**。
- 標題層級固定：`h1.doc-title` 30px/800，`h2` 21px/800 且帶 `border-left:5px solid var(--pm-accent)` 的章節豎線，`h3` 16px/700。表頭淺底、表體白底，保持參考 PRD 的邊距與資訊密度。
- 標題下方 `p.doc-sub` 寫「目標使用者 · 涉及端 · 版本號」一行副標題。

**② 主色用 CSS 變數收口（可隨需求/品牌調整，但只改顏色、不改結構）：**
```css
:root{
  --pm-accent:#5b5bd6;                                            /* 唯一需要改的主色 */
  --pm-ink:#1f2937;
  --pm-heading:color-mix(in srgb, var(--pm-accent) 38%, #1f2937); /* 標題色 */
  --pm-line:color-mix(in srgb, var(--pm-accent) 13%, #fff);       /* 表格描邊 */
  --pm-soft:color-mix(in srgb, var(--pm-accent) 9%, #fff);        /* 表頭淺底 */
  --pm-panel:520px;
}
```
> 換主色只改 `--pm-accent` 一處，標題色/描邊/表頭底色跟著推導，不用逐處調。**表頭文案與列數不允許跟著改**（見 §2.2 ③）。

**③ 文件級 `<style>` 的位置（配合一鍵複製全文）：** 把這份文件專屬的 `<style>` 放在 `<main id="prdContent">` **內部的第一個子元素**，而不是 `<head>` 裡。§2.8 複製全文抓的是 `#prdContent` 的 HTML，樣式在容器內才會被一併帶走，粘到Notion/Google 文件才不掉格式。全域性互動骨架的樣式（懸浮按鈕、側欄、拖曳手柄）仍留在 `<head>`，避免被複製出去。

**④ 表格：**
- 表格使用 `table-layout: fixed`
- 各表推薦列寬（用 `<colgroup><col>` 承載，便於 §2.7 拖曳時改 `col.style.width`）：

  | 表 | 列寬 |
  |---|---|
  | 專案資訊 `.meta-table` | 首列 `160px`，值列自適應 |
  | 詳細方案 `.scheme-table` | `100px / 120px / 360px / 自適應` |
  | 資料埋點 `.tracking-table` | 序號 `65px`、埋點名 `145px`、埋點型別 `90px`，其餘自適應 |
- **不要**用 CSS `resize`（`resize:both/horizontal`）來調列寬行高——它會留拖曳殘影、破壞表格截圖。列寬/行高改用 **§2.7 的專用拖曳手柄**：手柄 `hover` 才出現、拖曳寫 **inline px** 尺寸隨 `outerHTML` 持久化、滑鼠移開即隱藏，靜態截圖保持乾淨。
- `td` 設定 `word-break: break-word` 避免文字溢位
- **極度重要（原型預覽體驗）：** 原型列若用 iframe，不要按原始尺寸硬塞進單元格，尤其是 16:9 桌面端或工作台原型——必須用"等比例縮放容器"包裹（見 §3.3）。若用高畫質截圖，給 `img.proto-shot` 設 `max-width:100%; height:auto`，並保留真實 `width`/`height` 屬性。

### 2.6 右側雙欄互動原型預覽（必做）

> **背景（踩坑記錄）：** 這套右側「互動原型預覽」面板過去只存在於少數歷史 PRD 成品裡，未沉澱成規範，導致從零寫 PRD 時容易漏掉（2.4 又只讓放儲存按鈕）。**故在此固化為必做項：每份 PRD 都要內建該面板。** 它與「六、詳細方案」表格裡的靜態原型列（截圖/小 iframe）不同，這是一個全域性常駐、可切頁、可縮放的活預覽 dock。

**目標：** PRD 左側正文 + 右側一個可關閉的深色面板，面板內嵌**活的原型 iframe**，用頂部下拉切換頁面/場景，支援拖曳改寬，整體等比縮放。**雙欄預設關閉**——PRD 開啟時是乾淨的正文閱讀態，原型面板由使用者點右下角「雙欄預覽」主動開啟。理由：多數人開啟 PRD 是為了讀需求，不是為了看原型；預設展開會擠掉正文寬度、並在每次滾動時過載 iframe，反而干擾閱讀。

**① HTML 結構：**
- **`<body>` 不帶 `dual-pane`（預設關閉）。** 只有使用者點開關、或 §2.6 ⑩ 的深連結命中時才加上。**不要因為原型目錄裡有檔案就自動開啟**——面板內容與正文寬度是兩件事。
- `.prototype-sidebar`（`position:fixed; right:0; top:0; height:100vh; 深色 #1a1a2e; flex 縱向`）內含：
  - `.sidebar-header`：`✕` 關閉按鈕（`onclick="toggleDualPane()"`）+ 標題「互動原型預覽」。
  - `.preview-context`：一行說明（如收口範圍、或"完整互動依賴後端、靜態預覽僅還原介面"等真實約束，**不誇大成全功能可跑**）。
  - `.page-selector > select#pageSelect`（`onchange="switchPage(this.value)"`）。
  - `.preview-zoom`：一行縮放控制元件 `－ / 百分比 / ＋ / 適配`（詳見 ⑨）。
  - `.device-shell > .device-wrapper > iframe#prototypeFrame`。
  - `.prototype-resizer`：面板左緣豎向拖曳手柄。
- `.fab-group`（`position:fixed; right:28px; bottom:28px`）：含「雙欄預覽」開關按鈕 +「💾 儲存並通知AI」按鈕。**雙欄開啟時整組右移**到面板左側：`body.dual-pane .fab-group { right: calc(var(--panel-w) + 28px); }`。（即 2.4 的儲存按鈕併入此 fab-group，不再單獨懸浮。）
  - **開關按鈕的兩個狀態都要有明確文字**，不要只靠顏色區分：關閉態顯示「雙欄預覽」，開啟態顯示「收起預覽」（或加 `aria-pressed`）。使用者不知道當前是開還是關時，面板會被當成 bug 而不是功能。

**② CSS 關鍵：**
- `:root { --panel-w: 520px; }`
- `body.dual-pane { margin:0!important; max-width:none!important; padding-right: calc(var(--panel-w) + 36px); }`（正文讓出右側面板寬度）
- `body.dual-pane .prototype-sidebar { display:flex; }`（預設 `.prototype-sidebar{display:none}`）
- **`.device-wrapper iframe { transform-origin: top left; }` 只在 `.dual-pane` 下才需要**——面板關閉時 iframe 不渲染，`scalePreview()` 裡對 `clientWidth` 為 0 的 `shell` 要有兜底（見 ③ 的 `Math.max(120, ...)`，別算出 `scale:0` 把 iframe 縮成一條線）。
- `.device-wrapper iframe { transform-origin: top left; }`、`.device-shell { overflow:auto; }`（豎屏長頁可滾）
- **`.device-wrapper { flex: 0 0 auto; }`（極易漏，漏了縮放就是壞的）**：`.device-shell` 通常是 `display:flex` 居中，而 flex item 預設 `flex-shrink:1` —— JS 明明把 wrapper 設成 1170px，實際渲染仍被壓回 480px，於是**放大後既不出捲軸、原型還被裁掉一半**。實測踩過：必須顯式禁止收縮。放大後若還想從頂部開始看，配 `.device-shell { align-items:flex-start; }`。

**③ JS 關鍵（內嵌 PRD 底部）：**
```js
// 每項：{value,label,url,w,h}。url 指向可定址原型；w/h = 該頁邏輯尺寸
const CATALOG = [ { value:'p1', label:'P1 · xxx', url:'../原型/xxx-prototype.html#p1', w:375, h:812 }, /* ... */ ];
let previewPage = CATALOG[0].value;
let previewZoom = null;   // null = 適配寬度；數字 = 手動縮放倍率（見 ⑨）
function currentCfg(){ return CATALOG.find(o=>o.value===previewPage) || CATALOG[0]; }
function scalePreview(){
  const shell=document.querySelector('.device-shell'), wrap=document.getElementById('deviceWrapper'), frame=document.getElementById('prototypeFrame');
  const cfg=currentCfg(), innerW=Math.max(120, shell.clientWidth-40);
  const fit=innerW/cfg.w, scale=(previewZoom==null)? fit : previewZoom;
  frame.style.width=cfg.w+'px'; frame.style.height=cfg.h+'px'; frame.style.transform='scale('+scale+')';
  wrap.style.width=Math.round(cfg.w*scale)+'px'; wrap.style.height=Math.round(cfg.h*scale)+'px';
  const lab=document.getElementById('previewZoomLabel');
  if(lab) lab.textContent=Math.round(scale*100)+'%'+(previewZoom==null?' · 適配':'');
}
function switchPage(v){
  previewPage=v; const sel=document.getElementById('pageSelect'); if(sel) sel.value=v;
  if(!document.body.classList.contains('dual-pane')) return;          // 關閉態只記狀態，不載入 iframe
  const f=document.getElementById('prototypeFrame'); if(f) f.src=currentCfg().url;
  requestAnimationFrame(scalePreview); setTimeout(scalePreview,350);
}
function toggleDualPane(){
  const on = document.body.classList.toggle('dual-pane');
  const btn = document.getElementById('dualPaneToggle'); if(btn) btn.textContent = on ? '收起預覽' : '雙欄預覽';
  if(on){ const f=document.getElementById('prototypeFrame'); if(f && !f.src) f.src=currentCfg().url;   // 首次開啟才載入 iframe，關閉態不載入
          requestAnimationFrame(scalePreview); setTimeout(scalePreview,350); }
}
// 拖曳 .prototype-resizer 改 --panel-w（clamp 如 380..min(900, innerWidth-360)）後 scalePreview()
window.addEventListener('resize', scalePreview);
// 預設關閉：load 時只準備下拉，不載入 iframe、不加 dual-pane。深連結 #preview=<page> 才自動開啟（見 ⑩）
window.addEventListener('load', ()=>{ /* renderSelect() */ const m=location.hash.match(/preview=([\w-]+)/); if(m){ previewPage=m[1]; toggleDualPane(); } });
```

> **預設關閉的實現要點：** iframe 的 `src` 在關閉態**留空**（首次開啟才賦值），否則面板不顯示、原型卻在後台載入，白吃資源；`switchPage()` 在關閉態只更新 `previewPage` 變數、不動 `src`。⑧ 的 scroll-spy 已限定 `body.dual-pane` 才生效，無需再改。

**④ 橫屏適配（極度重要）：** 16:9 桌面端或工作台原型邏輯尺寸可用 `w:1280,h:720`；豎屏/手機頁用自身尺寸（如 `375×812`）；報告等長頁用其真實高度（如 `480×1360`）。各頁按面板內寬 `scale`，`.device-shell` 溢位可滾，**不要把橫屏頁硬塞成手機豎屏**。

**⑤ iframe 取材：** 優先指向**可按 hash/場景定址**的原型（`prototype.html#page-id`）。若真實產品依賴後端無法靜態執行（如實時音影片或硬體協同鏈路），可指向「截圖版/狀態版」HTML（每場景一個 hash，活 DOM 還原 UI），並在 `.preview-context` 據實說明互動限制。

**⑥ 與 3.4.2 聯動：** 原型內切頁時 `postMessage({type:'page-changed',page})`，PRD 既有監聽同步 `#pageSelect`（向後相容）。

**⑦ 裁剪與迭代：** 僅 1 個原型頁時可省下拉、只留單頁預覽，但**面板本身必須內建**（只是預設收起）；新增頁必須同步往 `CATALOG` / `#pageSelect` 加項（見 5.3 第 15 項「PRD 雙欄預覽下拉項」）。

**⑧ 滾動聯動 / scroll-spy（必做）：** 左側正文滾到某模組，右側互動預覽**自動切到該模組對應的原型頁**（滾到「介面1」→預覽定位介面1，滾到「介面3」→跟隨切介面3），不用手點下拉。
- **取材：** 給「六、詳細方案」**每個 `<tr>`** 加 `data-preview="<CATALOG 裡對應頁的 value>"`（寫在行上比寫在 `td.mod` 上穩——`rowspan` 合併時不會漏行）。新增模組/頁/行時必須同步補這個屬性（併入 5.3 迭代清單）。選擇器相應用 `.scheme-table [data-preview]`，行與單元格兩種寫法都能命中。
- **啟用判定：** 監聽 `window` 滾動（`requestAnimationFrame` 節流），取視口上方約 35% 處「啟用線」**之上最後一個** `data-preview` 元素為當前模組；`v !== previewPage` 時才 `switchPage(v)`（避免反覆過載 iframe）；僅 `body.dual-pane` 開啟時生效。
- **不與使用者打架：** 監聽 `#pageSelect` 的 `change`，使用者**手動選頁**後短暫（~4s）暫停聯動（`switchPage` 程式化改 `select.value` 不會觸發 `change`，故自動切不會誤鎖）。

```js
function initPreviewScrollSync(){
  var nodes = Array.prototype.slice.call(document.querySelectorAll('.scheme-table [data-preview]'));
  if(!nodes.length) return;
  var lockUntil = 0, sel = document.getElementById('pageSelect');
  if(sel) sel.addEventListener('change', function(){ lockUntil = Date.now() + 4000; });
  function pickActive(){
    if(!document.body.classList.contains('dual-pane') || Date.now() < lockUntil) return;
    var line = window.innerHeight * 0.35, current = null;
    for(var i=0;i<nodes.length;i++){ if(nodes[i].getBoundingClientRect().top <= line) current = nodes[i]; }
    if(!current) current = nodes[0];
    var v = current.getAttribute('data-preview');
    if(v && v !== previewPage) switchPage(v);
  }
  var ticking = false;
  function onScroll(){ if(ticking) return; ticking = true; requestAnimationFrame(function(){ pickActive(); ticking = false; }); }
  window.addEventListener('scroll', onScroll, { passive:true });
  window.addEventListener('resize', onScroll);
  pickActive();
}
// 在 window load 裡：renderSelect(); switchPage(previewPage); initPreviewScrollSync();
```

**⑨ 預覽縮放（必做）：** 只有「適配寬度」不夠用——橫屏 `1280×720` 縮排 520px 面板後細節看不清，也沒法放大區域性看某個控制元件。故面板內固定提供一組縮放控制元件。

- **控制元件形態沿用 §4.6 互動流程圖那一組**（`－ / 百分比 / ＋ / 適配`），保持全 skill 一致；側欄無下載需求，**去掉 §4.6 的 `📸`**。放在 `.page-selector` 與 `.device-shell` 之間，深色底細按鈕，不與正文搶空間。
- **檔位固定梯**：`25 / 50 / 75 / 100 / 125 / 150 / 200 / 300`（%）。`＋/－` 在梯上跳一格，clamp 在 25%–300%。「適配」把 `previewZoom` 置回 `null` 回到自適應。
- 從適配態第一次點 `＋/－` 時，以**當前適配倍率**為起點在梯上找下一格，不會突然跳到 100% 讓畫面猛跳。
- **溢位由已有的 `.device-shell{overflow:auto}` 承接**，捲軸即可平移。**前提是 ② 裡的 `.device-wrapper{flex:0 0 auto}` 別漏**，否則 wrapper 被 flex 壓回面板寬度、放大等於白做。**不做 §4.6 那種按住拖曳平移**——側欄裡的是活原型，拖曳會和原型自身的點選/滑動互動打架。
- **`Ctrl/⌘ + 滾輪`** 在 `.device-shell` 上縮放（`preventDefault`）。**如實記一條限制：指標懸在 iframe 內部時滾輪事件歸 iframe 文件，父頁收不到**，此時快捷鍵無效——所以**按鈕是主路徑、快捷鍵只是補充**，不要向使用者宣傳成"隨處滾輪縮放"。
- **切頁保留縮放模式**：`switchPage()` 與 ⑧ 的 scroll-spy 自動切頁都**不重置** `previewZoom`（適配繼續適配，手動百分比保持不變），規則簡單可預期。拖 `.prototype-resizer` 改 `--panel-w` 同理：適配模式重算、手動模式保持百分比。
- **`previewZoom` 只存 JS 變數，不寫進 DOM**（遵守 §2.7「不落 `data-*` 痕跡」的約定），保證 §2.4 儲存與 §2.8 複製的產物乾淨。

```css
.preview-zoom { display:flex; align-items:center; gap:6px; padding:8px 16px; border-bottom:1px solid rgba(255,255,255,.08); }
.preview-zoom button { background:rgba(255,255,255,.08); color:#e8e6ff; border:1px solid rgba(255,255,255,.16); border-radius:6px; padding:3px 10px; font-size:12px; cursor:pointer; line-height:1.6; }
.preview-zoom button:hover { background:rgba(255,255,255,.18); }
.preview-zoom #previewZoomLabel { min-width:82px; text-align:center; font-size:12px; color:#b9b5e0; font-variant-numeric:tabular-nums; }
```

```html
<div class="preview-zoom">
  <button type="button" onclick="zoomPreview(-1)" title="縮小">－</button>
  <span id="previewZoomLabel">100%</span>
  <button type="button" onclick="zoomPreview(1)" title="放大">＋</button>
  <button type="button" onclick="fitPreview()" title="適配面板寬度">適配</button>
</div>
```

```js
const ZOOM_STEPS = [0.25,0.5,0.75,1,1.25,1.5,2,3];
function currentPreviewScale(){
  if(previewZoom!=null) return previewZoom;
  const shell=document.querySelector('.device-shell');
  if(!shell) return 1;
  return Math.max(120, shell.clientWidth-40)/currentCfg().w;   // 當前適配倍率
}
function zoomPreview(dir){
  const now=currentPreviewScale();
  let next;
  if(dir>0) next=ZOOM_STEPS.find(s=>s>now+1e-4);
  else      next=[...ZOOM_STEPS].reverse().find(s=>s<now-1e-4);
  previewZoom = next==null ? Math.min(3, Math.max(0.25, now)) : next;
  scalePreview();
}
function fitPreview(){ previewZoom=null; scalePreview(); }
// Ctrl/⌘ + 滾輪（限制：指標在 iframe 內時事件歸 iframe，父頁收不到）
document.querySelector('.device-shell')?.addEventListener('wheel', function(e){
  if(!e.ctrlKey && !e.metaKey) return;
  e.preventDefault();
  zoomPreview(e.deltaY < 0 ? 1 : -1);
}, { passive:false });
```

**⑩ 深連結（可選）：** 想讓「詳細方案」裡某個原型列的連結或外部訊息直接把面板開啟到某一頁，用 `#preview=<page-id>` —— `load` 時命中就自動 `toggleDualPane()` 並切到該頁（見 ③ 的 load 監聽）。**這是唯一會自動開啟面板的情形**，且必須由 URL 顯式觸發；不存在"原型目錄非空就自動開"。

### 2.7 全文件可編輯 · 表格行列拖曳 · 全表增刪行 · 撤銷重做（必做）

> **背景（踩坑記錄）：** 舊版只給「六、詳細方案」描述列加 `contenteditable`、只有詳細方案表能增刪行；其餘正文（背景/目標/埋點…）在瀏覽器裡都改不了，且 §2.5 舊規曾**禁用**列寬行高調整。**現固化為必做項：每份 PRD 都內建下面這套自包含的「通用編輯模組」**，一次性提供①全文件可編輯 ②全表增刪行 ③列寬/行高拖曳 ④撤銷/重做。模組**冪等、純內嵌、無外部依賴**，直接整段貼進 PRD 底部 `<script>`（在儲存按鈕邏輯之前），無需逐個單元格手寫 `contenteditable`。

**① 能力與邊界**
- **全文件可編輯：** 自動給正文內容塊（`td/th/p/li/h1~h4/.alert/blockquote/dd/dt`）加 `contenteditable` 並接管變更追蹤（`blur` 後內容變化 → `data-changed="true"` + `.edited-cell` 高亮）。
- **reload 安全（極易踩坑）：** 「已接管」「原始內容」用記憶體態 `WeakMap`/`WeakSet` 守衛，**絕不把 `data-pm-tracked`/`data-original` 寫進 DOM**——否則儲存（`outerHTML`）後這些髒屬性被存檔，重新開啟時守衛命中、`blur` 監聽不再掛載，編輯高亮靜默失效。僅 `contenteditable`、`data-changed`、`.edited-cell` 會隨存檔保留（前者保持可編輯、後兩者作為評審標記，符合預期）。
- **排除項（保持互動骨架不被誤編輯）：** 右側 `.prototype-sidebar` 預覽面板、`.fab-group`/`.save-btn(-container)`/`.dual-pane-toggle` 懸浮按鈕、各拖曳手柄、`.pm-anchor`、`iframe`/`script`/`style`/`button`；**含 `img`/`iframe`/`table`/`video`/`canvas` 的容器單元格（詳細方案「原型」列無論用 iframe 還是截圖 `<img>`）整體不接管**，避免原型/截圖被改壞。
- **全表增刪行：** 作用於**所有資料表**（功能清單/詳細方案/埋點…）。**表頭行自動識別**：整行均為 `<th>`（含寫在 `<tbody>` 裡的表頭行）或位於 `<thead>` 的行都不加增刪/行高控制元件、僅用於列寬手柄定位。每個資料行首格 `hover` 出現 `＋`（下方插一行）/`－`（刪除本行，留 1 行兜底）；新行克隆結構、**去掉 `id`/`rowspan`/`colspan`** 防重複 id、清空文字、自動接管編輯。
- **列寬/行高拖曳：** 表頭每列右緣 `.col-resizer`（改 `<col>` 寬，下限 48px）、每資料行首格下緣 `.row-resizer`（改 `tr` 高，下限 24px）。手柄預設 `opacity:0`、`hover` 才顯、寫 inline px → 隨 `outerHTML` 儲存，且靜態截圖無殘影。無 `<colgroup>` 的表會按表頭單元格當前寬度自動補一個。
- **撤銷/重做：** 上述所有操作都進同一個撤銷棧，快捷鍵連續撤銷/重做，詳見 **⑤**。

**② CSS 關鍵（手柄一律 hover-only）：**
```css
.edited-cell { background:#e8f5e9 !important; }
.editable-table-wrap { position:relative; margin:14px 0; }
.editable-table-wrap > table { margin:0 !important; }
.pm-anchor { position:relative; }
.row-ctrl { position:absolute; left:-30px; display:flex; flex-direction:column; gap:3px; opacity:0; pointer-events:none; transition:opacity .15s; z-index:4; }
tr:hover > * .pm-anchor > .row-ctrl, tr:hover .pm-anchor > .row-ctrl { opacity:1; pointer-events:auto; }
.row-ctrl button { width:22px; height:18px; border:none; border-radius:5px; cursor:pointer; color:#fff; font-size:13px; font-weight:700; line-height:1; }
.row-add { background:#00b894; } .row-del { background:#e74c3c; }
.editable-table-remove { position:absolute; top:-12px; right:8px; z-index:5; border:none; border-radius:999px; background:rgba(231,76,60,.96); color:#fff; font-size:12px; padding:6px 10px; cursor:pointer; opacity:0; pointer-events:none; transition:opacity .15s; }
.editable-table-wrap:hover .editable-table-remove { opacity:1; pointer-events:auto; }
.col-resizer { position:absolute; top:0; right:0; width:9px; height:100%; cursor:col-resize; transform:translateX(50%); z-index:3; opacity:0; transition:opacity .15s; }
.col-resizer::after { content:''; position:absolute; left:4px; top:0; width:2px; height:100%; background:#00b894; opacity:0; transition:opacity .15s; }
th:hover .col-resizer, td:hover .col-resizer, body.col-resizing .col-resizer.active { opacity:1; }
.col-resizer:hover::after, body.col-resizing .col-resizer.active::after { opacity:1; }
.row-resizer { position:absolute; left:0; bottom:0; width:100%; height:9px; cursor:row-resize; transform:translateY(50%); z-index:3; }
.row-resizer::after { content:''; position:absolute; top:4px; left:0; width:100%; height:2px; background:#00b894; opacity:0; transition:opacity .15s; }
.row-resizer:hover::after, body.row-resizing .row-resizer.active::after { opacity:1; }
body.col-resizing, body.row-resizing { user-select:none !important; }
body.col-resizing { cursor:col-resize !important; } body.row-resizing { cursor:row-resize !important; }
/* 撤銷/重做的瞬時提示：用完即從 DOM 移除，不進儲存與複製的產物 */
.pm-undo-toast { position:fixed; left:50%; bottom:34px; transform:translateX(-50%); background:rgba(33,33,45,.92); color:#fff; padding:8px 16px; border-radius:8px; font-size:13px; line-height:1.4; pointer-events:none; opacity:0; transition:opacity .18s; z-index:9999; }
.pm-undo-toast.show { opacity:1; }
```

**③ JS 模組（已在無頭 Chrome 對真實 PRD 結構實測 34 項全綠：全文件可編輯/排除 img 原型列/表頭識別/增刪行/列寬±與48px下限/行高/edited 高亮/無髒屬性洩漏/冪等再init，以及文字·增行·刪行·刪表·列寬·行高的撤銷重做、連續多步撤銷、新編輯清空重做分支、恢復節點監聽器仍活、輸入框內交還原生撤銷、toast 自動摘除。整段照貼）：**
```js
(function () {
  var EDITABLE_BLOCK_SELECTOR = 'td, th, p, li, h1, h2, h3, h4, .alert, blockquote, dd, dt';
  var EXCLUDE_SELECTOR = '.prototype-sidebar, .fab-group, .save-btn, .save-btn-container, .dual-pane-toggle, ' +
    '.col-resizer, .row-resizer, .row-ctrl, .pm-anchor, .editable-table-remove, .pm-undo-toast, script, style, iframe, button';
  var SKIP_CELL_CONTENT = 'table, iframe, video, canvas, img';   // 含這些的容器格不整體接管（如原型/截圖列）
  var origMap = new WeakMap(), rowDone = new WeakSet();

  /* ========== 撤銷/重做棧（純記憶體，不寫 DOM，不跨重新整理） ========== */
  var undoStack = [], redoStack = [], MAX_STEPS = 200, applying = false;
  function pushStep(step){
    if (applying) return;                     // 撤銷/重做自身產生的變更不再入棧
    undoStack.push(step);
    if (undoStack.length > MAX_STEPS) undoStack.shift();
    redoStack.length = 0;                     // 新編輯清空重做分支
  }
  function reinsert(node, parent, next){      // next 可能已被後續操作刪掉，兜底 append
    if (!parent) return;
    if (next && next.parentNode === parent) parent.insertBefore(node, next); else parent.appendChild(node);
  }
  var toastEl = null, toastTimer = null;
  function toast(msg){                        // 瞬時提示：用完即從 DOM 摘除，不汙染儲存/複製的產物
    if (!toastEl){
      toastEl = document.createElement('div'); toastEl.className = 'pm-undo-toast';
      toastEl.setAttribute('contenteditable','false'); document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    requestAnimationFrame(function(){ if (toastEl) toastEl.classList.add('show'); });
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function(){ if (toastEl){ toastEl.remove(); toastEl = null; } }, 1300);
  }
  function runStep(s, dir){ applying = true; try { s[dir](); } finally { applying = false; } }
  function undo(){
    commitPending();                          // 先結算正在輸入的這一筆，保證棧序正確
    var s = undoStack.pop(); if (!s){ toast('沒有可撤銷的操作'); return; }
    runStep(s, 'undo'); redoStack.push(s); toast('已撤銷');
  }
  function redo(){
    commitPending();
    var s = redoStack.pop(); if (!s){ toast('沒有可重做的操作'); return; }
    runStep(s, 'redo'); undoStack.push(s); toast('已重做');
  }
  function isFormField(t){ return !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT'); }
  // 捕獲階段 + preventDefault：必須攔掉瀏覽器對 contenteditable 的原生撤銷，否則兩套棧會疊加執行
  document.addEventListener('keydown', function(e){
    if (!(e.metaKey || e.ctrlKey) || e.altKey) return;
    if (isFormField(e.target)) return;                                  // 輸入框/下拉內交還原生行為
    var k = (e.key || '').toLowerCase();
    if (k === 'z' && !e.shiftKey){ e.preventDefault(); undo(); }        // ⌘Z / Ctrl+Z
    else if (k === 'y' || (k === 'z' && e.shiftKey)){ e.preventDefault(); redo(); }   // ⌘⇧Z / Ctrl+Y / Ctrl+⇧Z
  }, true);

  /* ---- 文字編輯：一次連續輸入合併成一步（停頓 600ms / 失焦 / 觸發撤銷 時結算） ---- */
  var pending = null, pendTimer = null, PEND_MS = 600;
  function flagState(el){ return { changed: el.getAttribute('data-changed'), cls: el.classList.contains('edited-cell') }; }
  function applyFlag(el, s){
    if (s.changed) el.setAttribute('data-changed', s.changed); else el.removeAttribute('data-changed');
    if (s.cls) el.classList.add('edited-cell'); else el.classList.remove('edited-cell');
  }
  function syncChangedFlag(el){ if (el.innerHTML !== origMap.get(el)) markEditableCellChanged(el); }
  function reveal(el){ if (el && el.isConnected && el.scrollIntoView) el.scrollIntoView({ block:'nearest' }); }
  function seed(el){ pending = { el: el, before: el.innerHTML, flag: flagState(el) }; }
  function commitPending(){
    if (pendTimer){ clearTimeout(pendTimer); pendTimer = null; }
    var p = pending; pending = null;
    if (!p) return;
    var el = p.el, before = p.before, beforeFlag = p.flag, after = el.innerHTML;
    if (after === before) return;
    syncChangedFlag(el);
    var afterFlag = flagState(el);
    pushStep({
      undo: function(){ el.innerHTML = before; applyFlag(el, beforeFlag); reveal(el); },
      redo: function(){ el.innerHTML = after;  applyFlag(el, afterFlag);  reveal(el); }
    });
  }
  function onEditFocus(){ if (pending && pending.el !== this) commitPending(); if (!pending) seed(this); }
  function onEditInput(){
    var el = this;
    if (!pending || pending.el !== el){ commitPending(); seed(el); }
    if (pendTimer) clearTimeout(pendTimer);
    pendTimer = setTimeout(function(){
      var still = pending && pending.el;
      commitPending();
      if (still && document.activeElement === still) seed(still);       // 還在打字就續上下一步
    }, PEND_MS);
  }
  function onEditBlur(){ if (pending && pending.el === this) commitPending(); syncChangedFlag(this); }

  /* ========== 編輯接管 ========== */
  function isExcluded(el){ return !!(el.closest && el.closest(EXCLUDE_SELECTOR)); }
  function isHeaderRow(tr){ return tr.cells.length > 0 && Array.prototype.every.call(tr.cells, function(c){ return c.tagName === 'TH'; }); }
  function headerRowOf(table){
    if (table.tHead && table.tHead.rows[0]) return table.tHead.rows[0];
    for (var i=0;i<table.rows.length;i++) if (isHeaderRow(table.rows[i])) return table.rows[i];
    return table.rows[0] || null;
  }
  function markEditableCellChanged(el){ if(!el) return; el.setAttribute('data-changed','true'); el.classList.add('edited-cell'); }
  function trackEditable(el){
    if (origMap.has(el)) return; origMap.set(el, el.innerHTML);   // 記憶體態守衛，不寫入 HTML
    el.setAttribute('contenteditable','true'); el.style.outline='none';
    el.addEventListener('focus', onEditFocus);
    el.addEventListener('input', onEditInput);
    el.addEventListener('blur', onEditBlur);
  }
  function makeDocumentEditable(root){
    (root||document).querySelectorAll(EDITABLE_BLOCK_SELECTOR).forEach(function(el){
      if (isExcluded(el)) return;
      if (el.querySelector(SKIP_CELL_CONTENT)) return;
      trackEditable(el);
    });
  }
  function wrapTable(table){
    if (table.closest('.editable-table-wrap')) return table.closest('.editable-table-wrap');
    var wrap=document.createElement('div'); wrap.className='editable-table-wrap'; wrap.setAttribute('contenteditable','false');
    table.parentNode.insertBefore(wrap, table); wrap.appendChild(table);
    var rm=document.createElement('button'); rm.type='button'; rm.className='editable-table-remove'; rm.textContent='刪除表格';
    rm.addEventListener('click', function(e){
      e.preventDefault();
      var parent=wrap.parentNode, next=wrap.nextSibling;
      wrap.remove();                                          // 節點留在棧裡，監聽器不丟，撤銷即原樣插回
      pushStep({ undo:function(){ reinsert(wrap, parent, next); reveal(wrap); }, redo:function(){ wrap.remove(); } });
    });
    wrap.appendChild(rm); return wrap;
  }
  function blankRowFrom(tr){
    var clone=tr.cloneNode(true); clone.style.height=''; clone.removeAttribute('id');
    Array.prototype.forEach.call(clone.cells, function(c){
      c.removeAttribute('rowspan'); c.removeAttribute('colspan'); c.removeAttribute('id');
      c.removeAttribute('data-changed'); c.classList.remove('edited-cell');
      c.querySelectorAll('.row-ctrl, .col-resizer, .row-resizer, .pm-anchor').forEach(function(n){
        if(n.classList.contains('pm-anchor')){ while(n.firstChild) n.parentNode.insertBefore(n.firstChild,n); n.remove(); } else n.remove();
      });
      if(!c.querySelector('iframe, img, video, canvas')) c.innerHTML='<br>';
      c.removeAttribute('contenteditable');
    });
    return clone;
  }
  function installRowControls(tr){
    var first=tr.cells[0]; if(!first || first.querySelector(':scope > .pm-anchor > .row-ctrl')) return;
    first.style.position='relative';
    var anchor=document.createElement('span'); anchor.className='pm-anchor'; anchor.setAttribute('contenteditable','false');
    var ctrl=document.createElement('span'); ctrl.className='row-ctrl';
    var add=document.createElement('button'); add.type='button'; add.className='row-add'; add.textContent='+'; add.title='在下方插入一行';
    var del=document.createElement('button'); del.type='button'; del.className='row-del'; del.textContent='−'; del.title='刪除本行';
    add.addEventListener('click', function(e){
      e.preventDefault();
      var nr=blankRowFrom(tr), parent=tr.parentNode, next=tr.nextSibling;
      parent.insertBefore(nr, next); decorateRow(nr); makeDocumentEditable(nr);
      pushStep({
        undo:function(){ nr.remove(); },
        redo:function(){ if(tr.parentNode) tr.parentNode.insertBefore(nr, tr.nextSibling); else reinsert(nr, parent, next); reveal(nr); }
      });
    });
    del.addEventListener('click', function(e){
      e.preventDefault();
      var body=tr.parentNode; var dataRows=Array.prototype.filter.call(body.rows, function(r){return !isHeaderRow(r);});
      if(dataRows.length<=1) return;
      var next=tr.nextSibling;
      tr.remove();                                            // 同上：整行節點保活在棧裡，撤銷後控制元件仍可用
      pushStep({ undo:function(){ reinsert(tr, body, next); reveal(tr); }, redo:function(){ tr.remove(); } });
    });
    ctrl.appendChild(add); ctrl.appendChild(del); anchor.appendChild(ctrl); first.insertBefore(anchor, first.firstChild);
  }
  function ensureCols(table){
    if (table.querySelector('colgroup')) return table.querySelector('colgroup');
    var headRow=headerRowOf(table); if(!headRow) return null;
    var cg=document.createElement('colgroup');
    for(var i=0;i<headRow.cells.length;i++){ var col=document.createElement('col'); col.style.width=headRow.cells[i].offsetWidth+'px'; cg.appendChild(col); }
    table.insertBefore(cg, table.firstChild); return cg;
  }
  function installColResizers(table){
    var cg=ensureCols(table); if(!cg) return; var cols=cg.querySelectorAll('col');
    var headRow=headerRowOf(table); if(!headRow) return;
    Array.prototype.forEach.call(headRow.cells, function(th, idx){
      if(idx>=cols.length) return; if(th.querySelector(':scope > .col-resizer')) return;
      th.style.position='relative';
      var h=document.createElement('span'); h.className='col-resizer'; h.setAttribute('contenteditable','false');
      var col=cols[idx];
      h.addEventListener('mousedown', function(e){
        e.preventDefault(); e.stopPropagation();
        var startX=e.clientX, startW=col.offsetWidth||th.offsetWidth, beforeW=col.style.width;
        h.classList.add('active'); document.body.classList.add('col-resizing');
        function mv(ev){ col.style.width=Math.max(48, startW+(ev.clientX-startX))+'px'; }
        function up(){
          document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up);
          h.classList.remove('active'); document.body.classList.remove('col-resizing');
          var afterW=col.style.width;
          if(afterW!==beforeW) pushStep({ undo:function(){ col.style.width=beforeW; }, redo:function(){ col.style.width=afterW; } });
        }
        document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up);
      });
      th.appendChild(h);
    });
  }
  function installRowResizer(tr){
    var first=tr.cells[0]; if(!first || first.querySelector(':scope > .row-resizer')) return;
    first.style.position='relative';
    var h=document.createElement('span'); h.className='row-resizer'; h.setAttribute('contenteditable','false');
    h.addEventListener('mousedown', function(e){
      e.preventDefault(); e.stopPropagation();
      var startY=e.clientY, startH=tr.offsetHeight, beforeH=tr.style.height;
      h.classList.add('active'); document.body.classList.add('row-resizing');
      function mv(ev){ tr.style.height=Math.max(24, startH+(ev.clientY-startY))+'px'; }
      function up(){
        document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up);
        h.classList.remove('active'); document.body.classList.remove('row-resizing');
        var afterH=tr.style.height;
        if(afterH!==beforeH) pushStep({ undo:function(){ tr.style.height=beforeH; }, redo:function(){ tr.style.height=afterH; } });
      }
      document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up);
    });
    first.appendChild(h);
  }
  function decorateRow(tr){ if(rowDone.has(tr) || isHeaderRow(tr) || tr.closest('thead')) return; rowDone.add(tr); installRowControls(tr); installRowResizer(tr); }
  function installTableControls(root){
    (root||document).querySelectorAll('table').forEach(function(table){
      if(isExcluded(table) || table.closest('.no-edit')) return;
      wrapTable(table); installColResizers(table);
      Array.prototype.forEach.call(table.rows, decorateRow);
    });
  }
  function init(root){ installTableControls(root); makeDocumentEditable(root); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', function(){ init(document); }); else init(document);
  window.PMEdit={ init:init, makeDocumentEditable:makeDocumentEditable, installTableControls:installTableControls,
                  undo:undo, redo:redo, canUndo:function(){ return undoStack.length>0; }, canRedo:function(){ return redoStack.length>0; } };
})();
```

**④ 接入約定：**
- 詳細方案及其它定寬表必須帶 `<colgroup><col>`（見 §2.5），列寬拖曳改的就是這些 `<col>`。
- 某張表確實不想被編輯/加控制元件時，給該 `<table>` 加 `class="no-edit"` 豁免（如純展示裝飾表）。
- **迭代聯動（接 §5.3）：** 新增表格/新增整塊正文後，呼叫 `PMEdit.init(新節點)` 讓控制元件對新節點冪等生效；`PMEdit.init`、`installTableControls`、`makeDocumentEditable` 均可重複安全呼叫，不會重複加手柄。
- 儲存仍走 §2.4 的「💾 儲存並通知AI」按鈕抓 `outerHTML`；編輯內容、`edited-cell`、inline 列寬/行高都會一併落盤。

**⑤ 撤銷 / 重做（必做 · 快捷鍵）**

> **背景（踩坑記錄）：** 刪掉一行或整張表後**沒有任何退路**——只能重新開啟檔案丟掉所有未儲存的修改。瀏覽器對 `contenteditable` 的原生撤銷只覆蓋文字，管不了增刪行、刪表和尺寸拖曳，且和自定義邏輯會打架。**故在編輯模組裡內建統一撤銷棧。**

- **快捷鍵（Mac / Windows 都支援）：**

  | 操作 | Mac | Windows / Linux |
  |------|-----|-----------------|
  | 撤銷 | `⌘ + Z` | `Ctrl + Z` |
  | 重做 | `⌘ + Shift + Z` | `Ctrl + Y`（同時相容 `Ctrl + Shift + Z`） |

- **覆蓋範圍（四類操作進同一個棧，按操作發生順序連續撤銷）：**
  1. **文字編輯** —— 一次連續輸入合併成一步（停頓 600ms、失焦、或按下撤銷鍵時結算），不會一個字一步。
  2. **表格增刪行** —— `＋` 插入行、`－` 刪除行。
  3. **刪除表格** —— 整張表連同 `.editable-table-wrap` 一起恢復。
  4. **尺寸調整** —— 列寬（`col.style.width`）、行高（`tr.style.height`），一次拖曳一步（`mouseup` 才入棧，拖動過程不刷屏）。
- **新編輯清空重做分支**：撤銷若干步後又動手改了內容，重做棧立即清空——與所有編輯器一致的行為，避免出現分叉歷史。
- **關鍵實現點（別踩）：**
  - **刪除必須"保活節點"，不能存 HTML 字串。** 刪行/刪表時把 `tr` / `wrap` 的**節點物件**連同 `parentNode` + `nextSibling` 存進棧，撤銷時原樣 `insertBefore` 回去——這樣行控制元件、拖曳手柄、`contenteditable` 監聽全都還在。若改成存 `innerHTML` 再回填，恢復出來的是**死節點**：按鈕還在但點不動，還得重跑一遍 `PMEdit.init`。
  - **`nextSibling` 可能已被後續操作刪掉**，回插前判斷 `next.parentNode === parent`，否則退化成 `appendChild`。
  - **必須在捕獲階段 `preventDefault` 攔掉原生撤銷**，否則瀏覽器的 contenteditable undo 和本棧會**同時執行、撤兩步**。`INPUT/TEXTAREA/SELECT` 內則放行交還原生行為。
  - **撤銷/重做期間設 `applying` 標誌位遮蔽入棧**，否則恢復動作自己會被記成新的一步，形成死迴圈。
  - **撤銷前先結算正在輸入的那一筆**（`commitPending()`），否則"打字 → 立刻 ⌘Z"會先撤掉更早的操作、把剛打的字留在頁面上。
  - **文字步要連 `data-changed` / `.edited-cell` 一起存取**，否則撤回到原始內容後綠色高亮還賴著不走。
  - 棧上限 200 步（刪表節點常駐記憶體，不設上限會越用越沉）。
- **不做的事（如實說明，別向使用者過度承諾）：**
  - **不承諾跨重新整理保留撤銷歷史**——棧只在記憶體裡，重新整理 / 重新開啟檔案即清空。要留檔就先儲存。
  - 撤銷棧**不寫進 DOM**（遵守本節「不落 `data-*` 痕跡」的約定），儲存與 §2.8 複製的產物保持乾淨。
  - 提示用的 `.pm-undo-toast` **顯示完即從 DOM 移除**，所以 §2.4 儲存和 §2.8 複製的邏輯**都不需要改**——不用把它加進任何排除名單。
- **入口：只做快捷鍵，不加常駐按鈕。** 若後續要加可見入口，放進「更多」選單，不要再往懸浮區塞按鈕（左下角一鍵複製、右下角雙欄預覽+儲存的佈局不動）。程式化呼叫走 `PMEdit.undo()` / `PMEdit.redo()`，狀態查詢走 `PMEdit.canUndo()` / `PMEdit.canRedo()`。

### 2.8 左下角「一鍵複製全文」（必做 · 原型 iframe 自動轉圖片）

> **目的：** 方便把整份 PRD 一鍵拷到Notion/Google 文件/Word 等外部文件。複製必須是**富文字**（`text/html`，保留表格/標題/加粗/列表），並在匯出前**剝離所有互動骨架與編輯痕跡**，否則粘出去會帶一堆手柄、綠色高亮和 `contenteditable` 髒屬性。
>
> **踩坑記錄（v2.6 修正）：** 舊版直接 `iframe.remove()`，PRD 粘出去後**原型/流程圖全部消失**，PM 每次都要手動重新截圖再貼一遍。現固化為：複製前先把每個 iframe 透過本地匯出服務換成 **base64 內聯圖片**，一次貼上即完整。

**① 按鈕：** 頁面**左下角**固定一個 `.copy-all-fab`（`position:fixed; left:28px; bottom:28px`），`onclick="copyAllContent()"`，文案「📋 一鍵複製全文」。與右下角 `.fab-group`（雙欄/儲存）分居兩側；雙欄開啟時右側面板不影響左下角，無需偏移。另配一個 `.copy-toast`（左下、`bottom:80px`）做輕量結果反饋，預設 `opacity:0`、`.show` 時淡入，2 秒後自動隱藏。**取圖期間 toast 常駐**（「正在生成原型圖片 n/N…」），出結果後才進入 2 秒自動隱藏。

**② 兩類圖都要內聯成 base64（本節核心）：**

PRD 裡的圖有兩種來源，**都得處理**，只處理 iframe 是不夠的：

| 來源 | 形態 | 介面 |
|---|---|---|
| 活原型 / 流程圖 | `<iframe src="../原型/x.html#p1">` | `POST /api/snapshot` → Playwright 渲染出 PNG |
| 詳細方案「原型」列的截圖版 | `<img src="../原型截圖/x.png">` | `POST /api/asset` → 直接讀本地檔案轉 base64 |

- **必須走本地匯出服務**，理由與 §4.5 同源：`file://` 下瀏覽器既不能 `fetch` 本地 PNG、canvas 也會被跨源汙染，**base64 只能由服務端下發**。禁止為此新造 `html2canvas` / `html-to-image` 前端截圖路徑。
- PRD 底部引入 `<script src="../../scripts/prototype-export-client.js?v=YYYYMMDD-prd"></script>`（PRD 在 `[需求名]/需求文件/` 下，故是 `../../scripts/`），拿到 `window.snapshotPrototypeViaServer(src,{base})` 與 `window.inlineAssetViaServer(src,{base})`。
- `/api/snapshot` 入參 `{src, base, scale?}` → 回 `{ok, dataUrl, cached, bytes}`。**取圖策略＝快取優先 + 自動重渲**：截圖存在且比原型 HTML 新 → 直接沿用 `[需求名]/原型截圖/`（或 `流程圖截圖/`）裡已有的 PNG；否則實時用 Playwright 只渲這一頁再落盤。`scale` 預設 `2`（與整輪匯出一致，保證同一份文件裡圖片清晰度統一），體積敏感時可傳 `1`。
- **服務端會自動適配四種 iframe**（不用 PRD 側操心）：平鋪原型的 `.device[id]`（按 hash 定位）、流程圖的 `.chart-container`、單屏頁（`.screen`/`.device`/`main`）、帶 query 的片段（如 `?only=flow-main`，query 會原樣帶上並單獨快取）。
- `/api/asset` 只放行 `png/jpg/jpeg/gif/webp/svg` 且必須落在專案目錄內、單張 ≤12MB —— 它把檔案原樣吐成 base64，不能退化成任意檔案讀取。
- **按 `src` 去重 + 頁面內 `Map` 快取**：同一份 PRD 裡同一個 src 只取一次；同一次會話第二次複製直接秒出。

**③ 三步走：剝骨架 → 取圖 → 落圖（順序不能反）**

1. **`stripSkeleton()`**：`document.body.cloneNode(true)` 後刪掉 `.prototype-sidebar`、`.fab-group`、`.copy-all-fab`、`.copy-toast`、`.col-resizer`、`.row-resizer`、`.row-ctrl`、`.pm-anchor`、`.editable-table-remove`、`script`/`noscript`；`.editable-table-wrap` 用其內部 `<table>` 替換自身。**iframe/img 此時先留著。**
2. **`collectMedia(clone)`**：**只掃 clone 裡活下來的節點**去取圖。
   > **踩坑（必須照做）：** 早期版本按 `document` 掃 iframe，把 §2.6 右側雙欄預覽的 `#prototypeFrame` 也算了進去——它隨 `.prototype-sidebar` 一起被刪了，結果**白渲一張圖、toast 還多報一張**（說"3 張"實際只貼出 2 張）。按 clone 掃天然規避。
   > **踩坑 2（同樣必須照做）：** 頁面 CSS 全在 `<head>` 裡，`document.body.cloneNode(true)` **帶不走**，`.proto-shot` 那類尺寸約束會整個丟失，1200px 的截圖直接把表格撐爆、描述列被擠成"一行一個字"。所以 `stripSkeleton()` 要**趁 clone 與實時 DOM 還一一對應**（刪節點之前，兩邊 `querySelectorAll('img')` 索引一致），把每張圖的實際顯示寬度 `getBoundingClientRect().width` 固化成內聯 `width` + `max-width:100%`。
3. **`finalizeClone(clone, jobs)`**：iframe 換成 `<img src="data:image/png;base64,…">`（失敗的才刪）、本地 `<img>` 的 `src` 換成 dataUrl（失敗的保留原樣）；再移除 `contenteditable`、`data-changed`/`data-original`/`data-orig`/`data-pm-tracked` 與 `.edited-cell`；給 `table` 補 `border-collapse/width`、`th,td` 補 `1px` 邊框+內邊距、`th` 補淺底色（內聯 style，確保粘到無樣式環境也有框）；最後把 `img` 的 `src` 絕對化——**`data:` 開頭的要跳過**，否則會把 base64 改壞。

**④ 三檔降級（必須據實告知，不許靜默失敗）：**

| 情況 | 行為 | toast 文案 |
|---|---|---|
| 全部取圖成功 | iframe 換成圖、本地 img 內聯 | `已複製全文（含 N 張圖），可直接貼上到Notion/Google 文件/Word` |
| 部分失敗 | 失敗的 iframe 刪掉、失敗的 img 保留原樣 | `已複製全文，含 N 張圖，M 張生成失敗已跳過` |
| 服務整體不可用 | 退回舊行為（刪所有 iframe、img 留本地路徑） | `匯出服務未啟動，已按純文字複製（原型圖缺失）` |

**⑤ 體積控制（不做會直接失敗）：** 服務下發的是 `scale=2` 的交付級 PNG，單張能到 3MB —— 一份含 3 個 iframe + 8 張原型截圖的真實 PRD 實測**原始合計約 19.5MB**，轉 base64 後 26MB，遠超各家文件貼上能吃下的量。故取到 dataUrl 後**在 PRD 頁面本地降取樣**：寬度上限 `MAX_IMG_WIDTH = 2000`，超出的按比例縮到 2000px 寬再以 `image/jpeg`（品質 0.9）重編碼，先鋪白底再畫（JPEG 無透明通道）。
- **為什麼可以在前端做**：`data:` URL 屬同源，**不會汙染 canvas**——被 `file://` 封死的只有"讀本地檔案"，不是"處理已經拿到手的 base64"。所以服務只負責突破 `file://` 的讀取限制，縮放留在瀏覽器，無需任何影象庫。
- 縮放失敗（`onerror`/`toDataURL` 拋錯）**一律退回原圖**，絕不因為壓縮失敗就丟圖。
- **粘出去「發虛」是降取樣造成的，不是 JPEG 造成的（v2.8 實測，別改錯地方）：** 上限曾定在 1200 + 品質 0.85，PM 反饋粘進文件發虛。同一素材同一區域四檔對照 —— JPEG .85 / JPEG .95 / PNG 無損 / WebP .92，**都縮到 1200 後幾乎無差別**，而不降取樣的原圖明顯銳利。細節是在縮放那一步丟的，換編碼格式救不回來，唯一有效的是抬高 `MAX_IMG_WIDTH`。9 張素材實測合計：`1200/.85 = 0.90MB`、`1600/.9 = 1.65MB`、`2000/.9 = 2.20MB`、`2880 原尺寸/.9 = 3.60MB`；取 **2000** 是清晰度與體積的拐點。
- **別用「貼出來看著還行」判斷夠不夠。** 圖在文件裡的顯示寬度由 ④ 固化的表格列寬決定（實測 335px），**這個尺寸下 1200 和 2880 肉眼無差別**，差異只在讀者放大看細節時暴露。驗收要放大到 1000px 以上再看。
- 再要更清晰只能繼續調大 `MAX_IMG_WIDTH`，代價是體積近似平方級上升；**WebP 體積更優（`2000/.9` 僅 1.34MB）但Notion/Google 文件/Word 對剪貼簿內 base64 WebP 的支援未實測，不要預設切過去**。

**⑥ 寫剪貼簿：** 優先 `navigator.clipboard.write([new ClipboardItem({'text/html':blobHtml,'text/plain':blobText})])`（`text/plain` = 清洗後 `clone.innerText` 兜底）；不支援或被拒時**回退**到離屏 `contenteditable` 容器 + 選區 + `document.execCommand('copy')`。成功/失敗都用 `.copy-toast` 提示。

**⑦ JS（整段照貼到 PRD 底部，須在 `prototype-export-client.js` 之後）：**
```js
(function(){
  var mediaCache = new Map();   // src → dataUrl，同一次會話沿用（iframe 與 img 共用）
  var MAX_IMG_WIDTH = 2000;     // 粘出去的圖片寬度上限，見 ⑤ 體積控制（1200 會讓放大看時發虛）

  // 服務下發的是 2 倍圖（一張能到 3MB），直接塞剪貼簿會幾十 MB。
  // data: URL 不會汙染 canvas，所以縮放可以在本頁做完，不用再依賴任何影象庫。
  function shrinkDataUrl(dataUrl, maxWidth){
    return new Promise(function(resolve){
      var im = new Image();
      im.onload = function(){
        if(!im.naturalWidth || im.naturalWidth <= maxWidth){ resolve(dataUrl); return; }
        try{
          var r = maxWidth / im.naturalWidth;
          var c = document.createElement('canvas');
          c.width = Math.round(im.naturalWidth * r);
          c.height = Math.round(im.naturalHeight * r);
          var ctx = c.getContext('2d');
          ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, c.width, c.height);  // JPEG 沒有透明通道，先鋪白底
          ctx.drawImage(im, 0, 0, c.width, c.height);
          resolve(c.toDataURL('image/jpeg', 0.9));
        }catch(e){ resolve(dataUrl); }   // 縮放失敗就用原圖，不能因此丟圖
      };
      im.onerror = function(){ resolve(dataUrl); };
      im.src = dataUrl;
    });
  }

  // ① 先剝互動骨架，iframe/img 都先留著
  function stripSkeleton(){
    var clone = document.body.cloneNode(true);
    // 頁面 CSS 在 <head> 裡，克隆 body 帶不走 → 原型列截圖會按 1200px 原圖把表格撐爆、
    // 描述列被擠成一行一個字。趁 clone 與實時 DOM 還一一對應，把實際顯示寬度固化成內聯樣式。
    var live = document.body.querySelectorAll('img'), copies = clone.querySelectorAll('img');
    for(var i=0; i<live.length && i<copies.length; i++){
      var w = Math.round(live[i].getBoundingClientRect().width);
      if(w > 0){ copies[i].style.width = w + 'px'; copies[i].style.height = 'auto'; }
      copies[i].style.maxWidth = '100%';
    }
    clone.querySelectorAll('.prototype-sidebar, .fab-group, .copy-all-fab, .copy-toast, .col-resizer, .row-resizer, .row-ctrl, .pm-anchor, .editable-table-remove, script, noscript').forEach(function(n){ n.remove(); });
    clone.querySelectorAll('.editable-table-wrap').forEach(function(w){ var t=w.querySelector('table'); if(t) w.replaceWith(t); else w.remove(); });
    return clone;
  }

  // ② 只掃 clone 裡活下來的節點，逐個取 base64
  async function collectMedia(clone){
    var jobs = [];
    clone.querySelectorAll('iframe[src]').forEach(function(el){
      jobs.push({ el: el, src: el.getAttribute('src'), kind: 'frame' });
    });
    clone.querySelectorAll('img[src]').forEach(function(el){
      var s = el.getAttribute('src');
      if(s && !/^data:/i.test(s)) jobs.push({ el: el, src: s, kind: 'asset' });
    });

    var out = { ok:0, fail:0, serviceDown:false, jobs: jobs };
    if(!jobs.length) return out;
    if(typeof window.snapshotPrototypeViaServer !== 'function' || typeof window.inlineAssetViaServer !== 'function'){
      out.serviceDown = true; out.fail = jobs.length; return out;
    }

    var srcs = [];
    jobs.forEach(function(j){ if(srcs.indexOf(j.src) === -1) srcs.push(j.src); });

    // 先把"服務在不在"一次性問清楚，再逐張取圖。
    // 別靠嗅探第一張的報錯文案來判斷服務死活——那既不準，又會讓每張圖都白等一遍探測。
    // 這一步最慢：健康探測 8s + 喚起 launcher + 等瀏覽器冷啟動最多 30s，實測服務確實沒起時約 39s，
    // 所以必須掛常駐 toast 說明在等什麼，不能讓使用者對著不動的介面猜。
    if(mediaCache.size < srcs.length){
      showToast('正在喚起原型匯出服務（首次啟動較慢，最長約 40 秒）…', false, true);
      try{
        await window.ensureExportServerReady();
      }catch(e){
        console.warn('[copy-all] 匯出服務不可用', e);
        out.serviceDown = true; out.fail = srcs.length; return out;
      }
    }

    for(var i=0;i<srcs.length;i++){
      var src = srcs[i];
      if(mediaCache.has(src)){ out.ok++; continue; }
      showToast('正在生成圖片 '+(i+1)+'/'+srcs.length+'…', false, true);
      var kind = jobs.filter(function(j){ return j.src === src; })[0].kind;
      try{
        var data = kind === 'frame'
          ? await window.snapshotPrototypeViaServer(src, {})
          : await window.inlineAssetViaServer(src, {});
        mediaCache.set(src, await shrinkDataUrl(data.dataUrl, MAX_IMG_WIDTH)); out.ok++;
      }catch(e){
        console.warn('[copy-all] 取圖失敗', src, e);
        out.fail++;   // 單張失敗不影響其餘，最後由 toast 如實報數
      }
    }
    return out;
  }

  // ③ 落圖 + 清編輯痕跡 + 補排版
  function finalizeClone(clone, jobs){
    (jobs||[]).forEach(function(j){
      var url = mediaCache.get(j.src);
      if(j.kind === 'frame'){
        if(!url){ j.el.remove(); return; }              // 原型取圖失敗 → 退回刪除
        var img = document.createElement('img');
        img.src = url;
        img.alt = j.el.getAttribute('title') || '原型預覽';
        img.style.cssText = 'max-width:100%;height:auto;border:1px solid #e5e3f5;border-radius:8px;';
        j.el.replaceWith(img);
      } else if(url){
        j.el.setAttribute('src', url);                  // 截圖內聯失敗 → 保留原樣，由 toast 如實報數
      }
    });
    clone.querySelectorAll('[contenteditable]').forEach(function(el){ el.removeAttribute('contenteditable'); });
    ['data-changed','data-original','data-orig','data-pm-tracked'].forEach(function(a){ clone.querySelectorAll('['+a+']').forEach(function(el){ el.removeAttribute(a); }); });
    clone.querySelectorAll('.edited-cell').forEach(function(el){ el.classList.remove('edited-cell'); });
    clone.querySelectorAll('table').forEach(function(t){ t.style.borderCollapse='collapse'; t.style.width='100%'; });
    clone.querySelectorAll('th,td').forEach(function(c){ c.style.border='1px solid #ccc'; c.style.padding='6px 10px'; c.style.verticalAlign='top'; });
    clone.querySelectorAll('th').forEach(function(c){ if(!c.style.background) c.style.background='#f2f1f8'; });
    clone.querySelectorAll('img').forEach(function(img){
      try{ if(!/^data:/i.test(img.getAttribute('src')||'')) img.setAttribute('src', img.src); }catch(e){}
    });
    return clone;
  }

  function showToast(msg, err, sticky){
    var t=document.querySelector('.copy-toast');
    if(!t){ t=document.createElement('div'); t.className='copy-toast'; document.body.appendChild(t); }
    t.textContent=msg; t.style.background= err? '#c0392b' : '#2a2459'; t.classList.add('show');
    clearTimeout(showToast._t);
    if(!sticky) showToast._t=setTimeout(function(){ t.classList.remove('show'); }, 2600);
  }

  async function writeClipboard(html, text){
    try{
      if(navigator.clipboard && window.ClipboardItem){
        await navigator.clipboard.write([new ClipboardItem({
          'text/html': new Blob([html],{type:'text/html'}),
          'text/plain': new Blob([text],{type:'text/plain'})
        })]);
        return true;
      }
      throw new Error('no async clipboard');
    }catch(e){
      var holder=document.createElement('div'); holder.setAttribute('contenteditable','true');
      holder.style.cssText='position:fixed;left:-99999px;top:0;opacity:0;'; holder.innerHTML=html;
      document.body.appendChild(holder);
      var range=document.createRange(); range.selectNodeContents(holder);
      var sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
      var okc=document.execCommand('copy'); sel.removeAllRanges(); holder.remove();
      if(!okc) throw new Error('execCommand 拒絕');
      return true;
    }
  }

  async function copyAllContent(){
    try{
      var clone = stripSkeleton();
      var media = await collectMedia(clone);
      finalizeClone(clone, media.jobs);
      await writeClipboard('<meta charset="utf-8">'+clone.innerHTML, clone.innerText);
      if(media.serviceDown)     showToast('匯出服務未啟動，已按純文字複製（原型圖缺失）', true);
      else if(media.fail)       showToast('已複製全文，含 '+media.ok+' 張圖，'+media.fail+' 張生成失敗已跳過', true);
      else if(media.ok)         showToast('已複製全文（含 '+media.ok+' 張圖），可直接貼上到Notion/Google 文件/Word');
      else                      showToast('已複製全文，可直接貼上到Notion/Google 文件/Word');
    }catch(e){
      showToast('複製失敗，請手動全選複製：'+(e.message||e), true);
    }
  }
  window.copyAllContent=copyAllContent;
})();
```

**⑧ CSS 草圖：**
```css
.copy-all-fab { position:fixed; left:28px; bottom:28px; z-index:1001; background:#fff; color:#3b357a; border:1px solid #d8d4f0; border-radius:12px; padding:13px 20px; font-size:14px; font-weight:700; cursor:pointer; box-shadow:0 4px 16px rgba(91,91,214,.18); display:flex; align-items:center; gap:8px; }
.copy-all-fab:hover { transform:translateY(-2px); border-color:#5b5bd6; }
.copy-toast { position:fixed; left:28px; bottom:80px; z-index:1002; max-width:360px; background:#2a2459; color:#fff; padding:11px 16px; border-radius:10px; font-size:13px; box-shadow:0 8px 24px rgba(20,16,70,.28); opacity:0; transform:translateY(8px); pointer-events:none; transition:opacity .2s, transform .2s; }
.copy-toast.show { opacity:1; transform:translateY(0); }
```

> **取材限制（據實說明，勿誇大）：**
> - base64 內聯圖**不依賴本地路徑**，這正是必須走服務出 base64、而不是貼相對路徑 `<img>` 的原因。
> - 但**目標文件是否真的會把 base64 圖存下來，取決於它自己的貼上實現**——Notion/Google 文件/Word 各不相同，首次接入某個目標文件時**必須人工粘一次確認**，不要向使用者承諾"一定能帶圖"。
> - **耗時實測**（某複雜 PRD，2 個 iframe + 8 張原型截圖）：截圖已存在時**全程 0.7 秒**（10 張全部命中快取）；服務沒起、需要喚起並冷啟動 Chromium 時最長約 **40 秒**；確認服務起不來時也是這個量級才出降級提示，所以那句常駐 toast 不能省。
> - 複製出的富文字約 **3.8MB**（10 張圖解碼後 2.83MB，base64 文字再膨脹 1.33×；原始素材 19.5MB，經 ⑤ 降取樣）。**報體積給使用者時要報剪貼簿裡的 base64 量，不是解碼後的位元組數**——兩者差 1/3，按後者承諾會低估。

---

### 2.9 內網（http · 不安全上下文）下的真實邊界（必須如實告知使用者，不許含糊）

PRD HTML 會被推到公司內網供多人瀏覽。內網是 `http://` 非 localhost，屬**不安全上下文**——`navigator.clipboard`、`ClipboardItem`、`showSaveFilePicker` 一律不存在。不要按"我本機點著好使"就當功能可用。

| 能力 | 作者本機（`file://`） | 內網訪客（`http://` 非 localhost） |
|---|---|---|
| `💾 儲存並通知AI` | ✅ 覆寫本地檔案 | ⚠️ 無 File System Access → 降級為**下載一份副本** |
| `📋 一鍵複製全文` | ✅ | ✅ 但 `navigator.clipboard` 在不安全上下文不存在，**必須有 `execCommand` 兜底**否則整個複製啞火 |
| 原型取圖（`/api/snapshot`、`/api/asset`） | ✅ | ✅ 但服務端要按專案目錄相對解析發起頁，見下面這條踩坑 |

> **踩坑（v2.7 修正）：** 內網用 http 開啟時 `location.pathname` 是**站點根路徑**、磁碟上並不存在，匯出服務舊版只按絕對路徑解析發起頁，導致 `/api/snapshot` 與 `/api/asset` 全返 400、「一鍵複製全文」**一張圖都取不到**（toast 還只說"生成失敗"）。服務端 `_resolve_base_html()` 必須**再按專案目錄相對解一次**。

> 任何一檔降級都要在 toast 裡講清楚丟了什麼（§2.8 降級三檔），不許靜默失敗。

---

## 步驟三：產出原型

### 3.0 設計方向前置（極度重要 · 動筆前必做）

> 原型的長相不由這一步臨時決定，由專案級的 `DESIGN.md` 決定。細節見 `.agents/workflows/pm-design.md`。

1. 檢查專案根目錄是否有 `DESIGN.md`。**沒有 → 先走 `pm-design.md` 流程 A2 建立**（只問使用者一個問題就能定方向），不要在沒有設計系統的情況下畫原型。
2. 有 → 讀它。原型的色彩、字型（含中文 fallback）、圓角、間距、動效強度、版面巨觀結構**全部取自 `DESIGN.md`**，本檔 §3.2 的通用原則只在 `DESIGN.md` 沒寫到時才補位。
3. 依 `pm-design.md` 流程 B 載入建構規則：hallmark 的 build 規則與指定主題、impeccable 的 `reference/craft-floor.md`。決定本需求的介面模式（Persuade / Operate / Read / Experience）並寫在原型 HTML 開頭註解。
4. 需要動效 → 用 GSAP（讀 `gsap-core` 等 skill），不手寫關鍵影格；尊重 `prefers-reduced-motion`。

### 3.1 規範

1. 根據PRD中的詳細方案設計互動原型
2. 使用 **HTML單檔案** 實現所有頁面狀態，透過 URL hash 切換檢視，如：
   - `prototype.html#home`
   - `prototype.html#camera`
   - `prototype.html#result-success`
3. 無 hash 開啟時預設平鋪展示全部頁面狀態，便於評審和截圖；帶 hash 時只展示對應頁面
4. 技術棧：**Tailwind CSS + Font Awesome**（CDN引入），無需構建工具
5. **極度重要（真實渲染匯出）：** 頁面內建懸浮匯出按鈕 `📸 一鍵匯出所有截圖`，僅在平鋪模式下顯示；按鈕必須接入 `../scripts/prototype-export-client.js`，優先呼叫本地 `scripts/prototype_server.py`，用 Playwright/Chromium 對真實 HTML 渲染結果截圖，不再用 `html-to-image` / `html2canvas` 作為預設匯出方案。
6. **極度重要（儲存路徑與命名）：** 匯出 PNG 自動儲存到該需求自己的目錄 `[需求名]/原型截圖/`（由匯出服務根據原型 HTML 所在位置自動推導）；檔名優先使用原型下方 `.device-label`，其次使用 `.page-title` / 註釋中的介面名稱，保證和介面名稱一致。
   > **極度重要（截圖目錄是 PM 的資產目錄，不許萬用字元清場）：** 每輪匯出前清理上一輪產物時，**只能刪本 HTML 在 `.export-manifest.json` 裡登記過的檔名**，絕不能用 `*.png` 把整個 `原型截圖/` 清空。
   > **實測踩過（刪了 8 張補 1 張）：** `原型截圖/` 裡同時存放 PM 手工產物。用 `[需求名]-shots.html`（狀態可定址的截圖版）按 hash 一個狀態一張手截、手工命名（`01-詳情頁.png` 等），PRD 的「原型」列直接 `<img>` 引這些名字。而對 `[需求名]-prototype.html` 跑一次匯出時，它本身沒有 `.device` 節點、只出 1 張整頁圖，`*.png` 卻把那 8 張全刪了，PRD 當場變成碎圖，且**這些圖不在 git 裡，刪了就沒了**。


7. **極度重要（匯出服務）：** 專案根目錄提供兩個雙擊入口——macOS 的 `啟動原型匯出服務.command` 和 Windows 的 `啟動原型匯出服務.bat`。服務連接埠由專案確定性推導（不是固定的 8765），頁面透過 `scripts/pm-runtime-config.js` 拿到實際地址，**不要在原型或 PRD 裡寫死任何連接埠號**。點匯出時若服務未響應，按鈕需顯示"正在連線匯出服務"，並按訪問者的平台提示對應的那個入口（客戶端已按 `navigator.userAgent` 自動選詞）。瀏覽器安全限制下，HTML 不能直接啟動 Python 程序，得有個東西在啟動器連接埠上應答：**macOS 上這個角色由 launchd 擔任**（安裝時已預設註冊按需啟動器，socket 啟用、空閒零程序），所以點匯出會自動起服務，不需要先雙擊入口；Windows 上沒有這一層，必須先雙擊 `.bat` 並保持視窗開著。
8. 同時保留 `trigger-export` 的 `postMessage` 監聽，以相容 iframe 嵌入場景；無 hash 時 body 加 `.tiled` class 平鋪展示所有 `.device`，有 hash 時只顯示對應單頁。
9. **極度重要（單頁模式 CSS 陷阱）：** 單頁模式下**禁止**對 `.gallery` 等包裹容器設定 `display: none`，否則內部 `.device` 即使有 `!important` 也不會顯示（CSS 繼承：父隱藏則子不可見）。正確做法：保持 `.gallery` 為 `display: block`，隱藏每個 `.device-wrapper`，僅對 `.device-wrapper.active` 設定 `display: flex`。JS init 中透過 `device.closest('.device-wrapper')` 找到父容器加 `active` 類。
10. 儲存路徑：`[需求名]/原型/[需求名]-prototype.html`（相對於專案根目錄）
11. 原型 HTML 底部必須加入 `<script src="../../scripts/prototype-export-client.js?v=YYYYMMDD"></script>`，匯出按鈕使用 `id="exportFab"` 或 `.export-btn`，不要繫結舊的 `html-to-image` 匯出函式。
    > **路徑說明：** 原型位於 `[需求名]/原型/`，而匯出腳本在專案根目錄 `scripts/` 共享，因此需 `../../`（退兩級）回到根目錄再進 `scripts/`。
12. **極度重要（原型 ↔ PRD 內容對齊）：** 原型中展示的所有文案、資料、狀態標籤、按鈕文字、提示資訊必須與 PRD「六、詳細方案」中對應行的「描述」列內容逐條一致。具體對齊規則：
    - **文案對齊**：原型中的標題、按鈕文字、提示文案、空狀態文案必須與 PRD 描述中的文字完全一致，不允許原型上寫"開始分析"而 PRD 寫"立即分析"
    - **資料對齊**：原型中使用的示例資料（如"剩餘額度 8/10次"、"綜合得分 82分"）必須與 PRD 描述中提到的資料保持一致
    - **狀態對齊**：原型中展示的狀態標籤（已完成/分析中/失敗等）及其顏色必須與 PRD 描述的狀態定義一致
    - **流程對齊**：原型中的頁面跳轉邏輯（點選A → 跳轉到B）必須與 PRD 描述的互動流程一致

### 3.2 設計規範

- 視覺風格以專案根目錄 `DESIGN.md` 為唯一依據（見 §3.0）；它沒寫到的才按產品品牌、目標使用者和使用場景補充，不預設行業配色
- 原型容器尺寸必須與真實業務端一致，**不要預設套手機豎屏**；桌面工作台、大屏或橫屏應用應使用對應的真實比例
- 無 hash 預覽場景下，頁面容器需要支援多頁平鋪；iframe 單頁預覽場景再按 hash 精確展示
- 容器使用 `.device` 類；建議透過 `.gallery-mode` 和 `.single-mode` 兩種狀態切換展示方式
- 若頁面使用字型圖示、彩色圖示按鈕或狀態徽標，必須提前考慮匯出後的還原效果，優先採用內聯 SVG 或為匯出單獨準備 fallback

### 3.3 嵌入PRD的方式

> **兩種形態都合法，按素材實際情況選（§2.3）：**
> - **高畫質截圖**（已有穩定截圖、或原型依賴後端跑不起來時優先）：
>   ```html
>   <img class="proto-shot" src="../原型截圖/[需求名]-signin.png" alt="簽到結果" width="1672" height="941">
>   <p class="asset-note"><a href="../原型/[需求名]-prototype.html#signin">開啟可點選原型</a></p>
>   ```
>   配 `.proto-shot{max-width:100%;height:auto;border-radius:8px;}`。**`width`/`height` 寫真實畫素**，避免載入抖動、並讓 §2.8 複製出圖尺寸正確。**不要為了"統一成 iframe"而把已有的高畫質截圖換掉**——截圖在Notion/Google 文件裡貼上更穩。
> - **可互動 iframe**（需要評審時直接點）：等比縮放容器寫法見下。

原型透過 **等比例縮放容器 + `<iframe>`** 嵌入到 PRD 表格對應行的「原型」列：

```html
<div class=”prototype-frame” data-pw=”375” data-ph=”700”>
  <iframe 
    class=”prototype-iframe”
    src=”../原型/[需求名]-prototype.html#page-id”>
  </iframe>
</div>
```

> **⚠️ 關鍵實現約束（踩坑記錄）：**
>
> **禁止使用 CSS 變數 + calc 來設定 iframe 尺寸。** `calc(var(--prototype-width) * 1px)` 這種 unitless 變數乘 px 的寫法在多數瀏覽器中不生效，會導致原型區域一片空白。
>
> **正確做法：** 原始寬高透過 `data-pw` / `data-ph` data 屬性傳遞，由 JS 讀取後顯式設定 iframe 的 `width`、`height`（帶 px 單位）和 `transform: scale()`。

**CSS 規範：**
```css
.prototype-frame {
  position: relative; overflow: hidden; border-radius: 8px;
  background: #f5f5f5; width: 320px; /* 預設預覽寬度 */
}
.prototype-iframe {
  position: absolute; top: 0; left: 0;
  border: none; background: transparent;
  transform-origin: top left;
}
```

**JS 縮放邏輯（必須內嵌在 PRD HTML 底部）：**
```js
function scalePrototypes() {
  document.querySelectorAll('.prototype-frame').forEach(frame => {
    const pw = parseInt(frame.dataset.pw) || 375;
    const ph = parseInt(frame.dataset.ph) || 700;
    const iframe = frame.querySelector('.prototype-iframe');
    if (!iframe) return;
    iframe.style.width = pw + 'px';
    iframe.style.height = ph + 'px';
    const containerWidth = frame.clientWidth || 320;
    const scale = containerWidth / pw;
    iframe.style.transform = 'scale(' + scale + ')';
    frame.style.height = Math.round(ph * scale) + 'px';
  });
}
window.addEventListener('load', scalePrototypes);
window.addEventListener('resize', scalePrototypes);
setTimeout(scalePrototypes, 500); // 兜底：確保 iframe 載入後尺寸正確
```

> **其他注意事項：**
> - 滑鼠 hover 到原型右下角區域時出現可拖曳縮放的互動提示，不要展示常駐箭頭或按鈕。
> - 使用者拖曳任意一個原型後，當前 PRD 頁面中的所有原型預覽都要保持統一比例同步變化，不能只改當前這一張。
> - 原型列寬和對應容器尺寸要跟隨縮放一起自動變化，不允許出現”原型變大了，但表格邊界還得手動再拉”的情況。
> - 不要額外做全域性”縮放操作面板”。
> - `border: none; background: transparent;` 去除外框，避免雙重邊框視覺問題。
> - 相對路徑基於 PRD 檔案所在目錄（`[需求名]/需求文件/`）往上一級，再進同需求的 `[需求名]/原型/` 目錄。PRD 與原型同屬一個需求頂層目錄、互為同級，故 iframe 的 `src` 仍寫 `../原型/[需求名]-prototype.html#page-id`（路徑值不變）。

### 3.4 原型互動增強規範

#### 3.4.1 Tab 切換模式

當多個關聯頁面屬於同一層級時（如 報告概覽/明細分析/行動計劃），**合併為單頁 + Tab 面板切換**，而非拆成獨立頁面。

**HTML 結構模式：**
```html
<!-- Tab 切換欄 -->
<div id="xxxTabs" style="background:#F0F0F5;border-radius:12px;padding:3px;display:flex">
  <div class="xxx-seg active" data-tab="tab-a" style="flex:1;...">標籤A</div>
  <div class="xxx-seg" data-tab="tab-b" style="flex:1;...">標籤B</div>
  <div class="xxx-seg" data-tab="tab-c" style="flex:1;...">標籤C</div>
</div>
<!-- Tab 面板 -->
<div id="tab-a" class="xxx-panel">面板A內容</div>
<div id="tab-b" class="xxx-panel" style="display:none">面板B內容</div>
<div id="tab-c" class="xxx-panel" style="display:none">面板C內容</div>
```

**CSS：**
```css
.xxx-seg { color: #8E8EA0; background: none; font-weight: 500; transition: all .2s; }
.xxx-seg.active { background: #fff; font-weight: 600; color: #1a1a2e; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
```

**JS：**
```js
// 共享切換函式
function switchTab(tabId) {
  document.querySelectorAll('.xxx-seg').forEach(s => s.classList.toggle('active', s.dataset.tab === tabId));
  document.querySelectorAll('.xxx-panel').forEach(p => p.style.display = 'none');
  var target = document.getElementById(tabId);
  if (target) target.style.display = '';
}
// 繫結點選
document.querySelectorAll('.xxx-seg').forEach(seg => {
  seg.addEventListener('click', function() { switchTab(this.dataset.tab); });
});
```

**適用場景：** 報告類（多維度展示）、設定類（分類配置）、詳情類（多Tab資訊）。

#### 3.4.2 PostMessage 雙向通訊協議（PRD ↔ 原型 iframe）

**原型 → PRD（頁面切換通知）：**
```js
// 原型內部：頁面切換時
window.parent.postMessage({ type: 'page-changed', page: 'report-overview' }, '*');
// 原型內部：Tab 切換時（附帶 tab 欄位）
window.parent.postMessage({ type: 'page-changed', page: 'report-overview', tab: 'tab-errors' }, '*');
```

**PRD → 原型（導航指令）：**
```js
// PRD 頁面選擇器切換時
frame.contentWindow.postMessage({ type: 'navigate', page: 'camera' }, '*');
```

**Tab 別名對映（向後相容）：** 當頁面合併為 Tab 後，舊的頁面名需要對映到新的 Tab ID：
```js
const tabAliases = { 'report-errors': 'tab-errors', 'report-plan': 'tab-plan' };
// 收到 navigate 指令時：若命中 alias 則跳到目標頁 + 切換 Tab
if (tabAliases[page]) { navigateTo('report-overview'); switchTab(tabAliases[page]); }
```

**PRD 側同步處理：** PRD 的訊息監聽器需要根據 `tab` 欄位反查選擇器顯示值：
```js
const tabToAlias = { 'tab-overview': 'report-overview', 'tab-errors': 'report-errors', 'tab-plan': 'report-plan' };
window.addEventListener('message', function(e) {
  if (e.data && e.data.type === 'page-changed') {
    const sel = document.getElementById('pageSelect');
    if (sel) sel.value = (e.data.tab && tabToAlias[e.data.tab]) ? tabToAlias[e.data.tab] : e.data.page;
  }
});
```

### 3.5 Pencil 高保真設計（可選增強）

> Pencil 是內建 MCP 協議的設計工具，Claude Code 透過 MCP 直接呼叫其設計能力，可以產出比純 HTML 更精美的高保真原型。
>
> **本專案已安裝 pencilplaybook**（`.claude/skills/pencilplaybook/`）。進入本節時先讀它的 SKILL.md；token map 從 `DESIGN.md` frontmatter 取值；它的感知規則（disabled 40%、hover ≥8% 亮度差、暗底正文不用純白、大標題負字距）優先於下文的通用描述。接線見 `pm-design.md` 流程 D。

#### 3.5.1 觸發與選擇

HTML 原型完成後，**主動詢問使用者**是否需要 Pencil 增強：

> HTML 互動原型已完成。需要用 Pencil 生成高保真設計稿嗎？
> - **使用 Pencil**：設計效果更精美，可匯出高畫質截圖，適合對外評審
> - **跳過 Pencil**：直接使用 HTML 原型，適合內部快速迭代
>
> （如果你的電腦沒有安裝 Pencil，可以跳過，後續隨時補做）

使用者選擇使用 Pencil 後，進入環境檢測流程。

#### 3.5.2 Pencil 環境檢測與安裝引導

**自動檢測流程：**

```
使用者選擇使用 Pencil
    ↓
檢測 /Applications/Pencil.app 是否存在
    ├─ 不存在 → 引導安裝 Pencil（見下方）
    └─ 存在 → 檢測 Pencil 是否正在執行（ps aux | grep Pencil）
         ├─ 未執行 → 提示使用者：「請先開啟 Pencil 應用，開啟後告訴我」
         └─ 已執行 → 檢測 MCP 連線是否可用
              ├─ MCP 不可用 → 檢查 .mcp.json 配置 + 嘗試 WebSocket 直連降級
              └─ MCP 可用 → 開始 Pencil 設計流程 ✅
```

**Pencil 安裝引導（未安裝時展示）：**

> **Pencil 安裝步驟：**
> 1. 前往 Pencil 官網下載 Mac 版安裝包
> 2. 將 Pencil.app 拖入 `/Applications/` 目錄
> 3. 首次開啟後，在 Pencil 設定中啟用 **MCP Server**（會自動生成 `~/.pencil/mcp/` 目錄）
> 4. 在專案根目錄建立 `.mcp.json` 配置檔案：
> ```json
> {
>   "mcpServers": {
>     "pencil": {
>       "command": "~/.pencil/mcp/claudeCodeCLI/out/mcp-server-darwin-arm64",
>       "args": ["--app", "claudeCodeCLI", "-enable_spawn_agents"]
>     }
>   }
> }
> ```
> 5. 重啟 Claude Code，確認 MCP 連線成功
>
> 安裝完成後告訴我，我繼續幫你畫高保真原型。如果暫時不想裝，可以跳過此步驟，HTML 原型不受影響。

#### 3.5.3 設計變數體系

Pencil 設計和 HTML 原型應共用同一套配色體系，確保視覺一致性。以下變數為產品無關的基礎示例，實際色值根據品牌規範和目標使用者調整：

| 變數 | 色值 | 用途 | HTML CSS 對應 |
|------|------|------|---------------|
| `$primary` | `#00B894` | 主色（薄荷綠） | `--color-primary` |
| `$accent` | `#0EA5E9` | 輔助色（藍） | `--color-accent` |
| `$bg` | `#F7F8FA` | 頁面背景 | `background` |
| `$border` | `#F0F0F5` | 卡片描邊 | `border-color` |
| `$text-primary` | `#1A1A2E` | 主文字 | `color` |
| `$text-secondary` | `#8E8EA0` | 輔助文字 | `color` |
| `$danger` | `#FF6B6B` | 錯誤/失敗 | 狀態標籤 |
| `$warning` | `#FFB946` | 警告/進行中 | 狀態標籤 |

- 在 Pencil 中透過 `set_variables` 設定全域性變數
- 在 HTML 中確保相同色值，不要出現 Pencil 用 `#00B894` 而 HTML 用 `#00c9a7` 的不一致
- 使用者可根據產品風格自定義這套變數，但兩端必須同步

#### 3.5.4 Pencil 設計工作流程

```
HTML原型（已完成） + 環境檢測通過
    ↓
① 開啟 Pencil → open_document（新建或開啟已有 .pen 檔案）
    ↓
② 設定設計變數 → set_variables（寫入 3.5.3 中定義的配色變數）
    ↓
③ 載入設計規範 → get_guidelines（獲取可用的 guide 和 style 列表）
    ↓
④ 批次建立頁面 → batch_design + spawn_agents（多頁面可並行）
   · 每次 batch_design 不超過 25 個操作
   · 多頁面場景用 spawn_agents 拆分為並行子任務
   · 先建立頁面骨架（frame/layout），再逐步填充內容
    ↓
⑤ 截圖驗證 → get_screenshot（逐頁截圖檢查效果）
   · 必須仔細檢查截圖：佈局對齊、文字可讀性、顏色一致性
   · 發現問題立即用 batch_design 修正
    ↓
⑥ 向使用者展示確認
   · 將截圖展示給使用者，逐頁確認
   · 使用者提出修改意見後迭代
    ↓
⑦ 匯出 PNG → export_nodes
   · 格式：PNG，2x 解析度
   · 輸出目錄：[需求名]/原型截圖/
   · 命名規則：[需求名]-[頁面ID].png
    ↓
⑧ HTML ↔ Pencil 視覺一致性校準（見 3.5.5）
    ↓
⑨ 更新 PRD
   · 原型列 iframe 仍指向 HTML 原型（保持可互動預覽）
   · 描述列可附上 Pencil 匯出的高保真截圖作為視覺參考（可選）
```

#### 3.5.5 HTML ↔ Pencil 視覺一致性校準

Pencil 設計稿完成後，**必須反向校準 HTML 原型**使兩端視覺一致。否則 PRD 中左側截圖和右側 iframe 會出現明顯的視覺差異。

**校準步驟：**

1. **逐頁讀取 Pencil 節點屬性**：用 `batch_get` 讀取每個頁面關鍵節點的顏色、漸變、間距、圓角
2. **對照檢查清單**：
   - 漸變色值和方向（如 `linear-gradient(135deg, #00B894, #0EA5E9)` vs `90deg`）
   - 卡片邊框（Pencil 用 `border` 還是 `box-shadow`？HTML 需保持一致）
   - 狀態標籤配色（已完成=綠、分析中=橙、失敗=紅）
   - 按鈕樣式（漸變 vs 純色、圓角大小）
   - 字號和字重
3. **更新 HTML CSS**：逐一修正差異，保持 HTML 原型的互動能力不變
4. **重新整理 PRD 驗證**：在 PRD 雙欄預覽中確認左右一致

#### 3.5.6 MCP 工具呼叫參考

| 步驟 | MCP 工具 | 用途 |
|------|----------|------|
| 開啟檔案 | `open_document` | 傳入 .pen 檔案路徑，或 `"new"` 新建 |
| 瞭解規範 | `get_guidelines` | 先不傳參獲取列表，再按名稱載入具體 guide/style |
| 瞭解結構 | `get_editor_state` | 獲取當前畫布狀態，首次必須 `include_schema: true` |
| 讀取節點 | `batch_get` | 查詢已有節點、設計系統元件列表 |
| 設計操作 | `batch_design` | I()插入、U()更新、C()複製、R()替換、D()刪除、G()生成圖片 |
| 並行設計 | `spawn_agents` | 多頁面/多區塊拆分為並行 Agent |
| 截圖檢查 | `get_screenshot` | 傳入 nodeId 獲取截圖驗證 |
| 佈局檢查 | `snapshot_layout` | 檢查對齊和溢位問題 |
| 匯出圖片 | `export_nodes` | 匯出 PNG/JPEG/WEBP/PDF |
| 設計變數 | `get_variables` / `set_variables` | 管理全域性顏色、字型等主題變數 |

#### 3.5.7 檔案路徑約定

| 檔案型別 | 路徑 | 說明 |
|----------|------|------|
| Pencil 原始檔 | `[需求名]/原型/[需求名].pen` | 設計原始檔，可反覆編輯 |
| 匯出截圖 | `[需求名]/原型截圖/[需求名]-[頁面ID].png` | 2x 解析度 PNG |
| HTML 原型 | `[需求名]/原型/[需求名]-prototype.html` | 保持可互動，視覺對齊 Pencil 稿 |

#### 3.5.8 注意事項

1. **HTML 原型是主交付物**：Pencil 設計是視覺增強，HTML 原型仍然是 PRD 中嵌入的主要載體。沒有 Pencil 不影響整個工作流運轉
2. **Pencil 必須處於開啟狀態**：MCP 工具依賴 Pencil 應用執行，呼叫前確認 Pencil 已啟動
3. **batch_design 操作上限**：單次不超過 25 個操作，大設計拆分多次呼叫
4. **binding 命名**：每次 batch_design 呼叫必須使用全新的 binding 名稱，禁止跨呼叫沿用
5. **圖片節點**：沒有 `image` 型別節點，圖片透過 `G()` 操作應用為 frame/rectangle 的 fill
6. **spawn_agents 並行**：建立 N 個頁面時，spawn N-1 個 Agent，當前會話做最後一個
7. **截圖必查**：每次設計操作後必須 `get_screenshot` 驗證，不能盲寫
8. **設計變數同步**：Pencil 和 HTML 必須使用同一套色值，見 3.5.3

#### 3.5.9 MCP 連線故障排查

當 MCP 連線不可用時，按以下順序排查：

1. **檢查 Pencil 是否執行**：`ps aux | grep -i pencil`
2. **檢查 .mcp.json 配置**：確認 `command` 路徑指向 `~/.pencil/mcp/claudeCodeCLI/out/mcp-server-darwin-arm64`
3. **檢查是否有殭屍程序**：`ps aux | grep mcp-server` 檢視是否有多個殘留程序，用 `kill` 清理
4. **重啟 Claude Code**：退出並重新進入，讓 MCP 重新建立連線
5. **WebSocket 直連降級**：若 MCP bridge 始終無法恢復，可透過 Python websockets 直連 Pencil：
   - 連線地址：`ws://[::1]:61969/`
   - 認證：傳送 `{"type": "identify", "app": "claudeCodeCLI"}` 獲取 `client_id`
   - 呼叫格式：`{"request_id": "xxx", "client_id": "xxx", "name": "get-editor-state", "payload": {...}}`
   - 方法名使用 **kebab-case**（如 `batch-design`、`export-nodes`），不是 snake_case

### 3.6 原型完成後一致性自查（極度重要）

原型 HTML 全部繪製完成後，**必須逐頁對照 PRD 進行一致性校驗**，校驗通過後才能進入下一步。

#### 自查流程

```
原型繪製完成
    ↓
逐頁讀取原型 HTML 中的文案/資料/狀態
    ↓
對照 PRD「六、詳細方案」中對應行的「描述」列
    ↓
發現不一致？
    ├─ 原型錯誤 → 修改原型 HTML
    └─ PRD 描述不夠準確 → 修改 PRD 描述列
    ↓
全部一致 → 進入步驟四
```

#### 逐頁校驗檢查項

對每個原型頁面，依次檢查：

| # | 檢查項 | 說明 |
|---|--------|------|
| 1 | 頁面標題/導航欄標題 | 與 PRD 二級功能名一致 |
| 2 | 按鈕文字 | 與 PRD 描述中的操作文案一致 |
| 3 | 提示文案/說明文字 | 包括 Toast、彈窗內容、空狀態提示 |
| 4 | 示例資料 | 列表項名稱、數值、日期等 |
| 5 | 狀態標籤 | 文字 + 顏色 與 PRD 狀態定義一致 |
| 6 | 頁面跳轉目標 | data-goto / hash 跳轉與 PRD 流程一致 |
| 7 | Tab/分段標籤 | 標籤文字和數量與 PRD 一致 |

#### 交付宣告

校驗完成後，在回覆中附上一致性確認：

> ✅ 原型 ↔ PRD 一致性校驗完成，共 N 個頁面已逐一核對，全部通過。

---

### 3.7 設計關卡（§3.6 通過後 · 必做）

一致性自查只保證「和 PRD 寫的一樣」，不保證「看起來不像 AI 模板」。§3.6 通過後：

1. 用 hallmark `audit` 對 `[需求名]/原型/[需求名]-prototype.html` 打分，取得問題清單。
2. 違反 `DESIGN.md` 的項目直接修，修完再 audit 一次；品味類建議列給使用者選。
3. 對外關鍵介面，或使用者要求時，再跑 impeccable `critique`；使用者指名修某面向時用它的分項命令（`typeset` / `layout` / `colorize` / `quieter` / `animate` / `clarify` / `adapt`），一次一個。
4. 交付前 impeccable `polish` 一次。
5. 在本輪回覆中告訴使用者 audit 分數、修了什麼、哪些建議留給他決定；不另存紀錄檔。使用者明確否決的建議（例如「不要動效」）寫進 `.pm-workflow/context/[需求名].md` 的約束段，避免下次又提。

原型定稿且引入新元件慣例時，跑 impeccable `document` 回寫 `DESIGN.md`（`pm-design.md` 流程 E）。

## 步驟四：產出流程圖與互動流程圖（均可裁剪）+ 時序圖章節規範

> **前置判斷：** 本步驟覆蓋 PRD 三個按需裁剪章節（見 2.2 / 1.3.1）：「四、業務流程圖」（Mermaid 檔案，業務邏輯層，§4.1–4.5）、「五、互動流程圖」（介面跳轉鏈路層，獨立 HTML，§4.6）與「八、時序圖」（端側編排層，研發/測試向，**PRD 內 Mermaid 原始碼文字章節**，§4.7）。三者各自獨立裁剪：省略哪章就跳過對應小節；前兩者都省略則不產出 `[需求名]/流程圖/` 目錄。以下規範僅對保留的章節執行。

### 4.1 規範與視覺風格（**核心：不要用 Mermaid 預設主題**）

> **踩坑記錄：** 舊版流程圖直接用 `theme:'default'`，出來是**深紫塊 + 粗黑線 + 白字**的 Mermaid 出廠樣，和 PRD 的淺色文件體系完全脫節——放到 PRD 裡像貼錯圖。**故把視覺風格固化為下面這套「淺底·細描邊·圓角·直角連線」**，與互動流程圖、PRD 三處保持同一套觀感。

**① 檔案與渲染：**
1. 使用 **Mermaid** 語法繪製，儲存為獨立 HTML 檔案
2. `mermaid.esm.min.mjs` 透過 jsdelivr CDN 引入
3. 每個圖表是獨立的 `<div class="chart-container">` 塊
4. 儲存路徑：`[需求名]/流程圖/[需求名]-flow.html`（相對於專案根目錄）

**② 頁面外殼（與互動流程圖 / PRD 同款）：**
```css
body {
  font-family: "Microsoft YaHei", "微軟雅黑", "PingFang SC", "Hiragino Sans GB", sans-serif;
  background: #f8f8fc; padding: 32px 24px; margin: 0; color: #30285b;
}
.chart-container {
  background: #fff; border-radius: 14px; padding: 28px 24px;
  border: 1px solid #ece9f6; box-shadow: 0 2px 12px rgba(48,40,91,.05);
  max-width: 1200px; margin: 0 auto 24px;
}
h1 { font-size: 22px; font-weight: 700; color: #30285b; text-align: center; margin: 0 0 6px; }
.subtitle { font-size: 13px; color: #8b86a3; text-align: center; margin: 0 0 22px; }
```
> **禁用**：`linear-gradient` 背景、`box-shadow` 重投影、彩色實心大色塊、圓角超過 16px 的氣泡。整套觀感是"文件裡的一頁"，不是"宣傳頁的一張圖"。

**③ Mermaid 主題（`themeVariables` 固定，只改 `--flow-accent` 一處配主色）：**
```js
mermaid.initialize({
  startOnLoad: true,
  securityLevel: 'loose',
  theme: 'base',                       // 必須是 base，default 會把節點塗成深紫
  themeVariables: {
    primaryColor:        '#faf9ff',    // 節點底色：極淺，不是色塊
    primaryBorderColor:  '#cbc4e7',    // 節點描邊：細，淺紫灰
    primaryTextColor:    '#30285b',    // 節點文字：深墨紫，不是白字
    lineColor:           '#8d82b1',    // 連線：中紫灰，1.8px
    textColor:           '#30285b',
    fontSize:            '15px',
    fontFamily:          '"Microsoft YaHei","微軟雅黑","PingFang SC",sans-serif'
  },
  flowchart: { useMaxWidth: false, htmlLabels: true, curve: 'linear', nodeSpacing: 60, rankSpacing: 70, padding: 18 },
  sequence:  { mirrorActors: false, messageMargin: 40 }
});
```
- **`curve: 'linear'`**：連線走**直角折線**，禁止 `'basis'`/曲線（曲線在多分支時相互交叉壓節點，評審看不清，也違反 §4.6 ③ 的同一條約定）。
- **節點用「淺底 + 細描邊 + 深字」，不用實心色塊。** 需要區分型別時靠**形狀**（`[]` 流程 / `{}` 判斷 / `([])` 起止），不靠填充色。
- 只有"開始/結束"這類終點節點允許 `classDef` 給一個淺色填充（如 `fill:#efeaff,stroke:#b9aee6`），**全域性實心色塊不超過 1 類**。

**④ 間距（防遮擋的硬性下限）：**
- `nodeSpacing: 60`、`rankSpacing: 70` 是**下限**；節點標籤偏長時繼續調大，不要靠縮小字號解決。
- 連線標籤兩側必須留白：Mermaid 用 `edgeLabelBackground` 或 `%%{init}%%` 指定與容器同色，標籤不得騎線上上壓字。
- **畫布寧可拉寬，不許把字擠小。** `useMaxWidth: false` 保留真實寬度，靠 PRD 的 iframe 橫向滾動 / 縮放來看，不為了塞進列寬而全域性縮字。

**⑤ 驗收：** 產出後按 4.3 的清單逐條核，並在瀏覽器裡**放大到 100% 看一眼**——小於 100% 時任何遮擋和模糊都看不出來（同 §2.8 ⑤ 的教訓）。

### 4.2 常用圖表型別

| 圖表型別 | Mermaid關鍵字 | 適用場景 |
|----------|--------------|----------|
| 時序圖 | `sequenceDiagram` | 多角色/多系統互動（使用者→客戶端→服務端→AI） |
| 活動/流程圖 | `flowchart TD` | 單使用者操作路徑、異常分支處理 |
| 狀態圖 | `stateDiagram` | 訂單/任務狀態流轉 |

### 4.3 交付前必須逐項核對（**遮擋與越界零容忍**）

**① 語法層：**
- 活動圖中若節點標籤含有 `()` 等特殊字元，容易觸發 **Syntax error**，建議將此類圖表拆分為獨立檔案，逐一驗證
- 流程圖節點標籤如包含中文括號或引號，先用瀏覽器渲染驗證後再嵌入
- 渲染報錯的**先修語法，不要直接刪圖或刪分支**（§4.1 ⑤）——刪掉的分支就是漏寫的需求

**② 視覺層（逐條打勾，任一不過就不能交付）：**

| # | 檢查項 | 怎麼算不合格 |
|---|--------|--------------|
| 1 | **無文字遮擋** | 任何連線壓住節點文字、標籤壓住連線、標籤之間互相重疊（這正是 §4.6 互動流程圖反覆踩的坑，業務流程圖同樣要查） |
| 2 | **無畫布越界** | 節點、標籤、迴流線超出畫布邊界被裁切；長標籤撐出容器 |
| 3 | **連線不穿節點** | 連線路徑穿過非起止節點的方框 |
| 4 | **直角折線** | 出現曲線/斜線（`curve` 必須為 `linear`） |
| 5 | **字號可讀** | 正文級標籤 < 14px；為塞進容器而縮字 = 不合格，應拉寬畫布 |
| 6 | **風格統一** | 出現深紫實心塊、白字、粗黑線、漸變背景（=漏改 `themeVariables`，見 §4.1 ③） |
| 7 | **主色一致** | 流程圖主色與 PRD `--pm-accent`、互動流程圖主色一致；換需求主色時三處一起換 |

**③ 出圖前必做的兩步：**
1. **放大到 100% 看一遍**——小於 100% 時遮擋和模糊看不出來（同 §2.8 ⑤）。
2. **在 PRD 的 iframe 裡再看一遍**——iframe 有自己的寬度約束，容器內不遮擋不等於嵌進 PRD 後也不遮擋；放不下的**調大 iframe 高度**，不要把圖壓扁。

### 4.4 嵌入PRD的方式

```html
<iframe 
  src="../流程圖/[需求名]-flow.html"
  style="width: 100%; height: 800px; border: none; background: transparent;">
</iframe>
```

### 4.5 匯出截圖必走本地匯出服務（必做 · 踩坑記錄）

> **背景（踩坑記錄）：** 流程圖常常比視口高很多。若匯出按鈕**直接在瀏覽器裡用 `html-to-image`/`html2canvas` 截 `.chart-container`**，長圖會被**截掉一半**（受瀏覽器畫布尺寸/視口限制）。專案早已為此做了**本地匯出服務**（`scripts/prototype_server.py`，Playwright 對每個 `.chart-container` 做**整元素截圖**，不受視口高度限制），卻容易在新生成流程圖時漏接，退化成半張圖。**故固化為必做項。**

**① 每個流程圖 HTML 必須接入匯出服務客戶端**（與原型匯出同一套）：
```html
<button class="export-btn" onclick="exportChart()">📸 匯出截圖</button>
<!-- 路徑取決於巢狀層級：[需求名]/流程圖/ 下為 ../../scripts/；舊扁平 流程圖/ 下為 ../scripts/ -->
<script src="../../scripts/prototype-export-client.js?v=YYYYMMDD-flow"></script>
```
- 客戶端會在**捕獲階段**攔截 `.export-btn`/`.export-fab`/`#exportFab` 的點選，轉而 POST `/api/screenshot` 到本專案的服務地址（連接埠從 `scripts/pm-runtime-config.js` 讀取，**別寫死連接埠**），由服務用 Playwright 截圖，輸出到 `[需求名]/流程圖截圖/`（舊扁平結構回退專案根 `流程圖截圖/`）。服務未啟動時會自動嘗試 launcher 喚起，仍失敗則提示使用者雙擊根目錄的啟動入口（Windows 是 `.bat`，macOS 是 `.command`）。

**② `onclick` 僅作降級兜底**：服務客戶端載入時它不會觸發（點選已被捕獲）。兜底實現必須**服務優先 + 整圖**：先 `window.exportPrototypeViaServer(btn)`，失敗再 `html-to-image`，且**必須按完整 scroll 尺寸截**，否則仍是半張：
```js
async function exportChart(){
  const btn=document.querySelector('.export-btn'), t=btn.textContent, bg=btn.style.background;
  btn.textContent='⏳ 匯出中...'; btn.disabled=true;
  if(window.exportPrototypeViaServer){ try{ await window.exportPrototypeViaServer(btn); return; }catch(e){ console.warn('服務匯出失敗，降級',e); } }
  try{
    const {toBlob}=await import('https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/+esm');
    const node=document.querySelector('.chart-container'), s=2;
    const blob=await toBlob(node,{cacheBust:true,backgroundColor:'#ffffff',pixelRatio:s,
      width:node.scrollWidth,height:node.scrollHeight,canvasWidth:node.scrollWidth*s,canvasHeight:node.scrollHeight*s,style:{transform:'none'}});
    const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='[需求名]-流程圖.png'; a.click(); URL.revokeObjectURL(a.href);
    btn.textContent='✅ 已匯出';
  }catch(e){ console.error(e); btn.textContent='❌ 失敗'; btn.style.background='#ef4444'; }
  setTimeout(()=>{ btn.textContent=t; btn.style.background=bg; btn.disabled=false; },2200);
}
```
**③ 自檢：** 流程圖產出後，按「四、原型一致性自查」同理確認匯出按鈕已 `include` 客戶端腳本、路徑層級正確（巢狀 `../../`）、點選能走服務出全圖——**不允許只留裸 `html-to-image` 按鈕**。

### 4.6 互動流程圖（Screen Flow · 介面跳轉鏈路整圖，可裁剪）

> **前置判斷：** 對應 PRD「五、互動流程圖」章節，按需裁剪（見 2.2 / 1.3.1）。核心介面 ≤2 個、或頁面間無跳轉鏈路且無狀態流轉 → 整節跳過。
>
> **定位：** 與 §4.1 的 Mermaid 流程圖**並存、各管一層**——Mermaid 管業務/時序/狀態邏輯，互動流程圖管「介面長什麼樣、從哪跳到哪」。目標是：**所有核心介面的縮圖拼成一整張圖，介面之間用帶觸發標籤的箭頭連線標註跳轉關係**，評審者不讀正文也能看懂整條產品鏈路。

**① 檔案與嵌入：**
- 儲存路徑：`[需求名]/流程圖/[需求名]-screenflow.html`
- PRD「五、互動流程圖」章節以 iframe 嵌入（同 §4.4 方式，高度按畫布實際高度給足），一整張圖即可，不拆多圖
- **章節內只放 iframe，不加說明段落**：圖本身自解釋（箭頭標籤+狀態機圖例），匯出入口等說明在 screenflow 頁頭自帶，PRD 裡不重複寫"這是什麼圖/怎麼匯出"之類的引導文字
- **必須帶縮放控制元件（放大/縮小/適配）**：右上角 `position:fixed` 一組 `📸 下載圖片 / ＋ / 百分比 / － / 適配` 按鈕 + 按住畫布拖曳平移（節點 iframe 已 `pointer-events:none`，整個畫布可抓取）。**嵌入 PRD（`self!==top`）預設"適配寬度"**，未手動縮放時視窗 resize 自動重新適配（如 PRD 開關雙欄）；**獨立開啟預設 100%**——匯出服務是獨立載入頁面，必須保證無縮放變換、按原尺寸截圖
- **「📸 下載圖片」按鈕放在縮放控制元件組裡（而非只放頁頭）**：頁頭在嵌入模式下隱藏，控制元件組常駐——PRD 內嵌預覽裡也能直接下載整張 PNG。按鈕保留 `class="export-btn"` 以被匯出服務客戶端捕獲攔截（同 §4.5，服務優先、html-to-image 兜底按原始尺寸截）
- **畫布底部留白**：最外側底部軌道的標籤之下再留 ≥30px，防止貼邊被 iframe/截圖裁切；頂部軌道同理
- **介面節點直接用縮放 iframe 引真實原型 hash 頁**（`../原型/[需求名]-prototype.html#page-id`，同級相對路徑），原型改動自動同步到互動流程圖，**禁止用截圖 `<img>` 拼貼**（會隨原型迭代失真）

**② HTML 結構：**
- 唯一畫布 `<div class="chart-container screenflow-canvas">`（`position:relative`，白底，寬度按佈局撐開）——**必須帶 `chart-container` 類**，本地匯出服務（§4.5）按該類做整元素截圖，長圖/寬圖不裁切
- 介面節點 `.flow-node`：內含 `.node-frame`（縮放 iframe，沿用 §3.3 的 `data-pw`/`data-ph` + JS 顯式設寬高與 `transform:scale()` 方案，禁 CSS 變數 calc）+ `.node-label`（節點下方介面名）+ 可選 `.node-badge`（狀態標記，如「首次使用」「上傳成功」）
- 佈局：主鏈路從左到右一行排開，分支/狀態變體（如 非首次使用）另起一行放在對應節點下方——與示意圖的排布方式一致
- 連線層 `<svg class="screenflow-svg">`：`position:absolute` 鋪滿畫布、`pointer-events:none`，置於節點之上

**③ 防遮擋幾何下限（零遮擋是硬指標，不是儘量）：**

> **踩坑記錄：** 互動流程圖反覆出現**文案遮擋**——箭頭標籤騎線上上、標籤壓住節點、長迴流線穿過中間節點。根因是"先擺節點、後補標籤"，標籤空間沒預留。**故把下面的間距下限固化；先給標籤留空間，再擺節點。**

| 量 | 下限 | 說明 |
|---|---|---|
| 同排節點水平間距 | **≥ 70px** | 留給豎直段連線 + 箭頭空間 |
| 上下排節點垂直間距 | **≥ 200px** | 要容納節點標籤(≈20px) + 水平軌道 + 標籤高度(≈22px) + 安全餘量 |
| 節點標籤與節點框 | 7px | `.node-label{margin-top:7px}` |
| 連線標籤四周 padding | **≥ 9px**（左右）/ 5px（上下） | 標籤白底矩形要完整包住文字，且不壓線 |
| 畫布四周留白 | **≥ 30px** | 最外側軌道標籤之下、之上都要留；貼邊會被 iframe/截圖裁切 |
| 迴流軌道間距（同側多條） | 每條 **≥ 28px** 錯峰 | 多條同側迴流線各佔一條軌道，不能擠同一通道 |
| 字號下限 | 節點標題 **≥ 13px**、邊標籤 **≥ 11.5px** | **禁止為適配 PRD 列寬縮字號**——畫布可以大，閱讀時用縮放看 |

**④ 零遮擋的保障機制（三道閘，缺一不可）：**

> **第一道：幾何約束（設計時）。** 按 ③ 的表格擺位。**先確定所有標籤文字與長度，再據此分配節點間距和軌道數**——不是擺完節點再想辦法塞標籤。
>
> **第二道：自動體檢 + 修復環（必須跑，直到通過為止）。** 初始化後呼叫幾何審計（見下方程式碼），檢測四類問題：**標籤壓節點、標籤互相重疊、連線穿非起止節點、連線穿其他標籤**，外加**畫布越界**。審計不過就按下面的順序修，改完**重新審計**，迴圈到 `ok:true` 才允許交付：
>
> | 優先順序 | 修法 | 適用 |
> |---|---|---|
> | 1 | **擴大畫布**（改 canvas 的 width/height，同步 SVG 的 `viewBox`/尺寸） | 內容越界、整體擁擠——首選，代價最小 |
> | 2 | **加大間距**（同排水平 / 上下垂直間距按 ③ 的上浮） | 標籤壓節點、標籤重疊 |
> | 3 | **重排路線或加軌道**（給同側迴流線分不同 `bend`，把擁擠通道的線挪到外側） | 連線穿節點、連線穿標籤 |
> | 4 | **拆分組**（一個畫布拆成兩個 `.chart-container`，各自帶標題） | 前三條都解決不了的大規模交叉——**此時要在圖注裡說明拆分邏輯** |
>
> **禁止的"修復"**：縮小字號、把標籤壓到節點上、刪掉導致遮擋的分支、用文字背景色蓋住遮擋痕跡（`background:white` 只能用於標籤自身的白底矩形，不能當作遮擋的遮羞布）。
>
> **第三道：匯出前攔截（機制保證）。** 匯出按鈕點選時**先審計，`ok:false` 就 `preventDefault` 並彈出具體問題列表**，不允許帶著遮擋出圖。這樣即使前面兩道漏了，也不會把有問題的圖交給評審。

```js
// 幾何審計：canvas 內所有 .flow-node / .edge-label / .flow-edge 做兩兩包圍盒 + 路徑取樣檢測
function auditFlow(canvas){
  const r = el => { const b = el.getBoundingClientRect(), c = canvas.getBoundingClientRect();
                    return { x:b.x-c.x, y:b.y-c.y, w:b.width, h:b.height, id: el.id || el.dataset.for || el.dataset.edge }; };
  const nodes  = [...canvas.querySelectorAll('.flow-node')].map(r);
  const labels = [...canvas.querySelectorAll('.edge-label, .edge-label-bg')].map(r);
  const edges  = [...canvas.querySelectorAll('.flow-edge')];
  const errs = [];
  const hit = (a,b,pad=2) => a.x-pad < b.x+b.w && a.x+a.w+pad > b.x && a.y-pad < b.y+b.h && a.y+a.h+pad > b.y;
  // ① 標籤壓節點 ② 標籤互相重疊
  labels.forEach(l => { nodes.forEach(n => { if(hit(l,n,0)) errs.push('標籤壓節點：'+l.id+' → '+n.id); });
                        labels.forEach(o => { if(l!==o && hit(l,o,0)) errs.push('標籤重疊：'+l.id+' / '+o.id); }); });
  // ③ 連線穿非起止節點 / 其他標籤 ④ 越界
  const cw = canvas.clientWidth, ch = canvas.clientHeight;
  nodes.concat(labels).forEach(n => { if(n.x<0||n.y<0||n.x+n.w>cw||n.y+n.h>ch) errs.push('畫布越界：'+n.id); });
  edges.forEach(e => { const L=e.getTotalLength(), m=e.getScreenCTM(); if(!m) return;
    const others = nodes.concat(labels).filter(b => b.id!==e.dataset.from && b.id!==e.dataset.to && b.id!==e.dataset.edge);
    for(let p=0;p<=L;p+=2){ const pt=e.getPointAtLength(p).matrixTransform(m), c=canvas.getBoundingClientRect();
      const q={x:pt.x-c.x, y:pt.y-c.y};
      others.forEach(b => { if(q.x>b.x-1&&q.x<b.x+b.w+1&&q.y>b.y-1&&q.y<b.y+b.h+1) errs.push('連線遮擋：'+e.dataset.edge+' / '+b.id); }); } });
  return { ok: errs.length===0, errors: [...new Set(errs)] };
}
// 匯出按鈕攔截（與 §4.5 的捕獲階段配合，服務匯出前先過這一關）
function guardExport(){ const c=document.querySelector('.chart-container'); const a=auditFlow(c);
  if(!a.ok){ alert('佈局檢查未通過，請先修復：\n'+a.errors.join('\n')); return false; } return true; }
```

> **自動擴畫布（推薦實現）：** 節點擺好後不用手算畫布尺寸——用 `Math.max(...所有節點/標籤的 right/bottom) + 30` 反推 canvas 的 width/height，同步寫 `viewBox`，**讓畫布去適應內容，而不是讓內容擠進固定畫布**。這樣"越界"這一類問題從根上消失。

**⑤ 箭頭繪製（關鍵實現約束）：**
- **禁止手寫死座標畫線。** 連線關係用資料驅動，JS 動態計算：

```js
// 每條邊：from/to = 節點 id；label = 觸發動作/條件；fromSide/toSide = 錨點方位
// bend = 同側軌道外擴距離（多條同側邊用不同 bend 錯峰）；fromOffset/toOffset = 錨點沿邊平移，防同點多線重疊
// labelT = 標籤在折線總長上的比例位置（預設取最長一段的中點）
const EDGES = [
  { from:'node-entry',  to:'node-scan',   label:'點選 開始掃描', fromSide:'right', toSide:'left' },
  { from:'node-entry',  to:'node-history',label:'非首次使用',        fromSide:'bottom', toSide:'top'  },
  { from:'node-report', to:'node-entry',  label:'點「返回」',        fromSide:'top', toSide:'top', bend:130, toOffset:-25 },
];
```
- **連線必須是直角折線（Manhattan 路由），禁止貝塞爾曲線/斜線**（踩坑記錄：曲線在長迴環、多分支時相互交叉壓節點，評審看不清）。逐段只能水平或垂直，按出/入方位路由：
  - 橫出橫入（right→left 等）：同 y 直連；不同 y 走中線 Z 形（`midX = (x1+x2)/2` 處兩個直角）
  - 橫出豎入 / 豎出橫入：一個直角拐點（`(x2,y1)` / `(x1,y2)`）
  - 豎出豎入對穿（bottom→top）：同 x 直連；不同 x 走中線 Z 形
  - **同側對（top→top / bottom→bottom，典型是"返回/重答"長迴環）：走"軌道"** —— `rail = 端點外側 bend px` 的水平橫杆，多條同側邊用不同 `bend` 錯峰，互不交叉且不越出畫布
- JS 在 load 後讀節點 `getBoundingClientRect()`（相對畫布、除以當前縮放係數）取錨點 → 生成途經點陣列 → 拼 `M/L` 折線 path + `marker-end` 三角箭頭；`resize` 與 iframe load 後 `setTimeout` 兜底重算
- 標籤放**最長一段的中點**（白底 `<rect>`+`<text>`，避免壓線；密集處用 `labelT` 挪位）；分支從同一節點引出多條邊，每條各帶條件標籤
- 節點/邊一旦增刪，只改 DOM 節點與 `EDGES` 陣列，連線自動重算——不存在改佈局後箭頭錯位的問題
- 交付前用無頭瀏覽器驗證：全部連線僅含水平或垂直段，且無越界、無交叉壓節點

**⑥ 狀態機說明（必做）：**
- **同一介面的不同狀態拆成獨立節點**（如「功能首頁·首次使用」vs「功能首頁·非首次使用」、「確認提交」vs「提交成功」），節點標籤註明狀態，不允許一個節點糊多個狀態
- 邊上的 label 寫「觸發動作＋條件」（如「點選確認上傳」「上傳成功後自動」「額度=0 時」），條件分支必須每條邊都有標籤
- 畫布角落放一個「狀態機圖例」塊（`.state-legend`）：列出關鍵物件的完整狀態流轉鏈（如 `分析任務：待上傳 → 上傳中 → 等待分析 → 已完成/失敗`），狀態名稱、顏色與 PRD 狀態定義及原型狀態標籤一致。**圖例塊本身也要進審計範圍**，不能被連線穿過

**⑦ 內容禁令：** 節點標籤、箭頭標籤、狀態圖例全部用產品語言，**不出現任何技術介面表述**（同 §2.3.1 ③）。

**⑧ 匯出與自檢（自檢不過不許交付）：**
- 按 §4.5 同一套規範接入本地匯出服務：`<script src="../../scripts/prototype-export-client.js?v=YYYYMMDD-screenflow"></script>` + `.export-btn` 按鈕，Playwright 對 `.chart-container`（即整張畫布）整元素截圖 → `[需求名]/流程圖截圖/`；**不允許裸 `html-to-image`**，降級兜底同 §4.5 ②
- 產出後逐項自檢，**任一項不過先修再交**：
  - **a) 遮擋與越界（硬指標）**：跑 ④ 的 `auditFlow()`，`ok:true`；在 100% 縮放下人眼看一遍，確認無標籤壓線壓節點、無越界被裁。
  - **b) 覆蓋完整**：節點覆蓋 PRD 詳細方案中的全部核心介面及其狀態變體。
  - **c) 邊與描述對應**：每條箭頭與描述列【互動說明】的「操作 → 結果」逐條對應，無缺邊、無多邊。
  - **d) 狀態一致**：狀態機圖例與 PRD 狀態定義及原型狀態標籤一致。
  - **e) 視覺統一**：主色與 PRD `--pm-accent`、業務流程圖一致（§4.3 ② 第 6、7 條同一套判據）。
  - **f) 匯出走服務**：匯出按鈕能出整圖，且遮擋未通過時被攔截（④ 第三道閘）。
  - **g) PRD 內複核**：嵌進 PRD 的 iframe 裡再看一遍——**iframe 內不遮擋才算通過**；放不下就調大 iframe 高度，不壓扁。

### 4.7 時序圖（研發/測試向 · PRD 內文字章節 · 可裁剪）

> **單一來源：** 若本需求已有 `[需求名]/技術規格/`，時序圖只放在 Spec 裡（見 pm-spec），PRD 省略本章並在 1.3.1 告知；兩處各放一份會在變更時失同步。
>
> **前置判斷：** 對應 PRD「八、時序圖」章節（**位於「資料埋點」之後、上線計劃/附錄之前，即正文最後**），按需裁剪（見 2.2 / 1.3.1）。**受眾是研發與測試**——研發照文字寫邏輯、測試照文字寫用例。無複雜端側編排的簡單需求（無語音/流式/多端協同/複雜動效狀態機）→ 整章跳過。

**① 形態（極度重要）：Mermaid 原始碼文字，不渲染成圖**
- 本章內容是**可複製的 Mermaid 原始碼文字塊**（`<pre class="seq-code">` 等寬深色程式碼塊），**不做 Mermaid 渲染、不出圖片、不用 iframe**——渲染圖研發/測試不好沿用；原始碼文字可直接讀、可整段複製到任意支援 Mermaid 的工具二次使用（踩坑記錄：首版做成渲染圖被打回）
- 每個程式碼塊右上角一個「📋 複製原始碼」按鈕（`navigator.clipboard` 優先、選區 `execCommand` 兜底）
- `<pre>` 不在 §2.7 編輯模組的可編輯選擇器內，原始碼不會被誤編輯，符合預期

**② 固定格式（兩圖為基本盤，可按需增減）：**
- 章首一句話說明本節構成與用途（1 張端側總時序 + N 張關鍵物件狀態圖，給研發/測試直接複製使用）
- **圖 1 · 端側互動編排總時序**：`sequenceDiagram`，泳道按當前需求實際參與方設定（如 使用者 / 前端 / 遊戲引擎或 SDK / 服務端），覆蓋從進入頁面到最終產物的完整編排：初始化、資源播放順序、錄音/輸入開關時機、請求與返回、alt/loop 分支、收尾跳轉
- **圖 2 · 關鍵物件狀態圖**：`stateDiagram-v2`，對核心展示物件（如角色動效、任務狀態）畫完整狀態流轉
- 每個程式碼塊下方附「**說明**」要點列表：列出圖內不展開的約定（如末幀延續、重試進入順序）與未納入項

**③ 書寫規範：**
- **動作名/資源名直接沿用真實資源目錄名**，不做二次命名（如 `出現-打招呼-介紹`、`傾聽迴圈`）
- 關鍵時序約束用 `Note` 標註（如「control 先返回也要等 done 且播報完成後再提交新 control 推進狀態」這類門控規則）
- 全域性異常處理用圖末 `Note over` 統一標註（網路異常重試、無識別文字補錄等），口徑與詳細方案【邊界說明】一致
- **技術欄位豁免**：本章允許出現介面/欄位/事件名（如 `voicechat/stream`、`nextStage`、`audio_chunk`）——§2.3.1 的"禁技術介面表述"只約束詳細方案描述列，時序圖本就是給研發/測試看的
- 原始碼雖不在 PRD 內渲染，交付前仍須在支援 Mermaid 的環境驗證一遍**無 Syntax error**（語法注意事項同 §4.3），保證研發複製即可用
- 參考本工作流 §4.7 的結構生成時序圖章節，並在交付前驗證 Mermaid 原始碼可直接沿用

**④ 一致性自檢：** 時序圖的分支與推進條件必須與詳細方案【功能邏輯】【邊界說明】口徑一致（異常處理、重試規則、次數限制等）——兩處衝突時**先對齊再交付**。

---

## 步驟五：交付與評審

### 5.1 交付格式

| 產出物 | 生成格式 | 交付方式 |
|--------|----------|----------|
| **PRD文件** | HTML (.html) | 瀏覽器開啟，直接截圖到Notion；或複製頁面內容貼上 |
| **原型** | HTML (.html) | 已內嵌在PRD的iframe中；也可單獨提供檔案 |
| **業務流程圖** | HTML (.html) | 已內嵌在PRD的iframe中；也可單獨提供檔案 |
| **互動流程圖** | HTML (.html) | 已內嵌在PRD「五、互動流程圖」章節iframe中；可經本地匯出服務匯出整張PNG |
| **時序圖** | PRD 內文字章節 | Mermaid 原始碼程式碼塊 + 一鍵複製按鈕（「八、時序圖」，正文最後）；研發/測試直接複製原始碼使用，不渲染成圖 |

> **交付前必做：** 跑一次 `validate_prd.py`（見 §5.2），並在回覆裡如實報告結果——**不要把"腳本沒跑"說成"已校驗"**，也不要把腳本通過說成"全文人工複核完畢"。

> **交付到Notion的方式：**
> 在瀏覽器中開啟 PRD HTML 檔案，對需要的部分用截圖工具（Mac: `Cmd+Ctrl+Shift+4`）截圖，然後直接 `Cmd+V` 貼上到Notion 或 Google 文件。

### 5.2 PRD最終檢查清單

> **第一步：先跑機械校驗，紅了先修（不要靠肉眼）。**
> ```sh
> python3 scripts/validate_prd.py [需求名/需求文件/需求名-PRD.html]
> # Windows 上沒有 python3 命令，用官方啟動器：
> # py -3 scripts\validate_prd.py …
> # 專案還沒裝過 skill 時，直接用 skill 目錄裡的那份：
> # python3 .agents/skills/studio-pm-workflow/assets/scripts/validate_prd.py …
> ```
> 不帶參數會自動掃描當前目錄下所有 `*-PRD.html`。它查的是**機械可判定**的部分：核心章節是否存在、有無版本記錄章節與修改痕跡（刪除線、「已修改」「已確認：」等標記）、有無獨立異常章節、章節編號連續性、六張表的表頭與列數、專案資訊是否雙列、詳細方案每行 `data-preview`、原型列是否有內容、描述列是否用 `.desc-block`（含 `<br>` 硬換行檢測）、埋點 snake_case 與六列、`#prdContent` 內是否有正文 `<style>`、需求目標表頭。
> **腳本通過 ≠ 合格**——視覺與內容品質仍需按下面的清單人工過；但**腳本不過就一定不合格**，先修到綠再往下走。

交付前確認（標 ★ 為核心骨架，始終檢查；其餘僅在該章節本次保留時檢查）：
- [ ] ★ **校驗腳本通過**（見上方命令），無 FAIL 項
- [ ] ★ 保留的章節按 2.2 順序自上而下排列，編號連續無跳號
- [ ] ★ 本次省略的章節已在需求確認階段告知使用者並獲認可（1.3.1）
- [ ] ★ 專案資訊為獨立雙列表且「最後更新」為今天；**全文沒有版本記錄章節、修改標記、刪除線、「已確認：」殘留**（只留最新版）
- [ ] ★ 需求目標寫的是**使用者結果+可衡量口徑**，不是"完成開發/新增入口/跑通並驗證"；沒有真實基線的數字寫「待基線確認」而非編造（§2.2 ④ 正反對照）
- [ ] ★ 全文沒有獨立的「異常與邊界」章節；邊界情況都在對應功能的【邊界說明】裡
- [ ] ★ **範圍塊存在**：「本期範圍」與「本期不做什麼 / 暫不展開」都寫了，且步驟一確認的"不做"已在其中落地（§2.2 ⑤）
- [ ] ★ **詳細方案一行 = 一個介面或一個狀態變體**，不是把多個介面塞進一格（§2.2 ⑦）
- [ ] ★ 描述列按 §2.3.1 組織：【頁面元素】【互動說明】**兩個必出塊每格都有**；按需塊逐條對照判定條件（**離了本頁就不成立才寫**），跨頁共享規則已上提到需求概述規則表而非每頁抄一遍；**每條獨立成段/成列表項（無多編號擠成一段）**；無"同上""詳見 x.x"這類指代；全文**無任何技術介面表述**
- [ ] ★ 結尾有「待後續確認的產品口徑」清單，全篇的"待確認"都已歸集（§2.2 ⑧）
- [ ] ★ 詳細方案表格為四列格式，rowspan合併一級模組，每個 `<tr>` 都帶 `data-preview`
- [ ] ★ 每個功能行對應的原型列有內容（高畫質截圖或 iframe 均可；iframe 無雙邊框白邊，截圖帶真實 width/height）
- [ ] ★ 原型中所有文案/資料/狀態 與 PRD「詳細方案」描述列完全一致（已通過 3.6 自查）
- [ ] ★ 「📋 一鍵複製全文」實測貼上一次：原型 iframe 已變成圖片（或服務未啟動時**如實提示**了「原型圖缺失」，不是靜默丟圖）——見 §2.8
- [ ] ★ 粘出去的圖**放大到 1000px 以上**再看一眼是否清晰——按文件裡的預設顯示尺寸（約 335px）看，任何解析度都一樣，糊不糊在這個尺寸下根本看不出來。見 §2.8 ⑤
- [ ] ★ **雙欄預覽預設是關閉的**：PRD 開啟時正文佔滿、右側面板不出現；點「雙欄預覽」才展開、按鈕文案變成「收起預覽」；再點收起後 iframe 不再後台載入——見 §2.6
- [ ] ★ 雙欄預覽的 `－/百分比/＋/適配` 可用：放大後 `.device-shell` 出捲軸、「適配」能回正、切頁後縮放模式保持——見 §2.6 ⑨
- [ ] ★ **撤銷/重做實測一輪**（§2.7 ⑤）：改一段文字、增一行、刪一行、刪一張表、拖一次列寬，各按 `⌘Z`/`Ctrl+Z` 逐步撤回都能復原（刪掉的行/表回來後按鈕和手柄仍可用），再 `⌘⇧Z`/`Ctrl+Y` 逐步重做；撤銷後新改一處、確認重做失效；儲存後重新開啟正常
- [ ] ★ 文件級 `<style>` 在 `#prdContent` 內、主色只由 `--pm-accent` 一處驅動（§2.5 ②③）
- [ ] ★ **三處主色一致**：PRD `--pm-accent`、業務流程圖、互動流程圖用的是同一個主色（§4.3 ② 第 7 條）
- [ ] （若保留業務流程圖）**無文字遮擋、無畫布越界、連線為直角折線**、渲染無 Syntax error，且已在 100% 縮放下和 PRD iframe 內各看一遍（§4.3 ②③）；若省略則確認未殘留空的流程圖 iframe
- [ ] （若保留時序圖）為**原始碼文字塊**（非渲染圖）且複製按鈕可用、原始碼經 Mermaid 環境驗證無 Syntax error、分支與推進條件與詳細方案【功能邏輯】/【邊界說明】口徑一致、技術欄位僅出現在本章（§4.7 自檢）
- [ ] （若保留互動流程圖）`auditFlow()` 返回 `ok:true`（無標籤壓節點 / 無標籤重疊 / 連線不穿非起止節點 / 無越界）、節點覆蓋全部核心介面與狀態變體、箭頭標籤與描述列【互動說明】逐條對應、狀態機圖例齊全、匯出走本地服務且遮擋未過時被攔截——§4.6 ④⑧
- [ ] （若保留資料埋點）埋點名為可理解的 snake_case、曝光/點選/結果分開、參數與參數值沿用埋點字典（無字典處寫「待確認」而非猜欄位）
- [ ] （若保留上線計劃）排期/灰度策略已寫明

### 5.3 迭代更新規則（極度重要）

> **鐵律：每次使用者新增或修改需求時，不能只更新直接提到的那一處。必須遍歷整份 PRD 文件以及關聯的原型、流程圖，把所有相關位置都同步更新。**

**Why：** PRD 是多處交叉引用的結構，漏改一處就會讓文件前後不一致、失去權威性。使用者曾反饋過只更新"五-2詳細方案"的模組卻忘了同步"三、需求概述"的功能清單表，導致文件失真。

**每次變更後必須遍歷的位置清單**：

| # | 位置 | 判斷是否需更新 |
|---|------|----------------|
| 1 | 📋 專案資訊與副標題 | 「最後更新」改為今天；功能範圍有實質變化時版本號遞增（必做）。**不新增任何修改紀錄** |
| 2 | 一、需求背景 | 是否影響業務視角、覆蓋產品、使用者洞察 |
| 3 | 二、需求目標 | 是否影響量化指標或目標項 |
| 4 | **三、需求概述** | ① 功能清單表：新增模組**必須加行**，功能調整必須改描述；② **範圍塊**：範圍或"不做"清單變化必須改；③ **跨頁共享規則表**：規則數值/口徑變化只改這裡（詳§2.3.1 ③） |
| 4.1 | **跨頁共享規則的引用方** | 規則表改了 → 檢查詳細方案裡引用它的各格是否仍成立（引用文字不需改，但要確認沒有格子裡又抄了一份舊值） |
| 5 | 四、業務流程圖 | 新增流程節點、分支、狀態流轉 |
| 6 | 五、互動流程圖（screenflow.html） | 新增/刪除介面或狀態變體 → 補/刪 `.flow-node` 節點與 `EDGES` 邊；跳轉關係變化 → 改箭頭與觸發標籤；狀態定義變化 → 同步狀態機圖例；**改動後必須重跑 `auditFlow()`，`ok:true` 才算改完**（見 §4.6 ④） |
| 7 | 六、詳細方案（使用者端 / 管理端 / 其他端，按當前需求實際存在的端組織） | 功能落地描述；不存在的端不要硬寫；描述列保持 §2.3.1 分塊結構；**新增介面 → 新增一行**（一行 = 一個介面，見 §2.2 ⑦） |
| 8 | 詳細方案 ·【邊界說明】 | 是否引入新的空態/極值/權限/異常場景 → 補進對應功能的【邊界說明】（**不新起獨立章節**），並與時序圖異常 Note 口徑一致 |
| 9 | 端側聯動與權限邊界 | 若涉及多端、後台、運營台或審核台，檢查是否需要同步 |
| 10 | 七、資料埋點 | 是否需要新埋點事件 |
| 11 | 八、時序圖（PRD 內原始碼文字塊） | 編排順序/分支/推進條件/異常口徑變化 → 同步總時序原始碼；新增關鍵物件或狀態 → 補狀態圖原始碼（見 §4.7） |
| 12 | 上線計劃（若存在） | 是否影響排期或灰度策略 |
| 13 | 附錄（若存在） | 名詞與參考資料是否仍成立 |
| 14 | 原型檔案（.html） | 新增頁面 + 更新 `pages` 陣列 + **逐頁檢查文案/資料/狀態是否與 PRD 描述一致（參照 3.6 節）** |
| 15 | PRD 雙欄預覽下拉項 + 滾動聯動 + 複製出圖 | 新增頁的 `CATALOG` 項 / `#pageSelect` option，並給詳細方案對應 `<tr>` 補 `data-preview=<value>`（見 2.6 ⑧ scroll-spy）；**並確認該頁能被 `/api/snapshot` 取到圖**（起服務後點一次「一鍵複製全文」，看 toast 有沒有報"生成失敗"），否則複製出去會缺這張原型（見 §2.8） |
| 16 | PRD 的頁面對映（如 `pageAliases`、端側頁面集合、預覽狀態） | 新增頁或刪除端側時需同步 |
| 17 | 正文末尾「待後續確認的產品口徑」清單 | 本次新產生的"待確認"要加進去；已確認的條目**把結論寫進正文對應位置，並從清單刪除**（清單只留仍未決的；全部確認完就整段刪掉） |
| 18 | 交付前 | 重跑 `validate_prd.py`（§5.2），確認改動沒有打破錶頭/分塊/data-preview/編號連續性 |

> **裁剪章節的處理：** 上表第 4/4.1/5/6/10/11/12/13 項對應的章節可能在初稿時已按 2.2 裁掉。遍歷到這些位置時：
> - 該章節**當前存在** → 按上表正常同步。
> - 該章節**當前不存在，但本次變更觸及了它**（如小需求升級後新增了流程分支、引入了新異常或新埋點）→ **需補回該章節**：先按 1.3.1 的方式告知使用者"本次需補回 X 章節，原因…"，確認後補寫，並按 2.2 順序插回正確位置、重排編號。
> - 該章節不存在且本次也不觸及 → 跳過。

**反向規則**：對原型 / 流程圖的獨立變更，同樣要反向檢查 PRD 各位置是否需要跟著改。

**跨文件同步**：本表只涵蓋 PRD 內部與原型、流程圖。變更若同時影響技術規格、驗收清單、原型驗證腳本、上線文件或 `DESIGN.md`，改走 `.agents/workflows/pm-change.md`（它包含本表，並把下游文件一起改到一致）。

**交付宣告**：迭代完成後，在對使用者的回覆中明確列出"本次同步更新了哪些位置"（含新增/省略/補回的章節），讓使用者能快速複核。 然後依 `pm-change.md` 步驟六提交到 git，理由寫在 commit 訊息裡，不寫進 PRD。

### 5.4 評審與迭代

1. 使用者評審PRD內容，提出修改意見
2. 根據反饋迭代修改
3. 最終確認後歸檔到 `[需求名]/需求文件/` 目錄

---

## 步驟六：上下文交接（會話續接）

> 需求溝通 + PRD 撰寫往往跨越多輪對話。當上下文即將耗盡時，必須將關鍵狀態持久化，確保新會話能無縫銜接。

### 6.1 觸發時機

以下任一情況出現時，**主動**執行交接流程：

- 系統出現上下文壓縮提醒（訊息被自動摘要/截斷）
- 使用者說"開新視窗""換個會話""繼續聊"等意圖
- AI 判斷當前會話剩餘空間不足以完成下一步驟

**觸發後立即提醒使用者**：
> 上下文快滿了，我先生成交接檔案，你開新視窗後發一句話就能恢復。

### 6.2 交接前：更新工作脈絡

把本次會話中**PRD 與其他交付物放不下、但下個會話必須知道**的現況，覆寫進隱藏檔 `.pm-workflow/context/[需求名].md`。它只有三段，每段都描述「現在」，不累積歷史：

```markdown
# [需求名] · 工作脈絡（隱藏檔，給 Claude 續接用）

## 目前進度
（例：PRD 與原型已完成並通過檢查；技術規格未開始）

## 使用者的偏好與約束
（例：客戶不接受彈窗；主色不可改；不要動效）

## 仍未決的問題
（與 PRD「待後續確認」清單一致，不重複寫 PRD 已有的內容）
```

交付物本身已經是最新版，所以這個檔案**不記錄做過什麼決策、改過什麼**。

### 6.3 生成交接檔案

儲存到隱藏路徑：**`.handoff/[需求名]-handoff.md`**（每次覆寫，只保留最新一份）

```markdown
# [需求名] · 會話交接

> 生成時間：YYYY-MM-DD HH:mm

## 現有交付物

| 產出物 | 路徑 |
|--------|------|
| PRD | [需求名]/需求文件/xxx-PRD.html |
| 原型 | [需求名]/原型/xxx-prototype.html |

## 下一步

新會話從 [具體步驟] 繼續。
```

### 6.4 生成恢復指令

交接檔案末尾附一段使用者可直接複製到新視窗的恢復指令：

```markdown
---

## 🔄 新視窗恢復指令（複製以下內容到新會話）

請讀取以下檔案恢復上下文，然後繼續工作：
1. @.handoff/[需求名]-handoff.md
2. @.pm-workflow/context/[需求名].md
3. @.agents/workflows/pm-prd.md
4. @[需求名]/需求文件/[需求名]-PRD.html （如已產出）

讀完後從「[具體步驟描述]」繼續。
```

### 6.5 新會話恢復流程

1. **讀取交接檔案與工作脈絡** → 掌握進度、約束、未決問題
2. **讀取工作流規範** → 確保產出格式一致
3. **讀取已有交付物** → 以檔案內容為準（交付物永遠是最新版）
4. **向使用者確認** → 簡要複述當前狀態，確認從哪裡繼續

---

## 目錄結構

> **核心原則：產物按「需求名」分資料夾。** 每個需求一個頂層目錄，自己的需求文件/原型/流程圖/截圖等都收納其中；`scripts/`、兩個啟動入口（`啟動原型匯出服務.command` / `.bat`）、`.handoff/`、`.pm-workflow/`、`.mcp.json`、`.agents/`、`PRODUCT.md`、`DESIGN.md`、`.claude/skills/` 為所有需求**共享**，留在專案根目錄。

```
PM工作流/
├── [需求名]/                       # ← 頂層 = 需求名，每個需求一個獨立目錄
│   ├── 需求文件/
│   │   └── [需求名]-PRD.html       # ← 輸出格式為 HTML，非 Markdown
│   ├── 原型/
│   │   ├── [需求名]-prototype.html # HTML 互動原型（主交付物，始終產出）
│   │   └── [需求名].pen            # Pencil 設計原始檔（可選，高保真模式）
│   ├── 流程圖/
│   │   ├── [需求名]-flow.html        # Mermaid 業務流程圖（按需；時序圖為 PRD 內文字章節，不落此處）
│   │   └── [需求名]-screenflow.html  # 互動流程圖·介面跳轉鏈路整圖（按需，見 §4.6）
│   ├── 原型截圖/                    # 該需求匯出的原型截圖
│   │   └── [頁面名].png            # HTML 匯出或 Pencil 匯出的 PNG
│   ├── 驗收清單/                    # 用到時才建（見 pm-acceptance）
│   ├── 資料分析/                    # 用到時才建（見 pm-data-analysis）
│   ├── 需求挖掘/                    # 用到時才建（見 pm-demand）
│   ├── 原型驗證/                    # 可用性測試腳本與結果（見 pm-validate）
│   ├── 技術規格/                    # 給工程師的技術交接 Spec（見 pm-spec）
│   ├── 上線/                        # 版本說明、上線檢查清單、落地頁、商店文案、定價（見 pm-launch）
│   └── 素材/                        # 使用者提供的原始材料（訪談逐字稿、客戶檔案），不是交付物
│
├── （另一個需求名）/                 # 結構同上，與上面互不混放
│
├── PRODUCT.md                      # 【共享】產品事實（impeccable init 產生，一次）
├── DESIGN.md                       # 【共享】設計系統：token 與元件慣例，所有原型以它為準
├── .claude/skills/                 # 【共享】設計層 skill：impeccable、hallmark、pencilplaybook、gsap-*、ui-ux-pro-max
├── scripts/                        # 【共享】輔助腳本和匯出服務
│   ├── pencil-draw-prompt.md       # Pencil 繪圖 Prompt 模板（參考用）
│   ├── start_service.py            # 服務入口：--check / --serve / --doctor
│   ├── pm_bootstrap.py             # 直譯器探測、執行環境準備、瀏覽器引擎探測
│   ├── pm_runtime.py               # 專案標識與連接埠推導、配置讀寫、健康檢查
│   ├── prototype_server.py         # Playwright 真實渲染 PNG 匯出服務（已支援巢狀目錄）
│   ├── prototype_launcher.py       # 輕量 launcher，按需拉起完整服務
│   ├── pm_launchagent.py           # macOS 按需啟動器的註冊/解除安裝
│   ├── prototype-export-client.js  # 原型匯出按鈕客戶端
│   ├── install_launcher.sh         # 裝/卸 macOS 按需啟動器（安裝時已預設註冊）
│   └── pm-runtime-config.js        # 自動生成：本專案服務地址（已 gitignore）
├── 啟動原型匯出服務.command           # 【共享】macOS 手動啟動（通常不用，點匯出會自動起）
├── 啟動原型匯出服務.bat               # 【共享】Windows 雙擊啟動，保持視窗開著
├── .handoff/                       # 【共享】會話交接檔案（上下文續接用）
│   └── [需求名]-handoff.md
├── .pm-workflow/                   # 【共享】執行配置與安裝清單（已 gitignore）
├── .mcp.json                       # 【共享】Pencil MCP 連線配置（可選）
├── .agents/workflows/              # 【共享】工作流定義
│   ├── pm-prd.md               # 主工作流：需求→PRD→原型→流程圖
│   ├── pm-demand.md            # 需求挖掘與分析工作流
│   ├── pm-acceptance.md        # 功能驗收清單工作流
│   └── pm-data-analysis.md     # 資料分析報告工作流
│
└── （skill 本體，隨 GitLab 分發）    # 【共享】assets/templates、assets/scripts
    ├── assets/templates/prd-content.html   # PRD 正文骨架（安裝時裝到專案 scripts/prd-content.html；寫 PRD 先複製它，見 §2.2）
    └── assets/scripts/validate_prd.py      # PRD 格式校驗（安裝時裝到專案 scripts/validate_prd.py；交付前必跑，見 §5.2）
```
