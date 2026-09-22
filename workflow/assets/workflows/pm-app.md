---
description: APP 開發工作流：依 ARCHITECTURE.md 選定的 APP 技術，依原型、DESIGN.md 與技術規格實作，接上本機後端
---

# APP 開發工作流

> APP 用什麼技術，由 `ARCHITECTURE.md` 的 `stack.app` 與 `services`（role: app）決定，本檔不預設。
> 下半部是 **APP 為 Flutter 時**的專屬做法；其他技術（React Native／Expo、原生 Swift／Kotlin…）照「通用規則」。

## 通用規則（任何 APP 技術）

### 前置

1. `ARCHITECTURE.md` 要有 role 為 app 的服務。沒有或沒有 stack → 先走 `pm-sysdesign.md` 和使用者討論選型，**不可自行選技術**。
2. 讀 `ARCHITECTURE.md` 第 6 節、`DESIGN.md`、本需求的原型與技術規格（`manifest.app_screens`）。缺技術規格 → 先走 `pm-spec.md`。
3. 後端最好已建好；還沒建也可以先做畫面，資料用假資料頂著，並在回覆中說明。

### 絕對不做

- **不啟動 APP、開發伺服器或模擬器**（工作台負責，啟動指令已封鎖）。
- 不把後端網址或金鑰寫死；從環境設定讀（工作台啟動時會帶入 `SUPABASE_URL`、`SUPABASE_ANON_KEY`、`BACKEND_URL`／`API_URL`，Android 模擬器上已自動換成 `10.0.2.2`）。
- 不手寫色碼、字型、圓角；用 `scripts/pm_tokens.py` 由 `DESIGN.md` 產生（Flutter 用 `dart`，React Native 用 `ts`）。
- 不打包正式版、不處理簽章與上架（上線階段才做）。

### 畫面

1. 依 `manifest.app_screens` 逐一實作，每個畫面對應原型的 `#page-id`；文案照 PRD 與原型。
2. **每個畫面檔加註解標記**，工作台用它顯示建置進度（任何語言都可以，放在註解裡）：
   ```
   // pm-screen: vaccination-list
   ```
3. 插畫未到位的地方用和原型相同的佔位；狀態齊全（載入中、空、錯誤、無網路）；可點區域夠大、支援系統字級。
4. 原生功能（推播、相機、定位、地圖）要在模擬器或實機確認，網頁預覽不準。

### 完成

1. 請使用者在右欄「APP」啟動，列出建議走一遍的流程與測試帳號。
2. 實作和原型或 Spec 有出入 → 不自己改文件，請使用者決定後走「變更」。
3. `python3 scripts/pm_sync.py commit 需求名 -m "[需求名] APP：一句話摘要"`。

---

## APP 為 Flutter 時

> 右欄「APP」分頁有專屬面板：手機外框的網頁預覽、模擬器啟動與畫面、熱重載、DevTools、建置進度。程式資料夾以 `ARCHITECTURE.md` 的 `dir` 為準（下文以 `app/` 舉例）。

### 專案骨架（第一次）

`app/` 還不存在時：

```bash
flutter create --org com.<工作室或產品英文> --project-name <產品英文小寫底線> --platforms ios,android,web app
```

`--project-name` 只能用英文小寫與底線（例如 `huru`）。建好之後：

- 套件依 `ARCHITECTURE.md` 第 6 節（狀態管理、路由）與後端選型；後端是 Supabase 時加 `supabase_flutter`。沒寫的先問使用者，不自行決定。
- 目錄：
  ```
  app/lib/
  ├─ main.dart            初始化 Supabase、主題、路由
  ├─ app_config.dart      讀 dart-define 的設定
  ├─ theme/tokens.dart    由 DESIGN.md 產生（勿手改）
  ├─ theme/app_theme.dart 用 AppTokens 組 ThemeData
  ├─ router.dart          go_router 路由表
  ├─ screens/             一個畫面一個檔
  ├─ widgets/             共用元件
  └─ data/                資料存取（Supabase 查詢集中在這裡）
  ```
- **Android 本機連線**：`android/app/src/debug/AndroidManifest.xml` 的 `<application>` 加 `android:usesCleartextTraffic="true"`（只在 debug，讓模擬器能連本機的 http 後端）。
- **iOS 本機連線**：`ios/Runner/Info.plist` 加 `NSAppTransportSecurity` → `NSAllowsLocalNetworking` = true。

### 設計 token

```bash
python3 scripts/pm_tokens.py dart --out app/lib/theme/tokens.dart
```

