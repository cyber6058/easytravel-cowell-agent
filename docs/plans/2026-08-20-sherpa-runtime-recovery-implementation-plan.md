# sherpa-onnx Gate D2-UR runtime recovery 實作計畫

日期：2026-08-20

依據：
`docs/specs/2026-08-20-sherpa-runtime-recovery-design.md`

設計基線 commit：
`bf44301630d6706e65c5cd9f98363941b157fc20`

狀態：書面設計已核准；本實作計畫等待使用者審閱。本文件只規劃工作，不授權修改程式、
執行 tests／real probes、讀取 per-user parent／archive／runtime、建立 recovery child、執行
sherpa、讀取 model／本人素材、合成、登入、上傳或 push。

## 0. 目的、Gate 與停止範圍

本計畫修復已確認的零結果 PowerShell JSON bug，並在不改寫 D2-U parent proof、不重複
promotion 的條件下，建立一份 hash-bound、single-use recovery child proof。

工作分成兩個互不授權的 Gate：

- Tasks 1–7 是未來 Gate D2-UR-I：實作、synthetic tests、完整離線驗證、一組唯讀 real
  Windows probes，以及建立／驗證一份實際 `RECOVERY_READY` child proof。
- Task 8 是未來 Gate D2-UR-X：只有使用者逐值核准 Task 7 交付的 actual child identity 後，
  才能執行一次 version utility 與一次 `offline-tts --help`。

D2-UR-I 通過不自動授權 D2-UR-X。D2-UR-X 通過也不自動授權 model deployment、model load、
reference extraction 或 synthesis。

即使本計畫全部完成，也只能回答 sherpa-onnx runtime version/help capability，不能宣稱：

- ZipVoice model 可載入或速度可接受；
- 本人相似度、自然度、A「整篇語調太平」或 B「句子交界生硬」已改善；
- Emilia-linked model 可供 EasyTravel 商用；
- 可以取代 Yating、交付旅客或整合正式 briefing workflow。

本計畫不包含 download、archive extraction、model／vocoder、本人影片／照片／音訊、reference
audio／text、TTS text、output WAV／MP3、SmartSub、Yating、ASR、CUDA、Vulkan、新 dependency、
cloud、login、upload、LINE、Cowell、deployment、cleanup 或 push。

## 1. 凍結 parent、runtime 與實作基線

Production recovery 只能接受下列唯一 parent：

| 欄位 | 固定值 |
|---|---|
| parent directory name | `runtime-v1.13.6-20260820T014555Z-b6b2c9b9` |
| parent evidence ID | `a3ba6b11-5b57-46db-b5e7-113c36e9d964` |
| parent manifest SHA-256 | `e841a4f6ee1aa24bb7bd78c8b57ac88336f84512b175bbd44066f099829d2123` |
| parent proof-file SHA-256 | `3e4e1fdec33d11e60096a58e8b35f12766ffeeab620582961634af27c49f06e9` |
| parent top-level state／safe code | `FAILED`／`RUNTIME_POSTFLIGHT_DIRTY` |
| preparation | `initial_state=BLOCKED_UNSIGNED`、`state=READY_TO_EXECUTE`、`promoted=true` |
| execution | `authorization=unsigned-exact-hash`、`commands=[]` |
| runtime root | `C:\Users\cance\AppData\Local\EasyTravelVoicePilot\runtime\sherpa-onnx\1.13.6` |

固定 identities：

| 項目 | Bytes | SHA-256 |
|---|---:|---|
| outer archive | 24,497,928 | `4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613` |
| canonical 8-row load inventory | — | `d3d440c0345eee6e6dae680c07036c830896b5bbfc98f4774f83b243cc05786f` |
| `bin/sherpa-onnx-version.exe` | 141,312 | `7cb2de6405de878417635845278b1be01413650b36e64c30df5314128f109869` |
| `bin/sherpa-onnx-offline-tts.exe` | 2,763,776 | `a62495554c6953d523626cfba0944be353857c9840b0e513170d45ba0e76a9f0` |

Production source 使用 pinned recovery spec 同時綁定這些值；不能只相信 operator 傳入的 ack。
Synthetic tests 另注入 temporary recovery spec，不讀取 production parent 或 runtime。

## 2. 允許檔案、0-diff controls 與 commit map

### 2.1 Gate D2-UR-I 允許修改

- `scripts/voice_pilot/runtime_proof.py`
- `tests/unit/voice_pilot/test_runtime_proof.py`
- 本計畫的 actual evidence section
- `STATUS.md`

不新增 dependency、fixture binary、script、module、package entrypoint 或 ignore rule。

### 2.2 嚴格 0 diff

