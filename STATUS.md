# STATUS

## 一句話現況

立益 Cowell 專用功能已完成；說明會產生器的 Hanhan 技術切片未通過人工聆聽，
使用者已選定本機 Yating 且缺少時 fail closed，修訂設計正等待書面審閱。

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
- 原實作計畫已標記暫停，需等使用者書面審閱修訂設計後，才重寫 Yating 語音 tasks。
- 本次 Yating 設計修訂後完整離線回歸為 `118 passed, 1 skipped in 4.83s`；skip
  仍是需顯式 opt-in 的真實 Hanhan integration test，沒有拿 skip 當 Yating 驗收。
- ffmpeg 未設定，因此 metadata 正確標示 `MP3_CONVERTER_UNAVAILABLE`；沒有安裝、
  沒有嘗試轉 MP3，已驗證的 WAV／SRT／TXT 均保留。
- 本次沒有 live 官網／JMA、Azure、LINE、Word COM 啟動或外部部署。

## 下一步

請使用者審閱 Yating 修訂設計；確認後重寫實作計畫的語音 tasks，再以
Windows Media Speech 實作整篇連續合成、SSML bookmark SRT 與無 fallback 的失敗契約。
完成管線後先重做 20–30 秒 Yating WAV／SRT 樣本供人工驗收，通過後才產生完整
6–8 分鐘版本。Cowell 部分則維持到立益公司電腦 clone、先跑完整離線測試，再由
OP 登入受控 Chrome，依序驗證 auth status 與 rooms preview。

## 阻塞點

本機無科威登入，因此真實頁面結構與正式 rooms apply 尚未驗證。正式
apply 必須在公司環境針對最終 preview 另行取得當次明確核准。

說明會產生器目前完成 M1 與舊 Hanhan Task 2 的技術驗證，但 Hanhan 未通過人工
聆聽；Yating 修訂仍待書面審閱、實作與正式管線短樣本驗收，完整 6–8 分鐘版本
尚未產生。新魅力頁面契約、JMA 資料及 LIST Word COM／視覺驗證也尚未實作或
端對端驗證。Azure 已移出第一階段自動流程；任何未來雲端 TTS 與自動 LINE
傳送仍是獨立核准關卡。

本機 capability probe 與真實 integration 顯示 `pdftoppm` 可用、Hanhan 可合成、
Word COM 已註冊，但 `ffmpeg` 尚未找到；Word COM 仍須在 Task 8 以最長 20 秒的
隱藏 instance 另測。
Codex 沙箱直接啟動新 `briefing.exe` 時看不到外部 WinGet Poppler 路徑，但同一
程式由專案 Python 啟動可正確偵測，需在一般 OP shell 再驗證 console launcher。
安裝 ffmpeg、live 官網／JMA、任何雲端 TTS、LINE、影片與部署都不包含在本次
核准內，必須各自另行確認。
