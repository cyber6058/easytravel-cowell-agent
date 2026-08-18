# LIST highlight-token safe-code implementation plan

日期：2026-08-18

狀態：書面規格已由 OP 核准；本計畫待 OP 核准後才可執行 repo 內離線實作

依據：
`docs/specs/2026-08-18-list-highlight-token-safe-code-design.md`

基線 commit：`e122984`

## 1. 目標與已知證據

只把 shared `Set-TokenHighlight` 的 generic missing-token failure 細分成
caller 已知位置的安全錯誤碼：

```text
LIST_HIGHLIGHT_TOKEN_MISSING_HEADER_P<paragraph>
LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T<table>_R<row>_C<column>
```

無效或混合的 context 一律 fail closed 為：

```text
LIST_HIGHLIGHT_CONTEXT_INVALID
```

已知實機證據是獲准的唯一一次 4 天 repro 已越過
`LIST_CELL_EXTRA_PARAGRAPH_SET_T1_R2_C3`，但停在 generic
`LIST_HIGHLIGHT_TOKEN_MISSING`。現有兩個 caller 分別是：

- `Set-HeaderParagraph`，已持有 header paragraph number；
- `Set-ListCell`，已持有 table／row／column。

本修正只增加診斷定位；Word Find 範圍、搜尋迴圈、黃色 highlight、token/text、空 token
的正常結果、plan/report schema、generator version、私人 master 與 calibration contract
全部不變。

## 2. 授權範圍與停止點

核准本計畫只授權：

- 修改 `scripts/briefing/patch_list_template.ps1`；
- 修改 `tests/unit/travel_briefing/test_windows_word.py`；
- 執行 repo 內 synthetic／source-contract 離線測試、PowerShell parser、`compileall`、
  靜態搜尋與 `git diff --check`；
- 更新 `STATUS.md` 並建立本機 commits。

本計畫不授權：

- 讀取或修改私人 master、calibration manifest、既有 DRAFT 或 installed runtime；
- 啟動 Word COM、執行 Word repro、產生 DOCX／PDF／PNG，或使用 GUI；
- NewAmazing／JMA GET、Yating、ffmpeg、安裝／下載、LINE、Cowell、deploy、publish、
  push 或任何外部寫入。

完整離線驗證通過後停止。新的 4 天 Word repro 仍需要另一個當次明確授權，且失敗
不得自動重試。

## Task 1：建立 safe-code red tests

### 檔案

- 修改 `tests/unit/travel_briefing/test_windows_word.py`

### 測試

新增 `test_highlight_failures_identify_header_paragraph_or_cell_coordinates`：

1. 從 runtime script 擷取 `Get-ListHighlightMissingCode`、header caller 與 cell caller；
2. assert helper 只有 `HEADER` 與 `CELL` 兩個 exact context，且不使用
   `[ValidateSet]` 讓 unsupported context 逸出成 PowerShell parameter-binding 訊息；
3. assert header 只接受正 paragraph 且 table／row／column 全為零；
4. assert cell 只接受正 table／row／column 且 paragraph 為零；
5. assert zero／negative、混合 metadata 與 unsupported context 的所有其他分支只 throw
   `LIST_HIGHLIGHT_CONTEXT_INVALID`；
6. assert helper 的 exact format strings 產生 `..._HEADER_P<number>` 與
   `..._CELL_T<table>_R<row>_C<column>`；
7. assert header caller 傳入自己的 `$number`，cell caller 傳入自己的 `$tableNumber` 與
   patch row／column，且兩者都把 helper 結果以 `-FailureCode` 傳入
   `Set-TokenHighlight`；
8. 用 Python `re.fullmatch(r"[A-Z][A-Z0-9_]{1,79}", code)` 驗證 representative
   header、cell 與三個 `[int]` 最大值組成的 cell code，並 assert 長度不超過 80。

新增 `test_highlight_failure_code_is_validated_before_empty_token_return`：

1. assert `Set-TokenHighlight` 新增 mandatory `FailureCode`；
2. assert contextual exact regex 與既有 `[A-Z][A-Z0-9_]{1,79}` safe-code contract 都在
   `IsNullOrEmpty($Token)` 前執行；
3. assert 任一無效 failure string 只 throw `LIST_HIGHLIGHT_CONTEXT_INVALID`；
4. assert zero matches 改為 `throw $FailureCode`，runtime 不再含 standalone
   `throw "LIST_HIGHLIGHT_TOKEN_MISSING"`；
5. assert 現有 `$boundary`、`$cursor`、`Find.ClearFormatting()`、`Find.Text`、
   `Find.Forward`、`Find.Wrap`、`Find.Execute()` 與黃色 highlight statements 仍存在且
   順序不變。

先執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_windows_word.py::test_highlight_failures_identify_header_paragraph_or_cell_coordinates" `
  "tests\unit\travel_briefing\test_windows_word.py::test_highlight_failure_code_is_validated_before_empty_token_return" -q
