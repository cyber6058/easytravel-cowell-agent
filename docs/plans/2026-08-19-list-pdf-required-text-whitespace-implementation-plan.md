# LIST PDF required-text layout-whitespace offline implementation plan

日期：2026-08-19

狀態：書面規格已由 OP 核准；本計畫等待 OP review，尚未開始實作。

依據：
`docs/specs/2026-08-19-list-pdf-required-text-whitespace-design.md`

設計基線 commit：
`ca7ea7571a893954507f2bbc51c76c86c340dfcf`

Implementation baseline：核准本計畫並開始實作後，以乾淨 working tree 的
`git rev-parse HEAD` 實際值為準，記錄到本計畫與 `STATUS.md`。

## 1. 目標與已知證據

本計畫只修正 `inspect_list_pdf()` 的 aggregate `required_text` presence check：

1. PDF layout 造成的空格、換行、tab 與其他 Python Unicode whitespace 不影響
   aggregate required-text presence；
2. 每個非 whitespace 字元及其順序仍須完整相同；
3. whitespace-only expected token 在開啟 PDF 前 fail closed；
4. 真正缺少的 token 仍以原始值、caller order、original-value dedupe 回報；
5. continuation、day token／page map、A4、image、page count、failed evidence、PNG 與
   index 契約全部不變。

唯一一次 4 天 Word repro 的同次證據為：

```text
LIST_PDF_REQUIRED_TEXT_MISSING
1 failed in 32.29s
```

保留的 DOCX 含完整 contiguous service-fee target；保留的 PDF 抽取文字在
`每人每天` 與 `新台幣` 之間有 Word layout newline。raw target 不匹配，但移除
whitespace 後完整匹配。這證明現行 blocker 是 PDF text QA false negative，不是正文
遺失。

本計畫不得把這份實機證據重新解讀為 successful artifact QA；正常 PDF、PNG 與 index
當時未發布，Word run 授權也已消耗。

## 2. 核准檔案、unchanged controls 與停止點

未來實作只允許修改：

- `tests/unit/travel_briefing/test_word_qa.py`；
- `src/travel_briefing/word_qa.py`；
- 本計畫與 `STATUS.md` handoff。

下列檔案與契約是明確 unchanged controls：

- `src/travel_briefing/workflow.py`；
- `src/travel_briefing/errors.py`；
- `src/travel_briefing/word_list.py`；
- `scripts/briefing/patch_list_template.ps1`；
- `scripts/briefing/render_list_template.ps1`；
- `tests/unit/travel_briefing/test_local_backend.py`；
- `tests/unit/travel_briefing/test_word_list.py`；
- `tests/unit/travel_briefing/test_windows_word.py`；
- `tests/integration/travel_briefing/test_word_list_integration.py`；
- private master、calibration manifest及所有既有 retained artifacts；
- LIST generator／plan／patch-report schema 4；
- Word render job／report schema 1；
- calibration schema 2；
- failed evidence schema 1；
- successful QA index schema 2；
- public function signatures、dataclasses、error codes與artifact names；
- QR removal、full-width identity、12 pt non-title、no-extra-paragraph、pagination、
  service-fee formatting與arbitrary-day contracts。

若實作證明必須修改任何 unchanged control、workflow caller、schema、adapter、master、
calibration或integration selector，立即停止並回到書面設計 review，不順手擴張。

本計畫不授權：

- Word COM、Word repro、GUI或實機 DOCX／PDF／PNG；
- private master／calibration讀寫；
- NewAmazing／JMA GET、Yating、ffmpeg、dependency download；
- LINE、Cowell、deploy、publish、push或任何外部寫入；
- 自動 retry、fallback、prior evidence overwrite或cleanup。

完整離線驗證通過後停止。任何新 4 天 Word verification 仍需另一個精確 one-shot
授權；只能跑一次、不跑其他天數，成功或失敗都不重試。

## 3. TDD seam 與 commit map

### 核准測試 seam

公開行為 seam 是：

```python
inspect_list_pdf(pdf_path, required_text=...)
```

tests 使用 PyMuPDF 寫入真實 synthetic A4 PDF，再透過 public function 觀察成功或
`ValueError`。不得直接 import 或測試 future private whitespace helper，也不得 mock
`inspect_list_pdf()` 內部協作者。

Expected values 來自核准規格中的固定 literals，不得用 production helper 重新計算預期。
每個改變行為的 slice 必須先看到指定 red，再做最小 production change轉綠。

### 預定 commits

所有離線驗證通過後建立：

1. `fix(briefing): ignore LIST PDF layout whitespace`
   - 兩個 red→green slices；
   - strict-content與page-local regression controls；
   - 只含兩個核准 implementation files。
2. `docs: record LIST PDF whitespace implementation handoff`
   - 本計畫實際結果與 `STATUS.md`；
   - 不含 production／test changes。

不得建立 red-only commit。若任一 slice 無法得到符合預期的 red，先檢查 test setup與
現行行為，不提前改 production。

## Task 1：implementation preflight 與 layout-wrap primary red

### 乾淨基線

離線實作開始先執行：

