# 免費優先的說明會本人語音短試驗實作計畫

日期：2026-08-19

依據：
`docs/specs/2026-08-19-free-first-briefing-voice-pilot-design.md`

設計基線 commit：
`fa5e6dd914e5589d878a379e88fd8a69bd0bd6e1`

狀態：書面設計、5 至 10 秒 reference 修正及本計畫已核准；Tasks 1–4 的 Gate I
離線安全骨架已完成並停在 Gate D 下載／安裝授權前。
本文件只是一份計畫，不授權下載、安裝、抽音、合成、訓練、上傳、付款、正式
整合或 push。

## 0. 必須先核准的上游相容性修正

核准設計原定從影片選取「約 2 至 3 秒」的參考音訊。唯讀查證鎖定的 SmartSub
v3.7.0 原始契約後，發現：

- 有效語音少於 3 秒是 error，建立音色會被阻擋；
- ZipVoice 建議選區為 5 至 10 秒；
- ZipVoice 選區上限為 15 秒；
- 定稿參考音訊會由原始媒體直接建立為 24 kHz、單聲道、16-bit WAV。

因此實作時必須把第一個固定 reference 改成 **5 至 10 秒**。這不是品質調參，
而是避免與已鎖定工具的輸入契約矛盾。使用者已於 2026-08-19 書面核准此修正；不得
硬送 2 至 3 秒、改用未鎖定舊版或跳過工具的 quality gate。

設計文件的該一行已在 Gate I documentation commit 同步修正；其餘盲測、一次調整
上限與正式整合邊界不變。

## 1. 成果與停止範圍

本計畫的唯一實際成果是一份隔離的 60 至 90 秒 A／B review pack，用來回答：

1. 本人聲線的 ZipVoice 候選是否比現況 Yating 自然；
2. 開場、重點、轉場與收尾是否改善「整篇語調太平」；
3. 一個長 cue 的 ZipVoice 候選是否改善「許多小音檔拼接」；
4. 這台 i7-8565U／8 GB RAM／Intel UHD 620 的電腦是否能合理完成本機推論。

短試驗通過或失敗後都停止。本計畫不包含：

- 30 至 60 分鐘資料錄製或 fine-tuning；
- 5 至 7 分鐘正式說明會長稿；
- 修改 `src/travel_briefing/` 或把 ZipVoice 加入正式 `VoiceProvider`；
- 把候選聲音用於旅客、LINE、`CONFIRMED`、影片、部署或發布；
- GPT-SoVITS 安裝或付費雲端 fallback；
- 上傳影片、參考音訊、逐字稿或候選音檔；
- 使用 ChatGPT／Codex 訂閱額度或任何 API key；
- 自動重試、靜默 fallback、模型更新、GPU pack 下載或 push。

## 2. 目前已驗證的基線

### 本機

2026-08-19 的唯讀查證結果：

- CPU：Intel Core i7-8565U，4 cores／8 logical processors；
- RAM：`8,485,707,776` bytes；
- GPU：Intel UHD Graphics 620，無 NVIDIA GPU；
- C 槽可用空間：`40,988,631,040` bytes（`38.17 GiB`）；
- SmartSub process count：`0`；
- 預定及預設 SmartSub 安裝目錄均不存在；
- Git working tree 乾淨，`main...origin/main [ahead 92]`；
- `git pull --ff-only`：`Already up to date.`。

硬體只證明有試驗空間，不證明即時或可接受速度。第一輪固定使用 CPU-only、
local concurrency 1；不下載 Intel Vulkan pack。CPU 路徑不合理時停止並回報，不能
把 GPU pack 當成已授權 fallback。

### 鎖定的 SmartSub release

以 GitHub 官方 release metadata 鎖定：

| 項目 | 固定值 |
|---|---|
| release | `v3.7.0` |
| tag commit | `27459b3fd0652bc5447ccf4ab30cb398014c35f7` |
| 發布時間 | `2026-08-06T02:12:32Z` |
| Windows asset | `SmartSub_Windows_3.7.0_x64.exe` |
| asset bytes | `127,844,583` |
| SHA-256 | `65f6c85aa196063f365562c41393d2f98ef0ce31e4ee3e0122d561668d433520` |
| source license | MIT |

來源：

