# LIST dynamic service-fee notice implementation plan

日期：2026-08-19

狀態：書面規格已由 OP 核准；本計畫等待 OP 核准後才可執行離線實作。

依據：
docs/specs/2026-08-19-list-service-fee-day-count-design.md

設計基線 commit：
6e3c27d3170e89597367931d0855e7e801a9c2f0

## 1. 目標與已知證據

只修正 canonical LIST master 內固定 6 天服務費正文，讓每份生成副本依
BriefingDraft.product.day_count 產生正確的中文天數與總額。

核准規則固定為：

- 每人每天新台幣 300 元；
- product.day_count 是唯一 day-count authority；
- 總額只由 day_count * 300 計算；
- 天數以繁體中文數字呈現，不建立 4／5／6／7／8／12 天白名單；
- 金額使用千分位，核准樣式為「新台幣 1,200 元」；
- 不修改或重校準私人 master。

唯一一次 4 天 Word run 已成功完成 layout QA，但同次 PDF 仍包含固定：

~~~text
六天共新台幣 1,800 元
~~~

且沒有預期的：

~~~text
四天共新台幣 1,200 元
~~~

目前 plan schema 3 只支援 header paragraphs 與 table cells。此次新增一個 typed、
main-story-only、exact-source、outside-table body paragraph patch；不能用全文件
ReplaceAll 或模糊的「六天／1,800」搜尋取代。

## 2. 授權範圍與停止點

核准本計畫只授權修改下列 production files：

- src/travel_briefing/word_list.py；
- scripts/briefing/patch_list_template.ps1；
- src/travel_briefing/workflow.py。

只授權修改下列 behavior／contract tests：

- tests/unit/travel_briefing/test_word_list.py；
- tests/unit/travel_briefing/test_windows_word.py；
- tests/unit/travel_briefing/test_local_backend.py。

另可更新本計畫、核准規格狀態與 STATUS.md，執行純離線 tests、PowerShell parser、
compileall、靜態／non-change checks 與 git diff --check，並建立本機 implementation
與 handoff commits。

下列是明確 unchanged controls：

- src/travel_briefing/word_qa.py；
- scripts/briefing/render_list_template.ps1；
- src/travel_briefing/list_calibration.py；
- src/travel_briefing/template_contract.py；
- src/travel_briefing/models.py；
- tests/unit/travel_briefing/test_word_qa.py；
- tests/unit/travel_briefing/test_artifact_store.py；
- tests/integration/travel_briefing/test_word_list_integration.py；
- tests/integration/travel_briefing/test_workflow.py；
- package／workflow version files、private master、calibration manifest 與 installed
  runtime。

若實作證明必須修改上述 unchanged control，立即停止並回到 scope review；不得順手
擴張。

本計畫不授權：

- 讀取或修改 private master、calibration 或既有 DRAFT；
- 啟動 Word COM、執行 Word repro、開啟 GUI 或產生 DOCX／正式 PDF／PNG；
- 設定 RUN_BRIEFING_WORD_INTEGRATION=1；
- NewAmazing／JMA GET、Yating、ffmpeg、安裝／下載、LINE、Cowell、deploy、publish、
  push 或任何外部寫入。

完整離線驗證通過後停止。新的實機 Word 驗證仍需另一個精確的一次性授權；成功或
失敗都不得在同一授權下重試。

## 3. 版本與資料契約

### 升版

- LIST_WORD_GENERATOR_VERSION：list-word/3 -> list-word/4；
- ListPatchPlan.schema_version：3 -> 4；
- PowerShell patch report schema：3 -> 4。

### 新 plan 欄位

ListPatchPlan.body_paragraphs 必須恰有一個 typed entry：

~~~text
field_id = "service_fee_notice"
anchor_prefix = "2. 本行程不接受在台灣事先支付導遊司機的服務費"
expected_source_text = canonical full source paragraph
text = complete generated target paragraph
~~~

### 新 report／result evidence

- patch report 新增 patched_body_paragraph_count = 1；
- ListWordBuildResult 保存同一欄位；
- Python strict report reader 要求 exact schema-4 key set、value type 與 exact count 1。

### 保持不變

- outer Word job schema 1；
- calibration schema 2 與 list-calibration/2；
- persisted WordRenderEvidence schema 3；
- QA index schema 2；
- travel briefing package／workflow version 0.2.1；
- old artifact-store fixtures 可繼續保存 list-word/3 作歷史 compatibility data，
  不批次改寫。

版本邊界由新的 LIST generator version 表示；本輪不是 package release，也不安裝或同步
runtime，因此不碰 package version。

