# 旅遊產品說明會 Word 與語音產生器實作計畫

日期：2026-08-09
依據：`docs/specs/2026-08-08-travel-briefing-document-audio-design.md`
狀態：Yating 修訂設計、Task 2B、Task 3、Task 4、Task 5 與 Task 6 均已由使用者
核准；Task 1 至 Task 6 的本機實作均已完成（Task 2A Hanhan 僅保留歷史技術
證據）。26 秒 Yating 正式管線樣本已依自然度政策通過人工驗收；Azure Task 已
取消。Task 4 正式頁唯讀驗收已於 2026-08-11 通過；Task 6 已完成離線 JMA XML
實作，第一次實際 JMA 預報讀取仍是獨立核准關卡。

## 目標

在不改變既有 Cowell 護照與分房流程的前提下，新增獨立的
`travel_briefing` 套件與 `easytravel-briefing-materials` 對話式 Skill。
OP 提供一個新魅力旅遊產品 URL、PDF 或兩者後，Skill 能產生可追溯、可審核的
LIST Word 草稿、繁中 MP3／WAV、逐字稿、SRT、manifest 與 review 報告。

實作採「語音優先的垂直切片」：先用合成資料與本機 Yating 完成整篇連續 WAV、
SSML bookmark SRT 與可聽樣本，讓使用者確認正式管線的內容、發音與節奏，再接
官網、PDF、JMA 和 LIST Word。

## 固定邊界

- 新程式放在 `src/travel_briefing/`，不得匯入 Cowell adapter、登入或寫入模組。
- 既有 `cowell` CLI 的四個頂層命令、0.3.2 安裝包與正式功能不得改變。
- 不另購 LLM API；Codex／Claude 依結構化輸入撰寫口語稿，CLI 負責驗證與產出。
- 不自動傳 LINE、不建立影片、不建立或呼叫 Azure Speech、不批次或排程。
- 官網與 JMA 是獨立網路測試關卡；離線測試不能呼叫它們。
- 私有 LIST 範本、來源 PDF、網頁完整回應、音檔與產出檔全部維持 Git 忽略。
- 每一階段先寫失敗測試，再做最小實作，跑完整離線測試後才提交。

## 已確認的本機條件

- 專案虛擬環境可用；測試命令固定使用
  `.\.venv\Scripts\python.exe -X utf8 -m pytest`。
- 系統預設 Python 3.14 沒有 pytest，不能拿它當測試環境。
- 既有 runtime 已有 `httpx`、`playwright`、`PyMuPDF`、`Pillow` 與 `keyring`。
- `pdftoppm` 已在 PATH，可用於 PDF 轉圖 QA。
- Windows Media Speech 已找到 `Microsoft Yating`（`zh-TW`、女性）；同稿人工比較
  已選定 Yating，缺少時不得自動退回 Hanhan。
- Yating 原生短樣本實測為 16 kHz、PCM 16-bit／mono；自動 sentence／word
  boundary metadata 皆為 0，但 SSML `<mark>` 可回傳 `Speech:Bookmark` markers。
- `ffmpeg` 目前不在 PATH；MP3 里程碑前須由使用者核准安裝，或提供既有路徑。
- `winword.exe` 目前不在 PATH；不能據此判定 Word COM 不存在，須以限時 COM
  capability probe 另行驗證。先前 COM 啟動曾逾時，因此 Word 階段必須 fail closed。

## 預定操作介面

新增獨立命令 `briefing`，不掛到 `cowell` 子命令下：

```powershell
briefing doctor --format json
briefing prepare --url <URL> --pdf <PDF> --output-dir <DIR>
briefing check-script --manifest <MANIFEST> --script <TXT>
briefing render --manifest <MANIFEST> --script <TXT> --template <DOC> --tts yating
briefing render --manifest <MANIFEST> --script <TXT> --template <DOC> `
  --confirm-draft-id <DRAFT_ID>