- `scripts/voice_pilot/pilot.py`
- `scripts/voice_pilot/synthesize_yating_baseline.py`
- `src/travel_briefing/`
- `tests/unit/travel_briefing/`
- 其他 tests、正式 briefing CLI、Skill、plugin、config、schemas、package version與 dependencies
- private LIST master、calibration、既有 DRAFT／briefing artifacts
- Cowell、NewAmazing、JMA、Word、LINE、Cloudflare 與 deployment files

Parent proof、runtime、archive、child proof、consumption record 與 probe evidence 都在 repository
外，永遠不得加入 Git。

### 2.3 未來 commits

1. `fix(voice-pilot): serialize empty probes as arrays`
   - 只含三個 PowerShell probe scripts、decoder contract與相關 tests。
2. `feat(voice-pilot): add runtime recovery proof`
   - 只含 recovery spec、child／consumption evidence、verifier、resume runner、CLI 與 tests。
3. `docs: record Gate D2-UR-I recovery handoff`
   - 只含本計畫 actual evidence 與 `STATUS.md`。

三個 commits 只留本機，不 push。本計畫被核准也不代表 D2-UR-I 已核准。

## 3. Public seam、schemas、CLI 與 safe codes

### 3.1 新資料模型

`scripts/voice_pilot/runtime_proof.py` 新增：

```text
RuntimeRecoverySpec
RuntimeRecoveryProof
PINNED_RUNTIME_RECOVERY
```

`RuntimeRecoverySpec` 固定包含：parent directory name、parent evidence ID、parent manifest、parent
proof-file hash、outer hash、inventory hash、expected load-candidate count `8`、required signature
status `NotSigned`、version executable hash與 mandatory executable hash。

`RuntimeRecoveryProof` 固定包含：state、safe code、exit code、evidence ID、recovery proof directory、
current manifest SHA-256與current proof-file SHA-256。它不包含 model、reference、text 或 output
欄位。

`RuntimeAdapters` 新增一個 `recovery_spec` 欄位；production default 使用
`PINNED_RUNTIME_RECOVERY`，tests 注入 synthetic spec。現有唯一 test adapter constructor同步更新，
但既有 runtime proof行為與 public seams保持不變。

### 3.2 新函式 seam

```text
validate_runtime_recovery_paths(
    repo_root, per_user_root, parent_proof_dir, recovery_proof_dir,
    runtime_dir=None, *, recovery_must_exist
)

prepare_runtime_recovery(
    parent_proof_dir, recovery_proof_dir, *, spec,
    ack_parent_evidence_id,
    ack_parent_manifest_sha256,
    ack_parent_proof_file_sha256,
    ack_outer_sha256,
    ack_load_inventory_sha256,
    ack_executable_sha256
) -> RuntimeRecoveryProof

verify_runtime_recovery(
    recovery_proof_dir, *, spec
) -> RuntimeRecoveryProof

resume_runtime_proof(
    parent_proof_dir, recovery_proof_dir, runtime_dir, *, spec,
    runner, process_probe, listener_probe, event_probe,
    ack_runtime_recovery_once,
    ack_parent_evidence_id,
    ack_parent_manifest_sha256,
    ack_parent_proof_file_sha256,
    ack_recovery_evidence_id,
    ack_recovery_manifest_sha256,
    ack_recovery_proof_file_sha256,
    ack_outer_sha256,
    ack_load_inventory_sha256,
    ack_version_executable_sha256,
    ack_executable_sha256
) -> RuntimeRecoveryProof
```

Tests只注入 synthetic runner／probes／spec；Tasks 1–6的tests不啟動production PowerShell probe
subprocess、Authenticode或第三方binary，也不讀production per-user files。Operator仍可執行本
計畫明列的repository、test與read-only process-count preflight commands。

### 3.3 Evidence filenames與schemas

```text
runtime-recovery-proof.json
  schema: easytravel.sherpa-runtime-recovery-proof.v1

runtime-recovery-consumption.json
  schema: easytravel.sherpa-runtime-recovery-consumption.v1
```

兩個文件都使用既有 UTF-8 canonical JSON、sorted keys、compact separators與排除自身
`manifest_sha256` 後的 SHA-256 規則。

Child 初始狀態固定 `RECOVERY_READY`、`execution=null`、reason
`ZERO_RESULT_PROBE_SERIALIZATION_FIXED`，且 consumption file 不存在。

Consumption file 只由 `resume-runtime-proof` 以 exclusive-create 建立一次。它保存 consumption
ID、UTC、pre-consume child evidence ID／manifest／proof-file SHA-256與自己的 manifest。Child
進入 `RECOVERY_EXECUTING` 時保存 consumption proof-file SHA-256和全部 literal acks。

### 3.4 CLI seam

