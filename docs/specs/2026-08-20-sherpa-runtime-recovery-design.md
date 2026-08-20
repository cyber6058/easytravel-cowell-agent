# sherpa-onnx Gate D2-U runtime recovery 設計

日期：2026-08-20

狀態：三段口頭設計已核准；本書面規格待使用者審閱。

前置文件：

- `docs/specs/2026-08-20-sherpa-runtime-only-capability-proof-design.md`
- `docs/plans/2026-08-20-sherpa-runtime-only-capability-proof-implementation-plan.md`
- `STATUS.md` 的 Gate D2-X 與 Gate D2-U 實際證據

## 1. 決策摘要

Gate D2-U 已消耗一次 unsigned exact-hash 授權，但在執行任何 sherpa command 前，因零筆
PowerShell process probe 沒有輸出 JSON 而安全失敗。Recovery 不得重跑原本的
`prove-runtime`、不得修改或偽裝舊 proof，也不得再次 promote runtime。

本設計採用四個固定決策：

1. 修正 process、listener、Event 三種 PowerShell probe 的 0／1／多筆 JSON array 契約。
2. 原始失敗 proof 永久唯讀，另建一份 hash-bound、single-use recovery child proof。
3. Gate D2-UR-I 只實作、測試、執行唯讀 Windows probes，並建立一份實際 child proof。
4. Gate D2-UR-X 必須另行逐值核准，才允許固定 version utility 與 `offline-tts --help`
   各執行一次。

這個 recovery 只回答「固定 sherpa-onnx runtime 能否在本機啟動並提供預期 CLI help」。它
仍不能證明 ZipVoice model 能載入、速度可接受、聲音自然，或模型可商用。

## 2. 已凍結的 parent proof

Recovery 只能接受下列唯一 parent；任何值不同都必須停止：

| 欄位 | 凍結值 |
|---|---|
| proof directory | `C:\Users\cance\AppData\Local\EasyTravelVoicePilot\proofs\runtime-v1.13.6-20260820T014555Z-b6b2c9b9` |
| evidence ID | `a3ba6b11-5b57-46db-b5e7-113c36e9d964` |
| final canonical manifest SHA-256 | `e841a4f6ee1aa24bb7bd78c8b57ac88336f84512b175bbd44066f099829d2123` |
| final `runtime-proof.json` SHA-256 | `3e4e1fdec33d11e60096a58e8b35f12766ffeeab620582961634af27c49f06e9` |
| top-level state | `FAILED` |
| safe code | `RUNTIME_POSTFLIGHT_DIRTY` |
| preparation initial state | `BLOCKED_UNSIGNED` |
| preparation current state | `READY_TO_EXECUTE` |
| promoted | `true` |
| authorization | `unsigned-exact-hash` |
| execution commands | empty array |
| runtime root | `C:\Users\cance\AppData\Local\EasyTravelVoicePilot\runtime\sherpa-onnx\1.13.6` |

固定 runtime identity：

| 項目 | Bytes | SHA-256 |
|---|---:|---|
| outer archive | 24,497,928 | `4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613` |
| canonical 8-row load inventory | — | `d3d440c0345eee6e6dae680c07036c830896b5bbfc98f4774f83b243cc05786f` |
| `bin/sherpa-onnx-version.exe` | 141,312 | `7cb2de6405de878417635845278b1be01413650b36e64c30df5314128f109869` |
| `bin/sherpa-onnx-offline-tts.exe` | 2,763,776 | `a62495554c6953d523626cfba0944be353857c9840b0e513170d45ba0e76a9f0` |

八個 load candidates 都是 `NotSigned`；完整 relative path、bytes 與 digest 仍以原 parent
proof 和既有 D2 計畫的 actual evidence 為準。Recovery 必須重新計算實檔 inventory，不能
只相信本表。

## 3. 目的與非目的

### 3.1 目的