```

- `prepare` 至少接受 `--url` 或 `--pdf` 其中一項，也接受 `--op-values` 與
  `--conflict-decisions` 的本機 JSON。
- `prepare` 只建立新版本 manifest、review 與 agent narration input，不覆蓋舊檔。
- Skill 讀取 narration input，撰寫 TXT，再呼叫 `check-script`。
- `render` 預設永遠產生 DRAFT；只有無阻擋項目且 `--confirm-draft-id` 精確相符時，
  才能產生正式檔。
- 第一階段 `--tts` 只接受 `yating`，且預設值就是 `yating`；不提供 `auto`、
  `hanhan` 或 `azure`，避免隱性 fallback。
- 正式確認不包含 LINE、上傳或任何外部發布。

CLI 沿用穩定 exit code：成功 `0`、需 OP 審核 `20`、來源錯誤 `30`、輸入錯誤
`40`、內部錯誤 `50`。JSON 輸出不能包含憑證、完整網頁、私有文件內容或
OP 電話等敏感資料。

## 里程碑總覽

| 里程碑 | 可驗證成果 | 外部副作用 |
| --- | --- | --- |
| M1 | 獨立資料契約、CLI 骨架與 fail-closed 狀態 | 無 |
| M2 | 本機 Yating 30 秒與完整 6–8 分鐘連續 WAV／bookmark SRT；有 ffmpeg 後含 MP3 | 無 |
| M3 | URL／PDF 擷取、來源合併、衝突與 review | 僅另行核准的公開網頁讀取 |
| M4 | JMA 有效範圍天氣與範圍外提醒 | 僅另行核准的 JMA 讀取 |
| M5 | 私有 LIST 範本 5／6／7 天 Word 與視覺 QA | 本機檔案產出 |
| M6 | 端對端 Skill、三區域驗收與 0.1.0 私有安裝包 | Git push；不部署、不傳 LINE |

## Task 1：建立獨立套件、資料契約與 CLI 骨架（已完成）

狀態：commit `30fd146` 已推送；本節保留為完成紀錄。Yating capability 的增量
變更放在 Task 2B，不重寫這個歷史 commit。

### 檔案

- 新增 `src/travel_briefing/{__init__,__main__,cli,models,serialization,errors,exit_codes}.py`
- 修改 `pyproject.toml`，加入 `briefing = "travel_briefing.cli:main"`
- 新增 `tests/unit/travel_briefing/test_models.py`
- 新增 `tests/unit/travel_briefing/test_cli.py`
- 修改 `tests/unit/test_dedicated_scope.py`

### 實作與驗證

1. 先測 `BriefingDraft`、來源證據、flight、day、notice、OP field、weather、
   conflict、warning 與 artifact 的 JSON round trip。
2. 狀態只允許 `DRAFT_READY`、`BLOCKED`、`CONFIRMED`。
3. `draft_id` 由 canonical manifest、來源雜湊與產生時間計算；來源、天氣或講稿
   變動必須改變 ID。
4. `briefing doctor` 回報 Python、Windows、Hanhan、ffmpeg、Word COM、pdftoppm
   與必要環境變數，不做網路呼叫；Yating 增量檢查由 Task 2B 補上。
5. 測試 `cowell` CLI 仍只暴露 `doctor/auth/passports/rooms`，並禁止
   `travel_briefing` 匯入 Cowell adapter。
6. 執行新測試後再跑完整 `pytest`。

Commit：`feat(briefing): add isolated draft contract and cli`

## Task 2A：完成本機 Hanhan 語音技術切片（已完成、未獲採用）

狀態：commit `547c5f6` 已推送，結構測試通過，但使用者實際聆聽判定聲音不自然且
停頓明顯。保留本節與既有測試作歷史技術證據；正式流程不得自動呼叫 Hanhan。

### 檔案

- 新增 `src/travel_briefing/{capabilities,narration,subtitles,audio}.py`
- 新增 `src/travel_briefing/adapters/windows_speech.py`
- 新增 `scripts/briefing/synthesize_hanhan.ps1`
- 新增 narration、subtitles、audio unit tests 與 Hanhan integration test

### 實作與驗證

1. 用合成且不含公司原文的 narration fixture 寫失敗測試。
2. 依標點與手機字幕長度切成語意段，保留順序與文字雜湊。
3. PowerShell 只接收 UTF-8 JSON 工作檔路徑，不把講稿放進 command line。
4. 每段以 `Microsoft Hanhan Desktop` 輸出 PCM WAV；Python `wave` 驗證並串接，
   再由實際 frame 數建立 SRT。
5. Hanhan 不存在時回報 `LOCAL_TTS_UNAVAILABLE`，不假裝完成。
6. MP3 只透過設定路徑中的 ffmpeg 轉成 44.1 kHz mono 128 kbps；找不到時不安裝，
   WAV／SRT 可測但 MP3 必須 blocked。
7. 輸出不覆蓋既有檔，記錄 SHA-256、秒數、取樣率及聲道。
8. 已產生約 30 秒 Hanhan 樣本供使用者試聽；使用者未通過，因此沒有產生完整
   6–8 分鐘 Hanhan 版本。

Commit：`feat(briefing): add offline Hanhan audio pipeline`

## Task 2B：以 Yating 取代正式本機語音管線（已完成並通過人工試聽）

狀態：離線回歸 `144 passed, 2 skipped`，opt-in Yating integration `1 passed`；
26.087250 秒正式管線樣本及 5 段 bookmark SRT 已通過機械 QA。使用者指出
14.925 秒起「不舒服」的「服」音調略怪，但確認不應為單字建立特例，並同意依
「意思清楚的偶發腔調可接受、關鍵資訊可能誤解才阻擋」原則通過人工驗收。

### 檔案

- 新增 `src/travel_briefing/adapters/windows_media_speech.py`
- 新增 `scripts/briefing/synthesize_yating.ps1`
- 修改 `src/travel_briefing/{capabilities,narration,subtitles,audio,cli}.py`
- 新增 `tests/unit/travel_briefing/test_yating_audio.py`
- 新增 `tests/unit/travel_briefing/test_windows_media_speech.py`
- 新增 `tests/integration/travel_briefing/test_yating_integration.py`
- 修改 `tests/unit/travel_briefing/test_cli.py`

### 實作與驗證

1. 先寫失敗測試固定 canonical narration 與 SSML：XML 特殊字元必須跳脫，
   `segment-001` 前不插 marker，第二段起各插一次唯一
   `<mark name="segment-NNN"/>`，合成後的可見文字必須與 narration 完全相同。
2. `briefing doctor` 只列舉 Windows Media Speech 的 `AllVoices`，要求同時符合
   `DisplayName=Microsoft Yating` 與 `Language=zh-TW`；probe 不合成、不播放，
   也不把 Hanhan 可用誤報成正式 TTS 可用。
3. Python adapter 只把 UTF-8 JSON job 路徑放到 PowerShell command line。job 位於
   OS temp，包含 SSML、預期 voice、暫存 WAV 路徑及 bookmark JSON 路徑；講稿與
   SSML 不得出現在 process arguments、stdout、stderr 或長期 log。
4. PowerShell 以 Windows Media Speech 選定 Yating，保留使用者通過的預設
   speaking rate、pitch、volume 與 silence 設定，整份 SSML 只呼叫一次
   `SynthesizeSsmlToStreamAsync`。不得逐句合成，也不得呼叫 Hanhan 或網路服務。
5. PowerShell 以 `Windows.Media.IMediaMarker` reflection 讀出
   `Speech:Bookmark` 的名稱與 `Time`，把 WAV 與最小 marker JSON 寫到 job 指定的
   全新暫存路徑；任一路徑已存在、voice 不符或輸出為空時 fail closed。
6. Python 實際解碼 WAV header，要求 PCM、16-bit、mono、正取樣率與正 frame 數，
   並以 header 的 frame／sample rate 計算秒數；不得把實測 16 kHz 硬編碼成假定值。
7. bookmark 必須恰好是 `segment-002` 至最後一段，各一次、順序相同、時間嚴格
   遞增且小於 WAV 結尾。第一段 SRT 從 0 開始，後續邊界使用 marker，最後一段
   精確結束於 WAV frame 時間；任一不符都不得產生猜測 SRT。
8. `--tts` 第一階段只接受 `yating`。Yating 缺少、合成失敗、bookmark 失敗或
   結果不明時，回報穩定錯誤與已存在的暫存輸出狀態，不自動呼叫 Hanhan、Azure
   或其他聲音，也不盲目重試。
9. 最終 WAV／SRT／TXT／metadata 都使用 exclusive create，不覆蓋舊檔；metadata
   記錄 `Microsoft Yating`、Windows Media Speech、WAV header、marker count、
   narration hash、各 artifact SHA-256 及明確的 MP3 availability。
10. unit tests 覆蓋 XML escaping、marker 注入、缺少／重複／未知／倒序／越界
    markers、損壞 WAV、timeout、部分輸出、既有輸出及 no-fallback spy；一般測試
    不啟動真實 TTS。
11. integration test 只在 Windows 且
    `RUN_BRIEFING_YATING_INTEGRATION=1` 時真實合成去識別短稿，實際解碼 WAV 並驗證
    bookmarks／SRT；未 opt-in 時保留精確 skip reason。
12. 完整離線測試與 opt-in integration 通過後，產生一份 20–30 秒正式管線樣本，
    由使用者再次驗收流暢度與字幕同步。通過前不得產生完整 6–8 分鐘版本。

Commit：`feat(briefing): add fail-closed Yating audio pipeline`

## Task 3：建立口語稿契約與內容驗證（已完成）

狀態：commit `02f91c5` 已完成；完整離線回歸為 `171 passed, 2 skipped`。兩個 skip
仍是需顯式 opt-in 的真實 Hanhan／Yating integration tests，Task 3 本身的測試沒有
skip。使用者於完成回報後明確回覆「通過」，Task 3 驗收已關閉。

### 檔案

- 新增 `src/travel_briefing/script_policy.py`
- 新增 `src/travel_briefing/script_validation.py`
- 新增 `tests/unit/travel_briefing/test_script_validation.py`
- 新增 `packaging/easytravel-briefing-materials/shared/references/narration-policy.md`

### 實作與驗證

1. manifest 產生 `required_facts`：小費、人數、不可脫隊、巴士時數、保險、
   護照效期、房型、素食、電壓及天氣提醒。
2. `check-script` 驗證段落順序、必要事實、所有關鍵數字、爭議事實未出現及
   預估字數；不能只看到關鍵字就忽略相反語意。
3. Codex／Claude 只能依 narration input 改寫，不可重新抓來源或補猜資訊。
4. 合成後以實際音訊判定 6:00–8:00；只允許一次固定規則的壓縮／補充。
5. 發音字典先涵蓋航空班號、日期、金額、100V 與三區域常見日文地名；未知詞
   留在 review，不任意改字。

Commit：`feat(briefing): validate narration facts and timing`

## Task 4：解析新魅力 URL 與行程 PDF（live 契約已離線修復；待正式頁重驗）

### 檔案

- 新增 `src/travel_briefing/input_validation.py`
- 新增 `src/travel_briefing/adapters/newamazing.py`
- 新增 `src/travel_briefing/adapters/pdf_itinerary.py`
- 新增 `src/travel_briefing/product_lookup.py`
- 新增最小合成 HTML 與去識別 PDF 文字 fixtures
- 新增 NewAmazing 與 PDF parser unit tests
- 修改 `pyproject.toml`，加入唯一新 HTML parser dependency：
  `beautifulsoup4>=4.12,<5`

### 實作與驗證

1. URL allowlist 只接受 HTTPS `www.newamazing.com.tw`，redirect 也必須留在同 host，
   防止 Skill 被用來讀取任意 URL 或內網資源。
2. 優先解析 `GroupDetail.asp` 與官方列印頁；以產品代碼、標題與段落契約定位，
   不使用脆弱的整頁位置索引。
3. 官網 parser 至少輸出產品代碼、名稱、日期、航班、每日行程、飯店與
   「其他說明」各分類。
4. 必要 anchor 缺少時回報 `PARSE_CONTRACT_CHANGED`，不回傳空成功。
5. PDF 使用既有 PyMuPDF 並保留頁碼；掃描型無文字 PDF 回報需 OCR，第一版
   不暗中擴充 OCR。
6. PDF 產品代碼只在唯一且合法時尋找產品頁；零個或多個候選列為 blocked。
7. fixtures 只保留合成 DOM 與必要欄位，不提交完整網頁或私有 PDF。

### 網路關卡

先完成所有離線測試。之後另行取得核准，才以使用者已提供的大阪 URL 做一次
唯讀契約測試；不爬全站、不批次下載。

Commit：`feat(briefing): parse NewAmazing pages and itinerary PDFs`

離線完成紀錄（2026-08-09）：功能 commit `cc547f9`。34 個 Task 4 針對性測試全數通過；
完整離線回歸為 `205 passed, 2 skipped in 6.10s`，compileall 與 staged
`git diff --check` 也通過。測試資料只含合成 HTML、去識別頁面文字及測試期間產生
的暫存 PDF；這個 commit 未包含來源頁面或 live response。

Live 契約紀錄（2026-08-09）：使用者另行核准後，對已提供的大阪產品 URL 執行
恰好一次受限 GET；未跟隨 redirect，HTTP `200`，response `98,076` bytes，SHA-256
`06335de9cfee88e4a33248a6ead9950eaeebdab735ea2542806ca2ff8e3aaf61`。目前 parser 回報
`PARSE_CONTRACT_CHANGED`，缺少契約 anchor「產品資訊」。未保存原始 HTML，也未重試。
第二次 live request 前，須另行核准最小的契約診斷、修復與重測關卡。

Live 契約修復紀錄（2026-08-10）：經逐次明確核准的唯讀結構診斷，確認正式頁不是
舊 fixture 的語意式 section/table，而是 `.product_basic_info`、`#ReferenceFlights`
與 `#DailyItinerary .every_day` 卡片契約；列印控制仍指向同一頁，沒有另一個穩定的
列印頁可替代。parser 升為 `newamazing-html/2`，保留舊契約並新增嚴格卡片 profile，
驗證隱藏產品名稱／代碼、URL 代碼、航班欄位、首末航班日期、每日天次、餐食、飯店
與其他說明。正式頁沒有獨立的每日住宿城市欄位，因此 parser 不猜值；URL-only 產生
`SOURCE_CITY_MISSING` warning，URL+PDF 則保留 PDF 城市供 OP 核對。測試 fixture 為
純合成 DOM，未保存或提交正式頁 HTML、旅客資料或 live response。建立修復 commit
當時尚未重驗正式頁；任何 GET 均須逐次明確核准。針對性 NewAmazing／merge 測試為
`29 passed in 0.36s`；完整離線回歸為 `244 passed, 2 skipped in 5.78s`，compileall 與
`git diff --check` 均通過。

