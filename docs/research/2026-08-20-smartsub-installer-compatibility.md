# SmartSub 3.7.0 installer 相容性與 sherpa-onnx ZipVoice 直連可行性

- 調查日期：2026-08-20（Asia/Taipei）
- 調查性質：官方一手來源唯讀研究
- 本次未執行：下載 release asset、啟動 installer、安裝、解壓 model、讀取影片、建立音色、合成、登入、上傳或 push

## 結論摘要

1. **SmartSub 3.7.0 的同一 crash signature 已驗證。** 官方 issue #432 與本機 Event 1000 在七個欄位完全一致：application、version、application PE timestamp、module、module timestamp、exception code、fault offset。這已不是本機單一偶發事件。[官方 issue #432](https://github.com/buxuku/SmartSub/issues/432)
2. **Windows 11 25H2 相容性是強推論，不是官方已確認根因。** 兩台機器都是 25H2、但 build 與 GPU 不同；官方 issue 沒有 maintainer 回覆、標籤、assignee、milestone 或 linked development，也沒有修正 PR。不能把「可能是 25H2 與 NSIS `System.dll` 的相容問題」寫成已證明的 root cause。
3. **目前沒有可依賴的 SmartSub 官方修正或 workaround。** 截至 2026-08-20，issue #432 仍 open、0 comments；最新 release 仍是 v3.7.0，tag 後 `main` 只有兩個與 installer 無關的 commits。[v3.7.0 release](https://github.com/buxuku/SmartSub/releases/tag/v3.7.0)／[tag 至 main 比較](https://github.com/buxuku/SmartSub/compare/27459b3fd0652bc5447ccf4ab30cb398014c35f7...main)
4. **不依賴 SmartSub installer，直接使用官方 sherpa-onnx Windows CPU runtime，在技術介面上可行。** 官方文件目前指定 v1.13.6 Windows x64、TTS-enabled 的 pre-built archive；同一份官方 ZipVoice model 與 vocoder 可直接交給 `sherpa-onnx-offline-tts` CLI 或 C/C++、Python、.NET、JavaScript 等 API。[Windows x64 pre-built 文件](https://k2-fsa.github.io/sherpa/onnx/install/windows/generated/download/windows_x64.html)／[ZipVoice 文件](https://k2-fsa.github.io/sherpa/onnx/tts/zipvoice.html)
5. **「可行」不等於已在本機證明。** 本次沒有下載 v1.13.6 runtime、沒有列出或解壓 archive、沒有啟動 binary、沒有載入 model，也沒有合成；因此 Windows 25H2 本機啟動性、記憶體、速度、自然度仍是未驗證。
6. **商用權利尚未釐清。** sherpa-onnx 與 ZipVoice source code 是 Apache-2.0，但 `tts-models` release body 沒有替這個 checkpoint 明示 model license；檔名與官方訓練程式指向 Emilia，而 Emilia 官方 README 限 non-commercial、CC BY-NC-4.0，並說原始音訊著作權仍屬原權利人。程式碼 license 不能自動解決 model/data 權利；在取得 model-specific 商用授權或法律確認前，不應投入旅客／客戶／營運產出。

## 1. SmartSub v3.7.0 build 與 installer 證據

### 1.1 Release 身分

官方 v3.7.0 release 指向 commit `27459b3fd0652bc5447ccf4ab30cb398014c35f7`。GitHub release API 對 Windows asset 公布：

| 欄位 | 值 |
|---|---|
| asset | `SmartSub_Windows_3.7.0_x64.exe` |
| bytes | `127,844,583` |
| GitHub digest | `sha256:65f6c85aa196063f365562c41393d2f98ef0ce31e4ee3e0122d561668d433520` |
| published | `2026-08-06T02:12:32Z` |

來源：[release page](https://github.com/buxuku/SmartSub/releases/tag/v3.7.0)／[GitHub release API](https://api.github.com/repos/buxuku/SmartSub/releases/tags/v3.7.0)／[pinned source tree](https://github.com/buxuku/SmartSub/tree/27459b3fd0652bc5447ccf4ab30cb398014c35f7)

這證明本機先前驗證的 bytes/hash 對應官方 release asset；它不證明 installer 在所有 Windows 版本能執行，也不等於 code signing。

### 1.2 Packaging 設定

Pinned source 的設定是：

- `win.target: nsis`
- `requestedExecutionLevel: asInvoker`
- `oneClick: false`
- `perMachine: false`
- `allowToChangeInstallationDirectory: true`
- `deleteAppDataOnUninstall: true`

來源：[pinned `electron-builder.yml`](https://github.com/buxuku/SmartSub/blob/27459b3fd0652bc5447ccf4ab30cb398014c35f7/electron-builder.yml)

依賴版本是：

- `package.json` 宣告 `electron-builder: ^24.13.3`、`electron: ^30.1.0`；
- `package-lock.json` 實際鎖定 `electron-builder 24.13.3`、`app-builder-lib 24.13.3`、`app-builder-bin 4.0.0`、`electron 30.5.1`。

來源：[pinned `package.json`](https://github.com/buxuku/SmartSub/blob/27459b3fd0652bc5447ccf4ab30cb398014c35f7/package.json)／[pinned `package-lock.json`](https://github.com/buxuku/SmartSub/blob/27459b3fd0652bc5447ccf4ab30cb398014c35f7/package-lock.json)

**缺少的證據：** 這些 pinned files 沒有記錄實際放入 installer 的 NSIS `System.dll` 版本或 hash；issue 的 module version 也只是 `0.0.0.0`。因此允許來源範圍內無法把 `System.dll` 精確映射到某個 NSIS plugin build，更不能指定一個已證明有效的替換版本。

### 1.3 Release workflow 做了什麼、沒做什麼

Pinned workflow 在 `windows-2022`、Node `20.14.0` 上以 frozen lock 安裝依賴，再執行 `electron-builder --win --x64 --publish never`，最後做 bundle-size gate、stage 與 upload。該 tag 的 build/release run 成功，Windows x64 job 也成功。

來源：[pinned release workflow](https://github.com/buxuku/SmartSub/blob/27459b3fd0652bc5447ccf4ab30cb398014c35f7/.github/workflows/release.yml)／[release run 31064323316](https://github.com/buxuku/SmartSub/actions/runs/31064323316)／[Windows job 92498744141](https://github.com/buxuku/SmartSub/actions/runs/31064323316/job/92498744141)

Workflow 沒有可見的「執行剛產出的 Windows installer、完成安裝、再啟動 app」smoke step，也沒有可見的 Windows signing step。因而 workflow green 證明 build/upload 成功，不證明 end-user installation 成功。已下載 asset 的本機 Authenticode `NotSigned` 是另一項本機實測證據。

## 2. Crash signature 比對

### 2.1 官方 issue 與本機 Event 1000

主代理已用程式逐欄比對本機 Event 1000 與官方 issue #432；七欄全部 `ExactMatch=True`：

| Signature 欄位 | 官方 issue #432 | 本機 | 結果 |
|---|---|---|---|
| Application | `SmartSub_Windows_3.7.0_x64.exe` | 相同 | Exact match |
| Version | `3.7.0.0` | 相同 | Exact match |
| Application PE timestamp | `0x5c157f86` | 相同 | Exact match |
| Faulting module | `System.dll` | 相同 | Exact match |
| Module timestamp | `0x5c157efa` | 相同 | Exact match |
| Exception code | `0xc0000005` | 相同 | Exact match |
| Fault offset | `0x00001581` | 相同 | Exact match |

官方 issue 機器是 Windows 11 25H2 build `26200.8875`、NVIDIA RTX 5070 Ti；本機是 Windows 11 Home 25H2 build `26200.9168`、Intel UHD 620。兩次都在正式安裝開始前，由 installer 解到 `%LOCALAPPDATA%\Temp\...\System.dll` 的 module crash；process ID、temp directory 與 WER report ID 不同，這些不是 binary crash signature 的穩定欄位。

官方來源：[SmartSub issue #432](https://github.com/buxuku/SmartSub/issues/432)

### 2.2 能下的結論

**已證明：**

- 相同 official release binary 的同一 crash signature 至少出現在兩台不同硬體的 Windows 11 25H2 機器；
- fault 發生於 installer 解出的 `System.dll`，而不是已安裝後的 Electron app、ZipVoice model 或 GPU inference；
- 這不是單憑本機截圖猜測的故障。

**強推論，但未獲官方確認：**

- 問題很可能位於這個 v3.7.0 NSIS installer layer 與 Windows 11 25H2 環境的交互作用；
- 因兩台 GPU 不同且 app 尚未啟動，GPU-specific SmartSub inference bug 的解釋力較低。

**仍未知：**

- 是所有 25H2、特定 security setting、特定 CPU/OS component，還是更窄的條件；
- `System.dll` 中實際是哪一個 call/access 造成 `0xc0000005`；
- admin、compatibility mode、silent install、換路徑或手動解包是否有效且安全。這些都沒被官方 issue 證明，也不應以同一失敗 binary 盲試。

### 2.3 官方處理狀態（截至 2026-08-20）

- issue #432：open；0 comments；無 labels、assignees、milestone、linked development。
- latest release：仍為 v3.7.0。
- tag 後 `main`：兩個 commits，分別是 Qwen ASR JSON control-character 修正與 README 圖表修正；沒有 installer／NSIS fix。

來源：[issue #432](https://github.com/buxuku/SmartSub/issues/432)／[latest release](https://github.com/buxuku/SmartSub/releases/latest)／[tag 至 main 比較](https://github.com/buxuku/SmartSub/compare/27459b3fd0652bc5447ccf4ab30cb398014c35f7...main)

所以目前不建議重跑同一 installer，也不能把 SmartSub README 裡「GPU crash 時切 CPU」當作 installer crash 的官方 workaround；那段說明談的是 app 啟動後的 inference 加速，不是安裝前 `System.dll` fault。[pinned README](https://github.com/buxuku/SmartSub/blob/27459b3fd0652bc5447ccf4ab30cb398014c35f7/README.md)

## 3. 直接使用 sherpa-onnx ZipVoice runtime

### 3.1 為什麼這條路能繞過目前阻塞

SmartSub pinned source 本身也是用 sherpa-onnx：其 build script 把 `1.13.2` 的 custom Node native bundle 放進 Electron package，TTS catalog 則指定同一個官方 ZipVoice model archive、`vocos_24khz.onnx`、24 kHz、`numThreads=2` 與 CPU-capable request。這表示 SmartSub 的價值主要在 UI／工作流；底層 model 並不要求由 SmartSub installer 才能使用。

來源：[pinned `fetch-sherpa-native.mjs`](https://github.com/buxuku/SmartSub/blob/27459b3fd0652bc5447ccf4ab30cb398014c35f7/scripts/fetch-sherpa-native.mjs)／[pinned `ttsModelCatalog.ts`](https://github.com/buxuku/SmartSub/blob/27459b3fd0652bc5447ccf4ab30cb398014c35f7/main/helpers/ttsModelCatalog.ts)／[pinned `ttsRuntime.ts`](https://github.com/buxuku/SmartSub/blob/27459b3fd0652bc5447ccf4ab30cb398014c35f7/main/helpers/sherpaOnnx/ttsRuntime.ts)

官方 ZipVoice repository 也把 sherpa-onnx 指为 CPU deployment 路徑。[k2-fsa/ZipVoice](https://github.com/k2-fsa/ZipVoice)

### 3.2 應固定的 Windows runtime，不用過時版本

2026-08-20 的官方 Windows x64 文件已指向 `v1.13.6`。適合本案的是表格中 **Shared Libraries / MT / Release / TTS enabled** 的 asset：

| 欄位 | 固定值 |
|---|---|
| release | `v1.13.6` |
| asset | `sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2` |
| bytes | `24,497,928` |
| GitHub digest | `sha256:4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613` |
| direct URL | `https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.6/sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2` |

來源：[Windows x64 pre-built table](https://k2-fsa.github.io/sherpa/onnx/install/windows/generated/download/windows_x64.html)／[v1.13.6 release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/v1.13.6)／[GitHub release API](https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/v1.13.6)

不要回用先前討論中的 v1.13.4：官方 current docs 已更新到 v1.13.6，而且 v1.13.6 有可固定 bytes/digest 的正式 Windows x64 TTS-enabled asset。

這是一個 archive，不是 NSIS installer；官方文件把它定位為 pre-compiled executables and libraries。它因此避開 SmartSub 的 Electron／electron-builder／NSIS `System.dll` 路徑，但不保證自己的 binary 在本機一定可啟動。

### 3.3 已固定的 model 與 vocoder

官方 ZipVoice 文件要求 model archive 加獨立 vocoder：

| asset | bytes | GitHub digest |
|---|---:|---|
| `sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2` | `109,162,785` | `sha256:77219c8b40f4ee8d73a7f902305ff6c1128ef9b54461c41b4ca6ed890b6c2803` |
| `vocos_24khz.onnx` | `54,157,409` | `sha256:bcb3b970e384161c4d634f0bb9e999ff1c471b34c9bc0b1049a5014065ed3cc0` |

來源：[ZipVoice usage](https://k2-fsa.github.io/sherpa/onnx/tts/zipvoice.html)／[`tts-models` release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models)／[`tts-models` API](https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/tts-models)／[`vocoder-models` release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/vocoder-models)／[`vocoder-models` API](https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/vocoder-models)

專案既有 Gate D 紀錄顯示這兩檔已下載並通過相同 bytes/hash；本次研究沒有重新讀取、解壓或驗證其內部內容。若之後加上 v1.13.6 runtime，三個 direct-runtime assets 合計 `187,818,122` bytes，其中新的下載只有 `24,497,928` bytes。

### 3.4 CLI 的必要輸入與檔案

官方 `sherpa-onnx-offline-tts` ZipVoice 範例需要：

- `encoder.int8.onnx`
- `decoder.int8.onnx`
- `tokens.txt`
- `lexicon.txt`
- `espeak-ng-data`
- `vocos_24khz.onnx`
- reference WAV
- 與 reference WAV **逐字相符**的 reference text
- 要合成的文字、`--num-steps` 與 output filename

官方 validator 還會檢查 `espeak-ng-data` 下的 `phontab`、`phonindex`、`phondata`、`intonations`。來源：[ZipVoice CLI 文件](https://k2-fsa.github.io/sherpa/onnx/tts/zipvoice.html)／[v1.13.6 ZipVoice config validator](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.6/sherpa-onnx/csrc/offline-tts-zipvoice-model-config.cc)／[v1.13.6 CLI source](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.6/sherpa-onnx/csrc/sherpa-onnx-offline-tts.cc)

官方明確警告 reference text 若與 reference audio 不相符，合成品質會明顯下降。ZipVoice 是 zero-shot voice cloning，不是先用大量資料 fine-tune；direct CLI 每次 generation 都要給 reference audio 與 transcript。[ZipVoice 文件](https://k2-fsa.github.io/sherpa/onnx/tts/zipvoice.html)

### 3.5 CPU、API 與額外需求

v1.13.6 source 的 `OfflineTtsModelConfig` 預設 `provider = "cpu"`、`num_threads = 1`；官方 ZipVoice examples 常設 `num_threads = 2`。因此 CPU path 是上游正式介面，不需要 CUDA 或 Vulkan 才能建立 config。[v1.13.6 model config](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.6/sherpa-onnx/csrc/offline-tts-model-config.h)／[C API TTS example](https://k2-fsa.github.io/sherpa/onnx/c-api/html/tts.html)

可用介面包括：

- pre-built CLI：`sherpa-onnx-offline-tts`；
- C/C++、Python、Go、Java/Kotlin、Dart/Swift、.NET、JavaScript、Pascal API。

來源：[ZipVoice API examples index](https://k2-fsa.github.io/sherpa/onnx/tts/zipvoice.html)

對本案最小依賴的是 **pre-built CLI archive**：不需要 SmartSub、Electron、Node/npm、Python/pip、CMake、Visual Studio、CUDA、Vulkan、ASR model、登入或雲端服務。官方文件沒有要求用 installer；但 archive 尚未列出，故內部 executable/DLL 清單、Authenticode 與是否仍需要某個 Windows system runtime，必須在下一 gate 實測，不能先宣稱。

替代路徑及代價：

| 路徑 | 官方支援 | 新需求 | 本案判斷 |
|---|---|---|---|
| v1.13.6 pre-built CLI archive | Windows x64、TTS enabled | 一個 24.5 MB archive、解壓 | **推薦最小路徑** |
| Python package | `pip install sherpa-onnx` 會提供 CLI，支援 Windows x64 | Python、pip、package downloads | 可行但依賴與供應鏈面較大 |
| Node API | `npm install sherpa-onnx-node`; playback 才另需 `speaker` | Node/npm、packages | 可行但沒有必要 |
| source build | 官方 Windows build 路徑 | CMake >= 3.13、C++14 compiler、Visual Studio 2022 | 不符合免費短試驗的最小路徑 |

來源：[TTS FAQ](https://k2-fsa.github.io/sherpa/onnx/tts/faq.html)／[JavaScript ZipVoice example](https://k2-fsa.github.io/sherpa/onnx/javascript-api/examples/tts_zipvoice.html)／[Windows install index](https://k2-fsa.github.io/sherpa/onnx/install/index.html)

### 3.6 能力與效能仍未證明

SmartSub pinned source 留有「ZipVoice 單 process peak 約 1.5 GB」的 developer comment，但那不是這台機器的實測，也不應當成 direct v1.13.6 CLI 的保證。[pinned `ttsRuntime.ts`](https://github.com/buxuku/SmartSub/blob/27459b3fd0652bc5447ccf4ab30cb398014c35f7/main/helpers/sherpaOnnx/ttsRuntime.ts)

官方資料足以證明 API/CLI 與 CPU path 存在；不足以證明 i7-8565U／8 GB 的：

- binary 能在 Windows 11 25H2 build `26200.9168` 正常啟動；
- model 初始化峰值、60–90 秒稿 wall time 或 real-time factor；
- 中文專名發音；
- 本人相似度、自然度及 A/B 問題是否改善。

這些必須以新的、明確範圍的本機實驗回答。

## 4. License 與商用邊界

### 4.1 已知

- sherpa-onnx source repository：Apache-2.0。[repository/license](https://github.com/k2-fsa/sherpa-onnx)
- ZipVoice source repository：Apache-2.0。[repository/license](https://github.com/k2-fsa/ZipVoice)
- 官方 ZipVoice 訓練程式的標準 invocation 使用 `--dataset emilia` 與 `tokens_emilia.txt`。[training source](https://github.com/k2-fsa/ZipVoice/blob/master/zipvoice/bin/train_zipvoice.py)
- 本案 checkpoint 檔名是 `sherpa-onnx-zipvoice-distill-int8-zh-en-emilia`。
- Emilia 官方 README 說原始 101k-hour Emilia 是 `CC BY-NC 4.0`，只准 non-commercial，且原始音訊著作權仍屬原權利人。[Emilia official README](https://github.com/open-mmlab/Amphion/blob/main/preprocessors/Emilia/README.md)

### 4.2 缺少

- `sherpa-onnx` 的 `tts-models` release body 只說這是 pretrained TTS models，沒有替這個 exact ZipVoice checkpoint 明示 model license、training-data grant 或 commercial-use grant。[`tts-models` release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models)
- `vocoder-models` release body 也沒有替 `vocos_24khz.onnx` 提供清楚的 model-specific license。[`vocoder-models` release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/vocoder-models)
- 沒有官方聲明說 Apache-2.0 source license 覆蓋由 Emilia 訓練的 weights，或排除原始音訊權利人的主張。

### 4.3 判斷

**官方事實：** code 是 Apache-2.0；Emilia dataset 是 non-commercial；model release 未明示 exact checkpoint 的 license。

**保守推論：** 本案 checkpoint 與 Emilia 有強連結，但僅憑檔名與 training recipe 仍不能替 exact weights 補上一份不存在的 model card/license。

**結論：** 可把它視為待審的隔離研究候選，不能把「GitHub 免費下載」等同「可供旅行社商用」。在 maintainer 提供 model-specific 商用授權／provenance，或法律審查完成前，不應進入旅客、客戶、LINE、正式說明會或營運產物。這是風險邊界，不是法律意見。

## 5. 建議的下一個安全 gate

建議不要再碰 SmartSub 3.7.0 installer。若使用者要繼續，另立 **Gate D2：官方 sherpa-onnx runtime-only capability proof**，精確授權下列最小動作：

1. 只下載 v1.13.6 的 `sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2`；驗證 `24,497,928` bytes 與 `4a296e...ce4613`。
2. 先唯讀列出 archive；拒絕 absolute path、`..` traversal、symlink/reparse-point escape 及非單一預期 root，再解到新的 per-user dedicated directory。
3. 列出實際 executable/DLL、重算 hashes、查看 Authenticode；不要因 unsigned 自動放寬，實際狀態如實記錄。
4. 第一層 proof 只執行 `sherpa-onnx-offline-tts --help`／版本資訊，確認 process exit、CPU-capable options 與無 network prompt，然後停止。
5. Model archive 的 listing、解壓與 required-file validation 必須在授權文字中另行明示；不得默認包含。
6. 「model 能載入」若沒有安全的 no-generate API，不能偷換成合成。任何 reference audio、reference text、本人影片、聲音建立或 WAV 產出都仍屬下一個 Gate R／synthesis gate。
7. 在任何 customer-facing 或正式產出前，另立 license decision gate。

這個 D2 能先回答「官方 runtime 是否能在本機 Windows 25H2 啟動」，同時不把研究授權擴張成影片處理或語音合成。

## 6. 最終判定

| 問題 | 判定 |
|---|---|
| SmartSub 3.7.0 crash 是否只是本機偶發？ | **否；同一 crash signature 已由官方 issue 重現。** |
| 根因是否已被官方確認為 Windows 25H2？ | **否；只有強推論。** |
| 是否已有官方 fix/workaround？ | **截至 2026-08-20 未找到。** |
| 是否應重跑／變形執行同一 installer？ | **不建議。** |
| 可否繞過 SmartSub installer 直接跑 ZipVoice？ | **介面與官方 Windows CPU runtime 均存在，技術上可行。** |
| 本機是否已證明可跑、夠快、夠自然？ | **未驗證。** |
| 需要 ASR／CUDA／Vulkan／cloud 嗎？ | **pre-built CPU CLI 路徑不需要這些 model/加速/cloud 依賴。** |
| 可否直接商用？ | **不可宣稱；exact model 的商用權利未釐清。** |