- 修正零筆 probe 輸出造成的 false failure，同時保留 fail-closed 行為。
- 證明 parent、archive identity、完整 runtime inventory 與 child proof 之間的可驗證鏈結。
- 讓未來一次 recovery execution 不會重複 promote、不會覆寫 parent，也不會被重播。
- 在任何 binary execution 前留下明確的 single-use consume state。
- 讓中途 crash、timeout、非零退出、help contract mismatch 或 postflight dirty 都安全停止。

### 3.2 非目的

- 不修 SmartSub installer，也不啟動 SmartSub 或 Yating。
- 不下載、解壓、部署或讀取 model／vocoder。
- 不讀取使用者的影片、音訊或照片，不建立 reference audio 或音色。
- 不接受 text、model、reference、output、server、port、network、admin 或 compatibility mode
  參數。
- 不合成 WAV／MP3，不評估 A「整篇語調太平」或 B「句子交界生硬」。
- 不處理授權或商用適用性，不改 briefing workflow、依賴、PATH、registry、firewall 或排程。
- 不登入、不上傳、不發 LINE、不部署、不發布、不 push。

## 4. 已選方案與拒絕方案

### 4.1 已選：immutable parent + recovery child

Parent 是已發生事件的證據，保持 byte-for-byte 不變。新的 child proof 引用 parent 的
evidence ID、canonical manifest SHA-256、proof-file SHA-256、runtime identity 與失敗原因。
只有 child 可在未來 recovery execution 中由 `RECOVERY_READY` 前進到 terminal state。

這保留完整稽核鏈、避免把已消耗的 D2-U ack 當成新授權，也能明確實作 single-use。

### 4.2 拒絕：直接修改 parent 後重跑

這會改寫歷史失敗、模糊原授權是否已消耗，且無法從 final proof 區分第一次失敗與第二次
執行，因此禁止。

### 4.3 拒絕：把已 promoted runtime 當成全新 proof

這會繞過原本 archive、staging、unsigned ack 與 promotion 的因果鏈，也可能重複搬移或讓
錯誤 runtime 被當成新來源，因此禁止。

## 5. Repository 邊界

修改範圍固定為：

- `scripts/voice_pilot/runtime_proof.py`
- `tests/unit/voice_pilot/test_runtime_proof.py`
- 本設計後續對應的 implementation plan
- `STATUS.md`

維持單一 `runtime_proof.py`，在現有 CLI、path validation、canonical JSON、inventory verifier
與 bounded runner 上增加 recovery seam；不建立通用 workflow engine，也不重構無關程式。

Private evidence 固定留在：

```text
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\proofs\
```

Parent、child、runtime、archive 與任何 proof evidence 都不得加入 Git。

## 6. Probe JSON 契約

三個 production PowerShell scripts 都採同一形式：

```powershell
$rows = @(
    # 原有唯讀查詢與 Select-Object
)
ConvertTo-Json -InputObject $rows -Compress
```

契約如下：

- 0 筆必須輸出 `[]`。
- 1 筆必須輸出單元素 array，不能輸出 bare object。
- 多筆必須輸出 array。
- process、listener、Event 三個 scripts 都必須符合相同契約。
- `_powershell_json_probe()` 以 array 為正式格式；為相容既有單筆 PowerShell 行為，可將 bare
  object 正規化為單元素 list。
- 空 stdout、JSON `null`、scalar、非法 JSON、非零 exit、超過 1 MiB、編碼失敗或 30 秒
  timeout 都映射為 `RUNTIME_POSTFLIGHT_DIRTY`，不得被當成零筆成功。

Gate D2-UR-I 的 real-probe validation 只執行這三個唯讀 PowerShell queries，確認本機實際
輸出能解析為 array。0／1／多筆的完整組合由 synthetic tests 保證；不為了製造筆數而啟動
程序或 listener。

## 7. Recovery child proof

### 7.1 建立命令

現有 CLI 新增 `prepare-runtime-recovery`。它接受 parent proof directory、全新 child proof
directory，以及下列 literal acknowledgements：

- parent evidence ID；
- parent canonical manifest SHA-256；
- parent proof-file SHA-256；
- outer archive SHA-256；
- load inventory SHA-256；
- mandatory executable SHA-256。

