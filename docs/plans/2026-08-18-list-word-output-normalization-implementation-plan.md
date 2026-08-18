# LIST Word output normalization implementation plan

日期：2026-08-18

狀態：書面設計已由 OP 核准；本計畫待 OP 核准後執行 repo 內離線實作

依據：
`docs/specs/2026-08-18-list-word-output-normalization-design.md`

## 1. 目標與基線

在不改動私人 canonical master 或 calibration manifest 的前提下，把每次產生的
LIST Word 副本正規化為以下固定契約：

- 刪除校準 header cell 內的 QR，不留下 floating wrap 或預留空位；
- 除第一行 `日本精緻假期` 保留 master 原字級外，所有可見文字固定 12 pt；
- ordinary patched cell 只保留 Word 必要的一個 paragraph，不在內容後追加空白行；
- 自動折行及團名既有 manual line break 繼續有效；
- 先完成上述正規化，再 repaginate、SaveAs、reopen、匯出 PDF 並產生逐頁 PNG；
- 任一 QR、字級、paragraph、PDF image 或 page-map 契約不符都 fail closed。

目前 repo 基線：

```text
git pull --ff-only
Already up to date.

focused collection: 135 tests
focused execution: exit code 0
........................................................................ [ 53%]
...............................................................          [100%]
```

focused collection 涵蓋 template contract、Word plan、PowerShell adapter、Word QA、
workflow integration 與 briefing packaging。這次基線沒有啟動 Word COM。

## 2. 授權範圍與停點

核准本計畫只授權：

- 修改本 repo 的 Python、PowerShell、tests、packaging 文件與 STATUS；
- 使用 synthetic／mock 資料執行離線測試；
- PowerShell parser 檢查、`compileall`、package build 與 package content 驗證；
- 建立本機 commits。

核准本計畫不授權：

- 讀取或修改私人 master、calibration manifest 或既有 DRAFT；
- 啟動 Word COM、Yating、ffmpeg 或任何 GUI；
- live NewAmazing／JMA GET；
- 安裝或下載相依套件；
- 寫入 `%LOCALAPPDATA%` installed runtime；
- CONFIRMED、LINE、upload、deploy、publish、push 或 Cowell 存取。

離線實作完成後停下。使用私人 master 執行 4／5／6／7／8／12 天 Word 整合驗證，
以及同步 installed runtime，都需要新的當次明確授權。

## 3. 版本與資料契約

### 保持不變

- calibration manifest 保持 schema 2、`list-calibration/2` 及原始 bytes；
- outer Word job schema 保持目前版本；
- QA index 可保持 schema 2，因逐頁檔案結構沒有改變；
- canonical master hash、structure fingerprint 與 layout evidence 不重寫。

### 升版

- `LIST_WORD_GENERATOR_VERSION`：`list-word/2` -> `list-word/3`；
- `ListPatchPlan.schema_version`：2 -> 3；
- PowerShell patch report schema：2 -> 3；
- persisted Word evidence schema：2 -> 3；
- briefing package：0.2.0 -> 0.2.1 patch release。

### Plan 新增的顯式欄位

- `expected_source_header_qr_candidate_count`：從 calibration schema 2 的
  `normalized_layout.qr_shape_count` 讀取，必須是正整數；
- `output_qr_policy = "removed"`；
- `output_font_points = 12.0`；
- `preserved_title_paragraph = 1`。

所有 layout profile 仍保留 name、line spacing、paragraph spacing 與 cell margins，
但傳入 patch plan 的 `body_font_points` 一律正規化為 12.0。私人 calibration 檔內的
原 profiles 不改寫。

### Report／evidence 新契約

PowerShell patch report schema 3 除既有 page evidence 外，還要記錄：

- `qr_policy = "removed"`；
- source／output header QR candidate count，output 必須等於 0；
- `non_title_font_points = 12.0`；
- title font before／after，兩者必須相同且為單一正數；
- patched cell count；
- `extra_trailing_paragraph_count = 0`。