```

預期修正前為 2 個 tests 失敗，因 helper／`FailureCode` 尚不存在且 generic throw 仍存在；
若意外全綠，先停止並重新確認 test seam，不直接改 production code。

## Task 2：最小實作 caller-bound safe-code

### 檔案

- 修改 `scripts/briefing/patch_list_template.ps1`

### 實作

1. 在 `Set-TokenHighlight` 前新增 `Get-ListHighlightMissingCode`，參數為 `Context`、
   `ParagraphNumber`、`TableNumber`、`RowNumber`、`ColumnNumber`；四個數字皆為
   `[int]`，未提供時為零。
2. 不在 `Context` 使用 `[ValidateSet]`。函式本體以 case-sensitive exact comparison
   只接受 `HEADER`／`CELL`，讓 unsupported context 也得到固定 safe code。
3. `HEADER` 僅在 paragraph 大於零且 table／row／column 全為零時回傳
   `LIST_HIGHLIGHT_TOKEN_MISSING_HEADER_P{0}`；其他組合 throw
   `LIST_HIGHLIGHT_CONTEXT_INVALID`。
4. `CELL` 僅在 paragraph 為零且 table／row／column 全大於零時回傳
   `LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T{0}_R{1}_C{2}`；其他組合 throw 同一固定 code。
5. `Set-TokenHighlight` 新增 mandatory `[string]$FailureCode`。在 empty-token early
   return 前，同時驗證：
   - exact contextual pattern，只接受正整數且不接受 leading zero；
   - 既有 `^[A-Z][A-Z0-9_]{1,79}$` safe-code contract。
6. 任一驗證失敗只 throw `LIST_HIGHLIGHT_CONTEXT_INVALID`；不得 throw supplied value。
7. 保留既有 empty-token return、range boundary、Word Find loop、黃色 highlight 與 match
   count；只把 zero-match 的 generic literal 改成 `throw $FailureCode`。
8. `Set-HeaderParagraph` 以 `HEADER` 與 `$number` 建 code；`Set-ListCell` 以 `CELL`、
   `$tableNumber`、`[int]$Patch.row`、`[int]$Patch.column` 建 code。兩者均先建 code，
   再傳入 `Set-TokenHighlight`，不得把 token、text、欄位標籤或任何 OP value 交給 helper。

重新執行 Task 1 command；預期 2 個 tests 全綠。

Commit：`fix(briefing): localize LIST highlight failures`

## Task 3：focused regression、parser 與 non-change proof

執行完整 PowerShell adapter unit file：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_windows_word.py -q
```

PowerShell parser 只解析、不啟動 Word：

```powershell
powershell -NoProfile -Command `
  '$target="scripts\briefing\patch_list_template.ps1"; `
   $errors=$null; $tokens=$null; `
   [Management.Automation.Language.Parser]::ParseFile( `
     $target,[ref]$tokens,[ref]$errors)>$null; `
   if($errors.Count){$errors;exit 1}; `
   "PARSER_ERROR_COUNT=0"'
```

執行靜態定位：

```powershell
rg -n 'Get-ListHighlightMissingCode|Set-TokenHighlight|FailureCode|LIST_HIGHLIGHT_(TOKEN_MISSING|CONTEXT_INVALID)|Find\.(Text|Forward|Wrap|Execute)|HighlightColorIndex' `
  scripts\briefing\patch_list_template.ps1 `
  tests\unit\travel_briefing\test_windows_word.py
```

判讀要求：

- runtime 不得再有 standalone `throw "LIST_HIGHLIGHT_TOKEN_MISSING"`；
- contextual prefix、固定 context-invalid code 與 regression expectations 應存在；
- Find 與 highlight statements 必須仍由 regression 鎖定；
- 不得出現 token/text 被串入 exception 的新路徑。

任何 focused failure 或 parser error 都在同一最小 scope 內修正；不得放寬、skip、刪除
既有 highlight、paragraph、QR、font、pagination 或安全錯誤碼 assertion。

## Task 4：完整離線驗證

執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
```

完整 suite 的先前基線是 `551 passed, 8 skipped`。新增 2 個 tests 後預期為
`553 passed, 8 skipped`；回報以實際輸出為準，不為符合預估數字修改測試。

再檢查：

```powershell
git diff -- scripts/briefing/patch_list_template.ps1 `
  tests/unit/travel_briefing/test_windows_word.py
git status --short --branch
```

人工逐段確認 diff 只含 helper、`FailureCode` validation、兩個 caller wiring 與對應 tests；
不得包含 Word layout、內容、字體、QR、paragraph、schema、calibration 或 runtime 同步變更。

## Task 5：handoff 與本機提交

更新 `STATUS.md`，記錄：

- red tests 的原始失敗數與關鍵訊息；
- 修正後 target tests、focused adapter file、PowerShell parser、full suite、compileall、
  static search 與 `git diff --check` 的實際結果；
- helper 的 exact header／cell safe-code contract 與 context-invalid 行為；
- Word Find／highlight、私人 master、calibration、installed runtime 均未修改；
- Word 實機與 DOCX／PDF／PNG 結果仍未驗證；
- branch、commits、ahead count 與未 push 狀態。

Commit：`docs: record LIST highlight safe-code handoff`

最後要求：

```powershell
git status --short --branch
git log -3 --oneline
```

working tree 必須乾淨。本計畫不執行 push，因 public remote push 是獨立授權。

## 3. 完成定義

離線實作只有在下列條件全部成立時才算完成：

- 兩個 red-capable regression 已先失敗、最小修正後通過；
- header／cell code 只含合法正座標，不含 token、text 或 OP value；
- zero／negative、混合或 unsupported context 一律得到
  `LIST_HIGHLIGHT_CONTEXT_INVALID`；
- `FailureCode` 在 empty token return 前完成 exact 與 80-character safe-code validation；
- zero-match failure 使用 caller-bound code，runtime 不再有 standalone generic throw；
- Word Find 與黃色 highlight statements 未改且 focused tests 全綠；
- full suite、parser、compileall、static search 與 `git diff --check` 通過；
- STATUS 與本機 commits 完整、工作樹乾淨；
- 沒有 Word、私人檔案、網路、installed runtime、外部寫入或 push。

上述完成只代表離線診斷分類已修正，不代表私人 master 的 Word blocker 已實機解除。下一
關仍是取得新的明確授權，只執行一次 4 天 post-fix Word repro；失敗不重試。