## Task 1：建立 formatter 與 typed plan primary red tests

### 檔案

- 修改 tests/unit/travel_briefing/test_word_list.py

### 開工 preflight

離線實作開始先記錄：

~~~powershell
git status --short --branch
git pull --ff-only
$listServiceFeeBaseline = git rev-parse HEAD
if ($env:RUN_BRIEFING_WORD_INTEGRATION -eq "1") { throw "WORD_INTEGRATION_OPT_IN_MUST_BE_DISABLED" }
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
~~~

working tree 必須乾淨，HEAD 必須包含本計畫與核准規格。若 pull 帶入新 commit 且碰到
六個核准 implementation files，先重新比對計畫；若有未知 local changes，保留並停止，
不覆蓋。

### Primary formatter tests

使用 module import 避免 missing symbol 讓整個 test file collection 中止。新增：

1. exact examples：1、4、5、6、7、8、10、11、12、20、21 天；
2. 每例斷言中文天數、day_count * 300、千分位與完整 notice；
3. deterministic loop 1..366，要求非空中文 day text、正確總額，且輸出不包含
   「待 OP 確認」；
4. bool、0、負數與非 int 直接 input 必須 ValueError；
5. 測試不得用與 production 相同的 lookup table 重算 expected 中文文字。

### Typed plan test

擴充既有 arbitrary-day plan test並新增 focused assertion：

- schema 4、list-word/4；
- body_paragraphs 恰有一筆；
- field_id、anchor prefix、完整 canonical source text exact；
- target 由該 draft 的 day count 生成；
- target 與 source 不同；
- target 不含 CR、LF、BEL 或 vertical-tab Word marker；
- 4 天 target 包含「四天共新台幣 1,200 元」，12 天 target 包含
  「十二天共新台幣 3,600 元」。

### Red command

~~~powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest "tests\unit\travel_briefing\test_word_list.py::test_service_fee_notice_formats_positive_day_counts_without_duration_allowlist" "tests\unit\travel_briefing\test_word_list.py::test_service_fee_notice_rejects_invalid_day_counts" "tests\unit\travel_briefing\test_word_list.py::test_patch_plan_contains_one_dynamic_service_fee_body_paragraph" -q
~~~

預期 current code 因沒有 formatter／body_paragraphs 而紅。記錄實際第一個 failure；若
意外全綠，先確認 test 是否真的要求 schema 4 與 4 天／1,200 exact target，不直接改
production。

## Task 2：實作純 Python formatter 與 schema-4 plan

### 檔案

- 修改 src/travel_briefing/word_list.py

### Constants 與 pure formatter

新增單一 authority constants：

- NTD 300 daily rate；
- service_fee_notice field ID；
- exact anchor prefix；
- complete canonical source paragraph；
- static target prefix／suffix。

新增 deterministic Traditional Chinese integer formatter與完整 notice formatter：

1. 拒絕 bool、非 int 與 <= 0；
2. 不設定最大 trip length；
3. 不以 common duration dict 或 if day_count in (...) 實作；
4. 用 place-value／section algorithm處理中文零、十、百、千與更高位；
5. total 只計算一次 day_count * 300；
6. 金額用 Python deterministic comma formatting；
7. 回傳完整 paragraph，不讀日期、web notice、OP field、locale 或 environment。

實作時先用 1..366 loop 驗證沒有空字串、Arabic day fallback、leading／duplicate zero 或
common-duration branch。更大正整數走同一 algorithm，不另設錯誤白名單。

### Typed patch 與 plan validation

新增 immutable BodyParagraphPatch dataclass與 to_dict()，並把 body_paragraphs 加入
ListPatchPlan／serialized plan。

plan builder只建立一筆 service-fee patch。新增 validator要求：

- tuple exact length 1；
- field ID、anchor、source、target exact/non-empty；
- source與target不同；
- target exact包含 daily rate、中文天數與總額一次；
- source／target不得含 CR、LF、BEL、vertical tab；
- plan schema 4與generator list-word/4。

重新執行 Task 1 command，三個 tests 必須轉綠。此時只跑 pure plan tests；build／report
contract會在下一 Task一起升版，尚不建立 commit。

## Task 3：建立 patch report red 並完成 Python schema-4 evidence

### 檔案

- 修改 tests/unit/travel_briefing/test_word_list.py；
- 修改 src/travel_briefing/word_list.py。

### 先更新 synthetic report fixture

讓 SyntheticWordAdapter 預設寫：

- report schema 4；
- patched_body_paragraph_count = len(job["plan"]["body_paragraphs"])。