修復後 live 重驗紀錄（2026-08-10）：commit `5e8fed9` 已 push 至 private
`origin/main`。經使用者明確核准，執行恰好一次不 redirect、不 retry 的唯讀 GET；
HTTP `200`、response `98,468` bytes、SHA-256
`2e7a3403a64706b0ab272c22ac2559b691b1048caf7e680149247b7ef9de5e68`。parser 已進入
新版卡片 profile，但於「產品區域」回報 `PARSE_CONTRACT_CHANGED`；沒有保存原始
HTML 或 live response。下一步須先核准產品區域的權威來源設計，不能直接從名稱猜值；
本次 GET 授權已用畢。

## Task 5：實作來源優先、衝突與 OP review（已完成）

### 檔案

- 新增 `src/travel_briefing/{merge,validation,review,op_values}.py`
- 新增 merge、review 與 stale-decision unit tests

### 實作與驗證

1. 表格驅動測試固定 OP > PDF itinerary > 官網 notices > 天氣的來源規則。
2. 日期、天數、航班、飯店、住宿城市、主要景點順序矛盾時建立 blocking conflict。
3. 標點、全半形、簡稱與不改語意的餐食差異只建 warning，採 PDF 文字。
4. 缺少的 OP 欄位使用值 `待 OP 確認` 與 `highlight=yellow`，不能猜測。
5. `op-values.json` 與 `conflict-decisions.json` 綁定上一版 `draft_id`；拒絕過期決定。
6. `review.md` 顯示雙方來源、頁碼／URL、擷取時間與 OP 問題，但遮蔽電話等敏感值。

