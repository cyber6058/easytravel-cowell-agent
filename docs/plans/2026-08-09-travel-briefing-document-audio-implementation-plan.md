# 旅遊產品說明會 Word 與語音產生器實作計畫

日期：2026-08-09
依據：`docs/specs/2026-08-08-travel-briefing-document-audio-design.md`
狀態：等待使用者核准後才開始實作

## 目標

在不改變既有 Cowell 護照與分房流程的前提下，新增獨立的
`travel_briefing` 套件與 `easytravel-briefing-materials` 對話式 Skill。
OP 提供一個新魅力旅遊產品 URL、PDF 或兩者後，Skill 能產生可追溯、可審核的
LIST Word 草稿、繁中 MP3／WAV、逐字稿、SRT、manifest 與 review 報告。

實作採「語音優先的垂直切片」：先用合成資料與本機 Hanhan 產出可聽樣本，讓
使用者先確認內容、發音與節奏，再接官網、PDF、JMA、Azure 和 LIST Word。

## 固定邊界

- 新程式放在 `src/travel_briefing/`，不得匯入 Cowell adapter、登入或寫入模組。
- 既有 `cowell` CLI 的四個頂層命令、0.3.2 安裝包與正式功能不得改變。
- 不另購 LLM API；Codex／Claude 依結構化輸入撰寫口語稿，CLI 負責驗證與產出。
- 不自動傳 LINE、不建立影片、不建立付費 Azure 資源、不批次或排程。
- 官網、JMA、Azure 都是獨立網路測試關卡；離線測試不能呼叫它們。
- 私有 LIST 範本、來源 PDF、網頁完整回應、音檔與產出檔全部維持 Git 忽略。
- 每一階段先寫失敗測試，再做最小實作，跑完整離線測試後才提交。

## 已確認的本機條件

- 專案虛擬環境可用；測試命令固定使用
  `.\.venv\Scripts\python.exe -X utf8 -m pytest`。
- 系統預設 Python 3.14 沒有 pytest，不能拿它當測試環境。
- 既有 runtime 已有 `httpx`、`playwright`、`PyMuPDF`、`Pillow` 與 `keyring`。
- `pdftoppm` 已在 PATH，可用於 PDF 轉圖 QA。
- `ffmpeg` 目前不在 PATH；MP3 里程碑前須由使用者核准安裝，或提供既有路徑。
- `winword.exe` 目前不在 PATH；不能據此判定 Word COM 不存在，須以限時 COM
  capability probe 另行驗證。先前 COM 啟動曾逾時，因此 Word 階段必須 fail closed。

## 預定操作介面

新增獨立命令 `briefing`，不掛到 `cowell` 子命令下：

```powershell
briefing doctor --format json
briefing prepare --url <URL> --pdf <PDF> --output-dir <DIR>
briefing check-script --manifest <MANIFEST> --script <TXT>
briefing render --manifest <MANIFEST> --script <TXT> --template <DOC> --tts auto
briefing render --manifest <MANIFEST> --script <TXT> --template <DOC> `
  --confirm-draft-id <DRAFT_ID>
