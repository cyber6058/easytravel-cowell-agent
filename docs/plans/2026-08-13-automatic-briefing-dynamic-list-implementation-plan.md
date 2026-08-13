# 新魅力說明會全自動流程與動態 LIST 0.2.0 實作計畫

日期：2026-08-13

狀態：書面設計已於 2026-08-13 由使用者通過；本計畫待使用者核准後執行離線階段

依據：
`docs/specs/2026-08-12-automatic-briefing-dynamic-list-design.md`

## 1. 目標與目前基線

把現有 0.1.0 的「單一未校準範本路徑、只接受 5／6／7 天、Word／QA 必須一頁、
只記錄一張 PNG」契約，升級為 0.2.0：

- 三份私有 LIST 樣本只在一次性校準時使用；
- 執行期只讀一份私人 canonical master 與其 calibration manifest；
- 每日行程列支援任何經來源驗證的正整數天數，不按天數選範本；
- 先嘗試校準所得的可讀單頁 profile，無法單頁時回到正常字級並由 Word 自動續頁；
- 續頁重複團體識別與每日表頭，每日列不得跨頁；
- PDF 每頁都驗證並產生 `qa/page-NNN.png`；
- 一次明確的「產生說明會資料」要求可完成同一 DRAFT 的受限來源讀取、master、
  Word、pdftoppm、Yating 與已設定 ffmpeg 流程；
- JMA 網路讀取、校準、安裝、CONFIRMED、LINE、上傳、部署及發布維持獨立關卡。

2026-08-13 實測基線：

```text
365 passed, 3 skipped in 12.92s
```

三個 skip 是需 opt-in 的 Hanhan、Yating 與私有 LIST／Word integration。基線 HEAD
為 `67bc4c4`，工作樹乾淨，本機比 `origin/main` 多 12 個 commits。遠端仍是 public，
所以本計畫所有 commit 都只留本機，不 push。

## 2. 核准範圍與執行關卡

核准本計畫只授權 Task 1 至 Task 8：在本 repo 內修改程式、測試、文件與 packaging，
使用 synthetic／mock 資料，執行離線測試、validator、build，並建立本地 commits。

核准本計畫不授權：

- 讀取三份 `Downloads` 私有 LIST 的內容；
- 啟動 Word COM 或 Yating；
- 寫入 `%LOCALAPPDATA%\EasyTravelBriefing\private`；
- 安裝套件或下載依賴；
- live 新魅力或 JMA request；
- 使用或安裝 ffmpeg；
- 建立 CONFIRMED、傳 LINE、上傳、部署、發布或 push。

後續關卡固定如下：

| 關卡 | 任務 | 另行核准內容 |
| --- | --- | --- |
| L | Task 1–8 | 本計畫核准後可連續完成的 repo 內離線實作 |
| I | Task 9 | 在新 OS temp 目錄安裝 0.2.0；若需下載依賴，連線也只限該安裝 |
| C | Task 10 | 唯讀檢查三份私有 LIST、啟動受限 Word、建立私人 master |
| V | Task 11 | 用 master 實際產生 4／5／6／7／8／12 天 Word／PDF／PNG 並逐頁檢查 |
| E | Task 12 | 使用者提供的真實 URL／PDF、Yating 與可選 MP3 端對端 DRAFT 驗收 |

任一外部或 Word 寫入結果不明時都不 retry；先檢查本工具擁有的暫存輸出，再
fail closed。後一關卡只有在前一關卡有實際通過證據時才能開始。

## 3. 目標架構與資料契約

### 3.1 新模組邊界

- `template_contract.py`：描述一份 LIST 文件的 normalized 結構與版面 profile；
- `list_calibration.py`：純 Python 比較三份 inspection、挑選可重現基底、建立及驗證
  calibration manifest，不呼叫 Word；
- `word_list.py`：由已驗證 master／manifest 建立不限天數的 patch plan；
- `patch_list_template.ps1`：唯一 Word mutation boundary，執行 inspect、calibrate、
  patch，保留精確 PID／nonce ownership；
- `word_qa.py`：逐頁 PDF inspection、PNG rendering 與 page-index 驗證；
- `workflow.py`／`artifact_store.py`：保存多頁 QA artifact 並驗證 CONFIRMED 前置；
- `config.py`／`cli.py`：只接受 canonical master + calibration manifest，另提供一次性
  `calibrate-list` 命令；
- packaged `easytravel-briefing-materials` Skill：把自然語言的一次 DRAFT 授權轉成
 既有 `prepare -> check-script -> render` 決定性流程。