persisted Word evidence schema 3 保留 `qr_image_count` 欄位以減少 key churn，但新語意
固定為整份 PDF image count，且必須恰好為 0；另保存 header QR、字級與 paragraph
證據。新 runtime 拒絕舊 QR count 1，舊 runtime 也會拒絕新 QR count 0。

## Task 1：以 red tests 建立 schema 3 純 Python 契約

### 檔案

- 修改 `src/travel_briefing/list_calibration.py`
- 修改 `src/travel_briefing/config.py`
- 修改 `src/travel_briefing/template_contract.py`
- 修改 `src/travel_briefing/word_list.py`
- 修改 `tests/unit/travel_briefing/test_list_calibration.py`
- 修改 `tests/unit/travel_briefing/test_briefing_config.py`
- 修改 `tests/unit/travel_briefing/test_template_contract.py`
- 修改 `tests/unit/travel_briefing/test_word_list.py`

### Red tests

1. calibration manifest canonical JSON 及 SHA-256 round trip 完全不變，但可從
   `normalized_layout.qr_shape_count` 取得正整數 source count。
2. 缺少、bool、零或負數的 calibrated QR count fail closed。
3. `validate_list_template` 可分別驗證 source exact positive count 與 output exact zero；
   不傳新參數的 calibration call 保持既有 source-safe 行為。
4. patch plan 固定 schema 3、`list-word/3`、QR policy `removed`、12.0 pt 與 title
   paragraph 1。
5. normal／compact profile 不論原 body font 是 10／9／其他合格值，plan 中都為
   12.0；其他 spacing／margin 欄位逐值不變。
6. report reader 只接受 schema 3 與上述 exact evidence；schema 2、
   `first_page_only`、output QR > 0、font != 12、title before/after 不同或 extra
   paragraph > 0 都拒絕。
7. source inspection count 不等於 plan/calibration count或 output count 不等於 0 時，
   不 publish DOCX。

### 實作

- 在 `ListCalibrationManifest` 提供只讀 derived property；不得增刪 serialized key。
- `BriefingConfig` 保存 validated source QR count並傳到 local Word backend。
- `validate_list_template` 新增 expected QR count seam，讓 source／output 契約分離。
- 擴充 `ListPatchPlan` 與 `ListWordBuildResult`；更新 strict key-set validator。
- 所有 schema mismatch 錯誤訊息明確指出 version 3，不 fallback 到 version 2。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_list_calibration.py `
  tests\unit\travel_briefing\test_briefing_config.py `
  tests\unit\travel_briefing\test_template_contract.py `
  tests\unit\travel_briefing\test_word_list.py -q
git diff --check
```

Commit：`feat(briefing): define normalized LIST output contract`

## Task 2：實作 bounded Word output normalization

### 檔案

- 修改 `scripts/briefing/patch_list_template.ps1`
- 修改 `tests/unit/travel_briefing/test_windows_word.py`
- 修改 `tests/integration/travel_briefing/test_word_list_integration.py`

### Red tests

1. `Invoke-Patch` 只接受 plan schema 3 與 `list-word/3`。
2. source contract 要求 header QR candidate count 等於 plan 值；output contract
   要求等於 0。校準／diagnosis action 的 source QR 規則不變。
3. QR deletion 只處理 square candidate 且 anchor 位於 table 1 row 1 column 1；
   header 外 shape 不動，候選數不明確就 fail closed。
4. inline／floating collection 以倒序刪除或先保存 bounded candidates，避免刪除時
   collection index 漂移。
5. `Set-ListCell` 不含 `` `r`a ``、不寫新的 cell marker；它只改 duplicate range
   中 terminal cell marker 前的內容。
6. filled 與 intentionally empty cell 寫入後都恰有一個 required paragraph；visible
   text 必須與 patch 完全一致，extra paragraph count 為 0。
7. `Set-ListOutputFontContract` 把 main story、table text 及 continuation header 可見字元
   設為 12 pt，再把第一行 exact title 恢復為 mutation 前字級。
8. title 不是 exact `日本精緻假期`、原字級 mixed/undefined、after size 改變、或任一
   non-title visible character 不是 12 pt 都阻擋。
