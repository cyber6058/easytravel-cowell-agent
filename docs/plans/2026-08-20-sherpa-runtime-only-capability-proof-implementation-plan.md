# sherpa-onnx Windows runtime-only capability proof 實作計畫

日期：2026-08-20

依據：
`docs/specs/2026-08-20-sherpa-runtime-only-capability-proof-design.md`

設計基線 commit：
`2c1592180fc932ef2bc055c1b4459a039f33e292`

狀態：書面設計已核准；本實作計畫等待使用者審閱。本文件只規劃工作，不授權寫程式、
測試、下載、解壓、執行 runtime、讀取 model／本人素材、合成、登入、上傳或 push。

## 0. 目的、結果與停止範圍

本計畫以最小、可重驗的方式回答：

> 官方 sherpa-onnx v1.13.6 Windows x64 CPU runtime 能否在本機 Windows 11 25H2
> 完成 `sherpa-onnx-offline-tts.exe --help` 級啟動並正常結束？

Tasks 1–5 是 Gate D2-I，只建立 synthetic-only 離線安全骨架。Task 6 是未來 Gate D2-X，
Task 7 是只有發現 `NotSigned` 時才可能出現的 Gate D2-U。任何前一關通過都不自動授權
下一關。

即使 Tasks 1–7 全部通過，也只能宣稱 sherpa-onnx runtime 可啟動，不能宣稱：

- ZipVoice model 可載入或在 8 GB RAM 內可用；
- 推論速度、本人相似度、自然度、A 問題或 B 問題已通過；
- Emilia-linked model 有 EasyTravel 商用權利；
- 可取代 Yating、交付旅客或整合正式 briefing workflow。

本計畫不包含 model archive listing／extraction、vocoder、reference audio／text、TTS text、
output WAV、影片、Yating、SmartSub、ASR、CUDA、Vulkan、pip/npm package、source build、
cloud、login、upload、LINE、Cowell、deployment、cleanup 或 push。

## 1. 固定資產與環境

唯一允許的真實資產固定為：

| 欄位 | 固定值 |
|---|---|
| release | `v1.13.6` |
| asset | `sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2` |
| URL | `https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.6/sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2` |
| bytes | `24,497,928` |
| SHA-256 | `4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613` |
| expected root | `sherpa-onnx-v1.13.6-win-x64-shared-MT-Release` |

D2-I 不下載或讀取這個 asset；tests 使用自行建立的小型 synthetic `.tar.bz2` 與
test-specific `RuntimeAssetSpec`。

專案現有環境為 Python `>=3.12`、pytest，且 `scripts/voice_pilot/__init__.py` 已存在。
實作只使用 Python standard library；不得新增 dependency、修改 `pyproject.toml` 或建立
新的 package entrypoint。

## 2. 允許檔案、嚴格 unchanged controls 與 commit map

### Gate D2-I 允許新增或更新

- `scripts/voice_pilot/runtime_proof.py`；
- `tests/unit/voice_pilot/test_runtime_proof.py`；
- 本計畫的 actual evidence section；
- `STATUS.md`。

不修改 `scripts/voice_pilot/pilot.py`、`scripts/voice_pilot/__init__.py` 或 `.gitignore`。
真實 runtime path 一律在 repository 外，因此不以新 ignore rule 取代 path validation。

### 嚴格 0 diff

- `src/travel_briefing/`；
- `tests/unit/travel_briefing/`；
- `scripts/voice_pilot/pilot.py`；
- `scripts/voice_pilot/synthesize_yating_baseline.py`；
- 正式 CLI、Skill、plugin、config、schemas、package version與 dependencies；
- private LIST master、calibration、既有 DRAFT／briefing artifacts；
- Cowell、NewAmazing、JMA、Word、LINE、Cloudflare 與 deployment files。

### 未來 implementation commits

1. `feat(voice-pilot): add sherpa runtime safety harness`
   - 只含新 module 與新 tests；
   - 必須在完整離線驗證通過後建立。
2. `docs: record Gate D2-I offline handoff`
   - 只含本計畫 actual evidence 與 `STATUS.md`；
   - 不含 runtime、archive、EXE／DLL、proof evidence 或其他產物。

兩個 commits 只留本機，不 push。計畫核准不自動授權建立這兩個 commits；它們屬於
後續 Gate D2-I execution。

