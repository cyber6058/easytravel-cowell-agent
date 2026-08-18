# LIST full-cell highlight implementation plan

日期：2026-08-18

狀態：書面規格已由 OP 核准；本計畫待 OP 核准後才可執行 repo 內離線實作

依據：
`docs/specs/2026-08-18-list-full-cell-highlight-design.md`

基線 commit：`8555298`

## 1. 目標與已知證據

只修正 `Set-TokenHighlight` 的 full-cell token 路徑：先取得排除 Word 尾端
`U+000D`／`U+0007` 的 visible range；若 visible text 與 token case-sensitive 完全相同，
直接把該 range 套用 `$WdYellow`，不呼叫 Word Find。embedded token 仍走既有 Find／cursor
迴圈。

已知證據是唯一一次獲准的 4 天 Word repro 停在：

```text
LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2
```

4 天 synthetic plan 共有 7 個 highlighted ordinary cells：前 5 個是 embedded token，
T4/R1/C2、T4/R1/C3 是唯二 visible text 完全等於 token 的 full-cell cases；
T1/R2/C3 同一 token 出現兩次，必須繼續證明 Find loop 可處理 repeated matches。Word run
已越過前 5 格才停在第一個 full-cell case，而且 T4/R1/C2 寫值後的一段落與 exact text
assertions 均已通過。

目前最佳根因仍是推論：cell range 的固定 `End - 1` 只排除 `U+0007`，仍把 terminal
`U+000D` 留在 full-cell Find range。離線修正完成不代表 Word 實機已證明跨過 T4/R1/C2。

## 2. 授權範圍與停止點

核准本計畫只授權：

- 修改 `scripts/briefing/patch_list_template.ps1`；
- 修改 `tests/unit/travel_briefing/test_windows_word.py`；
- 修改 `tests/unit/travel_briefing/test_word_list.py`；
- 執行 synthetic／source-contract 測試、無 COM PowerShell helper probe、PowerShell parser、
  完整離線 suite、`compileall`、靜態搜尋與 `git diff --check`；
- 更新本計畫、`STATUS.md` 並建立本機 commits。

本計畫不授權：

- 啟動 Word COM、執行 Word repro、產生 DOCX／PDF／PNG 或操作 GUI；
- 讀取或修改私人 master、calibration manifest、既有 DRAFT 或 installed runtime；
- NewAmazing／JMA GET、Yating、ffmpeg、安裝／下載、LINE、Cowell、deploy、publish、push
  或任何外部寫入。

完整離線驗證通過後停止。新的 4 天 Word repro 仍需要另一個當次明確授權，只能執行
一次，無論成功或失敗都不得自動重試。

## Task 1：建立 content-shape 與 adapter red tests

### 檔案

- 修改 `tests/unit/travel_briefing/test_word_list.py`
- 修改 `tests/unit/travel_briefing/test_windows_word.py`

### Plan trigger-shape regression

新增 `test_patch_plan_classifies_highlight_tokens_by_content_shape`：

1. 使用既有 `draft(4)` 與 `build_list_patch_plan`，不讀私人檔案；
2. 依 patch execution order 收集所有 `highlight_text` 非空的 ordinary cells；
3. assert 共 7 格，前 5 格的 `text` 只包含 token、但不等於 token；
4. assert 最後兩格精確為 T4/R1/C2、T4/R1/C3，且兩者 `text == highlight_text ==
   WAITING_FOR_OP`；
5. assert T1/R2/C3 的 text 內同一 token 出現 2 次；
6. assert 兩個 full-cell text/token 不含 CR、LF、BEL，並保留 exact code-point assertion。

這個 test 鎖定觸發條件，修正前預期已通過；它不是 production red signal。

### PowerShell adapter regressions

新增 `test_visible_highlight_range_is_terminator_aware`：

1. assert `Get-ListVisibleRangeEnd` 位於 `Set-TokenHighlight` 前；
2. assert helper 只讀 range-like object 的 `Start`、`End`、`Text`；
3. assert只從尾端逐字排除 `[char]13` 與 `[char]7`；
4. assert沒有使用 `Trim`／`TrimEnd`，不排除 space、tab 或 `[char]11`；
5. assert original/computed bounds 不一致時只 throw
   `LIST_HIGHLIGHT_RANGE_INVALID`，不包含 range text。

新增 `test_full_cell_highlight_is_direct_and_embedded_tokens_keep_find`：