9. `Set-ListLayoutProfile` 只能接受 `body_font_points = 12.0`，不得把 daily rows 降回
   10／9 pt；line spacing 與 margins 仍依 profile 套用。
10. mutation 順序固定為 fill -> remove QR -> normalize font/paragraph -> pagination ->
    save -> reopen -> assert -> report。

### 實作

- 將 `Assert-BasicListContract` 拆出 source/output QR expectation，不降低其他 A4、table、
  merge、anchor 或 day-count 檢查。
- 新增 `Remove-CalibratedHeaderQrCandidates`，沿用現有 candidate 判定與 cell anchor
  規則；刪除 shape object 後不建立 spacer、textbox 或 placeholder。
- `Set-ListCell` 使用 duplicate range 並把 `End` 減去 terminal cell marker；寫入後
  重新取得 cell 並做 exact postcondition。
- 新增 presentation assertion helper，逐一忽略 CR/BEL 等非可見 markers；title 以
  exact paragraph range 排除，continuation headers 另行檢查。
- SaveAs 後 reopen 同一 DOCX，再跑 QR/font/paragraph assertion，最後才寫 schema 3
  report。

### 離線驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_windows_word.py `
  tests\unit\travel_briefing\test_word_list.py -q
powershell -NoProfile -Command `
  '$target="scripts\briefing\patch_list_template.ps1"; `
   $errors=$null; $tokens=$null; `
   [Management.Automation.Language.Parser]::ParseFile( `
     $target,[ref]$tokens,[ref]$errors)>$null; `
   if($errors.Count){$errors;exit 1}'
git diff --check
```

`test_word_list_integration.py` 只更新 opt-in assertions，本 Task 不設定
`RUN_BRIEFING_WORD_INTEGRATION`，因此不會啟動 Word。

Commit：`feat(briefing): normalize generated LIST Word output`

## Task 3：把 PDF 與 workflow evidence 改為 exact zero-image contract

### 檔案

- 修改 `src/travel_briefing/word_qa.py`
- 修改 `src/travel_briefing/workflow.py`
- 修改 `tests/unit/travel_briefing/test_word_qa.py`
- 修改 `tests/integration/travel_briefing/test_workflow.py`
- 修改 `tests/integration/travel_briefing/test_word_list_integration.py`

### Red tests

1. PDF 每一頁 `image_count` 都必須等於 0；第一頁或續頁出現任何 image 都阻擋。
2. 沒有 image 的 PDF 仍須通過 A4、minimum text、required text、continuation identity、
   repeated daily header、day-page map 與 page-count 檢查。
3. `WordRenderEvidence` schema 3 只接受 header QR 0、PDF image 0、non-title 12 pt、
   unchanged title size、extra paragraph 0 及完整 page hashes。
4. render-time acceptance 與 reload-time acceptance 使用同一組 exact predicates；不能
   一邊接受 0、另一邊仍要求 `>= 1`。
5. 舊 schema 2／QR-present fixture 明確失敗，不把 incompatibility 當成 missing evidence。
6. QR-free 輸出仍產生每頁 PNG 與 QA index，且 artifact count 與 page count 相符。

### 實作

- 移除 `word_qa.py` 的 preserved-QR first-page requirement，改為 aggregate 及 per-page
  exact zero image assertion。
- 擴充 `WordRenderEvidence` serialization／deserialization 為 schema 3，保留
  `qr_image_count` key 但只允許 0。
- `render_draft`、artifact validation 與 confirmation preflight 共用 exact contract；
  更新錯誤文字，不再宣稱 first-page QR。
- 不放寬 PDF 文字、幾何、續頁或 PNG 視覺 QA。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_word_qa.py `
  tests\integration\travel_briefing\test_workflow.py `
  tests\unit\travel_briefing\test_word_list.py -q
