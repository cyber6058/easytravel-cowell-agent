# sherpa-onnx Windows runtime-only capability proof 設計

日期：2026-08-20

狀態：口頭設計已核准；等待使用者審閱本書面版本

性質：Gate D2 的隔離式能力證明設計，不是下載、解壓、執行、模型載入或語音合成授權

依據：

- `docs/research/2026-08-20-smartsub-installer-compatibility.md`
- `docs/specs/2026-08-19-free-first-briefing-voice-pilot-design.md`
- `docs/plans/2026-08-19-free-first-briefing-voice-pilot-implementation-plan.md`

## 1. 背景與決策目的

SmartSub 3.7.0 installer 已在本機與官方 repository issue #432 呈現完全相同的七欄
APPCRASH signature。沒有官方 fix 或 workaround，也沒有證據支持以 admin、silent mode、
compatibility mode、不同路徑或重新執行相同 installer 可以安全解決，因此不再重跑或
變形執行 SmartSub 3.7.0 installer。

官方 sherpa-onnx 提供不依賴 SmartSub／Electron／NSIS 的 Windows x64 CPU runtime。
Gate D2 的唯一目的，是判定這個固定 runtime 能否在本機 Windows 11 25H2 完成
version／help 級啟動並正常結束。

Gate D2 不回答：

- ZipVoice model 能否載入；
- i7-8565U／8 GB RAM 的推論速度或記憶體峰值；
- 本人聲線、自然度、A 問題或 B 問題是否改善；
- Emilia-linked model 是否可供 EasyTravel 商用；
- sherpa-onnx 是否可接入正式 briefing workflow。

## 2. 套件判定階梯

為了讓「哪個套件可以用」有可驗證而不誇大的答案，判定分為四層：

| 層級 | 能回答的問題 | 目前狀態 |
|---|---|---|
| SmartSub installer | SmartSub 3.7.0 能否在本機完成安裝 | 已否決；同一 APPCRASH 已重現 |
| Gate D2 runtime proof | 官方 sherpa-onnx CLI 能否在本機啟動 | 本設計要回答 |
| 後續 model-load gate | 固定 ZipVoice model 能否在資源限制內載入 | 不在本設計 |
| 後續 Gate R | 實際聲音是否自然、像本人並勝過 Yating | 不在本設計 |

因此 D2 通過只能把 sherpa-onnx 標為「runtime 可啟動的候選」，不能標為「語音品質
已可用」。真正讓使用者聽音驗收，仍需要後續 model-load 與 synthesis 的新書面關卡。

## 3. 固定資產

Gate D2 唯一允許評估的上游資產為：

| 欄位 | 固定值 |
|---|---|
| release | `v1.13.6` |
| asset | `sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2` |
| URL | `https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.6/sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2` |
| bytes | `24,497,928` |
| SHA-256 | `4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613` |
| expected root | `sherpa-onnx-v1.13.6-win-x64-shared-MT-Release` |

URL、release、檔名、bytes、digest 或 expected root 任一不符即停止。不得換鏡像、舊版、
新版、Python wheel、npm package、source build、CUDA pack 或 Vulkan pack。

## 4. 已選方案與關卡

選定方案是擴充既有 `scripts/voice_pilot/` 隔離邊界，但建立獨立模組，避免擴大已承擔
稿件、WAV 與盲測責任的 `pilot.py`。

### Gate D2-I：synthetic-only 離線安全骨架

只允許建立驗證模組與 synthetic tests：

- 不下載真實 asset；
- 不讀取既有 model archive 或 vocoder；
- 不建立 per-user runtime；
- 不執行任何第三方 binary；
- 不讀取影片、音訊或逐字稿；
- 不合成、不登入、不上傳、不 push。

### Gate D2-X：exact runtime download 與有簽章 proof

只有 D2-I 完成並取得新的精確授權後，才允許：

1. 從唯一固定 URL 下載唯一 runtime archive；
2. 驗證 bytes／SHA-256；
3. 唯讀列出 archive 並通過安全檢查；
4. 解壓到全新 per-user staging；
5. 建立檔案 hashes 與 Authenticode inventory；
6. 只有所有將被載入的 executable／DLL 之 Authenticode 均為 `Valid` 時，執行
   version／help proof；
7. 寫下 evidence 並停止。

### Gate D2-U：unsigned exact-hash execution

