# LIST full-cell direct range retreat implementation plan

日期：2026-08-18

狀態：書面規格與本計畫均已由 OP 核准；離線實作於 2026-08-18 完成並通過完整
驗證。Word 實機 repro 仍是獨立關卡。

依據：
`docs/specs/2026-08-18-list-full-cell-direct-range-design.md`

設計基線 commit：`642a1e2`

## 1. 目標與已知證據

只修正 `Set-TokenHighlight` 的 exact full-cell direct range：移除把 trailing text
code-point 數量直接換算成 Word Range positions 的 `Get-ListVisibleRangeEnd`，改用與同一格
`Set-ListCell` post-write assertion 相同、已通過實機 execution 的 duplicate `End - 1`
操作。

保留以下行為不變：

- exact visible text 與 token 以 case-sensitive `-ceq` 比較；
- direct match 直接套 `$WdYellow`、記錄一個 match，且不呼叫 Find；
- embedded／repeated tokens 使用 `$findBoundary = [int]$Range.End - 1`；
- Find settings、match counter、cursor advancement 與 caller-bound safe codes；
- `Set-HeaderParagraph`、`Set-ListCell`、內容、schema、formatting、master 與 calibration。

已知實機 evidence chain：

1. 唯一一次 boundary-split 4 天 Word repro 通過五個 embedded cases，才停在第一個
   full-cell case：

   ```text
   LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2
   ```

2. 同一 execution 在 highlight 前，`Set-ListCell` 對同一格 duplicate 執行
   `End - 1` 後，已精確匹配 `Patch.text`。
3. T4/R1/C2 的 `Patch.text` 與 `Patch.highlight_text` 都是 `WAITING_FOR_OP`。
4. 現行 helper 讀到 cell 尾端兩個文字碼點 `U+000D U+0007`，卻從 `Range.End`
   退兩個 positions；這比已通過的同格操作多退一格。

現行四個相關離線 tests 仍為 `.... [100%]`。這是 source-contract gap，不是修正已
完成。離線計畫可驗證 source shape 與 compound-marker model，但不能宣稱 Word 已跨過
T4/R1/C2。

## 2. 已核准 test seam

本修正的 pre-agreed seam 是 PowerShell adapter source contract：

- `tests/unit/travel_briefing/test_windows_word.py` 檢查 adapter 的 Range boundary、
  safe-code、Find、cleanup 與 caller non-change contracts；
- `tests/unit/travel_briefing/test_word_list.py` 以現有 public plan builder 行為作
  content-shape control，只執行、不修改；
- 無 COM compound-marker model 使用規格中的已知 literal 與實機 invariant，獨立呈現
  兩個 terminal text code points 對一個 cell Range retreat 的差異。

source-contract tests 會與實作結構耦合，但這是因本階段明確禁止 Word COM，而經書面規格
核准的有限 seam。不得把它擴張成 mock Word、私人檔案 probe 或新的 COM instrumentation。

## 3. 授權範圍與停止點

核准本計畫只授權：

- 修改 `tests/unit/travel_briefing/test_windows_word.py`；
- 修改 `scripts/briefing/patch_list_template.ps1`；
- 唯讀執行 `tests/unit/travel_briefing/test_word_list.py` 的既有 content-shape control；
- 執行 source-contract tests、無 COM model、PowerShell parser、完整離線 suite、
  `compileall`、靜態／non-change checks 與 `git diff --check`；
- 更新本計畫、原書面規格狀態與 `STATUS.md`，並建立本機 commits。

本計畫不預期修改 `tests/unit/travel_briefing/test_word_list.py`。若實作時證明該檔、caller、
plan builder、schema、formatting 或其他 production file 必須改動，立即停止並回到書面
範圍審查。

本計畫不授權：

- 啟動 Word COM、執行 Word repro、產生 DOCX／PDF／PNG 或操作 GUI；
- 讀取或修改私人 master、calibration manifest、既有 DRAFT 或 installed runtime；
- NewAmazing／JMA GET、Yating、ffmpeg、安裝／下載、LINE、Cowell、deploy、publish、
  push 或任何外部寫入。