```text
prepare-runtime-recovery \
  --parent-proof-dir PATH --recovery-proof-dir PATH \
  --ack-parent-evidence-id ID \
  --ack-parent-manifest-sha256 HASH \
  --ack-parent-proof-file-sha256 HASH \
  --ack-outer-sha256 HASH \
  --ack-load-inventory-sha256 HASH \
  --ack-executable-sha256 HASH

verify-runtime-recovery RECOVERY_PROOF_DIR

resume-runtime-proof \
  --parent-proof-dir PATH --recovery-proof-dir PATH --runtime-dir PATH \
  --ack-runtime-recovery-once \
  --ack-parent-evidence-id ID \
  --ack-parent-manifest-sha256 HASH \
  --ack-parent-proof-file-sha256 HASH \
  --ack-recovery-evidence-id ID \
  --ack-recovery-manifest-sha256 HASH \
  --ack-recovery-proof-file-sha256 HASH \
  --ack-outer-sha256 HASH \
  --ack-load-inventory-sha256 HASH \
  --ack-version-executable-sha256 HASH \
  --ack-executable-sha256 HASH
```

Parser沒有 model、reference、text、output、server、port、network、admin、compatibility、download、
extract、cleanup 或 arbitrary command option。

Recovery CLI stdout限制在 2 KiB內，欄位固定為：state、safe code、evidence ID、parent evidence
ID、current manifest、current proof-file hash、outer／inventory／version／mandatory hashes與下一步。
不輸出 private path、完整 inventory rows、exception text或第三方 stdout全文。

### 3.5 State、exit與safe codes

| State | Exit | 意義 |
|---|---:|---|
| `RECOVERY_READY` | 0 | Child準備完成；停止並請求 D2-UR-X |
| `RECOVERY_EXECUTING` | 30 | Consumed unknown result；禁止重試 |
| `PASSED` | 0 | Version/help與postflight通過；停止 |
| `FAILED` | 30 | Contract／execution／evidence失敗；停止 |

新增兩個safe codes：

```text
RUNTIME_RECOVERY_PARENT_INELIGIBLE
RUNTIME_RECOVERY_ALREADY_USED
```

其餘沿用：

```text
RUNTIME_PATH_OUTSIDE_PER_USER_ROOT
RUNTIME_PATH_INSIDE_REPOSITORY
RUNTIME_OUTPUT_EXISTS
RUNTIME_ACK_MISMATCH
RUNTIME_EVIDENCE_TAMPERED
RUNTIME_POSTFLIGHT_DIRTY
RUNTIME_HELP_TIMEOUT
RUNTIME_HELP_NONZERO
RUNTIME_HELP_CONTRACT_MISMATCH
```

Safe code不含private path／exception text且不超過80 characters。同一 child creation、consume或
runtime execution failure都不自動retry。

## Task 1：Gate D2-UR-I preflight與probe JSON contract TDD

### 1.1 Preflight

Gate D2-UR-I 被逐字核准後才執行：

```powershell
git status --short --branch
git pull --ff-only
$d2urBaseline = git rev-parse HEAD
Test-Path '.\.venv\Scripts\python.exe'
(Get-Process SmartSub -ErrorAction SilentlyContinue | Measure-Object).Count
(Get-Process sherpa-onnx-version -ErrorAction SilentlyContinue | Measure-Object).Count
(Get-Process sherpa-onnx-offline-tts -ErrorAction SilentlyContinue | Measure-Object).Count
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
```

要求：working tree乾淨、pull是`Already up to date.`、HEAD等於使用者核准的plan handoff commit、
四類process都是0，且既有`.venv`存在。若`.venv`或pytest缺失，停止；D2-UR-I不授權pip/network
安裝。

先記錄baseline focused與完整離線suite：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\voice_pilot\test_runtime_proof.py -q
.\.venv\Scripts\python.exe -X utf8 -m pytest
```

Baseline不是新功能驗證，只證明修改前狀態；任一非綠停止。

### 1.2 RED：probe tests

在`tests/unit/voice_pilot/test_runtime_proof.py`新增：

```text
test_probe_scripts_use_inputobject_array_contract
test_probe_decoder_accepts_zero_one_many_arrays_and_legacy_object
test_probe_decoder_rejects_empty_null_scalar_invalid_or_oversized_stdout
test_probe_decoder_rejects_nonzero_timeout_encoding_and_launch_failures
```

Tests monkeypatch `subprocess.run`，不得實際啟動PowerShell。0／1／多筆輸出必須各自正規化為
Python list；legacy bare object只允許正規化為單元素list。Empty stdout、JSON `null`、scalar、
invalid JSON、nonzero、timeout、encoding failure與超過1 MiB全部是
`RUNTIME_POSTFLIGHT_DIRTY`。

執行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\voice_pilot\test_runtime_proof.py `
  -k "probe_scripts or probe_decoder" -q
