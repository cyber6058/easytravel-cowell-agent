# LIST embedded Find boundary split implementation plan

日期：2026-08-18

狀態：書面規格已由 OP 核准；本計畫等待 OP 核准，尚未修改 production 或 tests。

依據：
`docs/specs/2026-08-18-list-embedded-find-boundary-design.md`

設計基線 commit：`08647d3`

## 1. 目標與已知證據

只修正 `Set-TokenHighlight` 誤把同一個 terminator-aware boundary 同時用於
full-cell direct path 與 embedded Word Find 的回歸：

- `$visibleBoundary` 只供 exact visible-text comparison 與 full-cell direct
  highlight；
- `$findBoundary = [int]$Range.End - 1` 只供 embedded／repeated-token Word Find；
- 不新增 boundary object／helper，不寫死 T1／T4 座標，也不改 caller。

已知實機證據有明確的前後差分：

1. full-cell 修正前，唯一一次 4 天 Word run 越過五個 embedded cells，停在第一個
   full-cell token：

   ```text
   LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2
   ```

2. full-cell 修正後，唯一一次 4 天 Word run 立即停在第一個 embedded cell：

   ```text
   LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T1_R2_C2
   ```

修正後的 source-contract tests 目前仍為 `... [100%]`，因為 tests 也接受了共用的 visible
boundary。這是待補的 test gap，不代表 Word 回歸已解除。

無 COM model 已證明：paragraph range 的 legacy `End - 1` 與 visible end 差值為 0；
cell range 的差值為 1，因 legacy Find range 保留 terminal `U+000D`。4 天 synthetic plan
共有五個 embedded Find cases 與兩個 full-cell direct cases；T1/R2/C3 有兩次 token，必須
保留 cursor advancement。

目前最佳根因仍是可證偽推論：embedded cell Find 需要先前已通過實機的 `End - 1`
boundary。離線實作完成不代表 Word 已證明跨過 T1/R2/C2。

## 2. 授權範圍與停止點

核准本計畫只授權：

- 修改 `tests/unit/travel_briefing/test_windows_word.py`；
- 修改 `scripts/briefing/patch_list_template.ps1`；
- 唯讀執行 `tests/unit/travel_briefing/test_word_list.py` 的既有 content-shape control；
- 執行 synthetic／source-contract tests、無 COM boundary model、PowerShell parser、
  完整離線 suite、`compileall`、靜態搜尋與 `git diff --check`；
- 更新本計畫、`STATUS.md` 並建立本機 commits。

本計畫不預期修改 `tests/unit/travel_briefing/test_word_list.py`，因既有 test 已精確鎖定
5 embedded＋2 full-cell shapes。若實作時證明必須修改該檔，先停止並回到書面範圍審查，
不得順手擴張。

本計畫不授權：

- 啟動 Word COM、執行 Word repro、產生 DOCX／PDF／PNG 或操作 GUI；
- 讀取或修改私人 master、calibration manifest、既有 DRAFT 或 installed runtime；
- NewAmazing／JMA GET、Yating、ffmpeg、安裝／下載、LINE、Cowell、deploy、publish、push
  或任何外部寫入。

完整離線驗證通過後停止。新的 4 天 Word reproduction 需要另一個當次明確授權，只能
執行一次；不跑其他天數，成功或失敗都不得自動重試。

## Task 1：建立 boundary split red tests

### 檔案

- 修改 `tests/unit/travel_briefing/test_windows_word.py`

### Implementation baseline

實作開始先記錄：

```powershell
$listBoundaryBaseline = git rev-parse HEAD
git status --short --branch
```

working tree 必須乾淨，且 `$listBoundaryBaseline` 必須是已核准計畫所在的 HEAD。若不是，
先重新讀 `STATUS.md` 與 diff，不能覆蓋未知變更。

### 更新 validation-order source contract

保留 `test_highlight_failure_code_is_validated_before_empty_token_return` 的所有 safe-code 與
ordering assertions，只把錯誤的 shared-boundary expectation 拆開：

1. validation 仍在 empty-token return 前；
2. empty-token check 後依序存在：
   `$visibleBoundary = Get-ListVisibleRangeEnd -Range $Range`、
   `$findBoundary = [int]$Range.End - 1`、cursor 初始化與既有 Find settings；
3. `LIST_HIGHLIGHT_CONTEXT_INVALID`、caller-bound `$FailureCode` 與禁止 generic throw 的
   assertions 全部保留。

### 更新 direct／Find source contract

保留 test 名稱
`test_full_cell_highlight_is_direct_and_embedded_tokens_keep_find`，改成明確區分兩條路徑：

1. direct statements 必須使用 `$visibleBoundary`：helper result、visible duplicate、
   `SetRange(Range.Start, visibleBoundary)`、case-sensitive equality、yellow highlight、
   `$matches = 1`；
2. Find statements 必須使用 `$findBoundary`：`while ($cursor -lt $findBoundary)` 與
   `$search.SetRange($cursor, $findBoundary)`；
3. Find text、forward、no-wrap、execute、yellow highlight、match counter 與 cursor
   advancement 的順序不變；
