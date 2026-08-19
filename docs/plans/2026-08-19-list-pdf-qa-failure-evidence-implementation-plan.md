# LIST PDF QA failure evidence offline implementation plan

日期：2026-08-19

狀態：書面規格與本計畫均已由 OP 核准；離線實作已完成並通過完整驗證。
Word 實機 repro 仍是未授權的獨立關卡。

依據：
`docs/specs/2026-08-19-list-pdf-qa-failure-evidence-design.md`

設計基線 commit：`b0a68cbc24e7677793c1f0848f9eab1a4f57b530`

Implementation baseline commit：
`3ead9bab2236abcd76f6298dad2d145a2537d154`

## 1. 目標與已知證據

只修正 LIST PDF QA 的失敗可診斷性：

1. `inspect_list_pdf()` 必須指出每個缺少的 `required_text` token；
2. 有效 Word-exported PDF 在 deterministic PDF inspection 失敗時，必須保存到
   `failed-qa/LIST-qa.failed.pdf`；
3. 同目錄必須建立 hash-bound schema-1 `failure.json`；
4. 正常 PDF、PNG 與 QA index 在失敗路徑保持不存在；
5. 成功路徑、unknown Word result、no-retry 與所有既有 artifact schema 保持不變。

唯一一次 4 天 Word repro 已觀察到：

```text
ValueError: LIST QA PDF is missing required text
1 failed in 42.37s
```

該次沒有重跑，只保留含正確 4 天服務費正文的 `LIST.docx`；temporary PDF 已由
`TemporaryDirectory` 清除，因此不能推測實機 PDF 實際缺少哪個 token。

已執行的離線 synthetic feedback loop 連續三次穩定輸出：

```text
ATTEMPT_1=LIST QA PDF is missing required text
ATTEMPT_2=LIST QA PDF is missing required text
ATTEMPT_3=LIST QA PDF is missing required text
AssertionError: RED: missing token identities are not exposed
```

未來 primary unit test 會取代這個 throwaway harness；不得把 synthetic 結果描述成
真實 Word PDF 根因。

## 2. 核准檔案、unchanged controls 與停止點

核准本計畫未來只修改：

- `tests/unit/travel_briefing/test_word_qa.py`；
- `src/travel_briefing/word_qa.py`；
- 本計畫與 `STATUS.md`。

下列檔案與契約是明確 unchanged controls：

- `src/travel_briefing/workflow.py`；
- `src/travel_briefing/errors.py`；
- `src/travel_briefing/word_list.py`；
- `scripts/briefing/patch_list_template.ps1`；
- `scripts/briefing/render_list_template.ps1`；
- `tests/unit/travel_briefing/test_local_backend.py`；
- `tests/integration/travel_briefing/test_word_list_integration.py`；
- LIST generator `list-word/4` 與 plan／patch-report schema 4；
- Word render-job／render-report schema 1；
- calibration schema 2／`list-calibration/2`；
- persisted `WordRenderEvidence` schema 3；
- successful QA index schema 2；
- success PDF／PNG publication、page authority、day map 與 hashes；
- QR removal、full-width identity、12 pt non-title、no-extra-paragraph 與 arbitrary-day
  pagination contracts；
- private master、calibration、installed runtime 與 retained artifacts。

若實作證明必須修改任何 unchanged control、public error class、successful artifact
schema 或 workflow signature，立即停止並回到書面設計 review；不得順手擴張。

本計畫不授權：

- 啟動 Word COM、執行 Word repro、開 GUI 或產生實機 DOCX／PDF／PNG；
- 讀取或修改 private master、calibration、installed runtime 或既有 DRAFT；
- NewAmazing／JMA GET、Yating、ffmpeg、dependency download、LINE、Cowell、deploy、
  publish、push 或任何外部寫入。

完整離線驗證通過後停止。新的 4 天 Word repro 仍需另一個當次精確授權；只能跑
一次、不跑其他天數，成功或失敗都不得自動重試。

## 3. Implementation commit map

已建立兩個 implementation commits；第三個 handoff commit 由本文件與 STATUS
更新完成：