完整離線驗證通過後停止。新的 4 天 Word reproduction 仍需另一個當次明確授權，只能
執行一次；不跑其他天數，成功或失敗都不得自動重試。

## Task 1：建立 one-retreat primary red regression

### 檔案

- 修改 `tests/unit/travel_briefing/test_windows_word.py`

### 實作基線與乾淨工作樹

實作開始先記錄：

```powershell
git status --short --branch
git pull --ff-only
$listDirectRangeBaseline = git rev-parse HEAD
```

pull 前 working tree 必須乾淨，且 pull 後重新確認 HEAD、`STATUS.md`、本計畫與核准規格
一致，再記錄 implementation baseline。
若有未知變更或新 commit 改到核准兩檔，保留現況並停止，不覆蓋或自動重訂計畫。

### 將錯誤 helper test 改成單一 behavior regression

把 `test_visible_highlight_range_is_terminator_aware` 改名為能描述行為的
`test_full_cell_direct_range_reuses_one_position_retreat`，並要求：

1. 整份 script 不再定義或呼叫 `Get-ListVisibleRangeEnd`；
2. direct path 先取得 `$visibleRange = $Range.Duplicate`；
3. 只計算一次 `$directEnd = [int]$visibleRange.End - 1`；
4. 在指定 duplicate end 前，先判斷 `$directEnd -lt [int]$visibleRange.Start`；
5. invalid branch 只 throw `LIST_HIGHLIGHT_RANGE_INVALID`；
6. safe check 通過後使用 `$visibleRange.End = $directEnd`，不呼叫 `SetRange`；
7. 不用 `Range.Text` terminator loop、`Trim`、`TrimEnd`、CR／BEL code-point count
   或任何座標／field special case 推導 Word coordinate；
8. direct duplicate 繼續在 `finally` 以既有安全模式釋放；
9. `$findBoundary = [int]$Range.End - 1`、Find settings、counter 與 cursor statements
   仍存在且次序不變；
10. `Set-ListCell` 仍包含 live-proven `$postRange.End = [int]$postRange.End - 1`
    與 exact text check。

這是一個 vertical slice：一個 regression 描述「direct range 只退一個 Word position，
同時不破壞 Find 與 post-write invariant」這一項行為；Task 2 只做讓它通過的最小
production change。

### Red command

依序執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_list.py::test_patch_plan_classifies_highlight_tokens_by_content_shape" `
  "tests\unit\travel_briefing\test_windows_word.py::test_full_cell_direct_range_reuses_one_position_retreat" -q