- `https://github.com/buxuku/SmartSub/releases/tag/v3.7.0`
- `https://github.com/buxuku/SmartSub/tree/27459b3fd0652bc5447ccf4ab30cb398014c35f7`
- `https://raw.githubusercontent.com/buxuku/SmartSub/main/LICENSE`

Pinned `electron-builder.yml` 證明 Windows package 為 per-user NSIS、
`requestedExecutionLevel: asInvoker`、可選安裝目錄。若實際 installer 要求管理員權限、
不允許指定目錄、版本不是 3.7.0 或 hash 不符，立即停止。

### 鎖定的 ZipVoice assets

SmartSub v3.7.0 pinned source 指定 `zipvoice-distill-zh-en`，24 kHz、預估解壓後約
217 MB，使用 `numThreads=2` 的 sherpa-onnx ZipVoice request。所需兩個官方 GitHub
assets 為：

| 項目 | bytes | SHA-256 |
|---|---:|---|
| `sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2` | `109,162,785` | `77219c8b40f4ee8d73a7f902305ff6c1128ef9b54461c41b4ca6ed890b6c2803` |
| `vocos_24khz.onnx` | `54,157,409` | `bcb3b970e384161c4d634f0bb9e999ff1c471b34c9bc0b1049a5014065ed3cc0` |

直接來源固定為：

- `https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2`
- `https://github.com/k2-fsa/sherpa-onnx/releases/download/vocoder-models/vocos_24khz.onnx`

三個待下載 assets 合計 `291,164,777` bytes（`277.68 MiB`）。安裝、解壓、暫存及
voice data 仍需額外空間，因此下載關卡要求至少 2 GiB 可用；目前符合。此總數不含
未核准的 Vulkan／CUDA pack。

### License 紅旗

- SmartSub source 是 MIT；
- ZipVoice source 及官方 model card 標示 Apache-2.0；
- 但這份 distill model 標示以 Emilia 訓練，而 Emilia 官方資料條款為
  `CC BY-NC-4.0`，且提醒原始音訊著作權仍屬原權利人。

模型卡與訓練資料條款之間不足以讓本計畫宣稱「正式商業使用已無疑義」。因此：

- 本輪只准私人、本機、內部評估；
- 即使盲測通過，也不得交付旅客或併入營運產出；
- 正式整合前須取得足以支持商業使用的書面授權釐清，或改用商用權利清楚的模型／
  provider；
- 本計畫不提供法律結論，也不把 Apache-2.0 model card 當成訓練資料問題已自動消失。

這項紅旗不需要阻止私人技術試聽，但會阻擋任何 production acceptance。

## 3. 核准檔案與 unchanged controls

未來離線安全骨架只允許建立或修改：

- `.gitignore`；
- `scripts/voice_pilot/__init__.py`；
- `scripts/voice_pilot/pilot.py`；
- `scripts/voice_pilot/synthesize_yating_baseline.py`；
- `tests/unit/voice_pilot/test_pilot.py`；
- 本計畫、核准設計中 reference 時長的單行修正及 `STATUS.md`。

明確不得修改：

- `src/travel_briefing/` 全部 production files；
- `tests/unit/travel_briefing/` 與既有 integration tests；
- CLI、Skill、plugin、package version、schemas 與正式 Yating provider；
- private LIST master、calibration、既有 briefing artifacts 或 current DRAFT；
- Cowell、NewAmazing、JMA、Word、LINE、Cloudflare 或部署相關檔案。

若離線骨架需要新 dependency、`src/` change、Node／Electron build、SmartSub source clone、
registry edit、firewall rule 或系統設定，立即停止回到 plan review。

## 4. 關卡總覽

| 關卡 | 內容 | 本計畫核准後是否自動授權 |
|---|---|---|
| P | 書面計畫與 5–10 秒 reference 修正 | 已核准 |
| I | Tasks 1–4：synthetic-only 離線骨架、tests、local commits | 已核准並完成 |
| D | Task 5：下載三個 pinned assets、安裝 SmartSub／model | 需新的精確核准 |
| R | Tasks 6–9：讀影片、選 reference、Yating／ZipVoice 各一次、盲測 | 需新的精確核准及中途人工確認 |
| A | Task 10：第一次未過時只改一個變數再試一次 | 需使用者指定唯一變數 |
| L | 30–60 分鐘資料、fine-tune、5–7 分鐘稿 | 不在本計畫；需新設計 |