```

預期先因現有pipeline與`null`相容行為失敗；不得改斷言讓它變綠。

### 1.3 GREEN：最小修正

三個scripts改成先指派array，再使用`-InputObject`：

```powershell
$rows = @(
    # 原查詢
)
ConvertTo-Json -InputObject $rows -Compress
```

`_powershell_json_probe()`：

- list直接回傳；
- dict正規化為單元素list；
- empty stdout、decoded `None`與scalar拒絕；
- 保留`-NoProfile`、`-NonInteractive`、encoded command、closed stdin、30秒timeout與1 MiB上限。

執行focused、完整suite、compile與diff check：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\voice_pilot\test_runtime_proof.py -q
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q `
  scripts\voice_pilot tests\unit\voice_pilot
git diff --check
```

全部exit `0`後建立第一個code commit。此Task不執行real probe。

## Task 2：Pinned recovery spec、path與parent eligibility TDD

### 2.1 RED：synthetic eligible parent helper

新增test helper `_prepare_failed_promoted_unsigned_parent()`：

1. 建立temporary synthetic archive、mandatory EXE、version EXE與六個DLL，合計八個load
   candidates；
2. 注入`NotSigned`signature records；
3. 用現有`prepare_runtime()`建立`BLOCKED_UNSIGNED`parent；
4. 用synthetic exact hashes呼叫一次`run_runtime_proof()`；
5. process probe故意在command loop前失敗，runner若被呼叫就raise assertion；
6. 斷言parent是`FAILED/RUNTIME_POSTFLIGHT_DIRTY`、`promoted=true`、
   `authorization=unsigned-exact-hash`、`commands=[]`。

這只操作pytest temporary tree，不讀production parent／archive／runtime，也不執行任何synthetic
檔案。

新增tests：

```text
test_pinned_runtime_recovery_matches_frozen_parent_contract
test_recovery_paths_require_fixed_per_user_parent_runtime_and_new_child
test_recovery_paths_reject_relative_repo_outside_root_existing_or_reparse_paths
test_parent_eligibility_accepts_only_failed_promoted_unsigned_empty_command_parent
test_parent_eligibility_rejects_identity_state_auth_command_or_hash_mismatch
test_parent_eligibility_rejects_archive_runtime_inventory_or_load_set_tampering
test_parent_eligibility_requires_exact_eight_notsigned_rows_and_fixed_executables
```

### 2.2 GREEN：資料模型與pure validators

新增`RuntimeRecoverySpec`、`RuntimeRecoveryProof`與`PINNED_RUNTIME_RECOVERY`。Production pinned
constant逐值寫入§1所有identities。

新增：

```text
validate_runtime_recovery_paths(...)
_read_parent_for_recovery(...)
_validate_parent_recovery_eligibility(...)
```

Eligibility順序固定：

1. path／reparse／repo boundary；
2. parent proof-file SHA；
3. parent schema／canonical manifest／evidence ID；
4. top-level與preparation state；
5. authorization與empty commands；
6. pinned outer／inventory／version／mandatory identities；
7. archive binding；
8. final runtime path與完整8-row tree rehash；
9. 八列`NotSigned`且沒有其他status；
10. parent proof-file SHA再讀一次，證明validation期間未變。

Identity不同但文件本身未被竄改，回`RUNTIME_RECOVERY_PARENT_INELIGIBLE`；canonical evidence、archive
或runtime bytes被改，回`RUNTIME_EVIDENCE_TAMPERED`。任一失敗都不建立child。

執行Task 2 tests與全部runtime tests；不commit到Tasks 3–6綠燈前。

## Task 3：Recovery child preparation與CLI-free evidence TDD

### 3.1 RED：child creation contract

新增：

```text
test_prepare_recovery_creates_exclusive_ready_child_after_all_checks
test_prepare_recovery_binds_parent_archive_inventory_version_and_mandatory_hashes
test_prepare_recovery_records_full_inventory_and_zero_execution
test_prepare_recovery_never_creates_consumption_record
test_prepare_recovery_preserves_parent_and_runtime_byte_for_byte
test_prepare_recovery_rejects_each_ack_mismatch_before_child_creation
test_prepare_recovery_refuses_existing_child_or_temporary_evidence_collision
test_prepare_recovery_write_failure_never_reuses_partial_child
```

Tests在呼叫前後hash parent proof與所有runtime candidates，並比較directory listing；不以mtime
作判斷，避免read access time造成誤判。

### 3.2 GREEN：child writer

新增recovery-specific helpers，不能把parent `_evidence_path()`誤指向child：

```text
_recovery_evidence_path()
_recovery_consumption_path()
_with_recovery_manifest_hash()
_write_new_recovery_evidence()
_read_recovery_evidence()
```

`prepare_runtime_recovery()`必須先完成Task 2全部validation，再exclusive-create child directory與
`runtime-recovery-proof.json`。Child至少記錄：

- schema、evidence ID、created UTC／Taipei、state／safe code／reason；
- parent directory name、evidence ID、manifest、proof-file hash與eligibility snapshot；
- outer identity；
- inventory hash、完整8 rows、version／mandatory identities；
- fixed runtime root；
- `execution=null`。

寫入後read-back canonical manifest，計算child proof-file SHA並以`RuntimeRecoveryProof`回傳。
任何write failure停止；不刪除、不覆寫或重用partial child directory。

## Task 4：Read-only recovery verifier與tamper matrix TDD

### 4.1 RED：verifier tests

新增：

```text
test_verify_ready_recovery_is_read_only_and_recomputes_complete_binding
test_verify_recovery_rejects_child_manifest_or_file_tampering
test_verify_recovery_rejects_parent_after_child_tampering
test_verify_recovery_rejects_archive_or_runtime_after_child_tampering
test_verify_ready_recovery_rejects_unexpected_consumption_record
test_verify_consumed_recovery_requires_valid_consumption_manifest_and_file_hash
test_verify_recovery_rejects_state_consumption_or_command_contract_mismatch
test_verify_recovery_validates_bounded_command_output_and_fixed_order
```

Read-only test保存parent、child、consumption（若有）與runtime files的bytes／SHA和directory listing；
verify後全部相同。

### 4.2 GREEN：state-aware verifier

`verify_runtime_recovery()`固定重驗：

- child schema／manifest／evidence ID；
- pinned parent與parent proof-file hash；
- archive與runtime inventory；
- `RECOVERY_READY`時consumption不存在且execution是null；
- consumed states時consumption存在、schema／manifest有效，且child authorization保存其file hash；
- command只能是version後help，argv／cwd／timeout／stdin／shell／bounded output都符合既有contract；
- `PASSED`無safe code且兩個commands完整；
- `FAILED`有safe code；
- `RECOVERY_EXECUTING`回exit30且不被當成可續跑。

Verifier永遠不repair、replace、finalize、create consumption或執行probe／runner。

## Task 5：Single-use resume、command journal與postflight TDD

### 5.1 RED：consume boundary

新增：

```text
test_resume_authenticates_child_before_any_write_probe_or_runner
test_resume_refuses_nonready_or_consumed_child_without_replay
test_resume_exclusive_consumption_record_binds_preconsume_child_hashes
test_resume_consumes_child_before_parent_runtime_or_process_preflight
test_resume_ack_or_parent_mismatch_after_consume_fails_with_empty_commands
test_resume_consumption_or_state_write_failure_never_executes_binary
test_resume_preserves_parent_and_never_moves_copies_extracts_or_promotes_runtime
```

Wrong child evidence ID／manifest／proof-file hash不得寫任何檔案。正確child identity後才可建立一次
consumption；之後即使parent ack錯，也必須terminal fail且不能replay。

### 5.2 RED：command與journal contract

新增：

```text
test_resume_runs_fixed_version_then_help_once_with_closed_process_contract
test_resume_persists_version_evidence_before_starting_help
test_resume_persists_help_evidence_before_postflight
test_resume_uses_child_only_path_delta_and_preserves_parent_environment
test_resume_rejects_model_text_reference_output_server_port_or_unknown_args
test_resume_fails_timeout_launch_nonzero_or_help_contract_without_retry
test_resume_fails_new_process_listener_event_or_unknown_postflight
test_resume_fails_runtime_inventory_change_after_commands
test_resume_passes_only_after_two_commands_clean_postflight_and_final_verify
```

Runner與probes全部injected。Tests檢查call order，runner永遠只收到：

```text
runtime_dir\bin\sherpa-onnx-version.exe
runtime_dir\bin\sherpa-onnx-offline-tts.exe --help
```

### 5.3 GREEN：exclusive consume與progressive journal

`resume_runtime_proof()`順序固定：

1. path boundary；
2. child current file hash／manifest／evidence ID對使用者ack；
3. state是`RECOVERY_READY`且consumption不存在；
4. exclusive-create canonical consumption；
5. replace child為`RECOVERY_EXECUTING`並保存全部acks與consumption file hash；
6. read-back consumption與executing child；
7. 重驗parent identity、其餘acks、runtime path與inventory；
8. process／listener preflight；
9. version command一次；完成後立即replace／read-back command evidence；
10. help command一次；完成後立即replace／read-back command evidence；
11. process／listener／Event 1000 postflight及inventory rehash；
12. replace terminal `PASSED`或`FAILED`；
13. 呼叫read-only verifier。

Recovery-specific writer先flush並`os.fsync()`，再使用同directory exclusive `.tmp`與same-volume
replace；consumption exclusive file也要flush／fsync後read-back。`.tmp`已存在、write／replace／
read-back失敗都exit30；不清理或重用tmp。Consumption一旦存在就是authoritative used marker。

每個command使用argument list、`shell=False`、`stdin=DEVNULL`、fixed cwd、30秒timeout、
capture output，PATH只在child environment前置fixed runtime `bin`與`lib`。沿用64 KiB bounded
output evidence；help仍要求既有七個tokens。

任何failure不啟動下一個command、不retry、不直接呼叫EXE、不修改parent。

## Task 6：CLI dispatch、完整離線驗證、scope proof與code commits

### 6.1 RED／GREEN：CLI integration

新增：

```text
test_prepare_recovery_cli_requires_all_paths_and_literal_acks
test_verify_recovery_cli_is_read_only_and_bounded
test_resume_recovery_cli_requires_one_time_ack_and_all_exact_hashes
test_recovery_cli_rejects_model_reference_text_output_and_unknown_options
test_main_dispatch_never_routes_recovery_commands_to_parent_verifier
test_recovery_cli_stdout_is_bounded_and_omits_private_paths_and_command_output
```

`_build_parser()`新增§3.4三個commands。`main()`使用三個explicit branches；不能用現有final
catch-all把新command誤送到`verify_runtime_proof()`。

新增`_recovery_cli_summary()`，輸出不超過2 KiB。`RECOVERY_READY` next step固定
`stop-and-request-d2-ur-x`；其他states固定`stop`。

### 6.2 Focused與完整驗證

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\voice_pilot\test_runtime_proof.py -q
.\.venv\Scripts\python.exe -X utf8 -m pytest
.\.venv\Scripts\python.exe -X utf8 -m compileall -q `
  scripts\voice_pilot tests\unit\voice_pilot
