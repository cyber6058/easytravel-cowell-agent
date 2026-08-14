# STATUS

## 一句話現況

說明會產生器 0.2.0 的 Gate I 已完成；真實 OP-choice worksheet 與 blank choice artifact
已由既有兩份 private-safe reports 純離線產生並驗證，decision table 仍為
`BLOCKED_MIXED_VALUE`；36 個 choices 已整理成 13 個 review groups，但尚未由 OP 選擇或
填寫，仍無 master／manifest／config。

## 這次做了什麼

- 2026-08-14 只讀真實 private-safe worksheet，依相同 decision family、component pattern、
  changed properties、三份 safe values 與 eligibility 將 36 decisions 整理成 13 個 OP
  review groups。沒有使用多數決、沒有選 base、沒有填 blank choices，也沒有新增 private
  artifact、啟動 Word 或進入 Gate C。

- 2026-08-14 經當次明確核准，只讀取唯一且 SHA-256 符合 STATUS 紀錄的
  `component-diagnosis.json` 與 `normalization-decision-table.json`，執行一次
  `prepare-list-normalization-choices`；未讀原始 LIST、未啟動 Word，也未執行 diagnosis
  或 calibration。
- 全新 private 目錄只含 `normalization-choice-worksheet.json`（60,473 bytes，SHA-256
  `5683469da2c788982b3b8145fdbf5cc2c3c58bb5630f34d2089bbe30268da517`）與
  `normalization-choices.blank.json`（5,975 bytes，SHA-256
  `43c81418254d6b7e15dfe56e6c66b16809cf7eb134492fb67de218fd0f6e61a4`）。
- 真實 worksheet 分類為 `BLOCKED_MIXED_VALUE`，含 36 decisions、7 derived audits、
  0 blockers、108 options；固定 sample-001／002／003，其中 1 個 sentinel option 標成
  ineligible。36 個 blank choices 全未填；unsafe filename/path/recommendation token 命中 0。
- 後驗重建驗證顯示 worksheet 與 blank artifact 均 exact match；兩份來源 report SHA-256
  維持不變，WINWORD process 0。private artifacts 未加入 Git。

- 2026-08-14 新增 strict decision-table reader 與
  `prepare-list-normalization-choices` 純離線 CLI；它只接受互相吻合的 component report
  與 decision table，在全新 private 目錄 exclusive-create worksheet 與 blank choices。
- Worksheet 固定使用 sample-001／002／003，只呈現 source/component SHA-256、changed
  properties 與 allowlisted numeric／enum／digest values；不含來源檔名、路徑或推薦，
  sentinel option 保留證據但標成 `eligible_as_base: false`。
- 本回合只用 synthetic artifacts，未讀既有 private reports、未啟動 Word、未執行
  diagnosis 或 calibration。targeted tests 為 `69 passed`；完整離線回歸為
  `494 passed, 3 skipped in 7.63s`，compileall 與 `git diff --check` 通過；venv 未安裝 Ruff。

- 從 Cowell CLI 0.3.2 以 allowlist 複製護照名單與既有訂單分房功能。
- CLI 只保留 doctor、auth、passports、rooms。
- 科威唯讀允許清單只保留此產品所需六個頁面。
- 新增範圍防回歸與真實模組入口測試；完整離線測試為 97 passed。
- Skill 驗證結果為 Skill is valid。
- 安裝包為 dist/EasyTravel-Cowell-CLI-0.3.2.zip，SHA256：
  dbbc92b772e15a9b0733be0c199e6579bac9043dfc32ca7851a0b1505e3c3e5f。
- GitHub repo 已驗證為 PRIVATE：
  https://github.com/cyber6058/easytravel-cowell-agent
- 初始功能 commit：a21e684（已推送至 origin/main）。
- 2026-08-08 完成旅遊產品說明會 Word 與語音產生器的逐段需求確認。
- 新設計固定 URL／PDF 來源優先、衝突阻擋、黃色「待 OP 確認」、JMA 天氣、
  Azure HsiaoChen／本機 Hanhan 語音備援，以及 OP 手動傳 LINE 的邊界。
- 設計文件：
  docs/specs/2026-08-08-travel-briefing-document-audio-design.md。
- 先前設計階段只有文件變更，未執行付費服務、LINE 傳送及真實產出。
- 本次重新執行完整離線測試：`97 passed in 15.32s`。
- 使用者已確認
  `docs/specs/2026-08-08-travel-briefing-document-audio-design.md`。
- 新增語音優先的分階段實作計畫：
  `docs/plans/2026-08-09-travel-briefing-document-audio-implementation-plan.md`。
- 原流程指定的 `writing-plans` Skill 本機未安裝，因此以同等的檔案／測試／commit
  粒度手動建立計畫；該計畫現已由使用者核准。
- 計畫自檢結果：11 tasks、11 commits、0 placeholders；完整離線測試為
  `97 passed in 5.96s`。
- 2026-08-09 完成 Task 1：新增隔離的 `src/travel_briefing/` 套件、不可變
  `BriefingDraft` 資料模型、schema version 1 JSON round trip、canonical
  `draft_id`、穩定 exit codes 及 `briefing` console entry point。
- `draft_id` 已以測試證明會隨來源雜湊、天氣、講稿雜湊或產生時間改變；未知狀態
  與內容遭竄改但 ID 未更新的 manifest 都會 fail closed。
- `briefing doctor --format json` 只做本機 PATH、Registry 與環境變數存在性檢查，
  不啟動 Word COM、不合成語音、不呼叫網路，且不回顯 Azure key／region 值。
- 實測專案 Python 3.14、Windows、Microsoft Hanhan Desktop、Word COM 註冊及
  `pdftoppm` 可偵測；ffmpeg 與 Azure Speech 環境變數目前未設定。Word 結果目前
  僅為 Registry 註冊檢查，不代表 Task 8 的限時 COM 實機 probe 已通過。
- 新增模型、CLI、manifest 防竄改、WinGet fallback、模組入口及 Cowell 隔離測試；
  最終完整離線回歸為 `105 passed in 4.95s`，`git diff --check` 通過。
- Task 1 已提交並推送：commit `30fd146`，本機與 `origin/main` SHA 一致。
- 2026-08-09 完成 Task 2 技術切片：新增 narration 分段與文字 SHA-256、最多兩行的
  frame-timed SRT、PCM WAV 驗證／串接、MP3 轉檔契約與本機能力模組。
- 新增 Windows Speech adapter 與 `scripts/briefing/synthesize_hanhan.ps1`；PowerShell
  command line 只接收 UTF-8 JSON 工作檔路徑，不接收講稿文字，使用
  `Microsoft Hanhan Desktop`、rate `-1`、44.1 kHz／16-bit／mono PCM。
- 真實 Hanhan integration test 已啟用實跑為 `1 passed`；一般完整離線測試會明確
  skip 此 opt-in 測試，最終 staged release gate 為
  `118 passed, 1 skipped in 4.30s`。
- unknown speech／ffmpeg 結果只執行一次，先檢查已產生片段／檔案大小再 fail closed；
  已有輸出會在 adapter 呼叫前拒絕覆蓋。
- 正式試聽資料位於 Git 忽略的
  `output/briefings/SYNTHETIC-HANHAN/20260809-task2-sample-v2/`，包含 WAV、SRT、
  TXT 與 metadata；內容為 105 字的純合成 fixture，無真實團號、姓名或電話。
- 試聽 WAV 實測為 1,322,530 frames、29.989342 秒、2,645,104 bytes；WAV SHA-256
  為 `a2a8631b29927a7a0ee7b2d5c05a2f128e5642fe52299231e2b0fb8563585b39`。
- sample-v2 QA 結果為 `RESULT: OK`：SRT 結尾與 frame 時間同為 29,989 ms、4 個
  段落邊界連續、WAV／SRT／TXT／canonical narration 共 4 個 hash 全相符。
- 使用者實際聆聽後判定 Hanhan 不自然且停頓明顯；量測四個句間長停頓為約
  820、970、890、970 ms，整篇一次 Hanhan 合成仍有相同停頓，因此不是 WAV
  串接額外插入的錯誤。
- 同稿本機 Yating 對照 WAV 已產生並解碼驗證：26.087250 秒、16 kHz、PCM
  16-bit／mono，SHA-256
  `d538b0a4d8d4f98d9bfc7758fbfbe720c6b868d249d6a43bed64b3e91851b519`；使用者判定
  Yating 較好。
- 使用者選定 Yating 為唯一自動本機聲音；目標電腦缺少 Yating 時阻擋音訊，
  不自動退回 Hanhan。使用者表示目前沒有 Azure Speech 資源，因此第一階段不建立、
  不設定也不呼叫 Azure。
- 已修訂 `docs/specs/2026-08-08-travel-briefing-document-audio-design.md`：Yating
  採整篇連續合成並以零時長 SSML bookmarks 建立 SRT；bookmark 或音檔驗證不符
  即 fail closed。
- 實機 probe 顯示 Yating 的自動 sentence／word boundary metadata 皆回傳 0 個
  marker，但 SSML `<mark>` 可正確回傳 `Speech:Bookmark`；三句測試取得兩個
  1,496 ms／3,026 ms markers，且有無 bookmarks 的 WAV byte count 同為 146,654。
- 使用者已書面確認 Yating 修訂設計；原實作計畫已改成 Yating-only 第一階段，
  新增 Task 2B 的連續 SSML bookmark 管線，並正式取消 Azure Task 7。
- 修訂計畫把下一個核准範圍限制為 Task 2B 的本機程式、離線／opt-in 整合測試及
  20–30 秒正式管線樣本；完整 6–8 分鐘音訊與外部關卡不隨計畫核准自動開啟。
- 計畫自檢為 12 個 Task headings（2 完成、1 取消、9 待執行）、11 個 commit
  邊界、0 個未定欄位，且 6 個舊 Azure／auto-Hanhan 可執行片語均不存在。
- 本次 Yating 計畫修訂後完整離線回歸為 `118 passed, 1 skipped in 5.12s`；skip
  仍是需顯式 opt-in 的真實 Hanhan integration test，沒有拿 skip 當 Yating 驗收。
- ffmpeg 未設定，因此 metadata 正確標示 `MP3_CONVERTER_UNAVAILABLE`；沒有安裝、
  沒有嘗試轉 MP3，已驗證的 WAV／SRT／TXT 均保留。
- 該 Yating 計畫修訂階段沒有 live 官網／JMA、Azure、LINE、Word COM 啟動或外部部署。
- 2026-08-09 使用者明確核准 Task 2B；以 TDD 完成 Windows Media Speech
  `Microsoft Yating` 整篇單次 SSML 合成，第二段起插入唯一 bookmark，並由真實
  `Speech:Bookmark` 時間建立連續 SRT。
- 新增 `windows_media_speech.py` 與 `synthesize_yating.ps1`；Python command line
  只帶 OS temp 中的 UTF-8 JSON job 路徑，PowerShell 僅精確選用
  `Microsoft Yating`／`zh-TW`，保留預設韻律，不呼叫 Hanhan、Azure 或網路。
- WAV 會實際解碼並要求 PCM、16-bit、mono、正取樣率與正 frame；取樣率不硬編碼。
  缺少、重複、未知、倒序、越界或經毫秒換算後無效的 bookmarks 一律阻擋 SRT，
  timeout／失敗只檢查暫存輸出一次，不重試也不 fallback。
