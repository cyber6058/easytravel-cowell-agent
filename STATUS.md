# STATUS

## 一句話現況

立益 Cowell 專用功能已完成；說明會產生器 Task 2B 的 Yating-only 本機語音管線
與 Task 3 口語稿契約均已通過，下一個未核准工作是 Task 4 URL／PDF 解析。

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
- 本次沒有 live 官網／JMA、Azure、LINE、Word COM 啟動或外部部署。
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
- 本次仍未安裝 ffmpeg、未產生 MP3／完整 6–8 分鐘音訊、未啟動 Word COM，亦未
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
- 本次沒有 live 官網／JMA request、Word COM、ffmpeg 安裝、MP3、完整 6–8 分鐘
  音訊、Azure、LINE、Cowell access 或任何部署／外部發布。

## 下一步

Task 3 已完成；等待使用者另行決定是否核准 Task 4 URL／PDF 解析，不得自動讀取
live 官網或產生完整 6–8 分鐘音訊。Cowell 部分則維持到立益公司電腦 clone、先跑
完整離線測試，再由 OP 登入受控 Chrome，依序驗證 auth status 與 rooms preview。

## 阻塞點

本機無科威登入，因此真實頁面結構與正式 rooms apply 尚未驗證。正式
apply 必須在公司環境針對最終 preview 另行取得當次明確核准。

說明會產生器的 Task 2B 與 Task 3 均已完成，沒有技術阻塞。Task 4 尚未核准，
完整 6–8 分鐘版本尚未產生；新魅力頁面契約、JMA 資料及 LIST Word COM／視覺驗證
也尚未實作或端對端驗證。Azure 已移出第一階段自動流程；任何未來雲端 TTS 與
自動 LINE 傳送仍是獨立核准關卡。

本機 capability probe 與真實 integration 顯示 Yating 可用且正式管線可合成，
`pdftoppm` 可用、Hanhan 僅供舊比較、Word COM 已註冊，但 `ffmpeg` 尚未找到；
Word COM 仍須在 Task 8 以最長 20 秒的隱藏 instance 另測。
Codex 沙箱直接啟動新 `briefing.exe` 時看不到外部 WinGet Poppler 路徑，但同一
程式由專案 Python 啟動可正確偵測，需在一般 OP shell 再驗證 console launcher。
安裝 ffmpeg、live 官網／JMA、任何雲端 TTS、LINE、影片與部署都不包含在本次
核准內，必須各自另行確認。