任何前一關通過都不授權下一關。尤其 Gate I 不授權下載；Gate D 不授權使用本人
影片或合成；Gate R 不授權 second attempt 或正式整合。

## Task 1：implementation preflight 與私人檔案 fail-closed

### 基線

Gate I 開始時執行：

```powershell
git status --short --branch
git pull --ff-only
$voicePilotBaseline = git rev-parse HEAD
(Get-Process SmartSub -ErrorAction SilentlyContinue | Measure-Object).Count
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
```

要求 working tree 乾淨、SmartSub 與 WINWORD count 都是 0，並記錄 baseline。若有未知
變更或程序，不覆蓋、不終止，先停止回報。

### `.gitignore` 最小防護

在現有 `output/`、`*.wav`、`*.mp3`、`*.srt` 規則外，加入：

```text
# Voice pilot private media, cloned voices, installers, and model weights
*.mp4
*.m4a
*.aac
*.flac
*.svoice
*.onnx
SmartSub_Windows_*.exe
sherpa-onnx-zipvoice-*.tar.bz2
```

不得忽略 `scripts/voice_pilot/` 或 `tests/unit/voice_pilot/`。用 `git check-ignore -v
--no-index` 對上述每種 synthetic filename 證明會被忽略，並證明新 Python files 不會
被忽略。

這是 defense in depth；真正私人產物仍只放 `output/voice-pilot/` 或 repo 外的 pinned
provider 目錄，不因有 ignore rule 就可任意複製。

## Task 2：script freeze 與 Yating wrapper 的離線 TDD

### 公開 seam

`scripts/voice_pilot/pilot.py` 提供可 import 的純函式與 CLI；不新增 project entrypoint。
script seam 固定為：

```text
freeze-script INPUT_TXT --output-dir DIR
verify-script DIR
```

`freeze-script`：

1. 以 UTF-8 讀取私人固定稿；
2. 使用與 `segment_narration()` 相同的 whitespace canonicalization，不能改字；
3. 拒絕空稿、`待 OP 確認`、section marker、review code、NUL 或無法編碼內容；
4. 要求 216 至 324 個不含空白字元，作為 3.6 chars/sec 下 60–90 秒的預先範圍；
5. 將開場、重點／轉場、收尾三個 text span 以輸入中的空白段落固定；
6. 寫出一份 canonical TXT 與一個 **單一 cue** 的 SRT；cue 從 0 開始、end 為 120 秒，
   只用來讓 SmartSub 以一個 `synthesize()` call 取得足夠 slot，不代表字幕時間；
7. manifest 只記 schema、character count、三個 text-span hashes、完整稿 SHA-256、
   output hashes；不抄入私人全文。

同一 canonical TXT 同時是 Yating 及 ZipVoice 唯一文字來源。SmartSub pinned source 只會
把 cue 內換行壓成空格；Yating `segment_narration()` 也會把 whitespace 壓成空格，因此
候選的實際字詞必須以 canonical hash 相同為前提。

### Tests 先紅後綠

在 `tests/unit/voice_pilot/test_pilot.py` 新增：

```text
test_freeze_script_writes_one_cue_and_preserves_canonical_text
test_freeze_script_locks_three_review_spans_and_hashes
test_freeze_script_rejects_private_placeholders_and_review_codes
test_verify_script_detects_text_or_manifest_tampering
```

所有 fixtures 都是 synthetic 中文文字，不含真實產品、旅客或 OP 資料。先看到缺少
module／behavior 的預期 red，再最小實作轉綠；不得提交 red-only commit。

### Yating wrapper

`synthesize_yating_baseline.py` 只能：

- 讀 `freeze-script` 的 canonical TXT 與 manifest；
- 再次驗證 hash；
- 呼叫既有 `segment_narration()`、`synthesize_yating()` 與
  `WindowsMediaSpeechAdapter`；
- 使用 repo 既有 `scripts/briefing/synthesize_yating.ps1`；
- 寫入一個全新 `output/voice-pilot/<run-id>/baseline/`；
- 需要命令列 literal `--ack-local-yating-once`，且輸出目錄存在時 fail closed；
- unknown result 時只檢查同次 artifacts，不重送、不 fallback。

離線 tests 只用 fake adapter 檢查 payload、hash、no-overwrite 與 unknown-result 行為；
Gate I 不得執行真正 Yating。現況 120-character／2-segment chunk contract保持不改，
因為它正是 B 問題的 baseline，不為盲測偷偷修好。