```

- `prepare` 至少接受 `--url` 或 `--pdf` 其中一項，也接受 `--op-values` 與
  `--conflict-decisions` 的本機 JSON。
- `prepare` 只建立新版本 manifest、review 與 agent narration input，不覆蓋舊檔。
- Skill 讀取 narration input，撰寫 TXT，再呼叫 `check-script`。
- `render` 預設永遠產生 DRAFT；只有無阻擋項目且 `--confirm-draft-id` 精確相符時，
  才能產生正式檔。
- 正式確認不包含 LINE、上傳或任何外部發布。

CLI 沿用穩定 exit code：成功 `0`、需 OP 審核 `20`、來源錯誤 `30`、輸入錯誤
`40`、內部錯誤 `50`。JSON 輸出不能包含 Azure 金鑰、完整網頁、私有文件內容或
OP 電話等敏感資料。

## 里程碑總覽

| 里程碑 | 可驗證成果 | 外部副作用 |
| --- | --- | --- |
| M1 | 獨立資料契約、CLI 骨架與 fail-closed 狀態 | 無 |
| M2 | 本機 Hanhan 30 秒與完整 6–8 分鐘 WAV／SRT；有 ffmpeg 後含 MP3 | 無 |
| M3 | URL／PDF 擷取、來源合併、衝突與 review | 僅另行核准的公開網頁讀取 |
| M4 | JMA 有效範圍天氣與範圍外提醒 | 僅另行核准的 JMA 讀取 |
| M5 | Azure HsiaoChen F0 受額度保護的短樣本與完整備援 | 僅另行核准的 Azure 呼叫 |
| M6 | 私有 LIST 範本 5／6／7 天 Word 與視覺 QA | 本機檔案產出 |
| M7 | 端對端 Skill、三區域驗收與 0.1.0 私有安裝包 | Git push；不部署、不傳 LINE |

## Task 1：建立獨立套件、資料契約與 CLI 骨架

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
   與必要環境變數，不做網路呼叫。
5. 測試 `cowell` CLI 仍只暴露 `doctor/auth/passports/rooms`，並禁止
   `travel_briefing` 匯入 Cowell adapter。
6. 執行新測試後再跑完整 `pytest`。

Commit：`feat(briefing): add isolated draft contract and cli`

## Task 2：完成本機 Hanhan 語音垂直切片

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
8. 先產生約 30 秒 Hanhan 樣本供使用者試聽；通過後才產生完整 6–8 分鐘版本。

Commit：`feat(briefing): add offline Hanhan audio pipeline`

## Task 3：建立口語稿契約與內容驗證

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

## Task 4：解析新魅力 URL 與行程 PDF

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

## Task 5：實作來源優先、衝突與 OP review

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

## Task 6：加入 JMA 短期與週間預報

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

## Task 7：加入受額度保護的 Azure F0 TTS

### 檔案

- 新增 `src/travel_briefing/adapters/azure_speech.py`
- 新增 `src/travel_briefing/quota_ledger.py`
- 新增 Azure Speech 與 quota ledger unit tests
- 新增 `config/briefing.example.toml`

### 實作與驗證

1. 直接用既有 `httpx` 呼叫 Azure Speech REST，不新增 Azure SDK。
2. 金鑰只讀 `AZURE_SPEECH_KEY`，區域只讀 `AZURE_SPEECH_REGION`；錯誤與 log
   不得回顯 header、key 或完整 SSML。
3. 設定必須宣告 `tier = "F0"`；缺少、非 F0 或未取得本次 cloud-TTS 核准時，
   `auto` 直接選 Hanhan。
4. Asia/Taipei 每月 ledger 在 450,000 字元停止；先 reserve，成功後 commit，
   未知結果不可盲目重送，改查 ledger／產出後交由 OP 決定。
5. 每次只允許一個並行要求，使用 `zh-TW-HsiaoChenNeural` 與 `rate=-8%`。
6. Azure 失敗只 fallback 一次 Hanhan，不循環重試。
7. unit tests 以 `respx` 模擬成功、401、429、timeout、未知結果與金鑰遮蔽。

### 真實服務關卡

使用者自行建立或提供已確認的 F0 資源後，先估算字數並顯示剩餘本機預算；取得
當次核准才合成 20–30 秒樣本。使用者聆聽通過後才產生完整音訊。程式不得建立、
升級或修改 Azure 資源。

Commit：`feat(briefing): add guarded Azure F0 synthesis`

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

## Task 9：端對端 workflow、產出與正式確認

### 檔案

- 新增 `src/travel_briefing/workflow.py`
- 新增 `src/travel_briefing/artifact_store.py`
- 新增 `src/travel_briefing/config.py`
- 修改 `config/briefing.example.toml`，加入 output、template 與 ffmpeg 路徑設定
- 完成 `src/travel_briefing/cli.py`
- 新增 workflow integration test 與 artifact store unit tests
- 修改 `.gitignore`，明確加入 briefing local state／ledger 名稱

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
- 完善 Task 3 建立的 canonical
  `packaging/easytravel-briefing-materials/shared/SKILL.md`
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
5. Hanhan 與 Azure HsiaoChen 各一段短樣本，最終選定預設聲音；
6. 至少一份完整 6–8 分鐘 MP3／WAV／TXT／SRT；
7. JMA 範圍內與範圍外各一例；
8. 一個 `BLOCKED` 草稿及一個由 OP 明確確認的本機 `CONFIRMED` 產出。

每份 Word 必須逐頁人工查看，每份最終語音必須實際播放抽聽。未完成 Azure 或
Word 實機驗證時，不能因離線測試通過就宣稱第一階段完成。

### 文件與提交

- 更新 `STATUS.md`：實際測試輸出、安裝包 SHA、未驗證項目與下一關卡。
- 每個小任務使用上列 commit；每個安全里程碑結束依專案規則 push private remote。
- 不部署、不傳 LINE、不上傳來源或產出。

最後 Commit：`docs(briefing): record 0.1.0 acceptance results`

## 實作核准關卡

本計畫核准後，可直接開始 Task 1 的純離線程式與測試。下列動作仍需在發生前
另行取得明確核准：

1. 安裝或下載 ffmpeg；
2. 對新魅力官網或 JMA 執行 live request；
3. 使用 Azure key 合成任何真實音訊；
4. 建立、升級或改成付費 Azure 資源；
5. 傳送 LINE、上傳檔案、部署服務或製作影片。

Task 2 的 30 秒本機 Hanhan 樣本完成後先停下來讓使用者試聽；這是本計畫第一個
產品體驗關卡，也是繼續完整語音與後續 Word 之前的優先回饋點。