## 3. 公開 seam、資料模型與 safe codes

### Module public seam

`scripts/voice_pilot/runtime_proof.py` 提供下列 dataclasses：

```text
RuntimeAssetSpec
VerifiedArchive
ArchiveMemberPlan
ArchivePlan
SignatureRecord
LoadInventory
RuntimePreparation
RuntimeProof
```

可 import 的主要函式固定為：

```text
verify_archive_identity(archive_path, *, spec) -> VerifiedArchive
build_archive_plan(archive_path, *, verified, expected_root) -> ArchivePlan
validate_runtime_paths(repo_root, per_user_root, archive_path, staging_dir, runtime_dir, proof_dir)
safe_extract_runtime(archive_path, *, plan, staging_dir) -> Path
build_load_inventory(staging_dir, *, signature_probe) -> LoadInventory
prepare_runtime(archive_path, *, spec, staging_dir, runtime_dir, proof_dir, signature_probe)
run_runtime_proof(proof_dir, *, runner, process_probe, listener_probe, event_probe)
verify_runtime_proof(proof_dir) -> RuntimeProof
```

`signature_probe`、`runner`、process／listener／event probes 在 tests 一律 injection；不得
在 synthetic tests 中執行 PowerShell signature probe 或第三方 EXE。

### CLI seam

```text
prepare-runtime --archive PATH --staging-dir DIR --runtime-dir DIR --proof-dir DIR
prove-runtime --proof-dir DIR --runtime-dir DIR --ack-valid-signed-runtime
prove-runtime --proof-dir DIR --runtime-dir DIR --ack-not-signed-runtime-once \
  --ack-outer-sha256 HASH --ack-load-inventory-sha256 HASH \
  --ack-executable-sha256 HASH
verify-runtime-proof PROOF_DIR
```

CLI 沒有 download、model、reference、text、output、server、port、admin 或 fallback option。
Production default 永遠使用 pinned `RuntimeAssetSpec` 與 fixed per-user root；只有 Python
function tests可注入 synthetic spec／temporary roots。

### CLI exit contract

| exit | 意義 |
|---:|---|
| `0` | `READY_TO_EXECUTE`、`PASSED` 或獨立 verification 通過 |
| `20` | 預期安全停止 `BLOCKED_UNSIGNED`；未執行第三方 binary |
| `30` | contract、identity、archive、signature、execution 或 evidence failure |

CLI stdout 只輸出 bounded JSON：state、safe code、outer／inventory／mandatory executable
hash、evidence ID與下一步。不得輸出完整 home listing、model／media path、token、私人文字或
third-party stdout全文。

### Safe codes

```text
RUNTIME_ASSET_SIZE_MISMATCH
RUNTIME_ASSET_SHA256_MISMATCH
RUNTIME_PATH_OUTSIDE_PER_USER_ROOT
RUNTIME_PATH_INSIDE_REPOSITORY
RUNTIME_OUTPUT_EXISTS
RUNTIME_ARCHIVE_UNSAFE_MEMBER
RUNTIME_ARCHIVE_LIMIT_EXCEEDED
RUNTIME_ARCHIVE_ROOT_MISMATCH
RUNTIME_EXTRACTION_FAILED
RUNTIME_EXECUTABLE_MISSING
RUNTIME_EXECUTABLE_AMBIGUOUS
RUNTIME_SIGNATURE_NOT_SIGNED
RUNTIME_SIGNATURE_INVALID
RUNTIME_ACK_MISMATCH
RUNTIME_HELP_TIMEOUT
RUNTIME_HELP_NONZERO
RUNTIME_HELP_CONTRACT_MISMATCH
RUNTIME_POSTFLIGHT_DIRTY
RUNTIME_EVIDENCE_TAMPERED
```

Safe code 必須穩定、無 path／exception text及不超過 80 characters。詳細診斷只進 private
proof evidence；同一 failure 不自動 retry。

## Task 1：Gate D2-I preflight、asset identity 與 path contract TDD

### Preflight

開始 future implementation 前執行：

```powershell
git status --short --branch
git pull --ff-only
$d2Baseline = git rev-parse HEAD
(Get-Process SmartSub -ErrorAction SilentlyContinue | Measure-Object).Count
(Get-Process sherpa-onnx-offline-tts -ErrorAction SilentlyContinue | Measure-Object).Count
(Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count
```

