# STATUS

## 一句話現況

立益 Cowell 專用功能已完成；大阪、東北、北海道產品的 LIST Word 與繁中語音
產生器已完成 Task 1 純離線資料契約與獨立 `briefing doctor` CLI，下一步為本機
Hanhan 語音垂直切片。

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
- 本次沒有 live 官網／JMA、Azure、LINE、Word COM 啟動或外部部署。

## 下一步

依核准計畫進入 Task 2：先以合成、無公司原文的 fixture 建立 Hanhan WAV／SRT
紅燈測試，再完成 UTF-8 工作檔、PCM 驗證、音訊串接與實際 frame 計時；先交付
約 30 秒本機 Hanhan 樣本讓使用者試聽，通過後才做完整 6–8 分鐘版本。Cowell
部分則維持到立益公司電腦 clone、先跑完整離線測試，再由 OP 登入受控 Chrome，
依序驗證 auth status 與 rooms preview。

## 阻塞點

本機無科威登入，因此真實頁面結構與正式 rooms apply 尚未驗證。正式
apply 必須在公司環境針對最終 preview 另行取得當次明確核准。

說明會產生器目前僅完成 M1／Task 1；新魅力頁面契約、JMA 資料、LIST Word
COM／視覺驗證與 Azure／Hanhan 音訊尚未實作或端對端驗證。任何付費 Azure
資源與自動 LINE 傳送仍是獨立核准關卡。

本機 capability probe 顯示 `pdftoppm` 可用、Hanhan 與 Word COM 已註冊，但
`ffmpeg` 尚未找到；Word COM 仍須在 Task 8 以最長 20 秒的隱藏 instance 另測。
Codex 沙箱直接啟動新 `briefing.exe` 時看不到外部 WinGet Poppler 路徑，但同一
程式由專案 Python 啟動可正確偵測，需在一般 OP shell 再驗證 console launcher。
安裝 ffmpeg、live 官網／JMA、Azure TTS、LINE、影片與部署都不包含在本次核准
內，必須各自另行確認。