Commit：`feat(briefing): enforce source precedence and review states`

完成紀錄（2026-08-09）：功能 commit `2bba83f`。來源優先、blocking conflict、
語意等價 warning、9 個黃色 OP 待確認欄位、draft-bound OP 值／衝突決策、狀態重算
及遮蔽敏感資料的 Markdown review 均已完成。34 個 Task 5 針對性測試全數通過；
完整離線回歸為 `239 passed, 2 skipped in 9.67s`，compileall、行寬檢查與 staged
`git diff --check` 均通過。兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／Yating
integration tests。

## Task 6：加入 JMA 短期與週間預報（離線實作已完成）

### 檔案

- 新增 `src/travel_briefing/adapters/jma.py`
- 新增 `src/travel_briefing/weather.py`
- 新增 `src/travel_briefing/data/jma_area_aliases.json`
- 修改 `pyproject.toml` 的 package data 設定
- 新增最小合成 JMA XML fixtures 與 weather unit tests

### 實作與驗證

1. 用標準庫 XML parser 處理 `VPFD51` 與 `VPFW50`，不新增 JMA SDK。
2. 城市映射必須得到唯一 JMA 預報區；初始 alias 只涵蓋大阪、東北、北海道
   實際案例需要的城市。
3. 同日期以較短期、較新發布的資料優先；保存發布時間、取得時間與來源 URL。
4. 超出範圍固定輸出「尚無短期預報，請於出發前更新」，不查歷史平均。
5. JMA 錯誤為 warning／待更新，不得讓其他安全草稿消失。
6. review、Word 與講稿都含 JMA 署名和一般參考免責提醒。