允許 test 明示覆寫 report schema與body patch count，以建立 negative controls；不要讓
fixture自動修正 production輸入。

更新 test_build_list_word_uses_a_temp_job_and_publishes_exclusively 斷言：

- plan JSON是schema 4／list-word/4且只有一個body patch；
- result generator_version == list-word/4；
- result patched_body_paragraph_count == 1；
- 既有page、QR、font、title、cell paragraph、hash與exclusive cleanup assertions不變。

新增 report fail-closed cases：

- schema 3；
- missing body count；
- body count bool、0或2；
- extra unknown key。

全部必須拒絕 publish output DOCX。

### Report red command

~~~powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest "tests\unit\travel_briefing\test_word_list.py::test_build_list_word_uses_a_temp_job_and_publishes_exclusively" "tests\unit\travel_briefing\test_word_list.py::test_word_report_requires_exactly_one_service_fee_body_patch" -q
~~~

預期 current report reader仍要求schema 3／舊key set而紅。若先停在fixture shape，修正
test setup；不得放寬 strict reader。

### 最小 Python report change

- ListWordBuildResult 新增 patched_body_paragraph_count；
- _read_patch_report() 要求schema 4、exact新key與exact int 1；
- build_list_word() 傳入 expected body patch count並映射result；
- schema 3不fallback、不自動補1；
- 不改outer job schema、inspection、pagination、QR、font、title或cell evidence。

重新執行report command與整個test_word_list.py，全部綠後建立第一個implementation
commit：

~~~text
feat(briefing): define dynamic LIST service fee plan
~~~

## Task 4：建立 PowerShell bounded body-patch red contracts

### 檔案

- 修改 tests/unit/travel_briefing/test_windows_word.py

### Schema／function source tests

把既有patch schema test更新為schema 4／list-word/4／report body count 1，保留所有
QR、12 pt、title與cell evidence assertions。

新增 source-contract tests，要求未來helpers具備：

1. WdMainTextStory = 1 與 WdWithInTable = 12 constants；
2. 只從 Document.StoryRanges.Item(WdMainTextStory).Paragraphs 列舉；
3. candidate只由exact approved anchor prefix辨識；
4. source階段的0／multiple／changed／in-table／invalid-range安全碼；
5. visible duplicate range只退一個paragraph mark position；
6. range assignment只發生在通過complete source equality之後；
7. 不使用ReplaceAll、wildcard replace、header/footer或table search；
8. post-reopen再次要求唯一target、outside-table、paragraph mark與unchanged main-story
   paragraph count；
9. post-reopen missing／multiple／changed／count-changed安全碼；
10. mutation順序為source inspect -> table/header patches -> service-fee patch -> font／
    pagination -> SaveAs/reopen -> service-fee assertion -> report。

測試以function source邊界為單位，不以整檔不精確的substring count取代實際contract。

### Red command

~~~powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest "tests\unit\travel_briefing\test_windows_word.py::test_service_fee_body_patch_is_main_story_exact_and_bounded" "tests\unit\travel_briefing\test_windows_word.py::test_service_fee_body_patch_revalidates_after_reopen" "tests\unit\travel_briefing\test_windows_word.py::test_patch_action_requires_schema_four_and_reports_service_fee_evidence" -q
~~~

預期 current adapter因helpers不存在、仍接受schema 3且沒有report field而紅。若test只因
舊test name不存在，先確認node IDs；不得把collect error當成behavior red。

## Task 5：實作 bounded Word正文patch與schema-4 report

### 檔案

- 修改 scripts/briefing/patch_list_template.ps1

### Plan validation

Invoke-Patch 只接受schema 4、list-word/4，並要求：

- body_paragraphs.Count -eq 1；
- 唯一field ID為service_fee_notice；
- anchor、expected source、target皆非空；
- target與source不同；
- 不接受額外body patch或未知ID。

invalid plan只回 LIST_SERVICE_FEE_PLAN_INVALID，不輸出plan text。

### Exact main-story locator

新增bounded locator helper：

1. 取得main story paragraph collection；
2. 複製每個paragraph range並排除exact一個paragraph mark；
3. 若range empty、end<=start或末端不是paragraph boundary，回range error；
4. 只以case-sensitive approved prefix建立candidates；
5. 要求candidate count exactly 1；
6. 以Range.Information(WdWithInTable)拒絕table-contained候選；
7. source phase要求完整visible text exact等於expected_source_text；
8. post-reopen phase要求完整visible text exact等於target；
9. 所有COM duplicate／paragraph／story objects在finally bounded release。

不得把private正文、路徑、COM exception或全文寫入safe diagnostic。