命令不接受 runtime binary arguments、model、text、reference 或 output。

### 7.2 建立前 eligibility

在建立 child directory 前必須完成：

1. parent 與 child 都是 per-user proofs root 下的 absolute path，且不在 repository 中。
2. parent、proofs root、runtime root 與 child 的既有 parent chain 都不是 reparse point。
3. child path 不存在；不覆寫、不接續、不沿用半成品。
4. parent proof-file SHA、canonical manifest 與 evidence ID 全部符合凍結值。
5. parent schema 有效，top-level 是 `FAILED/RUNTIME_POSTFLIGHT_DIRTY`。
6. preparation 是 `initial_state=BLOCKED_UNSIGNED`、`state=READY_TO_EXECUTE`、
   `promoted=true`。
7. execution authorization 是 `unsigned-exact-hash`，`commands` 是空 array。
8. runtime root 是固定 final path，存在且不是 reparse point。
9. archive binding、完整 8-row runtime inventory、outer／inventory／mandatory hashes 全部重驗
   相符。
10. 所有 literal acknowledgements 相符。

任一步失敗都不得建立 child、修改 parent、移動 runtime 或執行 EXE。

### 7.3 Child schema

新檔名固定為 `runtime-recovery-proof.json`，schema 固定為
`easytravel.sherpa-runtime-recovery-proof.v1`。至少包含：

- 自己的 evidence ID、state、safe code、created UTC 與 canonical manifest SHA-256；
- parent proof directory、evidence ID、manifest SHA-256 與 proof-file SHA-256；
- parent eligibility snapshot；
- outer archive SHA-256；
- inventory SHA-256、完整 8-row identity、mandatory executable identity，以及存在時的 version
  executable identity；
- fixed runtime root；
- `execution: null`；
- `RECOVERY_READY` 建立原因 `ZERO_RESULT_PROBE_SERIALIZATION_FIXED`。

Canonical manifest 的計算沿用 parent proof：以 UTF-8 canonical JSON 對排除
`manifest_sha256` 後的文件計算 SHA-256。Child proof-file SHA-256 在檔案完成後另行計算並交付，
不把自己的 file hash 寫回檔內，避免自我遞迴。

### 7.4 Read-only verifier

新增 `verify-runtime-recovery`。它重新驗證 child manifest、parent identity、parent file、archive
binding、runtime inventory、狀態與 command evidence，但不修正、promote、執行或改寫任何檔案。

## 8. Recovery state machine

Child 只有下列狀態：

```text
RECOVERY_READY
  -> RECOVERY_EXECUTING
       -> PASSED
       -> FAILED
```

- `RECOVERY_READY`：D2-UR-I 已完成，沒有 binary execution。
- `RECOVERY_EXECUTING`：D2-UR-X 的 exact child identity 已驗證，child 已被原子消耗。
- `PASSED`／`FAILED`：terminal；永遠不得再次 resume。
- 程序若在 terminal write 前 crash，child 保留 `RECOVERY_EXECUTING`，視為 unknown result；不得
  自動重試、重設成 ready 或另行直接執行。

Parent 在所有狀態轉換中都保持 byte-for-byte 不變。

## 9. Gate D2-UR-X 執行資料流

`resume-runtime-proof` 是未來 D2-UR-X 專用命令。它只能處理前述 parent 與一份尚未使用的
child。

### 9.1 Exact gate 與 pre-consumption validation

D2-UR-I handoff 必須先提供完整實際值，讓使用者另行逐值核准：

- implementation commit SHA；
- parent evidence ID、manifest SHA-256、proof-file SHA-256；
- child evidence ID、manifest SHA-256、proof-file SHA-256；
- outer archive SHA-256；
- inventory SHA-256；
- version executable SHA-256；
- mandatory executable SHA-256。