若任一 load-candidate executable／DLL 為 `NotSigned`，D2-X 必須停在 inventory。只有
使用者另行確認 outer archive SHA-256、完整 load-candidate inventory SHA-256、mandatory
executable SHA-256 與每個 `NotSigned` 狀態後，才能執行相同 version／help proof。任何
其他簽章錯誤一律阻擋，不提供 bypass 關卡。

Gate D2-I、D2-X 與 D2-U 互不自動授權。前一關通過不代表下一關已核准。

## 5. Repository 元件與修改範圍

### `scripts/voice_pilot/runtime_proof.py`

獨立的標準函式庫模組與 CLI，責任限於：

- 固定 `RuntimeAssetSpec`；
- 驗證 local archive 的 bytes 與 SHA-256；
- 建立及驗證安全 archive plan；
- 逐檔解壓到全新 staging；
- 建立 extracted-file／Authenticode inventory；
- 檢查固定執行命令；
- 執行 bounded runtime proof；
- 寫入去識別、可重驗的 evidence JSON。

它不得含網路 client、model options、TTS text、reference audio、output WAV、SmartSub、
Yating、cloud、login、upload、LINE、Cowell 或正式 briefing import。

### `tests/unit/voice_pilot/test_runtime_proof.py`

只使用程式建立的 synthetic `.tar.bz2`、假 executable metadata 與 injected process
runner。tests 不執行真實 executable、不依賴網路，也不寫入 per-user production root。

### 不得修改

- `scripts/voice_pilot/pilot.py`；
- `src/travel_briefing/`；
- 既有 `tests/unit/travel_briefing/`；
- 正式 CLI、Skill、plugin、package version、schema 與 Yating provider；
- private LIST master、calibration、既有 briefing artifacts 或 current DRAFT；
- Cowell、NewAmazing、JMA、Word、LINE、Cloudflare 或 deployment files；
- project dependencies、registry、system PATH、firewall、service 或 scheduled task。

設計、後續實作計畫與 `STATUS.md` 可以依各自關卡更新。runtime、archive、inventory 及
evidence 永遠不進 Git。

## 6. 固定 per-user 路徑

只有 Gate D2-X 才能建立：

```text
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\downloads\sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2.partial
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\downloads\sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\runtime-staging\{run-id}\
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\runtime\sherpa-onnx\1.13.6\
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\proofs\runtime-v1.13.6-{run-id}\
```

模組必須拒絕 repository 內路徑、相對路徑、symlink／junction／reparse escape、已存在的
staging／final target 及不在固定 per-user root 下的 resolved path。

下載前，同一 volume 的可用空間必須至少為 2 GiB；這同時覆蓋 fixed archive、2 GiB
解壓安全上限與 evidence overhead。低於門檻即停止，不縮小 safety limits 勉強執行。

不自動刪除或覆蓋 `.partial`、archive、staging、runtime 或 evidence。任何清理均須先列出
resolved absolute paths，再取得新的明確授權。

## 7. 資料流

```text
官方 asset
  -> 全新 .partial
  -> compressed bytes 與 SHA-256
  -> 正式 archive filename
  -> archive plan 安全檢查
  -> 全新 staging 逐檔解壓
  -> extracted tree 與 Authenticode inventory
  -> load-candidate signatures 全為 Valid，否則依狀態停止
  -> allowlisted version/help command
  -> evidence JSON
  -> 停止
```

repository 模組不負責網路下載。Gate D2-X 的 operator command 使用固定 PowerShell
下載命令與全新 `.partial`；下載成功不代表可解壓，解壓成功也不代表可執行。

## 8. Archive 安全契約

Archive inspection 必須在任何寫檔前建立完整 plan，並拒絕：

- absolute path、drive-qualified path、UNC path、`..` traversal 或 empty component；
- Windows alternate data stream colon；
- trailing dot／space 及 `CON`、`PRN`、`AUX`、`NUL`、`COM1`–`COM9`、
  `LPT1`–`LPT9` 等 device name；
- symlink、hardlink、device、FIFO、socket、sparse／unknown member type；
- duplicate normalized path、case-fold collision 或 file／directory prefix collision；
- 多個 top-level roots 或不等於 fixed expected root；
- 單檔超過 1 GiB、總解壓量超過 2 GiB 或 entries 超過 20,000。