### 網路關卡

離線 XML 測試通過後，另行核准一次 JMA 唯讀測試。測試只抓本次三個區域需要的
資料，不建立背景排程或快取服務。

Commit：`feat(briefing): add JMA forecast adapter`

完成紀錄（2026-08-11）：依核准的
`docs/specs/2026-08-11-jma-weather-enrichment-design.md` 完成標準庫 XML parser、
官方 HTTPS provenance 限制、VPFD51／VPFW50 產品與時間軸驗證、日本日期換算、
同日降水機率最大值、唯一大阪 alias 與測站映射、短期優先／同產品較新發布優先、
同發布時間矛盾 fail closed，以及城市缺漏／未知／超出範圍的固定降級文字。
synthetic XML 與公開 seam 針對性測試為 `12 passed`；完整離線回歸實測為
`270 passed, 2 skipped in 5.64s`，兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
Yating integration tests。compileall 與 `git diff --check` 通過；沒有執行實際
JMA 預報 request，也沒有保存 live response。

## Task 7：Azure F0 TTS（已取消）

2026-08-09 使用者確認沒有 Azure Speech 資源，並選定本機 Yating。第一階段不得
新增 Azure adapter、quota ledger、key／region 設定、`auto` cloud fallback 或
Azure integration test，也沒有本 Task 的 implementation commit。未來若重新考慮
雲端 TTS，必須從新設計與當次核准開始，不能直接恢復本計畫的舊內容。