## Task 3：PCM 檢查、等音量與盲測包 TDD

### WAV 契約

只接受可由 Python standard-library `wave` 解碼的：

- PCM；
- 16-bit；
- mono；
- sample rate 介於 16 kHz 與 48 kHz；
- duration 60 至 90 秒；
- finite, non-zero RMS；
- 無 clipped sample。

Yating 16 kHz 與 ZipVoice 24 kHz 保留各自 native sample rate，播放器負責轉換；不新增
resampler dependency，也不把較高 sample rate 本身宣稱為較自然。

### 等音量

`build-blind-pack` 使用 standard library 重新寫 PCM WAV，移除來源 metadata，將兩者
各自調到 `-23.0 dBFS RMS`，peak ceiling 固定 `-1.0 dBFS`。若任一音檔因 crest factor
無法同時達到 target 與 ceiling，整包 fail closed，不用 clipping、compressor 或
不同目標掩蓋差異。

不得做：

- 降噪、EQ、reverb、de-esser、music、silence chopping；
- time stretch、atempo、pitch shift 或 sample-rate enhancement；
- 逐句重切或跨引擎不同後製；
- 覆蓋 baseline／candidate 原檔。

### 盲測包

CLI seam：

```text
build-blind-pack --baseline-wav ... --candidate-wav ... --script-manifest ... --output-dir ...
verify-blind-pack DIR
```

`build-blind-pack` 以 `secrets` 隨機決定 A／B，產生：

```text
review/A.wav
review/B.wav
review/scorecard.md
review/manifest.json
private/reveal.json
private/source-manifest.json
```

`review/` 中不得出現 `Yating`、`ZipVoice`、來源檔名、reference path 或 engine hashes
對照。`private/reveal.json` 在評分完成前不讀、不傳給使用者。scorecard 固定列出開場、
重點／轉場、收尾三個已鎖定 text spans，不能事後挑好聽片段。

### Tests 先紅後綠

使用程式建立短 synthetic PCM fixtures；測試本身可用較短 duration override，production
CLI 永遠固定 60–90 秒：

```text
test_probe_rejects_silence_stereo_non_pcm_and_clipping
test_normalization_matches_minus_23_dbfs_without_touching_inputs
test_normalization_fails_when_peak_ceiling_and_rms_target_conflict
test_blind_pack_hides_engine_identity_and_uses_injected_mapping_in_tests
test_blind_pack_rejects_script_hash_or_duration_mismatch
test_verify_blind_pack_detects_tampering_and_reveal_leakage
```

randomness 透過 injectable chooser 在 tests 固定；production default 必須是 `secrets`，
不得用可預測 timestamp 或 filename 決定 A／B。

## Task 4：Gate I 完整離線驗證、commits 與停止

### Focused tests

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\voice_pilot\test_pilot.py -q
```

再執行既有 Yating unchanged controls：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\travel_briefing\test_yating_audio.py `
  tests\unit\travel_briefing\test_windows_media_speech.py -q
```

不得改舊 assertions、skip 或 production code取得綠燈。

### Scope proof

```powershell
git diff --name-only $voicePilotBaseline
git diff --exit-code $voicePilotBaseline -- src tests/unit/travel_briefing
rg -n "httpx|requests|urllib|socket|ElevenLabs|Azure|Volcengine|LINE|Cowell" `
  scripts\voice_pilot tests\unit\voice_pilot
git diff --check
```

`src` 與既有 `tests/unit/travel_briefing` 必須 0 diff。source scan 不得出現新的 cloud／
upload／business integration；Yating wrapper 只能 import 本機既有 adapter。

### 完整 suite

```powershell
$smartSubBefore=(Get-Process SmartSub -ErrorAction SilentlyContinue | Measure-Object).Count
$winwordBefore=(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
.\.venv\Scripts\python.exe -X utf8 -m pytest
$suiteExit=$LASTEXITCODE
.\.venv\Scripts\python.exe -X utf8 -m compileall -q scripts\voice_pilot tests\unit\voice_pilot
$smartSubAfter=(Get-Process SmartSub -ErrorAction SilentlyContinue | Measure-Object).Count
$winwordAfter=(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
git diff --check
git status --short --branch
```

要求 suite exit 0、SmartSub／WINWORD before-after 都是 0、compile及diff clean。記錄實際
pass／skip count與duration，不使用預估數字。