解壓不得使用 `extractall`。只依已驗證 plan 建立 directory，再把 regular-file bytes
逐檔寫入全新路徑；每次寫入前後都確認 resolved target 仍位於 staging。中途失敗保留
staging 與 evidence，不 rename 成 final target，也不自動重試。

Outer archive digest 是上游 identity。Inner hashes 用來把 inventory 與後續執行綁定，
但因上游未逐檔發布 digest，不能把自行計算的 inner hashes 描述為上游簽署證據。

## 9. Runtime execution 契約

Mandatory proof：

```text
sherpa-onnx-offline-tts.exe --help
```

若 archive 唯一包含 `sherpa-onnx-version.exe`，可另執行該 version utility；缺少它不以
猜測的 `--version` 替代。`--help` 必須存在且 exit `0`，輸出必須包含已鎖定的 TTS／
ZipVoice options，至少包括 provider、threads、ZipVoice encoder／decoder、reference
audio／text 及 output filename；這些 options 只驗證 help text，不提供實際值。

執行限制：

- `subprocess` argument list、`shell=False`、stdin closed；
- cwd 固定為 extracted executable directory；
- 最長 30 秒；
- 不接受 text、model、reference、output、server、port 或 network argument；
- 不持久修改 PATH；必要時只在 child environment prepend extracted `bin`／`lib`；
- 不使用 admin、compatibility mode、debugger、DLL replacement 或 alternate runtime；
- 執行前後 SmartSub、sherpa 相關 process 與 TCP listener 均須沒有新增殘留。

沒有新 listener／prompt 只能描述為本次觀測結果，不能誇大為已證明 binary 絕無任何
瞬時 outbound activity。

## 10. Authenticode 與執行停點

對所有將被載入的 `.exe`／`.dll` 記錄：relative path、bytes、SHA-256、Authenticode
status、status message、signer subject、issuer、thumbprint 與 timestamp certificate。

`load-candidate inventory` 固定包含 allowlisted proof executable 及 extracted tree 中每個
`.dll`。Rows 依 normalized relative path 排序，以 UTF-8 canonical JSON 計算單一 SHA-256，
讓 Gate D2-U 的確認綁定完整 load set，而不是只綁一個入口 `.exe`。

- 所有 load-candidate 均為 `Valid`：在 Gate D2-X 精確授權內，可進入 allowlisted proof。
- 任一 load-candidate 為 `NotSigned`：停止並提出綁定完整 inventory 的 Gate D2-U
  exact-hash 確認。
- `HashMismatch`、`NotTrusted`、`UnknownError` 或任何其他狀態：阻擋，不提供 bypass。

GitHub outer digest 與 `NotSigned` 可以共同建立可追溯 identity，但不能被描述成 publisher
signature，也不能自動授權 execution。

## 11. Evidence 契約

Evidence JSON 至少記錄：

- schema／run ID／UTC 與 Asia/Taipei timestamp；
- OS edition、version、build、architecture、CPU 與 RAM；
- outer asset URL、release、filename、bytes、SHA-256；
- archive member count、total uncompressed bytes、expected root 與 plan hash；
- extracted file inventory 與 Authenticode fields；
- exact command argv、cwd、child-only environment delta、timeout；
- start／end、wall time、exit code、stdout／stderr bytes、hash 與 bounded text；
- process／listener before-after、Windows Event 1000 檢查；
- final state：`READY_TO_EXECUTE`、`BLOCKED_UNSIGNED`、`PASSED` 或 `FAILED`；
- failure code 與未執行的後續步驟。

Evidence 不記錄 model、影片、音訊、reference text、TTS text、旅客資料、帳號、token、
完整 home listing 或不必要的絕對私人路徑。

## 12. Fail-closed 規則

下列任一事件立即停止：

- URL、bytes、SHA-256、expected root 或資產名稱不符；
- download 失敗、`.partial` 已存在、磁碟不足或目的地已存在；
- archive safety contract 失敗或解壓中斷；
- mandatory executable 缺少、重複、位於非預期 root 或被 reparse；
- signature 不符合當前已核准關卡；
- command timeout、crash、nonzero exit 或 help contract 不符；
- Windows Event 1000、新殘留 process／listener 或無法判定執行結果；
- 程式要求 model、文字、reference、output、admin 或額外 dependency。