### 3.2 Calibration manifest version 2

私人 `calibration-manifest.json` 固定包含：

- `schema_version = 2`；
- `generator_version = "list-calibration/2"`；
- 三筆只含 SHA-256、day count 與 normalized structure fingerprint 的 sample evidence；
- deterministic base sample SHA-256；
- canonical master SHA-256 及 normalized structure fingerprint；
- A4、方向、margins、header/footer distance、固定表格、欄寬、merged cells、QR／shape
  geometry、style／border／shading digests；
- daily header 與 body-row prototype 契約；
- 由三份樣本證明的 ordered layout profiles，包括 normal profile、可用的 compact
  profiles 及共同最小可讀字級；
- `continuation_group_header = true`、`repeat_daily_header = true`、
  `allow_day_row_split = false`、`qr_policy = "first_page_only"`；
- 建立時間、Word version 及 calibration report SHA-256。

manifest 不保存來源路徑、basename、完整文件文字、團號、電話、行程、QR bytes 或
其他可還原私有內容。source `.doc`、master、manifest、校準 PDF／PNG 全部位於私人
本機目錄且不進 Git。

### 3.3 版面選擇演算法

動態 Word patch 使用固定順序：

1. 把已驗證來源資料套入 canonical master 的 daily body-row prototype；
2. 套用既有安全縮寫規則，不截斷或刪除事實；
3. 先用 normal profile 計算 Word 實際頁數；
4. 若超過一頁，依 calibration manifest 的順序嘗試較緊但仍可讀的 profiles；
5. 第一個能成為一頁的 profile 即採用；
6. 若所有合格 profiles 都不能成為一頁，恢復 normal profile，允許 Word 自動續頁；
7. daily header row 設為 repeat heading，daily body rows 禁止跨頁；
8. section header 用 `PAGE > 1` 的條件欄位顯示團體編號／名稱，因此第一頁不重複、
   續頁一定有識別；
9. 產出 report 記錄 selected profile、page count 與每個 day row 的 start/end page；
10. 任一 day row 的 start/end page 不同，即回報 `LIST_DAY_ROW_TOO_TALL` 並阻擋。

這個演算法不含 4／5／6／7／8 天分支；天數只決定要複製幾列。

## Task 1：建立純離線 calibration domain contract

### 檔案

- 新增 `src/travel_briefing/list_calibration.py`
- 修改 `src/travel_briefing/template_contract.py`
- 新增 `tests/unit/travel_briefing/test_list_calibration.py`
- 修改 `tests/unit/travel_briefing/test_template_contract.py`

### Red tests

1. schema 2 inspection 必須驗證 page geometry、margins、四個固定表格、每日 7 欄、
   merged-cell map、QR／shape、style、font、paragraph、border 及 shading 欄位。
2. normalized fingerprint 必須忽略每日 body-row 數及團務文字，但任何固定欄寬、
   merged cell、QR、margin 或 style 漂移都會改變。
3. 三份 sample 只允許 day count、團務內容及明示 adaptive fields 不同；其他差異
   回傳有欄位路徑的 `CALIBRATION_CONTRACT_CONFLICT`。
4. base selection 先取 day count 中位數；同值時取 SHA-256 字典序最小者。
5. layout profiles 依可讀性由高到低排序，minimum font 不得低於三份樣本共同下限。
6. calibration manifest round trip 必須 canonical、hash-stable，且拒絕未知欄位、
   重複 sample、非三筆 sample、zero hash、路徑及來源全文。
7. master hash、structure fingerprint、generator/schema 任一不符都 fail closed。

### 實作

- 將現有 `_SUPPORTED_DAY_COUNTS` 從 template contract 移出；本 Task 仍保留舊
  `expected_list_table_shapes()` 相容層，真正不限天數在 Task 3 啟用。
- 建立 immutable dataclasses：`ListLayoutProfile`、`ListTemplateInspectionV2`、
  `ListCalibrationSample`、`ListCalibrationManifest`、`CalibrationComparison`。
- 對 Word points 統一四捨五入至 0.01，顏色、border、font 與 style 轉成穩定 canonical
  value 後才計算 fingerprint。
- 比較器只回報結構欄位名稱與 hash，不回吐原始 cell 文字。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_list_calibration.py `
  tests\unit\travel_briefing\test_template_contract.py -q
git diff --check
```

Commit：`feat(briefing): define LIST calibration contract`

## Task 2：加入受限 Word inspection 與 master calibration adapter

### 檔案