### Commit map

1. `feat(voice-pilot): add isolated blind comparison harness`
   - `.gitignore`、scripts、tests；
   - 只含 synthetic-only verified implementation。
2. `docs: record free-first voice pilot offline handoff`
   - 設計 reference 時長修正、本計畫 actual results、`STATUS.md`；
   - 不含其他 production changes。

兩個 commits 都只留本機，不 push。Gate I 完成後必須停止並提出 Gate D exact asset
approval；不得因 tests green 就下載。

## Gate I 實際證據（2026-08-19）

- 實作基線：`4f2d51428377cdcfd96c877832c5982ff2c87930`；開工時 SmartSub／WINWORD
  process count 均為 `0`，`git pull --ff-only` 為 `Already up to date.`。
- implementation commit：`100ede1ae3b5d88f7743f8e779621744d59412ae`；只包含
  `.gitignore`、`scripts/voice_pilot/` 與 `tests/unit/voice_pilot/test_pilot.py`。
- `git check-ignore -v --no-index` 證明 MP4／M4A／AAC／FLAC／SVOICE／ONNX／
  SmartSub installer／ZipVoice archive 均被忽略，新 Python 原始碼不被忽略。
- TDD focused tests：`20 passed`；既有 Yating unchanged controls：`25 passed`。
- 完整離線 suite：`614 passed, 8 skipped in 22.80s`；`compileall` exit `0`。
- `src/` 及既有 `tests/unit/travel_briefing/` 相對基線均為 0 diff；新目錄對
  network／cloud／LINE／Cowell 關鍵字掃描為 0 命中；`git diff --check` 通過。
- SmartSub／WINWORD 在完整 suite 前後均為 `0 / 0`。沒有下載、安裝、讀取影片、
  抽音、啟動 Yating／SmartSub、合成、上傳、付款、正式整合或 push。

Gate I 到此完成，只證明安全骨架及 synthetic 契約；不證明 SmartSub 可安裝、
ZipVoice 效能／品質、本人相似度或真實音訊自然度。下一步仍須新的 Gate D 精確授權。

## Task 5：Gate D pinned download、安裝與本機 capability proof

只有新的精確 Gate D 授權後，才能建立：

```text
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\downloads
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\SmartSub\3.7.0
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\data
```

### 下載與完整性

只從本計畫三個 direct GitHub URLs 下載，不先走 `ghproxy`、Quark、HF mirror 或其他
鏡像。每個 download 使用全新 `.partial` 檔，完成後計算 SHA-256；hash相符才改為正式
檔名。任一 URL、size、hash 變更或不符都停止，不重抓另一來源。

installer 另執行：

```powershell
Get-AuthenticodeSignature <exact-installer-path> | Format-List Status,StatusMessage,SignerCertificate
```

若簽章不是 `Valid`，不按 SmartScreen bypass；先把 official GitHub hash證據與實際
signature status 回報使用者，再取得新的執行確認。

### 安裝

經確認後，以可見的 interactive NSIS UI 安裝，固定目的地：

`C:\Users\cance\AppData\Local\EasyTravelVoicePilot\SmartSub\3.7.0`

要求：

- 版本畫面為 3.7.0；
- 不要求 admin／per-machine；
- 不接受自動升級到其他版；
- 不登入、不輸入 API key、不設定 cloud provider、不匯入 cookies；
- 不貼網路影片 URL；
- 不下載 ASR、CUDA、Vulkan 或其他模型。

若任一要求不成立，離開 installer／app並保留檔案，不嘗試不同版本。

### Model storage

第一次啟動只把 SmartSub 統一 storage root 設成：

`C:\Users\cance\AppData\Local\EasyTravelVoicePilot\data`

依 pinned source，TTS model 目標必須解析為：

`C:\Users\cance\AppData\Local\EasyTravelVoicePilot\data\models\tts\zipvoice-distill-zh-en`

關閉 SmartSub 後，從已驗證 archive 解壓到全新 staging；確認唯一 top-level folder、
required files及無 path traversal，再把 folder contents與已驗證 `vocos_24khz.onnx`
放到上述 model 目錄。required files至少為：

```text
encoder.int8.onnx
decoder.int8.onnx
tokens.txt
lexicon.txt
espeak-ng-data/phontab
vocos_24khz.onnx
```