要求 working tree乾淨、pull為 `Already up to date.`、三類 process均為 0。未知變更或程序
不覆蓋、不終止，先停止。記錄 `$d2Baseline`，後續所有 scope proof以此 commit為準。

### Tests 先紅

在新 test file 建立：

```text
test_pinned_runtime_asset_matches_approved_contract
test_verify_archive_identity_accepts_exact_synthetic_spec
test_verify_archive_identity_rejects_size_or_sha256_mismatch
test_runtime_paths_reject_repo_relative_outside_root_existing_and_reparse_targets
test_runtime_paths_accept_only_new_siblings_under_fixed_per_user_root
test_runtime_cli_has_no_download_model_text_reference_or_output_options
```

Test fixture archive 只含數十 bytes 的 synthetic regular file。先執行 focused tests並看到
因缺少 module／public seam而 red；不得用 skip、xfail、弱化 assertion 或先建立 production
stub讓測試假綠。

### 最小 green

建立 pinned constants、dataclasses、chunked SHA-256、`resolve(strict=False)` 加上 parent
containment／reparse-point checks、new-output contract及 CLI parser。Production fixed roots為：

```text
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\downloads
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\runtime-staging
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\runtime\sherpa-onnx\1.13.6
C:\Users\cance\AppData\Local\EasyTravelVoicePilot\proofs
```

Module import及 parser construction不得建立任何目錄或讀取 per-user files。

### Task 1 focused verification

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\voice_pilot\test_runtime_proof.py -q
```

要求新 tests全綠，沒有 runtime／SmartSub／WINWORD process變化，Git中只有核准的新 module
與 test file。

## Task 2：Archive plan 與 no-`extractall` safe extraction TDD

### Tests 先紅

新增 parameterized cases：

```text
test_archive_plan_accepts_one_expected_root_with_regular_files_and_directories
test_archive_plan_rejects_absolute_drive_unc_parent_ads_device_and_trailing_names
test_archive_plan_rejects_symlink_hardlink_special_and_unknown_members
test_archive_plan_rejects_duplicate_casefold_and_file_directory_prefix_collisions
test_archive_plan_rejects_wrong_or_multiple_roots_and_entry_or_size_limits
test_safe_extract_writes_only_planned_regular_files_without_extractall
test_safe_extract_refuses_existing_target_and_reparse_escape
test_safe_extract_preserves_incomplete_staging_and_never_promotes_on_failure
```

Fixtures必須包含 Windows slash／backslash、casefold及 reserved-name edge cases。用 monkeypatch
使 `TarFile.extractall`／`extract` 一被呼叫就 failure，直接證明 production path沒有使用它們。

### 最小 green

`build_archive_plan` 在任何 output write前完整列出 members，normalize為 POSIX relative
components，再檢查：

- 唯一 fixed top-level root；
- regular file／directory only；
- entries `<= 20,000`；
- single file `<= 1 GiB`；
- total uncompressed bytes `<= 2 GiB`；
- no absolute／drive／UNC／`..`／ADS／device／trailing dot-space；
- no duplicate、casefold、file-prefix collision。

`safe_extract_runtime` 依 immutable plan逐檔以 binary stream寫入全新 staging；每次 mkdir／
open前後都重新確認 resolved path仍在 staging且 ancestor不是 reparse point。任一 mismatch
保留 incomplete staging、寫 failure evidence，不建立或覆蓋 final runtime。

### Task 2 focused verification

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\voice_pilot\test_runtime_proof.py -q
```

額外 source assertion必須證明 `runtime_proof.py` 沒有 `.extractall(` 或 `.extract(`。

## Task 3：Load inventory、Authenticode policy 與 promotion stop TDD

### Tests 先紅

新增：

```text
test_load_inventory_includes_allowlisted_executable_and_every_dll_in_canonical_order
test_load_inventory_hash_is_stable_and_changes_on_path_bytes_hash_or_signature_change
test_prepare_runtime_returns_ready_only_when_every_load_candidate_is_valid
test_prepare_runtime_stops_unsigned_before_promotion_or_execution
test_prepare_runtime_blocks_invalid_untrusted_unknown_and_mixed_signature_states
test_prepare_runtime_rejects_missing_duplicate_or_reparsed_mandatory_executable
test_unsigned_ack_must_match_outer_inventory_executable_hashes_and_literal
```

