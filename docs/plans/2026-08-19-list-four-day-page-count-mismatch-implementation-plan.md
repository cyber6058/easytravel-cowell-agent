# LIST 4-day exported-page authority implementation plan

日期：2026-08-19

狀態：書面規格與本計畫均已由 OP 核准；離線實作已完成並通過完整驗證。
Word 實機 repro 仍是獨立關卡。

依據：
`docs/specs/2026-08-19-list-four-day-page-count-mismatch-design.md`

設計基線 commit：`35fa408ff788abd5112b2d23e41044245d7892d7`

## 1. 目標與已知證據

只修正 LIST 最終頁數權威的資料流：不再把 patch 階段 Word
`ComputeStatistics` 的 `built.computed_page_count` 改名傳成獨立
`expected_page_count`；沒有明示獨立 expectation 時，由 PyMuPDF 實際 inspect 的
PDF page count 控制 PNG set、QA index 與 `WordRenderEvidence.page_count`。

保留以下行為不變：

- patch 與 render report 的 `computed_page_count` 仍必須是正整數，並保留為診斷；
- caller 若真的明示獨立 `expected_page_count`，PDF mismatch 仍 fail closed；
- PDF byte count、A4、必要文字、image policy、續頁識別與 daily header checks；
- `day_page_map` 與唯一 date token 必須在 PDF 指定頁精確匹配；
- PDF、contiguous PNG set、QA index 與 published evidence page count 一致；
- content-driven pagination，不新增 4／5／6／7／8／12 天 production branch；
- Word ownership、timeout、single-run、no-retry、schema、formatting、master 與 calibration。

唯一一次 4 天 Word repro 已觀察到：

```text
expected_page_count=2
ValueError: Word report and PDF LIST page count do not match
1 failed in 35.45s
```

Retained DOCX 的 Word-authored `docProps/app.xml Pages=1`，且沒有 manual page
break、last-rendered break、`pageBreakBefore` 或額外 section。這支持現行 Word
statistic 不是可靠的 exported-artifact authority；因 temporary PDF 已清理，不能把
PDF exact count 1 描述成直接觀察。

## 2. 已核准 test seams

本修正使用兩個既有、純離線 public seams：

1. `render_list_word_for_qa()` 的 synthetic render adapter＋synthetic PDF＋synthetic
   pdftoppm runner，能精確建立「Word statistic 2／有效 PDF 1」而不啟動 Word。
2. `LocalRenderBackend.render_word()` 的既有 monkeypatched composition test，能證明
   build statistic 2 不再被傳成 expectation，而 final evidence 使用 QA PDF count 1。

既有 explicit expectation mismatch test 保留不弱化：`expected_page_count=2` 搭配
one-page PDF 仍必須拒絕 publish。這項 control 區分「沒有獨立 expectation」與「caller
真的提出獨立 expectation」。

不得用 mock Word、private master、calibration、retained DOCX mutation 或新的 COM
instrumentation 擴張 test seam。

## 3. 授權範圍與停止點

核准本計畫只授權修改：

- `tests/unit/travel_briefing/test_word_qa.py`；
- `src/travel_briefing/word_qa.py`；
- `tests/unit/travel_briefing/test_local_backend.py`；
- `src/travel_briefing/workflow.py`；
- 本計畫、原書面規格狀態與 `STATUS.md`。

允許執行 target tests、兩個 focused test files、既有 unchanged controls、PowerShell
parser、完整離線 suite、`compileall`、靜態／non-change checks 與
`git diff --check`，並建立本機 implementation／handoff commits。

下列檔案與行為是明確 unchanged controls：

- `src/travel_briefing/word_list.py`；
- `scripts/briefing/patch_list_template.ps1`；
- `scripts/briefing/render_list_template.ps1`；
- `tests/integration/travel_briefing/test_word_list_integration.py`；
- patch/render report schema、QA index schema、artifact manifest、generator version；
- QR removal、12-point typography、paragraph normalization、pagination profiles；
- private master、calibration manifest、installed runtime 與既有 retained artifacts。

若實作證明必須修改任何 unchanged control，立即停止並回到書面範圍審查；不得順手
改 schema、PowerShell ordering、formatting 或 integration expectations。

本計畫不授權：

- 啟動 Word COM、執行 Word repro、開啟 GUI 或產生 DOCX／正式 PDF／PNG；
- 讀取或修改 private master、calibration、既有 DRAFT 或 installed runtime；
- NewAmazing／JMA GET、Yating、ffmpeg、安裝／下載、LINE、Cowell、deploy、publish、
  push 或任何外部寫入。

完整離線驗證通過後停止。新的 4 天 Word reproduction 仍需另一個當次明確授權，
只能執行一次；不跑其他天數，成功或失敗都不得自動重試。