```

預期 content-shape control 通過；primary adapter regression 必須因現行 helper 仍存在、
direct path 尚未使用 duplicate `End - 1` 而紅燈。回報實際 pass／fail 數與最短關鍵
assertion，不要求符合預估字樣。

若 primary adapter regression 意外全綠，停止並重新確認 test 是否真的能區分 `End - 2` 與
`End - 1`；不得直接修改 production，也不得弱化、skip 或刪除 tests。

## Task 2：最小 production change

### 檔案

- 修改 `scripts/briefing/patch_list_template.ps1`

### 移除錯誤 abstraction

完整移除 `Get-ListVisibleRangeEnd` function。它只有一個 production caller，且將 textual
terminator count 映射成 Range positions 的抽象已被實機 invariant 否定。

不得以另一個 helper、CR+BEL special case、regex、Trim 或 hard-coded coordinate 取代。

### 修改 `Set-TokenHighlight`

保留 failure-code validation 與 empty-token return。對 non-empty token：

1. 保留 `$findBoundary = [int]$Range.End - 1`；
2. 保留既有 cursor、matches 與 `$visibleRange = $null` 初始化；
3. 在既有 `try` 內取得 `$visibleRange = $Range.Duplicate`；
4. 計算 `$directEnd = [int]$visibleRange.End - 1`；
5. 若 `$directEnd -lt [int]$visibleRange.Start`，throw
   `LIST_HIGHLIGHT_RANGE_INVALID`；
6. 指定 `$visibleRange.End = $directEnd`；
7. 以既有 `[string]$visibleRange.Text -ceq $Token` 比較；
8. exact match 時套 `$WdYellow` 並設 `$matches = 1`；
9. 無論 match 或 safe failure，都透過既有 `finally` release duplicate；
10. 只有 `$matches -eq 0` 才進入完全不變的 Find loop。

必須用 duplicate 自己的 `Start`／`End` 做 direct safe check，不混用文字碼點數量。不得
更改 `Set-HeaderParagraph`、`Set-ListCell`、Find boundary/settings/cursor、safe-code builder
或 caller wiring。

重新執行 Task 1 command。primary regression 必須轉綠，content-shape control 必須持續
通過。若失敗需要超出上述最小 source change，停止，不修改其他 production。

## Task 3：對齊 preservation contracts 與執行 compound-marker model

### 對齊現有 source contracts

primary regression 轉綠後，才更新同檔內因舊 helper shape 過時的 preservation tests；
這一步不得再改 production：

1. `test_highlight_failure_code_is_validated_before_empty_token_return` 保留 validation、
   empty-token、Find settings、caller-bound `$FailureCode` 與禁止 generic throw assertions；
   移除 helper expectation，並要求 direct branch 在 Find 前。
2. `test_full_cell_highlight_is_direct_and_embedded_tokens_keep_find` 改鎖定 duplicate、
   one-position `directEnd`、safe check、direct `End` assignment、exact equality、yellow 與
   `$matches = 1`；Find boundary、settings、counter 與 cursor advancement 全部不變。
3. `test_list_cell_replaces_only_visible_text_and_asserts_one_paragraph` 補上
   `$postRange` duplicate、`End - 1`、exact text check、safe error 與 cleanup controls。

執行完整 target set：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_list.py::test_patch_plan_classifies_highlight_tokens_by_content_shape" `
  "tests\unit\travel_briefing\test_windows_word.py::test_highlight_failure_code_is_validated_before_empty_token_return" `
  "tests\unit\travel_briefing\test_windows_word.py::test_full_cell_direct_range_reuses_one_position_retreat" `
  "tests\unit\travel_briefing\test_windows_word.py::test_full_cell_highlight_is_direct_and_embedded_tokens_keep_find" `
  "tests\unit\travel_briefing\test_windows_word.py::test_list_cell_replaces_only_visible_text_and_asserts_one_paragraph" -q
```

所有 cases 必須通過。preservation contract update 只反映已由 primary red→green slice 決定的
source behavior，不能引入第二個 production change。

若失敗只涉及核准 direct-range source shape，可在本計畫兩個核准檔案內做最小修正後重跑；
若需要改 caller、plan builder 或格式契約，立即停止。

### 無 COM compound-marker model

不得載入或執行 patch script、JobPath、Word adapter 或 COM。以已知 literal 建立獨立模型：

- token range span 是 7；
- paragraph text tail 有一個 terminator code point，range terminator span 是 1；
- cell text tail 有兩個 terminator code points，range terminator span 是 1；
- removed algorithm 以 text count 退兩格，cell visible span 只剩 6；
- selected algorithm 對 paragraph 與 cell 都退一個 range position，visible span 都是 7。

cell range terminator span 1 的依據必須明記為先前 live `Set-ListCell` exact assertion，不能
描述成這次 model 新證明的 Word 事實。

輸出固定、不含 token 或 OP content 的摘要：

```text
TOKEN_RANGE_SPAN=7
PARAGRAPH_TEXT_TERMINATOR_CODEPOINTS=1
PARAGRAPH_RANGE_TERMINATOR_SPAN=1
PARAGRAPH_SELECTED_VISIBLE_SPAN=7
CELL_TEXT_TERMINATOR_CODEPOINTS=2
CELL_RANGE_TERMINATOR_SPAN=1
CELL_REMOVED_ALGORITHM_VISIBLE_SPAN=6
CELL_SELECTED_VISIBLE_SPAN=7
CELL_REMOVED_ALGORITHM_OVER_RETREAT=1
SELECTED_DIRECT_END_RETREAT=1
```