Signature fixtures使用 injected structured records，覆蓋 `Valid`、`NotSigned`、
`HashMismatch`、`NotTrusted`與`UnknownError`。不簽 synthetic binary、不讀 Windows system
binary，也不執行 PowerShell。

### 最小 green

Load candidate固定為：

- 唯一 `sherpa-onnx-offline-tts.exe`；
- 若唯一存在則加入 `sherpa-onnx-version.exe`；
- extracted tree內每個 `.dll`。

Canonical inventory rows包含 normalized relative path、bytes、SHA-256及完整 signature fields；
依 normalized path排序，以 UTF-8 canonical JSON計算 inventory SHA-256。

Production signature probe未來以 `powershell -NoProfile -NonInteractive`、`-LiteralPath`及
structured JSON output呼叫 `Get-AuthenticodeSignature`。動態 path不得拼成可執行 script；
tests只驗證 adapter command builder／JSON parser，不實際執行 PowerShell。

決策固定為：

- all load candidates `Valid` -> `READY_TO_EXECUTE`；
- any `NotSigned`且沒有其他錯誤 -> `BLOCKED_UNSIGNED`、exit `20`；
- any other status／probe ambiguity -> `FAILED`、exit `30`。

`prepare-runtime` 在 staging完成 inventory。只有 all-valid或未來 exact D2-U ack通過時才能
atomic promote至全新 final runtime；unsigned／invalid狀態不 promote、不執行、不清理。

## Task 4：Bounded proof runner、evidence 與 tamper verification TDD

### Tests 先紅

新增：

```text
test_proof_runner_uses_shell_false_closed_stdin_fixed_cwd_and_child_only_path
test_proof_runner_allows_only_offline_tts_help_and_optional_version_utility
test_proof_runner_rejects_model_text_reference_output_server_port_and_unknown_args
test_proof_runner_requires_ready_state_or_exact_unsigned_ack_before_promotion
test_proof_runner_fails_timeout_nonzero_crash_or_missing_help_tokens_without_retry
test_proof_runner_fails_new_process_listener_or_event_1000_postflight
test_proof_evidence_records_bounded_output_hashes_timing_inventory_and_os_facts
test_proof_evidence_omits_private_content_and_unnecessary_absolute_paths
test_verify_runtime_proof_detects_archive_inventory_runtime_output_or_manifest_tampering
test_cli_stdout_is_bounded_json_and_never_contains_third_party_output
```

Injected runner回傳固定 fake argv、stdout、stderr、exit、duration；process／listener／event
probes使用 deterministic before-after fixtures。不得以 `subprocess` 執行 shell、PowerShell或
fake EXE取得測試綠燈。

### 最小 green

Mandatory command固定為：

```text
sherpa-onnx-offline-tts.exe --help
```

若 inventory內唯一存在 `sherpa-onnx-version.exe`，可先無參數執行；不存在時明確記錄
`version_utility = not_present`，不得猜測 `--version`。

Third-party runner固定：argument list、`shell=False`、stdin `DEVNULL`、cwd為 executable
directory、timeout `30` seconds、binary output capture。Child environment只可在該 process
prepend extracted `bin`／`lib`；不改 system／user PATH。

Help output可在 stdout或stderr，但 exit必須為 `0`，且 normalized bounded output包含：

```text
provider
num-threads
zipvoice-encoder
zipvoice-decoder
reference-audio
reference-text
output-filename
```

Runner不接受由 caller提供任意 argv。Timeout、nonzero、exception、missing token、Event 1000、
new residual process／listener或probe unknown都 fail closed；每個 command最多執行一次。

Evidence schema至少記錄設計要求的 system／asset／archive／inventory／signature／command／
timing／output hashes／postflight／state／failure code。Captured output最多保留每個 stream
64 KiB；完整 bytes count與SHA-256仍記錄。Manifest以 canonical JSON自我 hash，
`verify-runtime-proof`重算所有可重驗 hashes與state contract。

### D2-I CLI tests

CLI tests只對 synthetic archive及 injected adapters直接呼叫 `main(argv, adapters=...)`。
Production `main()`不得提供公開 injection flags；tests透過 Python seam注入。

## Task 5：Gate D2-I 完整離線驗證、local commits 與停止