```powershell
git status --short --branch
git pull --ff-only
$listWhitespaceBaseline = git rev-parse HEAD
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
Get-ChildItem Env:RUN_BRIEFING_WORD_INTEGRATION -ErrorAction SilentlyContinue
```

要求 working tree 乾淨、Word opt-in 未設定。記錄 implementation baseline、branch、
WINWORD baseline與pull原文。若出現未知變更，保留現況並停止，不覆蓋使用者工作。

### Primary behavior test

在 `test_word_qa.py` 新增：

```text
test_pdf_inspection_matches_required_text_across_layout_whitespace
```

透過既有 PyMuPDF test style 建立一頁 A4 PDF。使用 PyMuPDF built-in
`fontname="china-t"`，把核准 service-fee文字分成兩個相鄰文字行，使 readback 明確包含：

```text
每人每天
新台幣 300 元，四天共新台幣 1,200 元
```

test setup 必須先用 PyMuPDF readback assertion 證明：

- raw PDF text不含contiguous required token；
- `"".join(extracted.split())` 包含
  `"".join(required_token.split())`；
- PDF仍有至少20個non-whitespace characters。

接著只透過 `inspect_list_pdf()` 傳入contiguous service-fee literal，要求回傳一頁有效
inspection。setup assertion只驗證fixture形狀，不取代public seam assertion。

### Red command

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_matches_required_text_across_layout_whitespace" -q
```

預期現行 raw substring code拋出：

```text
LIST QA PDF is missing required text
```

記錄實際第一個 failure。若 red來自字型、PDF geometry、insufficient text或fixture
readback不符，先修正test-only fixture；只有 public seam 因 raw substring 拋 missing-text
才是有效primary red。

## Task 2：最小 aggregate comparison green

### Production change

只修改 `src/travel_briefing/word_qa.py`：

1. 新增一個private helper，語意固定為 `"".join(value.split())`；
2. 在page loop、A4、readability與no-image checks全部通過後，為`whole_text`建立一份
   whitespace-free comparison copy；
3. 每個`required_text` value只在presence comparison時使用自己的compact copy；
4. missing collection仍保留原始value並沿用`dict.fromkeys()`的caller-order／
   original-value dedupe；
5. 不把helper用於continuation、day token、day-page mapping或任何output／diagnostic。

不得加入regex、Unicode normalization、case folding、punctuation removal、fallback、schema
變更或new public API。

### Green commands

先重跑Task 1 command，必須轉綠，再執行既有missing-token control：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_matches_required_text_across_layout_whitespace" `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_reports_missing_required_text_once_in_input_order" -q
```

兩個都必須通過。existing error message、original missing tokens、order、dedupe以及不洩漏
matched／full PDF text的assertions不改。

## Task 3：whitespace-only expected token red→green

### Validation red

新增：

```text
test_pdf_inspection_rejects_whitespace_only_required_text
```

用既有有效A4 PDF，將`required_text`設為只含space、tab與newline的單一字串。只透過
`inspect_list_pdf()`要求：

```text
ValueError: LIST PDF QA requires non-empty expected text
```

### Red command

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_rejects_whitespace_only_required_text" -q
```

在Task 2 matching change後，empty compact token會錯誤地被視為存在，因此此test必須先
因沒有raise而紅。若它意外已紅在其他setup錯誤，先修正fixture。

### Minimal validation green

擴充現有`required_text` input validation：任何value不是string、原始empty，或private
helper處理後empty，全部使用既有safe message fail closed。validation必須在
`fitz.open()`前完成。

重跑Task 3 command並要求轉綠，再合跑Tasks 1–3三個targets。

## Task 4：strict-content與page-local non-change controls

這些是對核准unchanged behavior的characterization／regression controls，不驅動新的
production分支。

### Non-whitespace strictness

新增parametrized public-seam test：

```text
test_pdf_inspection_layout_whitespace_tolerance_preserves_content_strictness
```

至少包含兩個fixed literal cases：

- PDF少一個non-whitespace Chinese character；
- PDF punctuation與required token不同。

兩者都必須raise既有missing-text error，且
`missing_required_text == (original_required_token,)`。test不得呼叫private helper計算
expected value。

### Continuation raw strictness

新增：

```text
test_pdf_inspection_does_not_apply_aggregate_whitespace_tolerance_to_continuation
```

建立兩頁synthetic LIST PDF；第二頁identity/header只透過layout whitespace才能與
`continuation_required_text`相等。要求仍以既有continuation error fail closed。這證明
aggregate helper沒有被重用到page-local checks。

day token／day-page mapping沿用既有tests，不新增新的production seam。

### Focused command

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_matches_required_text_across_layout_whitespace" `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_rejects_whitespace_only_required_text" `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_layout_whitespace_tolerance_preserves_content_strictness" `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_does_not_apply_aggregate_whitespace_tolerance_to_continuation" `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_reports_missing_required_text_once_in_input_order" `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_validates_every_page_and_day_mapping" `
  "tests\unit\travel_briefing\test_word_qa.py::test_pdf_inspection_blocks_missing_continuation_identity_or_wrong_day_page" -q