- 最終 WAV／SRT／TXT／metadata 全部 exclusive create；metadata 記錄 voice、engine、
  WAV header、marker count、narration／artifact hashes，並明確標示
  `MP3_CONVERTER_UNAVAILABLE`。
- `briefing doctor` 實機只列舉 Windows Media `AllVoices`，已確認 Yating 可用；
  Hanhan 標為 `legacy_comparison_only`，已取消的 Azure 環境變數不再造成假 warning。
- opt-in 真實整合測試結果為 `1 passed`；最後完整離線回歸為
  `144 passed, 2 skipped in 6.85s`，兩個 skip 分別是需顯式 opt-in 的 Hanhan 與
  Yating 本機整合測試；`git diff --check` 通過。
- Task 2B 功能、測試與計畫狀態已提交於 commit `2fe8e7c`。
- Task 2B 自然度政策與人工驗收決策已提交於 commit `72e22c8`。
- 正式管線樣本位於 Git 忽略的
  `output/briefings/SYNTHETIC-YATING/20260809-task2b-sample-v1/`。獨立 QA 為
  `RESULT: OK`：26.087250 秒、16 kHz、PCM 16-bit／mono、417,396 frames、5 段
  SRT／4 bookmarks，SRT 與 WAV 結尾同為 26,087 ms。
- 新樣本 WAV SHA-256 為
  `d538b0a4d8d4f98d9bfc7758fbfbe720c6b868d249d6a43bed64b3e91851b519`，與使用者
  選中的 `02-Yating-local.wav` 完全相同；SRT SHA-256 為
  `75a936538f95f0ecfb234cab56a6c2eef3a3ce1f9defbf2f1e1bcffc49b97d67`。
- 使用者指出 14.925 秒起「不舒服」的「服」音調略怪，並確認不應針對單字改稿
  或累積發音特例。正式政策改為：不看逐字稿仍能理解且不改變意思的偶發怪腔可
  接受；聽不清、可能改變語意或誤認關鍵資料時才阻擋；跨樣本重現才升級為整體
  韻律／引擎評估。使用者已依此原則通過 Task 2B 人工驗收。
- Task 2B 階段仍未安裝 ffmpeg、未產生 MP3／完整 6–8 分鐘音訊、未啟動 Word COM，亦未
  呼叫 live 官網／JMA、Azure、LINE 或任何外部發布。
- 2026-08-09 使用者以「繼續進行」核准既定 Task 3；新增
  `script_policy.py`、`script_validation.py` 與 canonical narration policy reference，
  沒有修改 Yating 合成器或生成完整語音。
- `build_narration_input()` 由 `BriefingDraft` 產生固定八段與來源綁定的
  `required_facts`；核心涵蓋小費、人數、不可脫隊、巴士時數、保險、護照效期、
  房型、素食、電壓及天氣提醒。缺值、未知來源／分類、未確認 OP 欄位、未解衝突、
  BLOCKED 草稿與未知專名一律進 review，不補猜。
- `check_script()` 要求八個 exact markers 依序各出現一次，保護事實子句與所有關鍵
  日期／班號／時間／金額／人數／時數／效期／百分比／電壓，並阻擋相反語意、
  未核准數字及爭議值。驗證 JSON 不回吐講稿；序列化的禁用值只留 SHA-256 與字數。
- 合成前字數估計採已通過 Yating 短樣本的 3.6 可發音字元／秒，只是 warning；
  `validate_audio_duration()` 仍以實際 WAV 秒數判斷 360–480 秒。第一次過短／過長只
  允許固定規則補充／壓縮一次，第二次仍超界即 blocked 並轉人工 review。
- 發音表只涵蓋班號、機場代碼、日期、金額、電壓與大阪／東北／北海道常見地名；
  未知詞保留原字進 review。依使用者決策，沒有為「不舒服」的「服」或其他一般字
  建立逐字補丁。
- Task 3 功能 commit 為 `02f91c5`。完整離線回歸實測為
  `171 passed, 2 skipped in 5.66s`；兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests，Task 3 測試沒有 skip；compileall 與 staged
  `git diff --check` 均通過。
- 使用者於完成回報後明確回覆「通過」；Task 3 人工驗收已關閉。這項通過當時不包含
  Task 4、live 官網／JMA、完整 6–8 分鐘音訊或任何其他後續關卡。
- Task 3 階段沒有 live 官網／JMA request、Word COM、ffmpeg 安裝、MP3、完整 6–8 分鐘
  音訊、Azure、LINE、Cowell access 或任何部署／外部發布。
- 2026-08-09 經使用者核准完成說明會產生器 Task 4：新增 HTTPS
  `www.newamazing.com.tw` URL／redirect allowlist、語意式 NewAmazing HTML parser、
  保留頁碼的 PyMuPDF 文字擷取與 PDF parser，以及產品代碼唯一候選決策。
- NewAmazing parser 以產品資訊、航班資訊、每日行程及其他說明 anchor 定位；必要
  anchor 缺少時回報 `PARSE_CONTRACT_CHANGED`。無文字 PDF 回報
  `PDF_OCR_REQUIRED`，沒有暗中加入 OCR。
- Task 4 fixtures 只有合成 HTML 與去識別頁面文字；PDF extractor 測試使用測試期間
  產生的暫存 PDF。沒有提交來源 PDF、完整官網頁面或 live response。
- Task 4 的 34 個針對性測試通過；完整離線回歸實測為
  `205 passed, 2 skipped in 6.10s`。兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests；compileall、行寬檢查與 staged `git diff --check` 均通過。
- Task 4 依計畫只新增 `beautifulsoup4>=4.12,<5`；本機 venv 實裝 4.15.0。
  額外執行 `pip check` 時發現既有 `keyring` 依賴未安裝；這不是 Task 4 引入，且
  本次未擴充範圍補裝，完整測試仍全綠。
- Task 4 功能 commit 為 `cc547f9`。完成該離線 commit 時尚未對新魅力官網發出
  request，且 commit 不含來源頁面或 live response。
- 2026-08-09 使用者另行核准對已提供的大阪產品 URL 執行一次 live 唯讀契約測試。
  實際只發出 1 個 GET、沒有 redirect 或 retry；HTTP `200`、response `98,076`
  bytes、SHA-256 `06335de9cfee88e4a33248a6ead9950eaeebdab735ea2542806ca2ff8e3aaf61`。
- 該 live response 在「產品資訊」anchor 回報 `PARSE_CONTRACT_CHANGED`，因此真實
  URL 自動解析目前仍 blocked。沒有保存原始 HTML；單次 live 授權已用畢。
- 2026-08-10 經逐次明確核准完成最小 live 結構診斷：正式頁採
  `.product_basic_info`、`#ReferenceFlights`、`#DailyItinerary .every_day` 卡片契約，
  列印控制仍指向同一頁，沒有另一個穩定列印頁。每次授權只執行一個 GET，未保存
  原始 HTML、旅客資料或 live response。
- NewAmazing parser 已升為 `newamazing-html/2`：保留舊契約，新增嚴格卡片 profile，
  驗證產品名稱／代碼、URL 代碼、航班欄位與首末日期、每日天次、餐食、飯店及其他
  說明；必要欄位漂移仍回報 `PARSE_CONTRACT_CHANGED`。
- 正式頁沒有獨立的每日住宿城市欄位，parser 不從標題猜城市。URL-only 會留下
  `SOURCE_CITY_MISSING` warning；URL+PDF 會保留 PDF 城市供 OP 核對，不製造假衝突。
- 修復只加入純合成卡片 fixture，沒有把正式產品代碼、完整頁面、電話、email 或 PII
  寫入原始碼。修復後尚未再發出 live GET，因此不能宣稱正式 URL 已驗收可用。
- NewAmazing／merge 針對性測試為 `29 passed in 0.36s`；完整離線回歸實測為
  `244 passed, 2 skipped in 5.78s`。兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests；compileall、行寬檢查與 `git diff --check` 均通過。
- 卡片結構修復 commit `5e8fed9` 已於 2026-08-10 push 至 private `origin/main`。
- 2026-08-10 經使用者明確核准執行恰好一次修復後正式頁 GET；未跟隨 redirect、
  未 retry，HTTP `200`、response `98,468` bytes、SHA-256
  `2e7a3403a64706b0ab272c22ac2559b691b1048caf7e680149247b7ef9de5e68`。
  parser 已進入新版卡片 profile，但在「產品區域」回報
  `PARSE_CONTRACT_CHANGED`。沒有保存原始 HTML 或 live response；該次授權已用畢。
- 2026-08-10 使用者核准以 OP 明確確認取代產品代碼、航點或名稱猜測；設計已寫入
  `docs/specs/2026-08-10-travel-briefing-product-region-resolution-design.md`。規格固定
  URL-only 缺區域時使用動態 `product_region` OP 欄位、URL+PDF 保留 PDF 區域、
  未知或矛盾值 fail closed；使用者於 2026-08-11 明確回覆「通過」。
- 2026-08-11 依通過規格完成區域確認：NewAmazing／PDF parser 在來源未明示區域時
  保留空值、多區域仍 fail closed；merge 只建立一個 `SOURCE_REGION_MISSING` warning，
  由唯一有值的來源補足，或在兩者都缺時附加黃色 `product_region` OP 欄位；兩個
  非空區域不一致仍建立 blocking conflict。parser evidence 版本分別升為
  `newamazing-html/3` 與 `pdf-itinerary/2`。
- `apply_op_values()` 只在草稿已要求 `product_region` 時接受大阪／東北／北海道，
  更新產品與 OP provenance 並重算 `draft_id`；未知值及未要求的 override 均拒絕。
- 區域確認針對性測試為 `57 passed in 0.54s`；完整離線回歸實測為
  `258 passed, 2 skipped in 6.03s`。兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests；compileall、行寬檢查與 `git diff --check` 均通過。
- 設計與實作 commits `3aa59fe`、`239a713` 已於 2026-08-11 push 至 private
  `origin/main`，本機與遠端均為 `239a713` 後才執行正式頁驗證。
- 2026-08-11 經使用者明確核准執行恰好一次修復後正式頁 GET；未跟隨 redirect、
  未 retry，HTTP `200`、response `98,464` bytes、SHA-256
  `a4077429981bb47c6cbfccae113901a1b3d66b9a4cc069c35fa7e12a8470f216`。
  `newamazing-html/3` 實測解析 2 航班、5 天及 5 項其他說明，產品區域保留空值，
  merge 只建立 1 個 `SOURCE_REGION_MISSING` warning 與 1 個 `product_region` OP
  待確認欄位，狀態為 `DRAFT_READY`，結果 `PASS`。沒有保存原始 HTML 或 live
  response；該次 GET 授權已用畢。
- 2026-08-09 經使用者另行核准完成 Task 5：新增 `merge`、`validation`、`op_values`
  與 `review` seams，落實 PDF／官網 notices／天氣來源優先、blocking conflicts、
  語意等價 warnings，以及 9 個不得猜值的黃色 OP 待確認欄位。
- OP values 與 conflict decisions 都綁定當前 `draft_id`；過期決策 fail closed。
  決策會實際更新 scalar、航班或每日行程資料並重算狀態；review 保留 URL 或 PDF
  basename／頁碼／取得時間，同時遮蔽電話且不洩漏 PDF 目錄。