不執行 SmartSub 內建 downloader，避免它自動從 `ghproxy` fallback。重新啟動後只確認
model card顯示 installed；不建立音色、不送入影片、不合成。

### Capability proof 與停止

記錄：

- app version、安裝路徑、storage／model／temp／userData實際路徑；
- installer、archive、vocoder及required model files hashes；
- CPU-only、local concurrency 1、無 cloud providers／credentials；
- app與所有 child processes、記憶體基線、Git status；
- 是否出現未預期 network／update／model prompt。

SmartSub source預期 voice clone資料位於 Electron `userData/voiceClones/<id>`；實際
Windows路徑只在 app 啟動後以只讀證據確認，不能先猜成已驗證。

Gate D 到此停止。下載與安裝不授權使用本人影片或任何合成。

### Gate D 實際證據（2026-08-19）

- Gate D 基線為 `207703be7182f8dce8846cd49016e411764dca65`；`git pull --ff-only`
  為 `Already up to date.`，SmartSub／WINWORD process 前檢均為 `0 / 0`。
- 三個 direct GitHub assets 各只下載一次；正式檔名重驗結果為：installer
  `127,844,583` bytes／SHA-256
  `65f6c85aa196063f365562c41393d2f98ef0ce31e4ee3e0122d561668d433520`，ZipVoice
  archive `109,162,785` bytes／SHA-256
  `77219c8b40f4ee8d73a7f902305ff6c1128ef9b54461c41b4ca6ed890b6c2803`，vocoder
  `54,157,409` bytes／SHA-256
  `bcb3b970e384161c4d634f0bb9e999ff1c471b34c9bc0b1049a5014065ed3cc0`。
- 合計 `291,164,777` bytes，三檔 bytes／hash 全部相符，殘留 `.partial` count 為
  `0`。檔案保留在 `%LOCALAPPDATA%\EasyTravelVoicePilot\downloads`。
- installer 的 Authenticode 實測為 `NotSigned`，`SignerCertificate` 與
  `TimeStamperCertificate` 均不存在。依本 Task 的 fail-closed 規則，在執行 installer
  前停止，沒有按 SmartScreen bypass。
- 尚未啟動／安裝 SmartSub、解壓／部署 model、讀取本人影片、建立音色、啟動 Yating、
  合成、下載 ASR／CUDA／Vulkan／其他模型、登入、上傳或 push。繼續執行此 unsigned
  exact-hash installer 必須取得新的明確確認。

### Gate D unsigned installer 執行結果（2026-08-19）

- 使用者另行明確核准執行上述 exact-hash `NotSigned` installer，並只允許繼續 Task 5。
  開工 `git pull --ff-only` 為 `Already up to date.`，基線為
  `c16ecfd1f56dcc04cb5e6158b7b07a58ae5555c6`。
- 執行前再次驗證 installer：`127,844,583` bytes，SHA-256
  `65f6c85aa196063f365562c41393d2f98ef0ce31e4ee3e0122d561668d433520`，
  Authenticode `NotSigned`，內嵌 Product／File Version 均為 `3.7.0`；install／data
  paths不存在，SmartSub／WINWORD process均為 `0 / 0`。
- computer-use native pipe 回傳系統找不到指定檔案，因此沒有啟動 Skill禁止的自製 helper；
  改以 screenshot Skill和可見 `Start-Process` 執行一次。沒有 `/S`，唯一 argument 是
  核准 per-user path的 NSIS `/D`；啟動 PID為 `17356`。
- installer沒有出現 SmartScreen或NSIS UI。Windows Application Error event `1000`
  證明 PID `0x43CC`在 `System.dll`發生 `0xc0000005` access violation，fault offset
  `0x00001581`；WER event `1001`的 Report ID為
  `612b70b2-e2f2-4115-b0a1-73533d65fdad`。同次本機 screenshot 保存在 temp，未進 Git。
- postflight沒有 SmartSub relevant process、安裝檔案或uninstall registry entry；核准install
  path只留下空目錄，常見 alternate paths與data path不存在。NSIS temp保留
  `System.dll`／`UAC.dll`；沒有自動清理。
- 依本計畫禁止 automatic retry／silent fallback，未重跑 installer，也未改用 admin、
  相容模式、其他路徑／版本或手動解包。因此 SmartSub與ZipVoice model均未安裝，
  capability proof未完成；Gate D在installer APPCRASH阻塞並停止。

## Task 6：Gate R reference 選取與人工確認

