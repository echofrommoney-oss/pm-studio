---
description: APP 開發工作流：依原型、DESIGN.md 與技術規格，在 app/ 實作 Flutter APP，接上本機 Supabase
---

# APP 開發工作流（Flutter）

> 依原型（畫面長相與流程）、`DESIGN.md`（視覺）、技術規格（資料與介面）實作 Flutter APP。
> 使用者在工作台右欄「APP」分頁看網頁版預覽與模擬器畫面，用熱重載即時看修改結果。

## 觸發方式

- 使用者說「APP」「Flutter」「做畫面」「手機版」
- 工作台按「開發 → APP」

## 前置

1. `ARCHITECTURE.md` 第 6 節（APP 慣例）、`DESIGN.md`、本需求的原型與技術規格（`manifest.app_screens`）。缺技術規格 → 先走 `pm-spec.md`。
2. 後端：APP 要用到的資料表與函式最好已由 `pm-backend.md` 建好（右欄「後端 → 建置進度」）。還沒建也可以先做畫面，資料用假資料頂著，但要在回覆中說明。
3. `flutter --version` 確認可用。

## 絕對不做

- **不執行 `flutter run`、不啟動模擬器**（工作台已封鎖）：執行由工作台負責，使用者在右欄按啟動、熱重載。
- 不把 Supabase 網址或金鑰寫死在程式裡；一律從 `--dart-define` 讀（見下方「接後端」）。
- 不手寫色碼、字型、圓角；一律用 `AppTokens`（見下方「設計 token」）。
- 不 `flutter build` 正式版、不處理簽章與上架（上線階段才做）。

## 專案骨架（第一次）

`app/` 還不存在時：

```bash
flutter create --org com.<工作室或產品英文> --project-name <產品英文小寫底線> --platforms ios,android,web app
```

`--project-name` 只能用英文小寫與底線（例如 `huru`）。建好之後：

- 套件（依 `ARCHITECTURE.md`；沒指定就用這組）：`flutter pub add supabase_flutter go_router flutter_riverpod`
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

## 設計 token

```bash
python3 scripts/pm_tokens.py dart
```

產生 `app/lib/theme/tokens.dart`（`AppTokens.colorsPrimary`、`AppTokens.radiusSm`…）。`app_theme.dart` 用它組 `ThemeData`（`ColorScheme`、`TextTheme`、元件圓角）。`DESIGN.md` 改了就重跑，不要手改 tokens.dart。

中文字型：`DESIGN.md` 指定的西文字型搭配 `PingFang TC`（iOS）／`Noto Sans TC`（Android）fallback。需要 Google Fonts 就用 `google_fonts` 套件。

## 接後端

工作台啟動 APP 時會帶 `--dart-define-from-file`，內含 `SUPABASE_URL`、`SUPABASE_ANON_KEY`、`APP_ENV`（Android 模擬器的網址已自動換成 `10.0.2.2`）。`app_config.dart`：

```dart
class AppConfig {
  static const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  static const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');
  static bool get hasBackend => supabaseUrl.isNotEmpty && supabaseAnonKey.isNotEmpty;
}
```

`main.dart` 在 `hasBackend` 為 false 時顯示清楚的提示畫面（「本機後端沒開：到工作台啟動 Supabase 後按重新啟動」），不要直接當掉。

資料表名、欄位名、權限行為照技術規格；RLS 會擋的操作要處理錯誤並顯示友善訊息。

## 畫面

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

## 檢查

```bash
flutter analyze
flutter test
```

`analyze` 要乾淨。至少為資料轉換與關鍵元件寫 widget test（完整的自動測試在 QA 階段）。

## 完成

1. 請使用者在右欄「APP」按「網頁預覽」或選模擬器啟動，列出建議他走一遍的流程，並附上可登入的測試帳號（「後端 → 帳號」建立的）。
2. 原生功能（推播、相機、定位、地圖）在網頁預覽不準，明講要用模擬器確認哪些。
3. 實作和原型或 Spec 有出入 → 不要自己改文件，在回覆中說明，請使用者決定後走「變更」。
4. `python3 scripts/pm_sync.py commit 需求名 -m "[需求名] APP：一句話摘要"`。