Operator invocation 必須帶 literal `--ack-runtime-recovery-once` 和上述 identity arguments。
Child identity／file hash 尚未驗證前的錯誤不准改寫任一 proof。Child identity 確認後，任何
parent、ack、state、path、runtime inventory 或 probe mismatch 都將 child 原子完成為
`FAILED`、`commands=[]`，並停止。

### 9.2 Consume point

全部 identity、ack、runtime inventory，以及 process／listener preflight probes 通過後，先將
child 原子寫成 `RECOVERY_EXECUTING`，再允許第一個 binary。這個 transition 是 single-use
consume point；之後無論成功、失敗或 crash 都不得重用 child。

### 9.3 唯一允許的 commands

順序固定：

1. `bin/sherpa-onnx-version.exe`，無額外 argument，只執行一次。
2. `bin/sherpa-onnx-offline-tts.exe --help`，只執行一次。

每個 command 都必須：

- 使用 argument list 與 `shell=False`；
- `stdin=subprocess.DEVNULL`；
- cwd 固定為該 executable directory；
- 每個 command timeout 30 秒；
- 只在 child environment 的 PATH 前置固定 runtime `bin` 與 `lib`；
- 不改 parent process environment、registry、system PATH 或 compatibility settings；
- bounded capture stdout／stderr，記錄 bytes、SHA-256、截斷後 base64、exit 與 elapsed time。

Version command 完成後，必須先原子寫入該 command evidence，才可進入 help。Help 完成後也先
原子寫入 command evidence，再執行 postflight。若 abrupt crash，已完成的 command evidence
因此仍可稽核，而 child 不能再用。

### 9.4 Postflight 與結果

執行後固定取得：

- related process snapshot；
- TCP listener snapshot；
- invocation window 內的 Application Error Event 1000；
- runtime inventory re-verification。

下列任一情況都令 child `FAILED`，不重試：

- command launch exception、timeout 或非零 exit；
- required help tokens 不完整；
- 新 related process、listener 或 Event 1000；
- 任一 postflight probe unknown／invalid；
- runtime inventory 改變；
- child evidence 寫入或驗證失敗。

只有兩個 commands 都符合 contract、postflight clean、inventory unchanged，child 才能是
`PASSED`。完成後執行一次 read-only verifier，更新 `STATUS.md`、建立本機 docs commit並停止。

## 10. Safe codes 與 exit

沿用既有 safe codes，避免建立第二套相同語意：

| 情況 | Safe code |
|---|---|
| path 越界或 reparse | `RUNTIME_PATH_OUTSIDE_PER_USER_ROOT` |
| child path 已存在 | `RUNTIME_OUTPUT_EXISTS` |
| parent 不符合唯一 eligibility | `RUNTIME_RECOVERY_PARENT_INELIGIBLE` |
| exact ack 不符 | `RUNTIME_ACK_MISMATCH` |
| parent、child 或 runtime identity／inventory 被改變 | `RUNTIME_EVIDENCE_TAMPERED` |
| child 不是 `RECOVERY_READY` | `RUNTIME_RECOVERY_ALREADY_USED` |
| probe 失敗或 postflight dirty | `RUNTIME_POSTFLIGHT_DIRTY` |
| timeout | `RUNTIME_HELP_TIMEOUT` |
| launch exception 或非零 exit | `RUNTIME_HELP_NONZERO` |
| help tokens 不符 | `RUNTIME_HELP_CONTRACT_MISMATCH` |

`RECOVERY_READY`、`PASSED` 與成功的 read-only verify 回傳 exit `0`；所有 rejected、`FAILED`、
`RECOVERY_EXECUTING` unknown-result 或 tampered 狀態回傳 exit `30`。Safe code 不包含 private
path、exception text 或超過 80 characters 的內容；詳細診斷只留在 private child evidence。

## 11. 測試設計

### 11.1 Probe tests

- process／listener／Event 各自覆蓋 0、1、多筆結果，並斷言 production script 輸出 array。
- bare object 相容正規化為單元素 list。
- empty stdout、JSON null、scalar、invalid JSON、nonzero、timeout、encoding failure、oversize
  全部 fail closed。