只有新的 Gate R 授權後，SmartSub clone wizard 才能唯讀開啟：

`C:\Users\cance\Downloads\5fbafd89-d770-4af1-9e87-23a72e7d254f.mp4`

固定做法：

1. 選 `Local ZipVoice`，不選火山或 ElevenLabs；
2. 從完整影片自動建議中只選一段 5 至 10 秒；
3. quality report 必須沒有 error，且無他人聲、音樂、敏感資料、截斷句首／尾；
4. 第一輪不開降噪；
5. 不讓 ASR cascade 使用 cloud。若本機 ASR不能轉寫，直接手動輸入；
6. 將建議 transcript當候選，使用者逐字確認後才保存；
7. 保存前記錄 source video SHA、start／end、prepared WAV規格／hash、reference text
   hash與quality report；manifest不保存全文；
8. 名稱固定為 `easytravel-pilot-v1`，不建立多個 voice後挑最好的一個。

建立音色時 SmartSub會自動產生一次短 preview；這是 Gate R 內已揭露的 provider
execution。preview 成功只證明 capability，不算 60–90 秒 Gate 1 評分。若建立結果
不明，先查同一 voice record與artifacts，不再按一次保存。

使用者必須先看到並確認：

```text
reference start/end、實際秒數、逐字稿、quality warnings、prepared WAV hash
```

未確認前不執行 Task 7／8。

## Task 7：固定 60–90 秒稿件

從一份既有本機 canonical briefing narration 擷取一段真實說明會文字，不做新
NewAmazing GET，也不讀取 Cowell。選擇條件：

- `check-script` 已無 error；
- 不含旅客 PII、未確認 OP 欄位、爭議值或 review placeholder；
- 不與本人影片 sample 重複同一句；
- 216–324 non-whitespace characters；
- 三個空白段落依序是開場、重點／自然轉場、收尾；
- 包含至少一組地名及一組日期／時間／金額／班號類 critical term，供正確性驗收；
- 不為語調表現新增來源不存在的事實。

使用 `freeze-script` 建立 canonical TXT、單一 0–120 秒 cue SRT及manifest，然後讓
使用者看完整文字、三個固定 spans、critical terms與SHA-256。核准後稿件凍結；
第一輪不能因模型表現修改文字。

## Task 8：Yating baseline 與 ZipVoice candidate 各一次

### Yating baseline

只執行一次：

```powershell
.\.venv\Scripts\python.exe -X utf8 `
  scripts\voice_pilot\synthesize_yating_baseline.py `
  --script-manifest <exact-manifest> `
  --output-dir <new-baseline-dir> `
  --ack-local-yating-once
```

記錄既有管線實際 chunk count、segments、bookmarks、duration、PCM format與hashes。
60–90 秒稿通常會超過 120 characters，故 baseline 預期保留現行多 chunk 行為；不能
直接呼叫底層 PowerShell避開 production path，也不能重跑來挑較好版本。

### ZipVoice candidate

SmartSub 使用：

- 本地 `easytravel-pilot-v1`；
- frozen **single-cue** SRT；
- audio-only、無 video；
- CPU-only；
- local concurrency `1`；
- clone quality `high`（`numSteps=8`）；
- global speed `1.0`；
- 不開降噪、背景音、ducking、cloud或GPU pack；
- cue slot 120 秒，預估與實測都必須落在slot內；
- session evidence 的 `appliedSpeed` 必須為 `1.0`、action為none，不能有 resynthesis、
  atempo、truncate、overlong或alignment repair。

只按一次開始並等待一個 final candidate WAV。單一 cue 可證明 SmartSub adapter只收到
一次 `synthesize()`，但不能宣稱 ZipVoice模型內部完全沒有自己的 punctuation chunking；
app logs若有內部分塊必須保留，沒有log則在每個標點與可能接縫人工聽查。

候選 wall-time上限 20 分鐘。期間每 60 秒內記錄一次所有 SmartSub processes的 CPU、
working set與狀態；若系統不穩或到時未完成，先檢查同一 session／artifact，不能再按
一次。CPU failure不會自動下載 Vulkan。

兩個引擎的 canonical text hash、字數與 critical terms必須相同。任一 duration不在
60–90 秒、音檔格式不符、非靜音檢查失敗、詞句錯誤或結果不明，就不建立 blind pack。

## Task 9：盲測、揭盲與 Gate 1 判定