## Task 8：移植 LIST 範本修補與 Word 視覺 QA

### 檔案

- 新增 `src/travel_briefing/template_contract.py`
- 新增 `src/travel_briefing/word_list.py`
- 新增 `scripts/briefing/patch_list_template.ps1`
- 新增 `scripts/briefing/render_list_template.ps1`
- 新增 template contract、Word plan unit tests 與 private template integration test

### 實作與驗證

1. 先檢查已驗證 `briefing-material-builder` 的 manifest schema 與 patch 行為，移入
   repo 成為單一實作；不得在個人 Skill 與 repo 維護兩份不同邏輯。
2. 私有範本以設定路徑傳入；不複製、不修改原始 `.doc`，只在新 output 目錄操作。
3. capability probe 最長 20 秒建立隱藏 Word COM instance、讀版本後退出。逾時只
   終止本工具確定建立的 PID，絕不能全域停止所有 WINWORD。
4. 範本契約驗證表格數、必要 anchor、merged cells、QR shape 與版面指紋。
5. 以同一 master table 增減 5／6／7 天列，套用黃色 `待 OP 確認`。
6. 先依固定優先縮短景點文字；仍超過一頁時回報 blocked，不無限縮字。
7. Word COM 匯出 PDF，`pdftoppm` 轉 PNG；程式檢查一頁、QR、文字非空與版面統計，
   人工逐頁檢查三份私有樣本。
8. 沒有私有範本環境變數時 integration test 可標示 skip reason；正式驗收不能
   以 skip 當成通過。

Commit：`feat(briefing): patch and validate LIST templates`