- 修改 `scripts/briefing/patch_list_template.ps1`
- 修改 `src/travel_briefing/adapters/windows_word.py`
- 修改 `src/travel_briefing/list_calibration.py`
- 修改 `src/travel_briefing/word_list.py`
- 修改 `tests/unit/travel_briefing/test_windows_word.py`
- 修改 `tests/unit/travel_briefing/test_word_list.py`
- 修改 `tests/unit/travel_briefing/test_list_calibration.py`

### Red tests

1. inspect-v2 job 只接受三個已解析 `.doc`／`.docx` path、OS temp report path、nonce
   與 owned PID path；未知 key／action 拒絕。
2. Python 在 Word 前後逐檔計算 SHA-256；任何來源 hash 改變都回報
   `CALIBRATION_SOURCE_CHANGED`。
3. Word 以 read-only 開啟三份 sample；不呼叫來源文件的 Save／SaveAs。
4. inspection report 包含 Task 1 的全部 layout fields，但 routine error／CLI JSON 不含
   文件文字、路徑或 OP 值。
5. 只有 pure comparison 通過才建立 working copy；失敗時不建立 master。
6. master 由 deterministic base 複製，清除 header 團號／團名、一般資料、航班、每日
   行程與 guide 值，只保留固定 labels、格式、QR、daily header 及一列 prototype。
7. master plain-text scan 只允許 calibrated fixed labels；日期、航班、email、電話、
   團號或原始動態 token 殘留即阻擋。
8. master 與 manifest 都 exclusive create；既有目的檔不覆蓋。
9. timeout／未知結果只記錄 owned temp output 是否存在，不 retry，也不停止其他 Word。

### 實作

- 保留現有 `Get-WordOwnerRecord`、nonce、PID、process start time 與 hidden Word 規則。
- 將 `Get-ListInspection` 升為 schema 2，新增 margins、table/cell geometry、style、font、
  paragraph、border、shading、shape anchor 及 header/footer fingerprints。
- 新增 `inspect-v2` 與 `calibrate` action；舊 `probe` 不開文件且仍限制 20 秒。
- calibration Python orchestration 先 inspect 三份、純比較、再送一次 calibrate job；
  Word temp output 經 Python 驗證後才 exclusive publish 到私人目錄。
- calibration report 對 sample 只使用 `sample-001` 至 `sample-003` 與 hashes，不保存
  Downloads 路徑。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_windows_word.py `
  tests\unit\travel_briefing\test_word_list.py `
  tests\unit\travel_briefing\test_list_calibration.py -q
powershell -NoProfile -Command `
  '$e=$null;$t=$null;[Management.Automation.Language.Parser]::ParseFile("scripts\briefing\patch_list_template.ps1",[ref]$t,[ref]$e)>$null;if($e.Count){$e;exit 1}'
git diff --check
```

本 Task 的測試只 mock Word adapter，不設定 `RUN_BRIEFING_WORD_INTEGRATION`。

Commit：`feat(briefing): add bounded LIST calibration adapter`

## Task 3：移除 5／6／7 天限制並建立 dynamic row plan

### 檔案

- 修改 `src/travel_briefing/template_contract.py`
- 修改 `src/travel_briefing/word_list.py`
- 修改 `scripts/briefing/patch_list_template.ps1`
- 修改 `tests/unit/travel_briefing/test_template_contract.py`
- 修改 `tests/unit/travel_briefing/test_word_list.py`

### Red tests

1. canonical master 固定為 header + 一列 prototype 的 `2x7` daily table。
2. 1、4、5、6、7、8、12 天都產生 `N+1 x 7` output plan；零、負數、缺日、重複、
   不連續或 `len(days) != day_count` 都拒絕。
3. 程式與 PowerShell 不再包含 `5, 6, or 7`、`day_count in {5, 6, 7}` 或 daily rows
   6 至 8 的執行限制。
4. daily prototype 的 font、paragraph、height rule、border、shading、vertical alignment、
   merged state 與 cell margins 在複製後保持一致。
5. 原始 master 不變，output path 仍 exclusive create。
6. 安全縮寫只能移除已核准的括號細節；時間、集合點、交通、安全資訊及來源完整
   文字不被截斷。
7. output normalized fingerprint 與 master 固定契約一致，只有 daily row count 可變。

### 實作

- `expected_list_table_shapes(day_count)` 改為接受任何非 bool 正整數。
- patch plan 升為 schema 2、generator `list-word/2`，綁定 master SHA-256、calibration
  manifest SHA-256、normalized fingerprint 及 ordered layout profiles。