1. `a632c9607e43911d17080cb5e0d38a073ac4fe86`
   `feat(briefing): report missing LIST PDF tokens`
   - missing-token primary test；
   - private typed `ValueError` 與 ordered-unique token calculation。
2. `09897a8b4bbcb65e80296682b9649e278fcbc669`
   `feat(briefing): preserve failed LIST PDF QA evidence`
   - failure publication、generic failure、collision、success 與 rollback tests；
   - preflight、schema-1 report、exclusive publication與 outer error envelope。
3. `docs: record LIST PDF failure evidence handoff`
   - 本計畫狀態與 `STATUS.md` 的實際驗證結果。

不得建立 red-only commit；每個 production commit 都必須包含使自己的 primary red
轉綠的最小 test 與 production change。

## Task 1：implementation preflight 與 missing-token primary red

### 乾淨基線

離線實作開始先執行：

```powershell
git status --short --branch
git pull --ff-only
$listPdfFailureBaseline = git rev-parse HEAD
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
Get-ChildItem Env:RUN_BRIEFING_WORD_INTEGRATION -ErrorAction SilentlyContinue
```

working tree 必須乾淨，Word opt-in 必須未設定。記錄 implementation baseline、
WINWORD baseline 與 `git status` 原文。若 pull 後 HEAD、規格、計畫或兩個核准
implementation files 出現未知變更，保留現況並停止，不覆蓋使用者工作。

### 先寫 primary test

在 `test_word_qa.py` 新增：

```text
test_pdf_inspection_reports_missing_required_text_once_in_input_order
```

使用現有 `write_pdf()` 建立有效 A4 synthetic PDF，PDF 只包含 product code 與
`JX820`。呼叫 `inspect_list_pdf()` 時傳入：

```text
SYN-LIST-260901
JX820
JX821
SERVICE-FEE-TOKEN
JX821
```

test 以 `pytest.raises(ValueError)` 捕捉結果，並要求：

- `error.value.missing_required_text == ("JX821", "SERVICE-FEE-TOKEN")`；
- 重複缺少 token 只出現一次；
- 順序依 caller 第一次出現順序；
- message 仍是 `LIST QA PDF is missing required text`；
- 不輸出 matched token 或完整 extracted PDF text。

### Red command

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_reports_missing_required_text_once_in_input_order" -q
```

預期 current code 因 generic `ValueError` 沒有 `missing_required_text` 而紅。記錄實際
第一個 failure；若意外全綠，先確認 test 確實檢查兩個 ordered-unique 缺少值，不直接
修改 production。

## Task 2：實作 typed missing-token inspection error

### 檔案

- 修改 `src/travel_briefing/word_qa.py`。

### 最小 production change

在 `word_qa.py` 內新增 private、非 public API 的
`_ListPdfRequiredTextError(ValueError)`：

- constructor 只接受 non-empty missing-token tuple；
- 保存 immutable `missing_required_text`；
- message 固定為 `LIST QA PDF is missing required text`；
- 不新增 `errors.py` public class 或 exit code。

在 `inspect_list_pdf()` 已取得 `whole_text` 後，以 caller first-occurrence order 建立
ordered-unique missing tuple。可使用 deterministic insertion-order dedupe，但不得排序、
normalize、strip 或把 token 改成摘要；matched token 不進入 tuple。

只有 missing tuple 非空時才 raise private typed error。其他 page geometry、empty text、
image、continuation 與 day-map branches 完全不變。

重新執行 Task 1 command，primary test 必須轉綠，再執行既有 inspection controls：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_validates_every_page_and_day_mapping" `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_blocks_missing_continuation_identity_or_wrong_day_page" `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_fails_closed_on_page_text_or_image_drift" -q
```

全部綠後建立 commit 1。不得為了測試通過改舊 assertions 或將 generic failures 改成
warning。

## Task 3：建立 failed-evidence publication primary red

### 檔案

- 修改 `tests/unit/travel_briefing/test_word_qa.py`。

### Test-only setup

沿用 `SyntheticRenderAdapter` 產生已通過 render-report bytes checks 的有效 A4 PDF。
傳入一個 PDF 不含的 `SERVICE-FEE-TOKEN` 作 required text；不使用 private content、
Word、pdftoppm 或實機 retained artifact。

新增：

```text
test_word_pdf_render_preserves_failed_pdf_and_token_report_before_raising
```

呼叫 `render_list_word_for_qa()` 後必須 raise `WordGenerationError`，並要求：

1. adapter 只記錄一個 job；
2. `failed-qa/LIST-qa.failed.pdf` 存在且 non-empty；
3. `failed-qa/failure.json` 存在；
4. JSON top-level 與 nested PDF keys exact符合 schema 1；
5. `missing_required_text == ["SERVICE-FEE-TOKEN"]`；
6. JSON bytes／SHA-256 等於 retained failed PDF；
7. outer code 是 `WORD_GENERATION_FAILED`；
8. outer details exact包含 stage、safe inner code、missing list與兩個 relative paths；
9. requested normal PDF、PNG directory與index均不存在；
10. adapter 收到的 temp job path 已由既有 lifecycle 清理。

### Red command

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_word_pdf_render_preserves_failed_pdf_and_token_report_before_raising" -q
```

