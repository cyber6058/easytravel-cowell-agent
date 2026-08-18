# LIST leader cell manual-line-break fix implementation plan

日期：2026-08-18

狀態：書面規格已由 OP 核准；本計畫待 OP 核准後才可執行 repo 內離線實作

依據：
`docs/specs/2026-08-18-list-leader-cell-manual-line-break-fix-design.md`

基線 commit：`0b0b7a1`

## 1. 目標與已知證據

只修正 LIST ordinary cell T1/R2/C3 的領隊姓名／台灣手機換行契約：

- 畫面仍分成兩行；
- patch payload 使用 `U+000B` manual line break；
- payload 不得含會建立新段落或 cell marker 的 `U+000D`、`U+000A`、`U+0007`；
- Word adapter 的單一 paragraph assertion 維持不變；
- 私人 master 與 calibration manifest 維持不變。

現有離線 tight loop 對實際 4 天 synthetic plan 連續三次得到：

```text
RUN_CODEPOINTS=U+000D|U+000D|U+000D
AssertionError: all three plans must use one-paragraph manual line breaks
```

現有 PowerShell 結構測試同時為 `1 passed`，所以必須在 Python patch-plan payload
層新增 regression，不能只依賴 adapter source-text assertion。

## 2. 授權範圍與停止點

核准本計畫只授權：

- 修改 `src/travel_briefing/word_list.py`；
- 修改 `tests/unit/travel_briefing/test_word_list.py`；
- 執行 repo 內 synthetic／mock 離線測試、PowerShell parser、`compileall`、靜態搜尋與
  `git diff --check`；
- 更新 `STATUS.md` 並建立本機 commits。

本計畫不授權：

- 修改 `scripts/briefing/patch_list_template.ps1`；
- 讀取或修改私人 master、calibration manifest、既有 DRAFT 或 installed runtime；
- 啟動 Word COM、Yating、ffmpeg 或 GUI；
- NewAmazing／JMA GET、安裝／下載、LINE、Cowell、deploy、publish、push 或任何外部寫入。

完整離線驗證通過後停止。新的 4 天 Word repro 仍需要另一個當次明確授權，且失敗
不得自動重試。

## Task 1：建立 payload-level red tests

### 檔案

- 修改 `tests/unit/travel_briefing/test_word_list.py`

### 測試

新增 `test_patch_plan_uses_manual_line_break_for_leader_cell`：

1. 使用既有 `draft(4)` 與 `build_list_patch_plan` 公開 seam；
2. 取得 `plan.cell(1, 2, 3).text`；
3. assert exact value 為
   `領隊姓名：合成領隊\v*台灣手機：待 OP 確認`；
4. assert 全部 `plan.cells` 的 `text` 均不含 `\r`、`\n`、`\a`。

新增 parameterized `test_patch_plan_rejects_forbidden_word_markers_in_ordinary_cells`：

1. 依序把 `\r`、`\n`、`\a` 注入一個 ordinary OP field；
2. 呼叫 `build_list_patch_plan`；
3. 要求固定、不含欄位值的 `ValueError`；
4. 明確 assert exception 不含 synthetic secret 或完整 rejected value。

先執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_list.py::test_patch_plan_uses_manual_line_break_for_leader_cell" `
  "tests\unit\travel_briefing\test_word_list.py::test_patch_plan_rejects_forbidden_word_markers_in_ordinary_cells" -q
