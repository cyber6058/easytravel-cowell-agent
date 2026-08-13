# STATUS

## 一句話現況

說明會產生器 0.2.0 的 Gate I 已完成；Gate C `5992` mixed-width 程式修正已完成離線
驗證，schema-2 欄寬指紋改讀固定 prototype cells，不再使用
`Columns.Item(...).Width`。本回合未讀三份 LIST、未啟動 Word 或校準，既有 private
reviews 均未變；完整離線測試 `451 passed, 3 skipped`，未 push。

## 這次做了什麼

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

## 下一步

Gate C mixed-width 程式修正與離線回歸已完成。下一步仍須由使用者另行明確核准，
才能再次讀取相同三份 LIST、啟動 Word，並於另一個 exclusive private 目錄校準一次；
本回合的修正授權不包含該實機驗證。只有 Gate C 成功建立並驗證 master 後，才分別
取得 Gate V（4／5／6／7／8／12 天 Word 視覺 QA）與 Gate E
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

Gate I 已完成，沒有剩餘安裝阻塞。Gate C header tail 契約已修訂；`5992` 已證實由
schema 2 對非均勻 table 1 的 column-width member 存取觸發，而非 header mutation；
mixed-width 程式路徑現已完成離線修正，但尚未以三份真實 LIST／Word 重新驗證。
既有 private reviews 與 `5992-diagnostic.json` 不能覆蓋或刪除；新的 Word 回合、再次
讀取三份 LIST 或重跑 calibration 都需要新的明確核准。

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