## Task 1：建立 exported-PDF-authority primary red regression

### 檔案

- 修改 `tests/unit/travel_briefing/test_word_qa.py`

### 實作基線與乾淨工作樹

離線實作開始先記錄：

```powershell
git status --short --branch
git pull --ff-only
$listPageAuthorityBaseline = git rev-parse HEAD
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
```

pull 前 working tree 必須乾淨。pull 後重新確認 HEAD、`STATUS.md`、本計畫與核准規格
一致，再記錄 implementation baseline。若有未知變更或新 commit 改到四個核准
implementation files，保留現況並停止，不覆蓋或自動重訂計畫。

### 擴充既有 synthetic adapter

讓 `SyntheticRenderAdapter` 能獨立指定：

- 實際寫出的 PDF `page_count`；
- render report 的 `reported_page_count`。

`reported_page_count` 預設為 `None`；未指定時沿用 PDF page count，確保所有既有 tests
行為不變。只能用明確 `is None` 判斷，不以 truthiness 處理頁數。

### 新增 primary regression

新增一個 behavior test，名稱清楚表達「沒有獨立 expectation 時使用 inspected PDF
count」。設定：

- adapter 寫出有效 one-page synthetic PDF；
- adapter render report 寫 `computed_page_count=2`；
- 不傳 `expected_page_count`；
- pdftoppm runner 只產生一張 PNG；
- 使用現有 synthetic required text，不提供不相關的 private content。

成功契約必須同時斷言：

1. `result.pdf_inspection.page_count == 1`；
2. `result.computed_page_count == 2`，證明 Word statistic 仍保留為診斷；
3. publish 一個 PDF、一張 `page-001.png` 與一個 QA index；
4. index `page_count == 1` 且只有一個 page entry；
5. pdftoppm 只執行一次；
6. temp job 已清理，且未啟動 Word。

### Red command

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_word_pdf_render_uses_inspected_pdf_count_without_independent_expectation" -q
```

預期 current code 在 publish 前因下列現行錯誤紅燈：

```text
Word report and PDF LIST page count do not match
```

回報實際 fail output，不為符合預估字樣修改 test。若 test 意外全綠，停止並確認它是否
真的建立 report 2／PDF 1，且沒有傳 `expected_page_count`；不得直接改 production。

## Task 2：讓 `word_qa` 以 inspected PDF 控制 artifact page set

### 檔案

- 修改 `src/travel_briefing/word_qa.py`

### 最小 production change

在 `render_list_word_for_qa()` 保留 job、adapter、unknown-result、report schema、PDF
existence 與 byte-count checks。只調整 page-count authority 的順序與判斷：

1. 先讀取並驗證 render report；
2. 驗證 temporary PDF 存在、非空，且 bytes 與 report 相同；
3. 呼叫既有 `inspect_list_pdf()`，完成 A4、text、image、continuation、day map 與
   date-token checks；
4. 若 `expected_page_count is not None`，只比較這個明示 expectation 與
   `inspection.page_count`；不同時以不含內容的 page-count error 阻擋；
5. 不論有無 expectation，通過後的 artifact required count 一律是
   `inspection.page_count`；
6. 移除 `report["computed_page_count"]` 與 artifact required count 的 equality gate；
7. legacy mode 仍只接受 inspected PDF count 1；
8. multi-page mode 將 inspected PDF count 傳給 `render_list_pdf_to_pngs()`，並用同一值
   建立 QA index；
9. `ListWordQaResult.computed_page_count` 繼續回傳 report statistic，不改 dataclass 或
   schema。

不得修改 `inspect_list_pdf()` 的內容／page-map checks、`render_list_pdf_to_pngs()` 的
contiguous page-set checks、publish ordering 或 exclusive-output behavior。

重新執行 Task 1 command，primary regression 必須轉綠。

### Explicit expectation preservation control

執行既有 test：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_word_pdf_render_rejects_page_count_mismatch_before_publish" -q
```

它必須繼續因 explicit expected 2／PDF 1 而阻擋，且 destination PDF、index、PNG 都不得
publish。不得放寬 assertion、改成 warning、skip 或刪除此 test。

再執行 Task 1 primary＋本 control 同一 command，兩者都必須通過。若需要改 report
schema、index schema 或 PowerShell 才能通過，立即停止。

## Task 3：建立 backend red regression 並移除假 expectation

### 檔案

- 修改 `tests/unit/travel_briefing/test_local_backend.py`；
- 修改 `src/travel_briefing/workflow.py`。

### 先修改既有 composition test

在 `test_local_backend_composes_existing_word_build_and_qa` 保留 build result 的
`computed_page_count=2`，把 synthetic QA result 改為：