- Word 先把 daily table 正規化成一列 prototype，再複製至 N 列；不得按 N 選來源。
- 保留現有 blocked conflict、CONFIRMED 黃色欄位及最多兩筆航班檢查。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_template_contract.py `
  tests\unit\travel_briefing\test_word_list.py -q
rg -n "5, 6, or 7|day_count in|dailyRows.*6|dailyRows.*8" `
  src\travel_briefing scripts\briefing tests\unit\travel_briefing
git diff --check
```

`rg` 只允許歷史 migration error 測試或明示「不得存在」的 policy assertion 命中，
不能命中 production branch。

Commit：`feat(briefing): generate LIST rows for any trip length`

## Task 4：加入內容驅動單頁嘗試與安全續頁

### 檔案

- 修改 `scripts/briefing/patch_list_template.ps1`
- 修改 `src/travel_briefing/word_list.py`
- 修改 `tests/unit/travel_briefing/test_word_list.py`
- 修改 `tests/unit/travel_briefing/test_windows_word.py`

### Red tests

1. profile 選擇依 manifest 順序，不依 day count；normal 一頁時不嘗試 compact。
2. compact profile 能一頁時採第一個成功 profile；所有 profile 仍多頁時恢復 normal。
3. daily header 設為 repeated heading、每個 body row `AllowBreakAcrossPages = false`。
4. output section header 新增只在 `PAGE > 1` 顯示的團體編號／名稱；不覆寫 master
   原有 header/footer。
5. QR 留在第一頁；不得複製 QR 到續頁。
6. report schema 2 包含 selected profile、computed page count、每一日 start/end page、
   continuation header 與 repeated table header 狀態。
7. 日列 start/end page 不同、頁數為零、day map 缺漏／重複／不連續都 fail closed。
8. 8 天可以是一頁或多頁，7 天也可以多頁；結果只由 Word layout report 決定。
9. 無法單頁時不得保留 compact 字級到多頁版，也不得隱藏、裁切或刪字。

### 實作

- 在 output copy 的 section header 尾端加入 nested Word fields：PAGE 大於 1 時才顯示
  團體編號／名稱；第一頁 field result 為空。
- 對 daily header row 設 `HeadingFormat`，對 body rows停用跨頁。
- 每個 profile 套用後用 Word `ComputeStatistics(wdStatisticPages)` 實測；不以字數或
  day count 推估頁數。
- 以 row range 的 start/end page 建立 `day_page_map`；過高單日回報精確 day number，
  error 不包含行程全文。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_word_list.py `
  tests\unit\travel_briefing\test_windows_word.py -q
git diff --check
```

本 Task 只驗證 job／report 契約與 mock layout；真實 Word 分頁留在 Gate V。

Commit：`feat(briefing): paginate LIST output without shrinking long trips`

## Task 5：把 Word QA 與 artifact store 升級為逐頁模型

### 檔案

- 修改 `src/travel_briefing/word_qa.py`
- 修改 `scripts/briefing/render_list_template.ps1`
- 修改 `src/travel_briefing/artifact_store.py`
- 修改 `src/travel_briefing/workflow.py`
- 修改 `src/travel_briefing/models.py`（只有需要新增 QA evidence 欄位時）
- 修改 `tests/unit/travel_briefing/test_word_qa.py`
- 修改 `tests/unit/travel_briefing/test_artifact_store.py`
- 修改 `tests/integration/travel_briefing/test_workflow.py`

### Red tests

1. 1、2、3 頁 synthetic PDF 每頁都必須是 A4 portrait 且有足夠非空文字。
2. 第一頁必須有 QR image；續頁依 `first_page_only` 不要求也不得誤判缺 QR。
3. 續頁缺團體識別或 calibrated daily header labels 時阻擋。
4. `day_page_map` 指定的日期 token 必須出現在正確頁且只計一次。
5. `pdftoppm` 一次受限轉換全部頁面，exclusive publish 為
   `qa/page-001.png` 至 `qa/page-NNN.png`；缺頁、額外頁、空檔或編號斷裂都阻擋。
6. Word report page count、PDF page count、PNG count 及 QA index page count 必須一致。
7. artifact store 允許安全的相對子路徑，但拒絕 absolute path、`..`、空段、drive、
   UNC 及 resolved escape。
8. 每張 PNG 使用唯一 kind `word_qa_page_NNN`；kind 與檔名必須連續並與
   `word_qa_index` 一致。
9. CONFIRMED 會驗證並複製 PDF、index 及所有 page PNG；缺一頁就拒絕。
10. 0.1 manifest 只有 `word_qa_png` 時回報 `LEGACY_LIST_QA_REQUIRES_RERENDER`，
    不把舊單頁 QA 當成 0.2 驗收。
11. Word render adapter 接受正整數頁數，不再拋 `LIST_PAGE_COUNT_BLOCKED`；report 頁數
    仍必須與實際 PDF 一致。

### 實作

- 新增 aggregate `ListPdfInspection` 與 per-page inspection；不再要求 PDF 恰好一頁。
- 移除 `render_list_template.ps1` 的單頁阻擋，但保留 read-only open、owned PID、
  bounded timeout、exclusive PDF path 及沒有 retry 的既有安全契約。
- 將 `render_list_pdf_to_png()` 改為 `render_list_pdf_to_pngs()`，publish 前先確認 temp
  output 集合精確。
- 建立 `qa/index.json`，保存 page count、relative paths、hashes、required text checks
  與 day-page mapping；不保存完整文件文字。
- `_prepare_artifacts()` 預先記錄 `word_qa` 與 `word_qa_index`，實際 render 後動態加入
  `word_qa_page_NNN`。
- nested artifact 的 parent directory 只在 path 驗證後建立；existing file／directory
  一律不覆蓋。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_word_qa.py `
  tests\unit\travel_briefing\test_artifact_store.py `
  tests\integration\travel_briefing\test_workflow.py `
  tests\unit\travel_briefing\test_windows_word.py -q