用同一次 baseline／candidate執行 `build-blind-pack`，再以獨立 `verify-blind-pack`
重驗 hashes、RMS、peak、duration、script hash與identity leakage。只有 review folder
提供使用者。

使用者先聽完整 A／B，再依固定三個 text spans評分：

- 開場；
- 重點提醒與轉場；
- 收尾。

scorecard 逐項記錄：

- 自然度 1–5；
- A 問題是否存在；
- B／接縫問題是否存在；
- 本人相似度 1–5；
- 每個 critical term是否正確；
- 三個 spans各自偏好 A、B或平手。

評分完成並寫入hash-bound scorecard後才讀 `private/reveal.json`。ZipVoice通過條件完全
沿用核准設計：自然度至少4/5、三段至少兩段勝Yating、本人相似度至少3/5、A/B問題
消失、critical terms 100%正確且技術manifest完整。

揭盲後更新 `STATUS.md`，但不修改正式 workflow、不把候選交付旅客。

## Task 10：唯一一次 adjustment

若第一次未過，立即停止並提供：

- 原始分數及揭盲結果；
- 失敗屬於音色、韻律、接縫、critical term、效能或技術契約；
- 可以單獨改動的候選變數及其預期作用。

只有使用者指定並另行授權一個變數，才可第二次試驗。允許的單一變數限：

- 更換成另一個已逐字確認、同樣5–10秒的reference；或
- `numSteps` 8改4；或
- 一個明確、上游支援的推論參數。

不得同時換稿、換 reference、換模型、加後製或下載 GPU pack。第二次仍未過就終止
ZipVoice，未來 GPT-SoVITS 必須有新規格與下載清單。

## Task 11：handoff、保留與清理決策

每個完成或安全停止點更新：

- 本計畫 actual evidence；
- `STATUS.md` 的一句話現況／做了什麼／下一步／阻塞點；
- exact asset／model／reference／script／audio／score hashes；
- 未驗證項目與下一個明確授權文字。

程式與文件可建立 local commits；私人音訊、逐字稿、model、installer、SmartSub state、
score identity map與output永不進Git。session結束確認`git status`沒有私人檔案。

不自動 uninstall、刪 downloads、刪model或刪 cloned voice。SmartSub installer設定
`deleteAppDataOnUninstall: true`，uninstall可能刪除 voice data；任何清理都需新的精確
確認並先列出絕對路徑。也不 push。

## 5. Gate I 完成條件

第一個可實作階段只有 Tasks 1–4。完成必須同時證明：

1. 私人media、clone bundle、installer及model artifacts被Git防護；
2. fixed script由單一canonical text產生Yating輸入與single-cue SRT；
3. placeholders、review codes、稿件tampering與hash mismatch均fail closed；
4. Yating wrapper有exact-once literal、no-overwrite與unknown-result檢查；
5. PCM16 mono、duration、silence、clipping、RMS與peak契約有synthetic tests；
6. A/B隨機、review identity isolation、sealed reveal與tamper detection有tests；
7. 沒有新dependency、network client、cloud provider或production wiring；
8. focused tests、既有Yating controls、完整suite及compile實際通過；
9. `src/travel_briefing/`與既有tests 0 diff；
10. SmartSub／WINWORD before-after皆0；
11. local commits建立、working tree乾淨、未push；
12. 未讀取／抽出本人影片，未下載、安裝或合成任何真實音訊。

Gate I green 只證明安全骨架可用，不證明 SmartSub可安裝、ZipVoice有品質或音訊自然。

## 6. 核准紀錄與下一關卡

使用者已於 2026-08-19 同時核准 5 至 10 秒 reference 修正、本計畫及只執行
Tasks 1–4 的 synthetic-only Gate I。Gate I 已完成，授權已消耗，不能延伸為下載、
安裝、讀取影片或合成。

若要進入 Gate D，下一個精確授權語句為：

```text
核准 Gate D：只從實作計畫列出的三個官方 GitHub URL 下載固定 assets，驗證 bytes、SHA-256 與 installer 簽章，並依 Task 5 以 per-user 方式安裝 SmartSub 3.7.0 及固定 ZipVoice model，完成本機 capability proof 後停止；不讀取或抽出本人影片、不建立音色、不啟動 Yating、不合成語音、不下載 ASR／CUDA／Vulkan 或其他模型、不登入、不上傳、不推送。
```