git diff --check
```

要求全部exit `0`。不得新增skip、刪test或放寬既有assertions。

### 6.3 Static scope proof

```powershell
git diff --name-only $d2urBaseline
git diff --exit-code $d2urBaseline -- `
  scripts\voice_pilot\pilot.py `
  scripts\voice_pilot\synthesize_yating_baseline.py `
  src\travel_briefing `
  tests\unit\travel_briefing `
  pyproject.toml `
  uv.lock
rg -n "requests|httpx|urllib\.request|socket|websocket|extractall\(|\.extract\(" `
  scripts\voice_pilot\runtime_proof.py
rg -n "model|reference-audio|reference-text|output-filename|server|port" `
  scripts\voice_pilot\runtime_proof.py
git status --short
```

第一個name list只能含兩個核准code files。Protected diff必須0。Network／unsafe extraction scan
要求0 matches；`rg`因此可用exit `1`表示沒有命中，不能誤判為驗證失敗。第二個scan可以命中
既有required help tokens與explicit reject tests，但不得出現新的CLI option或execution
argument，必須人工逐列說明。

### 6.4 Code commits與real-probe前狀態

Task 1驗證後建立第一個commit。Tasks 2–6全部完成後再跑一次§6.2／§6.3，建立第二個commit。

第二個commit後要求：

- working tree乾淨；
- source相對第二個commit 0 diff；
- SmartSub／sherpa version／sherpa offline-tts／WINWORD process都是0；
- 尚未讀production parent／archive／runtime；
- 尚未建立real child或執行real PowerShell probes；
- 尚未執行任何sherpa binary。

## Task 7：Gate D2-UR-I 唯讀real probes與actual child preparation

本Task仍屬D2-UR-I，但必須等Tasks 1–6 code commits、完整suite與scope proof全部完成才執行。

### 7.1 Fixed paths與preflight

```powershell
$d2urParent = 'C:\Users\cance\AppData\Local\EasyTravelVoicePilot\proofs\runtime-v1.13.6-20260820T014555Z-b6b2c9b9'
$d2urRuntime = 'C:\Users\cance\AppData\Local\EasyTravelVoicePilot\runtime\sherpa-onnx\1.13.6'
$d2urArchive = 'C:\Users\cance\AppData\Local\EasyTravelVoicePilot\downloads\sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2'
$d2urProofs = 'C:\Users\cance\AppData\Local\EasyTravelVoicePilot\proofs'
$d2urRunId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$d2urChild = Join-Path $d2urProofs "runtime-recovery-v1.13.6-$d2urRunId"
```

只讀檢查：

- parent／archive／runtime存在；
- child不存在；
- parent `runtime-proof.json` SHA等於固定proof-file hash；
- parent／runtime／proofs roots無reparse；
- code working tree乾淨且HEAD是第二個code commit；
- protected code相對第二個code commit 0 diff；
- 四類process是0。

任一不符停止，不建立child、不執行probe或binary。

### 7.2 一組real Windows probe validation

只執行process、listener、Event三個production probe各一次。Operator用既有Python直接import
fixed private probe functions，stdout只列JSON type與row count，不列process、listener或Event
明細：

```powershell
$d2urProbeCode = @'
import json
from datetime import datetime, timedelta, timezone
from scripts.voice_pilot.runtime_proof import (
    _default_event_probe,
    _default_listener_probe,
    _default_process_probe,
)
now = datetime.now(timezone.utc)
rows = {
    "process": _default_process_probe(),
    "listener": _default_listener_probe(),
    "event": _default_event_probe(
        (now - timedelta(seconds=2)).isoformat(), now.isoformat()
    ),
}
assert all(isinstance(value, list) for value in rows.values())
print(json.dumps({
    name: {"json_type": "array", "rows": len(value)}
    for name, value in rows.items()
}, sort_keys=True, separators=(",", ":")))
'@
.\.venv\Scripts\python.exe -X utf8 -c $d2urProbeCode
```

要求exit `0`且三項`json_type`都是`array`。不啟動程序或listener來製造特定row count。若失敗，
停止並回報；本Gate不重跑real probe set。

### 7.3 建立actual child一次

只執行一次：

```powershell
.\.venv\Scripts\python.exe -X utf8 `
  .\scripts\voice_pilot\runtime_proof.py prepare-runtime-recovery `
  --parent-proof-dir $d2urParent `
  --recovery-proof-dir $d2urChild `
  --ack-parent-evidence-id 'a3ba6b11-5b57-46db-b5e7-113c36e9d964' `
  --ack-parent-manifest-sha256 'e841a4f6ee1aa24bb7bd78c8b57ac88336f84512b175bbd44066f099829d2123' `
  --ack-parent-proof-file-sha256 '3e4e1fdec33d11e60096a58e8b35f12766ffeeab620582961634af27c49f06e9' `
  --ack-outer-sha256 '4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613' `
  --ack-load-inventory-sha256 'd3d440c0345eee6e6dae680c07036c830896b5bbfc98f4774f83b243cc05786f' `
  --ack-executable-sha256 'a62495554c6953d523626cfba0944be353857c9840b0e513170d45ba0e76a9f0'
```