停止後不得：自動 retry、resume partial、換來源、換版本、改 PATH／registry／firewall、
下載 Visual C++ runtime、pip/npm package、ASR、CUDA、Vulkan 或 model。需要任何新依賴時，
先回到書面計畫與新授權。

## 13. Gate D2-I 測試與驗證

Synthetic tests 至少涵蓋：

1. exact bytes／SHA-256 通過，任一不符失敗；
2. absolute、drive、UNC、`..`、ADS、device name 與 trailing dot／space；
3. symlink、hardlink、special member 與 unknown member；
4. duplicate、case-fold 與 file／directory prefix collision；
5. multiple／wrong top-level root 與 size／entry limits；
6. 已存在 output、repo 內 path、reparse escape 與中斷 staging；
7. safe extraction 不使用 `extractall` 且不覆蓋；
8. executable missing／duplicate／unexpected location；
9. allowlisted argv、`shell=False`、closed stdin、cwd、child-only env 與 timeout；
10. model／text／reference／output arguments 被拒絕；
11. `Valid`、`NotSigned` 與其他 signature status 的不同停點；
12. evidence schema、bounded output、hashes、no-private-content 與 tamper detection。

驗證命令必須包含：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest tests\unit\voice_pilot\test_runtime_proof.py -q
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q scripts\voice_pilot tests\unit\voice_pilot
git diff --check
```

另需證明：

- `src/travel_briefing/` 與既有 `tests/unit/travel_briefing/` 相對基線 0 diff；
- 新模組沒有 network、cloud、model load、TTS、upload、LINE 或 Cowell client；
- SmartSub、sherpa 與 WINWORD process 在 tests 前後均為 0；
- 沒有真實 asset、archive、executable、DLL、model 或 evidence 進 Git；
- complete suite 的實際 pass／skip count與duration有記錄，不以預估代替。

## 14. 成功與失敗的產品判定

### D2-I 成功

只能宣稱離線驗證骨架及 synthetic safety contract 已通過；不證明 runtime 存在或可跑。

### D2-X／D2-U 成功

只有以下條件同時成立才可宣稱 runtime capability proof 通過：

1. exact official outer asset identity 通過；
2. archive plan 與 isolated extraction 通過；
3. signature 符合當前核准關卡；
4. mandatory `sherpa-onnx-offline-tts.exe --help` 在 30 秒內 exit `0`；
5. required ZipVoice options 出現在 help output；
6. 沒有 crash、Event 1000、新殘留 process／listener、model request 或 output audio；
7. evidence 完整且可重驗。

通過時的唯一產品結論是：

> SmartSub 3.7.0 installer 不可用；官方 sherpa-onnx v1.13.6 Windows CPU runtime
> 在這台 Windows 11 25H2 電腦上可啟動，值得進入下一個獨立 model-load 設計。

失敗時如實記錄 failure code並停止，不自動改評估 GPT-SoVITS、pip/npm 或付費雲端。

## 15. 商用與後續驗收邊界

即使 D2 通過，Emilia-linked ZipVoice weights 的 model-specific commercial rights仍未
釐清。D2 不解除這項 production blocker，也不授權把任何候選音訊交付旅客、LINE、
說明會或正式營運。

使用者要實際聽音並判斷 A／B 問題，後續至少還需：

1. model-load 書面設計與資源上限；
2. exact model archive listing／extraction／required-file validation 授權；
3. 本人 reference audio／transcript 的新授權；
4. 一次 bounded synthesis 與 Yating 盲測 Gate R；
5. 商用權利清楚的 model／provider，才能考慮正式整合。

## 16. Handoff 與 Git

每個完成或安全停止點更新 `STATUS.md`，固定記錄：一句話現況、做了什麼、下一步、
阻塞點、exact hashes、test／exit output及未驗證項目。

程式與文件可建立 local commits；runtime、archive、DLL／EXE、proof evidence及私人資料
不得 commit。依目前聲音試驗邊界不 push。

## 17. 書面審閱關卡

核准本書面設計只授權建立 Gate D2 implementation plan，仍不授權寫程式、下載、解壓、
執行 runtime、讀取 model／影片／音訊、啟動 Yating／SmartSub、合成、登入、上傳或 push。

下一個精確授權語句為：

```text
同意此書面設計，開始建立 Gate D2 runtime-only capability proof 的實作計畫；仍不下載、不解壓、不執行 runtime、不讀取 model 或本人素材、不合成、不登入、不上傳、不推送。
```