4. direct match 必須發生在任何 Find 前，且 Find 仍受 `$matches -eq 0` 保護；
5. visible duplicate 的既有 `finally`／`FinalReleaseComObject` assertions 不變；
6. function 內不得保留未區分的 `$boundary = ...`，不得出現 T1/R2/C2、T4/R1/C2
   或其他 coordinate special case；
7. zero match 仍 throw caller-bound `$FailureCode`。

### Red command

依下列順序執行四個 tests：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_list.py::test_patch_plan_classifies_highlight_tokens_by_content_shape" `
  "tests\unit\travel_briefing\test_windows_word.py::test_visible_highlight_range_is_terminator_aware" `
  "tests\unit\travel_briefing\test_windows_word.py::test_highlight_failure_code_is_validated_before_empty_token_return" `
  "tests\unit\travel_briefing\test_windows_word.py::test_full_cell_highlight_is_direct_and_embedded_tokens_keep_find" -q
```

預期修正 production 前：前兩個 controls 通過、後兩個 boundary-contract tests 失敗，摘要
形狀預期為 `..FF`。失敗原因必須是 `$visibleBoundary`／`$findBoundary` 尚未分流，而不是
fixture、import 或語法錯誤。

若 tests 意外全綠、controls 失敗或失敗原因不同，立即停止並重查 test seam；不得先改
production，也不得用放寬 assertion、skip、刪 test 或改 fixture 製造預期紅燈。

## Task 2：最小實作兩條 boundary

### 檔案

- 修改 `scripts/briefing/patch_list_template.ps1`

### 保留 helper

`Get-ListVisibleRangeEnd` 完全不改。它仍只從 range-like object 的 `Start`、`End`、`Text`
計算排除 terminal `U+000D`／`U+0007` 的 visible end，並維持
`LIST_HIGHLIGHT_RANGE_INVALID`。

### 修改 `Set-TokenHighlight`

只在 non-empty token 後把目前的 shared `$boundary` 拆成：

```powershell
$visibleBoundary = Get-ListVisibleRangeEnd -Range $Range
$findBoundary = [int]$Range.End - 1
```

然後只做下列機械式替換：

1. visible duplicate 使用
   `$visibleRange.SetRange([int]$Range.Start, $visibleBoundary)`；
2. exact full-cell equality、direct `$WdYellow`、`$matches = 1` 與 visible duplicate 的
   `finally` cleanup 完全保留；
3. embedded loop 使用 `while ($cursor -lt $findBoundary)`；
4. 每次 duplicated search 使用 `$search.SetRange($cursor, $findBoundary)`；
5. 其餘 Find 設定、match counter、cursor advancement 與 zero-match error 不改。

不得：

- 新增另一個 helper、boundary object 或 coordinate／field-name branch；
- 移動 failure-code validation 或 empty-token return；
- 改動 `Set-HeaderParagraph`、`Set-ListCell` 或 caller safe-code wiring；
- 改動 visible duplicate cleanup 或順手處理既有 `$search` COM lifecycle；
- 全域替換其他函式中的 `End - 1`；
- 改內容、schema、QR policy、12 pt、paragraph、pagination 或 layout contract。

## Task 3：Green tests 與無 COM boundary model

### Target green

重新執行 Task 1 的四-test command。預期四個 tests 全綠。若任何 test 失敗，只能在
Task 1／2 的兩個檔案與核准行為內修正。

### 無 COM boundary model

只從 runtime script 擷取 `Get-ListVisibleRangeEnd`；不得載入 job dispatch、`Invoke-Patch`、
Word adapter 或 `JobPath`。以 `PSCustomObject` 建立 paragraph 與 cell synthetic ranges，
另以 `End - 1` 計算 Find boundary，證明：

- paragraph `TOKEN + U+000D`：legacy Find end 與 visible end 相同；
- cell `PREFIX + TOKEN + U+000D + U+0007`：legacy Find end 比 visible end 多 1；
- visible helper 仍保留 space、tab、`U+000B`，只排除 terminal CR／BEL；
- 5 個 embedded shapes 被選為 Find、2 個 exact shapes 被選為 direct；
- T1/R2/C3 仍有 2 個 token occurrences。

probe 只輸出固定、不含內容的摘要：

```text
PARAGRAPH_LEGACY_MINUS_VISIBLE=0
CELL_LEGACY_MINUS_VISIBLE=1
PROPOSED_FIND_COUNT=5
PROPOSED_DIRECT_COUNT=2
REPEATED_TOKEN_MAX_OCCURRENCES=2
```

probe 前後記錄既有 WINWORD process count，僅作 non-use evidence；不得啟動、終止或接管
使用者的 Word process。

## Task 4：Focused regression、parser 與 non-change proof

執行兩個相關 test files：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_word_list.py `
  tests\unit\travel_briefing\test_windows_word.py -q