- Task 5 功能 commit 為 `2bba83f`。34 個針對性測試通過；完整離線回歸實測為
  `239 passed, 2 skipped in 9.67s`。兩個 skip 仍是真實 Hanhan／Yating integration
  tests；compileall、行寬檢查及 staged `git diff --check` 均通過。
- 本次沒有 JMA request、Word COM、ffmpeg 安裝、完整 6–8 分鐘音訊、Azure、LINE、
  Cowell access、部署或外部發布，也未保存任何 live 原始內容。
- 2026-08-11 經使用者明確核准，只讀查閱 JMA 官方產品目錄、XML 技術資料、
  PULL 型取得方式與使用條款；沒有抓取任何實際天氣預報電文。確認 Task 6 短期來源
  為 `VPFD51`、週間來源為 `VPFW50`，兩者從「定時」Atom feed 發現。
- Task 6 最小設計已寫入
  `docs/specs/2026-08-11-jma-weather-enrichment-design.md`：每日城市空白時不猜測，
  固定顯示「尚無短期預報，請於出發前更新」；城市只有唯一 alias 才可對應 JMA
  預報區，overlap 採 VPFD51，JMA 失敗降級但不破壞安全草稿。
- Task 6 設計 commit `10e587e` 與功能 commit `025611b` 已完成：新增標準庫 JMA
  XML parser、官方 HTTPS provenance、VPFD51／VPFW50 產品與時間軸驗證、日本日期
  換算、唯一大阪 alias／測站映射、短期與較新發布優先、矛盾 fail closed，以及
  城市缺漏或超出範圍的固定降級結果；沒有新增 JMA SDK 或網路 fetcher。
- Task 6 針對性測試實測為 `12 passed`；完整離線回歸為
  `270 passed, 2 skipped in 5.64s`。兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests；compileall、行寬檢查與 `git diff --check` 均通過。
- 本次實作只使用 synthetic XML，沒有實際 JMA 預報 request、live response、Word
  COM、ffmpeg 安裝、完整音訊、LINE、Cowell access、部署或外部發布。
- 2026-08-12 經使用者指示繼續開發後，完成 Task 8 的離線 LIST Word 基礎：新增
  `template_contract.py`、`word_list.py`、`word_qa.py`、Windows Word adapter、
  patch／render PowerShell scripts，以及需顯式 opt-in 的私有範本 integration test。
- LIST 契約驗證四表格、八個欄位錨點、合併格座標、四段標題、header QR
  candidate、單 section、A4 portrait 與不含團務／PII 文字的 layout fingerprint；
  5／6／7 天共用 master table 動態增減列，缺值保留黃色 `待 OP 確認`，安全縮寫後
  仍過長即 blocked，不截斷內容。
- Word adapter command line 只帶 OS temp job 路徑；所有權由 nonce、精確 WINWORD
  PID 與 process start time 綁定。逾時只檢查一次暫存輸出、不 retry、不掃描或停止
  其他 Word 程序。PowerShell scripts 為 ASCII-only，中文錨點只從 UTF-8 job 讀取。
- PDF／PNG QA 程式要求單頁 A4、必要文字、非空文字與至少一個圖片物件，再以明確
  設定的 `pdftoppm` 產生單張 150 DPI PNG；正式 DOCX 仍須逐頁人工看圖才能通過。
- Task 8 新增 39 個單元測試；針對性回歸為 `39 passed in 0.78s`，最終完整離線回歸為
  `309 passed, 3 skipped in 8.66s`。第三個 skip 是未授權的私有 LIST／Word
  integration；本次未啟動 COM、未讀私有範本、未產生任何正式 Word／PDF／PNG。
- Task 8 離線實作已本機提交為 `3b8c64a`；因 public remote 阻塞，尚未 push。
- 2026-08-12 接續檢查：`git pull --ff-only` 回傳 `Already up to date.`；本機比
  `origin/main` 多 4 個 commits（Task 6 與 public remote 阻塞紀錄），工作樹當時乾淨。
- 2026-08-12 由接手者重新執行完整離線回歸：`270 passed, 2 skipped in 8.56s`；
  compileall、Python 100 字元行寬檢查及 `git diff --check origin/main..HEAD` 通過，
  待推送範圍未發現產出檔、credentials 或旅客 PII。
- 2026-08-12 兩次 GitHub 即時唯讀查詢均顯示
  `cyber6058/easytravel-cowell-agent` 為 `PUBLIC`／`private: false`，與本專案必須
  private 的規則及先前 STATUS 紀錄矛盾；因此沒有 push，也沒有變更 repo visibility。
- 針對全部 28 個本機 Git commits 的唯讀歷史掃描未發現禁用 artifact 副檔名；3 個
  高可信 credential pattern 命中只位於 PII 掃描器規則與其遮蔽測試 fixture，不是
  實際 credential。這不是完整外洩鑑識，也不代表 repo 曾公開的風險已撤銷。
- 2026-08-12 依使用者指示不變更 GitHub visibility，繼續完成 Task 9 本機離線實作：
  新增受限來源 fetch、artifact store、strict local config、workflow orchestration、
  Word／Yating local backend，以及 `prepare`、`check-script`、`render` CLI。
- 每個 run 只能建立在 `output/briefings/<product-code>/<timestamp>/` 的全新目錄；
  manifest 與來源、artifact、口語稿均以 hash 綁定。部分 render 失敗保留安全 artifact
  並可從目前狀態重試；任意 BLOCKED 狀態、路徑漂移、hash 漂移與重複 artifact 均
  fail closed。
- `render --confirm-draft-id` 要求 exact draft ID、script hash、零 blocking conflict、
  零黃色必要欄位、Word PDF／PNG QA 與完整音訊 artifact；確認只在本機複製並移除
  `DRAFT` 檔名前綴，不重新 render、不傳 LINE、不上傳。
- 外部 HTML 僅可經 allowlisted HTTPS host、最多一次同 host redirect、無 retry 且
  5 MB 上限取得；raw response 只暫存於 OS temp，manifest 僅保存 hash 與證據。本次
  測試全用 synthetic data／mock transport，沒有送出 live request。
- Task 9 最終完整離線回歸為 `358 passed, 3 skipped in 8.51s`；三個 skip 仍是需明確
  opt-in 的 Hanhan、Yating 與私有 LIST／Word integration。compileall、
  `git diff --check`、staged 禁用產出路徑、PII 與 secret 掃描均通過。
- Task 9 程式已本機提交為 `e487db7`；使用者明確指示不改成 private，因此沒有變更
  visibility，也沒有向目前 public 的 `origin` push。
- 2026-08-12 完成 Task 10 本機離線實作：新增 canonical
  `easytravel-briefing-materials` Skill、byte-identical Codex／Claude copies、Codex
  plugin／local marketplace、獨立 briefing pyproject／installer、allowlist build 與
  packaging contract tests。安裝器先驗證必要路徑與範本 fingerprint，再建立自己的
  app／venv／config；不讀 Cowell session 或 credentials，也不覆蓋既有安裝。
- 正式 `render` CLI 測試鎖定只暴露 Yating；Hanhan 腳本不進安裝包。Skill 明確分開
  live source、私有範本／Word COM、Yating、ffmpeg、draft confirmation 與外部傳送關卡，
  並禁止猜值、雲端 TTS、自動 LINE、影片、部署與發布。
- 三份 Skill validator 皆回傳 `Skill is valid!`；plugin validator 回傳
  `Plugin validation passed`。PowerShell parser、compileall、行寬、`git diff --check`、
  staged artifact／PII／secret scan、ZIP allowlist 與 ZIP secret pattern scan 均通過。
- Task 10 最終完整離線回歸為 `365 passed, 3 skipped in 15.74s`；三個 skip 仍是需明確
  opt-in 的 Hanhan、Yating 與私有 LIST／Word integration tests。
- 本機套件為 `dist/EasyTravel-Briefing-Materials-0.1.0.zip`，SHA-256：
  `14db8cc9e7e8ce9c90eec37a62069b59f018f940674e795c18f88339b4ab93e5`；ZIP 有
  67 個 archive entries，未含 Cowell、credentials、私有來源、範本或生成 artifacts。
- Task 10 實作已本機提交為 `0daf457`。本次未安裝套件、未改 GitHub visibility、
  未 push，也未執行 live URL／JMA、私有範本、Word COM、Yating、ffmpeg 安裝、LINE、
  Cowell、部署或外部發布。
- 2026-08-12 經使用者明確核准 Task 11 第一關，只在新的 OS temp root 解壓及安裝
  `EasyTravel-Briefing-Materials-0.1.0.zip`；安裝時把 `LOCALAPPDATA`／`USERPROFILE`
  指向該 root，並使用 `-SkipCodexPluginInstall -SkipClaudeSkillInstall`，沒有改動使用者
  現有 Codex／Claude 設定。範本是當次建立的純 synthetic DOCX，沒有讀私有 LIST。
- ZIP SHA-256 重驗仍為
  `14db8cc9e7e8ce9c90eec37a62069b59f018f940674e795c18f88339b4ab93e5`；Python
  3.14 暫存 venv 成功安裝 briefing 0.1.0、Beautiful Soup 4.15.0、httpx 0.28.1、
  PyMuPDF 1.28.2 與其依賴，`pip check` 回傳 `No broken requirements found.`。
- 已安裝的 `briefing --version` 回傳 `briefing 0.1.0`；`render --help` 只暴露
  `--tts {yating}`。config 可從隔離的 `LOCALAPPDATA` 載入 synthetic `.docx`、output
  root、layout hash 與現有 `pdftoppm`；`cowell_cli` 不可匯入，且安裝包沒有 Hanhan
  script。
- 安裝器執行的 `doctor` 與後續 JSON probe 均實測 Python／Windows／Yating voice
  enumeration／Word registry／pdftoppm 為 ok；ffmpeg 未設定所以整體狀態為 warning。
  這不代表 Word COM 已啟動、Yating 已合成或 MP3 已驗收。
- 對同一隔離目錄重跑 installer 會以 exit 1 拒絕，訊息為 app already exists；app、
  config 與檔案數均保持不變，證明不覆蓋既有安裝。PyMuPDF 1.28.2 會印出既有
  `fitz` API 未來棄用 warning，未影響本次命令，但應在後續維護處理。
- 驗證後已刪除唯一的 temp root（1,524 files／253 directories）以及本次在 repo
  產生的 pip／PowerShell cache；沒有保留安裝、synthetic 範本或測試 config，也沒有
  live request、Word COM、語音合成、LINE、Cowell、部署、發布或 push。
- 2026-08-12 使用者採用新的全自動使用方式：提供新魅力 URL、行程 PDF 或兩者並
  要求「產生說明會資料」，同一次要求即可啟動該 `draft_id` 的受限來源讀取、私人
  LIST master、Word COM、Yating、pdftoppm 與已設定 ffmpeg DRAFT 管線；正常情況
  不再逐步詢問，只有缺值、衝突、契約漂移或 QA 失敗才集中回報。
- 新設計把三份 `.doc` 定位為一次性格式校準樣本；校準通過後只保留一份私人
  canonical master，依來源實際 N 天複製每日列，不再有 5／6／7 天範本選擇。
  內容在可讀性下限內放不下一頁時自動續頁，續頁重複團體識別與每日表頭，不能
  靠過度縮字、截字或刪除事實硬塞單頁。