```

全部綠後執行完整PDF／Word QA unit file：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_word_qa.py -q
```

failed-evidence token／generic／collision／rollback與successful publication controls必須全綠；
不得為了新test改舊assertions、error schemas或publication behavior。

## Task 5：unchanged controls與scope proof

### Direct unchanged tests

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_local_backend.py `
  tests\unit\travel_briefing\test_word_list.py `
  tests\unit\travel_briefing\test_windows_word.py -q
```

這些tests維持workflow required-text composition、dynamic service-fee、Word patch、QR、font、
paragraph與pagination contracts。不得修改它們或放寬assertions。

### Static changed-file audit

```powershell
git diff --name-only $listWhitespaceBaseline
git diff --exit-code $listWhitespaceBaseline -- `
  src/travel_briefing/workflow.py `
  src/travel_briefing/errors.py `
  src/travel_briefing/word_list.py `
  scripts/briefing/patch_list_template.ps1 `
  scripts/briefing/render_list_template.ps1 `
  tests/unit/travel_briefing/test_local_backend.py `
  tests/unit/travel_briefing/test_word_list.py `
  tests/unit/travel_briefing/test_windows_word.py `
  tests/integration/travel_briefing/test_word_list_integration.py
git diff --check
```

implementation changed files只允許：

```text
src/travel_briefing/word_qa.py
tests/unit/travel_briefing/test_word_qa.py
```

計畫／STATUS只在handoff階段另行計入。任一unchanged control有diff就停止，不自動restore
使用者變更。

再以source scan確認production沒有新增external integration、retry或schema wiring：

```powershell
rg -n "RUN_BRIEFING_WORD_INTEGRATION|DispatchEx|win32com|NewAmazing|JMA|LINE|Cowell" `
  src/travel_briefing/word_qa.py
rg -n "compact|split\(\)|required_text|continuation_required_text|day_tokens" `
  src/travel_briefing/word_qa.py tests/unit/travel_briefing/test_word_qa.py
```

第一個scan不得有new hits；第二個scan只用於人工核對helper僅進入aggregate path，不能把
hit count本身當通過證據。

## Task 6：完整離線驗證與implementation commit

### 環境與suite

先確保Word opt-in未設定：

```powershell
Remove-Item Env:RUN_BRIEFING_WORD_INTEGRATION -ErrorAction SilentlyContinue
$winwordBefore = (Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
.\.venv\Scripts\python.exe -X utf8 -m pytest
$suiteExit = $LASTEXITCODE
$winwordAfter = (Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
```

要求suite exit 0、integration Word tests保持opt-in skip、WINWORD before／after一致。若
WINWORD count改變，停止並回報，不terminate process掩蓋原因。

再執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
git status --short --branch
```

記錄focused test、完整`test_word_qa.py`、direct unchanged、full suite的pass／skip count與
duration，以及compile、diff、scope、WINWORD evidence。所有數字由command輸出取得，不
心算。

全部通過後才建立implementation commit：

```text
fix(briefing): ignore LIST PDF layout whitespace
```

commit只允許兩個implementation files。不得把plan／STATUS混入implementation commit。

## Task 7：handoff與停止

完整離線實作與verification通過後：

1. 更新本計畫status，寫入implementation baseline、實際red／green原文、test counts、
   durations、changed-file audit、WINWORD evidence與implementation commit SHA；
2. 更新`STATUS.md`的一句話現況／做了什麼／下一步／阻塞點；
3. 建立documentation handoff commit；
4. 確認working tree乾淨；
5. 停止，不push、不執行Word。

若任何focused或full-suite test失敗，先在核准兩檔內診斷；若需要擴張範圍就停止等待
新設計。不得弱化、skip、刪除test，或以Word run取代offline failure。

完成後的唯一下一個可建議關卡是新的4天one-shot Word repro authorization。離線綠燈
本身不能宣稱「給連結即可穩定產生說明會資料」。

## 4. Completion checklist

- [ ] implementation preflight clean，baseline與WINWORD狀態已記錄；
- [ ] public-seam layout-wrap primary test先以missing-text紅，再轉綠；
- [ ] production helper只做Python Unicode whitespace removal；
- [ ] whitespace-only required token test先紅，再以input validation轉綠；
- [ ] genuinely missing／punctuation-drift token仍fail並回報原始值；
- [ ] continuation與day-page checks維持strict；
- [ ] missing-token order／dedupe與failed-evidence schemas不變；
- [ ] 完整`test_word_qa.py`與direct unchanged controls全綠；
- [ ] implementation changed files精確只有兩個核准檔案；
- [ ] full suite、compile、diff與scope gates全綠；
- [ ] WINWORD before／after一致且Word opt-in未設定；
- [ ] implementation與documentation commits分離；
- [ ] private master、calibration、adapters、workflow與integration selector未修改；
- [ ] 未push、未跑Word、未使用任何external integration。

## 5. Review gate

本計畫必須由OP核准後才能修改production或tests。核准本計畫只授權離線實作與離線
verification，不授權Word、private master、GET、push或其他external integration。

精確下一授權文字：

```text
同意此實作計畫，開始離線實作
```