預期 current code 直接拋 typed `ValueError`，temporary PDF 被清除且沒有 `failed-qa`，
因此紅燈。若紅燈來自 synthetic PDF 無效或 report mismatch，先修正 test setup，不得先
改 production。

## Task 4：實作 preflight、failure report 與 exclusive publication

### 檔案

- 修改 `src/travel_briefing/word_qa.py`。

### Preflight

由 requested `output_pdf` 計算 exact paths：

```text
failed directory = output_pdf.parent / "failed-qa"
failed PDF       = failed directory / "LIST-qa.failed.pdf"
failure report   = failed directory / "failure.json"
```

在 `adapter.run()` 前檢查整個 failed directory 不存在。若存在，以 deterministic
`ValueError` fail closed；不得啟動 adapter、刪除、清空、merge 或覆寫該目錄。

### Private publication helpers

新增小型 private helpers，職責分離：

1. path helper：只從 requested PDF 產生固定 destinations；
2. exclusive JSON writer：用 create-new semantics 寫 UTF-8 deterministic JSON與 newline；
3. failed-evidence publisher：建立 fresh directory、呼叫既有 `_copy_exclusive()`、
   驗證 copied PDF bytes／SHA-256、最後寫 `failure.json` completion marker；
4. rollback：publication 任一步失敗時，只反向移除該 helper 已建立的 report、PDF與
   fresh empty directory，再 re-raise original error。

不得使用 recursive delete。由於 preflight 要求 directory 原先不存在，rollback 不得
碰觸 prior evidence 或任何父目錄內容。

JSON 必須使用 schema-1 exact keys：

```text
schema_version
status
stage
error_code
message
missing_required_text
pdf.relative_path
pdf.bytes
pdf.sha256
```

`relative_path` 固定為 `LIST-qa.failed.pdf`；hash 為 lowercase SHA-256。不得寫 absolute
path、完整 PDF text、private path、environment 或 COM dump。

### Inspection catch boundary

只包住現有 `inspect_list_pdf()` 呼叫：

- private typed missing error → inner code
  `LIST_PDF_REQUIRED_TEXT_MISSING` 與 ordered missing list；
- 其他 inspection `ValueError` → `LIST_PDF_INSPECTION_FAILED` 與 empty list。

已通過 render report、PDF existence與byte-count checks後，才允許 publication。
Unknown Word result、invalid report、missing／empty PDF、byte mismatch、pdftoppm failure與
success-publication failure均不得進入此 catch。

publisher 成功後，raise existing `WordGenerationError`，message保持安全，details exact為：

```text
stage = "pdf-inspection"
error_code = safe inner code
missing_required_text = ordered list
failed_pdf = "failed-qa/LIST-qa.failed.pdf"
failure_report = "failed-qa/failure.json"
```

保留原 inspection error 為 chained cause。不得修改 `errors.py`、新增 retry或把 failed
artifact包成 `ListWordQaResult`。

重新執行 Task 3 command，primary 必須轉綠。

