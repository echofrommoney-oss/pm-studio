# PM 工作台（pm-console）

給 studio-pm-workflow 用的本機前台：在瀏覽器裡跟 Claude 對話、選工作流，右邊即時看 PRD、原型、流程圖。
背後是在你的專案資料夾裡以無頭模式執行 Claude Code（`claude -p`），用的是你的 Claude 訂閱額度。

**一個產品專案裝一套。** 每套有自己的連接埠、對話紀錄和顏色，標題列顯示專案名稱，瀏覽器分頁圖示也是專案色，同時開兩個專案不會混。

## 需要的東西

- Python 3.9 以上
- Claude Code，已在終端機執行過一次 `claude` 並登入訂閱帳號
- 同一個專案資料夾先裝好 studio-pm-workflow

## 安裝（每個產品專案做一次）

```bash
# 1. 先裝 studio-pm-workflow
python3 /路徑/PM-K12--skills/scripts/initialize.py --project /路徑/產品A

# 2. 再裝工作台
python3 /路徑/pm-console/install_pm_console.py --project /路徑/產品A
```

Windows 把 `python3` 換成 `py -3`。重複執行會更新成最新版，不會動到對話紀錄。

## 使用

雙擊專案根目錄的 `開啟PM工作台.command`（macOS）或 `開啟PM工作台.bat`（Windows），瀏覽器會自動打開。保持那個視窗開著，關掉就停止。

1. 左邊「新增需求」，取一個需求名稱（會變成專案裡的資料夾）。
2. 中間選工作流，描述需求，⌘/Ctrl + Enter 送出。
3. Claude 會先列確認問題，你直接在對話框回答，它接著寫。
4. 右邊下拉選單切換 PRD、原型、流程圖；檔案一寫入就會自動更新。

同一個需求的多輪對話會延續上下文；按「開新對話」讓 Claude 從頭開始，檔案保留。
一個專案同一時間只跑一個任務。

## 設定（`.pm-console/config.json`，第一次啟動自動產生）

| 欄位 | 說明 |
|---|---|
| `project_name` | 顯示的專案名稱，留空用資料夾名 |
| `allowed_tools` | Claude 可以自動執行的動作。被擋下時畫面會提示，需要再加 |
| `permission_mode` | 預設 `acceptEdits`：可自動改檔，其他動作照 `allowed_tools` |
| `model` | 指定模型，留空用 Claude Code 預設 |
| `use_subscription` | `true` 時會移除環境變數 `ANTHROPIC_API_KEY`，確保走訂閱而不是 API 計費 |
| `language_rule` | 每輪都會附上的語言規則（預設繁體中文、台灣用語） |
| `workflows` | 工作流按鈕，分產出／設計／調整三排（PRD＋原型、需求挖掘、技術規格、驗收清單、資料分析、上線包；設計方向、檢查原型、加動效、高保真；變更、原型驗證、自由指令）。每顆可設 `group`。可自行新增，例如 `{"id":"d01","label":"轉成 D01","file":"","instruction":"把本需求的 PRD 轉成帶 REQ ID 的 D01…"}` |

## 安全

- 只聽 127.0.0.1，其他電腦連不到。
- 所有會執行或寫入的請求都要帶頁面內的一次性 token，且必須來自工作台頁面本身。
- 預覽只開放需求資料夾內的產物，`.pm-workflow`、`.pm-console` 等設定檔讀不到。
- Claude 在專案資料夾內執行；它能做什麼由 `allowed_tools` 決定，不建議改成 `bypassPermissions`。

## 資料放在哪

`.pm-console/`（已加進 .gitignore）：工作台對話紀錄、每個需求的 Claude session、設定、執行狀態。刪掉等於清空工作台紀錄，不影響產出檔案。

## 已知限制

- 已用模擬的 Claude Code 輸出完整測過流程（建立需求、串流、續聊、預覽、權限提示、安全檢查）；第一次接真的 Claude Code 時，若畫面一直停在「準備中」，請看啟動視窗的訊息，或在終端機執行 `python3 scripts/pm_console.py --check`。
- Windows 版未在實機測過。
- 截圖匯出、一鍵複製全文依賴 studio-pm-workflow 的匯出服務；工作台啟動時會自動幫你啟動它（Windows 首次約需一兩分鐘準備環境）。