model 前後只讀取 WINWORD process count 作 non-use evidence；不得啟動、終止或接管既有
WINWORD process。

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
rg -n 'Get-ListVisibleRangeEnd|directEnd|Set-TokenHighlight|postRange|findBoundary|Range.End - 1|SetRange|Find\.(Text|Forward|Wrap|Execute)|HighlightColorIndex|LIST_HIGHLIGHT_(RANGE|CONTEXT|TOKEN)' `
  scripts\briefing\patch_list_template.ps1 `
  tests\unit\travel_briefing\test_windows_word.py
```

判讀要求：

- helper function／call 為零；
- direct duplicate 只有一個 `End - 1` retreat 與一個 safe assignment；
- `Set-ListCell` write range 與 post-write range 的既有 `End - 1` 均完整保留；
- embedded loop 與 search range 只使用 `$findBoundary`；
- direct branch 不呼叫 Find；
- validation、safe codes、Find settings、cursor 與 cleanup 均未改；
- 沒有 Trim、terminal-code-point loop、coordinate／field special case；
- exception 不含 token、cell text 或 OP value。

以 `$listDirectRangeBaseline` 做 non-change comparison，要求：

- `src/travel_briefing/word_list.py` 與
  `tests/unit/travel_briefing/test_word_list.py` diff 為零；
- `Set-HeaderParagraph` 與 `Set-ListCell` source segments diff 為零；
- patch-plan／report schema、generator version、QR policy、12-point typography、paragraph、
  pagination、layout、master、calibration 與 installed runtime 均無變更；
- production/test changed files 精確為核准的兩檔。

任何 focused、model、parser 或 non-change failure 只在核准兩檔的最小範圍內修正；如需
擴張 scope，停止並回報。

## Task 5：完整離線驗證與 implementation commit

執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
```

最近一次已記錄完整 suite 基線為 `556 passed, 8 skipped`。本計畫修改既有 tests、不新增
case，數量預期不變；這只是參考，回報一律使用實際輸出，不為符合數字修改 tests。

最後逐段檢查：

```powershell
git diff -- scripts/briefing/patch_list_template.ps1 `
  tests/unit/travel_briefing/test_windows_word.py