- 書面規格為
  `docs/specs/2026-08-12-automatic-briefing-dynamic-list-design.md`；它在使用者複核
  後取代舊設計的 5／6／7 天限定與單頁即阻擋規則。規格自檢沒有 TODO／TBD，
  `git diff --check` 通過。本輪只寫文件，沒有讀取三份私有範本內容、啟動 Word
  COM／Yating、發出 live URL／JMA request、安裝 ffmpeg 或產生任何 artifact。
- 2026-08-13 使用者明確回覆「書面規格通過」；上述動態 LIST 規格正式關閉設計
  複核關卡，規格狀態已同步更新。
- 新增 `docs/plans/2026-08-13-automatic-briefing-dynamic-list-implementation-plan.md`：
  共 12 個 Task／12 個 commit。Task 1–8 是待核准的 repo 內離線程式、測試、Skill
  與 0.2.0 package；Task 9–12 分別是乾淨安裝、三份私有 LIST 校準、4／5／6／7／
  8／12 天 Word 視覺驗收，以及真實一次要求 DRAFT，各自保留獨立核准 gate。
- 計畫明確涵蓋 calibration schema 2、唯一 canonical master、任意正整數天數、
  內容驅動單頁嘗試、安全續頁、逐頁 PDF／PNG QA、nested artifact 驗證、0.1 config
  fail-closed migration，以及 packaged Agent 的一次 DRAFT 授權。
- 規劃前重跑完整離線基線：`365 passed, 3 skipped in 12.92s`；三個 skip 仍是需
  opt-in 的 Hanhan、Yating 與私有 LIST／Word integration。本輪沒有啟用任何一項。
- 2026-08-13 使用者核准 0.2.0 離線 Task 1–8；已依序完成 calibration schema 2、
  受限 Word adapter、任意天數 patch plan、內容驅動單頁／安全續頁、逐頁 QA 與
  artifact tracking、單一 master/manifest config、一次要求的一個 bounded DRAFT
  Skill 契約，以及 0.2.0 allowlist package。
- Task 1–7 本機 commits 為 `983c29b`、`a665643`、`6e76071`、`70763f3`、
  `31211e8`、`7998cb6`、`8fcb0a5`。Task 8 提交前的最終完整離線回歸為
  `437 passed, 3 skipped in 17.28s`；三個 skip 仍是既有 opt-in Hanhan、Yating 與
  私人 LIST／Word integration，沒有啟動或放寬。
- compileall、100 字元 production Python 行寬、六份 PowerShell parser、三份 Skill
  validator、plugin validator、Skill mirror hash、`git diff --check`、stage/ZIP 禁用
  副檔名與私人 marker scan 全部通過；scan 結果為 0 forbidden stage files、
  0 forbidden ZIP names、0 private marker/key hits。
- 0.2.0 套件為 `dist/EasyTravel-Briefing-Materials-0.2.0.zip`，SHA-256：
  `d0affb3403b0c622a74caf218182f46dd46ab6bb275ee6254710a3a0c7d818fc`；stage 有
  63 files、ZIP 有 68 entries，不含 `.doc`／`.docx`、來源 PDF、私人 calibration
  manifest、來源 hash、Cowell 或 Hanhan script。
- 2026-08-13 使用者另行核准 Gate I；開始前先以 `PIP_NO_INDEX=1` 建立兩個隔離
  preflight venv。`--no-build-isolation` 路徑回報
  `BackendUnavailable: Cannot import 'setuptools.build_meta'`；installer 同等的 build
  isolation 路徑回報 `No matching distribution found for setuptools>=75`。這證明
  0.2.0 的乾淨安裝需要該次網路下載，原 Gate I 核准沒有明示此權限，所以未自行
  連線、未開始正式安裝。兩個 probe 各有 869 files／134 directories，均已完整刪除；
  沒有讀私人 LIST、啟動 Word／Yating、寫入真實 LOCALAPPDATA／USERPROFILE 或 push。
- 2026-08-13 GitHub 即時重驗仍為 `PUBLIC`／`private: false`；使用者在收到明確警告
  後仍指示「直接push」。此動作違反私人產品只能推送到 private repo 的規則，依
  使用者當次明確要求執行；後續是否成功只以遠端 `main` SHA 為準，不以命令意圖
  冒充完成。push 前由彙整者親自重跑完整離線測試：
  `437 passed, 3 skipped in 20.65s`；`git diff --check` 通過，分支為
  `0 behind / 21 ahead`。
- 首次例外 push 實際輸出為 `c31876f..39d37d9  main -> main`；隨後以
  `git ls-remote origin refs/heads/main` 驗證遠端完整 SHA 為
  `39d37d92fa0e2ef1cf32ce195013f902f3b6433f`，與本機 HEAD 相同，分支為
  `0 behind / 0 ahead`。GitHub visibility 重驗仍為 `PUBLIC`／`private: false`。
- 2026-08-13 重新接手時先抓取遠端並確認 `origin/main` 已從 `c31876f` 前進至
  `116cb97`；舊工作階段未完成且已被遠端正式 JMA 實作取代的草稿，完整保存在
  本機 `stash@{0}`（`codex-wip-before-116cb97-sync`），沒有套回或覆蓋新版檔案。
- 同步後由接手者親自跑完整離線回歸，首次結果為
  `1 failed, 436 passed, 3 skipped in 7.16s`：PyMuPDF 1.28.2 匯入舊 `fitz` API 時
  把棄用警告寫到 stdout，導致 `briefing doctor --format json` 的 subprocess 輸出
  不再是純 JSON。已將 PDF itinerary 與 Word QA 的 production／test imports 改為
  官方 `pymupdf` module（保留區域 alias `fitz`，不改行為或資料契約）。
- 修正後針對性回歸為 `24 passed in 1.35s`，`briefing doctor --format json` 實際
  stdout 可直接解析；最終完整離線回歸為 `437 passed, 3 skipped in 7.11s`，
  compileall 與 `git diff --check` 均通過。三個 skip 仍是需顯式 opt-in 的 Hanhan、
  Yating 與私人 LIST／Word integration tests，沒有啟動、放寬或拿 skip 冒充驗收。
- 使用者在再次收到 public repo 範圍提醒後，明確授權只將相容修正 `e0d1b60` push；
  實際輸出為 `116cb97..e0d1b60  main -> main`，隨後 `git ls-remote` 回讀完整 SHA
  `e0d1b60a09f6591913b5c65d9b9714c14f2e1938`，與本機一致、`0 behind / 0 ahead`。
  `gh repo view` 同時重驗為 `PUBLIC`／`isPrivate: false`；此授權不包含 Gate I 紀錄
  commit 或任何後續 public push。
- 以 `e0d1b60` 重建 0.2.0 package：stage 為 63 files，ZIP SHA-256 為
  `faf66fd78e4f4d865668ac16b4c38defbabd5271313baa020c0faa2390881876`。
- Gate I 開始時 PATH、WinGet 目錄、Program Files、常見工具目錄及全磁碟唯讀搜尋均
  證實沒有 `pdftoppm.exe`；使用者另行核准 WinGet 安裝
  `oschwartz10612.Poppler 25.07.0-0`。安裝完成後實跑 `pdftoppm -v` 回傳
  `pdftoppm version 25.07.0`；這是保留於本機的持久工具安裝，不在 temp cleanup 內。
- 使用者明確核准 Gate I 透過 pip 下載 package 宣告的 build/runtime dependencies；
  在唯一全新 OS temp root 解壓 0.2.0，建立純 synthetic master 與完整 schema 2
  calibration manifest，將 `LOCALAPPDATA`／`USERPROFILE` 指向該 root，並以
  `-SkipCodexPluginInstall -SkipClaudeSkillInstall` 安裝，沒有修改真實 Agent 設定。
- 隔離安裝實際下載並安裝 Beautiful Soup 4.15.0、httpx 0.28.1、PyMuPDF 1.28.2
  與其宣告依賴；`pip check` 原文為 `No broken requirements found.`，已安裝命令回傳
  `briefing 0.2.0`，且 `cowell_cli` 不可匯入。
- Gate I JSON doctor 可直接解析；list calibration 與 configured pdftoppm 都為 `ok`，
  master hash 相符，Yating voice enumeration 與 Word registry probe 為 `ok`；ffmpeg
  未設定，因此整體狀態正確為 `warning`。這沒有啟動 Word COM 或執行語音合成。
- config 結構只含 output／template／tools，template 只有 canonical `master_path` 與
  `calibration_manifest`；`render --help` 沒有 `--template`，且只暴露
  `--tts {yating}`。
- 同一 installer 第二次執行以 exit 1／`LIST_RECALIBRATION_REQUIRED` 拒絕覆蓋；
  重跑前後 1,520 files／227 directories、config hash 與 app pyproject hash 全部不變。
  最後刪除唯一 temp root：1,520 files、227 directories、74,354,729 bytes，並回讀
  確認路徑不存在；另刪除本次 sandbox 在 repo 產生的 67 個 pip／PowerShell cache
  files 與 150 個 cache directories，工作樹未殘留測試安裝或 cache。
- Gate I 沒有讀取三份私人 LIST、啟動 Word COM／Yating、發出 live 官網／JMA
  request、安裝 ffmpeg、傳 LINE、存取 Cowell、部署或發布 artifact。
- 2026-08-13 使用者以這台機器的三個精確 absolute paths 核准 Gate C；執行前驗證
  size、mtime 與既定 SHA-256 均相符，且真實 `config.toml` 與固定私人目的目錄均
  不存在，沒有覆蓋既有設定或產物。
- 首次 bounded probe 明確失敗於 Word owner 綁定。診斷證實 Word COM 已啟動，但
  原 PowerShell 錯用 Word 不提供的 `Application.Hwnd`；改為建立不存檔的 hidden
  空白文件視窗，以 `Window.Hwnd` 綁定精確 WINWORD PID／start time，並只回傳
  allowlisted stage、HRESULT 與穩定 error code。修正後 20 秒 probe 實跑成功，回傳
  `{"available": true, "word_version": "16.0"}`；修正 commit 為本機 `6f7cd6f`。
- Gate C 隨後只執行一次 `calibrate-list`，沒有 retry；命令在第一階段 inspect 以
  `WORD_GENERATION_FAILED`／`LIST_HEADER_PARAGRAPHS_CHANGED` 明確停止，對應私人
  review 的 `CALIBRATION_CONTRACT_CONFLICT` 欄位路徑
  `list_header_paragraph_count`。未建立 `LIST-master.docx`、calibration manifest、
  config、PDF 或 PNG，也沒有殘留 WINWORD process。
- 三份來源在校準命令後重算 SHA-256，依序仍為
  `c230eb24397124cbf0fc6940765be14a9e5a07742f64039f0c01d60f05420b76`、
  `84d7db2fa9f01fea2bfb0563a37f78c0aa3993cb972a913506b67496f056420b`、
  `cf62502532344530ec9e0c65161b1fee5624abd6243f32bb6530a1d72cc558bc`。
  固定私人目錄只保留不含文件內容／檔名／路徑的 review JSON；其 SHA-256 為
  `ebd166ea8b83a80cd2ef96c5536d676e672921cafc4a5e47f8d0e6eb4ba99c01`。