離線實作紀錄（2026-08-12）：已將既有 `briefing-material-builder` 的四表格修補
契約移入 repo，新增 5／6／7 天 patch plan、固定安全縮寫、黃色 `待 OP 確認`、
來源不覆寫與 exclusive-create 輸出。Word adapter 只接收 OS temp 中的 UTF-8 job
路徑，並以 nonce、精確 WINWORD PID 與 process start time 綁定所有權；逾時不 retry，
且只能終止本次明確建立的 PID。PowerShell 腳本維持 ASCII-only，中文錨點由 UTF-8
job JSON 傳入，避免 Windows PowerShell 5.1 的無 BOM UTF-8 解碼問題。

範本契約現會驗證四表格、八個固定欄位錨點、合併格可存取座標、四段標題、
header QR candidate、單 section、A4 portrait 與不含團務／PII 文字的 layout
fingerprint。PDF QA 另檢查單頁 A4、必要文字、非空文字與圖片物件，再以明確設定的
`pdftoppm` 產生單張 150 DPI PNG。Task 8 新增 39 個單元測試；完整離線回歸為
`309 passed, 3 skipped in 8.66s`，第三個 skip 是需顯式 opt-in 且必須提供私有範本、
已核准 fingerprint 與 pdftoppm 路徑的 Word integration test。

本紀錄不代表 Task 8 正式驗收完成：本次沒有啟動 Word COM、沒有讀取私有 LIST
範本，也沒有產生或人工查看 5／6／7 天 Word／PDF／PNG。實機 probe、三份私有
範本 integration 與逐頁視覺 QA 仍是獨立核准關卡；正式驗收不能以目前 skip 取代。
離線實作已本機提交為 `3b8c64a`；因 public remote 阻塞，尚未 push。

## Task 9：端對端 workflow、產出與正式確認

### 檔案

- 新增 `src/travel_briefing/workflow.py`
- 新增 `src/travel_briefing/artifact_store.py`
- 新增 `src/travel_briefing/config.py`
- 新增 `config/briefing.example.toml`，只包含 output、template 與 ffmpeg 路徑設定
- 完成 `src/travel_briefing/cli.py`
- 新增 workflow integration test 與 artifact store unit tests
- 修改 `.gitignore`，明確加入 briefing local state 與暫存工作檔名稱

### 實作與驗證

1. 每次建立 `output/briefings/<product-code>/<timestamp>/`；解析後必須仍在指定
   output root 內且不能已存在。
2. 原始外部回應只存在 OS temp；結束或失敗時清理，manifest 只留 hash、欄位證據、
   URL、頁碼與時間。
3. 部分失敗仍保留安全 artifact 與 review；每個 artifact 記錄
   completed／blocked／missing。
4. `render --confirm-draft-id` 驗證目前 manifest hash、零 blocking conflicts、
   零必要黃色 OP 欄位、Word QA 及音訊 QA。
5. CONFIRMED 只移除檔名 DRAFT 與黃色狀態，不觸發 LINE、上傳或外部 write。
6. PII／secret scan 檢查 Git staged files 與 log；產出檔維持 ignored。

Commit：`feat(briefing): orchestrate draft and confirmed artifacts`

## Task 10：建立 Codex／Claude 對話 Skill 與 0.1.0 安裝包

### 檔案

- 擴充 `packaging/easytravel-briefing-materials/`
- 建立 canonical `packaging/easytravel-briefing-materials/shared/SKILL.md`，引用 Task 3
  已建立的 narration policy
- 新增 briefing 專用 `app-pyproject.toml`
- 新增共享 references：CLI、來源規則、OP review、語音與範本設定
- 新增 Codex plugin manifest 與 tool-specific thin wrapper
- 新增 Claude thin wrapper／安裝說明，由 canonical Skill 產生
- 新增 `scripts/build_easytravel_briefing_package.ps1`
- 新增 `tests/unit/test_briefing_packaging.py`
- 修改 `README.md`
- 修改 `AGENTS.md` 的核准 scope，只加入本設計功能，不放寬 Cowell 寫入範圍

### 實作與驗證

1. 安裝包版本固定 `EasyTravel-Briefing-Materials-0.1.0.zip`。
2. 保留現有 Cowell 0.3.2 zip 與 packaging 目錄，不覆蓋或重新命名；briefing build
   只複製 `src/travel_briefing`、briefing scripts/config 與專用 pyproject，不夾帶
   Cowell package、session 或 credentials。