```

預期修正前為 4 個 test cases 失敗；若意外全綠，先停止並重新確認 test seam，不直接
改 production code。

## Task 2：最小修正 plan source 與 boundary validation

### 檔案

- 修改 `src/travel_briefing/word_list.py`

### 實作

1. 將 `_build_header_cells` 的 `leader_text` 中 `\r` 改成 `\v`；文字、星號、欄位順序
   與 highlight contract 全部不變。
2. 新增一個私有 ordinary-cell validator，逐一檢查 `CellPatch.text` 是否包含
   `\r`、`\n` 或 `\a`。
3. 在 `build_list_patch_plan` 完成所有 cell builders 後、建立 `ListPatchPlan` 前執行
   validator。
4. 遇到 forbidden marker 時只拋固定訊息
   `LIST ordinary cell text contains a forbidden Word marker`，不得把 cell text、OP value
   或其他可能含 PII 的內容放進 exception。
5. 不自動轉換外來 CR/LF，不修改 `CellPatch` schema、plan schema/version、PowerShell
   adapter 或 calibration contract。

重新執行 Task 1 command；預期 4 個 cases 全綠。

再執行原始 4 天資料流的離線 loop：

```powershell
.\.venv\Scripts\python.exe -X utf8 -c "import runpy; from travel_briefing.word_list import build_list_patch_plan; ns=runpy.run_path(r'tests\integration\travel_briefing\test_word_list_integration.py'); value=build_list_patch_plan(ns['synthetic_draft'](4), expected_layout_fingerprint='a'*64).cell(1,2,3).text; print('T1_R2_C3_CODEPOINTS=' + ','.join('U+%04X'%ord(ch) for ch in value if ch in '\r\v')); assert '\r' not in value and '\v' in value"
```

預期輸出：

```text
T1_R2_C3_CODEPOINTS=U+000B
```

Commit：`fix(briefing): use manual line break in LIST leader cell`

## Task 3：focused regression 與 adapter non-change proof

執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_word_list.py `
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

確認 adapter 沒有被修改：

```powershell
git diff --exit-code -- scripts/briefing/patch_list_template.ps1
```

任何 focused regression 或 parser error 都先修正同一最小 scope；不得放寬、skip 或刪除
既有 paragraph assertion。

## Task 4：完整離線驗證

執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
rg -n 'leader_text = .*\\r|LIST_CELL_EXTRA_PARAGRAPH_SET' `
  src\travel_briefing scripts\briefing tests\unit\travel_briefing
git diff --check
```

靜態搜尋的判讀：

- `src/travel_briefing/word_list.py` 不得再有 leader `\r`；
- PowerShell 的 `LIST_CELL_EXTRA_PARAGRAPH_SET` fail-closed assertion 必須仍存在；
- tests 可保留明確驗證 forbidden `\r` 的 literals。

完整 suite 的先前基線是 `547 passed, 8 skipped`。新增 4 個 parameterized cases 後預期
為 `551 passed, 8 skipped`；回報以實際輸出為準，不為符合預估數字修改測試。

## Task 5：handoff 與本機提交

更新 `STATUS.md`，記錄：

- red tests 的原始失敗數與訊息；
- green tests、focused suite、full suite、parser、compileall、static search 與
  `git diff --check` 的實際結果；
- 原始 4 天離線 loop 已由 `U+000D` 變為 `U+000B`；
- PowerShell、私人 master、calibration、installed runtime 均未修改；
- Word 實機與 DOCX／PDF／PNG 視覺結果仍未驗證；
- branch、commits、ahead count 與未 push 狀態。

Commit：`docs: record LIST leader line-break fix handoff`

最後要求：

```powershell
git status --short --branch
git log -3 --oneline
```

working tree 必須乾淨。本計畫不執行 push，因 public remote push 是獨立授權。

## 3. 完成定義

離線實作只有在下列條件全部成立時才算完成：

- red-capable payload regression 已先失敗、修正後通過；
- T1/R2/C3 的實際 4 天 synthetic plan 只含 `U+000B`，不含 `U+000D`；
- 任一 ordinary cell 的 CR、LF、BEL 在 Word 前 fail closed，錯誤不洩漏值；
- PowerShell 單一 paragraph assertion 未修改且 focused tests 全綠；
- full suite、parser、compileall、static search 與 `git diff --check` 通過；
- STATUS 與本機 commits 完整、工作樹乾淨；
- 沒有 Word、私人檔案、網路、installed runtime、外部寫入或 push。

上述完成只代表離線 contract 修正，不代表私人 master 的 Word blocker 已實機解除。下一
關仍是取得新的明確授權，只執行一次 4 天 post-fix Word repro；失敗不重試。