git diff --check
```

Commit：`fix(briefing): require QR-free LIST QA evidence`

## Task 4：更新 0.2.1 package 與操作文件

### 檔案

- 修改 `src/travel_briefing/__init__.py`
- 修改 `scripts/build_easytravel_briefing_package.ps1`
- 修改 `packaging/easytravel-briefing-materials/app-pyproject.toml`
- 修改 `packaging/easytravel-briefing-materials/INSTALL.txt`
- 修改 plugin manifest 的 version
- 修改 `packaging/easytravel-briefing-materials/shared/SKILL.md`
- 修改 `packaging/easytravel-briefing-materials/shared/references/audio-and-template.md`
- 同步 Codex／Claude 的 byte-identical skill mirrors
- 修改 `tests/unit/test_briefing_packaging.py`
- 視需要修改 `README.md`

### Red tests

1. package metadata 全部一致為 0.2.1。
2. canonical Skill 與兩份 mirror byte-identical。
3.文件明載 output copy 無 QR、不留 QR 空位、唯一 title 例外及其餘 12 pt。
4. package 仍包含更新後的 `travel_briefing` source 與 PowerShell patch script。
5. package 不含 master、calibration、DOCX、PDF、PNG、OP values、credentials 或 output。
6. installer 的 calibration schema 2／`list-calibration/2` 檢查保持不變。

### 驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\test_briefing_packaging.py -q
```

再以 fresh OS temp directory 執行 package build，避免覆蓋既有 dist：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\build_easytravel_briefing_package.ps1 `
  -Version 0.2.1 -DistRoot <fresh-temp-dist>
```

檢查 zip entry allowlist、hash、檔案數、三份 Skill validator 及敏感資料掃描。temp
package 只作驗證，不安裝到 `%LOCALAPPDATA%`。

Commit：`build(briefing): package LIST output normalization 0.2.1`

## Task 5：完整離線回歸、靜態禁語與 handoff

### 完整驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
rg -n "list-word/2|first_page_only|preserved QR|QR candidate.*preserve|qr_image_count < 1" `
  src\travel_briefing scripts\briefing tests packaging
git diff --check
```

rg 結果只允許 calibration schema 2 對 source master 的歷史 policy；任何 output path
殘留舊契約都必須修正。不得以放寬 assertion、skip 或刪除 case 讓 suite 變綠。

### STATUS 與提交

- 記錄每組 focused test 與 full suite 的原始輸出；
- 記錄 PowerShell parse、compileall、package hash／entries 與 diff check；
- 明確寫「Word COM／私人 master integration 未驗證」；
- 記錄 commits、當前 branch、ahead count、無 push；
- working tree 必須乾淨，私人檔及 generated package 不進 Git。

Commit：`docs: record LIST output normalization handoff`

## 4. 後續私人 Word 整合關卡（不含在本計畫核准內）

取得新的明確授權後才可：

1. 確認目前使用者開啟的 Word 狀態，不關閉、不接管其他 Word process；
2. 對既有私人 master／manifest 做 read-only hash 與 schema 檢查；
3. 在 exclusive temp output 建立 4／5／6／7／8／12 天 de-identified drafts；
4. 每份檢查 DOCX header QR 0、非 title 12 pt、title size unchanged、extra paragraph 0；
5. 每份 PDF 所有頁面 image count 0，且 day-page map／page count 一致；
6. 開啟所有 PNG 逐頁人工檢查 full-width header、折行、表格、yellow values 與續頁；
7. 任何 unknown Word result 不 retry，先保存 owned temp evidence 並 fail closed。

只有這個關卡實際通過後，才能宣稱 Word blocker 已修復。installed runtime 同步與新的
正式 DRAFT 各自仍是後續獨立授權。

## 5. 完成定義

離線實作完成需同時滿足：

- master／calibration bytes 未變；
- list-word plan/report 與 persisted evidence 的 schema 3 tests 全綠；
- PowerShell mutation 的 source/output QR、font 與 paragraph assertions 已存在；
- PDF／workflow exact zero-image contract 全綠；
- 0.2.1 package build、allowlist、Skill mirrors 與 sensitive scan 通過；
- 完整 offline suite、compileall、PowerShell parse、`git diff --check` 通過；
- STATUS、local commits 與下一個 private Word approval boundary 完整；
- 沒有 Word COM、GET、JMA、Yating、LINE、upload、deploy、publish、push 或 Cowell 動作。