### Focused tests

```powershell
$smartSubBefore = (Get-Process SmartSub -ErrorAction SilentlyContinue | Measure-Object).Count
$sherpaBefore = (Get-Process sherpa-onnx-offline-tts -ErrorAction SilentlyContinue | Measure-Object).Count
$winwordBefore = (Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count

.\.venv\Scripts\python.exe -X utf8 -m pytest `
  tests\unit\voice_pilot\test_runtime_proof.py -q
```

記錄實際 test count及duration，不預填數字。

### Static scope proof

```powershell
git diff --name-only $d2Baseline
git diff --exit-code $d2Baseline -- `
  src `
  tests\unit\travel_briefing `
  scripts\voice_pilot\pilot.py `
  scripts\voice_pilot\synthesize_yating_baseline.py `
  pyproject.toml

rg -n "^\s*(import|from)\s+(urllib|requests|httpx|socket|aiohttp|ftplib)" `
  scripts\voice_pilot\runtime_proof.py `
  tests\unit\voice_pilot\test_runtime_proof.py

rg -n "extractall\(|\.extract\(" scripts\voice_pilot\runtime_proof.py
```

兩個 `rg` commands必須 0 match。Source URL只可出現在 pinned asset constant；不得存在
mirror、model、cloud、upload或business integration。

### Complete suite 與 compile

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest
$suiteExit = $LASTEXITCODE

.\.venv\Scripts\python.exe -X utf8 -m compileall -q `
  scripts\voice_pilot `
  tests\unit\voice_pilot
$compileExit = $LASTEXITCODE

$smartSubAfter = (Get-Process SmartSub -ErrorAction SilentlyContinue | Measure-Object).Count
$sherpaAfter = (Get-Process sherpa-onnx-offline-tts -ErrorAction SilentlyContinue | Measure-Object).Count
$winwordAfter = (Get-Process WINWORD -ErrorAction SilentlyContinue | Measure-Object).Count