git diff --check
```

Commit：`feat(briefing): validate and track every LIST QA page`

## Task 6：加入 calibration CLI、唯一 master config 與 migration failure

### 檔案

- 修改 `src/travel_briefing/config.py`
- 修改 `src/travel_briefing/cli.py`
- 修改 `src/travel_briefing/capabilities.py`
- 修改 `src/travel_briefing/workflow.py`
- 修改 `config/briefing.example.toml`
- 修改 `tests/unit/travel_briefing/test_briefing_config.py`
- 修改 `tests/unit/travel_briefing/test_cli.py`
- 修改 `tests/unit/travel_briefing/test_capabilities.py`
- 修改 `tests/unit/travel_briefing/test_local_backend.py`

### CLI 契約

```powershell
briefing calibrate-list `
  --sample C:\path\sample-1.doc `
  --sample C:\path\sample-2.doc `
  --sample C:\path\sample-3.doc `
  --private-dir C:\path\new-private-calibration-dir `
  --pdftoppm C:\path\pdftoppm.exe `
  --format json
```

執行期 config 固定為：

```toml
[output]
root = "C:\\EasyTravel\\output\\briefings"

[template]
master_path = "C:\\EasyTravel\\private\\LIST-master.docx"
calibration_manifest = "C:\\EasyTravel\\private\\calibration-manifest.json"

[tools]
pdftoppm = "C:\\Program Files\\poppler\\bin\\pdftoppm.exe"
```

### Red tests

1. `calibrate-list` 必須恰好收到三個互異、存在的 DOC／DOCX；private dir 必須不存在。
2. command routine JSON 只回傳 hashes、day counts、狀態及新私人 artifact paths，不
   回傳來源 paths 或文字。
3. config 只接受 `master_path` + `calibration_manifest`；舊 `path` +
   `layout_fingerprint` 回報 `LIST_RECALIBRATION_REQUIRED` 及操作說明。
4. config 載入時不啟動 Word，但驗證 manifest schema、master hash、normalized
   fingerprint metadata 及兩者位於私人／非 output 路徑。
5. `doctor` 只做檔案 hash/schema 與 capability probe；不啟動 Word、不合成、不讀
   sample、不呼叫網路。
6. `render --template` 從 CLI 移除，避免 runtime override canonical master。
7. Local backend 只從 config 取得 master/manifest，patch plan 綁定兩個 hashes。
8. calibration error、unknown Word result 及既有 private dir 都不覆蓋現況。
9. workflow 的 Word evidence 必須記錄 master／calibration hashes、實際 page count 與
   QA index hash；draft ID／artifact hash 漂移時不允許確認。

### 實作

- 新增 `calibrate-list` subcommand，透過 Task 2 orchestration 執行；不自動改 config。
- example config 改為 master/manifest，不放 zero fingerprint 假範例。
- capability JSON 新增 `list_calibration` 狀態：`ok`、`missing`、`changed`、
  `unsupported`；訊息不含私人來源內容。
- workflow generator 升為 `travel-briefing/0.2.0`，Word generator 為 `list-word/2`。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_briefing_config.py `
  tests\unit\travel_briefing\test_cli.py `
  tests\unit\travel_briefing\test_capabilities.py `
  tests\unit\travel_briefing\test_local_backend.py `
  tests\integration\travel_briefing\test_workflow.py -q
.\.venv\Scripts\python.exe -X utf8 -m travel_briefing.cli render --help
git diff --check
```

