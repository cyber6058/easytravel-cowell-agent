# STATUS

## 一句話現況

立益 Cowell 專用功能已完成；大阪、東北、北海道產品的 LIST Word 與繁中語音
產生器設計已由使用者正式確認；分階段實作計畫已寫成草稿，尚未開始實作。

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
- 本次只有文件變更，未修改程式或執行付費服務、LINE 傳送及真實產出。
- 本次重新執行完整離線測試：`97 passed in 15.32s`。
- 使用者已確認
  `docs/specs/2026-08-08-travel-briefing-document-audio-design.md`。
- 新增語音優先的分階段實作計畫：
  `docs/plans/2026-08-09-travel-briefing-document-audio-implementation-plan.md`。
- 原流程指定的 `writing-plans` Skill 本機未安裝，因此以同等的檔案／測試／commit
  粒度手動建立計畫；未開始功能實作。
- 計畫自檢結果：11 tasks、11 commits、0 placeholders；完整離線測試為
  `97 passed in 5.96s`。

## 下一步

請使用者審閱並核准新的實作計畫；核准後從 Task 1 純離線資料契約與 CLI 開始，
並在 Task 2 先交付 30 秒本機 Hanhan 試聽。Cowell 部分則維持到立益公司電腦
clone、先跑完整離線測試，再由 OP 登入受控 Chrome，依序驗證 auth status 與
rooms preview。

## 阻塞點

本機無科威登入，因此真實頁面結構與正式 rooms apply 尚未驗證。正式
apply 必須在公司環境針對最終 preview 另行取得當次明確核准。

說明會產生器目前只有設計：新魅力頁面契約、JMA 資料、LIST Word COM／視覺
驗證與 Azure／Hanhan 音訊尚未實作或端對端驗證。任何付費 Azure 資源與自動
LINE 傳送仍是獨立核准關卡。

本機 capability probe 顯示 `pdftoppm` 可用，但 `ffmpeg` 與 `winword.exe` 不在
PATH；Word COM 仍須限時另測。安裝 ffmpeg、live 官網／JMA、Azure TTS、LINE、
影片與部署都不包含在計畫文件核准內，必須各自另行確認。