### Replacement與postcondition

在source inspection與既有header/table patches成功後：

- 記錄main-story paragraph count；
- 取得唯一verified visible duplicate；
- 只設定duplicate Text = patch.text；
- 立即重新定位並驗證target exact；
- 不插入／刪除paragraph，不碰paragraph mark，不改master。

現行Set-ListOutputFontContract接著把notice納入12 pt non-title契約，之後才pagination與
SaveAs。

reopen output DOCX後，在寫report前：

- 重新跑target locator；
- 確認source fixed paragraph沒有survive；
- 確認main-story paragraph count不變；
- 既有presentation assertion同時證明notice visible chars是12 pt；
- report寫schema 4與patched_body_paragraph_count = 1。

### Safe codes

精確實作核准規格中的：

- LIST_SERVICE_FEE_PLAN_INVALID；
- LIST_SERVICE_FEE_SOURCE_PARAGRAPH_MISSING；
- LIST_SERVICE_FEE_SOURCE_PARAGRAPH_MULTIPLE；
- LIST_SERVICE_FEE_SOURCE_PARAGRAPH_CHANGED；
- LIST_SERVICE_FEE_RANGE_INVALID；
- LIST_SERVICE_FEE_SOURCE_IN_TABLE；
- LIST_SERVICE_FEE_POST_REOPEN_MISSING；
- LIST_SERVICE_FEE_POST_REOPEN_MULTIPLE；
- LIST_SERVICE_FEE_POST_REOPEN_CHANGED；
- LIST_SERVICE_FEE_PARAGRAPH_COUNT_CHANGED。

### Green與parser

重新執行Task 4 command，再執行：

~~~powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests\unit\travel_briefing\test_windows_word.py tests\unit\travel_briefing\test_word_list.py -q
powershell -NoProfile -Command "$errors=$null;$tokens=$null;[Management.Automation.Language.Parser]::ParseFile('scripts\briefing\patch_list_template.ps1',[ref]$tokens,[ref]$errors)>$null;if($errors.Count){$errors;exit 1};'PARSER_ERROR_COUNT=0'"
~~~

兩檔focused tests與parser全綠後建立第二個implementation commit：

~~~text
fix(briefing): patch dynamic LIST service fee notice
~~~

## Task 6：建立 PDF required-text workflow red並最小接線

### 檔案

- 修改 tests/unit/travel_briefing/test_local_backend.py；
- 修改 src/travel_briefing/workflow.py。

### Backend composition red

更新synthetic ListWordBuildResult fixture：

- generator version list-word/4；
- patched_body_paragraph_count = 1；
- 其他page、QR、font、title、paragraph與hash evidence不變。

擴充test_local_backend_composes_existing_word_build_and_qa，要求QA kwargs的
required_text exact包含：

1. product code；
2. 所有非空flight numbers；
3. 由同一pure formatter產生的完整service-fee paragraph。

保持dict.fromkeys去重語意與既有continuation required text、day tokens、pdftoppm、
master／calibration assertions。

### Red command

~~~powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest "tests\unit\travel_briefing\test_local_backend.py::test_local_backend_composes_existing_word_build_and_qa" -q
~~~

預期 current workflow只傳product code與flight number，因缺service-fee paragraph而在
exact assertion紅；不得透過放寬test為in而掩蓋ordering／duplicate drift。

### 最小workflow change

- 從word_list.py匯入同一notice formatter；
- 在現有required_text tuple最後加入完整calculated notice；
- 不在workflow重算中文數字或費率；
- 不改inspect_list_pdf()、word_qa.py、page count、day map、PNG/index或evidence schema。

重新執行backend command必須轉綠，再跑整個test_local_backend.py。建立第三個
implementation commit：

~~~text
fix(briefing): require dynamic service fee in LIST PDF
~~~

## Task 7：focused regression、compatibility與non-change proof

### 核准focused files

~~~powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests\unit\travel_briefing\test_word_list.py tests\unit\travel_briefing\test_windows_word.py tests\unit\travel_briefing\test_local_backend.py -q
~~~

### 直接相關unchanged controls

~~~powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests\unit\travel_briefing\test_word_qa.py tests\unit\travel_briefing\test_artifact_store.py tests\integration\travel_briefing\test_workflow.py -q
~~~

test_artifact_store.py中刻意存在的old list-word/3歷史fixture不得批次改成4；本次schema
bump只影響新patch plan/report/generator。

### Word opt-in與process control

~~~powershell
if ($env:RUN_BRIEFING_WORD_INTEGRATION -eq "1") { throw "WORD_INTEGRATION_OPT_IN_MUST_BE_DISABLED" }
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
~~~