`render --help` 必須只有 Yating，且不得出現 `--template`。

Commit：`feat(briefing): configure one calibrated LIST master`

## Task 7：更新一次要求的 Agent workflow 與專案制度

### 檔案

- 修改 `AGENTS.md`
- 修改 `packaging/easytravel-briefing-materials/shared/SKILL.md`
- 修改 `packaging/easytravel-briefing-materials/shared/references/cli.md`
- 修改 `packaging/easytravel-briefing-materials/shared/references/audio-and-template.md`
- 修改兩份 Codex／Claude Skill mirrors
- 修改 `tests/unit/test_briefing_packaging.py`
- 修改 `README.md`

### Red tests

1. Skill 明示：同一則訊息包含 URL／PDF 與「產生說明會資料」時，該次 DRAFT 已
   授權 supplied URL read、canonical master、owned Word、pdftoppm、Yating 及 configured
   ffmpeg，不得在正常階段重複詢問。
2. 權限只綁定 supplied source 與當次 draft；新來源／事實版本需新產生要求。
3. 缺值、衝突、parser/template drift、QA failure 才集中中斷。
4. Skill 仍明示 calibration、live JMA、dependency install、CONFIRMED、LINE、upload、
   deploy、publish 與 Cowell 不在一次 DRAFT 授權內。
5. 缺 Yating 不退回 Hanhan／Azure；缺 ffmpeg 不安裝，保留 WAV／TXT／SRT。
6. CONFIRMED 沿用既有較嚴格邊界：仍要求 MP3 與精確 draft ID；缺 ffmpeg 的 DRAFT
   可以審核，但不能 CONFIRM。
7. 正常流程不含 5／6／7 天 template selection；只使用 config 的唯一 master。
8. canonical、Codex、Claude 三份 Skill／references byte-identical。
9. AGENTS 明確指出 0.2.0 校準完成後的一次 DRAFT 授權，且不擴大 Cowell scope。

### 實作

- 把 packaged Skill 的 per-stage approval 文字改為 approved one-request boundary。
- `doctor` 可自動執行，因為它只做 capability／hash probe；任何 `warning` 仍不是新增
  fallback 或安裝權限。
- Agent 在 prepare 成功且 narration input ready 時，自動撰寫八段稿、check，再 render；
  若 review required，集中列出需要 OP 的項目並停止。
- DRAFT 完成只回報 status、draft ID、review 與 artifacts；不自動 CONFIRM／傳送。
- generic `C:\Users\cance\.codex\skills\briefing-material-builder` 不在 repo 離線階段
  修改；此產品以 packaged `easytravel-briefing-materials` Skill 為執行真相。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\test_briefing_packaging.py -q
python -X utf8 C:\Users\cance\.codex\skills\.system\skill-creator\scripts\quick_validate.py `
  packaging\easytravel-briefing-materials\shared
git diff --check
```

另外驗證 packaged plugin 與 Claude mirror，三份都必須回傳 `Skill is valid!`。

Commit：`docs(briefing): make one request authorize one local draft`

## Task 8：升版、完整離線回歸與 0.2.0 allowlist package

### 檔案

- 修改 `src/travel_briefing/__init__.py`
- 修改 `packaging/easytravel-briefing-materials/app-pyproject.toml`
- 修改 `packaging/easytravel-briefing-materials/INSTALL.txt`
- 修改 `packaging/easytravel-briefing-materials/APP-README.md`
- 修改 `packaging/easytravel-briefing-materials/Install-EasyTravelBriefingMaterials.ps1`
- 修改 plugin manifest 與 packaging metadata
- 修改 `scripts/build_easytravel_briefing_package.ps1`
- 修改 `tests/unit/test_briefing_packaging.py`
- 修改 `STATUS.md`

### Red tests

1. runtime、app pyproject、plugin、INSTALL 與 build default 全部是 `0.2.0`。
2. installer 只接受已存在的 master + calibration manifest + pdftoppm；不接受 raw sample
   list，也不自動啟動 calibration、Word 或 Yating。
3. installer 在寫入 app/config 前驗證 manifest schema 與 master SHA-256；舊 0.1 config
   不覆寫，回報需先備份並重新校準。
4. ZIP 包含 calibration Python／PowerShell surfaces 與新版 config，但不含 `.doc`、
   `.docx`、PDF、PNG、私人 calibration manifest、來源 hash、private 目錄、Cowell
   或 Hanhan script；必要的 plugin metadata 不受此條影響。