要求exit `0`、state `RECOVERY_READY`、safe code null、parent／outer／inventory／version／mandatory
identities全部符合，且CLI輸出不含private paths。

這個command只讀parent、archive與runtime bytes／hash，從immutable parent繼承已綁定的8-row
signature metadata，並寫一個新child。它不重跑Authenticode、不move／copy／extract runtime、
不建立consumption、不執行EXE。

若command非零，不重送、不換child path、不清理partial artifact，立即停止並記錄exact safe
code與現存paths。

### 7.4 Read-only child verification與postflight

只執行一次：

```powershell
.\.venv\Scripts\python.exe -X utf8 `
  .\scripts\voice_pilot\runtime_proof.py `
  verify-runtime-recovery $d2urChild
```

要求exit `0`、state `RECOVERY_READY`。接著只讀證明：

- child `runtime-recovery-proof.json` manifest與proof-file SHA；
- child evidence ID；
- `runtime-recovery-consumption.json`不存在；
- parent proof-file hash仍為固定值；
- runtime inventory仍為固定hash且8 rows相符；
- parent、runtime與archive沒有move／copy／delete；
- SmartSub／sherpa version／sherpa offline-tts／WINWORD process都是0；
- repository沒有private evidence或未核准檔案。

### 7.5 Handoff與docs commit