- Word ownership 修正的針對性測試為 `15 passed`；最終完整離線回歸為
  `440 passed, 3 skipped in 7.32s`，compileall、兩支 PowerShell parse 與
  `git diff --check` 均通過。三個 skip 仍是需 opt-in 的 Hanhan、私人 LIST／Word
  與 Yating integration；因 master 未建立，真實 Word PDF render 及逐頁視覺 QA
  正確標記為未驗證。
- 使用者另行核准新的 Gate C 唯讀診斷回合，要求保留現有 blocked review 並重查
  相同三份 LIST 的 header paragraph 契約。新增 schema 2
  `diagnose-header-v2` Word action：只接受三個唯一 Word paths，報告只含來源 hash、
  field path、數字型段落結構與固定 label ID；不保存檔名、路徑或實際文字。來源在
  Word 前後都重算 hash，任何變動都 fail closed；額外／未核准 report 欄位會被拒絕。
- 真實唯讀診斷以 Word `16.0` 完成一次：三個 hash 對應的
  `list_header_paragraph_count` 依序為 `5／4／5`，分類為
  `SAMPLE_CONTRACT_CONFLICT`。三份共同結構是第 1 段抬頭、第 2 段 `group_code`、
  第 3 段 `group_name`；差異位於第 4 段至 cell marker 的尾端內容，且該區沒有上述
  固定 label 或 inline shape。此證據只描述結構，不自行判定尾端內容可刪除。
- 新診斷另存於固定私人目錄的 `header-paragraph-diagnostic.json`，SHA-256 為
  `c51f8e43af07239049f88bad0dd7ea6b6931c217ae5bf4161e79970674b30982`；舊
  `calibration-review.json` SHA-256 仍為
  `ebd166ea8b83a80cd2ef96c5536d676e672921cafc4a5e47f8d0e6eb4ba99c01`。
  兩檔均不含來源檔名／路徑／實際文字，且不在 Git 工作樹內。
- 診斷後三份來源 SHA-256 仍與既定值完全相同；沒有 master、manifest、config、
  PDF／PNG 或殘留 WINWORD。診斷功能 commit 為本機 `313cbbc`；針對性回歸為
  `33 passed`，完整離線回歸為 `444 passed, 3 skipped in 7.41s`，compileall、
  PowerShell parse 與 `git diff --check` 均通過。
- 使用者核准修訂 Gate C header paragraph 契約：固定保留第 1–3 段，第 4 段到 cell
  結尾正規化為一個空白 prototype 段。實作保留舊的 exact-four guard，只有 schema 2
  校準 inspection 允許來源尾端為 4–32 段；尾端若重現 `group_code`／`group_name`
  固定 label 或 inline shape 仍 fail closed。修訂 commit 為本機 `a84758b`；
  PowerShell parse 與 `git diff --check` 通過，針對性測試為 `34 passed in 0.54s`，
  完整離線回歸為 `445 passed, 3 skipped in 8.36s`。
- 在全新 exclusive private 目錄執行且只執行一次 `calibrate-list`。結果為
  `WORD_GENERATION_FAILED`，stage `run-action`、HRESULT `-2146822296`
  （`0x800A1768`，Word runtime error `5992`）、adapter code `NONE`；依錯誤碼與目前
  程式路徑，疑似為 schema 2 inspection 存取混合欄寬表格的 `Columns` collection，
  但未取得第二個 Word 回合驗證，因此只記為 `unverified` 推論。
- 失敗後沒有重試。三份來源與兩份舊 review 的 SHA-256 再驗均完全相同，WINWORD
  為 0；沒有 master、manifest 或 config。新 private 目錄只保留
  `calibration-review.json`，SHA-256 為
  `99ab632314cb8a40298bb012ecd02be0de57ab16bd93a95f7212a5b8feae988a`；內容只有安全
  hash、錯誤欄位與未驗證的 candidate field path，不含文件文字。
- 使用者核准一次 Gate C `5992` 細粒度診斷。新增嚴格的 schema 2
  `diagnose-5992-v2` Word job：一次 job 先逐份執行 source inspection，若全數成功才
  依正式 median-day／hash 規則選 base sample，並只在暫存 working copy 執行校準
  mutation。checkpoint 僅允許固定 phase／operation／field ID 與數字座標；report
  拒絕額外欄位、文件文字、檔名或路徑。來源前後均重算 SHA-256，working copy 不
  產生 master 並於 finally 清除。功能 commit 為本機 `146f901`。
- 診斷程式的 PowerShell parser、production Python 100 字元檢查、compileall 與
  `git diff --check` 通過；針對性回歸為 `39 passed in 0.47s`，完整離線回歸為
  `450 passed, 3 skipped in 10.91s`。三個 skip 仍是既有 opt-in Hanhan、私人
  LIST／Word 與 Yating integration，沒有放寬或拿 skip 冒充本次實機診斷。
- 唯一一次實機 `diagnose-5992-v2` 以 Word `16.0` 完成且沒有 retry。它在
  `sample-001`、phase `inspect-source`、operation `table-width-column-item`、
  field path `samples[0].inspection.table_column_widths_points`、table 1／column 1
  精確重現 HRESULT `0x800A1768`／low-word `5992`；完成的 source inspections 為 0，
  base sample 尚未選取。這證實失敗發生在讀取來源的 `Columns.Item(1).Width`，早於
  header tail 正規化及任何 calibration working-copy mutation。
- 安全診斷另存於 private `5992-diagnostic.json`，SHA-256 為
  `92a30ee8d28d67be317d571167293f17cb4dc74bc9f9a241b6070760e7f4dcd2`。診斷後三份
  來源與三份舊 review hash 再驗均完全一致，WINWORD 為 0，仍無 master／manifest／
  config。Word 在專用 runtime root 留下的兩個 Diagnostics log 未讀取內容並已連同
  root 刪除；本回合 2,185 files／887 directories 的測試暫存 root 亦已完整刪除。
- 使用者另行核准 Gate C mixed-width 修正；開工的 `git pull --ff-only` 回傳
  `Already up to date.`。schema-2 欄寬指紋現在固定使用四張表的 prototype rows
  `2／2／2／1` 與 column counts `3／6／7／3`，透過 `Table.Cell(row, column)` 取得
  cell 並讀取 `Cell.Width`，移除已證實會在非均勻表格觸發 `5992` 的
  `Columns.Item(...).Width` 路徑。
- 新增 `table-width-prototype-cell` checkpoint 並保留舊的 width checkpoint operation，
  讓既有診斷 review 維持相容；回歸測試固定上述 prototype mapping，且禁止 schema-2
  inspection 再出現 `Columns.Item` 欄寬存取。
- 修正的針對性回歸為 `40 passed in 0.47s`，完整離線回歸為
  `451 passed, 3 skipped in 8.72s`；PowerShell parser、compileall、production Python
  100 字元行寬檢查與 `git diff --check` 均通過。三個 skip 維持既有 opt-in
  integrations，沒有放寬測試。
- 本修正回合未讀三份真實 LIST、未啟動 Word、未校準，也未建立或改動 master、
  manifest、config、QA 或任何 private review；結束檢查 WINWORD 為 0。專用 synthetic
  測試暫存目錄已精確刪除並確認不存在。
- 使用者另行核准真實 Gate C 校準；開工的 `git pull --ff-only` 回傳
  `Already up to date.`。執行前重新確認三份來源的 size、mtime 與既定 SHA-256 全部
  相符，四份既有 private reviews 的 SHA-256 也完全相符；全新 exclusive private
  目錄、config、master、manifest 與 runtime root 均不存在，WINWORD 為 0，
  `pdftoppm version 25.07.0` 可用。
- 在 `list-calibration-v3-mixed-width` 執行且只執行一次 `calibrate-list`，沒有 retry。
  命令明確回傳 `WORD_GENERATION_FAILED`、stage `run-action`、HRESULT
  `-2146822297`（`0x800A1767`，Word runtime error `5991`）、adapter code `NONE`。
- Microsoft 的 Word table 文件指出，非均勻或含垂直合併儲存格的表格不能安全地個別
  存取 `Rows`；目前 schema-2 inspection 在 prototype cell widths 後的第一個候選為
  operation `table-format-row`、field path `samples[].inspection.style_digest` 與
  `table.Rows.Item(...).Range`。本次 coarse calibration report 沒有 checkpoint，因此
  以上只記為 `unverified` 推論，未擅自修正或再次啟動 Word。
- 校準後三份來源與四份既有 reviews 的 SHA-256 均完全不變，WINWORD 為 0；沒有
  master、manifest、config、PDF 或 PNG。新 private 目錄只保留安全的
  `calibration-review.json`，SHA-256 為
  `5835e1397a59f7b58d9c734568d658a3d445e2704c00e16b95a58634d27b8e61`；檔案不含
  LIST 檔名、Downloads 路徑、source path 欄位或文件文字。
- 專用 runtime root 共有 208 files／39 directories／9,951,797 bytes；兩個 Word
  Diagnostics logs 未讀取內容，已連同 Python caches 精確刪除並確認 root 不存在。
  本回合沒有程式碼變更，因此沒有重跑測試；最近完整離線結果維持
  `451 passed, 3 skipped in 8.72s`。
- 2026-08-13 依「繼續開發」授權完成 Gate C vertically-merged-row 離線修正；開工的
  `git pull --ff-only` 回傳 `Already up to date.`。schema-2 inspection 的四表格式、
  daily header 與 daily body prototype 指紋全部改由固定 cell 座標取得，移除該函式及
  新 helper 對 `Rows.Item(...).Range` 的依賴；舊 checkpoint operation 仍保留相容性，
  新 cell checkpoint 已加入嚴格 allowlist。
- 新增防回歸測試，固定 prototype rows `2／2／2／1`、column counts `3／6／7／3`，
  並禁止 schema-2 inspection 與格式 helper 出現 `Rows.Item`。針對性測試為
  `41 passed`；完整離線回歸為 `452 passed, 3 skipped in 7.28s`，PowerShell parser、
  compileall 與 `git diff --check` 均通過。三個 skip 維持既有 opt-in integrations。
- 本回合未讀三份私人 LIST、未啟動 Word、未執行 calibration，也未建立或改動
  master、manifest、config、QA 或 private review；因此 `5991` 的實機排除狀態仍為
  **未驗證**。
- 使用者另行核准一次新的 Gate C 真實校準；開工的 `git pull --ff-only` 回傳
  `Already up to date.`。執行前驗證三份來源 SHA-256 全部符合既定值，五份既有
  private reviews／diagnostics 的 SHA-256 全部符合既定值；既有 master／manifest
  數量為 0，真實 config 與全新目的目錄均不存在，WINWORD 為 0，`pdftoppm 25.07.0`
  可用。
- 兩次 sandbox 內的 probe 在寫入 job 前即被 temp ACL 拒絕，均未啟動 Word、未讀取
  LIST、未消耗 calibration；改在 sandbox 外執行 bounded hidden owned probe 後成功，
  原文為 `{"available": true, "word_version": "16.0"}`。
- 在全新 `list-calibration-v4-cell-format` 私人目錄執行且只執行一次
  `calibrate-list`，沒有 retry。命令明確回傳 `WORD_GENERATION_FAILED`、stage
  `run-action`、HRESULT `-2146233087`（`0x80131501`，low word `5377`）、adapter code
  `NONE`。此錯誤沒有安全 checkpoint，不能推定 row-access 修正是否已越過原 `5991`。