3. Codex／Claude wrapper 只描述同一套 prepare → agent script → check → render →
   OP confirm 流程，測試兩份規則內容 hash 一致。
4. Skill 明確禁止猜值、付費資源、自動 LINE、影片與未核准網路測試。
5. 安裝器建立自己的 app／venv 與 config，不讀 Cowell session 或 credentials。
6. 執行 Skill validator、plugin validator、build，並計算 zip SHA-256。

Commit：`build(briefing): package conversational workflow`

## Task 11：三區域驗收與交付

### 離線驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
git diff --check
git status --short
```

另外執行專案完整測試、Skill／plugin validator、briefing 0.1.0 build、zip allowlist，
以及 staged secret、PII、來源文件與產出副檔名掃描。

### 實際案例

在取得各自關卡核准後，以使用者提供的私有資料驗收：

1. 大阪 URL-only；
2. 東北 PDF-only，並測產品頁唯一解析；
3. 北海道 URL+PDF，並建立一個受控衝突案例；
4. 5、6、7 天 Word 各一份；
5. Yating 正式管線短樣本通過人工聲音與字幕同步驗收，且 capability 缺少時
   確實 fail closed、不產生 Hanhan 或雲端語音；
6. 至少一份完整 6–8 分鐘 MP3／WAV／TXT／SRT；
7. JMA 範圍內與範圍外各一例；
8. 一個 `BLOCKED` 草稿及一個由 OP 明確確認的本機 `CONFIRMED` 產出。

每份 Word 必須逐頁人工查看，每份最終語音必須實際播放抽聽。未完成 Yating
正式管線或 Word 實機驗證時，不能因離線測試通過就宣稱第一階段完成。

### 文件與提交

- 更新 `STATUS.md`：實際測試輸出、安裝包 SHA、未驗證項目與下一關卡。
- 每個小任務使用上列 commit；每個安全里程碑結束依專案規則 push private remote。
- 不部署、不傳 LINE、不上傳來源或產出。

最後 Commit：`docs(briefing): record 0.1.0 acceptance results`

## 計畫自檢

- 12 個 Task headings：5 個已完成、1 個已完成 live 契約離線修復但待正式頁重驗、
  1 個已取消、5 個尚待執行。
- 12 個 commit 邊界：6 個既有 implementation commits、1 個新增的 Task 4 live
  契約修復邊界、5 個後續小步 commits；取消的 Task 7 沒有 implementation commit。
- 0 個未定欄位或佔位內容。
- 0 個可執行的 Azure adapter／key／quota／自動 TTS selector；第一階段只有
  `--tts yating`。
- Task 8 離線程式已完成，但 Word COM、私有 LIST 範本與視覺 QA 仍未執行。下一個
  外部入口須先解除 public GitHub remote 的 push 阻塞；實際 JMA 預報、Task 8
  integration 與 push 仍各自需要明確核准，不能合併推定。

## 實作核准關卡

Task 2B、Task 3、Task 4 離線解析與 Task 5 已獲核准並完成本機程式與測試；
Task 2B 的短樣本也已通過人工試聽。Task 4 的 live 結構診斷、離線修復與修復後
重驗均已執行；重驗在產品區域安全阻擋，所有 GET 授權均已用畢。下列動作仍需在
發生前另行取得明確核准：

1. 安裝或下載 ffmpeg；
2. 再次對新魅力官網或首次對 JMA 執行 live request；
3. 在其他目標電腦安裝或啟用 Yating／Windows 語言元件；
4. 啟動 Word COM、讀取私有 LIST 範本或執行 Word 視覺驗收；
5. 傳送 LINE、上傳檔案、部署服務或製作影片；
6. 未來新增或呼叫任何雲端 TTS。

Task 2B 的 20–30 秒 Yating 正式管線樣本已通過使用者試聽與 SRT 檢查；Task 3、
Task 4 離線解析、live 卡片結構修復、產品區域 OP 確認及 Task 5 均已完成；Task 4
正式頁唯讀驗收於 2026-08-11 通過，會建立 `DRAFT_READY` 與待 OP 確認區域。Task 6
離線實作已完成；第一次實際 JMA 預報讀取、完整 6–8 分鐘語音及所有其他外部關卡
仍未授權。