5. package Skill mirrors 及 references byte-identical。
6. staging secret／PII／artifact scan 與 ZIP allowlist 通過。

### 完整離線驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\build_easytravel_briefing_package.ps1 -Version 0.2.0
```

同時執行：

- Python production files 100 字元行寬檢查；
- PowerShell parser 檢查四份 briefing scripts 與 installer/build scripts；
- 三份 Skill validator 與 plugin validator；
- staged 禁用副檔名、PII、credential pattern scan；
- ZIP entry allowlist 與 ZIP 內容 secret pattern scan；
- 計算 `dist/EasyTravel-Briefing-Materials-0.2.0.zip` SHA-256。

plugin validator 固定使用：

```powershell
python -X utf8 C:\Users\cance\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py `
  packaging\easytravel-briefing-materials\plugins\easytravel-briefing-materials
```

本 Task 只 build ZIP，不安裝、不讀 private master、不啟動 Word／Yating、不連線、
不 push。

Commit：`build(briefing): package dynamic LIST workflow 0.2.0`

## Task 9：0.2.0 乾淨安裝 Gate I

本 Task 不隨計畫核准自動執行。取得 Gate I 明確核准後：

1. 在全新 OS temp root 解壓 0.2.0；
2. 建立 synthetic master 及 schema 2 calibration manifest，不使用三份私有 LIST；
3. 把 `LOCALAPPDATA`／`USERPROFILE` 指向 temp root，略過真實 Codex／Claude 安裝；
4. 安裝 app，執行 `pip check`、`briefing --version`、`doctor`、CLI help；
5. 驗證 installer rerun 拒絕覆蓋；
6. 驗證 config 只有 master/manifest，render 沒有 `--template`；
7. 刪除本 Task 唯一 temp root，記錄檔案／目錄數與刪除結果。

若 pip 需要下載依賴，Gate I 核准畫面要明示該次網路安裝；不允許把現有使用者 app、
config、Skill 或 plugin 當作測試目標。

2026-08-13 Gate I 已完成。使用者明確核准暫存環境下載宣告依賴；因本機沒有既有
`pdftoppm`，另經當次安裝核准以 WinGet 安裝 Poppler 25.07.0-0。0.2.0 在唯一全新
OS temp root 以 synthetic master／schema 2 manifest 安裝成功；`pip check`、版本、
doctor、config、CLI surface、Cowell 隔離及 installer rerun 拒絕均通過。重跑前後
1,520 files／227 directories 與 config／app hashes 不變；驗證後已刪除該 temp root
共 74,354,729 bytes，並清除本次在 repo 產生的 PowerShell／pip cache。此 Gate 未讀
私人 LIST、未啟動 Word COM 或合成 Yating、未執行 live request，也未安裝 ffmpeg。

Commit：`docs(briefing): record 0.2.0 clean install acceptance`

## Task 10：三份私有 LIST 校準 Gate C

本 Task 必須另行取得 Gate C 明確核准。固定輸入：

1. `C:\Users\cance\Downloads\LIST-26NRT0108JX06A.doc`
   - SHA-256 `c230eb24397124cbf0fc6940765be14a9e5a07742f64039f0c01d60f05420b76`
2. `C:\Users\cance\Downloads\LIST-25NRT1107JX07A.doc`
   - SHA-256 `84d7db2fa9f01fea2bfb0563a37f78c0aa3993cb972a913506b67496f056420b`
3. `C:\Users\cance\Downloads\LIST-2026SDJ0722JX5A.doc`
   - SHA-256 `cf62502532344530ec9e0c65161b1fee5624abd6243f32bb6530a1d72cc558bc`

私人目的目錄固定為：

`%LOCALAPPDATA%\EasyTravelBriefing\private\list-calibration-v2`

### 執行與停止條件

1. 先驗證三個 absolute path、size、mtime 及上述 SHA-256；任何不符先停下。
2. 執行最長 20 秒的 owned hidden Word capability probe。
3. 執行一次 calibration command；calibration Word job 最長 180 秒，沒有 retry。
4. 原檔一律 read-only；command 後重算三份 SHA-256，必須完全相同。
5. 三份結構若不能依設計歸一，保留只有 hashes／field paths 的 private review，回報
   `CALIBRATION_CONTRACT_CONFLICT`，不建立 master、不自行選樣本。
6. 通過時產生 `LIST-master.docx`、`calibration-manifest.json`、private source/master
   QA PDF／PNG；全部維持 Git ignored／untracked。