- 失敗後三份來源 SHA-256 全部不變，WINWORD 為 0；沒有 master、manifest、config、
  PDF、PNG 或新 calibration review。CLI 將空的全新 private 目錄自動移除；五份既有
  private reviews／diagnostics 未覆蓋或刪除。兩個失敗 probe 遺留的精確 temp 目錄已
  清除並回讀確認不存在。本回合沒有程式碼變更，因此未重跑測試，最近完整離線結果
  維持 `452 passed, 3 skipped in 7.28s`。
- 2026-08-13 依「進行下一步」授權完成 Gate C `0x80131501` 細粒度診斷的離線實作；
  開工的 `git pull --ff-only` 回傳 `Already up to date.`。保留既有
  `diagnose-5992-v2` 相容性，新增通用 `diagnose-gate-c-v3` action，兩者共用同一個
  bounded Word job、三份來源 hash 綁定、job-local working copies、來源前後 hash
  驗證、checkpoint allowlist 與 exclusive report boundary。
- v3 report 只允許 Word version、分類、完成 inspection 數、base sample ID、固定
  phase／operation／field ID、數字座標、HRESULT 與 adapter code；拒絕額外欄位，
  不保存來源路徑、檔名、文件文字或 master。回歸測試另固定 `0x80131501`／low word
  `5377` 的 round trip，並驗證輸出不含 `LIST-` 或 `source_path`。
- 針對性測試為 `44 passed`；完整離線回歸為 `455 passed, 3 skipped in 7.34s`，
  PowerShell parser、compileall 與 `git diff --check` 均通過。三個 skip 維持既有
  opt-in integrations。本回合未讀私人 LIST、未啟動 Word、未建立或改動任何 private
  artifact，因此 v3 診斷的實機結果仍為**未驗證**。
- 2026-08-14 使用者明確核准一次 `diagnose-gate-c-v3` 真實診斷，不包含 calibration
  retry；開工的 `git pull --ff-only` 回傳 `Already up to date.`。執行前再次驗證三份
  來源與五份既有 private reviews／diagnostics 的 SHA-256 全部符合既定值；全新診斷
  目錄不存在，既有 master／manifest 數量為 0，真實 config 不存在，WINWORD 為 0。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。唯一一次 v3 診斷隨後完成且沒有
  retry：classification `ERROR_OBSERVED`、完成 source inspections `0`、base sample
  `sample-000`；checkpoint 為 phase `inspect-source`、sample `sample-001`、operation
  `table-borders`、field path `samples[0].inspection.border_digest`、table `1`，HRESULT
  `-2146233087`（`0x80131501`，low word `5377`）、adapter code `NONE`。
- 此 checkpoint 證實 row-access 修正已越過先前候選路徑，新的阻塞點是 schema-2
  inspection 對 `$table.Borders` collection 的列舉；尚未核准或執行 border-access
  修正，也未校準。
- 診斷後三份來源與五份既有 private reviews／diagnostics 的 SHA-256 全部不變，
  WINWORD 為 0；沒有 master、manifest、config、PDF 或 PNG。全新 private 目錄只含
  `gate-c-v3-diagnostic.json`，共 745 bytes，SHA-256 為
  `60d5de09c7d995f53a268723625145b24ceff19dce17d538e743761d58eed22c`；內容僅含既定
  hashes、checkpoint 與錯誤欄位，不含來源路徑、檔名或文件文字。本回合沒有程式碼
  變更，因此未重跑測試，最近完整離線結果維持 `455 passed, 3 skipped in 7.34s`。
- 2026-08-14 依「好 下一步」授權完成 Gate C border-access 離線修正；開工的
  `git pull --ff-only` 回傳 `Already up to date.`。schema-2 inspection 已移除唯一的
  `$table.Borders` collection 列舉，改以四張表固定 prototype rows `2／2／2／1`、
  column counts `3／6／7／3` 的每個 cell 建立 border fingerprint。
- 每個 prototype cell 固定讀取 top／left／bottom／right／diagonal-down／diagonal-up
  六種 border types（Word constants `-1／-2／-3／-4／-7／-8`）；相鄰 cell 的外框涵蓋
  表格內部格線。六種 access 各有獨立 allowlisted checkpoint，保留 table／row／column，
  若實機仍失敗可定位到特定 cell 與 border side。
- 新增防回歸測試，固定上述 border types／operations，並禁止 schema-2 inspection
  再出現 `$table.Borders` 或 collection enumeration。針對性測試為 `45 passed`；完整
  離線回歸為 `456 passed, 3 skipped in 8.14s`，PowerShell parser、compileall 與
  `git diff --check` 均通過。三個 skip 維持既有 opt-in integrations。
- 本回合未讀私人 LIST、未啟動 Word、未執行診斷或校準，也未建立或改動任何 private
  artifact；既有 v3 diagnostic SHA-256 仍為
  `60d5de09c7d995f53a268723625145b24ceff19dce17d538e743761d58eed22c`，WINWORD 為 0。
- 2026-08-14 使用者明確核准一次新的 `diagnose-gate-c-v3` 真實診斷，不包含
  calibration retry；開工的 `git pull --ff-only` 回傳 `Already up to date.`。執行前
  再次驗證三份來源與六份既有 private reviews／diagnostics 的 SHA-256 全部符合既定
  值；全新診斷目錄不存在，master／manifest 數量為 0，真實 config 不存在，
  WINWORD 為 0。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。唯一一次 v3 診斷隨後完成且沒有
  retry：三份 source inspections 全部完成，選定 base 為 `sample-001`，證實固定 cell
  border fingerprint 已實機越過先前 `$table.Borders` 阻塞點。
- 診斷在 diagnostic-only working copy mutation 明確停止：classification
  `ERROR_OBSERVED`；checkpoint phase `calibrate-copy`、sample `sample-001`、operation
  `header-tail-normalize`、field path `master_working_copy.prototype_header`、table 1／
  row 1／column 1／paragraph 4；HRESULT `-2146233087`（`0x80131501`，low word `5377`），
  adapter code `LIST_HEADER_NORMALIZATION_FAILED`。
- 此 adapter code 來自 `Set-NormalizedHeaderDynamicTail` 寫入後的明確 postcondition：
  `$HeaderCell.Range.Paragraphs.Count -ne 4`。因此這不是未知 COM 寫入結果；目前程式以
  paragraph 4 start 到 cell end 前一字元的 range 寫入單一 CR，但 Word 完成後仍未得到
  exact-four 契約。尚未核准或執行 normalization 修正，也未校準。
- 診斷後三份來源與六份既有 private reviews／diagnostics 的 SHA-256 全部不變，
  WINWORD 為 0；沒有 master、manifest、config、PDF 或 PNG。全新 private 目錄只含
  `gate-c-v3-diagnostic.json`，共 782 bytes，SHA-256 為
  `e3c469bb5fb727efc36aeeffa1d7532c9d232d82d0321f45d961ed0ec156cec2`；內容僅含既定
  hashes、checkpoint 與錯誤欄位，不含來源路徑、檔名或文件文字。本回合沒有程式碼
  變更，因此未重跑測試，最近完整離線結果維持 `456 passed, 3 skipped in 8.14s`。
- 2026-08-14 依「好 下一步」授權完成 Gate C header-tail normalization 離線修正；
  開工的 `git pull --ff-only` 回傳 `Already up to date.`。既有實作把 paragraph 4 start
  到 cell marker 前的整段 tail range 替換為單一 CR，會在 Word 受保護的 cell 終止段落
  之外再形成一個段落；現在改為將該 range 內容清空，讓 Word 保留既有的終止段落作為
  唯一空白 paragraph 4。
- exact-four postcondition 現在先取得 `$observedParagraphCount`，並以新的 allowlisted
  `header-tail-postcondition` checkpoint 記錄 table 1／row 1／column 1 及實際段落數，
  再判斷是否為 4；若實機仍不符，安全 v3 report 可直接回報 observed count，不需猜測。
- 更新防回歸測試，禁止 normalization 再寫入額外 CR，並固定清空 tail、observed-count
  checkpoint 與既有 fail-closed postcondition。針對性測試為 `45 passed`；完整離線
  回歸為 `456 passed, 3 skipped in 7.61s`，PowerShell parser、compileall 與
  `git diff --check` 均通過。三個 skip 維持既有 opt-in integrations。
- 本回合未讀私人 LIST、未啟動 Word、未執行診斷或校準，也未建立或改動任何 private
  artifact；最近 v3 diagnostic SHA-256 仍為
  `e3c469bb5fb727efc36aeeffa1d7532c9d232d82d0321f45d961ed0ec156cec2`，WINWORD 為 0。
- 2026-08-14 使用者以「好 下一步」核准一次新的 `diagnose-gate-c-v3` 真實診斷，
  不包含 calibration retry；開工的 `git pull --ff-only` 回傳 `Already up to date.`。
  執行前再次驗證三份來源與七份既有 private artifacts 的 SHA-256 全部符合既定值；
  全新診斷目錄不存在，master／manifest 數量為 0，真實 config 不存在，WINWORD 為 0。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。唯一一次 v3 診斷隨後完整通過且
  沒有 retry：classification `NOT_REPRODUCED`、三份 source inspections 全部完成、
  base `sample-001`、checkpoint phase／operation 均為 `complete`；HRESULT `0`／
  `0x00000000`、low word `0`、adapter code `NONE`。
- 此結果證實 schema-2 source inspection、header-tail normalization、其餘
  diagnostic-only working-copy mutations 與 `SaveAs2` 路徑均已在 Word `16.0` 實跑
  完成；diagnostic master 依設計在 temporary boundary 內清除，沒有正式 master 或
  manifest。這不等於 Gate C 正式 calibration 已執行或成功。
- 診斷後三份來源與七份既有 private artifacts 的 SHA-256 全部不變，WINWORD 為 0；
  沒有 master、manifest、config、PDF、PNG 或 diagnostic master。全新 private 目錄
  只含 `gate-c-v3-diagnostic.json`，共 696 bytes，SHA-256 為
  `c7db1141eb42240069dae1faa060917d2783ff25367b9a731d425534b4117d25`；內容僅含既定
  hashes、complete checkpoint 與零錯誤欄位，不含來源路徑、檔名或文件文字。本回合
  沒有程式碼變更，因此未重跑測試，最近完整離線結果維持
  `456 passed, 3 skipped in 7.61s`。
- 2026-08-14 使用者以「好 下一步」明確核准一次正式 Gate C `calibrate-list`；範圍
  只允許全新 exclusive private 目錄執行一次，沒有 retry，不包含 Gate V、config
  寫入、Gate E 或 push。開工的 `git pull --ff-only` 回傳 `Already up to date.`；
  執行前再次驗證三份來源與八份既有 private artifacts 的 SHA-256 全部符合既定值，
  全新校準目錄不存在，既有 master／manifest 數量為 0，真實 config 不存在，
  WINWORD 為 0，`pdftoppm 25.07.0` 可用。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。唯一一次正式 `calibrate-list` 隨後
  執行完成且沒有 retry，但 CLI 只回傳 `INTERNAL_ERROR`／`Unexpected internal error`，
  `details` 為空；沒有 Word adapter stage、HRESULT、field paths 或受控 review。