## Task 5：generic failure、collision、success 與 rollback controls

### 檔案

- 修改 `tests/unit/travel_briefing/test_word_qa.py`。

### Generic inspection failure

新增 test-only adapter option或最小 test adapter，產生 render report 合法但非 A4 的
synthetic PDF。新增：

```text
test_word_pdf_render_preserves_generic_inspection_failure_without_token_dump
```

要求 failed PDF/report 存在、inner code為 `LIST_PDF_INSPECTION_FAILED`、missing list為
empty，正常 artifacts不存在。不得把非 A4 誤報為 missing token。

### Collision preflight

新增：

```text
test_word_pdf_render_blocks_existing_failed_qa_directory_before_adapter
```

預先建立 `failed-qa` 並放一個 sentinel。呼叫後必須在 adapter job list仍為empty時
fail；sentinel bytes不變，normal outputs不存在。

### Success non-change

在既有 parametrized success test 加一項 assertion：成功發布 PDF／PNG set／index後，
`failed-qa` 不存在。其餘 page count、hash、day map、report statistic與job cleanup
assertions不變。

### Publication rollback

新增：

```text
test_failed_pdf_evidence_rolls_back_fresh_paths_when_report_write_fails
```

用 monkeypatch 讓 private exclusive JSON writer 在 failed PDF copy與hash驗證後 raise
synthetic `OSError`。要求 re-raise後 failed PDF、failure report與fresh failed directory均
不存在，normal outputs不存在，父目錄 sentinel不變。不得透過放寬 production exception
或 recursive cleanup 讓 test通過。

### Focused command

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_reports_missing_required_text_once_in_input_order" `
  "tests\unit\travel_briefing\test_word_qa.py::test_word_pdf_render_preserves_failed_pdf_and_token_report_before_raising" `
  "tests\unit\travel_briefing\test_word_qa.py::test_word_pdf_render_preserves_generic_inspection_failure_without_token_dump" `
  "tests\unit\travel_briefing\test_word_qa.py::test_word_pdf_render_blocks_existing_failed_qa_directory_before_adapter" `
  "tests\unit\travel_briefing\test_word_qa.py::test_failed_pdf_evidence_rolls_back_fresh_paths_when_report_write_fails" -q
```

五個 targets 全綠後，執行完整 `test_word_qa.py`：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_word_qa.py -q
```

全部通過才建立 commit 2。

## Task 6：focused unchanged controls 與 scope proof

### Direct unchanged controls

執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_local_backend.py `
  tests\unit\travel_briefing\test_word_list.py `
  tests\unit\travel_briefing\test_windows_word.py -q
```

這些 tests 必須維持 required text composition、service-fee formatter、Word patch adapter、
QR、font、paragraph與arbitrary-day contracts。不得因本修正修改它們或調整 assertions。

### Static non-change

以 implementation baseline 執行：

```powershell
git diff --name-only $listPdfFailureBaseline
git diff --exit-code $listPdfFailureBaseline -- `
  src/travel_briefing/workflow.py `
  src/travel_briefing/errors.py `
  src/travel_briefing/word_list.py `
  scripts/briefing/patch_list_template.ps1 `
  scripts/briefing/render_list_template.ps1 `
  tests/unit/travel_briefing/test_local_backend.py `
  tests/integration/travel_briefing/test_word_list_integration.py
git diff --check
```

changed-file list只允許兩個核准 implementation files與計畫／STATUS handoff。任一
unchanged control有diff即停止；不自動restore使用者變更。

確認 production 沒有 common-duration branch、retry或外部 integration addition：

```powershell
rg -n "failed-qa|LIST_PDF_REQUIRED_TEXT_MISSING|LIST_PDF_INSPECTION_FAILED" `
  src/travel_briefing/word_qa.py tests/unit/travel_briefing/test_word_qa.py
rg -n "RUN_BRIEFING_WORD_INTEGRATION|DispatchEx|win32com|NewAmazing|JMA|LINE|Cowell" `
  src/travel_briefing/word_qa.py