在本計畫新增actual evidence section，並更新`STATUS.md`。必須列出：

- baseline、兩個code commits、docs commit前HEAD與working tree；
- baseline／focused／full suite／compile／scope proof關鍵原文；
- real process／listener／Event probe的row counts與JSON types；
- parent、outer、inventory、version、mandatory identities；
- child resolved directory、evidence ID、manifest、proof-file SHA與state；
- consumption不存在；
- parent hash與process before／after；
- 沒有執行binary、model、media、synthesis、login、upload、cleanup、retry或push；
- 使用所有actual values完整生成的D2-UR-X approval sentence。

建立第三個docs commit後停止，不push、不進Task 8。

## Task 8：未授權 Gate D2-UR-X single-use version/help runbook

本Task不屬於D2-UR-I。只有Task 7 handoff完成、使用者逐值核准parent、child、runtime與Git
identities後才可執行。

### 8.1 Handoff必須先產生的literal approval

完整approval sentence必須包含：

- approved final handoff HEAD與implementation code commit；
- parent evidence ID、manifest、proof-file SHA；
- child directory、evidence ID、manifest、pre-consume proof-file SHA；
- outer、inventory、version、mandatory executable SHA；
- literal `--ack-runtime-recovery-once`；
- 只允許一個preflight read-only verifier、version一次、help一次，以及resume內一個terminal
  read-only verifier；