產生 `app/lib/theme/tokens.dart`（`AppTokens.colorsPrimary`、`AppTokens.radiusSm`…）。`app_theme.dart` 用它組 `ThemeData`（`ColorScheme`、`TextTheme`、元件圓角）。`DESIGN.md` 改了就重跑，不要手改 tokens.dart。

中文字型：`DESIGN.md` 指定的西文字型搭配 `PingFang TC`（iOS）／`Noto Sans TC`（Android）fallback。需要 Google Fonts 就用 `google_fonts` 套件。

### 接後端

工作台啟動 APP 時會帶 `--dart-define-from-file`，內含 `SUPABASE_URL`、`SUPABASE_ANON_KEY`、`BACKEND_URL`、`API_URL`、`APP_ENV`（Android 模擬器的網址已自動換成 `10.0.2.2`）。後端不是 Supabase 時用 `BACKEND_URL`。`app_config.dart`：

```dart
class AppConfig {
  static const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  static const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');
  static bool get hasBackend => supabaseUrl.isNotEmpty && supabaseAnonKey.isNotEmpty;
}
```

`main.dart` 在 `hasBackend` 為 false 時顯示清楚的提示畫面（「本機後端沒開：到工作台啟動 Supabase 後按重新啟動」），不要直接當掉。

資料表名、欄位名、權限行為照技術規格；RLS 會擋的操作要處理錯誤並顯示友善訊息。

### 畫面

1. 依 `manifest.app_screens` 逐一實作，每個畫面對應原型的 `#page-id`。
2. **每個畫面檔的第一行寫標記**，工作台用它顯示建置進度：
   ```dart
   // pm-screen: vaccination-list
   ```
   代號和 `manifest.app_screens` 一字不差。一個代號只標在一個檔案。
3. 文案照 PRD 與原型，不自己改寫。
4. 插畫：`DESIGN.md` 規定要插畫但圖檔還沒到的位置，用和原型相同的佔位（色塊＋註解標明情境與尺寸），之後替換。
5. 狀態齊全：載入中、空狀態、錯誤、無網路。空狀態與錯誤的文案照 PRD【邊界說明】。
6. 無障礙：可點區域至少 48×48、圖示按鈕加 `Semantics`／`tooltip`、支援系統字級放大。

### 避開 Material 預設長相（Flutter 專屬的設計規則）

hallmark 與 impeccable 的規則以網頁為主，套到 Flutter 時照下面做，否則畫面會回到 Material 的標準長相：

- **主題不只換色**：`ThemeData` 之外，用 `ThemeExtension` 放 `DESIGN.md` 的間距階梯、圓角、陰影、插畫佔位樣式，所有元件從這裡取值。
- **自己的元件庫**：在 `widgets/` 做 `AppScaffold`、`AppCard`、`AppButton`、`AppSectionHeader`、`AppEmptyState` 等，畫面只用這些，不直接用 Material 的 `Card`、`ElevatedButton`、預設 `AppBar`。
- **字級要有層次**：標題、內文、輔助文字至少三級，字級差要明顯；中文用 PingFang TC／Noto Sans TC 並設定適合中文的行高（約 1.5–1.7）。
- **一個記憶點**：每個主要畫面要有一個讓人記得的元素（例如首頁的大插畫問候區、有個性的空狀態），不是清一色的列表加卡片。
- **質感**：`DESIGN.md` 有紙紋、手繪、柔和陰影這類描述時，用背景紋理、非純白底色、柔和的陰影實現，不用 Material 預設的 elevation。
- **動效克制**：依 `DESIGN.md` 的動效強度，用隱式動畫或 `flutter_animate` 做進場與狀態回饋，尊重系統的減少動態設定。
- **做完用看的檢查**：請使用者啟動 APP 網頁預覽後，用 `python3 scripts/pm_shot.py <網頁預覽網址> .pm-console/shots/<畫面>.png --size mobile` 截圖並用 Read 看，對照 `DESIGN.md` 修。

### 檢查

```bash
flutter analyze
flutter test
```

`analyze` 要乾淨。至少為資料轉換與關鍵元件寫 widget test（完整的自動測試在 QA 階段）。

### 完成

1. 請使用者在右欄「APP」按「網頁預覽」或選模擬器啟動，列出建議他走一遍的流程，並附上可登入的測試帳號（「後端 → 帳號」建立的）。
2. 原生功能（推播、相機、定位、地圖）在網頁預覽不準，明講要用模擬器確認哪些。
3. 實作和原型或 Spec 有出入 → 不要自己改文件，在回覆中說明，請使用者決定後走「變更」。
4. `python3 scripts/pm_sync.py commit 需求名 -m "[需求名] APP：一句話摘要"`。