- 事後唯讀程式路徑確認：正式 calibration 先執行 `inspect-v2`，再由
  `compare_calibration_samples()` 比較三份 normalized layouts；若拋出
  `CalibrationContractError`，目前 `main()` 的 generic `except Exception` 會把它抹成
  本次看到的 `INTERNAL_ERROR`。由於前一回 v3 已證實相同 source inspection、mutation
  與 SaveAs2 路徑可通過，sample contract comparison conflict 是目前最可能原因；但
  本次沒有安全 stage/report，因此只記為**未驗證推論**，不據此修改契約。
- 校準後三份來源與八份既有 private artifacts 的 SHA-256 全部不變，WINWORD 為 0；
  全新 private 目錄因空白由 CLI 自動移除，沒有 master、manifest、config、review、
  PDF 或 PNG。本回合沒有程式碼變更，因此未重跑測試，最近完整離線結果維持
  `456 passed, 3 skipped in 7.61s`。
- 2026-08-14 完成可逆的 Gate C 離線安全修正，沒有讀取真實 LIST、啟動 Word 或重跑
  calibration。`calibrate_list_templates()` 現在依序回報固定 allowlist stage：
  `inspect-samples`、`compare-samples`、`calibrate-master`、`validate-master`、`publish`。
  CLI 捕捉 `CalibrationContractError` 後會以 exclusive create 寫入
  `calibration-review.json`；內容只含 schema/status、受控 error code、stage、三個來源
  SHA-256 與排序後 field paths，不含來源路徑、檔名或內容，並以 exit code 20 回傳
  `CALIBRATION_CONTRACT_CONFLICT`，不再落入泛化 `INTERNAL_ERROR`。
- TDD 紅測先確認缺少 `on_stage` 與 review；實作後目標測試為 34 passed。完整離線回歸
  原文為 `457 passed, 3 skipped in 7.36s`；`compileall -q src tests` 與
  `git diff --check` 均通過。此 venv 沒有 `ruff.exe`，因此 Ruff 明確標記為未驗證，
  沒有為此安裝新依賴。
- 2026-08-14 使用者明確重新核准一次新的正式 Gate C calibration；範圍只含 20 秒
  hidden owned probe、全新 exclusive private 目錄的一次 `calibrate-list` 與唯讀後驗，
  不含 retry、Gate V、config 寫入、Gate E 或 push。開工 `git pull --ff-only` 回傳
  `Already up to date.`。第一次 preflight 腳本因 PowerShell 單一字串索引錯誤而無法
  取得來源 hash/size，且三個縮略的 artifact 預期 hash 不足以驗證；該次沒有啟動 Word、
  沒有讀取文件內容，也沒有執行 calibration。改從既有 STATUS 取回完整 hash 並修正
  唯讀腳本後，三份來源 hash/size、八份既有 private artifacts 全部符合既定值；新目標、
  config 不存在，master／manifest 各 0，WINWORD 0，pdftoppm 可用。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。隨後在全新
  `list-calibration-v7-safe-review` 執行且只執行一次正式 `calibrate-list`，沒有 retry；
  命令受控回傳 `CALIBRATION_CONTRACT_CONFLICT`、stage `compare-samples`，field paths
  為 `border_digest`、`daily_body_prototype_digest`、`daily_header_digest`、`font_digest`、
  `paragraph_digest`、`shape_geometry_points`、`style_digest`、
  `table_column_widths_points`。因此未進入 `calibrate-master`，不得自行放寬契約。
- 後驗三份來源 hash/size 與八份舊 artifacts 全部不變，WINWORD 0，仍無 master、
  manifest 或 config。全新目錄只含 606-byte `calibration-review.json`，SHA-256 為
  `3b60876667ce6f093f1299371c57956a74209a0e85c34bc7b010d9bd8ef69dc7`；keys 僅為
  schema/status、error code、stage、source SHA-256、field paths，且不含 LIST 名稱、
  Downloads 路徑、`source_path` 或文件內容。本回合沒有程式碼變更，因此未重跑測試，
  最近完整離線結果維持 `457 passed, 3 skipped in 7.36s`。
- 2026-08-14 依使用者「好 下一步」完成 Gate C conflict matrix 離線核心，沒有讀取
  真實 LIST、啟動 Word、執行 diagnosis/calibration，亦未建立或修改 private artifact。
  `build_calibration_conflict_matrix()` 只接受三個唯一 sample 與 normalized layout 既有
  欄位；欄位必須確實存在至少兩種 canonical values，否則 fail closed。field 與 sample
  均固定排序，classification 為 `TEMPLATE_CONTRACT_CONFLICT`，每個差異固定標示
  `REQUIRES_OP_DECISION`，不會自行宣稱可正規化。
- Matrix 明確排除 day count、dynamic content 與 adaptive profiles。既有 `*_digest`
  只輸出 normalized digest，純數值樹才輸出 normalized value；任何其他含字串結構
  （包括可能帶 Word shape 名稱的 `shape_geometry_points`）只輸出 canonical SHA-256，
  避免 private 名稱進入 review。`compare_calibration_samples()` 發現衝突時會附上此
  matrix，CLI 只將它 exclusive-create 到 private `calibration-review.json`，一般錯誤
  details 仍只含 stage、field paths 與 review path。
- TDD 紅測先確認 matrix builder 不存在；收緊 shape 名稱輸出後，針對性回歸為
  `36 passed in 1.23s`，完整離線回歸原文為 `459 passed, 3 skipped in 7.24s`；
  `compileall -q src tests`、production Python 100 字元行寬與 `git diff --check` 均通過。
  此 venv 仍沒有 Ruff，因此 Ruff 未驗證且沒有安裝新依賴。
- 2026-08-14 依使用者「好 下一步」完成專用 read-only conflict diagnosis CLI 的離線
  實作；沒有讀取真實 LIST、啟動 Word、執行 diagnosis/calibration，亦未建立或修改
  private artifact。新命令 `diagnose-list-conflicts` 只接受三個唯一 DOC／DOCX 與全新
  `--private-dir`，刻意沒有 `pdftoppm`、master、manifest 或 config 參數；既有 private
  目錄會在 Word inspection 前 fail closed。
- `diagnose_calibration_conflicts()` 只呼叫一次 `inspect_list_templates_v2()`，接著以共用
  純 comparison helper 產生 field paths／matrix；不呼叫 `calibrate_list_templates()`。
  有衝突時 private `conflict-diagnosis.json` 回報 `TEMPLATE_CONTRACT_CONFLICT` 並以
  exit code 20 停止；沒有 normalized layout 衝突時回報
  `NORMALIZED_LAYOUT_COMPATIBLE` 並立即結束，這不宣稱 adaptive profiles 或完整
  calibration 已通過。兩條路徑都不可能進入 `calibrate-master`。
- CLI report 以 exclusive create 寫入，只含 schema/status、command、固定 stage、
  classification、Word version、source SHA-256、field paths 與 private-safe matrix；一般
  CLI output 不展開 matrix。測試明確把 calibration function 替換成 fail sentinel，證實
  diagnosis CLI 不會呼叫它。TDD 紅測先確認 diagnosis API 不存在；針對性回歸為
  `40 passed in 1.16s`，完整離線回歸原文為 `463 passed, 3 skipped in 7.32s`。
- 2026-08-14 使用者以「好 下一步」明確核准一次真實 `diagnose-list-conflicts`；範圍
  只含 preflight、20 秒 hidden owned probe、全新 private 目錄的一次 `inspect-v2`／
  comparison 與唯讀後驗，沒有 retry，不含 calibration、Gate V、config、Gate E 或
  push。開工 `git pull --ff-only` 回傳 `Already up to date.`；三份來源 hash/size、九份
  既有 private artifacts 全部符合既定值，新目標與 config 不存在，master／manifest
  各 0，WINWORD 0。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。隨後在全新
  `list-diagnosis-v8-conflict-matrix` 執行且只執行一次 `diagnose-list-conflicts`，沒有
  retry；結果為 `TEMPLATE_CONTRACT_CONFLICT`、stage `compare-samples`，重現相同八個
  field paths：`border_digest`、`daily_body_prototype_digest`、`daily_header_digest`、
  `font_digest`、`paragraph_digest`、`shape_geometry_points`、`style_digest`、
  `table_column_widths_points`。命令只完成 inspection/comparison，沒有 calibration 路徑。
- Matrix 顯示 `border_digest` 與 `daily_header_digest` 各有兩種值：sample-001／002 相同，
  sample-003 不同。其餘六欄各有三種值。欄寬的四表總寬以程式計算：sample-001 為
  `563.6／556.7／556.35／556.7 pt`，sample-002 與 sample-003 均為
  `558.25／556.7／556.35／556.7 pt`；第 2–4 表總寬相同但部分欄位重新分配，第 1 表
  sample-001 總寬另多 5.35 pt。這些只是不透明差異與數值證據，未據此選 base、平均或
  放寬契約。
- 第一次唯讀群組摘要腳本使用此 PowerShell/.NET 不支援的 `SHA256.HashData()`，導致
  群組數無效，且 case-insensitive `-match 'LIST-'` 誤中 CLI command 的小寫 `list-`；
  diagnosis 沒有重跑。改用 report 已有的 safe digest/value 分組並改成 case-sensitive
  檢查後，上述矩陣結果成立，report 不含大寫 LIST 檔名、Downloads 或 `source_path`。
- 後驗三份來源 hash/size 與九份舊 artifacts 全部不變，WINWORD 0，仍無 master、
  manifest 或 config。新目標只含 8,888-byte `conflict-diagnosis.json`，SHA-256 為
  `24a5fb1ab2b71773096cf8cc893acc7001dc018afbefb27a3d4fbf9283fec53d`。本回合沒有
  程式碼變更，因此未重跑測試，最近完整離線結果維持
  `463 passed, 3 skipped in 7.32s`。
- 2026-08-14 使用者以「好 下一步」核准離線建立 component diagnosis。新增
  `diagnose-list-components` 與 Word action `diagnose-components-v2`，只以 read-only
  開啟三份來源，輸出固定 cell／border／shape IDs、數值／enum，以及立即 SHA-256 後的
  style／font 名稱與 daily header/body 子元件；不讀取或輸出 Word text、不建立 working
  copy／master／manifest，也不呼叫 calibration。Python 對 report 採 exact-schema
  allowlist，拒絕額外欄位，並以執行前後 SHA-256 偵測來源變更。舊 schema-2 inspection
  digests、`_normalized_layout_dict()` 與正式 comparison contract 均未修改。
- 本次只用 synthetic adapter 驗證，沒有啟動 Word、沒有讀取真實 LIST，也沒有建立新的
  private artifact。針對性測試原文為 `70 passed`；PowerShell parser 原文為
  `PowerShell parse OK`，`compileall OK`，`git diff --check` 通過；完整離線回歸原文為
  `469 passed, 3 skipped in 7.34s`。
- 2026-08-14 使用者明確核准「一次新的真實 read-only component diagnosis」。開工
  `git pull --ff-only` 回傳 `Already up to date.`；三份來源依序精確匹配既定 SHA-256
  與 `77,824／81,408／86,016` bytes，新 private 目標不存在，WINWORD 0。只執行一次
  `diagnose-list-components`，沒有 probe、retry 或 calibration；命令回傳 `status: ok`。