```

第一個 scan 必須只命中預期的新 failure contract；第二個 scan 必須沒有新增命中。

## Task 7：完整離線驗證與本機 handoff

### 環境與完整 suite

先確保 Word opt-in 未設定：

```powershell
Remove-Item Env:RUN_BRIEFING_WORD_INTEGRATION -ErrorAction SilentlyContinue
$winwordBefore = (Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
.\.venv\Scripts\python.exe -X utf8 -m pytest
$suiteExit = $LASTEXITCODE
$winwordAfter = (Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
```

要求 suite exit 0、integration tests維持 opt-in skip、`$winwordAfter -eq $winwordBefore`。
若 WINWORD count改變，停止並回報，不以 terminate process掩蓋原因。

再執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
git status --short --branch
```

記錄 pytest pass／skip count、duration、compile exit、WINWORD before／after、focused
outputs與changed-file list。所有數字由命令輸出取得，不心算。

### Handoff

完整驗證通過後：

1. 更新本計畫狀態為離線實作完成並記錄兩個 implementation commits；
2. 更新 `STATUS.md` 的一句話現況／做了什麼／下一步／阻塞點；
3. 建立 commit 3；
4. 確認 working tree乾淨；
5. 停止，不 push、不跑 Word。

下一步只可建議一個新的精確 4 天 one-shot Word repro authorization。未獲新授權前，
不得因離線 tests全綠而執行 Word、讀 private master或產生新的 QA artifacts。

## 4. Actual offline verification

### Primary red-to-green evidence

- Missing-token primary red：
  `AttributeError: 'ValueError' object has no attribute 'missing_required_text'`。
- Typed missing-token green：primary `1 passed`；existing inspection controls
  `5 passed`。
- Failed-evidence publication primary red：
  `_ListPdfRequiredTextError: LIST QA PDF is missing required text`，證明 current
  code 仍直接拋 inspection error且沒有 retained evidence。
- Failed-evidence primary green：`1 passed`。
- Token／generic／collision／rollback focused controls：`5 passed`。
- 完整 `test_word_qa.py`：`24 passed in 1.58s`。

### Unchanged controls and complete suite

- `test_local_backend.py`、`test_word_list.py`、`test_windows_word.py`：
  `114 passed in 1.72s`。
- 完整離線 suite：`589 passed, 8 skipped in 19.81s`。
- WINWORD before／after：`0 / 0`；Word opt-in未設定。
- `compileall` exit 0；`git diff --check` exit 0。
- Implementation baseline至兩個production commits的changed files只有：
  `src/travel_briefing/word_qa.py`與
  `tests/unit/travel_briefing/test_word_qa.py`。
- 所有列出的unchanged controls diff為零；external integration scan clean。

## 5. Completion checklist

- [x] primary missing-token test先紅後綠；
- [x] missing tokens ordered、unique且不包含 matched/full PDF text；
- [x] primary failed-evidence publication test先紅後綠；
- [x] schema-1 JSON exact且bytes／SHA-256綁定failed PDF；
- [x] token／generic inspection failures使用正確 safe inner codes；
- [x] outer error維持 `WORD_GENERATION_FAILED` 與relative paths；
- [x] normal outputs在failure path保持不存在；
- [x] existing `failed-qa` 在adapter前fail closed且sentinel不變；
- [x] rollback只清理同次fresh paths；
- [x] success path不建立failed directory且既有schema/hash不變；
- [x] `test_word_qa.py`與direct unchanged controls全綠；
- [x] complete offline suite、compile、diff與scope gates全綠；
- [x] WINWORD before／after一致且Word opt-in未設定；
- [x] private master、calibration、workflow、errors、PowerShell與integration test未修改；
- [x] 本機 commits與STATUS handoff完成；
- [x] 未 push、未跑Word、未使用任何external integration。

## 6. Next gate

本計畫的離線實作已完成。離線綠燈不授權 Word 或 push，也不能判定上一個已刪除的
實機 PDF 缺少哪個 token。

若 OP 要進行新的實機驗證，精確下一個授權句為：

```text
同意只執行一次 4 天 post-fix Word repro；不跑其他天數；若成功，完成同次 DOCX／PDF／PNG QA；成功或失敗都不重試。
```