前後只讀process count；不啟動、終止或接管既有WINWORD。不得執行Word integration
selector，連4天也不跑。

### Static safety audit

~~~powershell
rg -n "service_fee|body_paragraphs|list-word/4|schema_version|patched_body_paragraph_count|required_text" src\travel_briefing\word_list.py src\travel_briefing\workflow.py scripts\briefing\patch_list_template.ps1 tests\unit\travel_briefing\test_word_list.py tests\unit\travel_briefing\test_windows_word.py tests\unit\travel_briefing\test_local_backend.py
rg -n "ReplaceAll|wdReplaceAll|private\\list-calibration|EASYTRAVEL_LIST_TEMPLATE_PATH" src\travel_briefing\word_list.py src\travel_briefing\workflow.py scripts\briefing\patch_list_template.ps1
~~~

第一個command人工確認source->plan->Word->report->PDF chain只有一個authority。第二個
command不得在新增service-fee functions／paths中出現global replacement或private path；
既有無關字串若存在，必須以baseline diff證明不是本輪新增。

### Baseline changed-file audit

以$listServiceFeeBaseline驗證production／test changed files精確為六個核准檔。下列
unchanged files diff必須為零：

~~~powershell
git diff --exit-code $listServiceFeeBaseline -- src/travel_briefing/word_qa.py scripts/briefing/render_list_template.ps1 src/travel_briefing/list_calibration.py src/travel_briefing/template_contract.py src/travel_briefing/models.py tests/unit/travel_briefing/test_word_qa.py tests/unit/travel_briefing/test_artifact_store.py tests/integration/travel_briefing/test_word_list_integration.py tests/integration/travel_briefing/test_workflow.py src/travel_briefing/__init__.py tests/unit/test_briefing_packaging.py
~~~

若focused／parser／compatibility／non-change failure需要修改核准六檔之外的production或
tests，立即停止；不更新計畫後偷渡修正。

## Task 8：完整離線驗證與implementation handoff

### 完整驗證

確認Word opt-in仍未開啟後執行：

~~~powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q src tests
git diff --check
~~~

最近一次已記錄完整suite為557 passed、8 skipped、45.89s。新tests會增加passed數；
此數字只作趨勢參考，回報一律貼未修改的實際輸出，不為符合預估而skip、刪除或弱化
tests。

完整suite若意外嘗試Word、private calibration、network或dependency download，立即停止。
任何失敗只在核准六檔內做最小修正並重跑相同比例驗證；若超出scope則停止詢問。

### Final diff review

~~~powershell
git diff $listServiceFeeBaseline -- src/travel_briefing/word_list.py scripts/briefing/patch_list_template.ps1 src/travel_briefing/workflow.py tests/unit/travel_briefing/test_word_list.py tests/unit/travel_briefing/test_windows_word.py tests/unit/travel_briefing/test_local_backend.py
git status --short --branch
~~~

人工確認：

- 沒有duration whitelist、date-derived day count或web/OP fee override；
- full canonical source equality發生在mutation前；
- paragraph mark只退一個range position且沒有table cell算法混用；
- source與post-reopen safe codes不混淆；
- body paragraph count與12 pt postcondition仍在；
- PDF required text用同一formatter；
- QR、title、cell、pagination、PDF page authority與no-retry contracts未弱化；
- 沒有private text dump、path、COM exception或source內容寫入diagnostic。

### Handoff

更新本計畫狀態、原規格狀態與STATUS.md，記錄：

- implementation baseline、pull、working tree、Word opt-in與WINWORD baseline；
- 每個primary red的實際錯誤與green command；
- 三個implementation commits與changed-file scope；
- focused、parser、compatibility、non-change、完整suite、compileall、static audit與
  git diff --check的實際輸出；
- generator／plan／report升版與unchanged evidence/package schemas；
- 未讀寫private master/calibration，未啟動Word或外部integration；
- 4天實機notice仍未經新Word artifact驗證。

建立本機handoff commit：

~~~text
docs: record dynamic LIST service fee handoff
~~~

最後執行：

~~~powershell
git status --short --branch
git log -5 --oneline
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
~~~

working tree必須乾淨。本計畫不執行push；push與installed runtime同步都是另外的明確
授權關卡。

## OP implementation review gate

本計畫完成後必須由OP審閱。核准本計畫才可修改六個implementation files並跑純離線
驗證；仍不授權Word或任何外部integration。

精確下一句是：

~~~text
同意此實作計畫，開始離線實作
~~~