### 11.2 Parent 與 child tests

- 唯一合法 parent 能建立 `RECOVERY_READY` child。
- parent evidence ID、manifest、proof-file hash、state、safe code、initial state、promoted、
  authorization、commands、三個 approved hashes、version identity、runtime path 或任一 inventory
  row 不符，都在 child creation 前拒絕。
- child exclusive-create、防覆寫、absolute per-user path、no-reparse 與 repository exclusion。
- child canonical manifest、proof-file tamper、parent-after-child tamper 與 runtime-after-child tamper。
- verifier 全程 read-only。

### 11.3 Resume tests

- 缺少 child、錯誤 child、已用 child、錯誤 ack 或 implementation handoff identity 都拒絕。
- runtime 不可再次 promote、move、copy 或 extract。
- fixed argv、order、cwd、`shell=False`、closed stdin、child PATH 與 30 秒 timeout。
- parser／CLI 不存在 model、text、reference、output、server、port 或任意 command seam。
- consume 前無 binary；consume 後 command 最多各一次。
- version evidence 必須在 help 前持久化；crash 留在 `RECOVERY_EXECUTING` 且不可重播。
- timeout、nonzero、help mismatch、process、listener、Event、unknown probe、inventory change 都
  terminal fail。
- `PASSED` 與每一種 `FAILED` child 都能被 read-only verifier驗證；任何 evidence tamper 被拒絕。

### 11.4 Implementation verification

Gate D2-UR-I 必須完成：

- focused recovery tests；
- 完整離線 suite；
- `compileall`；
- `git diff --check`；
- production source scan，證明沒有 network client、unsafe extraction、model／media／synthesis
  options 或新依賴；
- SmartSub、sherpa 與 WINWORD process before／after counts；
- 三個 read-only real Windows probes 的合法 JSON array evidence；
- protected briefing、Yating、pilot、dependency、Skill／plugin 與 deployment paths 0 diff。

不得放寬、skip 或刪除既有 tests 來換取綠燈。

## 12. Gate 分離與完成定義

### 12.1 Gate D2-UR-I：implementation + child preparation

必須另行核准 implementation plan 後才可執行。授權範圍只有：

- 修改固定 repository files；
- synthetic tests 與完整離線驗證；
- 唯讀 Windows probes；
- 唯讀讀取 parent proof、archive binding 與已 promoted runtime 的 8-row bytes／hash／signature
  metadata；
- 建立一份新的 per-user child proof；
- 唯讀驗證 child；
- 更新 STATUS、建立本機 code／docs commits並停止。

D2-UR-I 完成只代表 recovery mechanism 綠燈且 child 是 `RECOVERY_READY`。它不授權 sherpa
binary execution，也不代表 runtime capability proof 通過。

### 12.2 Gate D2-UR-X：single runtime recovery execution

只有 D2-UR-I handoff 提供所有 actual values，且使用者另行逐值核准完整 literal gate 後，才
允許一個 `resume-runtime-proof` invocation。不得因 tests、child ready 或使用者先前核准
D2-U 而推定授權。

D2-UR-X 完成後停止。即使 child `PASSED`，model deployment、model load、reference extraction
及 synthesis 仍需新的各自設計與明確 Gate。

## 13. D2-UR-I handoff

Handoff 必須列出：

- baseline、implementation commit、docs commit 與工作樹狀態；
- focused／full suite／compile／scope proof 的關鍵原文輸出；
- real probes 的 row counts、JSON type 與 error status；
- parent identity 與重新驗證結果；
- child resolved directory、evidence ID、manifest SHA-256、proof-file SHA-256 與 state；
- outer、inventory、version、mandatory executable exact hashes；
- SmartSub／sherpa／WINWORD before-after process counts；
- 未執行的 binary、model、media、synthesis、login、upload、push 清單；
- 由 actual values 完整產生、沒有空白欄位的 D2-UR-X approval sentence。

本設計沒有授權 D2-UR-I 或 D2-UR-X；目前下一步只有使用者審閱本書面規格。