- no retry、no model／media／synthesis／login／upload／push。

不得留下變數、空白欄位或泛稱「上述hash」。

### 8.2 D2-UR-X preflight

另行核准後才：

1. `git pull --ff-only`；
2. HEAD必須等於核准的final handoff commit；
3. `runtime_proof.py`與test file相對implementation commit 0 diff；
4. working tree乾淨；
5. parent與child current proof-file hashes逐值相符；
6. child是`RECOVERY_READY`且consumption不存在；
7. `verify-runtime-recovery`唯讀通過；
8. 四類process是0；
9. runtime path與all 8 inventory rows相符。

任一不符就不呼叫resume。

### 8.3 唯一execution invocation

Operator從Task 7 handoff的literal values建立完整`resume-runtime-proof`command，包含§3.4全部
acks。只呼叫一次，不用shell字串、不加其他argument。

Command內部先authenticate／consume child，再依序執行：

1. `sherpa-onnx-version.exe`一次；
2. `sherpa-onnx-offline-tts.exe --help`一次；
3. fixed postflight與inventory rehash；
4. terminal evidence；
5. read-only verifier一次。

若exit非0、child是`RECOVERY_EXECUTING`／`FAILED`、command evidence不完整或postflight dirty，
立即停止。不得重跑resume、直接手動執行EXE、修改child、刪consumption或建立第二份child來
繞過結果。

### 8.4 D2-UR-X stop

更新STATUS與本計畫actual evidence，建立本機docs commit後停止。即使`PASSED`，下一步也只能
提出新的model-load設計；不得直接讀取ZipVoice model、本人影片／音訊或合成聲音。

## 9. Gate D2-UR-I 完成條件

Tasks 1–7完成必須同時證明：

1. baseline、focused與完整離線suite都綠；
2. compileall與`git diff --check` exit 0；
3. 沒有新增dependency、network、unsafe extraction或arbitrary command seam；
4. protected files 0 diff；
5. 三個production probes各實際唯讀執行一次並輸出JSON array；
6. pinned parent proof-file、manifest、evidence ID與eligibility全部相符；
7. archive與runtime完整inventory read-only驗證；
8. 一份且只有一份actual child是`RECOVERY_READY`；
9. child consumption不存在；
10. parent proof與runtime byte-for-byte未改；
11. sherpa commands執行數0；
12. SmartSub／sherpa／WINWORD before-after都是0；
13. private evidence沒有進Git；
14. 三個local commits存在且working tree乾淨；
15. 沒有model、personal media、reference、synthesis、login、upload、cleanup、retry或push；
16. STATUS提供完整literal D2-UR-X approval sentence。

任何一項未達成都不能宣稱D2-UR-I完成，也不能提請D2-UR-X執行。

## 10. 本計畫的下一個核准句

只有使用者逐字核准下列句子，才授權Tasks 1–7：

> 核准 Gate D2-UR-I：只依 `docs/plans/2026-08-20-sherpa-runtime-recovery-implementation-plan.md` 執行 Tasks 1–7；固定 parent evidence ID `a3ba6b11-5b57-46db-b5e7-113c36e9d964`、manifest SHA-256 `e841a4f6ee1aa24bb7bd78c8b57ac88336f84512b175bbd44066f099829d2123`、proof-file SHA-256 `3e4e1fdec33d11e60096a58e8b35f12766ffeeab620582961634af27c49f06e9`，以及 outer／inventory／version／mandatory SHA-256 `4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613`／`d3d440c0345eee6e6dae680c07036c830896b5bbfc98f4774f83b243cc05786f`／`7cb2de6405de878417635845278b1be01413650b36e64c30df5314128f109869`／`a62495554c6953d523626cfba0944be353857c9840b0e513170d45ba0e76a9f0`；允許修改固定兩個 code files、執行 synthetic/focused/full tests、compile/scope proof、一組三個唯讀 Windows real probes，唯讀重驗固定 parent／archive／已 promoted runtime，建立並唯讀驗證一份全新 per-user `RECOVERY_READY` child proof，完成local commits與STATUS handoff後停止；不執行任何 sherpa／SmartSub／Yating binary、不建立consumption、不下載、不解壓、不讀model或本人素材、不合成、不登入、不上傳、不清理per-user產物、不重試real probe set或actual child command、不推送；Task 8仍未授權。

只核准本計畫內容或回覆一般「同意」都不授權D2-UR-I；必須逐字確認上面的完整Gate。