- `pdf_inspection.page_count=1`；
- 只有一張 synthetic PNG；
- 其餘 QR、font、title、paragraph 與 hash evidence 不變。

更新／新增 assertions：

1. `evidence.page_count == 1`；
2. `len(evidence.page_sha256s) == 1`；
3. `"expected_page_count" not in calls["qa"][1]`；
4. build kwargs、required text、continuation text、day map、pdftoppm path、master 與
   calibration evidence 仍保持既有 assertions。

### Backend red command

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_local_backend.py::test_local_backend_composes_existing_word_build_and_qa" -q
```

預期 current workflow 因仍傳入 `expected_page_count=built.computed_page_count` 而在
新增的 kwargs assertion 紅燈。若紅燈來自不相關的 fixture/hash 破壞，先修正 test setup，
不得先改 production。

### 最小 workflow change

只從 `LocalRenderBackend.render_word()` 呼叫 `render_list_word_for_qa()` 的 kwargs 移除：

```python
expected_page_count=built.computed_page_count,
```

不得改 `build_list_word()`、`WordRenderEvidence`、required／continuation text、day tokens、
adapter、pdftoppm 或 evidence mapping。重新執行 backend command，必須轉綠。

最後執行 Task 1＋Task 2 control＋backend test 的三-test target set；全部必須通過。

## Task 4：focused regression 與 non-change proof

### 兩個核准 test files

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_word_qa.py `
  tests\unit\travel_briefing\test_local_backend.py -q
```

### 相關 unchanged controls

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_word_list.py `
  tests\unit\travel_briefing\test_windows_word.py `
  tests\integration\travel_briefing\test_workflow.py -q
```

不得設定 `RUN_BRIEFING_WORD_INTEGRATION=1`。執行前後只讀 WINWORD process count；不
啟動、終止或接管既有 WINWORD process。

### PowerShell parser unchanged control

雖然兩個 adapters 不得修改，仍只讀解析以保留既有 contract evidence：

```powershell
$parseErrors = @()
foreach ($targetPath in @(
    "scripts\briefing\patch_list_template.ps1",
    "scripts\briefing\render_list_template.ps1"
)) {
    $errors = $null
    $tokens = $null
    [Management.Automation.Language.Parser]::ParseFile(
        $targetPath,
        [ref]$tokens,
        [ref]$errors
    ) | Out-Null
    $parseErrors += @($errors)
}
if ($parseErrors.Count) {
    $parseErrors
    exit 1
}
"PARSER_ERROR_COUNT=0"
```

### 靜態定位

```powershell
rg -n 'expected_page_count|computed_page_count|inspection\.page_count|required_page_count|render_list_pdf_to_pngs|page_count' `
  src\travel_briefing\workflow.py `
  src\travel_briefing\word_qa.py `
  tests\unit\travel_briefing\test_local_backend.py `
  tests\unit\travel_briefing\test_word_qa.py
```

人工確認：

- workflow 不再傳任何 build／Word statistic 作 `expected_page_count`；
- `word_qa` 先 inspect PDF，再處理 explicit expectation 與 PNG/index count；
- Word report statistic 仍驗證為正整數並由 result 保留；
- explicit expectation mismatch control 未弱化；
- day-page-map、date token、PDF content、A4、image 與 publish checks 未變；
- 無 day-count branch、metadata fallback、warning-only content failure 或 private data log。

### Baseline non-change comparison

以 `$listPageAuthorityBaseline` 驗證下列檔案 diff 為零：

```powershell
git diff --exit-code $listPageAuthorityBaseline -- `
  src/travel_briefing/word_list.py `
  scripts/briefing/patch_list_template.ps1 `
  scripts/briefing/render_list_template.ps1 `
  tests/integration/travel_briefing/test_word_list_integration.py
```

production/test changed files 必須精確為本計畫的四個 implementation files。docs 與
`STATUS.md` 可在 handoff task 更新。任何 focused、parser 或 non-change failure 只在四檔
核准範圍內最小修正；需要擴張時停止。

## Task 5：完整離線驗證與 implementation commit

先確認本 process 未 opt in Word integration：

```powershell
if ($env:RUN_BRIEFING_WORD_INTEGRATION -eq "1") {
    throw "WORD_INTEGRATION_OPT_IN_MUST_BE_DISABLED"
}
```