7. 程式驗證 master 不含團號、日期、班號、電話、email 或動態行程文字。
8. 逐頁視覺查看三份來源與 master 的 A4、抬頭、QR、四表格、merged cells、框線、
   字級、欄寬及 prototype row。
9. 記錄 master/manifest hashes、Word version、source hashes before/after 與 QA 結果；
   不把私人內容貼進 STATUS 或 Git。

校準成功後只更新本機 private config；config write 也包含在 Gate C 當次確認內，不能
覆蓋既有 config，若存在就先停止並請使用者決定。

Commit：`docs(briefing): record private LIST calibration result`

## Task 11：4／5／6／7／8／12 天 Word 視覺驗收 Gate V

Gate C 通過且另行取得 Gate V 核准後，使用同一 private master 與全 synthetic、
去識別 drafts：

- 4、5、6、7 天使用一般長度內容；
- 8、12 天刻意使用足以觸發續頁的內容；
- 額外一例單日內容高於整個可用頁面，預期 `LIST_DAY_ROW_TOO_TALL`。

每例驗證：

1. source draft day sequence 與 output rows 精確一致；
2. Word report、PDF page count、PNG count、QA index 與 artifact manifest 一致；
3. 第一頁固定抬頭、QR、一般資料及航班完整；
4. 續頁都有團體識別及 daily header；QR 不重複；
5. 每日列不跨頁，領隊／緊急資訊只在最後；
6. 沒有文字裁切、重疊、不可讀縮字、空白假成功或遺漏日次；
7. 4／5／6／7 與三份來源格式逐頁比對；8／12 驗證 normal profile 多頁可讀性；
8. 每張 PNG 都用 image inspection 實際查看，不以自動測試取代。

產出只放 private QA 目錄，驗收後保留供使用者檢閱，不提交 Git。

Commit：`docs(briefing): record dynamic LIST visual acceptance`

## Task 12：一次要求的真實 DRAFT 驗收 Gate E

Gate V 通過後，使用者另行提供新魅力 URL、PDF 或兩者並下達「產生說明會資料」。
該次要求只對該 DRAFT 授權 spec 列出的受限 URL、master、Word、pdftoppm、Yating 與
已設定 ffmpeg 行為。驗收至少包含：

1. 正常案例從一次要求走到 DRAFT，不再詢問範本或逐步要求 Word/Yating 核准；
2. 一個缺 OP 欄位或來源衝突案例集中回報且不猜值；
3. Word／PDF／逐頁 PNG 與 WAV／TXT／SRT hashes、頁數、bookmark、duration 全部
   實際驗證；
4. 本機未設定 ffmpeg 時不安裝，MP3 明確未完成，DRAFT 可審核但 CONFIRMED 被阻擋；
5. JMA live data 未另行核准時使用既有出發前更新安全文字；
6. 顯示 exact draft ID、review path、完成與未完成 artifacts；
7. 不 CONFIRM、不傳 LINE、不上傳、不部署、不發布、不 push。

若使用者之後要 CONFIRMED，必須先有 MP3、零阻擋、零必要黃色欄位、Word 全頁 QA、
音訊試聽，並對 exact draft ID 另行明確核准。

Commit：`docs(briefing): record 0.2.0 end-to-end draft acceptance`

## 4. 每個離線 implementation commit 的共同驗證

Task 1 至 Task 8 每一個 commit 前至少執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest <本 Task 針對測試> -q
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
git status --short
```

不得為了通過測試而刪 case、skip 新測試或放寬既有斷言。Word／Yating integration
在離線階段保持明示 skip，不能把 skip 當實機通過。

每個 commit 都檢查 staged paths，不得包含 `.doc`、`.docx`、PDF、PNG、WAV、MP3、
SRT、manifest、來源資料、團務值、PII、credential、session 或 browser profile。

## 5. 計畫自檢

- 12 個 Task，Task 1–8 為本計畫核准後的離線範圍，Task 9–12 各有獨立 gate；
- 12 個預定 commit，沒有把 calibration／Word／live／安裝混入離線 commits；
- 0 個 5／6／7 天 runtime selector；
- 0 個單頁硬性成功條件；
- 0 個 Azure、Hanhan fallback、自動 LINE、upload、deploy 或 publish 行為；
- 0 個未決欄位或佔位內容；
- private master、manifest、sample、QA 及產出永遠不進 Git／ZIP；
- public remote 未解除前，所有完成項目只 commit、不 push。

本計畫不改動 Cowell 既有訂單、護照名單、分房、preview 或 apply 契約。