git diff --check
git status --short --branch
```

完成條件：suite／compile exit均 `0`；三類 process before-after均 `0`；scope proof及
`git diff --check`通過；working tree只含核准 files；沒有真實 archive、runtime、EXE／DLL、
proof evidence、model或私人素材進 Git。

### D2-I commits 與 handoff

依第 2 節建立兩個 local commits，更新本計畫 actual evidence與`STATUS.md`，記錄：baseline、
test count／duration、suite count／duration、compile、scope proof、process counts、commit SHA、
未驗證項目與下一個 exact gate。完成後停止；不得因 tests green進入 Task 6。

### Gate D2-I actual evidence（2026-08-20）

- 使用者只核准 Tasks 1–5 的 synthetic-only 離線安全骨架。開工
  `git pull --ff-only` 為 `Already up to date.`，D2-I baseline 為
  `fef433dfcac57100a4c7947486a70b4e8fad817a`；SmartSub、
  `sherpa-onnx-offline-tts`、WINWORD 前檢均為 `0`。
- 依 TDD 完成 pinned asset／fixed path、archive plan、manual-stream extraction、canonical
  load inventory、Authenticode policy、signed／unsigned stop、fixed version／help runner、
  bounded evidence、tamper verification與 bounded CLI JSON。最終 focused command 使用單一
  pytest quiet level，實測為 `62 passed in 2.50s`。
- 完整離線 suite 實測為 `676 passed, 8 skipped in 32.46s`，exit `0`；
  `compileall -q scripts\voice_pilot tests\unit\voice_pilot` 無輸出且 exit `0`。
- 相對 baseline 的 `src/`、`tests/unit/travel_briefing/`、既有 voice-pilot scripts及
  `pyproject.toml` 均為 0 diff。新 production module 的 network-client imports為 0，
  `.extractall(`／`.extract(` 呼叫為 0；唯一 URL 是 pinned official GitHub asset。
  `git diff --cached --check` 無輸出且 exit `0`。
- 測試後 SmartSub、`sherpa-onnx-offline-tts`、WINWORD 仍為 `0 / 0 / 0`。Git只納入
  `scripts/voice_pilot/runtime_proof.py` 與
  `tests/unit/voice_pilot/test_runtime_proof.py`；implementation commit為
  `eefdf90776428e6eb32ab90c96ef027671f03ce9`。本 handoff 另以 docs-only local commit
  保存，兩個 commits均不 push。
- D2-I 只證明 synthetic safety contract與離線 harness通過；未下載、解壓或讀取真實
  runtime／model，未執行第三方 binary，未讀取本人素材，未啟動 Yating／SmartSub，未合成、
  登入、上傳或 push。因此尚未證明 sherpa runtime存在、可啟動、可載入 ZipVoice model、
  速度合格、聲音自然或可商用。
- 下一步仍是未授權的 Task 6／Gate D2-X。若要繼續，必須另行精確核准 fixed official
  v1.13.6 asset 的單次下載、identity verification、safe prepare及 all-valid help proof；
  D2-I 完成不授權 Task 6或未來 D2-U。

## Task 6：未來 Gate D2-X exact download、prepare 與 all-valid proof

**本計畫目前不授權執行本 Task。** 只有新的 exact D2-X approval後才能進行。

### D2-X preflight

重新確認：

- Git working tree乾淨且pull up to date；
- installed D2-I code hash與計畫 handoff一致；
- SmartSub、sherpa、WINWORD process均為0；
- exact `.partial`、archive、staging、final runtime及proof dir均不存在；
- fixed per-user root解析正確，無reparse escape；
- 同一 volume可用空間至少2 GiB；
- 不讀取或列出既有 model／video／audio directories。

任一不符停止，不刪、不覆蓋、不終止未知程序。

Preflight 產生一個新的 run ID，並把所有 dynamic paths 解析、列印及逐一確認位於核准的
absolute per-user roots；同一 run後續只能使用這組 variables：

```powershell
$d2RunId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '-' + `
  [guid]::NewGuid().ToString('N').Substring(0, 8)
$d2Url = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.6/sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2'
$d2Archive = 'C:\Users\cance\AppData\Local\EasyTravelVoicePilot\downloads\sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2'
$d2Partial = "$d2Archive.partial"
$d2Staging = Join-Path 'C:\Users\cance\AppData\Local\EasyTravelVoicePilot\runtime-staging' $d2RunId
$d2Runtime = 'C:\Users\cance\AppData\Local\EasyTravelVoicePilot\runtime\sherpa-onnx\1.13.6'
$d2Proof = Join-Path 'C:\Users\cance\AppData\Local\EasyTravelVoicePilot\proofs' `
  "runtime-v1.13.6-$d2RunId"
```

這些是execution-time generated values，不是操作者可改成其他root的configuration。

### Single visible download

只對 fixed official URL建立全新 `.partial`。下載 command必須為單次、可見、無mirror／resume／
retry；完成後先以檔案 metadata確認 `24,497,928` bytes，再計算SHA-256。兩者相符才用
`Move-Item -LiteralPath`改為正式 archive filename。

Future operator command固定為：

```powershell
if (Test-Path -LiteralPath $d2Partial) { throw 'RUNTIME_OUTPUT_EXISTS' }
if (Test-Path -LiteralPath $d2Archive) { throw 'RUNTIME_OUTPUT_EXISTS' }

Invoke-WebRequest -UseBasicParsing -MaximumRedirection 10 -ErrorAction Stop `
  -Uri $d2Url -OutFile $d2Partial

$d2PartialItem = Get-Item -LiteralPath $d2Partial
$d2PartialHash = (Get-FileHash -LiteralPath $d2Partial -Algorithm SHA256).Hash.ToLowerInvariant()
if ($d2PartialItem.Length -ne 24497928) { throw 'RUNTIME_ASSET_SIZE_MISMATCH' }
if ($d2PartialHash -ne '4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613') {
  throw 'RUNTIME_ASSET_SHA256_MISMATCH'
}

Move-Item -LiteralPath $d2Partial -Destination $d2Archive
```

Network failure、HTTP failure、partial already exists、size/hash mismatch均停止並保留
`.partial`；不自動重抓、resume、換transport或換來源。

### Prepare

以 production CLI執行一次：

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\voice_pilot\runtime_proof.py `
  prepare-runtime --archive $d2Archive --staging-dir $d2Staging `
  --runtime-dir $d2Runtime --proof-dir $d2Proof
```

CLI須再次驗證 outer identity，再做archive plan、逐檔解壓、inventory及signature probe。

- exit `20`／`BLOCKED_UNSIGNED`：立即停止，不執行任何 EXE，進入未來 Task 7 proposal；
- exit `30`：失敗停止，不 retry；
- exit `0`／`READY_TO_EXECUTE`：只有所有 load candidates `Valid`，可依同一 D2-X approval
  進入下一步。

### All-valid proof

只執行一次：

```powershell
.\.venv\Scripts\python.exe -X utf8 .\scripts\voice_pilot\runtime_proof.py `
  prove-runtime --proof-dir $d2Proof --runtime-dir $d2Runtime `
  --ack-valid-signed-runtime
```

再執行一次 read-only `verify-runtime-proof`。要求 exit `0`、state `PASSED`、help tokens完整、
無Event 1000、無新增殘留process／listener、沒有model request或audio output。任何unknown
result先唯讀檢查同次evidence，不重送。

### D2-X postflight

更新 `STATUS.md` 與本計畫 actual evidence，local docs commit後停止。不得讀model、建立
reference、合成、啟動Yating／SmartSub或提出runtime可商用。Archive、runtime、proof保留
在per-user root，不自動刪除或加入Git。

## Task 7：未來 Gate D2-U exact-hash unsigned execution

**只有 Task 6 實際產生 `BLOCKED_UNSIGNED` 才能提出本 Task，且本計畫目前不授權執行。**

Handoff必須先輸出完整、實際值，不可用泛稱或未填欄位：

- outer archive filename／bytes／SHA-256；
- load-candidate inventory SHA-256；
- mandatory executable relative path／bytes／SHA-256；
- 每個 `NotSigned` EXE／DLL的relative path／bytes／SHA-256；
- 所有非-`NotSigned` signature statuses；
- staging／proof resolved path及未建立final runtime的證據；
- 沒有第三方binary執行的process／Event證據。

使用者另行逐值確認後，operator command必須同時帶：literal
`--ack-not-signed-runtime-once`、actual outer SHA-256、actual inventory SHA-256與actual
mandatory executable SHA-256。任一ack不符，exit `30`且不promote／execute。

Ack全部相符才允許atomic promote並執行與Task 6完全相同的一次version/help proof；不得
增加model、text、reference、output、admin、compatibility mode或其他參數。完成後同樣
verify、postflight、STATUS、local docs commit並停止。

## 4. Gate D2-I 完成條件

Tasks 1–5 完成必須同時證明：

1. pinned runtime contract與production fixed roots不可由CLI覆寫；
2. production module沒有network client或download command；
3. archive identity、unsafe members、collisions及limits均有synthetic tests；
4. extraction不使用`extractall`／`extract`、不覆蓋且不越過staging；
5. signature inventory canonical且所有non-valid states fail closed；
6. unsigned state在promotion／execution前停止並要求三個actual hashes；
7. runner argv固定、`shell=False`、timeout、closed stdin及child-only PATH有tests；
8. model／text／reference／output／server／port options不存在或被拒絕；
9. help tokens、timeout、nonzero、Event 1000及residual process／listener有tests；
10. evidence bounded、去識別、hash-bound且tamper detection通過；
11. focused tests、完整suite、compile及diff實際通過；
12. `src`、既有travel briefing tests、舊voice-pilot scripts及dependencies 0 diff；
13. SmartSub／sherpa／WINWORD before-after皆0；
14. 沒有真實download、archive、EXE／DLL、model、media、audio或proof evidence；
15. local commits建立、working tree乾淨且未push；
16. `STATUS.md`留下exact evidence與下一個Gate D2-X授權邊界。

D2-I green只證明safety harness，不證明runtime存在、簽章狀態或本機可啟動。

## 5. 計畫審閱與下一個精確授權

核准本計畫後仍應只執行Tasks 1–5；Task 6與Task 7各自保留新的exact approval。下一個
精確授權語句為：

```text
核准 Gate D2-I：只依 `docs/plans/2026-08-20-sherpa-runtime-only-capability-proof-implementation-plan.md` 執行 Tasks 1–5，建立 `runtime_proof.py` 與 synthetic-only tests，完成 focused tests、完整離線 suite、scope proof、local commits 與 STATUS handoff 後停止；不下載、不解壓或讀取真實 runtime／model、不執行第三方 binary、不讀取本人素材、不啟動 Yating／SmartSub、不合成、不登入、不上傳、不推送。
```