- 三份 component 數量完全相同且沒有 presence 差異：styles／fonts／paragraphs 各 19、
  borders 114、daily header/body 各 7、shapes 1。styles 19 格全部一致，證實舊
  `style_digest` 衝突是因舊 digest 同時混入 font／paragraph，而非 style 本身不同。
  Fonts 有 13 格不同且全為 sample-001／002 相同、sample-003 不同：12 格字級、3 格
  bold、4 格 color。Paragraphs 有 11 格不同，均涉及 line spacing，其中 1 格另有
  line-spacing rule 差異，且該格 sample-002 回傳 Word mixed/undefined sentinel
  `9999999`，不得當成可直接套用的標準值。
- Borders 只有 4 個 prototype side 不同，全部為 sample-001／002 相同、sample-003
  不同，差異僅 line width `12／12／4`。Daily header 7 格全為 sample-001／002 相同、
  sample-003 不同，差異來自 font 與 paragraph 子元件，style 相同；daily body 7 格的
  font 與 paragraph 都不同，其中 1 格 sample-001／002 相同、其餘 6 格三份皆不同。
  唯一 `floating-001` 三份皆存在，但 left/top/width/height 皆不同，尺寸依序為
  `95.4／83.95／103.4 pt` 正方形。
- 第一版唯讀差異彙總腳本因 `ConvertTo-Json -Depth` 陣列語法錯誤而產生無效零差異；
  沒有重新執行 Word action。修正後只重讀既有安全 JSON 並得到上述結果。後驗三份來源
  hash／size 均不變，WINWORD 0。全新 private 目錄只含 134,596-byte
  `component-diagnosis.json`，SHA-256 為
  `86a9cecab6d1b544ee62ebe336ad7368bb591fc072deeeecd1c66ffb5ba5f12a`；report 不含
  大寫 LIST 檔名、Downloads、`source_path` 或 Windows 路徑。本回合沒有程式碼變更，
  最近完整離線回歸維持 `469 passed, 3 skipped in 7.34s`。
- 2026-08-14 使用者以「好 下一步」核准純離線 normalization decision table 開發；
  開工 `git pull --ff-only` 回傳 `Already up to date.`。新增
  `build_component_normalization_decision_table()`：固定 19 個 prototype style/font/
  paragraph IDs、114 個 border IDs、daily header/body 各 7 個 IDs，以及非空且跨樣本一致的
  synthetic shape ID/kind；缺漏、多出、重複或 shape kind 不合法均 fail closed，不得由
  base 選擇修補。
- 完整一致的 bundle 標為 `PRESERVE_UNANIMOUS`；任何差異標為 `REQUIRES_OP_BASE`，OP
  日後必須以 exact source SHA-256 與 component-value SHA-256 綁定選擇。兩份相同不會
  觸發多數決。`9999999` 會把該來源列為不合格 base 並將整表分類為
  `BLOCKED_MIXED_VALUE`；floating shape 的 left/top/width/height 固定作為一個
  `geometry_bundle`，不得拼裝。Daily body 是 style/font/paragraph 決策後的 derived audit，
  不建立第二套可能互相矛盾的決策。
- 新政策文件為
  `docs/specs/2026-08-14-list-normalization-decision-table.md`。本回合沒有讀取真實 LIST、
  既有 private report、啟動 Word、執行 diagnosis/calibration 或修改正式 comparison；
  `_normalized_layout_dict()` 與 `compare_calibration_samples()` 未變。針對性測試原文為
  `35 passed`，`compileall OK`，`git diff --check` 通過；完整離線回歸原文為
  `476 passed, 3 skipped in 7.69s`。
- 2026-08-14 使用者以「好 下一步」核准純離線 normalization planner 開發；開工
  `git pull --ff-only` 回傳 `Already up to date.`。新增 strict
  `load_component_diagnosis_artifact()`，只接受 `diagnose-list-components` 產出的 exact
  schema-1／status／command／stage、三個唯一且非零 source SHA-256、Word version 與三份
  allowlisted component evidence；額外欄位、缺欄、錯誤 hash 或不合法 component 立即拒絕。
- 新增 `plan-list-normalization --component-report ... --private-dir ...`。Parser 不接受
  `--sample`，命令不建立 Word adapter、不呼叫 diagnosis/calibration，只在不存在的 private
  目錄 exclusive-create `normalization-decision-table.json`；非 ready classification 回傳
  `needs_review`／exit 20，完全一致才回傳 `ok`。輸入不合法時只移除空目錄，不覆蓋或刪除
  任何已有 artifact。
- Decision table 以 canonical JSON 計算 semantic SHA-256。OP-choice artifact exact schema
  只允許 table hash、原三個 source hashes 與 choices；每個 choice 必須完整且唯一對應一個
  decision ID，同時匹配 eligible source SHA-256 與該來源的 component-value SHA-256。
  缺漏、多餘、重複、額外欄位、table/source/component hash 不符、選到 mixed sentinel
  來源，或試圖用 choice 解決 component-contract conflict 都會拒絕。政策文件已補上 schema。
- 本回合僅建立 synthetic component report 驗證 planner，沒有讀取既有 private report、
  真實 LIST、啟動 Word 或執行 calibration；正式 comparison/calibration 接線未修改。
  針對性測試原文為 `62 passed`，`compileall OK`，`git diff --check` 通過；完整離線回歸
  原文為 `487 passed, 3 skipped in 7.55s`。
- 2026-08-14 使用者明確核准「讀取一次既有 private-safe component report，離線產生
  真實 normalization decision table」。開工 `git pull --ff-only` 回傳
  `Already up to date.`；前驗既有 report 為 134,596 bytes，SHA-256 精確匹配
  `86a9cecab6d1b544ee62ebe336ad7368bb591fc072deeeecd1c66ffb5ba5f12a`，新 private 目標
  不存在且 WINWORD 0。只執行一次 `plan-list-normalization`，沒有 retry、Word、
  diagnosis 或 calibration；受控回傳 `needs_review`／`BLOCKED_MIXED_VALUE`。
- 真實表共有 36 個 decisions：fonts 13、paragraphs 11、borders 4、daily header 7、
  shapes 1。35 個為 `REQUIRES_OP_BASE`；唯一 `BLOCKED_MIXED_VALUE` 是
  `paragraphs:table-001-row-002-column-003`，changed properties 為 line spacing points／
  rule，三份中有 2 個 eligible、1 個 ineligible source。另有 daily body 7 個
  `VERIFY_AFTER_COMPONENT_NORMALIZATION` derived audits，component-contract blocker 為 0。
  Unanimous preserved counts 為 styles 19、fonts 6、paragraphs 8、borders 110，其餘 0。
- 全新 private 目錄只含 53,469-byte `normalization-decision-table.json`；file SHA-256
  為 `995130a3b8e5a27c0a52b629ef53e3c1d79761bbd58ff43ee415eca7cccdfb27`，canonical
  decision-table SHA-256 為
  `a41ce44d79852c1e7407f0f8f03f30e8bfce13603ad68853966c6d4aaf0b50fe`。後驗來源 report
  hash 不變、WINWORD 0，目標沒有 master／manifest／config。本回合沒有程式碼變更，
  最近完整離線回歸維持 `487 passed, 3 skipped in 7.55s`。

## 下一步

真實 worksheet 與 blank choice artifact 已完成，36 decisions 已整理成 13 個 review
groups。下一步由 OP 對每組明確指定 sample-001／002／003；選擇會展開到該組每個 exact
decision，再填入 blank artifact 的 source SHA-256 與 matching component-value SHA-256，
並用既有 hash-bound validator 驗證。所有 choices 完成並通過 validator 前
不能進 Gate C calibration。沒有新核准
不得再次讀取真實 LIST、啟動 Word、執行 diagnosis 或 calibration。只有 Gate C
成功建立並驗證 master 後，才分別取得 Gate V（4／5／6／7／8／12 天 Word 視覺 QA）與 Gate E
（真實 URL／PDF 到語音 DRAFT）的當次核准。
GitHub visibility 依使用者指示不變；`e0d1b60` public push 是收到風險警告後的單次
明確例外，不構成 Gate I 紀錄 commit 或後續 public push 授權。Cowell 部分維持到
立益公司電腦 clone、
先跑完整離線測試，再由 OP 登入受控 Chrome，依序驗證 auth status 與 rooms preview。

## 阻塞點

本機無科威登入，因此真實頁面結構與正式 rooms apply 尚未驗證。正式
apply 必須在公司環境針對最終 preview 另行取得當次明確核准。

GitHub 遠端於 2026-08-13 即時驗證仍為 public。依私有產品與「不可把內容複製到
公開處」規則，正常情況在 repo 重新驗證為 private 前不得 push；使用者本次在明知
衝突後明確要求直接 push，因此僅本次依反迎合條款記錄為違規例外。

Gate I 已完成，沒有剩餘安裝阻塞。Gate C v3 真實診斷已證實三份 source inspection、
所有 diagnostic-only mutation 與 SaveAs2 可完整通過；最新正式 calibration 已確認
阻塞於 `compare-samples` 的八個 field paths，而非 Word adapter 失敗。離線 matrix
核心與 read-only CLI 已對真實樣本執行；component evidence 已定位 font、paragraph、
border、daily prototypes 與 shape geometry 差異，但尚無產品決策可判定標準值，且
存在 Word mixed/undefined sentinel，不能自行放寬契約。
既有 private artifacts 與最新 reports 都不能覆蓋或刪除；新的 Word 回合、再次讀取
三份 LIST、診斷或 calibration 都需要新的明確核准。

說明會產生器 0.2.0 Task 1–8 的離線程式沒有 calibration、parser、merge、天氣、
Word plan、workflow 或 packaging 技術阻塞；
URL-only 正式頁已
驗證可建立 `DRAFT_READY` 草稿，但該產品仍須 OP 從大阪／東北／北海道明確確認
`product_region`，不能跳過此人工欄位。完整
6–8 分鐘正式版本尚未產生；Task 6 JMA parser、離線選擇與 Task 9 orchestration 已
完成，但正式資料取得及 LIST Word COM／私有範本／視覺驗證仍未實跑或端對端驗證。
第一批 alias 只有 synthetic 大阪
案例；仙台、札幌等城市必須取得 JMA 預報區證據與測試後才能加入。掃描型無文字
PDF 會明確
阻塞並要求另行 OCR review。Azure 已移出第一階段自動流程；任何未來雲端 TTS 與
自動 LINE 傳送仍是獨立核准關卡。

本機 capability probe 與真實 integration 顯示 Yating 可用且正式管線可合成，
`pdftoppm` 可用、Hanhan 僅供舊比較、Word COM 已註冊且 Gate C hidden owned probe
已以 Word `16.0` 實跑通過，但 `ffmpeg` 尚未找到；私人 master、PDF render 與逐頁
視覺 QA 因校準契約阻擋仍未驗證。
Task 11 隔離安裝已證明新 `briefing.exe` 可啟動，且顯式 config 可載入外部
`pdftoppm`；私有範本契約及 Word 實機 render 仍未驗證。
0.2.0 的任意天數與安全續頁邏輯已在 synthetic／mock 離線測試完成，但尚未代表
私人 LIST master 已建立或 Word 視覺驗收已通過；三份樣本的實際校準另屬 Gate C。
若樣本除日數、內容及可證明的自適應排版外仍有無法歸一的結構差異，校準必須
fail closed 並請使用者決定，不能自行挑一份或平均差異。
安裝 ffmpeg、再次 live 官網 request、首次實際 JMA 預報 request、任何雲端 TTS、LINE、
影片與部署都不包含在本次剩餘授權內，必須各自另行確認。