1. assert `Set-TokenHighlight` 在 non-empty token 後呼叫 visible-end helper；
2. assert duplicate range 被精確 bound 到 `Range.Start`／visible end；
3. assert `[string]$visibleRange.Text -ceq $Token` 的 full-cell branch 在任何
   `Find.Execute()` 前，且直接設定 `$WdYellow`、記錄恰好 1 match；
4. assert embedded branch 保留既有 `$cursor`、`Find.ClearFormatting()`、
   `Find.Text`、`Find.Forward`、`Find.Wrap`、`Find.Execute()`、match counter 與 cursor
   advancement，順序不變；
5. assert visible duplicate 在 `finally` 釋放；
6. assert zero match 仍 throw caller-bound `$FailureCode`。

先執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_list.py::test_patch_plan_classifies_highlight_tokens_by_content_shape" `
  "tests\unit\travel_briefing\test_windows_word.py::test_visible_highlight_range_is_terminator_aware" `
  "tests\unit\travel_briefing\test_windows_word.py::test_full_cell_highlight_is_direct_and_embedded_tokens_keep_find" -q
```

預期修正前為 plan trigger test 通過、2 個 adapter tests 失敗，原因是 helper 與 direct
full-cell path 尚不存在。若兩個 adapter tests 意外全綠，先停止並重新確認 test seam，
不直接修改 production code；不得藉由弱化、skip 或刪除既有測試製造紅綠結果。

## Task 2：最小實作 visible-end helper 與 full-cell direct path

### 檔案

- 修改 `scripts/briefing/patch_list_template.ps1`

### `Get-ListVisibleRangeEnd`

在 `Set-TokenHighlight` 前新增無 Word method dependency 的 helper：

1. 參數只接受 mandatory range-like object；
2. 將 `Start`、`End` 讀為整數，`Text` 讀為字串；
3. 若 original end 小於 start，立即 throw `LIST_HIGHLIGHT_RANGE_INVALID`；
4. 從 `Text` 最後一個 code point 向前走，只在字元為 `[char]13` 或 `[char]7` 時將
   visible end 減 1；
5. 若要扣除的 terminator 數量大於 range span，或 computed end 小於 start，只 throw
   `LIST_HIGHLIGHT_RANGE_INVALID`；
6. 回傳 visible end 的整數值。

不得對內容使用 `Trim`／`TrimEnd`、regex whitespace、normalize 或 replace。space、tab、
`U+000B` manual line break 與所有 visible text 必須保留。

### `Set-TokenHighlight`

1. 保留 mandatory `FailureCode` 的 contextual regex 與 80-character safe-code validation，
   且仍在 empty-token early return 前執行；
2. non-empty token 先以 `Get-ListVisibleRangeEnd` 取得 boundary，初始化原有 cursor／matches；
3. 建立一個 visible duplicate，以 `SetRange(Range.Start, boundary)` 精確限縮；
4. 若 duplicate text 以 `-ceq` 完全等於 token，直接設定
   `HighlightColorIndex = $WdYellow` 並把 matches 記為 1，不碰 Find；
5. 無論 direct branch 是否命中，都在 `finally` 以既有安全模式釋放 duplicate；
6. 只有 matches 仍為 0 時才以相同 terminator-aware boundary 執行既有 Find loop；
7. embedded path 的搜尋文字、forward、no-wrap、黃色、match counter、cursor advancement
   與 zero-match caller-bound error 均不改。

不得修改 `Set-HeaderParagraph`／`Set-ListCell` 的 caller safe-code wiring，也不得把條件寫成
T4/R1/C2 或 guide-field 特例。`Set-ListCell` 寫值與 post-write checks 使用的其他
`End - 1` 不在本修正範圍；只替換 `Set-TokenHighlight` 原本的 fixed boundary。

重新執行 Task 1 command；預期 3 個 tests 全綠。

Commit：`fix(briefing): highlight full-cell LIST tokens directly`

## Task 3：無 COM helper probe

只從 runtime script 擷取並載入 `Get-ListVisibleRangeEnd`；不得載入或執行 job dispatch、
`Invoke-Patch`、Word adapter 或任何 `JobPath`。以 `PSCustomObject` 建立 synthetic cases：