git status --short --branch
```

人工確認 diff 只含 helper removal、one-retreat direct range 與對應 source-contract
regressions。完整離線驗證全部通過後，才建立 implementation commit：

```text
fix(briefing): retreat LIST direct highlight range once
```

## Task 6：handoff 與本機文件提交

更新本計畫狀態、原書面規格狀態與 `STATUS.md`，記錄：

- implementation baseline commit 與開工 pull／working-tree 狀態；
- red run 的實際 pass／fail 形狀與關鍵 assertions；
- target green、無 COM model、focused files、PowerShell parser、完整 suite、compileall、
  static／non-change checks 與 `git diff --check` 的實際輸出；
- helper 已移除、direct path 只退一格、Find path 未改；
- production commit、handoff commit、branch 與 ahead count；
- Word、私人 master、calibration、DRAFT、installed runtime 與外部系統均未使用或修改；
- Word 實機與 DOCX／PDF／PNG 結果仍未驗證。

建立本機 handoff commit：

```text
docs: record LIST direct range handoff
```

最後執行：

```powershell
git status --short --branch
git log -3 --oneline
```

working tree 必須乾淨。本計畫不執行 push；push 是另一個明確授權關卡。

## 實作結果（2026-08-18）

- implementation baseline 為 `ad791d0dd15d99c986db5dee798a702d40b14e86`；開工
  `git pull --ff-only` 為 `Already up to date.`，working tree 乾淨。
- primary red command 原文為 `.F [100%]`。content-shape control 通過；adapter
  regression 因 `function Get-ListVisibleRangeEnd {` 仍存在而失敗，符合計畫後才修改
  production。
- 最小 production change 完整移除該 helper；direct duplicate 計算一次
  `$directEnd = [int]$visibleRange.End - 1`，safe check 後直接指定 `End`。同一 red command
  轉為 `.. [100%]`。
- 對齊 preservation contracts 後，五個 target tests 為 `..... [100%]`；沒有第二個
  production change。
- 無 COM model 輸出 `PARAGRAPH_SELECTED_VISIBLE_SPAN=7`、
  `CELL_TEXT_TERMINATOR_CODEPOINTS=2`、`CELL_RANGE_TERMINATOR_SPAN=1`、
  `CELL_REMOVED_ALGORITHM_VISIBLE_SPAN=6`、`CELL_SELECTED_VISIBLE_SPAN=7`、
  `CELL_REMOVED_ALGORITHM_OVER_RETREAT=1`、`SELECTED_DIRECT_END_RETREAT=1`，前後
  WINWORD count 都是 1。cell range span 仍來自先前 live invariant，不是本輪新 Word
  evidence。
- 兩個 focused files 的 84 tests 全綠；PowerShell parser 輸出
  `PARSER_ERROR_COUNT=0`。
- 第一次唯讀 non-change wrapper 因 PowerShell `.Split()` 把 delimiter 當字元集合，令
  direct／Find occurrence 誤計為 0 並以 exit 1 停止；未修改任何檔案。改用
  `IndexOf`／`Substring` 後重新執行，所有 checks 通過。
- final non-change proof 為 `PLAN_BUILDER_UNCHANGED=True`、
  `TEST_WORD_LIST_UNCHANGED=True`、`HEADER_CALLER_UNCHANGED=True`、
  `CELL_CALLER_UNCHANGED=True`、helper definition／call 均為 0、direct retreat／Find
  boundary 均為 1、coordinate／direct-forbidden counts 均為 0、
  `CHANGED_FILE_COUNT=2`、`CHANGED_FILES_EXACT=True` 與 `GIT_DIFF_CHECK_OK`。
- 完整 suite 為 `556 passed, 8 skipped in 25.98s`；另有 `COMPILEALL_OK` 與
  `GIT_DIFF_CHECK_OK`，validation 後 WINWORD count 仍為 1。
- implementation commit 為 `7cb8c0b`（`fix(briefing): retreat LIST direct highlight
  range once`）；只修改核准的 PowerShell adapter 與 source-contract tests。
- 沒有啟動 Word、讀寫私人 master／calibration／DRAFT、產生 DOCX／PDF／PNG、使用網路、
  installed runtime 或外部系統，也沒有 push。Word blocker 是否解除仍未驗證。

## 4. Failure handling

- primary red adapter regression 未按預期失敗：停止，不改 production。
- target／focused／full suite 失敗且可由核准 direct-range change 解決：做最小修正後重跑
  離線 tests；這不是 Word repro retry。
- failure 要求改 caller、plan builder、schema、formatting、master、calibration 或其他檔案：
  停止並回報新 scope。
- 工作樹有未知變更：保留並停止，不覆蓋。
- parser 或 compileall 失敗：只在核准兩檔內修正；若無法做到，停止。
- 不論離線結果如何，本計畫都不啟動 Word。

## 5. 完成定義

離線實作只有在下列條件全部成立時才算完成：

- adapter regression 先因 helper／over-retreat source shape 紅燈，再由最小 production
  change 轉綠；
- helper function 與 call 完全移除；
- direct duplicate 只退一個自己的 `End` position，且 assignment 前有 safe check；
- direct exact match bypass Find；
- embedded／repeated Find boundary、settings、counter 與 cursor loop 完整保留；
- `Set-ListCell` 的 live-proven one-position post-write assertion 未改；
- content-shape control 維持 5 embedded＋2 direct，repeated token 維持兩次；
- 無 COM model 明確區分兩個 terminal text code points 與一個 cell range position；
- 沒有 Trim、text-to-coordinate loop、座標或 field special case；
- focused tests、parser、完整 suite、compileall、static／non-change checks 與
  `git diff --check` 全部通過；
- STATUS、計畫、規格狀態與本機 commits 完整，working tree 乾淨；
- 沒有 Word、私人檔案、網路、installed runtime、外部寫入或 push。

上述完成只代表離線 correction 通過驗證，不代表私人 master 的 Word blocker 已解除。
下一關仍需新的明確授權，只執行一次 4 天 post-fix Word repro；不跑其他天數，成功或
失敗都不重試。

## 6. 計畫核准關卡

OP 已於 2026-08-18 使用下列用語核准本計畫。該核准只涵蓋本計畫列出的
production／test change、離線驗證與本機 commits，不涵蓋 Word 或其他外部關卡：

```text
同意此實作計畫，開始離線實作
```