執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
```

最近一次已記錄完整 suite 基線為 `556 passed, 8 skipped`。本計畫預計新增一個 QA
regression 並修改一個既有 backend test，因此正常趨勢可能是 557 passed、8 skipped；
這只供 sanity check，回報一律使用實際輸出，不為符合數字修改、弱化或 skip tests。

完整 suite 前後 WINWORD count 必須與 implementation baseline 相同。suite 若意外啟動
Word、讀 private calibration 或要求 network，立即停止，不能把它當成已授權 integration。

最後逐段檢查：

```powershell
git diff -- `
  src/travel_briefing/workflow.py `
  src/travel_briefing/word_qa.py `
  tests/unit/travel_briefing/test_local_backend.py `
  tests/unit/travel_briefing/test_word_qa.py
git status --short --branch
```

人工確認 diff 只含兩個 red→green slices。完整離線驗證全部通過後，才建立
implementation commit：

```text
fix(briefing): trust exported LIST page count
```

## Task 6：handoff 與本機文件提交

更新本計畫狀態、原書面規格狀態與 `STATUS.md`，記錄：

- implementation baseline、開工 pull、working-tree 與 WINWORD baseline；
- QA primary red 的實際錯誤、轉綠結果與 explicit expectation control；
- backend kwargs red 與最小 workflow green；
- focused files、unchanged controls、PowerShell parser、完整 suite、compileall、static／
  non-change checks 與 `git diff --check` 的實際輸出；
- final PDF authority chain及 Word statistic diagnostic contract；
- production commit、handoff commit、branch 與 ahead count；
- Word、private master、calibration、DRAFT、installed runtime 與 external systems 均未使用
  或修改；
- Word 實機與 DOCX／PDF／PNG 結果仍未驗證。

建立本機 handoff commit：

```text
docs: record LIST page authority handoff
```

最後執行：

```powershell
git status --short --branch
git log -3 --oneline
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
```

working tree 必須乾淨。本計畫不執行 push；push 是另一個明確授權關卡。

## OP 實作核准記錄

OP 已於 2026-08-19 回覆：

```text
同意此實作計畫，開始離線實作
```

該句只授權依本計畫修改四個 implementation files、執行純離線驗證並建立本機
commits；沒有授權 Word 或任何其他外部／integration 關卡。

## 實作結果（2026-08-19）

- implementation baseline 為
  `80dcb4f23723b3f61ee3f29923bfd7324f9351f3`；開工
  `git pull --ff-only` 為 `Already up to date.`，working tree 乾淨，
  `RUN_BRIEFING_WORD_INTEGRATION=0`，WINWORD baseline 為使用者既有的 1。
- QA primary regression 先建立 synthetic render report page count 2、實際 one-page
  PDF，且不傳 independent expectation。Red 原文為 `F [100%]`，停在
  `ValueError: Word report and PDF LIST page count do not match`。
- `word_qa.py` 只移除 Word-statistic equality gate，改為 PDF inspection 後才驗證
  explicit expectation，並以 `inspection.page_count` 控制 legacy／PNG set／QA index。
  Primary 轉為 `. [100%]`；既有 explicit expected 2／PDF 1 blocking control 仍為
  `. [100%]`，兩者合跑為 `.. [100%]`。
- Backend composition test 保留 build statistic 2、改用 QA PDF count 1，並要求 QA
  kwargs 不含 `expected_page_count`。Red 原文為 `F [100%]`，精確 assertion 顯示
  kwargs 仍含 `expected_page_count: 2`；`workflow.py` 移除唯一該 kwarg 後轉為
  `. [100%]`，三個 target tests 合跑為 `... [100%]`。
- 兩個核准 focused files 為 `...................... [100%]`；Word LIST、Windows
  adapter 與 synthetic workflow unchanged controls 最後為
  `............................... [100%]`；PowerShell parser 為
  `PARSER_ERROR_COUNT=0`。
- Baseline non-change command exit 0：`word_list.py`、兩個 Word PowerShell adapters
  與 Gate V integration test 對 baseline diff 為零。production／test changed files
  精確為計畫核准四檔；report／index schema、formatting、pagination、master 與
  calibration 均未改。
- 完整離線 suite 原文為 `557 passed, 8 skipped in 45.89s`；`compileall` exit 0，
  `git diff --check` 通過。驗證後 WINWORD count 仍為 1，Word opt-in 仍為 0。
- implementation commit 為
  `499e2e11d9723eae09318e8affcd28ae25cd3c78`（`fix(briefing): trust exported LIST
  page count`），只含四個核准 implementation files。
- 本輪沒有啟動 Word、讀寫 private master／calibration、產生 DRAFT／DOCX／正式
  PDF／PNG、修改 installed runtime，亦沒有 GET、JMA、Yating、ffmpeg、LINE、
  Cowell、deploy、publish 或 push。
- Word 實機與 DOCX／PDF／PNG QA 仍未驗證。下一步若要驗證，必須取得新的明確
  授權，只執行一次 4 天 post-fix Word repro；不跑其他天數，成功或失敗都不重試。