```

PowerShell parser 只解析、不啟動 Word：

```powershell
$targetPath = "scripts\briefing\patch_list_template.ps1"
$parseErrors = $null
$parseTokens = $null
[Management.Automation.Language.Parser]::ParseFile(
    $targetPath,
    [ref]$parseTokens,
    [ref]$parseErrors
) | Out-Null
if ($parseErrors.Count) {
    $parseErrors
    exit 1
}
"PARSER_ERROR_COUNT=0"
```

執行靜態定位：

```powershell
rg -n 'visibleBoundary|findBoundary|Get-ListVisibleRangeEnd|Set-TokenHighlight|Range.End - 1|SetRange|Find\.(Text|Forward|Wrap|Execute)|HighlightColorIndex|LIST_HIGHLIGHT_(RANGE|CONTEXT|TOKEN)' `
  scripts\briefing\patch_list_template.ps1 `
  tests\unit\travel_briefing\test_windows_word.py
```

判讀要求：

- visible duplicate 只使用 `$visibleBoundary`；
- embedded loop 與 search range 只使用 `$findBoundary`；
- header paragraph 因 legacy 與 visible ends 相同而維持原行為；
- full-cell direct branch 不呼叫 Find；
- 沒有 coordinate／field special case；
- helper、validation、safe-code、Find settings 與 cleanup 均仍存在；
- 沒有 token、text 或 OP value 被串入 exception。

以 `$listBoundaryBaseline` 做 non-change comparison，要求：

- `src/travel_briefing/word_list.py` 與
  `tests/unit/travel_briefing/test_word_list.py` diff 為零；
- `Set-HeaderParagraph`／`Set-ListCell` source segments unchanged；
- 沒有 output-content、schema、font、QR、paragraph、pagination、master、calibration 或
  installed-runtime 變更。

任何 focused failure、model failure 或 parser error 只在核准的兩檔最小 scope 內修正；若
需要擴張到 caller、plan builder 或 private artifact，停止並回報，不自行擴大。

## Task 5：完整離線驗證

執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
```

最近一次已記錄的完整 suite 基線是 `556 passed, 8 skipped`。本計畫不新增 test case，
因此數量預期不變；這只是參考，回報必須使用實際輸出，不能為符合數字而改 test。

最後逐段檢查：

```powershell
git diff -- scripts/briefing/patch_list_template.ps1 `
  tests/unit/travel_briefing/test_windows_word.py
git status --short --branch
```

人工確認 diff 只含兩個 source-contract tests 的 boundary expectations 與
`Set-TokenHighlight` 的兩變數分流。完整驗證通過後才可建立 implementation commit：

```text
fix(briefing): split LIST highlight boundaries
```

## Task 6：handoff 與本機文件提交

更新本計畫狀態與 `STATUS.md`，記錄：

- red run 的實際 pass／fail 形狀與兩個失敗原因；
- target green、無 COM model、focused files、PowerShell parser、完整 suite、compileall、
  static／non-change checks 與 `git diff --check` 的實際輸出；
- `$visibleBoundary` 與 `$findBoundary` 的精確責任；
- production commit、handoff commit、branch 與 ahead count；
- Word、私人 master、calibration、DRAFT、installed runtime 與外部系統均未使用或修改；
- Word 實機與 DOCX／PDF／PNG 結果仍未驗證。

建立本機 handoff commit：

```text
docs: record LIST boundary split handoff
```

最後執行：

```powershell
git status --short --branch
git log -3 --oneline
```

working tree 必須乾淨。本計畫不執行 push；依現行專案紀律，push 是另一個明確授權
關卡。

## 3. Failure handling

- red tests 未按預期失敗：停止，不改 production。
- target／focused／full suite 失敗且可由核准兩檔的 boundary split 解決：做最小修正後重跑
  離線 tests；這不是 Word repro retry。
- 失敗要求改 caller、plan builder、schema、formatting、master 或 calibration：停止並回報
  新 scope。
- 發現工作樹有未知變更：保留並停止，不覆蓋。
- 不論離線結果如何，本計畫都不啟動 Word。

## 4. 完成定義

離線實作只有在下列條件全部成立時才算完成：

- source-contract tests 先以 boundary 尚未分流為由紅燈，再由最小 production change 轉綠；
- `$visibleBoundary` 只服務 exact/direct path；
- `$findBoundary = [int]$Range.End - 1` 只服務 embedded／repeated Find；
- full-cell direct path 不呼叫 Find，embedded Find settings／cursor loop 完整保留；
- content-shape control 維持 5 Find＋2 direct，且 repeated max occurrences 為 2；
- paragraph boundary 差值 0、cell boundary 差值 1 的無 COM model 通過；
- helper、safe-code、caller、schema、content 與 formatting contracts 均不變；
- focused tests、parser、完整 suite、compileall、static／non-change checks 與
  `git diff --check` 全部通過；
- STATUS、計畫與本機 commits 完整，working tree 乾淨；
- 沒有 Word、私人檔案、網路、installed runtime、外部寫入或 push。

上述完成只代表離線 boundary split 通過驗證，不代表私人 master 的 Word blocker 已實機
解除。下一關仍需新的明確授權，只執行一次 4 天 post-fix Word repro；不跑其他天數，
成功或失敗都不重試。

## 5. 計畫核准關卡

OP 核准本計畫後，才可修改 tests 與 production。核准用語：

```text
同意此實作計畫，開始離線實作
```