- paragraph `TOKEN + U+000D`：visible end 等於 token 結尾；
- cell `TOKEN + U+000D + U+0007`：同樣回到 token 結尾；
- embedded text 加 CR/BEL：只排除最後兩個 terminators；
- 尾端 space、tab：不得被排除；
- 內含／尾端 `U+000B`：不得被排除；
- `End < Start` 與 terminator 數量大於 range span：只得到
  `LIST_HIGHLIGHT_RANGE_INVALID`。

probe 必須輸出固定、不含內容的摘要，例如：

```text
VISIBLE_RANGE_CASES=5
VISIBLE_RANGE_INVALID_CASES=2
VISIBLE_RANGE_ERROR=LIST_HIGHLIGHT_RANGE_INVALID
```

probe 前後可記錄既有 WINWORD process count 作 non-use evidence；不得啟動、終止或接管
使用者的 Word process。

## Task 4：focused regression、parser 與 non-change proof

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
rg -n 'Get-ListVisibleRangeEnd|Set-TokenHighlight|Range.End - 1|SetRange|Find\.(Text|Forward|Wrap|Execute)|HighlightColorIndex|LIST_HIGHLIGHT_RANGE_INVALID' `
  scripts\briefing\patch_list_template.ps1 `
  tests\unit\travel_briefing\test_windows_word.py
```

判讀要求：

- `Set-TokenHighlight` 不再使用 fixed `Range.End - 1`；
- 其他經既有 tests 鎖定的 `End - 1` 不得被這次全域替換；
- helper／direct branch／embedded Find loop 與固定 safe code 都存在；
- header paragraph 與 ordinary cell 的 caller-bound failure-code wiring diff 為零；
- 沒有 token、text 或 OP value 被串入 exception；
- 不得放寬或移除 paragraph、QR、font、pagination、layout 或安全錯誤碼 assertions。

任何 focused failure、probe failure 或 parser error 只在本計畫列出的最小 scope 內修正。

## Task 5：完整離線驗證

執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
```

目前完整 suite 基線是 `553 passed, 8 skipped`。若只新增上述 3 個 tests，預估為
`556 passed, 8 skipped`；這只是參考，回報一律以實際輸出為準，不為符合預估數字修改
測試。

最後逐段檢查：

```powershell
git diff -- scripts/briefing/patch_list_template.ps1 `
  tests/unit/travel_briefing/test_windows_word.py `
  tests/unit/travel_briefing/test_word_list.py
git status --short --branch
```

人工確認 diff 只含 visible-end helper、full-cell direct branch、保留的 embedded Find contract
與對應 regressions。不得包含輸出內容、schema、字體、QR、paragraph、pagination、私人檔案、
calibration 或 installed runtime 變更。

## Task 6：handoff 與本機提交

更新 `STATUS.md`，記錄：

- red run 的實際通過／失敗數與關鍵原因；
- green target tests、focused files、helper probe、PowerShell parser、full suite、compileall、
  static checks 與 `git diff --check` 的實際結果；
- direct full-cell 與 embedded/repeated Find 的精確行為；
- Word／私人 master／calibration／installed runtime 均未使用或修改；
- Word 實機與 DOCX／PDF／PNG 結果仍未驗證；
- branch、commits、ahead count 與未 push 狀態。

Commit：`docs: record LIST full-cell highlight handoff`

最後要求：

```powershell
git status --short --branch
git log -3 --oneline
```

working tree 必須乾淨。本計畫不執行 push，因 public remote push 是獨立授權。

## 3. 完成定義

離線實作只有在下列條件全部成立時才算完成：

- content-shape control test 鎖定 5 embedded＋2 full-cell cases；
- 兩個 adapter regressions 先紅、最小修正後全綠；
- helper 只排除尾端 CR／BEL，無 COM probe 證明 space、tab、manual line break 均保留；
- exact full-cell token 直接套黃色且不依賴 Word Find；
- embedded 與 repeated tokens 保留原 Find／cursor loop；
- invalid bounds 只產生 `LIST_HIGHLIGHT_RANGE_INVALID`，既有 caller-bound safe-code contract
  不變；
- focused tests、parser、完整 suite、compileall、靜態檢查與 `git diff --check` 全部通過；
- STATUS 與本機 commits 完整、工作樹乾淨；
- 沒有 Word、私人檔案、網路、installed runtime、外部寫入或 push。

上述完成只代表離線修正與回歸已完成，不代表私人 master 的 Word blocker 已實機解除。
下一關仍需新的明確授權，只執行一次 4 天 post-fix Word repro；不跑其他天數，失敗不重試。
