# STATUS

## 2026-08-20 sherpa runtime-only Gate D2-U stopped before binary execution

- Current state: the single approved Gate D2-U invocation safely failed with exit `30`, state `FAILED`, and safe code `RUNTIME_POSTFLIGHT_DIRTY` before the runtime command loop. The unsigned runtime was atomically promoted to the fixed final path, but evidence records `commands: []`; neither `sherpa-onnx-version.exe` nor `sherpa-onnx-offline-tts.exe --help` was executed.
- Work completed: clean baseline `a79eeda2310e97853c7da0824b0299cf3215bc41`; `git pull --ff-only` returned `Already up to date.`; protected D2-I code diff was 0. Preflight revalidated the approved outer/inventory/mandatory hashes, all 8 inventory files, 8 `NotSigned` statuses, no final runtime, and 0 related processes. The exact-hash prove command ran once with no retry. Read-only verification reproduced exit `30` and preserved the archive/runtime binding. Final evidence manifest SHA-256 is `e841a4f6ee1aa24bb7bd78c8b57ac88336f84512b175bbd44066f099829d2123`; proof-file SHA-256 is `3e4e1fdec33d11e60096a58e8b35f12766ffeeab620582961634af27c49f06e9`.
- Next step: stop. A new recovery design and approval are required; do not rerun the consumed prove command. The recovery must fix zero-result process-probe serialization and safely resume the already-promoted, hash-bound runtime without repeating promotion or silently treating the failed evidence as fresh. Only after a new bounded proof succeeds may model/reference/synthesis gates be proposed.
- Blockers: the confirmed harness bug is that the real PowerShell process probe emits no JSON when there are zero SmartSub/sherpa processes; its parser therefore fails before any runtime command. Direct diagnosis produced null/0 characters for that probe, while the listener probe succeeded with 43 rows and no error. Current related process count is 0 and relevant Event 1000 count for the invocation window is 0. Runtime startup and help contract remain unverified; no model, personal video/audio, reference, synthesis, Yating/SmartSub, login, upload, cleanup, retry, or push occurred.

## 2026-08-20 sherpa runtime-only Gate D2-X safe-stopped at unsigned runtime

- Current state: Gate D2-X Task 6 is complete and safely stopped at `BLOCKED_UNSIGNED` / exit `20`. The fixed official sherpa-onnx v1.13.6 archive passed exact identity and safe archive inspection, but all `8 / 8` load candidates are `NotSigned`; no sherpa EXE was executed and the final runtime was not created.
- Work completed: `git pull --ff-only` returned `Already up to date.` from clean baseline `d0b219e892ce007964d6b2f182376e66fa749723`; run ID `20260820T014555Z-b6b2c9b9` used one download with no retry. The archive is `24,497,928` bytes with SHA-256 `4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613`; safe inspection found 38 entries and 66,783,620 uncompressed bytes. Inventory SHA-256 is `d3d440c0345eee6e6dae680c07036c830896b5bbfc98f4774f83b243cc05786f`; mandatory `bin/sherpa-onnx-offline-tts.exe` is `2,763,776` bytes with SHA-256 `a62495554c6953d523626cfba0944be353857c9840b0e513170d45ba0e76a9f0`. The read-only verifier reproduced exit `20`; all 8 row bytes/hashes matched. Full actual values are recorded in `docs/plans/2026-08-20-sherpa-runtime-only-capability-proof-implementation-plan.md`.
- Next step: stop. Task 7 / Gate D2-U remains unauthorized. Any unsigned one-time version/help proof requires a new approval that literally binds the actual outer, inventory, and mandatory-executable SHA-256 values above; it still cannot add a model, reference, text, output, compatibility mode, or synthesis.
- Blockers: Authenticode policy prevented the runtime capability proof, so Windows startup, ZipVoice model loading, speed, naturalness, and commercial suitability remain unverified. Postflight retained the archive, staging, and proof; `execution` is null, final runtime is absent, relevant SmartSub/sherpa/WINWORD process counts stayed `0 / 0`, and relevant Application Error Event 1000 count was `0` from `2026-08-20T01:45:55Z` through `2026-08-20T01:56:17Z`. No model or personal media was read, no Yating/SmartSub, synthesis, login, upload, cleanup, or push occurred.

## 2026-08-20 sherpa runtime-only Gate D2-I offline harness completed

- Current state: Gate D2-I Tasks 1–5 are complete and stopped at the approved boundary. The repository now has a synthetic-only sherpa runtime safety harness and tests; this proves the offline contracts, not that the real runtime exists or works.
- Work completed: baseline `fef433dfcac57100a4c7947486a70b4e8fad817a`; focused `62 passed in 2.50s`; full offline suite `676 passed, 8 skipped in 32.46s`; compileall exit `0`; protected briefing/Yating/pilot/dependency paths are 0 diff; network-client imports and unsafe tar extraction calls are 0; SmartSub/sherpa/WINWORD stayed `0 / 0 / 0`. Implementation commit: `eefdf90776428e6eb32ab90c96ef027671f03ce9`. No push occurred.
- Next step: stop. Continuing requires a new exact Gate D2-X approval for the single pinned official sherpa-onnx v1.13.6 runtime download, identity verification, safe prepare, and an all-valid version/help proof. Gate D2-I does not authorize Task 6 or D2-U.
- Blockers: no real runtime or model was downloaded, extracted, read, or executed, so Windows startup, ZipVoice model loading, speed, naturalness, and commercial suitability remain unverified. No personal media, Yating/SmartSub, synthesis, login, upload, or push was used.

## 2026-08-20 sherpa runtime-only Gate D2 implementation plan awaiting review

- Current state: the user approved the written Gate D2 design and authorized only creation of its implementation plan. `docs/plans/2026-08-20-sherpa-runtime-only-capability-proof-implementation-plan.md` now defines seven tasks and is awaiting review; no task has been executed.
- Work completed: `git pull --ff-only` returned `Already up to date.` and the clean design baseline is `2c1592180fc932ef2bc055c1b4459a039f33e292`. The plan fixes three CLI seams (`prepare-runtime`, `prove-runtime`, `verify-runtime-proof`), stable safe codes, four synthetic TDD slices, archive no-`extractall` and path contracts, canonical load-candidate signature inventory, bounded help/version execution, evidence/tamper verification, complete-suite and scope proofs, two local implementation commits, and separately gated D2-X／D2-U runbooks. Tasks 1–5 are D2-I; Tasks 6–7 remain unauthorized. Self-review measured 606 lines, seven tasks, 42 headings, 44 paired Markdown fences, 16 completion checks, zero unresolved placeholders/trailing whitespace, all required hashes/gates present, and `git diff --check` clean.
- Next step: the user reviews and explicitly approves the implementation plan's exact Gate D2-I sentence. Only that future approval authorizes Tasks 1–5 synthetic-only code/tests/local commits; it still will not authorize a true runtime download, extraction, third-party binary execution, model access, personal media, or synthesis.
- Blockers: no runtime package has been downloaded or executed, so signature status and Windows capability remain unknown; model loading, audible quality, and commercial rights are outside D2-I. This turn made documentation-only changes; no code tests were required or run, and no runtime/model file, video/audio, Yating/SmartSub process, synthesis, login, upload, or push occurred.

## 2026-08-20 sherpa runtime-only Gate D2 written design awaiting review

- Current state: the complete Gate D2 oral design is approved and has been written as `docs/specs/2026-08-20-sherpa-runtime-only-capability-proof-design.md`; it is awaiting the user's written-spec review. The design can quickly decide whether the exact official sherpa-onnx v1.13.6 Windows CPU runtime starts on this Windows 11 25H2 machine, but explicitly cannot claim model loading, acceptable speed, natural voice, or commercial readiness.
- Work completed: `git pull --ff-only` returned `Already up to date.`; project status, the SmartSub compatibility research, the prior voice-pilot design/plan, and the isolated harness were rechecked. The approved design selects a separate `runtime_proof.py`, synthetic archive tests, fixed per-user paths, a no-`extractall` archive contract, exact asset bytes/SHA-256, a mandatory `sherpa-onnx-offline-tts.exe --help` proof, complete load-candidate Authenticode inventory, D2-I／D2-X／D2-U stop points, no-retry rules, evidence schema, and an explicit package-decision ladder. Self-review measured 366 lines, 26 headings, 10 paired Markdown fences, zero placeholders/trailing whitespace, all required gate/hash markers present, and `git diff --check` clean. This was documentation-only work, so no code tests were required or run.
- Next step: the user reviews and explicitly approves the written design. Only then create a detailed implementation plan; that plan still will not authorize code, downloads, extraction, binary execution, model access, personal media, or synthesis. A later separate approval will be required for synthetic-only D2-I implementation.
- Blockers: sherpa-onnx has not been downloaded or locally executed; ZipVoice model loading and audible quality are outside D2; the Emilia-linked model's commercial rights remain unresolved. No implementation code, test behavior, dependency, runtime/model file, video/audio, Yating/SmartSub process, synthesis, login, upload, or push was performed.

## 2026-08-20 SmartSub installer compatibility research completed; direct runtime remains gated

- Current state: official-source research confirms that SmartSub 3.7.0 issue #432 has the same seven-field APPCRASH signature as this machine, so the same installer should not be retried. A direct official sherpa-onnx Windows CPU runtime is technically plausible, but it has not been downloaded or run locally and the exact Emilia-linked ZipVoice model does not have clearly established commercial-use rights.
- Work completed: pulled the current branch (`Already up to date.`), inspected the pinned SmartSub v3.7.0 release/build/NSIS configuration and issue state, compared Windows 11 25H2 builds and the seven stable crash fields, fixed the current sherpa-onnx v1.13.6 TTS-enabled Windows x64 archive at `24,497,928` bytes and SHA-256 `4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613`, confirmed that no sherpa runtime is currently available in the project environment, and recorded the evidence in `docs/research/2026-08-20-smartsub-installer-compatibility.md`. This was documentation-only research; no code tests were required or run.
- Next step: if the user wants a private non-commercial capability check, first write and approve a separate Gate D2 plan for the exact v1.13.6 runtime-only download, archive inspection, isolated extraction, signature/hash inventory, and `--help`/version proof. Model extraction/loading, reference media, and synthesis must remain a later explicit gate. For customer-facing use, select or establish a model with commercially clear rights before any production trial.
- Blockers: SmartSub issue #432 remains open without an official fix or workaround; Windows 11 25H2 is a strong inference rather than a confirmed root cause; the direct runtime has not been locally verified; ZipVoice memory/static-output risks still require bounded QA; and the exact model's commercial rights remain unresolved. No installer was run, no new asset was downloaded, no archive/model/video was read or extracted, and no Yating, synthesis, login, upload, or push occurred.

## 2026-08-19 free-first voice pilot Gate D blocked by SmartSub installer APPCRASH

- 一句話現況：使用者已另行精確核准執行 exact-hash 的 `NotSigned` SmartSub 3.7.0 installer；installer 只啟動一次便在任何 SmartScreen／NSIS UI 或安裝檔案出現前，於自身解出的 `System.dll` 發生 `0xc0000005` APPCRASH，因此依 no-automatic-retry 與 fixed per-user UI 契約停止，Gate D 未完成。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`，基線 `c16ecfd1f56dcc04cb5e6158b7b07a58ae5555c6`；啟動前重新證明 installer 為 `127,844,583` bytes、SHA-256 `65f6c85aa196063f365562c41393d2f98ef0ce31e4ee3e0122d561668d433520`、Authenticode `NotSigned`，內嵌 Product／File Version 均為 `3.7.0`，SmartSub／WINWORD process `0 / 0`，install／data path 均不存在。computer-use native pipe 不可用後，依 screenshot Skill 改以可見 `Start-Process` 啟動一次，未使用 `/S`，只把 NSIS `/D` 指向核准的 per-user path；PID `17356`（event hex `0x43CC`）。Windows Application Error event `1000` 記錄 faulting module `C:\Users\cance\AppData\Local\Temp\nssFBB3.tmp\System.dll`、exception `0xc0000005`、offset `0x00001581`；WER event `1001` 的 Report ID 為 `612b70b2-e2f2-4115-b0a1-73533d65fdad`。
- 下一步：本次 Gate D 授權已在明確 crash 後停止；不應把同一失敗改成靜默解包、相容模式、admin、不同路徑或不同版本。若要繼續，先另行討論並核准新的 installer 相容性診斷／替代免費方案，不把診斷授權視為影片、音色或合成授權。
- 阻塞點：postflight SmartSub relevant process `0`、核准 install path 只有 installer 留下的空目錄（files／subdirectories `0 / 0`）、data path 不存在、常見 alternate SmartSub paths與 uninstall registry entry 均不存在；NSIS temp只留下 `System.dll`／`UAC.dll`。沒有安裝 SmartSub、解壓或部署 ZipVoice、讀取本人影片、建立音色、啟動 Yating、合成、下載其他模型、登入、上傳、清理暫存或 push。暫存 GUI 證據在 `C:\Users\cance\AppData\Local\Temp\codex-shot-2026-08-19_22-29-45.png`，未進 Git；WER archive雖存在但其 ACL拒絕讀取，未繞過。

## 2026-08-19 free-first voice pilot Gate D safe-stopped at unsigned installer

- 一句話現況：使用者已精確核准 Gate D；三個 pinned official GitHub assets 已下載並通過正式檔名的 bytes／SHA-256 重驗，但 SmartSub 3.7.0 installer 的 Authenticode 為 `NotSigned`，因此依 Task 5 在啟動 installer 前安全停止，SmartSub 與 ZipVoice model 均尚未安裝。
- 這次做了什麼：`git pull --ff-only` 為 `Already up to date.`，Gate D 基線為 `207703be7182f8dce8846cd49016e411764dca65`；前檢 SmartSub／WINWORD process 均為 `0 / 0`，專用 downloads／app／data 目錄原先不存在，C 槽可用 `40,655,564,800` bytes。只從計畫三個 direct GitHub URLs 各下載一次至 `.partial`，驗證後才改正式檔名；installer 為 `127,844,583` bytes／`65f6c85aa196063f365562c41393d2f98ef0ce31e4ee3e0122d561668d433520`，ZipVoice archive 為 `109,162,785` bytes／`77219c8b40f4ee8d73a7f902305ff6c1128ef9b54461c41b4ca6ed890b6c2803`，vocoder 為 `54,157,409` bytes／`bcb3b970e384161c4d634f0bb9e999ff1c471b34c9bc0b1049a5014065ed3cc0`；重驗總計 `291,164,777` bytes、全部 bytes/hash `True`、`.partial` count `0`。
- 下一步：若使用者仍要繼續，必須另行明確核准執行這個 `NotSigned` 但 exact bytes／SHA-256 相符的 installer，並明示 Windows SmartScreen 若出現時是否允許只對此 exact hash 選擇「仍要執行」；新的確認仍只涵蓋 Task 5 的可見 per-user 安裝、固定 model 部署與 capability proof，完成後再次停止。
- 阻塞點：installer 沒有 signer 或 timestamp certificate，無法用 Authenticode 證明 publisher identity；尚未啟動／安裝 SmartSub、尚未解壓或部署 model，且未讀取本人影片、未建立音色、未啟動 Yating、未合成、未下載 ASR／CUDA／Vulkan／其他模型、未登入、未上傳、未 push。三個已驗證下載檔保留在 `%LOCALAPPDATA%\EasyTravelVoicePilot\downloads`，未自動刪除。

## 2026-08-19 free-first voice pilot Gate I completed; stopped before downloads

- 一句話現況：使用者已書面核准5–10秒reference修正及實作計畫；Tasks 1–4的synthetic-only Gate I已完成並建立本機implementation commit `100ede1ae3b5d88f7743f8e779621744d59412ae`，目前安全停止在三個pinned assets的下載／安裝授權前。
- 這次做了什麼：從基線`4f2d51428377cdcfd96c877832c5982ff2c87930`新增私人media／model Git ignore、防竄改script freeze與single-cue SRT、exact-ack Yating wrapper、PCM16 mono／duration／silence／clipping檢查、-23 dBFS RMS／-1 dBFS peak等音量、A／B sealed reveal及identity-leak驗證；TDD focused為`20 passed`，既有Yating controls為`25 passed`，完整suite為`614 passed, 8 skipped in 22.80s`，compile exit 0，SmartSub／WINWORD before-after均`0 / 0`，`src/`與既有travel briefing tests為0 diff。
- 下一步：若使用者要繼續，須另行精確核准Gate D，才可從計畫固定的三個官方GitHub URL下載共`291,164,777` bytes／`277.68 MiB`、驗證hash／簽章並安裝SmartSub 3.7.0與固定ZipVoice model；Gate D完成後仍再次停止，不能讀影片、建音色或合成。
- 阻塞點：ZipVoice／Emilia商用license仍未釐清；CPU實際速度、本人相似度及A／B聽感均未驗證。未下載、未安裝、未讀取或抽出本人影片、未啟動Yating／SmartSub、未合成、未上傳、未付款、未修改正式管線、未push；既有OSA LIST QA阻擋保持獨立。

## 2026-08-19 free-first briefing voice pilot design awaiting written review

- 一句話現況：使用者已逐段口頭核准以 SmartSub + ZipVoice 為第一順位的免費本機語音試驗；正式書面規格已建立，現在停在使用者審閱關卡，尚未授權實作。
- 這次做了什麼：完成本人 2 分 59 秒影片的唯讀技術前檢，確認只有本人聲音後，將固定 60 至 90 秒盲測、A／B 問題處理、一次調整上限、30 至 60 分鐘後續錄音、5 至 7 分鐘長稿驗收、資料隔離及免費／付費 fallback 順序寫入 `docs/specs/2026-08-19-free-first-briefing-voice-pilot-design.md`；`git pull --ff-only` 為 `Already up to date.`。
- 下一步：使用者先審閱書面規格；只有收到精確核准後才建立實作計畫，計畫中的第一個實際關卡仍是列出版本、license、下載量、路徑及回復方式，再另行取得下載／安裝同意。
- 阻塞點：這台 i7-8565U／8 GB／無 NVIDIA GPU 機器的 ZipVoice 實際速度與品質尚未驗證；本人相似度、A／B 聽感也必須由使用者試聽。未下載模型、未安裝套件、未抽出或上傳音訊、未付款、未修改正式 Yating 管線。既有 OSA05261025D LIST day-page QA 阻擋保持獨立且未重試。

## 2026-08-19 OSA05261025D one-DRAFT stopped at LIST day-page QA

- Current state: the user-authorized one-request DRAFT used exactly one NewAmazing GET and one render. Prepare returned `DRAFT_READY`; the final render returned `BLOCKED` because LIST PDF inspection reported `LIST QA day page mapping does not match PDF`. No source or render retry was attempted.
- Work completed: `git pull --ff-only` returned `Already up to date.` Installed runtime and CLI are `0.2.1`; doctor passed Word COM, Microsoft Yating, configured pdftoppm, and schema-2 LIST calibration, with only the existing unavailable-ffmpeg warning. Prepare created source draft `0ac60232c48eaa64a6eb7f042e3b1291e9129d5d7d211445ce2a17e3c80e4b57` under `...\OSA05261025D\20260819T141938+0800`; it parsed 5 days, 2 flights, 1 source, and 0 conflicts without retaining raw HTML. `check-script` was ready with no issues, estimated 433.3 seconds, and script SHA-256 `a152c90334a240f04bb3665d660445a540bb5616e4f76e68d93da42c122e028a`.
- Render evidence: the one render took 81.2 seconds and created final draft `585278b4d26c20e78dd4046fb595545f0981a1c07c81e8fb57df1b317c9fc750` under `...\OSA05261025D\20260819T142144+0800`; WINWORD was `0 / 0`. Yating completed a PCM mono 16-bit 16 kHz WAV lasting `416.011375` seconds with 89 segments, 88 bookmarks, and 45 synthesis chunks. WAV/SRT/TXT SHA-256 values are `668fa94c...5c9a`, `d091559f...8859`, and `8053a61c...ac32`; SRT has 89 sequential monotonic cues, its last timestamp is within WAV tolerance, and waveform peak/RMS ratios are `0.713867 / 0.107296`.
- Word evidence: a DOCX and a one-page A4 failed-QA PDF were created, but the workflow withheld Word delivery evidence after the day-page mapping failure; missing required text was empty. Read-only PNG inspection of the existing failed-QA PDF showed a clean one-page QR-free full-width layout with five daily rows, no visible clipping/overlap/missing glyphs, and the requested title/non-title treatment. The visible day date is line-wrapped, consistent with the raw-regex day-token QA false negative, but the artifact remains blocked under fail-closed rules.
- Review/blockers: 10 OP fields remain unconfirmed; review also retains 2 `MISSING_REQUIRED_FACT`, 1 `WEATHER_DATA_UNAVAILABLE`, and 8 `UNKNOWN_PRONUNCIATION_TERM` items. MP3 is unavailable because ffmpeg is not configured. Human audible listening was not performed, so technical audio QA is not claimed as listening acceptance. No JMA, second GET, second Word/Yating render, ffmpeg installation, cloud TTS, CONFIRMED, LINE, Cowell, upload, deploy, publish, or push was performed.
- Next step: write and approve a minimal offline fix for day-page token matching across PDF layout whitespace, run the complete offline suite, then require a fresh explicit generation request before a new DRAFT render. Do not present the current DOCX as passed or retry this consumed one-DRAFT.

## 2026-08-19 UKB05270314A 0.2.1 runtime sync and one-DRAFT completed

- 一句話現況：依 OP 明確授權，installed runtime 已以可回復方式從 `0.2.0` 同步至已驗證的 `0.2.1`，隨後只對 UKB05270314A 執行一次 NewAmazing GET 與一次 DRAFT render；結果為 `DRAFT_READY / needs_review`，Word／PDF／PNG／WAV／TXT／SRT 技術 QA 通過，MP3 因既有 ffmpeg 未設定而缺少，實際語音聽感及黃色 OP 欄位仍待人工 review，未執行 CONFIRMED。
- 開工與套件：`git pull --ff-only` 為 `Already up to date.`，baseline `bd7e35446d0a28cc1f781df9e0242b358b08985b`，working tree 原為乾淨的 `main...origin/main [ahead 89]`，WINWORD 0。離線建立 `EasyTravel-Briefing-Materials-0.2.1.zip`，63 entries、SHA-256 `addd879483632a7b88ee20d51e0454b395eab8c8e34c4dedf568b30c532579e8`；修正首次把 repo `__pycache__` 誤算為 package source 的唯讀比對後，正式 `.py/.json` allowlist 為 repo/package 36／36、檔名差異 0、hash差異 0。
- Runtime 同步：現有 app 完整保留於 `C:\Users\cance\AppData\Local\EasyTravelBriefing\app-backup-0.2.0-20260819-122908`（1,452 files）；新 app 由已驗證 package stage 建立並沿用原 venv。利用機器上既有 setuptools 82.0.1 執行純本機 `--no-deps --no-build-isolation` metadata同步，沒有下載依賴。CLI與 distribution metadata均為 `0.2.1`，36個來源 hash與 repo完全一致，doctor的Word／Yating／pdftoppm／schema-2 calibration均ok；config SHA-256前後同為 `8ccffbfff23173ca123b59d340feb6d41ea839f86c5604e78dd503b975a23d59`，private master／manifest hashes仍為 `08b4393b...ae468`／`edf2300b...5931`。ffmpeg仍是唯一warning。
- 唯一來源 GET：第一次 orchestration command因把 config path 的 `str` 傳給要求 `Path` 的 `load_config()`，在 `prepare` 呼叫前即停止，沒有 GET；修正本機型別後才呼叫唯一一次 `prepare`，exit 20／`DRAFT_READY`，source draft ID `090f85f1ae970d52a144848af66be6edbea37545ab376e9880cf242078168584`，run為 `...\UKB05270314A\20260819T123006+0800`。解析結果為5天、2航班、1來源、0 conflicts，source warning code `SOURCE_CITY_MISSING`；沒有重抓、改網址、保留 raw HTML或使用替代來源。
- 旁白：同次 narration input `ready=true`，18個 protected facts；只按固定八段marker將每個受保護事實原文放入對應段落，不加入外部事實或未確認值。`check-script` exit 0、ready true、issues 0、1,623 characters、estimated 450.8 seconds、script SHA-256 `09b478f542a021c07da603b312bd0438822e57c3503156a5407766c09e991787`。
- 唯一 render：只呼叫一次正式 `render`，84.2秒完成，exit 20、`DRAFT_READY / needs_review`，新 draft ID `2c84af09ee03c6bb36d24e786a875439116e7c1a828cec17197b06a80efcb13e`，run為 `C:\Users\cance\Documents\EasyTravel-Private\briefing-output\UKB05270314A\20260819T123215+0800`；WINWORD `0 / 0`，沒有 render retry。
- Word artifacts：`DRAFT_UKB05270314A_說明會資料.docx` 33,532 bytes／SHA-256 `f97a898e43f3b5c9c1f26766c592a80305d2f6a1224e3f1a56ff286b03cfe0d2`；Word-QA PDF 163,887 bytes／SHA-256 `87ce05ed8b3c9e2e3115126f4e9ad4bcc78bf260bb236b29168566b4c6668361`；page-001 PNG 346,229 bytes／SHA-256 `5ddfffaec629e7065f190462d52cb7898769d471a371ab92812e9c766309b5d1`。DOCX是1保存頁、4 tables、rows `4／3／6／1`、7 body paragraphs、0 media／drawing／inline shapes；PDF是1頁A4 portrait、0 images，index schema 2將day 1..5全綁page 1且PNG hash相符。
- Word 契約與視覺：word evidence schema 3／`list-word/4`，QR image與header QR candidate均0，extra trailing paragraph 0，title 22 pt維持，所有非標題文字12 pt。原始解析度逐頁檢視通過：團名自然折成兩行並使用完整寬度，無QR或保留空位，五天daily rows／航班／黃色欄位／表格邊框完整，無裁切、重疊或缺字；服務費為五天新台幣1,500元。
- Audio artifacts：WAV 13,997,230 bytes／SHA-256 `1c3157da8857e71e27d67d6b803c93a93776d5af23fc1a03f5167460c00825e0`，SRT 8,324 bytes／SHA-256 `3e6c1f8641351b06740086217ea7a160638b45da47786c6dfcc2a4ba827699c7`，TXT 5,055 bytes／SHA-256 `2b1124843a17a0cc977ed684a7967da3dad0ca7f779e81da3652169f3535d9df`；metadata hashes全相符。WAV是PCM mono／16-bit／16kHz、437.412062秒且落在360..480秒；92 segments、91 bookmarks、46 batches，92個SRT cues編號與時序有效、單調且最後時間在WAV容差內；波形peak/rms證明非靜音。這些是自動結構證據，不冒充真人聽感 QA。
- Review／範圍：9個 OP fields全部維持黃色未確認；narration review codes為 `MISSING_REQUIRED_FACT`、`UNCONFIRMED_OP_FIELD`、`UNKNOWN_PRONUNCIATION_TERM`、`WEATHER_DATA_UNAVAILABLE`，沒有猜值。MP3 artifact是missing／`MP3_CONVERTER_UNAVAILABLE`。沒有live JMA、第二次NewAmazing GET、第二次Word/Yating、ffmpeg安裝、Hanhan／cloud TTS、CONFIRMED、LINE、Cowell、upload、deploy、publish或push。
- 下一步：OP先開啟DOCX與WAV review版型、資料及語音聽感，並提供當前 draft ID綁定的9個黃色欄位與必要來源／發音決策。若未來需要CONFIRMED，還須先補齊MP3能力、所有required fields及人工視聽驗收，再對 exact draft ID `2c84af09...cb13e`另行明確授權；本輪不確認、不對外傳送。
- 阻塞點：DRAFT本身已安全產出；CONFIRMED目前受9個未確認OP欄位、review codes、人工語音聽感尚未完成及MP3缺失阻擋。

## 2026-08-19 UKB05270314A DRAFT preflight blocked by stale installed runtime

- 一句話現況：OP 已提供 NewAmazing `UKB05270314A` 網址要求新的本機 DRAFT；one-request DRAFT 授權有效，但在任何來源 GET／Word／Yating 前，離線 preflight 發現 `%LOCALAPPDATA%` installed runtime 仍為 `briefing 0.2.0`，不含目前 repo `0.2.1` 已驗證的 LIST 輸出修正，因此安全停止，尚未消耗此網址的唯一 GET 或 DRAFT render。
- 前檢：`git pull --ff-only` 為 `Already up to date.`，baseline `a3d979171ee03304edbec8a3993ef878f2ef63fa`，working tree 原為乾淨的 `main...origin/main [ahead 88]`。installed `doctor` exit 0；Word registry、Yating、pdftoppm、schema-2 calibration、master hash與 normalized structure均 `ok`，WINWORD 0；ffmpeg 未設定而為 warning，故未來即使 DRAFT 成功也不會有 MP3。
- 版本證據：repo briefing package／`src/travel_briefing.__version__` 為 `0.2.1`，installed runtime 為 `0.2.0`。`word_list.py`、`word_qa.py`、`workflow.py` 的 repo／installed SHA-256 全不相符；installed `word_list.py` 仍保留 output QR candidate 與 source candidate 相等的舊契約，不能滿足已核准的 QR-free、full-width、12 pt、no-extra-paragraph、動態服務費及新版 PDF QA 路徑。只有 `adapters/windows_word.py` hash相符不足以宣稱 runtime已同步。
- 安全邊界：依既有 0.2.1 計畫與 canonical Skill，installed runtime 同步是 DRAFT 以外的獨立授權；不得以 current URL request 私自安裝、覆蓋 `%LOCALAPPDATA%` 或改用 repo `.venv` 作未核准 fallback。沒有執行 NewAmazing GET、JMA、Word、Yating、ffmpeg、CONFIRMED、LINE、Cowell、deploy、publish、push或任何 artifact 產生。
- 下一步：等待 OP 明確回覆「同意同步 installed runtime 至目前已驗證的 0.2.1；同步與 doctor 通過後，繼續執行 UKB05270314A 的原 one-DRAFT，不重抓、不改來源。」同步完成後先證明 runtime版本／關鍵hash／doctor，再用原網址執行一次 prepare；來源或 render若失敗則依 one-request規則停止，不做隱性 fallback。
- 阻塞點：installed runtime 0.2.0 與已驗證 repo 0.2.1 漂移；同步尚未獲得當次明確授權。ffmpeg 未設定只會缺 MP3，不阻擋 reviewable Word／WAV／TXT／SRT DRAFT。

## 2026-08-19 LIST 4-day whitespace post-fix one-shot Word repro succeeded

- 一句話現況：依 OP 精確授權只執行一次 `test_calibrated_master_renders_gate_v_day_counts[4]`，原文為 `1 passed in 32.97s`；同次 DOCX／PDF／PNG／schema-2 index 的結構、內容、雜湊與逐頁視覺 QA 全部通過，4 天 Word 產出路徑目前已驗證成功。
- 前檢與 selector：`git pull --ff-only` 為 `Already up to date.`，baseline `08f6b9f9cb5079f55483029626c9af8efc73772f`，working tree 原為乾淨的 `main...origin/main [ahead 87]`。完整離線 suite 原文 `594 passed, 8 skipped in 22.97s`；doctor 確認 Word registry、configured pdftoppm、schema-2 calibration、master hashes 與 normalized structure 均可用，唯一 warning 是本次不使用的 ffmpeg。collect-only 原文 `1 test collected in 0.34s`，唯一 node 是 `[4]`，collect 前後 WINWORD 均為 0且 fresh QA root 保持空白。
- 唯一實機 run：fresh root 為 `output/word-repro-whitespace-postfix-20260819-120734`；正式 selector 只呼叫一次並使用 `-x -vv`，結果 `WORD_REPRO_EXIT=0`、`1 passed in 32.97s`、WINWORD `0 / 0`。沒有重試，也沒有執行 5／6／7／8／12 天。
- 同次 artifacts：`day-004/LIST.docx` 32,731 bytes／SHA-256 `9b74e4bad28032f038ee3e96c5506b5b6c0b762ece49aa5f3403347fe10751ce`；`LIST-qa.pdf` 119,882 bytes／SHA-256 `5dcbd3b2d568af60ebeee089fd03ec2cf64975ba45bdc4b036c908941dce5acc`；`pages/page-001.png` 229,924 bytes／SHA-256 `a54333f1301a9c060481908bfe6a08d90d242c3f71663d94be62e16ab6d08f4f`；`pages/index.json` 347 bytes／SHA-256 `4c7353c84cc0c29482ccac87f9f7805523e563f0653d5fafd6b67da119fe0701`。root 精確只有這 4 檔，`failed-qa` 不存在。
- DOCX／內容 QA：DOCX 保存頁數 1，4 tables、rows `4／3／5／1`、7 body paragraphs、0 inline shapes、0 media、0 drawing parts；`SYN-LIST-260901`、`JX820`、`JX821`、`合成大阪4日`、`日本精緻假期` 與完整服務費正文均存在。「四天共新台幣 1,200 元」存在，「六天共新台幣 1,800 元」不存在；integration evidence 同時證明 QR image/header candidate 均為 0、非標題 12 pt、標題字級未改、額外尾端 paragraph count 為 0。
- PDF／index／視覺 QA：PDF 是 1 頁 A4 portrait（595.32 × 841.92 pt）、0 images，完整四天服務費與所有 required tokens 都可由 PyMuPDF 讀回；第一行標題約 21.96 pt，其他文字全部 12 pt。schema-2 index 的 `page_count=1`、day map 為 1／2／3／4 且全在 page 1，PNG SHA-256 與實檔完全一致。以原始解析度逐頁檢視 `page-001.png`：右上無 QR 或保留空位、團體資訊使用完整寬度，表格與注意事項沒有截斷、重疊或缺字。
- Postflight 與範圍：private master SHA-256 仍為 `08b4393b8e7782f9f1425a4a265a4f2737cb1dec7f1813f1b1c2ede88daae468`，manifest SHA-256 仍為 `edf2300b7fecb34662482291bc1de37f2502e6feb4f54aec00895b0354d80593`；WINWORD 0，Word opt-in 已清除。沒有修改 production／tests，沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish、push或其他天數 Word run。
- 下一步：4 天 synthetic Word blocker 已解除；OP 可提供一個 NewAmazing 連結要求新的本機 DRAFT。實際 DRAFT 仍須以該網址 parser／內容與當次 artifact QA 結果為準；5／6／7／8／12 天未在本次授權中驗證。
- 阻塞點：4 天 Word 路徑沒有已知 blocker；其他天數與真實網址 DRAFT 尚未由本次 one-shot 驗證。

## 2026-08-19 LIST PDF required-text whitespace offline implementation handoff

- 一句話現況：LIST PDF QA 已離線修正aggregate `required_text`對Word/PyMuPDF layout whitespace的false negative；兩個TDD slices與完整離線驗證全綠，但尚未重新執行Word實機repro，不能宣稱4天DOCX／PDF／PNG QA已通過。
- 開工與範圍：`git pull --ff-only`為`Already up to date.`，implementation baseline `06131f4e308bc1c723b71680387d1c04296d77d4`，working tree原為乾淨的`main...origin/main [ahead 85]`，WINWORD 0且Word opt-in未設定。production／test changes精確只有`src/travel_briefing/word_qa.py`與`tests/unit/travel_briefing/test_word_qa.py`。
- TDD slice 1：新增public-seam CJK A4 PDF regression，fixture先證明`每人每天\n新台幣...` raw不連續、compact可匹配；primary red原文`_ListPdfRequiredTextError: LIST QA PDF is missing required text`。加入private `"".join(value.split())` aggregate comparison後，primary與existing missing-token control為`2 passed`。
- TDD slice 2：whitespace-only expected token先為`Failed: DID NOT RAISE ValueError`；只擴充既有input validation後，三個core targets為`3 passed`。新增non-whitespace character／punctuation drift與continuation raw-strict controls後，focused set為`10 passed`。
- 實作契約：helper只進入aggregate required-text validation／presence；PDF／DOCX／JSON不改。whitespace-only token使用既有safe message fail closed；missing diagnostics仍回報original values並保留caller order／original-value dedupe。continuation、day mapping、A4、image、page count、failed evidence、PNG／index schemas與publication未改。
- 驗證：完整`test_word_qa.py`為`29 passed in 1.84s`；direct unchanged controls為`114 passed in 1.60s`；完整suite為`594 passed, 8 skipped in 22.97s`；WINWORD`0 / 0`且opt-in未設定；compileall exit 0、`git diff --check` exit 0、unchanged controls diff 0、external integration scan 0 hits。
- Commit：`51324495c13fbaf51cffdd800c29942bf164c00c`（`fix(briefing): ignore LIST PDF layout whitespace`）只含兩個核准implementation files；本段由緊接的本機documentation handoff commit保存，hash以`git log`為準。
- 誠實與範圍：沒有啟動Word、讀寫private master／calibration、產生實機DOCX／PDF／PNG、GET、JMA、Yating、ffmpeg、dependency download、LINE、Cowell、deploy、publish或push。離線synthetic綠燈不能取代real Word visual QA。
- 下一步：若OP要實機驗證，回覆「同意只執行一次 4 天 post-fix Word repro；不跑其他天數；若成功，完成同次 DOCX／PDF／PNG QA；成功或失敗都不重試。」新的授權只執行精確`[4]` selector一次，不跑其他天數且不重試。
- 阻塞點：新的4天same-run artifacts尚未生成；等待新的精確one-shot Word授權。

## 2026-08-19 LIST PDF required-text whitespace offline implementation plan review

- 一句話現況：OP 已核准 whitespace-normalization 書面規格；離線實作計畫已建立並等待 OP review，尚未修改或執行 production／tests，Word 實機仍是獨立關卡。
- 開工狀態：`git pull --ff-only` 為 `Already up to date.`，planning／design baseline `ca7ea7571a893954507f2bbc51c76c86c340dfcf`，working tree 原為乾淨的 `main...origin/main [ahead 84]`，WINWORD 0且Word opt-in未設定。`CONTEXT.md`不存在；重新核對核准規格、`inspect_list_pdf()`、現有PyMuPDF helpers、missing-token／failure-evidence tests與repo planning慣例。
- TDD seam：只透過public `inspect_list_pdf()`與真實synthetic A4 PDF觀察行為，不直接測private helper、不mock內部。計畫拆成layout-wrap primary red→minimal aggregate green、whitespace-only token red→validation green，再加入non-whitespace與continuation strict regression controls。
- 計畫文件：新增 `docs/plans/2026-08-19-list-pdf-required-text-whitespace-implementation-plan.md`，包含7個tasks、兩個分離commits、精確focused／full-suite commands、changed-file audit、WINWORD non-use、handoff與one-shot Word獨立授權。
- 最小實作範圍：未來只允許修改 `src/travel_briefing/word_qa.py` 與 `tests/unit/travel_briefing/test_word_qa.py`；workflow、errors、word_list、兩支PowerShell adapters、local-backend／Word／integration controls、schemas、private master與calibration全部unchanged。若需跨出範圍立即停止review。
- 自審：plan 435行、7個tasks、46個Markdown fences且成對、14個completion checks、placeholder 0，public seam、兩個red→green slices與精確下一授權皆存在，`git diff --check`通過。臨時無Word PyMuPDF probe以built-in `china-t`穩定readback `每人每天\n新台幣...`，raw contiguous false、compact contiguous true，確認primary fixture可執行；temp已清理。
- 誠實與範圍：本輪只建立plan與STATUS，沒有修改或執行production／tests，沒有Word、private master／calibration、DOCX／PDF／PNG、GET、JMA、Yating、ffmpeg、dependency download、LINE、Cowell、deploy、publish或push。`writing-plans` Skill不在可用清單，因此沿用repo既有test-first plan格式建立等價計畫。
- 下一步：OP review後若同意，回覆「同意此實作計畫，開始離線實作」；完整離線驗證通過後停止，新的4天Word repro仍需另一個精確one-shot授權。
- 阻塞點：離線實作計畫review gate；whitespace-normalization尚未實作，4天successful artifact QA仍未通過。

## 2026-08-19 LIST PDF required-text whitespace-normalization design review

- 一句話現況：OP 已核准只讓 aggregate `required_text` 忽略 PDF layout whitespace、其餘頁面與結構 QA 維持嚴格的設計；完整書面規格已建立並等待 OP review，尚未修改 production／tests，也未執行 Word。
- 開工與證據：`git pull --ff-only` 為 `Already up to date.`，baseline `0ccb3841622b916774df1d480ccfa9655931a449`，working tree 原為乾淨的 `main...origin/main [ahead 83]`，WINWORD 0且Word opt-in未設定。重新核對同次 failed PDF／failure report、`inspect_list_pdf()` raw substring seam、missing-token ordered-unique evidence與既有 strict continuation／day-page checks。
- 選定方案：只在 aggregate presence comparison 的副本上用 Python Unicode whitespace semantics 移除 whitespace；PDF／DOCX／error／JSON內容不改。whitespace-only expected token 必須在開啟PDF前 fail closed；真正缺字時仍回報原始token，保留caller order與original-value dedupe。大小寫、標點、Unicode寬度、字元內容與順序都不正規化。
- 書面規格：新增 `docs/specs/2026-08-19-list-pdf-required-text-whitespace-design.md`，固定helper語意、input validation、matching data flow、diagnostics、strict unchanged checks、兩檔implementation boundary、TDD regressions、完整離線驗證與one-shot Word獨立授權。
- 自審：規格342行、24個headings、16個Markdown fences且成對、placeholder 0；selected design、strict-unchanged section、review gate與精確下一授權文字皆存在，`git diff --check`通過。範圍可由單一小型離線implementation plan完成，沒有schema／adapter／workflow／master變更或模糊fallback。
- 範圍界線：本輪只允許spec、STATUS與本機documentation commit；沒有修改或執行production／tests，沒有Word、private master／calibration、DOCX／PDF／PNG、GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish或push。
- 下一步：OP review後若同意，回覆「同意此書面規格，開始建立離線實作計畫」；該句只授權建立計畫，不授權production／test edits或Word。
- 阻塞點：書面規格review gate；whitespace-normalization尚未實作，4天successful artifact QA仍未通過。

## 2026-08-19 LIST 4-day failure-evidence post-fix one-shot repro

- 一句話現況：依 OP 精確授權只執行一次 `test_calibrated_master_renders_gate_v_day_counts[4]`；Word 成功匯出一頁 A4 PDF，但流程以 `LIST_PDF_REQUIRED_TEXT_MISSING`／`1 failed in 32.29s` fail closed。保留證據證明正文並未遺失，而是 Word 在「每人每天」與「新台幣」之間自動換行，現行 raw substring QA 因而誤判；已遵守 no-retry 停止。
- 開工與 selector：`git pull --ff-only` 為 `Already up to date.`，baseline `8f9db08b46f4a3fac5a505b61e3a9401d197d306`，working tree 原為乾淨的 `main...origin/main [ahead 82]`。doctor 確認 Word registry、configured pdftoppm、schema-2 calibration、master SHA 與 normalized structure 都是 `ok`；未使用的 ffmpeg 為 warning。fresh QA root 是 `output/word-repro-failure-evidence-postfix-20260819-113502`；collect-only 原文 `1 test collected in 0.33s`，唯一 node 是 `[4]`，沒有 5／6／7／8／12，且 QA root 仍空、WINWORD `0 / 0`。
- 唯一實機結果：正式 selector 只呼叫一次並使用 `-x -vv`；原文為 `LIST QA PDF is missing required text`、outer `WORD_GENERATION_FAILED`、inner `LIST_PDF_REQUIRED_TEXT_MISSING`、`1 failed in 32.29s`、`WORD_REPRO_EXIT=1`。WINWORD 前後均為 0，opt-in 已清除，沒有第二次 Word／pytest 呼叫。
- 同次 artifacts：`day-004/LIST.docx` 為 32,730 bytes／SHA-256 `c339cbb8ede4fb4a0842e9411aad97b647682ad417e9e3b173a5affee8d22b21`；`failed-qa/LIST-qa.failed.pdf` 為 119,882 bytes／SHA-256 `6f210b3dd5108f952338cdd4c8efabd5f830363fd0e76d6bd27e0aeb0f878a3f`；schema-1 `failure.json` 為 549 bytes／SHA-256 `34ab6e493ce69eb4d84114f2971dc2dd8374d5ba66316267b733a874bd032baa`，其 PDF bytes／SHA 與實檔一致。正常 `LIST-qa.pdf`、`pages/`、PNG 與 `index.json` 全部不存在。
- 唯讀診斷：DOCX 有 4 個 tables、rows `4／3／5／1`、7 個 body paragraphs、0 media／0 inline shapes，完整四天服務費 token 存在。failed PDF 是 1 頁 A4 portrait（595.32 × 841.92 pt）、0 images；其文字實際為 `每人每天\n新台幣 300 元，四天共新台幣 1,200 元`。raw target 不匹配，但移除 whitespace 後完整匹配，因此目前 blocker 是 `inspect_list_pdf()` 的 raw substring 對合法版面換行敏感，不是 Word 漏填內容。
- Postflight 與範圍：private master 仍為 36,262 bytes／SHA-256 `08b4393b8e7782f9f1425a4a265a4f2737cb1dec7f1813f1b1c2ede88daae468`；manifest 仍為 3,096 bytes／SHA-256 `edf2300b7fecb34662482291bc1de37f2502e6feb4f54aec00895b0354d80593`；WINWORD 0，Word opt-in 未設定。沒有修改 production／tests，沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish、push，也沒有執行其他天數。
- 下一步：若 OP 要修正此 false negative，最小安全方向是先離線鎖定「required-text 比對時忽略 PDF layout whitespace，但仍要求完整非空白字元序列，day-token／page mapping 等其他 strict checks 不變」的書面規格；離線修正完成後，任何新 Word repro 仍需新的 one-shot 授權。
- 阻塞點：4 天實機內容已存在，但 successful DOCX／PDF／PNG QA 尚未通過；本次唯一 Word 授權已消耗，不得重試。

## 2026-08-19 LIST PDF QA failure-evidence offline implementation handoff

- 一句話現況：LIST PDF QA 已能以ordered-unique list指出缺少的required tokens；有效Word-exported PDF若在deterministic inspection失敗，會exclusive保存為`failed-qa/LIST-qa.failed.pdf`與hash-bound schema-1 `failure.json`，正常PDF／PNG／index保持不存在。離線實作與完整驗證已完成，但尚未重新執行Word實機repro。
- 開工與範圍：`git pull --ff-only`為`Already up to date.`，implementation baseline `3ead9bab2236abcd76f6298dad2d145a2537d154`，working tree乾淨，WINWORD 0，`RUN_BRIEFING_WORD_INTEGRATION`未設定。實際production／test changes精確只有`src/travel_briefing/word_qa.py`與`tests/unit/travel_briefing/test_word_qa.py`。
- Missing-token TDD：primary red原文為`AttributeError: 'ValueError' object has no attribute 'missing_required_text'`；加入private typed `ValueError`與caller-order dedupe後，primary `1 passed`、existing inspection controls `5 passed`。matched tokens與完整PDF text不進入錯誤內容。
- Failure-evidence TDD：primary red原文為`_ListPdfRequiredTextError: LIST QA PDF is missing required text`，證明temporary PDF仍會消失；加入preflight exclusive marker、token／generic safe inner codes、schema-1 report、copied PDF bytes／SHA-256驗證、exclusive JSON completion marker、fresh-path rollback與existing `WORD_GENERATION_FAILED` envelope後，primary `1 passed`。五個token／generic／collision／rollback focused controls全綠，完整`test_word_qa.py`為`24 passed in 1.58s`。
- Safety contracts：existing `failed-qa`會在adapter job前阻擋且不改sentinel；failure publication失敗只移除同次fresh PDF／report／directory，不使用recursive delete；success path不建立failed directory。Unknown Word result、invalid report、missing／empty PDF、byte mismatch、pdftoppm與successful publication paths不進入新catch。
- Commits：`a632c9607e43911d17080cb5e0d38a073ac4fe86`（missing tokens）與`09897a8b4bbcb65e80296682b9649e278fcbc669`（failed evidence）。`workflow.py`、`errors.py`、`word_list.py`、PowerShell adapters、local-backend與integration tests、private master／calibration及successful schemas全部diff為零。
- 完整驗證：direct unchanged controls原文`114 passed in 1.72s`；完整suite原文`589 passed, 8 skipped in 19.81s`；WINWORD `0 / 0`且opt-in未設定；`compileall` exit 0、`git diff --check` exit 0、external integration scan clean。
- 誠實與範圍：沒有啟動Word、讀寫private master／calibration、產生實機DOCX／PDF／PNG、GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish或push。離線synthetic綠燈不能判定上一份已刪PDF缺少哪個token，也不能宣稱4天實機路徑已修好。
- 下一步：若OP要實機驗證，回覆「同意只執行一次 4 天 post-fix Word repro；不跑其他天數；若成功，完成同次 DOCX／PDF／PNG QA；成功或失敗都不重試。」新的failed run會保留PDF與failure.json供唯讀診斷，但同一授權仍不重試。
- 阻塞點：新的4天Word artifact與實際missing-token evidence尚未生成；等待另一個精確one-shot Word授權。

## 2026-08-19 LIST PDF QA failure-evidence offline implementation plan review

- 一句話現況：OP 已核准 failed-PDF evidence 書面規格；test-first 離線實作計畫已建立並完成自審，等待 OP review，尚未修改或執行 production／tests，Word 實機仍是獨立關卡。
- 這次做了什麼：`git pull --ff-only` 為 `Already up to date.`，planning baseline／design commit 為 `b0a68cbc24e7677793c1f0848f9eab1a4f57b530`，working tree 原為乾淨的 `main...origin/main [ahead 78]`。重新核對核准規格、`word_qa.py` inspection／temporary publication seam、既有 synthetic adapters、exclusive-copy rollback pattern、direct tests與approval gates。
- 計畫文件：新增 `docs/plans/2026-08-19-list-pdf-qa-failure-evidence-implementation-plan.md`，拆成 missing-token primary red→green、failed-evidence publication red→green、generic／collision／success／rollback controls、focused unchanged controls、完整離線 suite與handoff七個 tasks，規劃兩個implementation commits與一個docs handoff commit。
- 最小實作範圍：未來只允許修改 `src/travel_briefing/word_qa.py` 與 `tests/unit/travel_briefing/test_word_qa.py`；`workflow.py`、`errors.py`、`word_list.py`、兩支PowerShell adapters、local-backend與integration tests、private master／calibration及所有success schemas皆為 unchanged controls。若需跨出範圍立即停止 review。
- 自審：placeholder scan 0、Markdown fences 46且成對、7個tasks、16個completion checks、496 lines，`git diff --check` 通過。自審抓到並修正初稿的完整baseline SHA錯誤，並補上primary case的matched `JX820` token，確保test同時證明matched token不外洩；commands、test names、rollback seam、三個commit boundaries、no-retry與Word／push gates一致。
- 誠實與範圍：本輪只建立計畫與本STATUS；沒有修改或執行production／tests，沒有啟動Word、讀寫private master／calibration、產生DOCX／PDF／PNG，也沒有GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish或push。`writing-plans` Skill不在可用清單，因此沿用repo既有`docs/plans` test-first格式建立等價計畫。
- 下一步：OP review後若同意，回覆「同意此實作計畫，開始離線實作」；完整離線驗證通過後停止，新的4天Word repro仍需另一個精確一次性授權。
- 阻塞點：離線實作計畫review gate；missing-token diagnostics與`failed-qa` artifacts尚未實作。

## 2026-08-19 LIST PDF QA failure-evidence design review

- 一句話現況：OP 已選定 A 方案；當有效 Word-exported PDF 在 deterministic inspection 失敗時，未來將只在 `failed-qa/` 保存 `LIST-qa.failed.pdf` 與 hash-bound schema-1 `failure.json`，正常 PDF／PNG／index 保持不存在，完整書面規格已建立並完成自審，等待 OP review。
- 這次做了什麼：`git pull --ff-only` 為 `Already up to date.`，baseline `c63cf07`，working tree 原為乾淨的 `main...origin/main [ahead 77]`。離線 synthetic A4 PDF loop 連續三次穩定得到 `LIST QA PDF is missing required text`，並以 `AssertionError: RED: missing token identities are not exposed` 證明現行錯誤無法指出 `JX821` 與 `SERVICE-FEE-TOKEN`；此 loop 沒有啟動 Word，也不假裝重現已被刪除的實機 PDF。
- 書面規格：新增 `docs/specs/2026-08-19-list-pdf-qa-failure-evidence-design.md`。規格固定 success/failure 路徑分離、`failed-qa` preflight exclusive marker、eligible failure boundary、ordered unique missing tokens、`LIST_PDF_REQUIRED_TEXT_MISSING`／`LIST_PDF_INSPECTION_FAILED` safe inner codes、`WORD_GENERATION_FAILED` outer envelope、schema-1 failure report、exclusive publication／rollback、兩個 production/test file scope及完整離線 acceptance gates。
- 自審：placeholder scan 0、Markdown fences 18且成對、29個 headings、385 lines，`git diff --check` 通過；成功路徑、失敗路徑、unknown Word result、pdftoppm failure、版本契約、rollback ownership、no-retry與未授權整合邊界沒有矛盾。規格可由單一小型離線 implementation plan 完成。
- 誠實與範圍：沒有修改或執行 production／tests，沒有啟動 Word、讀寫 private master／calibration、產生新 DOCX／PDF／PNG，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。這份規格不能判定上一份已刪 PDF 究竟缺少哪個 token。
- 下一步：OP review 後若同意，回覆「同意此書面規格，開始建立離線實作計畫」；該句只授權建立計畫，不授權 production／test edits 或 Word。
- 阻塞點：書面規格 review gate；failure evidence 與 missing-token diagnostics 尚未實作。

## 2026-08-19 LIST dynamic service-fee 4-day one-shot Word repro failed at PDF text QA

- 一句話現況：依 OP 精確授權只執行一次 `test_calibrated_master_renders_gate_v_day_counts[4]`；Word 成功產生部分 `LIST.docx`，但同次流程在 PDF required-text 檢查失敗，pytest 原文為 `ValueError: LIST QA PDF is missing required text` 與 `1 failed in 42.37s`，已遵守 no-retry 停止，不能宣稱 DOCX／PDF／PNG QA 通過。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`，working tree 原為乾淨的 `main...origin/main [ahead 76]`；doctor 確認 Word registry、configured pdftoppm、schema-2 calibration、master SHA 與 normalized structure 均為 `ok`。fresh QA root 是 `output/word-repro-service-fee-postfix-20260819-110511`；collect-only 原文為 `1 test collected in 0.65s`，只含 `[4]`，沒有 5／6／7／8／12，且 collect 前後 WINWORD 都是 0。
- 唯一實機結果：正式 selector 只呼叫一次，exit 1；WINWORD 前後均為 0。流程只保留 `day-004/LIST.docx`，32,651 bytes，SHA-256 `4572e79c7f2a4d504119cc353496937376f716be6097fa6a00a75189b8ab2437`；沒有正式 `LIST-qa.pdf`、PNG 或 `index.json`，因此 success-only artifact QA 未執行，也沒有第二次 Word 呼叫。
- 唯讀診斷：殘留 DOCX 的文字可讀到 `SYN-LIST-260901`、`JX820`、`JX821` 及完整「四天共新台幣 1,200 元」服務費正文；本次錯誤是 PDF inspection 的 aggregate required-text failure，臨時 PDF 已由流程清除，現有證據不足以安全判定究竟是哪個 PDF text token 缺失。沒有修改 production、tests、私人 master 或 calibration。
- Postflight：doctor 仍只有本次不使用的 ffmpeg warning；master 維持 36,262 bytes／SHA-256 `08b4393b8e7782f9f1425a4a265a4f2737cb1dec7f1813f1b1c2ede88daae468`，manifest 維持 3,096 bytes／SHA-256 `edf2300b7fecb34662482291bc1de37f2502e6feb4f54aec00895b0354d80593`，WINWORD 為 0。沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。
- 下一步：若要繼續，先另開一個不執行 Word的離線診斷／修正规格，讓失敗的暫存 PDF 文字或逐項 required token 能被保留為證據；修正與完整離線測試完成後，任何新的 Word repro 都必須重新取得一次性授權。
- 阻塞點：同次 PDF／PNG／index 未產出，4 天 Word 路徑目前仍未驗證成功；本次授權已消耗且不會重試。

## 2026-08-19 LIST dynamic service-fee notice offline implementation handoff

- 一句話現況：LIST generator 已離線升為 `list-word/4`，會依正整數 `product.day_count` 產生繁中天數與每人每日 300 元總額，以唯一 main-story exact body patch 寫入副本，並要求匯出 PDF 包含同一完整正文；完整離線驗證全綠，但 Word 實機尚未驗證。
- 開工證據：implementation baseline `ade857e09670acff3971c703fca62568cf031478`，`git pull --ff-only` 為 `Already up to date.`，working tree 乾淨，`RUN_BRIEFING_WORD_INTEGRATION` 為空，WINWORD baseline 0。
- Formatter／plan TDD：primary red 是 19 failures，原文核心為 `AttributeError: module 'travel_briefing.word_list' has no attribute 'format_list_service_fee_notice'` 與 `assert 3 == 4`；新增單一 NTD 300 authority、無常見天數白名單的繁中 place-value formatter、唯一 `service_fee_notice` typed patch與 plan schema 4後，19 targets轉綠；完整 `test_word_list.py` 在report slice完成後轉綠。
- Report TDD：synthetic report升 schema 4並新增 body count後，primary red為7 failures，核心為 `Word patch report does not match schema version 3`；strict reader／result升版後要求exact key set與 `patched_body_paragraph_count=1`，7 targets轉綠，schema 3／missing／bool／0／2／extra key均fail closed。
- Word adapter TDD：3個primary source-contract tests先因 `$WdMainTextStory`、bounded helpers與schema 4不存在而紅；新增唯一anchor candidate、完整source equality、outside-table、只退一個paragraph mark、bounded range assignment、SaveAs/reopen target與段落數重驗、10個safe codes及schema-4 report後轉綠。第一次子PowerShell parser command因外層變數展開而命令失敗，未改production；改用同程序AST parser後 `PARSER_ERROR_COUNT=0`。
- PDF authority TDD：backend primary先以actual `('SYN-OSA-260901', 'SY100')` 對預期三項tuple而紅；`workflow.py`改由同一 formatter把完整五天／1,500元正文加入 `required_text` 後，primary `1 passed`、完整 `test_local_backend.py` `3 passed`。
- Commits與範圍：`d902a1ad2a3b199948275e87068b9051561c713f`（plan／formatter／strict report）、`6103ce6e4ee431e4fd905adc8ea2400eeac71c4b`（bounded Word body patch）、`9552fa398bca0d1ffc34771e50a3a9165ef42ba4`（PDF required text）。對 baseline changed files精確為核准的三個 production與三個 unit test files；unchanged controls diff為零。
- 完整驗證：focused三檔與直接相關compatibility controls均到 `[100%]`，前後WINWORD 0；完整suite原文 `584 passed, 8 skipped in 41.40s`，另有 `COMPILEALL_OK`、`PARSER_ERROR_COUNT=0`、`GIT_DIFF_CHECK_OK`。forbidden addition scan clean、10個safe codes complete、changed-file scope與non-change audits通過。
- 版本邊界：generator `list-word/4`、plan schema 4、patch report schema 4；outer Word job schema 1、calibration schema 2／`list-calibration/2`、persisted `WordRenderEvidence` schema 3、QA index schema 2、package／workflow 0.2.1及歷史 `list-word/3` artifact fixtures不變。
- 誠實與範圍：沒有duration whitelist、date-derived fee、ReplaceAll、private path或OP/web override；沒有讀寫private master／calibration、啟動Word、產生DRAFT／DOCX／PDF／PNG、GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish或push。離線綠燈不能宣稱4天artifact已修好。
- 下一步：若OP要做實機驗證，回覆「同意只執行一次 4 天 post-fix Word repro；不跑其他天數；若成功，完成同次 DOCX／PDF／PNG QA；成功或失敗都不重試。」
- 阻塞點：新的4天Word artifact尚未生成與目視QA；本輪在離線handoff停止。

## 2026-08-19 LIST dynamic service-fee notice offline implementation plan review

- 一句話現況：OP 已核准 LIST 動態服務費正文書面規格；test-first 離線實作計畫已建立並完成自審，等待 OP 核准，尚未修改或執行 production／tests。
- 開工狀態：`git pull --ff-only` 為 `Already up to date.`，planning baseline 為 `6e3c27d3170e89597367931d0855e7e801a9c2f0`，working tree 原為乾淨的 `main...origin/main [ahead 71]`。重新核對核准規格、現行 plan／report／workflow seam、直接相關 tests、版本鏈與既有 `docs/plans` 慣例。
- 計畫文件：新增 `docs/plans/2026-08-19-list-service-fee-day-count-implementation-plan.md`，拆成 formatter／typed plan red→green、Python strict report red→green、PowerShell bounded main-story patch red→green、PDF required-text workflow red→green、focused／non-change、完整離線 suite 與 handoff 八個 tasks，規劃三個小型 implementation commits。
- 最小實作範圍：未來獲准後只改 `word_list.py`、`patch_list_template.ps1`、`workflow.py` 與對應的 `test_word_list.py`、`test_windows_word.py`、`test_local_backend.py`。`word_qa.py`、render adapter、calibration、template contract、models、兩個 integration tests、private master 與 installed runtime 均為 unchanged controls；若需跨出六檔立即停止 review。
- 契約與版本：`list-word/3` 升 `list-word/4`，patch plan／report schema 3 升 schema 4，新增唯一 typed `service_fee_notice` 與 `patched_body_paragraph_count=1`；outer job schema 1、calibration schema 2、persisted Word evidence schema 3、QA index schema 2、package／workflow `0.2.1` 不變。
- Test-first 與安全邊界：formatter 會覆蓋 1／4／5／6／7／8／10／11／12／20／21 及 1..366 deterministic loop，拒絕 bool／非正整數且不設常見天數白名單；PowerShell patch 必須 main-story-only、unique exact anchor、完整 source equality、outside-table、只排除一個 paragraph mark，SaveAs/reopen 後再驗證 target、段落數與 12 pt；PDF QA 使用同一 formatter 的完整正文作 required text。
- 自審：八個 tasks、三個 implementation commits、六個核准 implementation files、三項升版與五項 unchanged version contract 均一致；placeholder scan、fence／heading review 與 `git diff --check` 通過。計畫明列 primary red 的預期 failure、green commands、safe codes、non-change proof、完整 suite、compileall、static audit 與 no-Word stop point。
- 誠實與範圍：本輪只有 plan、spec status 與本 STATUS；沒有修改或執行 production／tests，沒有啟動 Word、讀寫 private master／calibration、產生 DRAFT／DOCX／PDF／PNG，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。4 天動態正文尚未經實作或 Word artifact 驗證。
- 下一步：OP 回覆「同意此實作計畫，開始離線實作」後才開始 Task 1 test edit；完整離線實作通過後，新的單次 4 天 Word repro 仍需另一個精確授權，成功或失敗都不重試。
- 阻塞點：離線實作計畫 review gate；`writing-plans` Skill 目前不在可用清單，因此依 repo 既有 plan 格式建立等價計畫，沒有藉此擴張授權。

## 2026-08-19 LIST dynamic service-fee notice design review

- 一句話現況：OP 已選定固定每人每天新台幣 300 元、由 `product.day_count` 計算總額並以中文天數顯示；完整離線書面規格已寫成並自審通過，等待 OP 審閱，尚未建立實作計畫或修改 production／tests。
- 開工與根因：`git pull --ff-only` 為 `Already up to date.`，baseline HEAD `a67e945`，working tree 原為乾淨的 `main...origin/main [ahead 70]`。唯讀 source 盤點確認固定「六天／1,800 元」不在 Python／PowerShell，而是 canonical master 保留的 main-story 正文；現行 schema-3 plan 只有 header paragraphs 與 table cells，沒有安全正文 locator。
- 方案與決策：比較受保護 body-paragraph patch、重校準 placeholder master、全文件取代三案；選定第一案。未來 schema 4／`list-word/4` plan 只允許一個 `service_fee_notice`，以唯一 anchor prefix、完整 source equality、outside-table 與 paragraph-mark boundary fail closed，SaveAs/reopen 後再驗證一次；不改 master、不使用 ReplaceAll。
- 資料規則：每日費率唯一常數為 300，天數唯一來源為正整數 `product.day_count`，總額只由乘法計算；中文數字 formatter 不設 4／5／6／7／8／12 白名單，也不新增最大旅遊天數。核准格式例如「四天共新台幣 1,200 元」與「十二天共新台幣 3,600 元」。
- 規格文件：新增 `docs/specs/2026-08-19-list-service-fee-day-count-design.md`，包含 observed defect、三方案、pure formatter、typed plan、main-story locator、bounded replace、post-reopen evidence、PDF required-text authority、安全錯誤碼、相容邊界、offline test matrix、future implementation files 與 acceptance criteria。
- 自審：placeholder scan 為 clean；schema 4／`list-word/4`／report schema 4 一致；1、4、10、12、21 天金額經 PowerShell 重算為 300／1,200／3,000／3,600／6,300；規格明確要求 1..366 deterministic loop 與更大正整數的 algorithm path，不使用 duration lookup table。`git diff --check` 通過。
- 範圍界線：只有 spec 與本 STATUS；沒有修改或執行 production／tests，沒有讀寫 private master／calibration、啟動 Word、產生 DOCX／PDF／PNG，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。
- 下一步：OP 審閱後若同意，回覆「同意此書面規格，開始建立離線實作計畫」；該句只授權建立計畫，不授權改 production／tests 或執行 Word。
- 阻塞點：書面規格 review gate；4 天 artifact 的固定 6 天服務費內容仍未修正。

## 2026-08-19 LIST exported-page authority 4-day post-fix Word repro and artifact QA

- 一句話現況：唯一一次 4 天 post-fix Word integration selector 已成功且三項版型規格（無 QR、除第一行外 12 pt、非標題 cell 無多餘 paragraph）均通過同次 DOCX／PDF／PNG QA；但人工內容 QA 發現 4 日團頁尾仍固定寫「六天共新台幣 1,800 元」，因此這份 synthetic artifact 不得宣稱可正式使用，且依 no-retry 約束沒有重跑。
- 前檢：`git pull --ff-only` 為 `Already up to date.`，HEAD `e48fe2a89e3c53076da05b3a3a9605929a6141e1`，working tree 乾淨。doctor 的 Word registry、configured pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure 均 `ok`；ffmpeg 是本案例不使用的唯一 warning。master 為 36,262 bytes／SHA-256 `08b4393b8e7782f9f1425a4a265a4f2737cb1dec7f1813f1b1c2ede88daae468`，manifest 為 3,096 bytes／SHA-256 `edf2300b7fecb34662482291bc1de37f2502e6feb4f54aec00895b0354d80593`，WINWORD baseline 是使用者既有的 1。
- Selector gate：全新且原為空的 QA root 是 `output/word-repro-page-authority-postfix-85cdddcdf9c24e0ea5e87306fc1fd12d`。collect-only 原文為 `1 test collected in 0.57s`，唯一 node 是 `test_calibrated_master_renders_gate_v_day_counts[4]`；collect 前後 WINWORD 均為 1，5／6／7／8／12 天沒有進入。
- 唯一正式 run：只呼叫一次上述 `[4]` selector並使用 `-x -vv`；原文為 `1 passed in 33.42s`、`WORD_REPRO_EXIT=0`。執行前後 WINWORD 均為 1，沒有重試。
- 同次 artifacts：`day-004/LIST.docx` 32,793 bytes／SHA-256 `42b3a0fec843fe4cd04ee670e5be7b9f1988a02ab1faf5b6f74365b3750128ec`；`LIST-qa.pdf` 119,928 bytes／SHA-256 `6e270f9c382b67feec2325347cc4ec48f852c968fa37b46964121b550729bf59`；`pages/page-001.png` 229,972 bytes／SHA-256 `ace08ae55b06f177b308a4a72ceb120738ec29157644c92d9b23eab76c0e567d`；schema-2 `index.json` 347 bytes／SHA-256 `6f68e47366b9a621628f09505e0ce9f45eba12282569fb8952c9b9a552d68b2e`。
- 結構／版型 QA：PDF 1 頁、A4 portrait `595.32 x 841.92 pt`、466 個 non-whitespace text characters、21 text blocks、image 0；PNG 為 `1241 x 1754`、約 150 DPI，index 的 page count／PNG hash／4 個 day-page mappings 全部一致。PDF span 只有標題 `日本精緻假期` 為 21.96 pt，其餘所有文字均為 12 pt。DOCX 是 4 tables、rows `4／3／5／1`、media／body drawing／header drawing 均 0、saved Pages 1；62 個非標題 cells 各只有 1 paragraph，唯一 4-paragraph cell 是原有 title block。逐頁原尺寸目視確認無 QR、首區自然使用完整寬度、無裁切／重疊／破表／缺字或可見多餘換行，4 天 row 都在第一頁。
- 新內容 blocker：PDF 明確包含固定字串「六天共新台幣 1,800 元」，沒有「四天共新台幣 1,200 元」。以程式計算 `4 * 300 = 1,200`；因此產品 `合成大阪4日` 與頁尾服務費說明矛盾。這個 blocker 不否定 exported-page authority fix 或三項版型修正，但會阻擋把 4 天 artifact 當成正式說明會資料。
- Postflight／範圍：doctor 再次確認 master hash、normalized structure、Word registry 與 pdftoppm 正常；master／manifest size、mtime、SHA-256 均未變，WINWORD 回到 1，process-scope opt-in 已清空。沒有修改 production／tests／私人 master／calibration，沒有第二次 Word、GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。
- 下一步：若 OP 要修正內容 blocker，先建立「依 `day_count` 動態產生服務費天數與總額，且保留未知費率 fail-closed」的離線書面規格；本輪授權已消耗，不再執行 Word。
- 阻塞點：4 日產品與固定 6 日／1,800 元頁尾文字矛盾；5／6／7／8／12 天實機仍未驗證。

## 2026-08-19 LIST exported-page authority offline implementation handoff

- 一句話現況：LIST QA 已離線改為以 PyMuPDF inspected PDF page count 控制 PNG set、QA index 與 final evidence；Word `computed_page_count` 只保留為正整數診斷，explicit independent expectation 仍 strict，完整離線驗證全綠，但 Word 實機尚未驗證。
- 開工證據：implementation baseline 為 `80dcb4f23723b3f61ee3f29923bfd7324f9351f3`，`git pull --ff-only` 為 `Already up to date.`，working tree 乾淨，`RUN_BRIEFING_WORD_INTEGRATION=0`，WINWORD baseline 是使用者既有的 1。
- QA red→green：新 synthetic seam 建立 render report 2／one-page PDF 1且不傳 expectation，先為 `F [100%]`／`ValueError: Word report and PDF LIST page count do not match`；最小修改 `word_qa.py` 後轉為 `. [100%]`。既有 explicit expected 2／PDF 1 control 仍為 `. [100%]`，兩者合跑 `.. [100%]`。
- Backend red→green：既有 composition test 保留 build statistic 2、QA artifact count 1，並新增 kwargs non-presence assertion；先為 `F [100%]`，精確顯示 `expected_page_count: 2` 仍存在。`workflow.py` 只移除該 kwarg 後轉為 `. [100%]`；三個 targets 合跑 `... [100%]`。
- 實作內容：`render_list_word_for_qa()` 先驗證 report／PDF bytes並完成 PDF inspection；只有 caller 明示 expectation 時才與 `inspection.page_count` 比較，通過後 artifact required count 一律取 inspected PDF。`ListWordQaResult.computed_page_count`、report/index schema、page map、date token、A4、content、image、publish 與 exclusive-output checks 不變。`LocalRenderBackend` 不再把 `built.computed_page_count` 傳成 expectation。
- Focused／non-change：兩個核准 test files 為 `...................... [100%]`；Word LIST、Windows adapter 與 synthetic workflow controls 最後為 `............................... [100%]`；PowerShell parser `PARSER_ERROR_COUNT=0`。`word_list.py`、兩個 Word PowerShell adapters、Gate V integration 對 baseline diff 為零，changed production／test files 精確為核准四檔。
- 完整驗證：`557 passed, 8 skipped in 45.89s`、compileall exit 0、`git diff --check` 通過；驗證後 WINWORD 仍為 1且 Word opt-in 仍為 0。沒有弱化、skip 或刪除 tests。
- Commits：implementation commit `499e2e11d9723eae09318e8affcd28ae25cd3c78`（`fix(briefing): trust exported LIST page count`）只含 `word_qa.py`、`workflow.py` 與兩個核准 tests；本段由緊接的本機 handoff 文件 commit 保存，hash 以 `git log` 為準。
- 範圍界線：沒有啟動 Word、讀寫 private master／calibration、產生 DRAFT／DOCX／正式 PDF／PNG、修改 installed runtime，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。離線綠燈不能宣稱 4 天 Word 已修好。
- 下一步：若要實機驗證，需新的明確授權「同意只執行一次 4 天 post-fix Word repro；不跑其他天數；若成功，完成同次 DOCX／PDF／PNG QA；成功或失敗都不重試。」
- 阻塞點：Word 實機與 artifacts 未驗證；本輪依核准計畫在離線 handoff 停止。

## 2026-08-19 LIST exported-page authority offline implementation plan review

- 一句話現況：OP 已核准 4 天 exported-page authority 書面規格；離線實作計畫已建立並等待 OP 核准，尚未修改或執行 production／tests。
- 開工狀態：`git pull --ff-only` 為 `Already up to date.`，planning baseline 為 `35fa408ff788abd5112b2d23e41044245d7892d7`，working tree 原為乾淨的 `main...origin/main [ahead 66]`。重新核對核准規格、現行 `LocalRenderBackend.render_word()`／`render_list_word_for_qa()`、兩個 unit test seams、既有 implementation-plan 慣例與 repo gates。
- 計畫文件：新增 `docs/plans/2026-08-19-list-four-day-page-count-mismatch-implementation-plan.md`，拆成 synthetic report 2／PDF 1 primary red、PDF-authority QA green、backend fake-expectation red／workflow green、focused＋unchanged controls、完整離線 suite／implementation commit、handoff 六個 tasks。
- Test-first 邊界：`test_word_qa.py` 新 regression 不傳 independent expectation，要求 inspected PDF 1 控制 one-page PNG/index，同時保留 `result.computed_page_count=2`；既有 explicit expected 2／PDF 1 mismatch test 必須繼續阻擋。`test_local_backend.py` 既有 composition test 會鎖定 build statistic 2 不得出現在 QA kwargs，final evidence 使用 QA page count 1。
- Production 範圍：未來獲准後只改 `word_qa.py` 的 page-count authority order／gate，以及從 `workflow.py` 移除 `expected_page_count=built.computed_page_count`。`word_list.py`、兩個 Word PowerShell adapters、Gate V integration、schema、formatting、master 與 calibration 全是 unchanged controls。
- 驗證與停止點：計畫要求兩個獨立 red→green slices、explicit expectation control、兩個 focused files、Word/LIST/workflow unchanged controls、PowerShell parser、baseline non-change comparison、完整離線 suite、compileall、WINWORD non-use 與 `git diff --check`；全綠才建立本機 implementation／handoff commits並停止。最近完整 suite `556 passed, 8 skipped` 只作趨勢參考，以未來實際輸出為準。
- 誠實邊界：本輪只有 plan、spec status 與 STATUS 文件；沒有修改或執行 production／tests，沒有啟動 Word、讀寫 private master／calibration、產生 DRAFT／DOCX／PDF／PNG，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。Word 成功仍未驗證。
- 下一步：OP 回覆「同意此實作計畫，開始離線實作」後才開始 Task 1 test edit。完整離線實作通過後，新的單次 4 天 Word repro 仍需另一個明確授權，不跑其他天數，成功或失敗都不重試。
- 阻塞點：離線實作計畫核准關卡。

## 2026-08-19 LIST 4-day exported-page authority diagnosis and design review

- 一句話現況：4 天 repro 的新 blocker 已離線收斂為「把 Word `ComputeStatistics=2` 的匯出前觀察誤當成獨立 `expected_page_count`」，而不是 4 天 patch plan 預先要求兩頁；已完成書面修正規格，等待 OP 審閱，尚未修改 production 或 tests。
- 開工與既有證據：`git pull --ff-only` 為 `Already up to date.`，基線 HEAD 為 `514da17aef3bd87f15e9945b7498752415d3e8f7`，working tree 原為乾淨。唯一既有 Word run 仍是 `1 failed in 35.45s`／`WORD_REPRO_EXIT=1`，`expected_page_count=2` 通過兩個 Word report check 後，PyMuPDF inspection 回傳非 2 頁並觸發 `Word report and PDF LIST page count do not match`；本輪沒有重跑 Word。
- 資料流根因：`patch_list_template.ps1` 的 `computed_page_count` 經 `ListWordBuildResult` 被 `LocalRenderBackend` 原封不動改名傳成 `expected_page_count`；`render_list_template.ps1` 又在 PDF 匯出前呼叫同一個 `ComputeStatistics`。兩個同源 Word 統計相等，不能證明匯出 PDF 頁數相等。
- Retained DOCX 唯讀證據：`docProps/app.xml Pages=1`，body paragraph 7、table 4、rows `4／3／5／1`、manual page break 0、last-rendered break 0、`pageBreakBefore` 0、section 1；daily table 是 1 header＋4 day rows，沒有結構性第二頁指令。由於暫存 PDF 已依失敗清理，實際 PDF=1 是由「PDF 非 2＋Word-authored saved metadata 1」支持的強推論，不冒充直接觀察。
- 離線 feedback loop：保留 DOCX 對 recorded expected 的 deterministic check 原文為 `RECORDED_EXPECTED_PAGE_COUNT=2`、`SAVED_DOCX_METADATA_PAGES=1`、`OFFLINE_PAGE_CONTRACT_MISMATCH=1` 並 exit 1；三個現有 focused contracts 為 `..... [100%]`，證明現有 tests 尚未涵蓋「Word statistic 2／有效 PDF 1／沒有獨立 expectation」的 seam。WINWORD 全程維持 baseline 1。
- 選定方案：以 PyMuPDF inspection 的匯出 PDF 頁數作 artifact authority；PDF=PNG set=QA index=`WordRenderEvidence.page_count`。Word patch／render `computed_page_count` 只保留為正整數診斷。`day_page_map` 與唯一 date token 仍必須在 PDF 指定頁精確匹配，所以不會用此修正掩蓋漏頁、錯頁或內容遺失；明示的真正 independent `expected_page_count` 仍維持 strict mismatch block。
- 書面規格：新增 `docs/specs/2026-08-19-list-four-day-page-count-mismatch-design.md`，記錄 observed／inferred 邊界、四個方案比較、被取代的單一 page-count clause、選定資料流、錯誤契約、red-then-green QA／backend regressions、unchanged controls 與四個 implementation files 的嚴格範圍。
- 誠實與範圍：本輪只讀 repo source、既有失敗 DOCX 的 OOXML、跑 5 個無 COM focused tests並寫文件；沒有修改或執行 production／tests，沒有啟動 Word、讀寫 private master／calibration、產生 DRAFT／PDF／PNG，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。修正尚未實作，Word 成功仍未驗證。
- 下一步：OP 審閱後若同意，回覆「同意此書面規格，開始建立離線實作計畫」；該句只授權建立計畫，不授權改 production／tests 或執行 Word。
- 阻塞點：書面規格審閱關卡；唯一 Word run 授權已消耗，PDF inspection 的精確頁數沒有 retained artifact，未來實機驗證仍需另一個明確的一次性 4 天授權。

## 2026-08-18 LIST direct-range post-fix 4-day repro crosses highlight and fails page-count QA

- 一句話現況：唯一一次獲准的 4 天 post-fix Word repro 已越過 T4/R1/C2 full-cell highlight blocker並產生 `LIST.docx`，但在 Word report 與 PDF inspection 的頁數一致性檢查失敗；因此沒有完成 DOCX／PDF／PNG QA，也不得重試。
- 前檢：開工 `git pull --ff-only` 為 `Already up to date.`，HEAD 為 `043e9a23623a75b35b2a380ae86ed9a9172b43e9`，working tree 乾淨。private master、manifest、pdftoppm 都存在；master 為 36,262 bytes／SHA-256 `08b4393b8e7782f9f1425a4a265a4f2737cb1dec7f1813f1b1c2ede88daae468`，manifest 為 3,096 bytes／SHA-256 `edf2300b7fecb34662482291bc1de37f2502e6feb4f54aec00895b0354d80593`，WINWORD baseline 是使用者既有的 1。
- Selector gate：全新 QA root `C:\Users\cance\projects\easytravel-cowell-agent\output\word-repro-direct-range-postfix-8c7371491c99459d9c0b83e008165cf2` 建立後為空；collect-only 原文為 `1 test collected in 0.95s`，唯一 node 是 `test_calibrated_master_renders_gate_v_day_counts[4]`，collect 後 WINWORD 仍為 1。
- 唯一正式 run：只呼叫一次上述 `[4]` selector並使用 `-x -vv`；5／6／7／8／12 天完全未進入。原文為 `1 failed in 35.45s`、`WORD_REPRO_EXIT=1`，依 OP 約束沒有重試。
- 新 blocker：`backend.render_word` 已完成 patch並進入 `render_list_word_for_qa`。Word report 的 `computed_page_count` 通過 `expected_page_count=2` check，接著 `inspect_list_pdf` 回傳不同頁數，最終為 `ValueError: Word report and PDF LIST page count do not match`。exception 沒有揭露 PDF inspection 的實際頁數，且 temporary PDF 隨失敗清理；不得以第二次 Word run 補證。
- Artifact／QA：QA root 只有 `day-004` directory 與 32,768-byte `day-004\LIST.docx`；DOCX 1、PDF 0、PNG 0、index 0。因正式 run 非零，不符合「若成功才完成同次 QA」條件，沒有另行 render、開啟或交付該 DOCX，也沒有用替代工具補產 PDF／PNG。
- Postflight：WINWORD 回到 baseline 1；private master／manifest 的大小與 SHA-256 完全未變。git working tree 在寫入本 STATUS 前仍乾淨，沒有修改 production 或 tests。
- 判讀：實機已支持 one-retreat direct path 能跨過先前 T4/R1/C2 blocker；目前尚不能宣稱 4 天 Word artifact 合格，因 pagination report 與實際 PDF page count 矛盾。這是新的最早失敗邊界，不是視覺 QA 結果。
- 下一步：若要繼續，先另行核准 4 天 `expected_page_count=2`／PDF inspection mismatch 的純離線診斷與書面修正規格；未核准前不修改 production／tests，也不再執行 Word。沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。
- 阻塞點：本次唯一 Word repro 授權已消耗且失敗；PDF inspection 實際頁數未知，DOCX／PDF／PNG QA 未完成。

## 2026-08-18 LIST full-cell direct range offline implementation handoff

- 一句話現況：`Set-TokenHighlight` 的 exact full-cell direct path 已離線改為 duplicate 只退一個自己的 `End` position，並移除把 cell 尾端兩個文字碼點錯當成兩個 Range positions 的 `Get-ListVisibleRangeEnd`；完整離線驗證全綠，但 Word 實機仍未驗證。
- TDD 證據：implementation baseline 為 `ad791d0dd15d99c986db5dee798a702d40b14e86`，開工 `git pull --ff-only` 為 `Already up to date.`。先只替換 primary regression，red 原文為 `.F [100%]`：content-shape control 通過，adapter 因 helper 仍存在而失敗。最小 production change 後同一 command 為 `.. [100%]`；對齊 preservation contracts 後五個 target tests 為 `..... [100%]`。
- 實作內容：production 完整移除唯一 caller 的 helper；direct duplicate 只計算一次 `$directEnd = [int]$visibleRange.End - 1`，以 `LIST_HIGHLIGHT_RANGE_INVALID` fail closed 後直接指定 `End`，再沿用 case-sensitive equality／黃色／`$matches = 1`。embedded／repeated Find boundary、settings、counter、cursor、caller-bound safe codes 與 cleanup 均未改。implementation commit 為 `7cb8c0b`。
- 無 COM／focused 驗證：compound-marker model 為 paragraph selected span 7、cell text terminator code points 2、cell range terminator span 1、removed algorithm span 6、selected span 7、over-retreat 1，前後 WINWORD 都是 1；兩個 focused files 的 84 tests 全綠，PowerShell parser 為 `PARSER_ERROR_COUNT=0`。
- Non-change 證據：第一次唯讀 wrapper 因 PowerShell `.Split()` 把 delimiter 當字元集合，將 direct／Find count 誤報 0 並 exit 1；未改檔。改用 `IndexOf`／`Substring` 後重跑，得到 plan builder、`test_word_list.py`、header caller、cell caller 全部 unchanged，helper definition／call 0、direct retreat／Find boundary 各 1、coordinate／forbidden 0、changed files 精確為核准兩檔，`GIT_DIFF_CHECK_OK`。
- 完整驗證：`556 passed, 8 skipped in 25.98s`、`COMPILEALL_OK`、`GIT_DIFF_CHECK_OK`；validation 後 WINWORD count 仍為 1。沒有新增 skip、弱化或刪除 tests。
- 範圍界線：沒有啟動 Word、讀寫私人 master／calibration／DRAFT、產生 DOCX／PDF／PNG、GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push；沒有修改內容、schema、QR policy、12 pt、paragraph、pagination、layout 或 installed runtime。
- 下一步：若要確認 blocker 是否解除，需要新的明確授權，只執行一次 4 天 post-fix Word repro；不跑其他天數，成功或失敗都不重試。只有成功產生同次 DOCX／PDF／PNG 後才能完成內容與視覺 QA。
- 阻塞點：Word 實機與 artifacts 未驗證；本輪依核准計畫在離線 handoff 停止。

## 2026-08-18 LIST full-cell direct range offline implementation plan review

- 一句話現況：OP 已核准 T4/R1/C2 full-cell direct range 書面規格；離線實作計畫已建立並等待 OP 核准，尚未修改 production 或 tests。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`，working tree 原為乾淨的 `main...origin/main [ahead 61]`。重新核對 commit `642a1e2` 的書面規格、現行 `Get-ListVisibleRangeEnd`／`Set-TokenHighlight`／`Set-ListCell`、三個 adapter tests、既有 content-shape control 與前一輪 plan 格式；`CONTEXT.md` 不存在。
- 計畫文件：新增 `docs/plans/2026-08-18-list-full-cell-direct-range-implementation-plan.md`，拆成 one-retreat red regression、最小 helper removal／direct range change、target green／無 COM compound-marker model、focused parser／non-change proof、完整 suite／implementation commit 與 handoff 六個 tasks。
- Test seam：只修改 `tests/unit/travel_briefing/test_windows_word.py` 的已核准 adapter source contracts；`tests/unit/travel_briefing/test_word_list.py` 只執行既有 5 embedded＋2 direct content-shape control，不修改。red 必須由 helper 尚在且 direct duplicate 尚未採單次 `End - 1` 造成；`Set-ListCell` 的 live-proven post-range assertion 是 unchanged control。
- Production 範圍：只修改 `scripts/briefing/patch_list_template.ps1`，移除唯一 caller 的 `Get-ListVisibleRangeEnd`；direct duplicate 只退一個自己的 `End`、先做 `LIST_HIGHLIGHT_RANGE_INVALID` safe check，再沿用 exact comparison／黃色／match。embedded／repeated Find boundary、settings、cursor、safe-code 與 cleanup 不改。
- 驗證與停止點：計畫要求 target red→green、無 COM compound-marker model、兩個 focused files、PowerShell parser、完整 offline suite、`compileall`、static／non-change checks 與 `git diff --check`；全綠後建立本機 implementation／handoff commits並停止。最近完整 suite 基線 `556 passed, 8 skipped` 只供參考，以未來實際輸出為準。
- 誠實邊界：本輪只寫規格狀態、計畫與 STATUS；沒有修改或執行 production／tests，沒有啟動 Word、讀寫私人 master／calibration、產生 DRAFT／DOCX／PDF／PNG，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。Word 成功仍未驗證。
- 下一步：OP 回覆「同意此實作計畫，開始離線實作」後才開始 Task 1 test edit。完整離線實作完成後，新的單次 4 天 Word repro 仍需另一個明確授權；不跑其他天數，成功或失敗都不重試。
- 阻塞點：離線實作計畫核准關卡。

## 2026-08-18 LIST full-cell direct range offline diagnosis and design review

- 一句話現況：T4/R1/C2 full-cell direct path 已離線縮小為 `Get-ListVisibleRangeEnd` 把 cell 尾端 `U+000D U+0007` 的兩個文字碼點誤當成兩個 Word Range 位置，令 direct duplicate 比已通過實機前置斷言的 `End - 1` 多退一格；已完成書面修正規格，等待 OP 審閱，尚未修改 production 或 tests。
- 實機既有證據：唯一一次 boundary-split 4 天 repro 已通過五個 embedded highlight cases，然後失敗於第一個 full-cell token `LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2`，原文為 `WORD_GENERATION_FAILED`／HRESULT `-2146233087`／return code 30／stage `run-action`／`1 failed in 23.37s`。同一 execution 在進入 highlight 前，`Set-ListCell` 對同一格的 duplicate 執行 `End - 1` 後已精確匹配 `Patch.text`，且該格 `Patch.text == Patch.highlight_text == WAITING_FOR_OP`。
- 離線診斷：現行 helper 依 `Range.Text` 尾端碼點數把 cell direct boundary 算成有效的 `End - 2`，會少掉一個 visible token 位置；無 COM compound-marker model 輸出 `CELL_TEXT_TERMINATOR_CODEPOINTS=2`、`CELL_RANGE_TERMINATOR_SPAN=1`、`CELL_CURRENT_VISIBLE_SPAN=6`、`CELL_EXPECTED_VISIBLE_SPAN=7`、`CELL_OVER_RETREAT=1`。模型前後 WINWORD 均為 1；cell marker 的 range span 來自前述實機 invariant，不是本輪新 Word probe。
- 測試缺口：現行四個相關離線 tests 仍為 `.... [100%]`，表示它們把錯誤的文字碼點至 Range 座標轉換當成契約，無法攔截這次實機矛盾；未以弱化、skip 或刪除測試方式處理。
- 選定方案：移除只有一個 production caller 的 `Get-ListVisibleRangeEnd`；direct duplicate 只退一個自己的 `End` 位置，先保留 `LIST_HIGHLIGHT_RANGE_INVALID` 安全檢查，再做既有 case-sensitive exact equality、黃色 highlight 與 `$matches = 1`。embedded／repeated Find 的 `$findBoundary = [int]$Range.End - 1`、settings、cursor、caller-bound safe codes 與 cleanup 全部不變，不新增 T4 座標特例。
- 書面規格：`docs/specs/2026-08-18-list-full-cell-direct-range-design.md` 記錄 evidence chain、四個方案比較、選定 source shape、錯誤與相容性契約、未來 red-then-green regression、完整離線驗證及單次 Word 關卡。
- 誠實邊界：本輪沒有啟動 Word、沒有重跑已消耗的 repro、沒有讀寫私人 master／calibration，也沒有修改或執行 production／tests、產生 DRAFT／DOCX／PDF／PNG、GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。修法能否跨過 T4/R1/C2 仍未經 Word 驗證。
- 下一步：OP 回覆「同意此書面規格，開始建立離線實作計畫」後，只建立離線實作計畫；那仍不授權修改程式或 tests。未來完成並核准實作後，新的單次 4 天 Word repro 仍需另一個明確授權，成功或失敗都不重試。
- 阻塞點：書面規格審閱關卡；Word 成功仍未驗證。

## 2026-08-18 LIST boundary-split post-fix 4-day repro returns to full-cell blocker

- 一句話現況：唯一一次獲准的 4 天 post-fix Word repro 已越過先前回歸的 T1 embedded highlights，但仍失敗於第一個 full-cell token `LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2`；因此 boundary split 的 embedded 路徑獲得實機支持，full-cell direct path 仍未成功，也沒有可做視覺 QA 的 artifacts。
- 前檢：開工 `git pull --ff-only` 為 `Already up to date.`；doctor 顯示 Word registry、configured pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure 均 `ok`，唯一 warning 是本測試不使用的 ffmpeg。collect-only 原文為 `1 test collected`，唯一 node 是 `test_calibrated_master_renders_gate_v_day_counts[4]`；WINWORD baseline 為使用者既有的 1。
- 唯一正式 run：只呼叫一次上述 `[4]` selector 並使用 `-x`，5／6／7／8／12 天完全未進入。原文為 `1 failed in 23.37s`、`WORD_REPRO_EXIT=1`；adapter evidence 為 `WORD_GENERATION_FAILED`／`LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2`／HRESULT `-2146233087`／return code 30／stage `run-action`。依 OP 約束沒有重試。
- Artifact／QA：同次 QA root `C:\Users\cance\AppData\Local\Temp\easytravel-word-boundary-split-postfix-5d25728cc4854b5c80c0e518d0ced685` 只有空的 `day-004` directory，`QA_ENTRY_COUNT=1`、`QA_FILE_COUNT=0`、DOCX／PDF／PNG 均為 0。因 run 未成功，未進入成功條件下的文件／圖片視覺 QA。
- Postflight：WINWORD 回到 baseline 1；doctor 再次確認 master hash、normalized structure、schema-2 calibration、Word registry 與 pdftoppm 均正常。沒有修改私人 master／calibration、production 或 tests。
- 判讀：實機 execution order 已重新跨過五個 embedded cases，表示 `$findBoundary = End - 1` 至少消除了 T1/R2/C2 回歸；流程回到修正前既有的 T4/R1/C2 full-cell blocker。這次結果沒有證明 direct visible-range highlight 為何未記錄 match，不能再靠同一授權探測或重跑。
- 下一步：若要繼續，先另行核准 T4/R1/C2 full-cell direct path 的純離線診斷與書面修正規格；未核准前不修改 production／tests，也不再執行 Word。沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。

## 2026-08-18 LIST embedded Find boundary split offline implementation handoff

- 一句話現況：`Set-TokenHighlight` 已離線分成 `$visibleBoundary` exact/direct path 與 `$findBoundary = [int]$Range.End - 1` embedded／repeated Find path；完整離線驗證全綠，但 Word 實機仍未驗證。
- TDD 證據：基線 `433c545712538ec6c5c731fa8fdc6ee84e5d`，開工 `git pull --ff-only` 為 `Already up to date.`。先只改兩個 source-contract tests，target run 原文為 `..FF [100%]`；兩個 controls 通過，另兩個 tests 都因新 boundary substring 尚不存在而 `ValueError: substring not found`。最小 production change 後相同 command 為 `.... [100%]`。
- 實作內容：`scripts/briefing/patch_list_template.ps1` 保留 `Get-ListVisibleRangeEnd`，exact full-cell visible duplicate 只用 `$visibleBoundary`；embedded loop 與 search range 只用 `$findBoundary`。`tests/unit/travel_briefing/test_windows_word.py` 明確鎖定兩條 boundary、保留 Find／cursor／safe-code／cleanup assertions，並禁止 shared `$boundary` 與 coordinate special case。implementation commit 為 `6e78c04`。
- 離線驗證：無 COM model 為 `PARAGRAPH_LEGACY_MINUS_VISIBLE=0`、`CELL_LEGACY_MINUS_VISIBLE=1`、`PROPOSED_FIND_COUNT=5`、`PROPOSED_DIRECT_COUNT=2`、`REPEATED_TOKEN_MAX_OCCURRENCES=2`，前後 WINWORD 都是 1；兩個 focused files 的 84 tests 全綠；parser 為 `PARSER_ERROR_COUNT=0`；完整 suite 為 `556 passed, 8 skipped in 32.86s`；`COMPILEALL_OK`、`GIT_DIFF_CHECK_OK`。
- 範圍證明：`PLAN_BUILDER_UNCHANGED=True`、`TEST_WORD_LIST_UNCHANGED=True`、`VISIBLE_HELPER_UNCHANGED=True`、`HEADER_CALLER_UNCHANGED=True`、`CELL_CALLER_UNCHANGED=True`、`CHANGED_FILE_COUNT=2`。沒有修改 schema、內容、QR policy、12 pt、paragraph、pagination、layout、私人 master、calibration、DRAFT 或 installed runtime。
- 下一步：若要確認 blocker 是否實際解除，需要新的明確授權，只執行一次 4 天 post-fix Word repro；不跑其他天數，成功或失敗都不重試。只有成功產生同次 DOCX／PDF／PNG 後才能做內容與視覺 QA。
- 阻塞點：本輪沒有 Word 授權，因此不得把離線綠燈宣稱為 Word 已修好；沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。

## 2026-08-18 LIST embedded Find boundary offline implementation plan review

- 一句話現況：OP 已核准 embedded Find boundary split 書面規格；離線實作計畫已建立並等待 OP 核准，尚未修改 production 或 tests。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；重新核對 `08647d3` 規格、現行 `Set-TokenHighlight`、既有 content-shape control 與兩個錯誤接受 shared boundary 的 source-contract tests。新增 `docs/plans/2026-08-18-list-embedded-find-boundary-implementation-plan.md`，拆成 test-first red、最小兩變數 source change、target green、無 COM boundary model、focused/parser/non-change、完整 suite 與 handoff 六個 tasks。
- 計畫選擇：只修改 `tests/unit/travel_briefing/test_windows_word.py` 與 `scripts/briefing/patch_list_template.ps1`；既有 `test_word_list.py` 的 5 embedded＋2 full-cell control 僅執行、不修改。`$visibleBoundary` 專供 exact/direct path，`$findBoundary = [int]$Range.End - 1` 專供 embedded／repeated Find；不新增 helper、不寫死座標、不改 caller／schema／formatting。
- 誠實邊界：本輪只有文件；沒有修改或執行 production/tests，沒有啟動 Word、讀寫私人 master／calibration、產生 DOCX／PDF／PNG，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。Word 成功仍未驗證。
- 下一步：OP 核准本計畫後才開始離線 TDD；完整離線驗證通過即停止。其後若要驗證實機，仍需另一個明確的一次性 4 天 Word 授權，不跑其他天數，成功或失敗都不重試。
- 阻塞點：離線實作計畫核准關卡。

## 2026-08-18 LIST embedded Find boundary offline diagnosis and design review

- 一句話現況：T1/R2/C2 回歸已離線縮小為 full-cell 修正把 terminator-aware visible boundary 同時套到 embedded Word Find；已完成 boundary split 書面規格，等待 OP 審閱，尚未修改 production 或 tests。
- 這次做了什麼：先執行 `git pull --ff-only`，結果為 `Already up to date.`；比較 full-cell 修正前後的 `Set-TokenHighlight`，確認先前實機已通過的 embedded Find boundary 由 `[int]$Range.End - 1` 改成 `Get-ListVisibleRangeEnd`。現有三個針對性離線測試仍輸出 `... [100%]`，因此確認 source-contract test 沒有區分 direct visible boundary 與 embedded Find boundary。無 COM model 證明 paragraph 的兩種 boundary 差值為 0、cell 差值為 1，4 天 plan 仍應分流為 5 個 embedded Find 與 2 個 full-cell direct cases。新增 `docs/specs/2026-08-18-list-embedded-find-boundary-design.md`，選定 `$visibleBoundary` 只供 exact/direct path、`$findBoundary = [int]$Range.End - 1` 只供 embedded Find；不寫死座標。
- 誠實邊界：本輪沒有啟動 Word、沒有重跑已消耗的一次性 repro、沒有讀寫私人 master／calibration、沒有產生 DOCX／PDF／PNG，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 push。根因目前仍是由實機前後故障位置與離線差分支持的最佳推論，不是新的 Word 實證。
- 下一步：OP 審閱並同意書面規格後，才建立離線實作計畫；計畫核准前不修改 PowerShell 或 tests。未來若完成離線修正，仍須另一個明確的一次性 4 天 Word 授權才能驗證，成功或失敗都不重試。
- 阻塞點：書面規格審閱關卡；Word 成功仍未驗證。

## 2026-08-18 LIST full-cell post-fix 4-day repro regresses first embedded highlight

- 一句話現況：獲准的唯一一次 4 天 post-fix Word repro 已失敗於 `LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T1_R2_C2`；這是 execution order 的第一個 embedded token cell，流程尚未到 T4/R1/C2，因此 full-cell direct path 未獲實機驗證，也沒有 DOCX／PDF／PNG 可供視覺 QA。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`。不啟動 Word 的前檢確認 private master／manifest hash、normalized structure、pdftoppm 與 Word COM registry 均正常；第一次 collect-only 的自訂文字計數器因 `-q` 輸出形狀不同而以 `SELECTOR_COUNT_CHANGED` 停止，未執行 test 或 Word。隨後只做 collect-only `-vv`，原文為 `1 test collected`，精確 selector 是 `test_calibrated_master_renders_gate_v_day_counts[4]`。正式 integration pytest 只呼叫一次且使用 `-x`；5／6／7／8／12 天完全未進入。
- 驗證：唯一正式 run 原文為 `1 failed in 10.44s`、`WORD_REPRO_EXIT=1`；adapter evidence 是 `WORD_GENERATION_FAILED`／`LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T1_R2_C2`／HRESULT `-2146233087`／return code 30／stage `run-action`。QA root `C:\Users\cance\AppData\Local\Temp\easytravel-word-fullcell-postfix-d2b083b7230c4c9da081be41961f8917` 只有空的 `day-004` directory，`QA_ENTRY_COUNT=1`、`QA_FILE_COUNT=0`。
- 判讀：上一個實機版本曾越過全部 5 個 embedded cells 才停在 T4/R1/C2；本次唯一與此路徑直接相關的變更，是 embedded Find boundary 也從原本 cell `End - 1` 改用排除 CR／BEL 的 visible end。目前最強證據是 terminator-aware boundary 不適合既有 embedded Word Find；這仍是對單次結果與 source diff 的推論，不是另一次 Word probe，且 direct full-cell branch 本次根本未到達。
- 事後狀態：WINWORD 回到 baseline 1；private `LIST-master.docx` 維持 36,262 bytes／SHA-256 `08b4393b8e7782f9f1425a4a265a4f2737cb1dec7f1813f1b1c2ede88daae468`，manifest 維持 3,096 bytes／SHA-256 `edf2300b7fecb34662482291bc1de37f2502e6feb4f54aec00895b0354d80593`，normalized fingerprint 維持 `c5786b598f981789a5dc856129d11435bc2e9ab9de665a7f1b5b5008f2e1cd0a`。
- 下一步：若要繼續，先另行核准 T1/R2/C2 embedded Find boundary 的純離線診斷與書面修正規格，評估 full-cell direct comparison 使用 visible range、embedded Find 保留原 boundary 的最小分流；未核准前不修改 production／tests。任何新的 Word repro 仍需另一個單次明確授權。
- 阻塞點：本次唯一 Word repro 授權已消耗且失敗，不得重跑。沒有修改 production／tests 或私人 master／calibration，沒有 GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST full-cell highlight offline implementation handoff

- 一句話現況：full-cell highlight 已離線改為 terminator-aware visible range 的 direct yellow path；embedded／repeated tokens 保留既有 Word Find／cursor loop。完整離線 suite 全綠，但私人 master 的 Word 實機結果仍未驗證。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`。先確認單元 `draft(4)` 只有 6 個 highlight cells，而實際 Word integration repro 使用全部 OP fields 未確認的 synthetic draft，才是已診斷的 5 embedded＋2 full-cell cases；因此只校正 regression fixture，不改核准設計。production 在 `scripts/briefing/patch_list_template.ps1` 新增純 range-like `Get-ListVisibleRangeEnd`，只排除尾端 CR／BEL；`Set-TokenHighlight` 對 exact full-cell token 直接套 `$WdYellow`，其餘才進既有 Find loop。implementation commit 是 `a7cd518`。
- TDD 證據：初始 target run 原文為 `.FF`，即 content-shape control 通過、兩個 adapter tests 失敗；失敗分別是 `Get-ListVisibleRangeEnd` 不存在的 `IndexError` 與 direct statements 不存在的 `ValueError`。最小實作後相同三個 tests 輸出 `... [100%]`／exit 0。
- 離線驗證：無 COM helper probe 輸出 `VISIBLE_RANGE_CASES=5`、`VISIBLE_RANGE_INVALID_CASES=2`、`VISIBLE_RANGE_ERROR=LIST_HIGHLIGHT_RANGE_INVALID`，且 `WINWORD_COUNT_BEFORE=1`／`WINWORD_COUNT_AFTER=1`。兩個 focused files 為 `84 tests collected in 0.13s` 且執行 exit 0；PowerShell parser 為 `PARSER_ERROR_COUNT=0`；完整 suite 為 `556 passed, 8 skipped in 24.49s`；`COMPILEALL_OK`、`git diff --check 880a0cf..HEAD` 與 commit check 均通過。source comparison 為 `HEADER_CALLER_UNCHANGED=True`、`CELL_CALLER_UNCHANGED=True`。
- 範圍證明：未修改輸出內容、schema、QR、12 pt、paragraph、pagination、caller safe-code、私人 master、calibration 或 installed runtime。沒有執行 JobPath、Word repro、DOCX／PDF／PNG、GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 public remote push；完成 handoff commit 後 `main` 預期為 `origin/main [ahead 54]`。
- 下一步：若要實機驗收，需新的明確授權，只執行一次 4 天 post-fix Word repro；不跑其他天數，失敗不重試。成功後才可檢查同次 DOCX／PDF／PNG 的內容、QR removal、12 pt、尾端空白行與分頁視覺契約。
- 阻塞點：本回合依核准計畫在完整離線驗證後停止。full-cell direct path 是否已跨過私人 master 的 T4/R1/C2 仍屬未驗證，不能把離線綠燈宣稱為 Word 實機成功。

## 2026-08-18 LIST full-cell highlight offline implementation plan review

- 一句話現況：OP 已核准 T4/R1/C2 full-cell highlight 書面規格；離線實作計畫已建立，明定 terminator-aware visible range、full-cell direct yellow path 與 embedded/repeated Find 保留契約，目前等待 OP 核准計畫，尚未修改 PowerShell／tests。
- 這次做了什麼：`git pull --ff-only` 為 `Already up to date.`；將設計狀態更新為 OP 已核准，並新增 `docs/plans/2026-08-18-list-full-cell-highlight-implementation-plan.md`。計畫拆成 content-shape／adapter red tests、最小 helper／direct path、無 COM probe、focused parser／non-change proof、完整 suite 與 handoff 六個 tasks。
- 驗證設計：先鎖定 4 天 plan 的 5 個 embedded＋2 個 full-cell cases；修正前預期 plan control 通過、兩個 adapter regressions 失敗。最小實作只讓 exact full-cell token bypass Word Find，embedded 與 repeated token 繼續使用既有 Find／cursor loop；再以 synthetic range probe 證明只排除尾端 CR／BEL。
- 下一步：OP 審閱並回覆「同意此實作計畫，開始離線實作」後，才可修改 `patch_list_template.ps1` 與兩個核准 test files；完整離線驗證通過後停止。
- 阻塞點：離線實作計畫核准關卡尚未通過；本次沒有修改 production source／tests，沒有 Word、私人 master／calibration、DRAFT、GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST T4/R1/C2 full-cell highlight offline diagnosis and design review

- 一句話現況：T4/R1/C2 已離線縮小為第一個「整格 visible text 完全等於 highlight token」的 ordinary cell；最有證據支持的原因是 cell Range 固定 `End - 1` 只排除 `U+0007`、仍把 terminal `U+000D` 留在 Word Find range。terminator-aware visible range＋full-cell direct highlight 書面設計已由 OP 核准；尚未改 production／tests。
- 這次做了什麼：`git pull --ff-only` 為 `Already up to date.`。追蹤 4 天 synthetic plan、`Set-ListCell` post-write assertion、`Set-TokenHighlight` 與 patch 執行順序；7 個 highlighted cells 中前 5 個都是 embedded，T4/R1/C2、C3 才是唯二 full-cell，且 target text/token code points 完全相同。新增 `docs/specs/2026-08-18-list-full-cell-highlight-design.md`，比較三個修法並選定不綁座標的 full-cell direct path。
- 診斷證據：boundary model 顯示 paragraph 的 `End - 1` 會正確去掉唯一 CR，但 cell 的 `End - 1` 仍留下 CR；selected-path probe 為 `DIRECT_COUNT=2`／`FIND_COUNT=5`，既有 T1/R2/C3 兩次 token 仍保留 Find loop。私人 master 只做唯讀 OOXML 結構檢查：T4/R1/C2、C3 都是兩個空 paragraph，排除 width／revision attributes 後 normalized XML 完全相同；實際 Word failure 前的 write-time assertion 已證明 output cell 是一個 paragraph 且 visible text 等於 patch text。
- 誠實界線：這是目前證據最支持的根因推論，不是 Word live proof。使用者禁止本回合執行 Word，因此沒有重跑 repro、沒有 COM instrumentation，也不能宣稱修法已越過 T4/R1/C2。
- 設計摘要：新增只讀 `Get-ListVisibleRangeEnd`，只剝除尾端 `U+000D`／`U+0007`；`Set-TokenHighlight` 對 exact full-cell token 直接將 visible duplicate 套黃色，embedded token 才走既有 Find／cursor loop。錯誤固定為安全碼，不改 caller safe code、schema、內容、QR、12 pt、paragraph、pagination、master 或 calibration contract。
- 下一步：依已核准規格建立離線實作計畫，待 OP 另行核准計畫後才修改 PowerShell／tests。
- 阻塞點：書面規格已核准，但離線實作計畫仍是獨立關卡；本次沒有啟動 Word、沒有修改私人 master／calibration 或既有 DRAFT，也沒有 GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST highlight post-fix 4-day repro localizes guide-name cell

- 一句話現況：獲准的唯一一次 4 天 post-fix Word repro 已把 generic highlight blocker 精確定位為 `LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2`；這是 table 4 的日本聯絡人／緊急聯絡人姓名 cell。依約沒有重試、沒有跑其他天數，也沒有 DOCX／PDF／PNG 可供視覺驗收。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；唯讀 doctor 確認 Word COM、pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure 均正常，唯一 warning 是本測試不使用的 ffmpeg。selector collect-only 精確為 `1 test collected`，WINWORD baseline 是使用者原本的 1。正式執行只選 `test_calibrated_master_renders_gate_v_day_counts[4]`、使用全新 OS temp QA root 與 `-x`；5／6／7／8／12 天完全未進入。
- 驗證：pytest 原始結果為 `1 failed`；adapter evidence 是 `WORD_GENERATION_FAILED`／`LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2`／HRESULT `-2146233087`／return code 30／stage `run-action`，外層 `WORD_REPRO_EXIT=1`。QA root `C:\Users\cance\AppData\Local\Temp\easytravel-word-highlight-postfix-05265b8976c648d1b51fc0a8730c70ce` 只有空的 `day-004` directory，`QA_ENTRY_COUNT=1`，沒有可渲染或交付的 artifact。
- 定位結論：離線 source mapping 證明 `_build_guide_cells` 以 `CellPatch(4, 1, 2, ...)` 寫入 `emergency_contact_name`；synthetic draft 未確認該 OP 欄位時，cell text 與 highlight token 都是固定 `WAITING_FOR_OP`。本次證據只證明 Word Find 在這個 full-cell token 路徑回報 zero match，尚未證明原因或修法。
- 事後狀態：WINWORD count 回到 baseline 1。doctor 再確認 `master_sha256_matches: true` 與 normalized structure fingerprint 正常；`LIST-master.docx` 維持 36,262 bytes／SHA-256 `08B4393B8E7782F9F1425A4A265A4F2737CB1DEC7F1813F1B1C2EDE88DAAE468`，manifest 維持 3,096 bytes／SHA-256 `EDF2300B7FECB34662482291BC1DE37F2502E6FEB4F54AEC00895B0354D80593`，mtime 均仍為 2026-08-17 17:25:55。
- 下一步：若要繼續，先離線診斷 T4/R1/C2 的 full-cell token Range boundary／Find 行為，提出最小修正與 regression；任何新的 Word repro 都需要另一個單次明確授權。
- 阻塞點：本次唯一 Word repro 授權已消耗且失敗，不得重跑。沒有修改程式或私人 master／calibration，沒有 GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST highlight-token safe-code offline implementation handoff

- 一句話現況：shared highlight missing-token failure 已離線改為 caller-bound safe code：header 使用 `LIST_HIGHLIGHT_TOKEN_MISSING_HEADER_P<paragraph>`，ordinary cell 使用 `LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T<table>_R<row>_C<column>`；無效或混合 metadata 固定 fail closed 為 `LIST_HIGHLIGHT_CONTEXT_INVALID`。完整離線 suite 全綠，但私人 master 的 Word 實機結果仍未驗證。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`。production 只修改 `scripts/briefing/patch_list_template.ps1`：新增不接觸 token/text 的 `Get-ListHighlightMissingCode`，在 `Set-TokenHighlight` 的 empty-token return 前驗證 contextual pattern 與 80-character adapter safe-code contract，zero match 改 throw 已驗證的 caller code；header／cell callers 只傳自己持有的位置。Word Find range／loop、黃色 highlight、內容、layout、schema、私人 master／calibration 均未修改。實作 commit 是 `f07d86e`。
- TDD 證據：先新增兩個核准的 source-contract regressions；修正前原始結果為 `2 failed`，第一案是 helper 尚不存在的 `IndexError`，第二案指出 mandatory `FailureCode` 尚未存在且 generic throw 仍在。最小修正後同一組為 `2 passed`；完整 `test_windows_word.py` 執行 exit 0，collect 輸出 `46 tests collected in 0.03s`。
- 完整驗證：PowerShell AST parser 輸出 `PARSER_ERROR_COUNT=0`；第一次巢狀 parser wrapper 因引號被 shell 吃掉而把 script 當命令，但在 mandatory `JobPath` parameter binding 即停止，未進入 script body 或 Word，改用目前的 no-profile PowerShell 直接 `ParseFile` 後通過。完整 suite 為 `553 passed, 8 skipped in 22.27s`；`compileall` 輸出 `COMPILEALL_OK`，`git diff --check HEAD^ HEAD` exit 0，standalone generic throw 搜尋輸出 `STANDALONE_GENERIC_THROW_COUNT=0`。
- 額外安全驗證：只抽取 helper source 的無 Word probe 得到 `HELPER_CODES=LIST_HIGHLIGHT_TOKEN_MISSING_HEADER_P2|LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T1_R2_C3`、`HELPER_INVALID_CASES=8`、`HELPER_MAX_LENGTH=69`；驗證結束時 `WINWORD_END_COUNT=1`，本回合未執行任何帶 `JobPath` 的 patch／COM 路徑。
- 下一步：若要確認私人路徑實際會回報哪個 contextual code，需要新的明確授權，只執行一次 4 天 post-fix Word repro；不跑其他天數，失敗不重試。成功後才可檢查同次 DOCX／PDF／PNG 的內容、QR、12 pt、尾端空白行與分頁視覺契約。
- 阻塞點：本回合依核准計畫在完整離線驗證後停止；沒有讀取或修改私人 master／calibration／DRAFT，沒有 GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。Word blocker 是否解除仍屬未驗證。

## 2026-08-18 LIST highlight-token safe-code offline implementation plan review

- 一句話現況：OP 已核准 caller-bound highlight safe-code 書面規格；離線實作計畫已建立，明定 header paragraph、ordinary cell table／row／column 與固定 context-invalid regression，現等待 OP 核准計畫，尚未修改 PowerShell／tests。
- 這次做了什麼：`git pull --ff-only` 為 `Already up to date.`；將設計狀態更新為 OP 已核准，並新增 `docs/plans/2026-08-18-list-highlight-token-safe-code-implementation-plan.md`。計畫拆成 red tests、最小 helper／caller wiring、focused parser／non-change proof、完整 suite 與 handoff 五個 tasks。
- 計畫邊界：只允許後續修改 `scripts/briefing/patch_list_template.ps1`、`tests/unit/travel_briefing/test_windows_word.py` 與 `STATUS.md`，執行 synthetic／source-contract 離線驗證並建立本機 commits；完整驗證後停止。
- 下一步：OP 審閱並回覆「同意此實作計畫，開始離線實作」後，才先建立兩個會紅的安全錯誤碼 regressions，再做最小 PowerShell 修正；未核准前不改 source／tests。
- 阻塞點：離線實作計畫核准關卡尚未通過；本次沒有 Word、私人 master／calibration、DRAFT、GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST highlight-token safe-code design review

- 一句話現況：generic `LIST_HIGHLIGHT_TOKEN_MISSING` 的兩個 caller 已離線盤點為 header paragraph 與 ordinary cell；OP 已確認 header 只帶 paragraph、cell 帶 table／row／column，選定 caller-bound safe-code helper 設計，目前書面規格待 OP 審閱，尚未改程式。
- 這次做了什麼：`git pull --ff-only` 為 `Already up to date.`；核對 commit `ee425a9`、shared `Set-TokenHighlight`、`Set-HeaderParagraph`／`Set-ListCell` callers 與 adapter `[A-Z][A-Z0-9_]{1,79}` 限制。新增 `docs/specs/2026-08-18-list-highlight-token-safe-code-design.md`，定義 `..._HEADER_P<number>`、`..._CELL_T<table>_R<row>_C<column>` 與固定 `LIST_HIGHLIGHT_CONTEXT_INVALID`。
- 設計邊界：只增加診斷 context；不改 Word Find、highlight color、token/text、plan/report schema、generator version、私人 master 或 calibration。`Set-TokenHighlight` 在 empty-token early return 前也驗證 failure code，避免錯誤 metadata 被隱藏。
- 下一步：OP 審閱並明確核准書面規格後，再建立離線實作計畫；未核准前不修改 PowerShell／tests。
- 阻塞點：書面規格審閱關卡尚未通過；本次沒有 Word、私人 master／calibration、GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST leader post-fix 4-day repro reaches highlight blocker

- 一句話現況：獲准的唯一一次 4 天 post-fix Word repro 已跨過 `LIST_CELL_EXTRA_PARAGRAPH_SET_T1_R2_C3`，但後續在 `run-action` 失敗於 generic `LIST_HIGHLIGHT_TOKEN_MISSING`；依約沒有重試、沒有跑其他天數，也沒有 DOCX／PDF／PNG 可供視覺驗收。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；前檢 doctor 確認 Word COM、pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure 均 `ok`，WINWORD baseline 為使用者原本的 1。只執行 opt-in integration 的 `[4]` node，使用全新 OS temp QA root 與 `-x`，5／6／7／8／12 天完全未進入。
- 驗證：pytest 原始結果為 `1 failed`；adapter evidence 是 `WORD_GENERATION_FAILED`／`LIST_HIGHLIGHT_TOKEN_MISSING`／HRESULT `-2146233087`／return code 30／stage `run-action`。QA root `C:\Users\cance\AppData\Local\Temp\easytravel-word-leader-postfix-3aa9f70a66b2409aa39e9565d08e807c` 只有空的 `day-004` directory，file count 0。事後 WINWORD count 回到 1；doctor 再確認 `master_sha256_matches: true` 與 normalized structure fingerprint 正常。
- 結論：commit `021f124` 已讓同一實機路徑不再停在 T1/R2/C3 的 extra-paragraph assertion，符合離線 `U+000B` 修正預期；但 shared `Set-TokenHighlight` 目前對 header 與 ordinary cell 都只拋同一 generic code，因此這次證據無法安全指出實際 caller、paragraph 或 table／row／column，也不能宣稱整份 Word 已修好。
- 下一步：若要繼續，先另行核准離線把 `LIST_HIGHLIGHT_TOKEN_MISSING` 細分為 header paragraph 與 ordinary cell table／row／column 的安全錯誤碼，建立 regression 並跑完整 suite；任何新的 Word repro 仍需另一個單次授權。
- 阻塞點：本次唯一 Word repro 授權已消耗且失敗，不得重跑。沒有修改程式或私人 master，也沒有 GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST leader-cell manual-line-break offline fix handoff

- 一句話現況：T1/R2/C3 的領隊姓名／台灣手機 patch payload 已離線由 `U+000D` 修正為 `U+000B` manual line break，保留兩行但維持單一 paragraph 語意；ordinary cell plan boundary 現在 fail closed 拒絕 CR／LF／BEL。完整離線 suite 全綠，但私人 master 的 Word 實機結果仍未驗證。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`。先在公開 `build_list_patch_plan` seam 新增 leader exact payload 與三種 forbidden marker cases；production 只修改 `src/travel_briefing/word_list.py`：leader separator `\r` 改為 `\v`，並在所有 cell builders 完成後、建立 `ListPatchPlan` 前執行不含值的固定訊息 validator。PowerShell adapter、plan schema/version、私人 master／calibration 均未修改。實作 commit 是 `021f124`。
- TDD 證據：目標 tests 修正前為 `4 failed`，leader failure 精確顯示 `\r` 對 `\v`，CR／LF／BEL 三案皆為 `DID NOT RAISE ValueError`；最小修正後同一組為 `4 passed`。原始實際 4 天 synthetic loop 現輸出 `T1_R2_C3_CODEPOINTS=U+000B`。
- 完整驗證：focused collection 為 `test_windows_word.py: 44`、`test_word_list.py: 35`，執行 exit 0；PowerShell parser 輸出 `PARSER_ERROR_COUNT=0`，adapter `git diff --exit-code` 通過。完整 suite 為 `551 passed, 8 skipped in 24.66s`；`compileall` 與 `git diff --check` exit 0。靜態搜尋沒有 leader `\r`，只保留預期的 `LIST_CELL_EXTRA_PARAGRAPH_SET` fail-closed assertion；WINWORD count 維持原本的 1。
- 下一步：若要驗收實機修正，需要新的明確授權，只執行一次 4 天 post-fix Word repro；不跑其他天數，失敗不重試。成功後才可檢查同次 DOCX／PDF／PNG 的兩行領隊欄、尾端空白行、QR 與 12 pt 視覺契約。
- 阻塞點：本回合依核准計畫在完整離線驗證後停止；沒有 Word、私人 master／calibration、GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。Word blocker 是否已解除仍屬未驗證。

## 2026-08-18 LIST leader-cell offline implementation plan review

- 一句話現況：OP 已核准 T1/R2/C3 的書面修正規格；離線實作計畫已建立，明確以 payload-level TDD 將領隊欄 `U+000D` 改為 `U+000B` 並在 plan boundary 拒絕 CR／LF／BEL，目前等待 OP 核准計畫，尚未修改 source／tests。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；以 commit `0b0b7a1`、已核准規格、實際 `draft(4)` test fixture、`build_list_patch_plan` seam 與既有 Word adapter tests 建立 `docs/plans/2026-08-18-list-leader-cell-manual-line-break-fix-implementation-plan.md`。計畫分成 red tests、最小 source fix、focused/parser、full suite 與 handoff 五個 tasks。
- 驗證設計：先要求 4 個 payload cases 紅燈，再把 actual 4-day loop 從 `U+000D` 轉為 `U+000B`；focused tests 維持 adapter paragraph assertion，最後跑完整 suite、parser、compileall、static search 與 `git diff --check`。預估 test count 僅作參考，回報以實際輸出為準。
- 下一步：OP 審閱並明確核准本實作計畫後，才可離線修改 `src/travel_briefing/word_list.py` 與 `tests/unit/travel_briefing/test_word_list.py`；完整測試通過後停止。
- 阻塞點：實作計畫尚未獲核准；本次沒有修改 production source／tests，沒有 Word、私人 master／calibration、GET、JMA、Yating、ffmpeg、installed runtime、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST leader-cell manual-line-break design review

- 一句話現況：4 天 repro 的 T1/R2/C3 blocker 已離線重現為領隊欄 patch payload 內的 `U+000D`；OP 已確認姓名與手機維持兩行，選定以 `U+000B` manual line break 保持單一 paragraph，目前書面規格待 OP 審閱，尚未改程式。
- 這次做了什麼：`git pull --ff-only` 為 `Already up to date.`；讀回既有 LIST normalization 規格／計畫與實際 builder／adapter／tests。實際 4 天 synthetic plan 的 tight loop 先得到 `T1_R2_C3_CODEPOINTS=U+000D`，再連續三次得到 `RUN_CODEPOINTS=U+000D|U+000D|U+000D`；現有 `test_list_cell_replaces_only_visible_text_and_asserts_one_paragraph` 仍為 `1 passed`，證實缺少 payload-level regression。
- 設計：新增 `docs/specs/2026-08-18-list-leader-cell-manual-line-break-fix-design.md`；只在 Python plan source 將領隊欄的 intentional break 改為 `U+000B`，並在 ordinary cell plan boundary fail closed 拒絕 CR／LF／BEL，不在 PowerShell 靜默轉換，也不放寬一段落 assertion。
- 下一步：OP 審閱並明確核准書面規格後，再建立離線實作計畫；未核准前不修改 source／tests。
- 阻塞點：書面規格審閱關卡尚未通過；本次沒有 Word、私人 master／calibration、GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST 4-day repro localizes write-time cell T1/R2/C3

- 一句話現況：獲准的唯一一次 4 天 Word repro 已把原本的 generic cell paragraph blocker 精確定位為 write-time 的 `LIST_CELL_EXTRA_PARAGRAPH_SET_T1_R2_C3`；依約沒有重試、沒有跑其他天數，也沒有 DOCX／PDF／PNG 可供視覺驗收。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；前檢 doctor 確認 Word COM、pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure 均 `ok`，WINWORD baseline 為使用者原本的 1。只執行 opt-in integration 的 `[4]` node，使用全新 OS temp QA root 與 `-x`，5／6／7／8／12 天完全未進入。
- 驗證：pytest 原始結果為 `1 failed`；adapter evidence 是 `WORD_GENERATION_FAILED`／`LIST_CELL_EXTRA_PARAGRAPH_SET_T1_R2_C3`／HRESULT `-2146233087`／return code 30／stage `run-action`。QA root `C:\Users\cance\AppData\Local\Temp\easytravel-word-coordinate-724f9631bc524514a500b1d8f56d7933` 只有空的 `day-004` directory，file count 0。事後 WINWORD count 回到 1；doctor 再確認 `master_sha256_matches: true` 與 normalized structure fingerprint 正常。
- 結論：失敗發生在 `Set-ListCell` 寫值階段的 table 1／row 2／column 3，不是 post-reopen assertion；新版座標化安全碼已達成定位目的。因 adapter 在產物建立前 fail closed，本次沒有可交付檔案，QR、12pt 與填值後空行的 Word 視覺結果仍屬未驗證。
- 下一步：若要繼續，先另行核准離線檢查 T1/R2/C3 的 master cell end-marker／段落結構與 `Set-ListCell` 寫值後 contract，建立針對性紅測後做最小修正並跑完整 suite；任何新的 Word repro 仍需新的單次授權。
- 阻塞點：本次唯一 Word repro 授權已消耗且失敗，不得重跑。沒有修改程式或私人 master，也沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST cell paragraph checkpoint and coordinate codes handoff

- 一句話現況：`LIST_CELL_EXTRA_PARAGRAPH` 已離線細分為 write-time 的 `LIST_CELL_EXTRA_PARAGRAPH_SET_T<table>_R<row>_C<column>` 與 post-reopen 的 `LIST_CELL_EXTRA_PARAGRAPH_POST_REOPEN_T<table>_R<row>_C<column>`；尚未執行新的 Word repro，因此實際失敗座標仍未知。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；新增受限 prefix 的 `Get-ListCellExtraParagraphCode`，座標只接受正整數，否則 fail closed 為 `LIST_CELL_COORDINATE_INVALID`。`Set-ListCell` 與 `Assert-ListOutputPresentationContract` 兩個原 generic throw site 都改傳入 table／row／column，且不輸出欄位文字。實作 commit 是 `9597372`。
- 驗證：regression test 先因缺少 builder 得到 `1 failed`，最小修正後 `1 passed`；focused Word 離線測試 `44 + 31` 全綠；PowerShell parser `PARSER_ERROR_COUNT=0`；兩個 checkpoint 範例皆通過 adapter safe-code regex；完整 suite `547 passed, 8 skipped in 23.57s`；`compileall` 與 `git diff --check` exit 0。WINWORD process count 維持原本的 1，沒有存取私人 master。
- 下一步：若要取得上次 4 天案例的確切 checkpoint 與 cell 座標，需要新的明確授權，只執行一次 4 天 Word repro、不跑其他天數、失敗不重試。
- 阻塞點：本次授權明確要求完整測試後停止、不執行 Word，所以尚未確認是 write-time 或 post-reopen，也不知道 table／row／column；沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST title post-fix Word repro reaches cell paragraph blocker

- 一句話現況：獲准的唯一一次 4 天 post-fix Word repro 已跨過 `LIST_SOURCE_TITLE_PARAGRAPH_MISMATCH`，但後續失敗於 `LIST_CELL_EXTRA_PARAGRAPH`；依約沒有重試、沒有跑其他天數，也沒有 DOCX／PDF／PNG 可供視覺驗收。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；前檢 doctor 確認 Word COM、pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure 均 `ok`，WINWORD baseline 為使用者原本的 1。只執行 opt-in integration 的 `[4]` node，使用新 OS temp QA root 與 `-x`，5／6／7／8／12 天完全未進入。
- 驗證：pytest 原始結果為 `1 failed`，adapter evidence 是 `WORD_GENERATION_FAILED`／`LIST_CELL_EXTRA_PARAGRAPH`／return code 30／stage `run-action`。QA root `C:\Users\cance\AppData\Local\Temp\easytravel-word-postfix-acaaaa53cfb34273a082904b06c715c4` 只有空的 `day-004` directory。事後 WINWORD count 回到 1；doctor 再確認 `master_sha256_matches: true` 與 normalized structure fingerprint 正常。
- 結論：commit `4e9d37d` 的 ANSI-safe title 修正已讓同一實機路徑通過原本的 title getter checkpoint；新 blocker 位於欄位填值後的 cell paragraph contract，與使用者要求移除填值後額外換行的區域一致，但本回合沒有猜測是哪個 cell，也沒有修改程式。
- 下一步：先另行核准離線把 `LIST_CELL_EXTRA_PARAGRAPH` 定位到安全的 table／row／column 或 patch checkpoint，建立紅測並最小修正；任何新的 Word repro 仍需新的單次授權。
- 阻塞點：本次唯一 Word repro 授權已消耗且失敗；未產生可交付檔案，沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 LIST title ANSI decoding root-cause fix handoff

- 一句話現況：唯一一次 4 天 Word repro 已把 getter 失敗精確定位為 `LIST_SOURCE_TITLE_PARAGRAPH_MISMATCH`；根因已證實並離線修正，但修正後尚未獲授權重跑 Word，因此 DOCX／PDF／PNG 成功仍未驗證。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；doctor 確認 Word COM、pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure 均正常。只執行 opt-in integration 的 `[4]` node、使用新 OS temp QA root 與 `-x`，5／6／7／8／12 天未進入且沒有重試。失敗 evidence 是 `WORD_GENERATION_FAILED`／`LIST_SOURCE_TITLE_PARAGRAPH_MISMATCH`／return code 30／stage `run-action`。
- 根因與修正：`patch_list_template.ps1` 是無 BOM UTF-8（首 bytes `112,97,114`），adapter 以 Windows PowerShell `5.1.26100.9168` 的 `powershell.exe -File` 執行；三處 `日本精緻假期` literal 被解析成 9 個錯誤 code points，而正確標題是 6 個 `U+65E5 U+672C U+7CBE U+7DFB U+5047 U+671F`。commit `4e9d37d` 改為只由這六個固定 code points 建構 `$ExpectedListTitle`，getter、pre-save 與 post-reopen 共用，正式 PowerShell source 不再含該非 ASCII literal。
- 驗證：新增 ANSI-safe regression 先 `1 failed`、修正後 `1 passed`；focused Word 離線測試 `43 + 31` 全綠；PowerShell parser `PARSER_ERROR_COUNT=0`；完整 suite `546 passed, 8 skipped in 23.30s`；`compileall` 與 `git diff --check` exit 0。事後 doctor 仍確認 master hash／structure 正常，`WINWORD` process count 維持原本的 1。QA root `C:\Users\cance\AppData\Local\Temp\easytravel-word-repro-cb0ee74e2bcb499897ef0783eb5a476d` 只有空的 `day-004` directory，file count 0。
- 下一步：若要驗收本修正，需要新的明確授權，只執行一次 4 天 post-fix Word repro，不跑其他天數、失敗不重試；成功後才能進行 DOCX／PDF／PNG 視覺 QA。
- 阻塞點：本次唯一 Word repro 授權已消耗，修正後 Word 實機結果仍屬未驗證；沒有 GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 或 public remote push。

## 2026-08-18 Get-ExactListTitleRange branch-safe codes handoff

- 一句話現況：`Get-ExactListTitleRange` 現在會保留 source／pre-save／post-reopen 階段，並把失敗細分為 `PARAGRAPH_MISMATCH`、`FIND_FALSE`、`FIND_RESULT_MISMATCH`；離線驗證完成，尚未執行 Word。
- 這次做了什麼：先以 regression test 取得 `1 failed` 紅燈，再讓 helper 接受受限的 `FailurePrefix`，三個 caller 分別傳入 `LIST_SOURCE_TITLE`、`LIST_PRE_SAVE_TITLE`、`LIST_POST_REOPEN_TITLE`，形成九種階段／分支安全碼；舊的 `*_RANGE_NOT_FOUND` 與 `LIST_POST_REOPEN_TITLE_CHANGED` 已從正式腳本移除。實作 commit 是 `1abc15c`。
- 驗證：目標 regression test `1 passed`；focused Word 離線測試 73 個測試點全綠；PowerShell parser `PARSER_ERROR_COUNT=0`；完整 suite `545 passed, 8 skipped in 19.40s`；`compileall` 與 `git diff --check` exit 0。沒有啟動 Word，既有 `WINWORD` process count 維持 1，也沒有存取私人 master。
- 下一步：若要辨認先前 4 天案例實際落在哪個 branch，需要新的明確授權後只跑一次 4 天 Word repro，維持不跑其他天數、失敗不重試。
- 阻塞點：本次授權明確要求完整測試後停止、不執行 Word，因此實際 Word branch 尚未驗證；GET、JMA、Yating、ffmpeg、LINE、Cowell、deploy、publish 與 public remote push 也都不在本次範圍。

## 2026-08-18 LIST 4-day repro localizes source title getter failure

- 一句話現況：三個 source checkpoint 細分後獲准的唯一一次 4 天 Word repro 已明確
  定位為 `LIST_SOURCE_TITLE_RANGE_NOT_FOUND`；immutable header 與 pre-save restore
  尚未執行，沒有重試、沒有跑其他天數，也沒有 DOCX／PDF／PNG 可視覺驗收。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；doctor 先確認
  Word COM、pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure
  均 `ok`。只執行 opt-in integration test 的 `[4]` node，使用新的 OS temp QA root
  與 `-x`；5／6／7／8／12 天完全未進入。
- 驗證：pytest 原始結果為 `1 failed`，adapter evidence 是
  `WORD_GENERATION_FAILED`／`LIST_SOURCE_TITLE_RANGE_NOT_FOUND`／return code 30／stage
  `run-action`。QA root 只有空的 `day-004` directory，file count 0。WINWORD 執行前、
  執行後與事後均為原本的 1；owned hidden Word 已清理。事後 doctor 再確認
  `master_sha256_matches: true` 與 normalized structure fingerprint 正常。
- 根因進度：新碼已排除 immutable header compare 與 pre-save title-font restore；
  失敗點確定是 `Get-ListTitleFontPoints` 呼叫 `Get-ExactListTitleRange` 後取得 null。
  helper 內仍有三個可能分支：完整 paragraph Trim 不等於 expected title、Word
  `Find.Execute()` 回傳 false，或 Find 後 candidate text 不等於 exact title；本次 safe
  evidence 無法再區分，不能猜定其中一個。
- 下一步：若要繼續，建議先另行核准離線把 getter 內上述三個 null 分支細分為不同
  safe codes 並跑完整 suite；之後任何新的 Word repro 仍需另一個當次明確授權。
- 阻塞點：本次唯一 4 天 Word repro 授權已消耗且失敗，不得重跑。沒有修改程式、
  私人 master 或 calibration，沒有 GET、JMA、Yating、ffmpeg、LINE、upload、publish、
  deploy、push 或 Cowell。

## 2026-08-18 LIST source checkpoint code split handoff

- 一句話現況：三個 LIST source-title checkpoint 已依 OP 核准範圍完成離線安全碼
  細分並通過完整 suite；本次明確不執行 Word，因此尚未取得下一次 4 天實機的精確
  checkpoint 結果。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`。immutable
  header compare 保留 `LIST_SOURCE_HEADER_TITLE_CHANGED`；master 原字級 getter 改為
  `LIST_SOURCE_TITLE_RANGE_NOT_FOUND`；pre-save title-font restore 改為
  `LIST_PRE_SAVE_TITLE_RANGE_NOT_FOUND`。既有 stage regression test 同時鎖定這三碼、
  plan 的 `LIST_TITLE_PLAN_INVALID` 與 post-reopen 的
  `LIST_POST_REOPEN_TITLE_CHANGED`。程式 commit 為 `4a6d395`。
- 驗證：更新後的 regression test 先得到預期 `1 failed`，兩個 safe code 完成替換後
  同一測試 `1 passed`；focused Word tests 為 `73 passed`，PowerShell parser 為
  `0 errors`，完整 suite 為 `545 passed, 8 skipped in 21.18s`，compileall 與
  `git diff --check` 通過。
- 下一步：若要實機定位，需要新的當次明確授權，只執行一次 4 天 Word repro、使用
  `-x`、不跑其他天數且未知結果不重試；新 adapter code 將可直接指出失敗 checkpoint。
- 阻塞點：Word COM 尚未用新碼驗證，沒有 DOCX／PDF／PNG 可交付。本次沒有啟動
  Word、沒有修改私人 master／calibration，也沒有 GET、JMA、Yating、ffmpeg、LINE、
  upload、publish、deploy、push 或 Cowell。

## 2026-08-18 LIST exact-title 4-day repro remains source-blocked

- 一句話現況：exact-title range 離線修正後獲准的唯一一次 4 天 Word repro 仍以
  `LIST_SOURCE_HEADER_TITLE_CHANGED` 安全失敗；沒有重試、沒有跑其他天數，也沒有
  DOCX／PDF／PNG 可供逐頁視覺驗收。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；doctor 先確認
  Word COM、pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure
  均 `ok`。只執行 opt-in integration test 的 `[4]` node，使用新的 OS temp QA root
  與 `-x`；5／6／7／8／12 天完全未進入。
- 驗證：pytest 原始結果為 `1 failed`，adapter evidence 是
  `WORD_GENERATION_FAILED`／`LIST_SOURCE_HEADER_TITLE_CHANGED`／return code 30／stage
  `run-action`。QA root 只有空的 `day-004` directory，file count 0。WINWORD 執行前、
  執行後與事後均為原本的 1；owned hidden Word 已清理。事後 doctor 再確認
  `master_sha256_matches: true` 與 normalized structure fingerprint 正常。
- 根因進度：commit `cfd6c78` 移除 text-length／Range-position 混算後，observable
  blocker 仍未改變，因此該修正不足以解除 Word source-title failure。現行同一 safe
  code 仍可能由 source font getter、immutable header check 或 pre-save title-font restore
  三個 checkpoint 回傳；這次 evidence 無法再區分，不能宣稱 exact finder 本身就是
  失敗點。
- 下一步：若要繼續，建議先另行核准離線把上述三個 source checkpoint 細分為不同
  safe codes 並跑完整 suite；之後任何新的 Word repro 仍需另一個當次明確授權。
- 阻塞點：本次唯一 4 天 Word repro 授權已消耗且失敗，不得重跑。沒有修改程式、
  私人 master 或 calibration，沒有 GET、JMA、Yating、ffmpeg、LINE、upload、publish、
  deploy、push 或 Cowell。

## 2026-08-18 LIST exact-title range offline fix handoff

- 一句話現況：已依既有核准規格完成 LIST exact-title range 的最小離線修正並通過
  完整 suite；程式不再用 `Range.Text` terminator 數量推算 Word `Range.End`，但本次
  沒有新的 Word COM 授權，因此 4 天實機是否跨過 source title blocker 仍未驗證。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`。新增
  `Get-ExactListTitleRange`：先用完整 paragraph range 驗證 Trim 後文字為 exact
  `日本精緻假期`，再沿用專案既有 Word `Find.Execute()` 找到只含 title token 的
  COM range。讀取 master 原字級、套回 title 字級及 save-reopen assertion 三處都改用
  同一 helper，不再把 `Range.Text.Length` 與 Word character position 混算。程式 commit
  為 `cfd6c78`。
- 驗證：新的 regression test 先得到預期 `1 failed`，修正後同一測試 `1 passed`；
  focused Word tests 為 `73 passed`，PowerShell parser 為 `0 errors`，完整 suite 為
  `545 passed, 8 skipped in 20.85s`，compileall 與 `git diff --check` 通過。沒有加入
  debug log 或 raw title 輸出，也沒有弱化既有 source／plan／post-reopen safe codes。
- 根因進度：離線證據支持前一輪最高順位假設：舊 getter 的錯誤點是先依文字內容計算
  terminator 數量，再直接改 Word range position；新的實作已移除這條耦合。不過沒有
  Word coordinate probe 或新實機 repro，故目前只能宣稱修正了可疑算法，不能宣稱
  Word blocker 已解除。
- 下一步：若要取得實機結論，需要新的當次明確授權，只執行一次 4 天 Word repro、
  使用 `-x`、不跑其他天數且未知結果不重試；若通過，再逐頁檢查該案例的 QA PNG。
- 阻塞點：Word COM 關卡尚未重新驗證，沒有 DOCX／PDF／PNG 可交付。本次沒有啟動
  Word、沒有修改私人 master／calibration，也沒有 GET、JMA、Yating、ffmpeg、LINE、
  upload、publish、deploy、push 或 Cowell。

## 2026-08-18 LIST title stage codes and 4-day source blocker

- 一句話現況：LIST title 已離線細分為 source／plan／post-reopen 三種安全錯誤碼並
  通過完整 suite；隨後唯一一次 4 天 Word repro 安全失敗於
  `LIST_SOURCE_HEADER_TITLE_CHANGED`，未跑 5／6／7／8／12 天，也沒有重試或可供
  視覺驗收的 DOCX／PDF／PNG。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；先新增 red
  regression test，再將兩個來源標題檢查改為
  `LIST_SOURCE_HEADER_TITLE_CHANGED`、兩個 plan contract 檢查改為
  `LIST_TITLE_PLAN_INVALID`、save-reopen 後的標題檢查改為
  `LIST_POST_REOPEN_TITLE_CHANGED`，並移除這三段的舊共用碼。程式 commit 為
  `f2bc33b`。離線關卡全綠後，doctor 確認 Word COM、pdftoppm、schema-2
  calibration、master SHA-256 與 normalized structure 均 `ok`，才只執行 opt-in
  integration test 的 `[4]` node，且使用 `-x`。
- 驗證：新增測試先得到預期 `1 failed`，修正後同一測試 `1 passed`；focused Word
  tests 為 `72 passed`，PowerShell parser 為 `0 errors`，完整 suite 為
  `544 passed, 8 skipped in 22.89s`，compileall 與 `git diff --check` 通過。唯一一次
  Word 原始結果為 `1 failed`，adapter evidence 是 `WORD_GENERATION_FAILED`／
  `LIST_SOURCE_HEADER_TITLE_CHANGED`／return code 30／stage `run-action`。新的 QA root
  只有空的 `day-004` directory，file count 0；WINWORD 前後與事後均為原本的 1，
  owned hidden Word 已清理。事後 doctor 再確認 `master_sha256_matches: true`。
- 根因進度：新碼已排除 plan final assertion 與 post-reopen assertion；錯誤仍在兩個
  source checks 之一。`build_list_patch_plan` 固定輸出 exact `日本精緻假期`，而
  `Get-ListTitleFontPoints` 又在 `Set-HeaderParagraph` 前執行；結合前次 full
  `Range.Text` 可 Trim 成 exact title 的證據，下一個最小離線調查點是 getter 以
  `Range.End` 減去 `Range.Text` terminator 數量的 boundary 算法。這是依 call order
  與既有證據的推論，尚未由新的 Word coordinate 診斷直接證實。
- 下一步：若要修復，先另行核准離線將 title token range 與 Word character-position
  boundary 分離並加入 regression tests；完整 suite 通過後，新的 Word repro 仍需
  另一個當次明確授權。
- 阻塞點：本次唯一 4 天 Word repro 授權已消耗且失敗，不得重跑；沒有任何可交付
  Word 產物。沒有修改私人 master／calibration，沒有 GET、JMA、Yating、ffmpeg、
  LINE、upload、publish、deploy、push 或 Cowell；5／6／7／8／12 天均未執行。

## 2026-08-18 LIST source title Range.Text diagnosis handoff

- 一句話現況：OP 核准的唯一一次 read-only LIST title `Range.Text` 格式診斷已完成；
  source master 的標題 Range 完全符合預期，已排除 leading spaces、VML shape marker、
  其他 control／零寬字元造成初始 title compare 失敗，問題範圍縮小到後續 Word
  mutation／save-reopen 之後的 final presentation assertion。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；用本次 owned
  hidden Word 將私人 master 以 read-only 開啟，只讀 table 1／row 1／cell 1／paragraph
  1，不 SaveAs、不產生 DRAFT、不執行 integration。probe 不輸出原文，只依已知
  exact title token 回報 Range 長度、token match 數與分類位置。
- 驗證：Range length 25；segments 為 `ASCII_SPACE [0,18)` 共 18、
  `EXPECTED_TITLE_TOKEN [18,24)` 共 6、`PARAGRAPH_MARK [24,25)` 共 1；exact title
  match count 1、start 18、known boundary trim exact match 為 true。沒有
  `OBJECT_MARKER`、`OTHER_CONTROL`、`OTHER_WHITESPACE` 或其他文字。假設 1 VML marker、
  假設 2 額外 control、假設 3 token 被拆開均被否定；假設 4「來源正常、錯誤在後續
  mutation／reopen」成立。
- 清理與完整性：診斷命令 finally 已 Close read-only document 並 Quit owned Word；
  Word 退出為非同步，命令結束瞬間 count 由 1 暫為 2，後續檢查已回到原本 1。
  事後 doctor 確認 `master_sha256_matches: true`、normalized structure、Word COM 與
  pdftoppm 均 `ok`。沒有原文、master path 或私人內容寫入 repo／STATUS。
- 下一步：先離線把共用 `LIST_HEADER_TITLE_CHANGED` 細分為 source、plan 與
  post-reopen output 的安全錯誤碼，加入 regression tests 並跑完整 suite；之後若獲
  新授權，只跑最小 4 天 Word repro 取得 final assertion 的精確 safe code，不先重跑
  5／6／7／8／12 天矩陣。
- 阻塞點：本次 read-only Word 診斷授權已消耗，沒有修碼或重跑整合。六天數 Word
  output 仍未通過，也沒有可視覺驗收的 DOCX／PDF／PNG；沒有 GET、JMA、Yating、
  ffmpeg、LINE、upload、publish、deploy、push 或 Cowell。

## 2026-08-18 LIST title spacing fix and second integration blocker

- 一句話現況：已依核准規格完成 leading-space 最小離線修正並通過完整 suite，但
  隨後獲准的新一輪私人 master Word COM 矩陣仍在第一個 4 天 case 以相同
  `LIST_HEADER_TITLE_CHANGED` 失敗；`-x` 已安全停止，5／6／7／8／12 天未執行，
  沒有 DOCX／PDF／PNG 可驗收。
- 這次做了什麼：新增 source-shape regression test，先得到預期紅測，再讓
  `Get-ListTitleFontPoints` 與 final presentation assertion 在 exact compare 前 Trim
  CR／BEL／space／tab；不刪 18 個前置空格、不改 master 或校準。修正 commit 為
  `d775099`。離線關卡全綠後，doctor 再確認 Word／pdftoppm／master hash／schema-2
  calibration 正常，才執行一次新的六案例 opt-in integration test。
- 驗證：新增測試先為 `1 failed`，修正後 `1 passed`；Word contract focused tests 為
  `71 passed`，PowerShell parser 0 errors，完整 suite 為
  `543 passed, 8 skipped in 21.30s`，compileall 與 `git diff --check` 通過。新整合
  test 原始結果仍為 `1 failed`，adapter evidence 是 `WORD_GENERATION_FAILED`／
  `LIST_HEADER_TITLE_CHANGED`／return code 30／stage `run-action`；QA file count 0。
  整合前後與事後 WINWORD process count 均為 1，owned Word 已清理。事後 doctor 再次
  確認 `master_sha256_matches: true`。
- 根因進度：唯讀 OOXML 已確認第一個 header paragraph 不只含 18 個 `U+0020` 與
  `日本精緻假期`，還含 1 個舊式 VML `w:pict`／shape（QR）。空白 Trim 修正仍失敗，
  表示 Word `Range.Text` 很可能含另一個 non-text shape/object marker；未經新的 Word
  診斷不能把推論當成已確認 code point，也不應再猜著修改。
- 下一步：取得一次唯讀 Word title `Range.Text` 字元格式診斷授權，只輸出段落長度、
  code point 類型／位置與 exact-title token match，不輸出其他私人內容、不 SaveAs、
  不產生 DRAFT。取得證據後再做離線修正；六天數矩陣仍需之後新的明確授權。
- 阻塞點：本次第二輪 Word integration 授權已消耗，輸出仍未通過。沒有重跑、沒有
  修改 master／calibration，沒有 GET、JMA、Yating、ffmpeg、LINE、upload、publish、
  deploy 或 Cowell；公開 remote 未獲新的 push 例外。

## 2026-08-18 LIST title leading-space Word integration blocker

- 一句話現況：OP 核准的 4／5／6／7／8／12 天私人 master Word COM 整合矩陣已用
  `-x` 執行一次；第一個 4 天 case 在 SaveAs 前明確失敗於
  `LIST_HEADER_TITLE_CHANGED`，因此安全停止，5／6／7／8／12 天均未執行，也沒有
  DOCX／PDF／PNG 可供視覺驗收。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；doctor 確認
  Word COM、pdftoppm、schema-2 calibration、master SHA-256 與 normalized structure
  均 `ok`。使用 repo 內 opt-in integration test 與合成 4／5／6／7／8／12 天資料，
  將 QA root 綁到新的 OS temp directory，且設定 first failure stop。整合前已有 1 個
  WINWORD process，結束後與再檢查都仍為 1，owned hidden Word 已清理，未關閉使用者
  原本的 Word。
- 驗證：pytest 原始結果為 `1 failed`，adapter evidence 是
  `WORD_GENERATION_FAILED`／`LIST_HEADER_TITLE_CHANGED`／return code 30／stage
  `run-action`。失敗 QA root 只有空的 `day-004` directory，file count 0。唯讀 OOXML
  盤點確認 canonical master 的第一個 header paragraph 是 18 個 `U+0020` 後接 exact
  `日本精緻假期`；既有 `Set-HeaderParagraph` 會 Trim 後比對，但新加入的
  `Get-ListTitleFontPoints` 對未 Trim 的整段做 exact compare，因而在任何輸出寫入前
  fail closed。事後 doctor 再次確認 `master_sha256_matches: true`。
- 下一步：依既有核准規格離線修正 title token／leading-space range 契約，加入真實
  source-shape regression test 並跑完整 suite；修正通過後，仍須取得新的 Word COM
  授權才能重跑六種天數整合矩陣。
- 阻塞點：本次 Word integration 授權已消耗且 4 天 case 未通過；不得在同一授權下
  修碼後重試。沒有修改 master／calibration，沒有 GET、JMA、Yating、ffmpeg、LINE、
  upload、publish、deploy 或 Cowell；公開 remote 未獲新的 push 例外。

## 2026-08-18 LIST Word output normalization implementation handoff

- 一句話現況：OP 核准的方案 1「輸出時正規化」已完成離線 TDD 實作；新產出的
  LIST Word copy 會移除校準 header QR 且不留空位、除第一行 `日本精緻假期` 外所有
  可見字固定 12 pt，程式填值也不再留下尾端空白段落。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`。source
  calibration schema 2 與 master bytes 保持不變；output plan／patch report／workflow
  evidence 升為 schema 3 與 `list-word/3`。PowerShell 只刪除 table 1 row 1 column 1
  內、數量與 calibration 相符的方形 QR candidate，然後釋放完整 header 寬度、套用
  12 pt contract、保留 exact title 原字級，並以 duplicate cell range 避免附加 CR／
  cell marker。PDF QA 改為每頁 image count exact 0，0.2.1 package 與三份 Skill mirror
  也鎖定同一契約。實作 commits 為 `f1902f4`、`f8f6d26`、`05a82f1`、`3515c63`。
- 驗證：Task 1 focused 輸出
  `........................................................................ [ 61%]`／
  `.............................................. [100%]`；Task 2 為
  `...................................................................... [100%]`；
  Task 3 為 `........................................ssssss..........................
  [ 93%]`／`..... [100%]`；Task 4 為 `.......... [100%]`。最終完整 suite 為
  `542 passed, 8 skipped in 18.76s`；compileall、patch/build PowerShell parser 與
  `git diff --check` 均通過。三份 Skill validator 都回傳 `Skill is valid!`。fresh OS
  temp package 為 63 entries，SHA-256
  `9c93f0f40969d42a50d199def48a4fd3b4a1f3edbfe3db9d6a0a4cb11df29fdc`；build 內建
  allowlist 與敏感資料掃描通過，未安裝 package。
- 下一步：若要驗證真實版面，需另行明確核准使用私人 canonical master 執行
  4／5／6／7／8／12 天 Word COM 整合；通過後再另行決定是否同步 installed runtime
  或產生新的正式 DRAFT。
- 阻塞點：Word COM／私人 master integration 尚未驗證，installed runtime 尚未同步，
  因此目前只能宣稱離線契約與模擬測試完成。這次沒有啟動 Word、GET、JMA、Yating、
  ffmpeg、LINE、upload、publish、deploy 或 Cowell；公開 remote 未獲 push 例外，
  所以只保留本機 commits。

## 2026-08-18 LIST Word output normalization design handoff

- 一句話現況：OP 已選擇方案 1「輸出時正規化」；移除 QR 且不留空位、除第一行
  `日本精緻假期` 外所有可見文字固定 12 pt、移除程式填值後多餘空白段落的書面規格
  已完成自審，實作尚未開始。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；唯讀檢查確認
  `Set-ListCell` 目前附加 CR 與 cell marker，既有輸出中幾乎所有已填 ordinary cell
  因而多出尾端空白段落。建立
  `docs/specs/2026-08-18-list-word-output-normalization-design.md`，明定 canonical
  master／calibration 不變，只在 owned output copy 移除校準 header QR、釋放文字
  wrapping 空間、統一字級並正規化 cell paragraph；generator 與 patch schema 升版，
  source QR 與 output zero-QR 驗證分離。
- 驗證：規格 203 行且無超過 100 字元的行，無 TBD／TODO／FIXME／placeholder，
  `git diff --check` 通過。未修改程式、master、calibration 或任何既有 DRAFT；目前
  使用者開啟中的 Word 文件也未被操作。
- 下一步：等待 OP 審閱並明確同意書面規格；之後先建立可執行實作計畫，再以 TDD
  修改 Word plan／PowerShell adapter／Word-PDF QA／workflow evidence 與 packaging。
- 阻塞點：`brainstorming` 設計關卡要求書面規格經使用者審閱後才能實作。私有 master
  Word 整合驗證仍需另行當次授權；沒有 GET、JMA、Yating、LINE、upload、publish、
  deploy、push 或 Cowell 動作，公開 remote 未獲 push 例外。

## 2026-08-18 OSA05261201A second one-shot DRAFT handoff

- 一句話現況：另一個日期完整的 NewAmazing 產品也在唯一一次 render 重現相同
  Word `VALIDATION_FAILED`；Yating／SRT／TXT 完成並通過 QA，但 Word QA PDF／PNG
  缺失，最終 draft 為 `BLOCKED`。這份對照證據表示問題不是日期未知特例，較可能
  位於共用 Word PDF／頁面 QA 階段，但具體 assertion 仍未被安全錯誤記錄。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；doctor 的
  Yating、Word registry、pdftoppm 與 schema-2 LIST calibration 均 `ok`，只有
  ffmpeg warning。依 OP 新 URL 執行唯一一次 GET，prepare run
  `20260818T090406+0800`、draft ID
  `1b1d89d623eb1e038a472cd8233a2a9ea86c5503183372784290c35e67cd5134`；
  解析為 5 天、2 段航班、全部日期存在、0 conflicts，warnings 為
  `SOURCE_CITY_MISSING`／`SOURCE_REGION_MISSING`。narration input `ready: true`，
  18 個 protected facts 依固定八段建立最小稿；`check-script` 回傳
  `ready: true`、`issue_codes: []`、估計 452.8 秒。
- 驗證：唯一一次 render 建立 run `20260818T090534+0800`，draft ID
  `33142239bb3219f61aa0083d8a539222b5b0b1e6ca2b60e5e79da8ec419c65b0`。
  DOCX 實體檔為 42,177 bytes，ZIP/OOXML 有 24 entries、0 個非目錄空 entry，且
  `[Content_Types].xml`、`word/document.xml`、document relationships 與 media 均存在；
  但 artifact 仍為 `blocked`，`word-evidence`、Word-QA PDF、QA index 與全頁 PNG
  全部 missing。safe error 與前一產品相同：stage `word`、code
  `VALIDATION_FAILED`、exception `ValueError`。Yating WAV／SRT／TXT 三份 SHA-256
  全與 metadata 相符；WAV 為 mono 16 kHz、440.027812 秒，SRT 92 cues 與 segment
  count 一致，末碼 440.032 秒只差約 4 ms。開頭／中段／結尾各 12 秒已抽聽，
  可辨且無明顯截斷或異常空白；WINWORD 0。暫存 helper 與 QA clips 已刪除。
- 下一步：若 OP 要定位共用 Word 問題，需另行核准「只用兩份既有 blocked DOCX
  執行一次 Word-QA 診斷」；診斷應保留具體 fail-closed assertion，同時不得重新 GET、
  重做 Yating 或把 blocked DOCX 當成正式交付。
- 阻塞點：兩個不同產品（一個日期未知、一個日期完整）都缺 Word QA evidence，
  因此目前不能逐頁視覺驗收或交付 DOCX。ffmpeg 未設定，MP3 仍 missing；review
  另有 2 個來源必要事實、10 個 OP 欄位、1 個 weather unavailable 與 8 個發音項目。
  沒有程式碼變更，沒有 JMA、LINE、upload、publish、deploy、push 或 Cowell 動作；
  公開 remote 未獲 push 例外。

## 2026-08-18 OSA0526D7459 one-shot unknown-date DRAFT handoff

- 一句話現況：指定 URL 的唯一一次正式日期未知 DRAFT GET 與唯一一次本機
  render 均已消耗且沒有重試；prepare 成功建立 `DRAFT_READY`，Yating／SRT／TXT
  完成並通過 QA，但 Word QA 回傳 `VALIDATION_FAILED`，最終 draft 因此為
  `BLOCKED`，不能交付 DOCX 為完成品。
- 這次做了什麼：開工 `git pull --ff-only` 為 `Already up to date.`；doctor 的
  Yating、Word registry、pdftoppm 與 schema-2 LIST calibration 均 `ok`，只有
  ffmpeg warning。唯一一次 GET 建立 run `20260817T212104+0800`，draft ID
  `294eabb306f494d2deb56099427db9f32f6ed4cdbcb422cfc53be62d9c25a17a`；解析為
  5 天、2 段航班、0 conflicts，5 個 day dates 全空白，只保留
  `SOURCE_CITY_MISSING`／`SOURCE_DATE_MISSING`。narration input `ready: true`，
  18 個 protected facts 依固定八段建立最小稿；`check-script` 回傳
  `ready: true`、`issue_codes: []`、估計 444.2 秒。
- 驗證：唯一一次 render 建立 run `20260817T212519+0800`，draft ID
  `2f46fb3745c856509ce71ce2a2dd25b701a773eb4c90f5702b65611cde9dc318`。
  Word DOCX 實體檔雖存在，但 artifact 為 `blocked`，`word-evidence`、Word-QA PDF、
  QA index 與全頁 PNG 都缺少；safe error 只保留 stage `word`、code
  `VALIDATION_FAILED`、exception `ValueError`，因此沒有視覺驗收也不得宣稱 Word
  完成。Yating WAV／SRT／TXT 均 `completed`；WAV 為 PCM mono 16 kHz、426.109438
  秒，落在 360–480 秒；三份 SHA-256 全與 metadata 相符，SRT 91 cues 與 segment
  count 一致，末碼 426.108 秒貼合音訊結尾。開頭／中段／結尾各 12 秒已抽聽，
  可辨且無明顯截斷或異常空白；WINWORD 0。暫存 helper 與 QA clips 已刪除。
- 下一步：若 OP 要繼續修 Word，需另行核准一次「只用既有 blocked DOCX 的
  Word-QA 診斷」或核准修正設計；不得把本次 no-retry 擴張成自動重跑 GET 或
  render。音訊三件可供內部 review，但整體說明會包仍是 `BLOCKED`。
- 阻塞點：Word QA 沒留下 PDF／PNG 或具體 assertion，現有 safe error 無法判定是
  page count、required text、QR、day-page map 或其他哪一條 ValueError；在新授權前
  不重跑。ffmpeg 未設定，MP3 仍為 `missing`，日期未知與 Word blocked 都阻擋
  CONFIRMED。沒有 JMA、LINE、upload、publish、deploy、push 或 Cowell 動作；公開
  remote 未獲 push 例外。

## 2026-08-17 unknown-date DRAFT implementation handoff

- 一句話現況：A「日期未知 DRAFT」已依核准規格完成 TDD 實作、完整離線驗證、
  package 驗證與 installed runtime 同步；尚未使用新的正式 DRAFT GET。
- 這次做了什麼：parser 升為 `newamazing-html/7`，接受全頁一致的 full-datetime
  或精確 `HH:MM`；無 published departure 且 time-only 時，product／flight／day
  dates 全部留白，混用格式 fail closed。merge 加單一 `SOURCE_DATE_MISSING`，
  PDF 有日期時把 blank web dates 視為缺漏而非衝突；narration 改為產品名稱句與
  nonblocking missing-date review；Word 的 product／flight／day 黃色 placeholder
  已由公開 patch-plan test 鎖定；CONFIRMED 對空白 product 或 day dates fail
  closed。程式 commit 為 `dcf7f2d`。
- 驗證：focused seams `126 passed in 3.48s`；完整 suite `534 passed, 8 skipped
  in 20.58s`；compileall 與 diff check 通過。0.2.0 package 為 63 entries，
  SHA-256 `7ceaee0a3ccf93bef1895979447579a1fc32b9e7fbe46643d8b2ec206faf0d06`。
  四個 changed installed modules 與 repo SHA-256 全部相符；doctor 的 Yating、
  Word、pdftoppm、schema-2 calibration 均 `ok`，WINWORD 0。
- 下一步：取得 OP 對同一產品「一次正式日期未知 DRAFT GET」的新明確授權後，
  執行 one-shot `prepare`；若 narration input ready，再依 one-DRAFT workflow 建稿、
  check-script、render、逐頁 Word QA 與人耳音訊驗收，不自動重試。
- 阻塞點：正式 DRAFT GET 尚未獲新授權。ffmpeg 仍未設定，因此可建立
  DOCX/WAV/SRT/TXT DRAFT，但 MP3 會 missing；日期未知與 MP3 missing 都阻擋
  CONFIRMED。沒有 LINE、upload、publish、push 或 Cowell 動作，公開 remote 未獲
  push 例外。

## 2026-08-17 unknown-date DRAFT design handoff

- 一句話現況：OP 已選擇 A「日期未知 DRAFT」方向；跨 parser、merge review、
  narration 與 CONFIRMED guard 的完整書面規格已自審並提交，實作尚未開始。
- 這次做了什麼：規格限定 live flight 全頁只能一致採 full-datetime 或
  time-only；無 published departure 且 time-only 時，product／flight／day dates
  全部留白，不猜值。merge 加單一 `SOURCE_DATE_MISSING` warning，Word 沿用黃色
  `待 OP 確認`，旁白只保留來源綁定產品名稱且加入 nonblocking missing-date
  review，CONFIRMED 對空白 product 或 day dates fail closed。PDF 日期仍優先，
  blank web dates 視為缺漏而非衝突。設計 commit 為 `feede57`。
- 下一步：OP 審閱
  `docs/specs/2026-08-17-newamazing-time-only-flight-design.md` 並明確同意後，
  才建立 implementation plan，再依 TDD 從公開 seams 加紅測與最小修正。
- 阻塞點：等待書面規格 review；尚未修改程式或 installed runtime。正式 DRAFT
  GET 仍未獲新的單次授權；沒有 CONFIRMED、LINE、upload、publish、push 或
  Cowell 動作，公開 remote 未獲 push 例外。

## 2026-08-17 time-only live flight diagnosis handoff

- 一句話現況：replacement 唯讀診斷 GET 已成功證明目前 NewAmazing live-card
  的四個航班「日期時間」值全部只有 `HH:MM`；頁面沒有可供 departure fallback
  的航班日期，因此先前方案 A 的來源前提不成立。
- 這次做了什麼：以正式 `_live_header_indexes()` 重建 alias-safe 一次性診斷器，
  先用合成 live-card 與「起飛時間／到達時間」alias 離線驗證，再執行唯一一次
  allowlisted、no-retry replacement GET。兩列 departure／arrival 共四值均為
  length 5、token `Dx2 U+003A Dx2`、digit runs `[2,2]`，現行 datetime regex
  全部拒絕；沒有輸出原始值，原始 HTML 未保留。一次性 script、pycache 均已
  刪除，WINWORD 0，repo 在記錄本段前為 clean。
- 下一步：請 OP 選擇書面設計方向。建議 A 是接受來源明確提供的 time-only
  航班，但將 product／flight／day dates 保持空白，加入來源缺日 warning，Word
  顯示黃色「待 OP 確認」，旁白只保留產品名稱並排除空白日期，且不得進入
  CONFIRMED；B 是不改 parser，要求 OP 提供本機行程 PDF，以 PDF 日期完成 DRAFT。
- 阻塞點：本次只獲診斷授權，尚未獲跨 parser／merge review／narration 的設計與
  實作同意。不得從產品代碼、抓取日期或其他文字猜日期；正式 DRAFT GET 仍需
  修正驗證完成後的另一個單次授權。公開 remote 未獲 push 例外。

## 2026-08-17 flight datetime diagnostic GET handoff

- 一句話現況：一次航班日期時間格式唯讀診斷 GET 已消耗，但因一次性診斷器
  自己的欄名契約過窄而未取得日期格式證據；沒有重試，也沒有修改 parser。
- 這次做了什麼：診斷 GET 使用既有 allowlisted、no-retry gateway，原始 HTML
  僅存在 OS temporary directory 並已隨程序清除。失敗點是診斷器只接受
  「出發時間」，未重用正式 parser 已支援「出發時間／起飛時間」的 alias
  mapping，因此回傳 `diagnostic contract missing unique departure field`。之後只用
  合成 fixture 離線修正：直接重用 `_live_header_indexes()`；完整遮罩流程與
  「起飛時間／到達時間」alias index 均通過。一次性檔案與 pycache 已刪除。
- 下一步：若 OP 同意一次 replacement 航班日期時間格式唯讀診斷 GET，重建已
  離線驗證的診斷器，只輸出字元類型遮罩、數字段長度、標點 code point 與現行
  regex 判定；取得證據後再提出窄幅 parser 設計。
- 阻塞點：目前仍不知道真實日期時間字串的形狀，不得猜測修正。replacement
  診斷 GET、後續 parser 實作及正式 DRAFT GET 都尚未獲新授權；沒有來源或
  DRAFT 產物留存，公開 remote 仍未獲 push 例外。

## 2026-08-17 live flight datetime parser handoff

- 一句話現況：缺少 `.departure_date` 的 NewAmazing live-card fallback 已完成
  並通過完整離線回歸；唯一一次正式 DRAFT GET 已安全停止在新的
  `日期時間格式` parser anchor，未產生 DRAFT。
- 這次做了什麼：以公開 `parse_newamazing_html()` seam 加入兩個去識別紅測，
  先證明缺節點與末航班不符的既有失敗，再將 parser 升為
  `newamazing-html/6`：缺節點時只採同頁第一段航班日期，並保留天數、首末
  航班與每日行程一致性檢查。focused suite 為 `13 passed`；完整離線 suite
  為 `525 passed, 8 skipped in 20.21s`，compileall、diff check、63-entry
  package build 均通過。程式已於本機 commit `02b8cca`，已安裝 parser 與 repo
  SHA-256 同為 `34856b3e0493d4061889b5d36345243c479059c4ba8bfb6ffdef7c72987c39f2`。
- 下一步：取得 OP 對「一次航班日期時間格式唯讀診斷 GET」的新明確授權後，
  只盤點去識別的格式形狀；重新設計、紅測、修正與完整驗證後，正式 DRAFT
  GET 仍需另一個新的單次授權。
- 阻塞點：本次正式 GET 已消耗且回傳 `PARSE_CONTRACT_CHANGED`／
  `日期時間格式`，依 no-retry 契約不得重試。沒有新 run、沒有啟動 Word；
  ffmpeg 仍未設定。公開 remote 未獲 push 例外，因此目前只保留本機 commits。

## 2026-08-17 missing departure-date parser design handoff

- 一句話現況：已完成 NewAmazing live-card 缺少明確出發日節點時的窄幅
  parser 修正設計；實作停在書面規格確認關卡前。
- 這次做了什麼：唯讀盤點確認產品卡仍有天數、航班與每日行程，只有
  `.departure_date` 缺漏；OP 已選擇方案 A。規格限定以同頁第一段航班日期
  作為缺節點時的來源，並保留產品代碼、正整數天數、首末航班及每日行程
  一致性驗證；禁止由團號、抓取日期或自由文字猜日期。設計文件已自審並
  於本機 commit `655056a`。
- 下一步：OP 確認書面規格後，從公開 `parse_newamazing_html()` seam 加入
  去識別紅測，再做最小 parser 修正並跑 focused 與完整離線 suite。
- 阻塞點：等待 OP 確認書面規格；尚未修改 parser，也尚未使用已另行授權的
  最後一次正式 DRAFT GET。公開 remote 未獲 push 例外，因此只做本機 commit。

## 2026-08-17 Word 內容修正 handoff

- 一句話現況：NewAmazing URL-only 說明會功能已依真實
  OSA05261103E 驗證；最新 `DRAFT_READY` Word 已改為完整行程、首間飯店
  與餐食 O/X，兩頁視覺 QA 通過。
- 這次做了什麼：將 live parser 由 `.day_content h3` 景點短標改為
  `h4.day_title_right` 完整行程，保留箭頭與括號說明；住宿只取第一個
  「或」之前的飯店；餐食固定解析早／午／晚三格，Word 僅顯示供餐 O、
  無餐或自理 X。真實 run `20260817T145825+0800` 已產出 DOCX、PDF QA、
  WAV、SRT、TXT；完整離線 suite 為 100% / exit 0，package build 為
  63 entries，SHA-256 `e775700ca605319f76cd79d9eff711832974153cbbeb16b1472c1dc11ccd0f13`。
- 下一步：OP 開啟最新 Word 審閱實際內容；若要進入 `CONFIRMED`，
  再補齊黃色 OP 欄位、缺漏事實、讀音 review 與 MP3。
- 阻塞點：本機沒有已設定的 ffmpeg，MP3 仍為 `missing`；這不阻擋
  DOCX/WAV/SRT/TXT DRAFT，但仍阻擋 `CONFIRMED`。目前未做人耳聽取驗收。

## 2026-08-17 URL-only DRAFT handoff

- 一句話現況：NewAmazing URL-only 說明會功能已可建立可審閱的本機
  `DRAFT_READY`；實際 OSA05261103E 已產出 DOCX、WAV、SRT、TXT。
- 這次做了什麼：將缺值、無即時天氣、未確認 OP 欄位、讀音 review 與缺
  ffmpeg 改為不阻擋 DRAFT；排除重複 `group_notes` 旁白；將 LIST 行程安全
  上限由 56 調到 64 字並修正長團名 QR 繞排；長 Yating 稿改為每批最多兩個
  narration segments，依真實 bookmark 串接 WAV/SRT；render error 僅保留
  private-safe adapter evidence。完整離線回歸 100% / exit 0。
- 下一步：OP 開啟最新 DRAFT 檢查內容並實際聆聽 WAV；若要進入
  `CONFIRMED`，再補齊黃色 OP 欄位、缺漏事實、讀音 review 與 MP3。
- 阻塞點：本機沒有已設定的 ffmpeg，所以 MP3 為 `missing`；這不再阻擋
  DOCX/WAV/SRT/TXT DRAFT，但仍阻擋 `CONFIRMED`。目前未做人耳聆聽驗收。

## 一句話現況

說明會產生器 0.2.0 的 Gate I 已完成；真實 OP-choice worksheet 與 blank choice artifact
已由既有兩份 private-safe reports 純離線產生並驗證，decision table 仍為
`BLOCKED_MIXED_VALUE`；OP 已明確指定 13 組全部選 sample-001，36 個 hash-bound choices
已填妥並通過 strict validation；欄寬亦明確選 sample-001，Gate C 單一來源 normalization
整合已通過完整離線回歸；manifest evidence 接線錯誤修正後的新正式 Gate C 已成功，
sample-001 normalization、SaveAs2、master validation、manifest 與 exclusive publish 全部
通過。正式 `LIST-master.docx` 與 `calibration-manifest.json` 已建立並完成 identity 後驗；
Gate C 與 Gate V Word 視覺 QA 均已完成；首次 Gate E 真實 URL 的 live notice mapping
已修正並建立新版 review，Yating 證實只是 sandbox 偽陰性；目前在 render 前只剩真實
來源／OP／天氣與發音 review，不是主機缺少語音套件。

## 這次做了什麼

- 2026-08-17 依 OP「換主機、搞清楚卡在哪並修正」完成 Gate E blocker diagnosis 與
  專案內可修部分。Yating 登錄、語音檔與繁中 language pack 均存在；sandbox 內 WinRT
  `AllVoices` 會回 `Internal Speech Error`，但 sandbox 外同一 probe 正確列出 Yating 並回
  `YATING_AVAILABLE`，因此不需安裝，也沒有 fallback。新主機缺少的
  `%LOCALAPPDATA%\EasyTravelBriefing\config.toml` 已以既有 master／manifest／pdftoppm 與
  private output 路徑建立；sandbox 外 `doctor` 顯示 Yating、Word、pdftoppm、calibration
  全部 `ok`，只剩未設定 ffmpeg warning。程式面確認 live `出團備註` 是含三個巢狀段落的
  compound notice，舊 parser 把它壓成 `other`。以去識別 fixture 先紅測，再升級
  `newamazing-html/4`：對有明文證據的句子拆出來源綁定 facts，並認得官網七種標準 notice
  headings；頁面未提供的內容仍不推測。targeted 為 `39 passed`，完整離線回歸為
  `516 passed, 8 skipped in 98.86s`，compileall 與 `git diff --check` 通過。修正後同一 URL
  在全新 private run `20260817T130627+0800` 建立 draft ID
  `f7f73fd01446210356788d7c292bb1f769ebbe93fef45d51ab5442637642727f`；parser version 4、
  5 天、0 conflicts、19 required facts，review items 從 39 降至 27：unknown notice 7→0、
  missing required facts 7→2。剩餘為 2 個來源真缺漏、10 個 OP 欄位、1 個不可用天氣與
  14 個待 review 發音項目；依契約未進行 check-script／Word／audio render。

- 2026-08-17 首次 Gate E 使用 OP 提供的 NewAmazing URL 執行 one-request local DRAFT。
  `doctor` 確認 Word、schema-2 master、manifest hash 與 pdftoppm 正常，但 Microsoft Yating
  不可用且 ffmpeg 未設定；沒有安裝或改用 Hanhan。單次 allowlisted GET 成功，於 private
  `gate-e-drafts/OSA05261103E/20260817T123515+0800` 建立 `DRAFT_READY` manifest，draft ID
  `24ce2d9f0b6e20a6aaed588f6f1ef9bdbe0f6eb3a93404a1de77c26ea1c04e42`，來源解析為 5 天且
  無 conflict。narration input 為 `ready: false`，共 39 個 review items：10 個未確認 OP
  欄位、7 個必要事實缺漏、7 個未知 notice category、1 個 weather unavailable、14 個
  unknown pronunciation terms。因此依 Skill 在 check-script／Word／audio render 前停止；
  實際只保留 manifest、manifest hash、review 與 narration input，未建立 DOCX／PDF／PNG／
  WAV／MP3，WINWORD 0，未 retry、未發布、未傳送。臨時 config 已移除。

- 2026-08-17 Gate V `final-v6` 已正式通過。先以人工檢出的 5 天空白續頁、6 天孤立
  注意事項標題及 7 天孤立緊急聯絡標題建立紅測，再加入 fail-closed pagination guards：
  兩個固定標題必須各精確命中一次並與後續內容同頁，文件尾端必須是可壓縮的空 paragraph；
  5 天 fixture 也正式要求單頁。完整離線回歸為
  `513 passed, 8 skipped in 98.65s`，PowerShell parser、compileall 與
  `git diff --check` 均通過。以既有校準 master 在全新 private `final-v6` 執行
  4／5／6／7／8／12 天真實 Word integration，結果為 `6 passed in 54.70s`；頁數依序
  1／1／2／2／2／2，共 10 張 PNG 已全部逐頁人工檢查，未見空白續頁、孤立標題、裁切、
  重疊或 QR 重複，續頁團體識別與日程表頭正確。產物保留於
  `C:\Users\user\Documents\EasyTravel-Private\gate-v-word-qa-20260817-final-v6`；master 與
  manifest SHA-256 仍分別為 `6b4fbf74fb10af0bf00e1c00841deea8d80546db60698b8152457873fcc041a5`
  及 `9fa1b84d5a566c000105b0bdd7f3caefee22cc04a26890b4f953925baabd8701`，WINWORD 0，
  未發布、未傳送。

- 2026-08-17 真實 header token 修正後的正式 `final-v4` 已有 4／5／6／7／8 天通過，
  只剩 12 天 `day page mapping does not match PDF`。根因是 QA 以 substring 搜尋 `9/1`，
  因而誤命中 `9/10`、`9/11`、`9/12`；不是 Word 版面錯誤。已保留 private `final-v4`
  事證、不覆寫；先以 `9/1`／`9/10` 同頁紅測重現，再改為日期 token 前後不得接數字的
  regex 邊界比對，仍要求每個 token 只在 report 指定頁精確出現一次。完整 Word QA unit
  suite 為 `18 passed`，全新短 private basetemp 完整回歸為
  `512 passed, 8 skipped in 8.74s`，compileall 與 `git diff --check` 通過。修正後正式六例
  尚未重跑。

- 2026-08-17 day-page 邊界修正後的正式 `final-v3` 仍是 4／5／6／7 通過、8／12
  失敗，但已進到 PDF continuation token 檢查。使用既有 8／12 DOCX raw render（沒有再
  patch Word）並逐頁檢視 4 張 PNG，確認兩例都是 2 頁：續頁有團號／團名、daily header
  已重複、QR 只在首頁、所有 day rows 完整且無裁切／跨頁。唯一錯誤是 workflow QA token
  用概念詞「行程／住宿／早餐／午餐／晚餐」，而校準 master 真實欄名為
  「行程簡介／飯店名稱／飯店電話／早／午／晚」。已先加 backend 紅測，再將 token 精確
  綁定真實 master labels；targeted test、compileall、`git diff --check` 與全新短 private
  basetemp 完整回歸均通過，結果為 `511 passed, 8 skipped in 8.77s`。`final-v3` 與 raw
  diagnosis 均保留；修正後正式六例尚未重跑。

- 2026-08-17 修正後持久化正式 `final-v2` 六例結果為 4／5／6／7 天全通過，8／12 天
  仍固定 `LIST_DAY_ROW_TOO_TALL`。正常短列仍被判跨頁的根因是 `Get-DayPageMap` 將
  row range 的 end collapse 到列終止標記後方；剛好換頁時會落到下一頁，誤判上一列。
  已保留 private `final-v2` 事證、不覆寫；先以紅測鎖住 end probe 必須退一個字元，再於
  collapse 前將 end 移回列自身 marker。真正跨頁列的 start/end 仍會不同並被擋。
  targeted test、PowerShell parser、compileall、`git diff --check` 與全新短 private
  basetemp 的完整回歸均通過，結果為 `511 passed, 8 skipped in 8.77s`。修正後正式六例
  尚未重跑。

- 2026-08-17 首次持久化正式六例結果為 4 天通過、5／6／7／8／12 天失敗：5–7 的
  第 2 頁是非日程的注意事項頁，已有團體 identity，但既有 QA 誤要求 daily header；
  8／12 的 synthetic 單列長文則正確觸發 `LIST_DAY_ROW_TOO_TALL`，沒有形成安全多列續頁。
  已保留 private `final-v1` 事證、不覆寫。依 Gate V 契約新增紅測後，QA 改為所有續頁
  必須有 identity，只有 day-page map 實際指向的日程續頁才強制 daily header；沒有 map 的
  舊呼叫仍維持每頁全檢查。8／12 fixture 改為正常單列長度，靠 8／12 列本身觸發續頁；
  4 天仍固定單頁，8／12 固定多頁，5–7 依真實 master pagination 驗收。Word QA targeted
  suite 為 `17 passed`，全新短 private basetemp 的完整回歸為
  `510 passed, 8 skipped in 8.70s`，compileall 與 `git diff --check` 通過。修正後正式六例
  尚未重跑。

- 2026-08-17 reopened-artifact 修正後，真實 4 天 Gate V 單例正式通過：
  `1 passed in 6.62s`，DOCX、1 頁 PDF、1 張 PNG、QR、日期映射與 QA index 一致；
  master hash 不變、WINWORD 0。另確認 pytest 結束會清除 basetemp，為使正式六例 PNG
  能依 Gate V 保留並逐頁人工檢查，opt-in integration harness 新增可選的明確
  `EASYTRAVEL_GATE_V_OUTPUT_ROOT`；設定時寫入該全新 private 根目錄，未設定仍用 tmp_path，
  產品流程與所有驗收斷言不變。完整離線回歸為
  `509 passed, 8 skipped in 8.65s`，compileall 與 `git diff --check` 通過。正式六例尚未執行。

- 2026-08-17 SaveAs2 後在原 COM document 重算仍回報舊的 2 頁，而重新開啟輸出 DOCX
  的 PDF render 為 1 頁，證明 Word current document 保留 pre-save pagination cache。
  已先把回歸測試加嚴為必須 reopen output artifact，再於 adapter 中 SaveAs2 後關閉並釋放
  working document、read-only 重開剛儲存的 DOCX，重新執行 saved-artifact inspection、
  Repaginate、page count 與 day map；report 不再採用舊 COM cache。targeted test、
  PowerShell parser、compileall、`git diff --check` 與全新短 private basetemp 的完整回歸
  均通過，結果為 `509 passed, 8 skipped in 8.72s`。尚未在 Word 重跑此修正。

- 2026-08-17 日期顯示修正後的 4 天案例證明儲存後 PDF 已為 1 頁，但 patch report 仍為
  2 頁，固定失敗於 `Word, PDF, and expected LIST page count do not match`；其
  day-page map 亦是 SaveAs2 前值。根因是 Word 在 SaveAs2 才完成首頁不同 header 的最終
  pagination，而 adapter 先量測再儲存。已先用紅測鎖住順序，再保留原 profile 選擇但將
  正式 `computed_page_count` 與 `day_page_map` 改為 SaveAs2 後重新 Repaginate／量測；
  targeted test、PowerShell parser、compileall、`git diff --check` 與全新短 private
  basetemp 的完整回歸均通過，結果為 `509 passed, 8 skipped in 8.60s`。尚未在 Word
  重跑此修正。

- 2026-08-17 原生 continuation header 修正後，4 天 QA 仍為 2 頁；最新版 build-only
  diagnostic 成功保留 DOCX，最終列印因診斷程式誤用不存在的 `DayPagePlacement.to_dict()`
  失敗，但沒有 unknown Word result。直接讀該 DOCX OpenXML 顯示每日列 line spacing 仍為
  normal 14pt，證明 compact 也無法單頁後依設計恢復 normal。視覺證據中的每日 ISO 日期
  `2026-09-01` 被 38.85pt 日期欄折成三行，這才是剩餘溢頁來源。已先用紅測鎖住 LIST
  presentation date，再將 canonical ISO 日期僅在 Word 顯示層轉為 `M/D`（draft 仍保留完整
  日期），PDF day-token QA 同用此 formatter；無法解析或非 canonical 值原樣保留，不猜測。
  日期 targeted cases 通過；另一個 workspace `.tmp` setup error 是父目錄不存在而非斷言
  失敗，改用全新短 private basetemp 後完整結果為 `508 passed, 8 skipped in 8.59s`，
  compileall 與 `git diff --check` 通過。尚未在 Word 重跑日期修正。

- 2026-08-17 QR 修正後的 4 天流程已成功建立 Word/PDF，但正式 QA 發現實際 2 頁且
  第 2 頁缺 continuation identity/header、day-page map 亦與 PDF 不符；fail-safe 仍未發布
  正式 QA 產物。另以本次 Gate V 範圍內的隔離 diagnostic artifact 略過兩個斷言取得 raw
  PDF/PNG，逐頁視覺確認兩頁頂端均顯示 Word「錯誤：遺漏測試條件。」，第 2 頁只是被
  推出的團體旅遊注意事項。根因為 `Add-ContinuationGroupHeader` 建立的巢狀 IF/PAGE field
  無效且佔用 header 高度。已先用紅測鎖住不得使用 IF fields，再改為 Word 原生
  `DifferentFirstPageHeaderFooter`：首頁 header 必須空白，第 2 頁起 primary header 直接顯示
  團號／團名，任何既有 header 內容或 shape 均 fail closed。targeted test 與 parser 通過；
  第一次完整 suite 因過長 private basetemp 觸發 Windows 深層 package path
  `DirectoryNotFoundException`（非功能失敗），換用全新短路徑且未改測試後完整結果為
  `508 passed, 8 skipped in 8.69s`，compileall 與 `git diff --check` 通過。尚未在 Word
  重跑此修正。

- 2026-08-17 header terminator 修正後的 4 天 Word 案例通過 paragraph-count contract，
  隨後固定失敗於 `LIST_QR_MISSING`；後驗仍為零產物、WINWORD 0、master hash 不變。
  master XML 證明第 1 段已是固定「日本精緻假期」且保留範本定位空白，浮動 QR 正錨定於
  該段；重寫該 range 會刪除 shape anchor。已先用紅測鎖住 QR-anchored title preservation，
  再改成第 1 段 trim 後必須與計畫標題完全相符但不 mutation，只 patch 第 2–4 段；
  targeted test、PowerShell parser、compileall、`git diff --check` 與完整離線回歸均通過，
  結果為 `507 passed, 8 skipped in 8.72s`。尚未在 Word 重跑此修正。

- 2026-08-17 擴列修正後的 4 天 Word 案例通過 day-row contract，隨後固定失敗於
  `LIST_HEADER_PARAGRAPHS_CHANGED`；後驗仍為零產物、WINWORD 0、master hash 不變。
  根因是 `Set-HeaderParagraph` 覆寫整段 range，最後一段包含 Word cell terminator，另補
  `CR` 會多造第 5 段。已先用紅測鎖住 terminator preservation，再改為只替換剔除既有
  paragraph／cell terminators 後的可見文字；targeted test、PowerShell parser、compileall、
  `git diff --check` 與完整離線回歸均通過，結果為
  `506 passed, 8 skipped in 8.82s`。尚未在 Word 重跑此修正。

- 2026-08-17 只重跑已核准集合內的 4 天 fixture 取得 private-safe 固定錯誤
  `LIST_DAY_COUNT_MISMATCH`（stage `run-action`、return code 30）；後驗仍為零產物、
  WINWORD 0、master hash 不變。manifest 與 master DOCX XML 都證明第 3 表正確為 2 列，
  根因是 `Set-DailyRowCount` 將完整原型列 `FormattedText` 指派給新列時，Word 會連同列
  終止標記附加額外列，而函式沒有在擴列後再次收斂。已先以紅測重現缺少 post-growth
  reconciliation，再加入最小的尾列校正與明確 `LIST_DAILY_ROW_RESIZE_FAILED` postcondition；
  targeted test、PowerShell parser、compileall、`git diff --check` 與完整離線回歸均通過，
  精確結果為 `505 passed, 8 skipped in 8.79s`。尚未在 Word 重跑修正後案例。

- 2026-08-17 首次真實 Gate V 六例（4／5／6／7／8／12 天）均在 Word patch action
  回傳通用 `WordGenerationError`，尚未進入 PDF／PNG 驗證；唯讀後驗確認 private 輸出
  根目錄為空、DOCX／PDF／PNG 均為 0、WINWORD 0、master SHA-256 不變且工作樹無產物
  異動，因此不是 unknown write，沒有盲目重跑。opt-in integration test 已改為在錯誤時
  只顯示既有 private-safe `code`／`stage`／`hresult`／`adapter_code` details，避免 pytest
  traceback 隱藏根因；完整離線 suite 再次通過（`504 passed, 8 skipped`，共 512 tests），
  compileall 與 `git diff --check` 通過。下一步只執行已核准集合內的 4 天 fixture 受控定位，
  找到共同根因後才恢復六例驗收。

- 2026-08-17 經使用者明確核准 Gate V 後，先將既有 opt-in Word integration test 從單一
  legacy fingerprint／單頁案例改為正式 schema-2 master＋calibration manifest 路徑，並固定
  參數化 4／5／6／7／8／12 天。4–7 天使用一般長度 synthetic 內容且必須單頁；8／12 天
  使用較長但受 route limit 約束的 synthetic 內容且必須觸發至少兩頁。每例都驗證 DOCX／
  PDF／PNG page set、QR、required text、day-page map 與 hash-bound QA index；不含額外的
  too-tall case、發布或傳送。
- 真實 Word 尚未執行；完整離線 suite 為 `504 passed, 8 skipped`（共 512 tests），
  compileall 與 `git diff --check` 通過。待本變更先 commit，再以全新 private basetemp 執行
  核准的六個 Gate V cases 並依 `pdf` skill 逐張檢視最新 PNG。

- 2026-08-17 使用者明確核准一次新的正式 Gate C；preflight 確認三份來源 hash、36 choices
  全選 sample-001、欄寬 base、decision table／choices hashes、全新輸出目錄、WINWORD 0、
  修正 commit `515bdd7` 與乾淨工作樹全部符合。正式 `calibrate-list` 隨後執行且只執行
  一次，沒有 retry，15.1 秒後以 exit 0／status `ok` 成功。
- 新 private 目錄恰好只含 `LIST-master.docx`（38,421 bytes，SHA-256
  `6b4fbf74fb10af0bf00e1c00841deea8d80546db60698b8152457873fcc041a5`）與
  `calibration-manifest.json`（3,096 bytes，SHA-256
  `9fa1b84d5a566c000105b0bdd7f3caefee22cc04a26890b4f953925baabd8701`）。manifest master
  hash／共同 normalized fingerprint 完全吻合，base 為 sample-001，三筆 sample evidence
  完整，unsafe token 0，沒有 review；DOCX ZIP signature 正確，三份來源 hash 不變，
  WINWORD 0。Gate C 已正式完成，但尚未執行 Gate V 視覺 QA 或 Gate E 端到端 DRAFT。

- 2026-08-17 經明確核准執行且只執行一次正式 Gate C，沒有 retry。結果為
  `CALIBRATION_MANIFEST_INVALID`、stage `validate-master`；這同時證明真實 Word SaveAs2、
  temporary master 建立／size／dynamic-token／hash 檢查及 master fingerprint comparison
  均已通過。全新 private 目錄只含 373-byte `calibration-review.json`，SHA-256
  `7d3780bf68f5932eab8272aee8f1a85fadceed8f4c8e0eecdf0bcf7e5101c3fa`；unsafe token 0、
  master／manifest 0、WINWORD 0，三份來源依 decision table SHA-256 後驗全部不變。
- 離線根因為 `build_calibration_manifest()` 把三份彼此不同的 pre-normalization fingerprints
  寫入 sample evidence，違反 manifest 要求三份 normalized fingerprints 必須等於已驗證
  master target 的 invariant。新增紅測重現相同錯誤後，改為每份 evidence 保留各自 source
  SHA／day count，但共同記錄核准的 target fingerprint；targeted suite 已全綠，完整離線
  suite 為 `504 passed, 3 skipped`，compileall 與 `git diff --check` 通過。

- 2026-08-17 為避免再做一輪只診斷不交付的 Word 回合，已把正式 `calibrate-list` 的
  post-Word validation／publish 路徑改為 fail-safe：成功時仍直接建立經驗證的 master 與
  manifest；失敗時只 exclusive-create private-safe `calibration-review.json`。固定錯誤碼涵蓋
  invalid calibration report、master missing／size mismatch／dynamic content／hash failure、
  manifest invalid 與 publish failed；不記 raw exception、來源路徑／檔名或內容，partial
  master 仍會回滾。
- 新增 core 與 CLI 防回歸測試，證明 malformed Word report 會定位在 `validate-master`、
  回傳 `needs_review`、只保留 source hashes 與固定 code／stage，且不建立 master／manifest。
  Targeted suite 全綠；完整離線 suite 為 `503 passed, 3 skipped`；compileall、
  `git diff --check`、長行檢查通過。

- 2026-08-17 唯一一次 `diagnose-sample-001-working-copy` 已執行且沒有 retry；命令回傳
  `needs_review`、classification `NOT_REPRODUCED`，checkpoint phase／operation 均為
  `complete`，HRESULT `0x00000000`、adapter code `NONE`。這證明 sample-001 的既有
  normalization mutation 可在 Word `16.0` 的 temporary working copy 完整跑到
  `SaveAs2` 前。
- 新 private 目錄只含 717-byte `sample-001-working-copy-diagnosis.json`，SHA-256
  `f6ad8fa982a467b9b3c6e92d7c1a638d16436ceaed02fffcf6e37bd4506c9ebb`；private-unsafe
  token 命中 0、master／manifest 0、working-copy cleanup 為 true。後驗 sample-001
  SHA-256 仍為 `c230eb24397124cbf0fc6940765be14a9e5a07742f64039f0c01d60f05420b76`、
  size 77,824 bytes，WINWORD 0。原始 Gate C `INTERNAL_ERROR` 因此進一步縮小到
  `SaveAs2`、master validation 或 publish，不再包含 normalization mutation。

- 2026-08-17 已依核准範圍完成 `diagnose-sample-001-working-copy` 的離線實作；執行真實
  Word 診斷前先完成 commit。命令嚴格綁定 decision table 的 sample-001 hash、36 個已完成
  choices 全選同一來源，且 schema-2 Word job 只建立 temporary working copy、沿用既有
  normalization mutation 並在 `SaveAs2` 前返回；`finally` 必須刪除 working copy，來源 hash
  若變更或 working copy 殘留均 fail closed。CLI 只允許在全新 private 目錄 exclusive-create
  一份 private-safe checkpoint／HRESULT report，不存在 master／manifest 參數或 publish 路徑。
- 新增 adapter、helper 與 CLI 邊界測試，包括 exact job schema、單次呼叫、來源異動拒絕、
  working-copy cleanup，以及 calibration fail sentinel。targeted suite 全綠；完整離線 suite
  全綠，PowerShell parser、compileall 與 `git diff --check` 均通過。

- 2026-08-17 唯一一次 `diagnose-normalized-gate-c-failure` 已執行且沒有 retry；命令以預期
  `needs_review`／exit 20 結束，classification 為 `PRE_MUTATION_PATH_CLEAR`、stage 為
  `compare-normalized-layout`。這證明真實 `inspect-v2`、source／choice binding、八欄位
  allowlist、sample-001 base、common profile 與 normalized fingerprint 計算全部通過；
  selected base 確實為 sample-001，fingerprint 為
  `c5786b598f981789a5dc856129d11435bc2e9ab9de665a7f1b5b5008f2e1cd0a`。
- 新 private 目錄只含 680-byte `normalized-gate-c-failure-diagnosis.json`，SHA-256
  `b6d3f3fd63ac3f2600f17c39acfa6f18959e57c4a1dfca5887e29e8ef0841463`；unsafe token
  命中 0、error 為 null、master／manifest 0。後驗三份來源 hash／size 不變、WINWORD 0。
  因此先前 `INTERNAL_ERROR` 已縮小到 working-copy calibration、SaveAs2、master validation
  或 publish，不能再歸因於 comparison。

- 2026-08-17 經明確核准新增 `diagnose-normalized-gate-c-failure` read-only CLI：只執行一次
  schema-2 `inspect-v2` 與純 Python normalized comparison，停在任何 working-copy 或
  `calibrate` Word action 前。report 只允許固定 stage／classification、source hashes、Word
  version、selected base／fingerprint 與 allowlisted exception type／code／field paths；不含
  raw exception text、來源路徑／檔名、文件內容或 master。
- Synthetic 測試以 calibration fail sentinel 證明 diagnosis 不會呼叫 calibration function；
  targeted regression 為 `72 passed in 1.77s`，完整離線回歸為
  `497 passed, 3 skipped in 9.01s`，compileall 與 `git diff --check` 通過；sandbox-safe
  basetemp 已清除。

- 2026-08-17 真實 Gate C preflight 通過：三份來源依 decision-table 順序各唯一匹配，
  hash 與 `77,824／81,408／86,016` bytes 不變；decision table SHA-256 為
  `995130a3b8e5a27c0a52b629ef53e3c1d79761bbd58ff43ee415eca7cccdfb27`，completed choices
  SHA-256 為 `55946dad8d35fad300e1a48245f899263609a7ebc4995406a8e5c297e344b970`；
  pdftoppm 可用、新目標不存在、WINWORD 0。
- 唯一一次 `calibrate-list` 隨後執行且沒有 retry，19.3 秒後回傳
  `{"status":"error","error":{"code":"INTERNAL_ERROR","message":"Unexpected internal error"}}`。
  後驗新目標目錄不存在、master／manifest 皆 0，三份來源仍各唯一匹配原 hash／size，
  WINWORD 0；因此沒有未知寫入，但 CLI 已折疊原始 Python 例外，本回合證據不足以判定
  根因。不得把此結果宣稱為 Gate C 成功，也不得在沒有新核准時重試 Word。

- 2026-08-17 OP 明確確認欄寬也選 sample-001。新增 fail-closed Gate C 單一來源 normalization
  整合：`calibrate-list` 的 decision table、completed choices 與 width-base sample 必須一起
  提供，三份即時 source hash 順序必須吻合，36 個 component choices 與 width base 必須
  全部指向同一 source；任何新的非既知八欄位 conflict 仍在 Word mutation 前阻塞。
- 選定來源的完整 schema-2 normalized layout 成為 master target；既有 source-mutation、
  dynamic-token、exclusive-create、master fingerprint 與 manifest validation 均未放寬。
  Targeted regression 原文為 `71 passed in 1.83s`；完整離線回歸改用專案內 sandbox-safe
  basetemp 後為 `496 passed, 3 skipped in 7.80s`，compileall 與 `git diff --check` 通過。
  預設 pytest temp 的第一次完整回歸因 Windows sandbox `WinError 5` 無法建立 tmp_path，
  不是程式測試失敗；本次建立的專案內 basetemp 已清除。

- 2026-08-15 使用者明確核准「一次新的 Gate C 真實校準」。唯讀 code／STATUS preflight
  發現現有 36-choice validator 尚未接入 `calibrate-list` 或 Word normalization job；直接
  執行只會重現已知 `compare-samples` 衝突，因此沒有消耗真實 Word 校準回合。
- 36 個 component choices 可覆蓋 font、paragraph、border、daily-header、shape 與相關
  digest 衝突，但 worksheet 漏列獨立的 `table_column_widths_points`。既有 private-safe
  證據顯示 sample-001 四表總寬為 `563.6／556.7／556.35／556.7 pt`，sample-002／003
  為 `558.25／556.7／556.35／556.7 pt`，第 2–4 表內部亦有部分欄位重新分配；不能自行
  平均、視為 derived 或假設 OP 已選。尚需一個明確 width base 決策後才能補最小整合實作。

- 2026-08-15 OP 明確指示「就選 sample 1」；13 個 review groups 全部展開為 36 個 exact
  decisions，均選擇 eligible `sample-001`。G05 的 sentinel 位於 sample-002，因此本次選擇
  沒有觸及 ineligible option。
- 在既有 private review 目錄 exclusive-create
  `normalization-choices.op-selected.json`（10,583 bytes，SHA-256
  `55946dad8d35fad300e1a48245f899263609a7ebc4995406a8e5c297e344b970`）；原 worksheet 與
  blank artifact SHA-256 維持不變。
- 獨立 read-back strict validation 為 `PASS`：36 choices、selected source 唯一且全為
  sample-001、decision-table SHA-256 綁定正確。未啟動 Word、未執行 calibration，
  WINWORD process 0。

- 2026-08-14 只讀真實 private-safe worksheet，依相同 decision family、component pattern、
  changed properties、三份 safe values 與 eligibility 將 36 decisions 整理成 13 個 OP
  review groups。沒有使用多數決、沒有選 base、沒有填 blank choices，也沒有新增 private
  artifact、啟動 Word 或進入 Gate C。

- 2026-08-14 經當次明確核准，只讀取唯一且 SHA-256 符合 STATUS 紀錄的
  `component-diagnosis.json` 與 `normalization-decision-table.json`，執行一次
  `prepare-list-normalization-choices`；未讀原始 LIST、未啟動 Word，也未執行 diagnosis
  或 calibration。
- 全新 private 目錄只含 `normalization-choice-worksheet.json`（60,473 bytes，SHA-256
  `5683469da2c788982b3b8145fdbf5cc2c3c58bb5630f34d2089bbe30268da517`）與
  `normalization-choices.blank.json`（5,975 bytes，SHA-256
  `43c81418254d6b7e15dfe56e6c66b16809cf7eb134492fb67de218fd0f6e61a4`）。
- 真實 worksheet 分類為 `BLOCKED_MIXED_VALUE`，含 36 decisions、7 derived audits、
  0 blockers、108 options；固定 sample-001／002／003，其中 1 個 sentinel option 標成
  ineligible。36 個 blank choices 全未填；unsafe filename/path/recommendation token 命中 0。
- 後驗重建驗證顯示 worksheet 與 blank artifact 均 exact match；兩份來源 report SHA-256
  維持不變，WINWORD process 0。private artifacts 未加入 Git。

- 2026-08-14 新增 strict decision-table reader 與
  `prepare-list-normalization-choices` 純離線 CLI；它只接受互相吻合的 component report
  與 decision table，在全新 private 目錄 exclusive-create worksheet 與 blank choices。
- Worksheet 固定使用 sample-001／002／003，只呈現 source/component SHA-256、changed
  properties 與 allowlisted numeric／enum／digest values；不含來源檔名、路徑或推薦，
  sentinel option 保留證據但標成 `eligible_as_base: false`。
- 本回合只用 synthetic artifacts，未讀既有 private reports、未啟動 Word、未執行
  diagnosis 或 calibration。targeted tests 為 `69 passed`；完整離線回歸為
  `494 passed, 3 skipped in 7.63s`，compileall 與 `git diff --check` 通過；venv 未安裝 Ruff。

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
- Task 1 已提交並推送：commit `30fd146`，本機與 `origin/main` SHA 一致。
- 2026-08-09 完成 Task 2 技術切片：新增 narration 分段與文字 SHA-256、最多兩行的
  frame-timed SRT、PCM WAV 驗證／串接、MP3 轉檔契約與本機能力模組。
- 新增 Windows Speech adapter 與 `scripts/briefing/synthesize_hanhan.ps1`；PowerShell
  command line 只接收 UTF-8 JSON 工作檔路徑，不接收講稿文字，使用
  `Microsoft Hanhan Desktop`、rate `-1`、44.1 kHz／16-bit／mono PCM。
- 真實 Hanhan integration test 已啟用實跑為 `1 passed`；一般完整離線測試會明確
  skip 此 opt-in 測試，最終 staged release gate 為
  `118 passed, 1 skipped in 4.30s`。
- unknown speech／ffmpeg 結果只執行一次，先檢查已產生片段／檔案大小再 fail closed；
  已有輸出會在 adapter 呼叫前拒絕覆蓋。
- 正式試聽資料位於 Git 忽略的
  `output/briefings/SYNTHETIC-HANHAN/20260809-task2-sample-v2/`，包含 WAV、SRT、
  TXT 與 metadata；內容為 105 字的純合成 fixture，無真實團號、姓名或電話。
- 試聽 WAV 實測為 1,322,530 frames、29.989342 秒、2,645,104 bytes；WAV SHA-256
  為 `a2a8631b29927a7a0ee7b2d5c05a2f128e5642fe52299231e2b0fb8563585b39`。
- sample-v2 QA 結果為 `RESULT: OK`：SRT 結尾與 frame 時間同為 29,989 ms、4 個
  段落邊界連續、WAV／SRT／TXT／canonical narration 共 4 個 hash 全相符。
- 使用者實際聆聽後判定 Hanhan 不自然且停頓明顯；量測四個句間長停頓為約
  820、970、890、970 ms，整篇一次 Hanhan 合成仍有相同停頓，因此不是 WAV
  串接額外插入的錯誤。
- 同稿本機 Yating 對照 WAV 已產生並解碼驗證：26.087250 秒、16 kHz、PCM
  16-bit／mono，SHA-256
  `d538b0a4d8d4f98d9bfc7758fbfbe720c6b868d249d6a43bed64b3e91851b519`；使用者判定
  Yating 較好。
- 使用者選定 Yating 為唯一自動本機聲音；目標電腦缺少 Yating 時阻擋音訊，
  不自動退回 Hanhan。使用者表示目前沒有 Azure Speech 資源，因此第一階段不建立、
  不設定也不呼叫 Azure。
- 已修訂 `docs/specs/2026-08-08-travel-briefing-document-audio-design.md`：Yating
  採整篇連續合成並以零時長 SSML bookmarks 建立 SRT；bookmark 或音檔驗證不符
  即 fail closed。
- 實機 probe 顯示 Yating 的自動 sentence／word boundary metadata 皆回傳 0 個
  marker，但 SSML `<mark>` 可正確回傳 `Speech:Bookmark`；三句測試取得兩個
  1,496 ms／3,026 ms markers，且有無 bookmarks 的 WAV byte count 同為 146,654。
- 使用者已書面確認 Yating 修訂設計；原實作計畫已改成 Yating-only 第一階段，
  新增 Task 2B 的連續 SSML bookmark 管線，並正式取消 Azure Task 7。
- 修訂計畫把下一個核准範圍限制為 Task 2B 的本機程式、離線／opt-in 整合測試及
  20–30 秒正式管線樣本；完整 6–8 分鐘音訊與外部關卡不隨計畫核准自動開啟。
- 計畫自檢為 12 個 Task headings（2 完成、1 取消、9 待執行）、11 個 commit
  邊界、0 個未定欄位，且 6 個舊 Azure／auto-Hanhan 可執行片語均不存在。
- 本次 Yating 計畫修訂後完整離線回歸為 `118 passed, 1 skipped in 5.12s`；skip
  仍是需顯式 opt-in 的真實 Hanhan integration test，沒有拿 skip 當 Yating 驗收。
- ffmpeg 未設定，因此 metadata 正確標示 `MP3_CONVERTER_UNAVAILABLE`；沒有安裝、
  沒有嘗試轉 MP3，已驗證的 WAV／SRT／TXT 均保留。
- 該 Yating 計畫修訂階段沒有 live 官網／JMA、Azure、LINE、Word COM 啟動或外部部署。
- 2026-08-09 使用者明確核准 Task 2B；以 TDD 完成 Windows Media Speech
  `Microsoft Yating` 整篇單次 SSML 合成，第二段起插入唯一 bookmark，並由真實
  `Speech:Bookmark` 時間建立連續 SRT。
- 新增 `windows_media_speech.py` 與 `synthesize_yating.ps1`；Python command line
  只帶 OS temp 中的 UTF-8 JSON job 路徑，PowerShell 僅精確選用
  `Microsoft Yating`／`zh-TW`，保留預設韻律，不呼叫 Hanhan、Azure 或網路。
- WAV 會實際解碼並要求 PCM、16-bit、mono、正取樣率與正 frame；取樣率不硬編碼。
  缺少、重複、未知、倒序、越界或經毫秒換算後無效的 bookmarks 一律阻擋 SRT，
  timeout／失敗只檢查暫存輸出一次，不重試也不 fallback。
- 最終 WAV／SRT／TXT／metadata 全部 exclusive create；metadata 記錄 voice、engine、
  WAV header、marker count、narration／artifact hashes，並明確標示
  `MP3_CONVERTER_UNAVAILABLE`。
- `briefing doctor` 實機只列舉 Windows Media `AllVoices`，已確認 Yating 可用；
  Hanhan 標為 `legacy_comparison_only`，已取消的 Azure 環境變數不再造成假 warning。
- opt-in 真實整合測試結果為 `1 passed`；最後完整離線回歸為
  `144 passed, 2 skipped in 6.85s`，兩個 skip 分別是需顯式 opt-in 的 Hanhan 與
  Yating 本機整合測試；`git diff --check` 通過。
- Task 2B 功能、測試與計畫狀態已提交於 commit `2fe8e7c`。
- Task 2B 自然度政策與人工驗收決策已提交於 commit `72e22c8`。
- 正式管線樣本位於 Git 忽略的
  `output/briefings/SYNTHETIC-YATING/20260809-task2b-sample-v1/`。獨立 QA 為
  `RESULT: OK`：26.087250 秒、16 kHz、PCM 16-bit／mono、417,396 frames、5 段
  SRT／4 bookmarks，SRT 與 WAV 結尾同為 26,087 ms。
- 新樣本 WAV SHA-256 為
  `d538b0a4d8d4f98d9bfc7758fbfbe720c6b868d249d6a43bed64b3e91851b519`，與使用者
  選中的 `02-Yating-local.wav` 完全相同；SRT SHA-256 為
  `75a936538f95f0ecfb234cab56a6c2eef3a3ce1f9defbf2f1e1bcffc49b97d67`。
- 使用者指出 14.925 秒起「不舒服」的「服」音調略怪，並確認不應針對單字改稿
  或累積發音特例。正式政策改為：不看逐字稿仍能理解且不改變意思的偶發怪腔可
  接受；聽不清、可能改變語意或誤認關鍵資料時才阻擋；跨樣本重現才升級為整體
  韻律／引擎評估。使用者已依此原則通過 Task 2B 人工驗收。
- Task 2B 階段仍未安裝 ffmpeg、未產生 MP3／完整 6–8 分鐘音訊、未啟動 Word COM，亦未
  呼叫 live 官網／JMA、Azure、LINE 或任何外部發布。
- 2026-08-09 使用者以「繼續進行」核准既定 Task 3；新增
  `script_policy.py`、`script_validation.py` 與 canonical narration policy reference，
  沒有修改 Yating 合成器或生成完整語音。
- `build_narration_input()` 由 `BriefingDraft` 產生固定八段與來源綁定的
  `required_facts`；核心涵蓋小費、人數、不可脫隊、巴士時數、保險、護照效期、
  房型、素食、電壓及天氣提醒。缺值、未知來源／分類、未確認 OP 欄位、未解衝突、
  BLOCKED 草稿與未知專名一律進 review，不補猜。
- `check_script()` 要求八個 exact markers 依序各出現一次，保護事實子句與所有關鍵
  日期／班號／時間／金額／人數／時數／效期／百分比／電壓，並阻擋相反語意、
  未核准數字及爭議值。驗證 JSON 不回吐講稿；序列化的禁用值只留 SHA-256 與字數。
- 合成前字數估計採已通過 Yating 短樣本的 3.6 可發音字元／秒，只是 warning；
  `validate_audio_duration()` 仍以實際 WAV 秒數判斷 360–480 秒。第一次過短／過長只
  允許固定規則補充／壓縮一次，第二次仍超界即 blocked 並轉人工 review。
- 發音表只涵蓋班號、機場代碼、日期、金額、電壓與大阪／東北／北海道常見地名；
  未知詞保留原字進 review。依使用者決策，沒有為「不舒服」的「服」或其他一般字
  建立逐字補丁。
- Task 3 功能 commit 為 `02f91c5`。完整離線回歸實測為
  `171 passed, 2 skipped in 5.66s`；兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests，Task 3 測試沒有 skip；compileall 與 staged
  `git diff --check` 均通過。
- 使用者於完成回報後明確回覆「通過」；Task 3 人工驗收已關閉。這項通過當時不包含
  Task 4、live 官網／JMA、完整 6–8 分鐘音訊或任何其他後續關卡。
- Task 3 階段沒有 live 官網／JMA request、Word COM、ffmpeg 安裝、MP3、完整 6–8 分鐘
  音訊、Azure、LINE、Cowell access 或任何部署／外部發布。
- 2026-08-09 經使用者核准完成說明會產生器 Task 4：新增 HTTPS
  `www.newamazing.com.tw` URL／redirect allowlist、語意式 NewAmazing HTML parser、
  保留頁碼的 PyMuPDF 文字擷取與 PDF parser，以及產品代碼唯一候選決策。
- NewAmazing parser 以產品資訊、航班資訊、每日行程及其他說明 anchor 定位；必要
  anchor 缺少時回報 `PARSE_CONTRACT_CHANGED`。無文字 PDF 回報
  `PDF_OCR_REQUIRED`，沒有暗中加入 OCR。
- Task 4 fixtures 只有合成 HTML 與去識別頁面文字；PDF extractor 測試使用測試期間
  產生的暫存 PDF。沒有提交來源 PDF、完整官網頁面或 live response。
- Task 4 的 34 個針對性測試通過；完整離線回歸實測為
  `205 passed, 2 skipped in 6.10s`。兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests；compileall、行寬檢查與 staged `git diff --check` 均通過。
- Task 4 依計畫只新增 `beautifulsoup4>=4.12,<5`；本機 venv 實裝 4.15.0。
  額外執行 `pip check` 時發現既有 `keyring` 依賴未安裝；這不是 Task 4 引入，且
  本次未擴充範圍補裝，完整測試仍全綠。
- Task 4 功能 commit 為 `cc547f9`。完成該離線 commit 時尚未對新魅力官網發出
  request，且 commit 不含來源頁面或 live response。
- 2026-08-09 使用者另行核准對已提供的大阪產品 URL 執行一次 live 唯讀契約測試。
  實際只發出 1 個 GET、沒有 redirect 或 retry；HTTP `200`、response `98,076`
  bytes、SHA-256 `06335de9cfee88e4a33248a6ead9950eaeebdab735ea2542806ca2ff8e3aaf61`。
- 該 live response 在「產品資訊」anchor 回報 `PARSE_CONTRACT_CHANGED`，因此真實
  URL 自動解析目前仍 blocked。沒有保存原始 HTML；單次 live 授權已用畢。
- 2026-08-10 經逐次明確核准完成最小 live 結構診斷：正式頁採
  `.product_basic_info`、`#ReferenceFlights`、`#DailyItinerary .every_day` 卡片契約，
  列印控制仍指向同一頁，沒有另一個穩定列印頁。每次授權只執行一個 GET，未保存
  原始 HTML、旅客資料或 live response。
- NewAmazing parser 已升為 `newamazing-html/2`：保留舊契約，新增嚴格卡片 profile，
  驗證產品名稱／代碼、URL 代碼、航班欄位與首末日期、每日天次、餐食、飯店及其他
  說明；必要欄位漂移仍回報 `PARSE_CONTRACT_CHANGED`。
- 正式頁沒有獨立的每日住宿城市欄位，parser 不從標題猜城市。URL-only 會留下
  `SOURCE_CITY_MISSING` warning；URL+PDF 會保留 PDF 城市供 OP 核對，不製造假衝突。
- 修復只加入純合成卡片 fixture，沒有把正式產品代碼、完整頁面、電話、email 或 PII
  寫入原始碼。修復後尚未再發出 live GET，因此不能宣稱正式 URL 已驗收可用。
- NewAmazing／merge 針對性測試為 `29 passed in 0.36s`；完整離線回歸實測為
  `244 passed, 2 skipped in 5.78s`。兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests；compileall、行寬檢查與 `git diff --check` 均通過。
- 卡片結構修復 commit `5e8fed9` 已於 2026-08-10 push 至 private `origin/main`。
- 2026-08-10 經使用者明確核准執行恰好一次修復後正式頁 GET；未跟隨 redirect、
  未 retry，HTTP `200`、response `98,468` bytes、SHA-256
  `2e7a3403a64706b0ab272c22ac2559b691b1048caf7e680149247b7ef9de5e68`。
  parser 已進入新版卡片 profile，但在「產品區域」回報
  `PARSE_CONTRACT_CHANGED`。沒有保存原始 HTML 或 live response；該次授權已用畢。
- 2026-08-10 使用者核准以 OP 明確確認取代產品代碼、航點或名稱猜測；設計已寫入
  `docs/specs/2026-08-10-travel-briefing-product-region-resolution-design.md`。規格固定
  URL-only 缺區域時使用動態 `product_region` OP 欄位、URL+PDF 保留 PDF 區域、
  未知或矛盾值 fail closed；使用者於 2026-08-11 明確回覆「通過」。
- 2026-08-11 依通過規格完成區域確認：NewAmazing／PDF parser 在來源未明示區域時
  保留空值、多區域仍 fail closed；merge 只建立一個 `SOURCE_REGION_MISSING` warning，
  由唯一有值的來源補足，或在兩者都缺時附加黃色 `product_region` OP 欄位；兩個
  非空區域不一致仍建立 blocking conflict。parser evidence 版本分別升為
  `newamazing-html/3` 與 `pdf-itinerary/2`。
- `apply_op_values()` 只在草稿已要求 `product_region` 時接受大阪／東北／北海道，
  更新產品與 OP provenance 並重算 `draft_id`；未知值及未要求的 override 均拒絕。
- 區域確認針對性測試為 `57 passed in 0.54s`；完整離線回歸實測為
  `258 passed, 2 skipped in 6.03s`。兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests；compileall、行寬檢查與 `git diff --check` 均通過。
- 設計與實作 commits `3aa59fe`、`239a713` 已於 2026-08-11 push 至 private
  `origin/main`，本機與遠端均為 `239a713` 後才執行正式頁驗證。
- 2026-08-11 經使用者明確核准執行恰好一次修復後正式頁 GET；未跟隨 redirect、
  未 retry，HTTP `200`、response `98,464` bytes、SHA-256
  `a4077429981bb47c6cbfccae113901a1b3d66b9a4cc069c35fa7e12a8470f216`。
  `newamazing-html/3` 實測解析 2 航班、5 天及 5 項其他說明，產品區域保留空值，
  merge 只建立 1 個 `SOURCE_REGION_MISSING` warning 與 1 個 `product_region` OP
  待確認欄位，狀態為 `DRAFT_READY`，結果 `PASS`。沒有保存原始 HTML 或 live
  response；該次 GET 授權已用畢。
- 2026-08-09 經使用者另行核准完成 Task 5：新增 `merge`、`validation`、`op_values`
  與 `review` seams，落實 PDF／官網 notices／天氣來源優先、blocking conflicts、
  語意等價 warnings，以及 9 個不得猜值的黃色 OP 待確認欄位。
- OP values 與 conflict decisions 都綁定當前 `draft_id`；過期決策 fail closed。
  決策會實際更新 scalar、航班或每日行程資料並重算狀態；review 保留 URL 或 PDF
  basename／頁碼／取得時間，同時遮蔽電話且不洩漏 PDF 目錄。
- Task 5 功能 commit 為 `2bba83f`。34 個針對性測試通過；完整離線回歸實測為
  `239 passed, 2 skipped in 9.67s`。兩個 skip 仍是真實 Hanhan／Yating integration
  tests；compileall、行寬檢查及 staged `git diff --check` 均通過。
- 本次沒有 JMA request、Word COM、ffmpeg 安裝、完整 6–8 分鐘音訊、Azure、LINE、
  Cowell access、部署或外部發布，也未保存任何 live 原始內容。
- 2026-08-11 經使用者明確核准，只讀查閱 JMA 官方產品目錄、XML 技術資料、
  PULL 型取得方式與使用條款；沒有抓取任何實際天氣預報電文。確認 Task 6 短期來源
  為 `VPFD51`、週間來源為 `VPFW50`，兩者從「定時」Atom feed 發現。
- Task 6 最小設計已寫入
  `docs/specs/2026-08-11-jma-weather-enrichment-design.md`：每日城市空白時不猜測，
  固定顯示「尚無短期預報，請於出發前更新」；城市只有唯一 alias 才可對應 JMA
  預報區，overlap 採 VPFD51，JMA 失敗降級但不破壞安全草稿。
- Task 6 設計 commit `10e587e` 與功能 commit `025611b` 已完成：新增標準庫 JMA
  XML parser、官方 HTTPS provenance、VPFD51／VPFW50 產品與時間軸驗證、日本日期
  換算、唯一大阪 alias／測站映射、短期與較新發布優先、矛盾 fail closed，以及
  城市缺漏或超出範圍的固定降級結果；沒有新增 JMA SDK 或網路 fetcher。
- Task 6 針對性測試實測為 `12 passed`；完整離線回歸為
  `270 passed, 2 skipped in 5.64s`。兩個 skip 仍是需顯式 opt-in 的真實 Hanhan／
  Yating integration tests；compileall、行寬檢查與 `git diff --check` 均通過。
- 本次實作只使用 synthetic XML，沒有實際 JMA 預報 request、live response、Word
  COM、ffmpeg 安裝、完整音訊、LINE、Cowell access、部署或外部發布。
- 2026-08-12 經使用者指示繼續開發後，完成 Task 8 的離線 LIST Word 基礎：新增
  `template_contract.py`、`word_list.py`、`word_qa.py`、Windows Word adapter、
  patch／render PowerShell scripts，以及需顯式 opt-in 的私有範本 integration test。
- LIST 契約驗證四表格、八個欄位錨點、合併格座標、四段標題、header QR
  candidate、單 section、A4 portrait 與不含團務／PII 文字的 layout fingerprint；
  5／6／7 天共用 master table 動態增減列，缺值保留黃色 `待 OP 確認`，安全縮寫後
  仍過長即 blocked，不截斷內容。
- Word adapter command line 只帶 OS temp job 路徑；所有權由 nonce、精確 WINWORD
  PID 與 process start time 綁定。逾時只檢查一次暫存輸出、不 retry、不掃描或停止
  其他 Word 程序。PowerShell scripts 為 ASCII-only，中文錨點只從 UTF-8 job 讀取。
- PDF／PNG QA 程式要求單頁 A4、必要文字、非空文字與至少一個圖片物件，再以明確
  設定的 `pdftoppm` 產生單張 150 DPI PNG；正式 DOCX 仍須逐頁人工看圖才能通過。
- Task 8 新增 39 個單元測試；針對性回歸為 `39 passed in 0.78s`，最終完整離線回歸為
  `309 passed, 3 skipped in 8.66s`。第三個 skip 是未授權的私有 LIST／Word
  integration；本次未啟動 COM、未讀私有範本、未產生任何正式 Word／PDF／PNG。
- Task 8 離線實作已本機提交為 `3b8c64a`；因 public remote 阻塞，尚未 push。
- 2026-08-12 接續檢查：`git pull --ff-only` 回傳 `Already up to date.`；本機比
  `origin/main` 多 4 個 commits（Task 6 與 public remote 阻塞紀錄），工作樹當時乾淨。
- 2026-08-12 由接手者重新執行完整離線回歸：`270 passed, 2 skipped in 8.56s`；
  compileall、Python 100 字元行寬檢查及 `git diff --check origin/main..HEAD` 通過，
  待推送範圍未發現產出檔、credentials 或旅客 PII。
- 2026-08-12 兩次 GitHub 即時唯讀查詢均顯示
  `cyber6058/easytravel-cowell-agent` 為 `PUBLIC`／`private: false`，與本專案必須
  private 的規則及先前 STATUS 紀錄矛盾；因此沒有 push，也沒有變更 repo visibility。
- 針對全部 28 個本機 Git commits 的唯讀歷史掃描未發現禁用 artifact 副檔名；3 個
  高可信 credential pattern 命中只位於 PII 掃描器規則與其遮蔽測試 fixture，不是
  實際 credential。這不是完整外洩鑑識，也不代表 repo 曾公開的風險已撤銷。
- 2026-08-12 依使用者指示不變更 GitHub visibility，繼續完成 Task 9 本機離線實作：
  新增受限來源 fetch、artifact store、strict local config、workflow orchestration、
  Word／Yating local backend，以及 `prepare`、`check-script`、`render` CLI。
- 每個 run 只能建立在 `output/briefings/<product-code>/<timestamp>/` 的全新目錄；
  manifest 與來源、artifact、口語稿均以 hash 綁定。部分 render 失敗保留安全 artifact
  並可從目前狀態重試；任意 BLOCKED 狀態、路徑漂移、hash 漂移與重複 artifact 均
  fail closed。
- `render --confirm-draft-id` 要求 exact draft ID、script hash、零 blocking conflict、
  零黃色必要欄位、Word PDF／PNG QA 與完整音訊 artifact；確認只在本機複製並移除
  `DRAFT` 檔名前綴，不重新 render、不傳 LINE、不上傳。
- 外部 HTML 僅可經 allowlisted HTTPS host、最多一次同 host redirect、無 retry 且
  5 MB 上限取得；raw response 只暫存於 OS temp，manifest 僅保存 hash 與證據。本次
  測試全用 synthetic data／mock transport，沒有送出 live request。
- Task 9 最終完整離線回歸為 `358 passed, 3 skipped in 8.51s`；三個 skip 仍是需明確
  opt-in 的 Hanhan、Yating 與私有 LIST／Word integration。compileall、
  `git diff --check`、staged 禁用產出路徑、PII 與 secret 掃描均通過。
- Task 9 程式已本機提交為 `e487db7`；使用者明確指示不改成 private，因此沒有變更
  visibility，也沒有向目前 public 的 `origin` push。
- 2026-08-12 完成 Task 10 本機離線實作：新增 canonical
  `easytravel-briefing-materials` Skill、byte-identical Codex／Claude copies、Codex
  plugin／local marketplace、獨立 briefing pyproject／installer、allowlist build 與
  packaging contract tests。安裝器先驗證必要路徑與範本 fingerprint，再建立自己的
  app／venv／config；不讀 Cowell session 或 credentials，也不覆蓋既有安裝。
- 正式 `render` CLI 測試鎖定只暴露 Yating；Hanhan 腳本不進安裝包。Skill 明確分開
  live source、私有範本／Word COM、Yating、ffmpeg、draft confirmation 與外部傳送關卡，
  並禁止猜值、雲端 TTS、自動 LINE、影片、部署與發布。
- 三份 Skill validator 皆回傳 `Skill is valid!`；plugin validator 回傳
  `Plugin validation passed`。PowerShell parser、compileall、行寬、`git diff --check`、
  staged artifact／PII／secret scan、ZIP allowlist 與 ZIP secret pattern scan 均通過。
- Task 10 最終完整離線回歸為 `365 passed, 3 skipped in 15.74s`；三個 skip 仍是需明確
  opt-in 的 Hanhan、Yating 與私有 LIST／Word integration tests。
- 本機套件為 `dist/EasyTravel-Briefing-Materials-0.1.0.zip`，SHA-256：
  `14db8cc9e7e8ce9c90eec37a62069b59f018f940674e795c18f88339b4ab93e5`；ZIP 有
  67 個 archive entries，未含 Cowell、credentials、私有來源、範本或生成 artifacts。
- Task 10 實作已本機提交為 `0daf457`。本次未安裝套件、未改 GitHub visibility、
  未 push，也未執行 live URL／JMA、私有範本、Word COM、Yating、ffmpeg 安裝、LINE、
  Cowell、部署或外部發布。
- 2026-08-12 經使用者明確核准 Task 11 第一關，只在新的 OS temp root 解壓及安裝
  `EasyTravel-Briefing-Materials-0.1.0.zip`；安裝時把 `LOCALAPPDATA`／`USERPROFILE`
  指向該 root，並使用 `-SkipCodexPluginInstall -SkipClaudeSkillInstall`，沒有改動使用者
  現有 Codex／Claude 設定。範本是當次建立的純 synthetic DOCX，沒有讀私有 LIST。
- ZIP SHA-256 重驗仍為
  `14db8cc9e7e8ce9c90eec37a62069b59f018f940674e795c18f88339b4ab93e5`；Python
  3.14 暫存 venv 成功安裝 briefing 0.1.0、Beautiful Soup 4.15.0、httpx 0.28.1、
  PyMuPDF 1.28.2 與其依賴，`pip check` 回傳 `No broken requirements found.`。
- 已安裝的 `briefing --version` 回傳 `briefing 0.1.0`；`render --help` 只暴露
  `--tts {yating}`。config 可從隔離的 `LOCALAPPDATA` 載入 synthetic `.docx`、output
  root、layout hash 與現有 `pdftoppm`；`cowell_cli` 不可匯入，且安裝包沒有 Hanhan
  script。
- 安裝器執行的 `doctor` 與後續 JSON probe 均實測 Python／Windows／Yating voice
  enumeration／Word registry／pdftoppm 為 ok；ffmpeg 未設定所以整體狀態為 warning。
  這不代表 Word COM 已啟動、Yating 已合成或 MP3 已驗收。
- 對同一隔離目錄重跑 installer 會以 exit 1 拒絕，訊息為 app already exists；app、
  config 與檔案數均保持不變，證明不覆蓋既有安裝。PyMuPDF 1.28.2 會印出既有
  `fitz` API 未來棄用 warning，未影響本次命令，但應在後續維護處理。
- 驗證後已刪除唯一的 temp root（1,524 files／253 directories）以及本次在 repo
  產生的 pip／PowerShell cache；沒有保留安裝、synthetic 範本或測試 config，也沒有
  live request、Word COM、語音合成、LINE、Cowell、部署、發布或 push。
- 2026-08-12 使用者採用新的全自動使用方式：提供新魅力 URL、行程 PDF 或兩者並
  要求「產生說明會資料」，同一次要求即可啟動該 `draft_id` 的受限來源讀取、私人
  LIST master、Word COM、Yating、pdftoppm 與已設定 ffmpeg DRAFT 管線；正常情況
  不再逐步詢問，只有缺值、衝突、契約漂移或 QA 失敗才集中回報。
- 新設計把三份 `.doc` 定位為一次性格式校準樣本；校準通過後只保留一份私人
  canonical master，依來源實際 N 天複製每日列，不再有 5／6／7 天範本選擇。
  內容在可讀性下限內放不下一頁時自動續頁，續頁重複團體識別與每日表頭，不能
  靠過度縮字、截字或刪除事實硬塞單頁。
- 書面規格為
  `docs/specs/2026-08-12-automatic-briefing-dynamic-list-design.md`；它在使用者複核
  後取代舊設計的 5／6／7 天限定與單頁即阻擋規則。規格自檢沒有 TODO／TBD，
  `git diff --check` 通過。本輪只寫文件，沒有讀取三份私有範本內容、啟動 Word
  COM／Yating、發出 live URL／JMA request、安裝 ffmpeg 或產生任何 artifact。
- 2026-08-13 使用者明確回覆「書面規格通過」；上述動態 LIST 規格正式關閉設計
  複核關卡，規格狀態已同步更新。
- 新增 `docs/plans/2026-08-13-automatic-briefing-dynamic-list-implementation-plan.md`：
  共 12 個 Task／12 個 commit。Task 1–8 是待核准的 repo 內離線程式、測試、Skill
  與 0.2.0 package；Task 9–12 分別是乾淨安裝、三份私有 LIST 校準、4／5／6／7／
  8／12 天 Word 視覺驗收，以及真實一次要求 DRAFT，各自保留獨立核准 gate。
- 計畫明確涵蓋 calibration schema 2、唯一 canonical master、任意正整數天數、
  內容驅動單頁嘗試、安全續頁、逐頁 PDF／PNG QA、nested artifact 驗證、0.1 config
  fail-closed migration，以及 packaged Agent 的一次 DRAFT 授權。
- 規劃前重跑完整離線基線：`365 passed, 3 skipped in 12.92s`；三個 skip 仍是需
  opt-in 的 Hanhan、Yating 與私有 LIST／Word integration。本輪沒有啟用任何一項。
- 2026-08-13 使用者核准 0.2.0 離線 Task 1–8；已依序完成 calibration schema 2、
  受限 Word adapter、任意天數 patch plan、內容驅動單頁／安全續頁、逐頁 QA 與
  artifact tracking、單一 master/manifest config、一次要求的一個 bounded DRAFT
  Skill 契約，以及 0.2.0 allowlist package。
- Task 1–7 本機 commits 為 `983c29b`、`a665643`、`6e76071`、`70763f3`、
  `31211e8`、`7998cb6`、`8fcb0a5`。Task 8 提交前的最終完整離線回歸為
  `437 passed, 3 skipped in 17.28s`；三個 skip 仍是既有 opt-in Hanhan、Yating 與
  私人 LIST／Word integration，沒有啟動或放寬。
- compileall、100 字元 production Python 行寬、六份 PowerShell parser、三份 Skill
  validator、plugin validator、Skill mirror hash、`git diff --check`、stage/ZIP 禁用
  副檔名與私人 marker scan 全部通過；scan 結果為 0 forbidden stage files、
  0 forbidden ZIP names、0 private marker/key hits。
- 0.2.0 套件為 `dist/EasyTravel-Briefing-Materials-0.2.0.zip`，SHA-256：
  `d0affb3403b0c622a74caf218182f46dd46ab6bb275ee6254710a3a0c7d818fc`；stage 有
  63 files、ZIP 有 68 entries，不含 `.doc`／`.docx`、來源 PDF、私人 calibration
  manifest、來源 hash、Cowell 或 Hanhan script。
- 2026-08-13 使用者另行核准 Gate I；開始前先以 `PIP_NO_INDEX=1` 建立兩個隔離
  preflight venv。`--no-build-isolation` 路徑回報
  `BackendUnavailable: Cannot import 'setuptools.build_meta'`；installer 同等的 build
  isolation 路徑回報 `No matching distribution found for setuptools>=75`。這證明
  0.2.0 的乾淨安裝需要該次網路下載，原 Gate I 核准沒有明示此權限，所以未自行
  連線、未開始正式安裝。兩個 probe 各有 869 files／134 directories，均已完整刪除；
  沒有讀私人 LIST、啟動 Word／Yating、寫入真實 LOCALAPPDATA／USERPROFILE 或 push。
- 2026-08-13 GitHub 即時重驗仍為 `PUBLIC`／`private: false`；使用者在收到明確警告
  後仍指示「直接push」。此動作違反私人產品只能推送到 private repo 的規則，依
  使用者當次明確要求執行；後續是否成功只以遠端 `main` SHA 為準，不以命令意圖
  冒充完成。push 前由彙整者親自重跑完整離線測試：
  `437 passed, 3 skipped in 20.65s`；`git diff --check` 通過，分支為
  `0 behind / 21 ahead`。
- 首次例外 push 實際輸出為 `c31876f..39d37d9  main -> main`；隨後以
  `git ls-remote origin refs/heads/main` 驗證遠端完整 SHA 為
  `39d37d92fa0e2ef1cf32ce195013f902f3b6433f`，與本機 HEAD 相同，分支為
  `0 behind / 0 ahead`。GitHub visibility 重驗仍為 `PUBLIC`／`private: false`。
- 2026-08-13 重新接手時先抓取遠端並確認 `origin/main` 已從 `c31876f` 前進至
  `116cb97`；舊工作階段未完成且已被遠端正式 JMA 實作取代的草稿，完整保存在
  本機 `stash@{0}`（`codex-wip-before-116cb97-sync`），沒有套回或覆蓋新版檔案。
- 同步後由接手者親自跑完整離線回歸，首次結果為
  `1 failed, 436 passed, 3 skipped in 7.16s`：PyMuPDF 1.28.2 匯入舊 `fitz` API 時
  把棄用警告寫到 stdout，導致 `briefing doctor --format json` 的 subprocess 輸出
  不再是純 JSON。已將 PDF itinerary 與 Word QA 的 production／test imports 改為
  官方 `pymupdf` module（保留區域 alias `fitz`，不改行為或資料契約）。
- 修正後針對性回歸為 `24 passed in 1.35s`，`briefing doctor --format json` 實際
  stdout 可直接解析；最終完整離線回歸為 `437 passed, 3 skipped in 7.11s`，
  compileall 與 `git diff --check` 均通過。三個 skip 仍是需顯式 opt-in 的 Hanhan、
  Yating 與私人 LIST／Word integration tests，沒有啟動、放寬或拿 skip 冒充驗收。
- 使用者在再次收到 public repo 範圍提醒後，明確授權只將相容修正 `e0d1b60` push；
  實際輸出為 `116cb97..e0d1b60  main -> main`，隨後 `git ls-remote` 回讀完整 SHA
  `e0d1b60a09f6591913b5c65d9b9714c14f2e1938`，與本機一致、`0 behind / 0 ahead`。
  `gh repo view` 同時重驗為 `PUBLIC`／`isPrivate: false`；此授權不包含 Gate I 紀錄
  commit 或任何後續 public push。
- 以 `e0d1b60` 重建 0.2.0 package：stage 為 63 files，ZIP SHA-256 為
  `faf66fd78e4f4d865668ac16b4c38defbabd5271313baa020c0faa2390881876`。
- Gate I 開始時 PATH、WinGet 目錄、Program Files、常見工具目錄及全磁碟唯讀搜尋均
  證實沒有 `pdftoppm.exe`；使用者另行核准 WinGet 安裝
  `oschwartz10612.Poppler 25.07.0-0`。安裝完成後實跑 `pdftoppm -v` 回傳
  `pdftoppm version 25.07.0`；這是保留於本機的持久工具安裝，不在 temp cleanup 內。
- 使用者明確核准 Gate I 透過 pip 下載 package 宣告的 build/runtime dependencies；
  在唯一全新 OS temp root 解壓 0.2.0，建立純 synthetic master 與完整 schema 2
  calibration manifest，將 `LOCALAPPDATA`／`USERPROFILE` 指向該 root，並以
  `-SkipCodexPluginInstall -SkipClaudeSkillInstall` 安裝，沒有修改真實 Agent 設定。
- 隔離安裝實際下載並安裝 Beautiful Soup 4.15.0、httpx 0.28.1、PyMuPDF 1.28.2
  與其宣告依賴；`pip check` 原文為 `No broken requirements found.`，已安裝命令回傳
  `briefing 0.2.0`，且 `cowell_cli` 不可匯入。
- Gate I JSON doctor 可直接解析；list calibration 與 configured pdftoppm 都為 `ok`，
  master hash 相符，Yating voice enumeration 與 Word registry probe 為 `ok`；ffmpeg
  未設定，因此整體狀態正確為 `warning`。這沒有啟動 Word COM 或執行語音合成。
- config 結構只含 output／template／tools，template 只有 canonical `master_path` 與
  `calibration_manifest`；`render --help` 沒有 `--template`，且只暴露
  `--tts {yating}`。
- 同一 installer 第二次執行以 exit 1／`LIST_RECALIBRATION_REQUIRED` 拒絕覆蓋；
  重跑前後 1,520 files／227 directories、config hash 與 app pyproject hash 全部不變。
  最後刪除唯一 temp root：1,520 files、227 directories、74,354,729 bytes，並回讀
  確認路徑不存在；另刪除本次 sandbox 在 repo 產生的 67 個 pip／PowerShell cache
  files 與 150 個 cache directories，工作樹未殘留測試安裝或 cache。
- Gate I 沒有讀取三份私人 LIST、啟動 Word COM／Yating、發出 live 官網／JMA
  request、安裝 ffmpeg、傳 LINE、存取 Cowell、部署或發布 artifact。
- 2026-08-13 使用者以這台機器的三個精確 absolute paths 核准 Gate C；執行前驗證
  size、mtime 與既定 SHA-256 均相符，且真實 `config.toml` 與固定私人目的目錄均
  不存在，沒有覆蓋既有設定或產物。
- 首次 bounded probe 明確失敗於 Word owner 綁定。診斷證實 Word COM 已啟動，但
  原 PowerShell 錯用 Word 不提供的 `Application.Hwnd`；改為建立不存檔的 hidden
  空白文件視窗，以 `Window.Hwnd` 綁定精確 WINWORD PID／start time，並只回傳
  allowlisted stage、HRESULT 與穩定 error code。修正後 20 秒 probe 實跑成功，回傳
  `{"available": true, "word_version": "16.0"}`；修正 commit 為本機 `6f7cd6f`。
- Gate C 隨後只執行一次 `calibrate-list`，沒有 retry；命令在第一階段 inspect 以
  `WORD_GENERATION_FAILED`／`LIST_HEADER_PARAGRAPHS_CHANGED` 明確停止，對應私人
  review 的 `CALIBRATION_CONTRACT_CONFLICT` 欄位路徑
  `list_header_paragraph_count`。未建立 `LIST-master.docx`、calibration manifest、
  config、PDF 或 PNG，也沒有殘留 WINWORD process。
- 三份來源在校準命令後重算 SHA-256，依序仍為
  `c230eb24397124cbf0fc6940765be14a9e5a07742f64039f0c01d60f05420b76`、
  `84d7db2fa9f01fea2bfb0563a37f78c0aa3993cb972a913506b67496f056420b`、
  `cf62502532344530ec9e0c65161b1fee5624abd6243f32bb6530a1d72cc558bc`。
  固定私人目錄只保留不含文件內容／檔名／路徑的 review JSON；其 SHA-256 為
  `ebd166ea8b83a80cd2ef96c5536d676e672921cafc4a5e47f8d0e6eb4ba99c01`。
- Word ownership 修正的針對性測試為 `15 passed`；最終完整離線回歸為
  `440 passed, 3 skipped in 7.32s`，compileall、兩支 PowerShell parse 與
  `git diff --check` 均通過。三個 skip 仍是需 opt-in 的 Hanhan、私人 LIST／Word
  與 Yating integration；因 master 未建立，真實 Word PDF render 及逐頁視覺 QA
  正確標記為未驗證。
- 使用者另行核准新的 Gate C 唯讀診斷回合，要求保留現有 blocked review 並重查
  相同三份 LIST 的 header paragraph 契約。新增 schema 2
  `diagnose-header-v2` Word action：只接受三個唯一 Word paths，報告只含來源 hash、
  field path、數字型段落結構與固定 label ID；不保存檔名、路徑或實際文字。來源在
  Word 前後都重算 hash，任何變動都 fail closed；額外／未核准 report 欄位會被拒絕。
- 真實唯讀診斷以 Word `16.0` 完成一次：三個 hash 對應的
  `list_header_paragraph_count` 依序為 `5／4／5`，分類為
  `SAMPLE_CONTRACT_CONFLICT`。三份共同結構是第 1 段抬頭、第 2 段 `group_code`、
  第 3 段 `group_name`；差異位於第 4 段至 cell marker 的尾端內容，且該區沒有上述
  固定 label 或 inline shape。此證據只描述結構，不自行判定尾端內容可刪除。
- 新診斷另存於固定私人目錄的 `header-paragraph-diagnostic.json`，SHA-256 為
  `c51f8e43af07239049f88bad0dd7ea6b6931c217ae5bf4161e79970674b30982`；舊
  `calibration-review.json` SHA-256 仍為
  `ebd166ea8b83a80cd2ef96c5536d676e672921cafc4a5e47f8d0e6eb4ba99c01`。
  兩檔均不含來源檔名／路徑／實際文字，且不在 Git 工作樹內。
- 診斷後三份來源 SHA-256 仍與既定值完全相同；沒有 master、manifest、config、
  PDF／PNG 或殘留 WINWORD。診斷功能 commit 為本機 `313cbbc`；針對性回歸為
  `33 passed`，完整離線回歸為 `444 passed, 3 skipped in 7.41s`，compileall、
  PowerShell parse 與 `git diff --check` 均通過。
- 使用者核准修訂 Gate C header paragraph 契約：固定保留第 1–3 段，第 4 段到 cell
  結尾正規化為一個空白 prototype 段。實作保留舊的 exact-four guard，只有 schema 2
  校準 inspection 允許來源尾端為 4–32 段；尾端若重現 `group_code`／`group_name`
  固定 label 或 inline shape 仍 fail closed。修訂 commit 為本機 `a84758b`；
  PowerShell parse 與 `git diff --check` 通過，針對性測試為 `34 passed in 0.54s`，
  完整離線回歸為 `445 passed, 3 skipped in 8.36s`。
- 在全新 exclusive private 目錄執行且只執行一次 `calibrate-list`。結果為
  `WORD_GENERATION_FAILED`，stage `run-action`、HRESULT `-2146822296`
  （`0x800A1768`，Word runtime error `5992`）、adapter code `NONE`；依錯誤碼與目前
  程式路徑，疑似為 schema 2 inspection 存取混合欄寬表格的 `Columns` collection，
  但未取得第二個 Word 回合驗證，因此只記為 `unverified` 推論。
- 失敗後沒有重試。三份來源與兩份舊 review 的 SHA-256 再驗均完全相同，WINWORD
  為 0；沒有 master、manifest 或 config。新 private 目錄只保留
  `calibration-review.json`，SHA-256 為
  `99ab632314cb8a40298bb012ecd02be0de57ab16bd93a95f7212a5b8feae988a`；內容只有安全
  hash、錯誤欄位與未驗證的 candidate field path，不含文件文字。
- 使用者核准一次 Gate C `5992` 細粒度診斷。新增嚴格的 schema 2
  `diagnose-5992-v2` Word job：一次 job 先逐份執行 source inspection，若全數成功才
  依正式 median-day／hash 規則選 base sample，並只在暫存 working copy 執行校準
  mutation。checkpoint 僅允許固定 phase／operation／field ID 與數字座標；report
  拒絕額外欄位、文件文字、檔名或路徑。來源前後均重算 SHA-256，working copy 不
  產生 master 並於 finally 清除。功能 commit 為本機 `146f901`。
- 診斷程式的 PowerShell parser、production Python 100 字元檢查、compileall 與
  `git diff --check` 通過；針對性回歸為 `39 passed in 0.47s`，完整離線回歸為
  `450 passed, 3 skipped in 10.91s`。三個 skip 仍是既有 opt-in Hanhan、私人
  LIST／Word 與 Yating integration，沒有放寬或拿 skip 冒充本次實機診斷。
- 唯一一次實機 `diagnose-5992-v2` 以 Word `16.0` 完成且沒有 retry。它在
  `sample-001`、phase `inspect-source`、operation `table-width-column-item`、
  field path `samples[0].inspection.table_column_widths_points`、table 1／column 1
  精確重現 HRESULT `0x800A1768`／low-word `5992`；完成的 source inspections 為 0，
  base sample 尚未選取。這證實失敗發生在讀取來源的 `Columns.Item(1).Width`，早於
  header tail 正規化及任何 calibration working-copy mutation。
- 安全診斷另存於 private `5992-diagnostic.json`，SHA-256 為
  `92a30ee8d28d67be317d571167293f17cb4dc74bc9f9a241b6070760e7f4dcd2`。診斷後三份
  來源與三份舊 review hash 再驗均完全一致，WINWORD 為 0，仍無 master／manifest／
  config。Word 在專用 runtime root 留下的兩個 Diagnostics log 未讀取內容並已連同
  root 刪除；本回合 2,185 files／887 directories 的測試暫存 root 亦已完整刪除。
- 使用者另行核准 Gate C mixed-width 修正；開工的 `git pull --ff-only` 回傳
  `Already up to date.`。schema-2 欄寬指紋現在固定使用四張表的 prototype rows
  `2／2／2／1` 與 column counts `3／6／7／3`，透過 `Table.Cell(row, column)` 取得
  cell 並讀取 `Cell.Width`，移除已證實會在非均勻表格觸發 `5992` 的
  `Columns.Item(...).Width` 路徑。
- 新增 `table-width-prototype-cell` checkpoint 並保留舊的 width checkpoint operation，
  讓既有診斷 review 維持相容；回歸測試固定上述 prototype mapping，且禁止 schema-2
  inspection 再出現 `Columns.Item` 欄寬存取。
- 修正的針對性回歸為 `40 passed in 0.47s`，完整離線回歸為
  `451 passed, 3 skipped in 8.72s`；PowerShell parser、compileall、production Python
  100 字元行寬檢查與 `git diff --check` 均通過。三個 skip 維持既有 opt-in
  integrations，沒有放寬測試。
- 本修正回合未讀三份真實 LIST、未啟動 Word、未校準，也未建立或改動 master、
  manifest、config、QA 或任何 private review；結束檢查 WINWORD 為 0。專用 synthetic
  測試暫存目錄已精確刪除並確認不存在。
- 使用者另行核准真實 Gate C 校準；開工的 `git pull --ff-only` 回傳
  `Already up to date.`。執行前重新確認三份來源的 size、mtime 與既定 SHA-256 全部
  相符，四份既有 private reviews 的 SHA-256 也完全相符；全新 exclusive private
  目錄、config、master、manifest 與 runtime root 均不存在，WINWORD 為 0，
  `pdftoppm version 25.07.0` 可用。
- 在 `list-calibration-v3-mixed-width` 執行且只執行一次 `calibrate-list`，沒有 retry。
  命令明確回傳 `WORD_GENERATION_FAILED`、stage `run-action`、HRESULT
  `-2146822297`（`0x800A1767`，Word runtime error `5991`）、adapter code `NONE`。
- Microsoft 的 Word table 文件指出，非均勻或含垂直合併儲存格的表格不能安全地個別
  存取 `Rows`；目前 schema-2 inspection 在 prototype cell widths 後的第一個候選為
  operation `table-format-row`、field path `samples[].inspection.style_digest` 與
  `table.Rows.Item(...).Range`。本次 coarse calibration report 沒有 checkpoint，因此
  以上只記為 `unverified` 推論，未擅自修正或再次啟動 Word。
- 校準後三份來源與四份既有 reviews 的 SHA-256 均完全不變，WINWORD 為 0；沒有
  master、manifest、config、PDF 或 PNG。新 private 目錄只保留安全的
  `calibration-review.json`，SHA-256 為
  `5835e1397a59f7b58d9c734568d658a3d445e2704c00e16b95a58634d27b8e61`；檔案不含
  LIST 檔名、Downloads 路徑、source path 欄位或文件文字。
- 專用 runtime root 共有 208 files／39 directories／9,951,797 bytes；兩個 Word
  Diagnostics logs 未讀取內容，已連同 Python caches 精確刪除並確認 root 不存在。
  本回合沒有程式碼變更，因此沒有重跑測試；最近完整離線結果維持
  `451 passed, 3 skipped in 8.72s`。
- 2026-08-13 依「繼續開發」授權完成 Gate C vertically-merged-row 離線修正；開工的
  `git pull --ff-only` 回傳 `Already up to date.`。schema-2 inspection 的四表格式、
  daily header 與 daily body prototype 指紋全部改由固定 cell 座標取得，移除該函式及
  新 helper 對 `Rows.Item(...).Range` 的依賴；舊 checkpoint operation 仍保留相容性，
  新 cell checkpoint 已加入嚴格 allowlist。
- 新增防回歸測試，固定 prototype rows `2／2／2／1`、column counts `3／6／7／3`，
  並禁止 schema-2 inspection 與格式 helper 出現 `Rows.Item`。針對性測試為
  `41 passed`；完整離線回歸為 `452 passed, 3 skipped in 7.28s`，PowerShell parser、
  compileall 與 `git diff --check` 均通過。三個 skip 維持既有 opt-in integrations。
- 本回合未讀三份私人 LIST、未啟動 Word、未執行 calibration，也未建立或改動
  master、manifest、config、QA 或 private review；因此 `5991` 的實機排除狀態仍為
  **未驗證**。
- 使用者另行核准一次新的 Gate C 真實校準；開工的 `git pull --ff-only` 回傳
  `Already up to date.`。執行前驗證三份來源 SHA-256 全部符合既定值，五份既有
  private reviews／diagnostics 的 SHA-256 全部符合既定值；既有 master／manifest
  數量為 0，真實 config 與全新目的目錄均不存在，WINWORD 為 0，`pdftoppm 25.07.0`
  可用。
- 兩次 sandbox 內的 probe 在寫入 job 前即被 temp ACL 拒絕，均未啟動 Word、未讀取
  LIST、未消耗 calibration；改在 sandbox 外執行 bounded hidden owned probe 後成功，
  原文為 `{"available": true, "word_version": "16.0"}`。
- 在全新 `list-calibration-v4-cell-format` 私人目錄執行且只執行一次
  `calibrate-list`，沒有 retry。命令明確回傳 `WORD_GENERATION_FAILED`、stage
  `run-action`、HRESULT `-2146233087`（`0x80131501`，low word `5377`）、adapter code
  `NONE`。此錯誤沒有安全 checkpoint，不能推定 row-access 修正是否已越過原 `5991`。
- 失敗後三份來源 SHA-256 全部不變，WINWORD 為 0；沒有 master、manifest、config、
  PDF、PNG 或新 calibration review。CLI 將空的全新 private 目錄自動移除；五份既有
  private reviews／diagnostics 未覆蓋或刪除。兩個失敗 probe 遺留的精確 temp 目錄已
  清除並回讀確認不存在。本回合沒有程式碼變更，因此未重跑測試，最近完整離線結果
  維持 `452 passed, 3 skipped in 7.28s`。
- 2026-08-13 依「進行下一步」授權完成 Gate C `0x80131501` 細粒度診斷的離線實作；
  開工的 `git pull --ff-only` 回傳 `Already up to date.`。保留既有
  `diagnose-5992-v2` 相容性，新增通用 `diagnose-gate-c-v3` action，兩者共用同一個
  bounded Word job、三份來源 hash 綁定、job-local working copies、來源前後 hash
  驗證、checkpoint allowlist 與 exclusive report boundary。
- v3 report 只允許 Word version、分類、完成 inspection 數、base sample ID、固定
  phase／operation／field ID、數字座標、HRESULT 與 adapter code；拒絕額外欄位，
  不保存來源路徑、檔名、文件文字或 master。回歸測試另固定 `0x80131501`／low word
  `5377` 的 round trip，並驗證輸出不含 `LIST-` 或 `source_path`。
- 針對性測試為 `44 passed`；完整離線回歸為 `455 passed, 3 skipped in 7.34s`，
  PowerShell parser、compileall 與 `git diff --check` 均通過。三個 skip 維持既有
  opt-in integrations。本回合未讀私人 LIST、未啟動 Word、未建立或改動任何 private
  artifact，因此 v3 診斷的實機結果仍為**未驗證**。
- 2026-08-14 使用者明確核准一次 `diagnose-gate-c-v3` 真實診斷，不包含 calibration
  retry；開工的 `git pull --ff-only` 回傳 `Already up to date.`。執行前再次驗證三份
  來源與五份既有 private reviews／diagnostics 的 SHA-256 全部符合既定值；全新診斷
  目錄不存在，既有 master／manifest 數量為 0，真實 config 不存在，WINWORD 為 0。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。唯一一次 v3 診斷隨後完成且沒有
  retry：classification `ERROR_OBSERVED`、完成 source inspections `0`、base sample
  `sample-000`；checkpoint 為 phase `inspect-source`、sample `sample-001`、operation
  `table-borders`、field path `samples[0].inspection.border_digest`、table `1`，HRESULT
  `-2146233087`（`0x80131501`，low word `5377`）、adapter code `NONE`。
- 此 checkpoint 證實 row-access 修正已越過先前候選路徑，新的阻塞點是 schema-2
  inspection 對 `$table.Borders` collection 的列舉；尚未核准或執行 border-access
  修正，也未校準。
- 診斷後三份來源與五份既有 private reviews／diagnostics 的 SHA-256 全部不變，
  WINWORD 為 0；沒有 master、manifest、config、PDF 或 PNG。全新 private 目錄只含
  `gate-c-v3-diagnostic.json`，共 745 bytes，SHA-256 為
  `60d5de09c7d995f53a268723625145b24ceff19dce17d538e743761d58eed22c`；內容僅含既定
  hashes、checkpoint 與錯誤欄位，不含來源路徑、檔名或文件文字。本回合沒有程式碼
  變更，因此未重跑測試，最近完整離線結果維持 `455 passed, 3 skipped in 7.34s`。
- 2026-08-14 依「好 下一步」授權完成 Gate C border-access 離線修正；開工的
  `git pull --ff-only` 回傳 `Already up to date.`。schema-2 inspection 已移除唯一的
  `$table.Borders` collection 列舉，改以四張表固定 prototype rows `2／2／2／1`、
  column counts `3／6／7／3` 的每個 cell 建立 border fingerprint。
- 每個 prototype cell 固定讀取 top／left／bottom／right／diagonal-down／diagonal-up
  六種 border types（Word constants `-1／-2／-3／-4／-7／-8`）；相鄰 cell 的外框涵蓋
  表格內部格線。六種 access 各有獨立 allowlisted checkpoint，保留 table／row／column，
  若實機仍失敗可定位到特定 cell 與 border side。
- 新增防回歸測試，固定上述 border types／operations，並禁止 schema-2 inspection
  再出現 `$table.Borders` 或 collection enumeration。針對性測試為 `45 passed`；完整
  離線回歸為 `456 passed, 3 skipped in 8.14s`，PowerShell parser、compileall 與
  `git diff --check` 均通過。三個 skip 維持既有 opt-in integrations。
- 本回合未讀私人 LIST、未啟動 Word、未執行診斷或校準，也未建立或改動任何 private
  artifact；既有 v3 diagnostic SHA-256 仍為
  `60d5de09c7d995f53a268723625145b24ceff19dce17d538e743761d58eed22c`，WINWORD 為 0。
- 2026-08-14 使用者明確核准一次新的 `diagnose-gate-c-v3` 真實診斷，不包含
  calibration retry；開工的 `git pull --ff-only` 回傳 `Already up to date.`。執行前
  再次驗證三份來源與六份既有 private reviews／diagnostics 的 SHA-256 全部符合既定
  值；全新診斷目錄不存在，master／manifest 數量為 0，真實 config 不存在，
  WINWORD 為 0。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。唯一一次 v3 診斷隨後完成且沒有
  retry：三份 source inspections 全部完成，選定 base 為 `sample-001`，證實固定 cell
  border fingerprint 已實機越過先前 `$table.Borders` 阻塞點。
- 診斷在 diagnostic-only working copy mutation 明確停止：classification
  `ERROR_OBSERVED`；checkpoint phase `calibrate-copy`、sample `sample-001`、operation
  `header-tail-normalize`、field path `master_working_copy.prototype_header`、table 1／
  row 1／column 1／paragraph 4；HRESULT `-2146233087`（`0x80131501`，low word `5377`），
  adapter code `LIST_HEADER_NORMALIZATION_FAILED`。
- 此 adapter code 來自 `Set-NormalizedHeaderDynamicTail` 寫入後的明確 postcondition：
  `$HeaderCell.Range.Paragraphs.Count -ne 4`。因此這不是未知 COM 寫入結果；目前程式以
  paragraph 4 start 到 cell end 前一字元的 range 寫入單一 CR，但 Word 完成後仍未得到
  exact-four 契約。尚未核准或執行 normalization 修正，也未校準。
- 診斷後三份來源與六份既有 private reviews／diagnostics 的 SHA-256 全部不變，
  WINWORD 為 0；沒有 master、manifest、config、PDF 或 PNG。全新 private 目錄只含
  `gate-c-v3-diagnostic.json`，共 782 bytes，SHA-256 為
  `e3c469bb5fb727efc36aeeffa1d7532c9d232d82d0321f45d961ed0ec156cec2`；內容僅含既定
  hashes、checkpoint 與錯誤欄位，不含來源路徑、檔名或文件文字。本回合沒有程式碼
  變更，因此未重跑測試，最近完整離線結果維持 `456 passed, 3 skipped in 8.14s`。
- 2026-08-14 依「好 下一步」授權完成 Gate C header-tail normalization 離線修正；
  開工的 `git pull --ff-only` 回傳 `Already up to date.`。既有實作把 paragraph 4 start
  到 cell marker 前的整段 tail range 替換為單一 CR，會在 Word 受保護的 cell 終止段落
  之外再形成一個段落；現在改為將該 range 內容清空，讓 Word 保留既有的終止段落作為
  唯一空白 paragraph 4。
- exact-four postcondition 現在先取得 `$observedParagraphCount`，並以新的 allowlisted
  `header-tail-postcondition` checkpoint 記錄 table 1／row 1／column 1 及實際段落數，
  再判斷是否為 4；若實機仍不符，安全 v3 report 可直接回報 observed count，不需猜測。
- 更新防回歸測試，禁止 normalization 再寫入額外 CR，並固定清空 tail、observed-count
  checkpoint 與既有 fail-closed postcondition。針對性測試為 `45 passed`；完整離線
  回歸為 `456 passed, 3 skipped in 7.61s`，PowerShell parser、compileall 與
  `git diff --check` 均通過。三個 skip 維持既有 opt-in integrations。
- 本回合未讀私人 LIST、未啟動 Word、未執行診斷或校準，也未建立或改動任何 private
  artifact；最近 v3 diagnostic SHA-256 仍為
  `e3c469bb5fb727efc36aeeffa1d7532c9d232d82d0321f45d961ed0ec156cec2`，WINWORD 為 0。
- 2026-08-14 使用者以「好 下一步」核准一次新的 `diagnose-gate-c-v3` 真實診斷，
  不包含 calibration retry；開工的 `git pull --ff-only` 回傳 `Already up to date.`。
  執行前再次驗證三份來源與七份既有 private artifacts 的 SHA-256 全部符合既定值；
  全新診斷目錄不存在，master／manifest 數量為 0，真實 config 不存在，WINWORD 為 0。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。唯一一次 v3 診斷隨後完整通過且
  沒有 retry：classification `NOT_REPRODUCED`、三份 source inspections 全部完成、
  base `sample-001`、checkpoint phase／operation 均為 `complete`；HRESULT `0`／
  `0x00000000`、low word `0`、adapter code `NONE`。
- 此結果證實 schema-2 source inspection、header-tail normalization、其餘
  diagnostic-only working-copy mutations 與 `SaveAs2` 路徑均已在 Word `16.0` 實跑
  完成；diagnostic master 依設計在 temporary boundary 內清除，沒有正式 master 或
  manifest。這不等於 Gate C 正式 calibration 已執行或成功。
- 診斷後三份來源與七份既有 private artifacts 的 SHA-256 全部不變，WINWORD 為 0；
  沒有 master、manifest、config、PDF、PNG 或 diagnostic master。全新 private 目錄
  只含 `gate-c-v3-diagnostic.json`，共 696 bytes，SHA-256 為
  `c7db1141eb42240069dae1faa060917d2783ff25367b9a731d425534b4117d25`；內容僅含既定
  hashes、complete checkpoint 與零錯誤欄位，不含來源路徑、檔名或文件文字。本回合
  沒有程式碼變更，因此未重跑測試，最近完整離線結果維持
  `456 passed, 3 skipped in 7.61s`。
- 2026-08-14 使用者以「好 下一步」明確核准一次正式 Gate C `calibrate-list`；範圍
  只允許全新 exclusive private 目錄執行一次，沒有 retry，不包含 Gate V、config
  寫入、Gate E 或 push。開工的 `git pull --ff-only` 回傳 `Already up to date.`；
  執行前再次驗證三份來源與八份既有 private artifacts 的 SHA-256 全部符合既定值，
  全新校準目錄不存在，既有 master／manifest 數量為 0，真實 config 不存在，
  WINWORD 為 0，`pdftoppm 25.07.0` 可用。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。唯一一次正式 `calibrate-list` 隨後
  執行完成且沒有 retry，但 CLI 只回傳 `INTERNAL_ERROR`／`Unexpected internal error`，
  `details` 為空；沒有 Word adapter stage、HRESULT、field paths 或受控 review。
- 事後唯讀程式路徑確認：正式 calibration 先執行 `inspect-v2`，再由
  `compare_calibration_samples()` 比較三份 normalized layouts；若拋出
  `CalibrationContractError`，目前 `main()` 的 generic `except Exception` 會把它抹成
  本次看到的 `INTERNAL_ERROR`。由於前一回 v3 已證實相同 source inspection、mutation
  與 SaveAs2 路徑可通過，sample contract comparison conflict 是目前最可能原因；但
  本次沒有安全 stage/report，因此只記為**未驗證推論**，不據此修改契約。
- 校準後三份來源與八份既有 private artifacts 的 SHA-256 全部不變，WINWORD 為 0；
  全新 private 目錄因空白由 CLI 自動移除，沒有 master、manifest、config、review、
  PDF 或 PNG。本回合沒有程式碼變更，因此未重跑測試，最近完整離線結果維持
  `456 passed, 3 skipped in 7.61s`。
- 2026-08-14 完成可逆的 Gate C 離線安全修正，沒有讀取真實 LIST、啟動 Word 或重跑
  calibration。`calibrate_list_templates()` 現在依序回報固定 allowlist stage：
  `inspect-samples`、`compare-samples`、`calibrate-master`、`validate-master`、`publish`。
  CLI 捕捉 `CalibrationContractError` 後會以 exclusive create 寫入
  `calibration-review.json`；內容只含 schema/status、受控 error code、stage、三個來源
  SHA-256 與排序後 field paths，不含來源路徑、檔名或內容，並以 exit code 20 回傳
  `CALIBRATION_CONTRACT_CONFLICT`，不再落入泛化 `INTERNAL_ERROR`。
- TDD 紅測先確認缺少 `on_stage` 與 review；實作後目標測試為 34 passed。完整離線回歸
  原文為 `457 passed, 3 skipped in 7.36s`；`compileall -q src tests` 與
  `git diff --check` 均通過。此 venv 沒有 `ruff.exe`，因此 Ruff 明確標記為未驗證，
  沒有為此安裝新依賴。
- 2026-08-14 使用者明確重新核准一次新的正式 Gate C calibration；範圍只含 20 秒
  hidden owned probe、全新 exclusive private 目錄的一次 `calibrate-list` 與唯讀後驗，
  不含 retry、Gate V、config 寫入、Gate E 或 push。開工 `git pull --ff-only` 回傳
  `Already up to date.`。第一次 preflight 腳本因 PowerShell 單一字串索引錯誤而無法
  取得來源 hash/size，且三個縮略的 artifact 預期 hash 不足以驗證；該次沒有啟動 Word、
  沒有讀取文件內容，也沒有執行 calibration。改從既有 STATUS 取回完整 hash 並修正
  唯讀腳本後，三份來源 hash/size、八份既有 private artifacts 全部符合既定值；新目標、
  config 不存在，master／manifest 各 0，WINWORD 0，pdftoppm 可用。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。隨後在全新
  `list-calibration-v7-safe-review` 執行且只執行一次正式 `calibrate-list`，沒有 retry；
  命令受控回傳 `CALIBRATION_CONTRACT_CONFLICT`、stage `compare-samples`，field paths
  為 `border_digest`、`daily_body_prototype_digest`、`daily_header_digest`、`font_digest`、
  `paragraph_digest`、`shape_geometry_points`、`style_digest`、
  `table_column_widths_points`。因此未進入 `calibrate-master`，不得自行放寬契約。
- 後驗三份來源 hash/size 與八份舊 artifacts 全部不變，WINWORD 0，仍無 master、
  manifest 或 config。全新目錄只含 606-byte `calibration-review.json`，SHA-256 為
  `3b60876667ce6f093f1299371c57956a74209a0e85c34bc7b010d9bd8ef69dc7`；keys 僅為
  schema/status、error code、stage、source SHA-256、field paths，且不含 LIST 名稱、
  Downloads 路徑、`source_path` 或文件內容。本回合沒有程式碼變更，因此未重跑測試，
  最近完整離線結果維持 `457 passed, 3 skipped in 7.36s`。
- 2026-08-14 依使用者「好 下一步」完成 Gate C conflict matrix 離線核心，沒有讀取
  真實 LIST、啟動 Word、執行 diagnosis/calibration，亦未建立或修改 private artifact。
  `build_calibration_conflict_matrix()` 只接受三個唯一 sample 與 normalized layout 既有
  欄位；欄位必須確實存在至少兩種 canonical values，否則 fail closed。field 與 sample
  均固定排序，classification 為 `TEMPLATE_CONTRACT_CONFLICT`，每個差異固定標示
  `REQUIRES_OP_DECISION`，不會自行宣稱可正規化。
- Matrix 明確排除 day count、dynamic content 與 adaptive profiles。既有 `*_digest`
  只輸出 normalized digest，純數值樹才輸出 normalized value；任何其他含字串結構
  （包括可能帶 Word shape 名稱的 `shape_geometry_points`）只輸出 canonical SHA-256，
  避免 private 名稱進入 review。`compare_calibration_samples()` 發現衝突時會附上此
  matrix，CLI 只將它 exclusive-create 到 private `calibration-review.json`，一般錯誤
  details 仍只含 stage、field paths 與 review path。
- TDD 紅測先確認 matrix builder 不存在；收緊 shape 名稱輸出後，針對性回歸為
  `36 passed in 1.23s`，完整離線回歸原文為 `459 passed, 3 skipped in 7.24s`；
  `compileall -q src tests`、production Python 100 字元行寬與 `git diff --check` 均通過。
  此 venv 仍沒有 Ruff，因此 Ruff 未驗證且沒有安裝新依賴。
- 2026-08-14 依使用者「好 下一步」完成專用 read-only conflict diagnosis CLI 的離線
  實作；沒有讀取真實 LIST、啟動 Word、執行 diagnosis/calibration，亦未建立或修改
  private artifact。新命令 `diagnose-list-conflicts` 只接受三個唯一 DOC／DOCX 與全新
  `--private-dir`，刻意沒有 `pdftoppm`、master、manifest 或 config 參數；既有 private
  目錄會在 Word inspection 前 fail closed。
- `diagnose_calibration_conflicts()` 只呼叫一次 `inspect_list_templates_v2()`，接著以共用
  純 comparison helper 產生 field paths／matrix；不呼叫 `calibrate_list_templates()`。
  有衝突時 private `conflict-diagnosis.json` 回報 `TEMPLATE_CONTRACT_CONFLICT` 並以
  exit code 20 停止；沒有 normalized layout 衝突時回報
  `NORMALIZED_LAYOUT_COMPATIBLE` 並立即結束，這不宣稱 adaptive profiles 或完整
  calibration 已通過。兩條路徑都不可能進入 `calibrate-master`。
- CLI report 以 exclusive create 寫入，只含 schema/status、command、固定 stage、
  classification、Word version、source SHA-256、field paths 與 private-safe matrix；一般
  CLI output 不展開 matrix。測試明確把 calibration function 替換成 fail sentinel，證實
  diagnosis CLI 不會呼叫它。TDD 紅測先確認 diagnosis API 不存在；針對性回歸為
  `40 passed in 1.16s`，完整離線回歸原文為 `463 passed, 3 skipped in 7.32s`。
- 2026-08-14 使用者以「好 下一步」明確核准一次真實 `diagnose-list-conflicts`；範圍
  只含 preflight、20 秒 hidden owned probe、全新 private 目錄的一次 `inspect-v2`／
  comparison 與唯讀後驗，沒有 retry，不含 calibration、Gate V、config、Gate E 或
  push。開工 `git pull --ff-only` 回傳 `Already up to date.`；三份來源 hash/size、九份
  既有 private artifacts 全部符合既定值，新目標與 config 不存在，master／manifest
  各 0，WINWORD 0。
- 20 秒 hidden owned probe 成功，原文為
  `{"available": true, "word_version": "16.0"}`。隨後在全新
  `list-diagnosis-v8-conflict-matrix` 執行且只執行一次 `diagnose-list-conflicts`，沒有
  retry；結果為 `TEMPLATE_CONTRACT_CONFLICT`、stage `compare-samples`，重現相同八個
  field paths：`border_digest`、`daily_body_prototype_digest`、`daily_header_digest`、
  `font_digest`、`paragraph_digest`、`shape_geometry_points`、`style_digest`、
  `table_column_widths_points`。命令只完成 inspection/comparison，沒有 calibration 路徑。
- Matrix 顯示 `border_digest` 與 `daily_header_digest` 各有兩種值：sample-001／002 相同，
  sample-003 不同。其餘六欄各有三種值。欄寬的四表總寬以程式計算：sample-001 為
  `563.6／556.7／556.35／556.7 pt`，sample-002 與 sample-003 均為
  `558.25／556.7／556.35／556.7 pt`；第 2–4 表總寬相同但部分欄位重新分配，第 1 表
  sample-001 總寬另多 5.35 pt。這些只是不透明差異與數值證據，未據此選 base、平均或
  放寬契約。
- 第一次唯讀群組摘要腳本使用此 PowerShell/.NET 不支援的 `SHA256.HashData()`，導致
  群組數無效，且 case-insensitive `-match 'LIST-'` 誤中 CLI command 的小寫 `list-`；
  diagnosis 沒有重跑。改用 report 已有的 safe digest/value 分組並改成 case-sensitive
  檢查後，上述矩陣結果成立，report 不含大寫 LIST 檔名、Downloads 或 `source_path`。
- 後驗三份來源 hash/size 與九份舊 artifacts 全部不變，WINWORD 0，仍無 master、
  manifest 或 config。新目標只含 8,888-byte `conflict-diagnosis.json`，SHA-256 為
  `24a5fb1ab2b71773096cf8cc893acc7001dc018afbefb27a3d4fbf9283fec53d`。本回合沒有
  程式碼變更，因此未重跑測試，最近完整離線結果維持
  `463 passed, 3 skipped in 7.32s`。
- 2026-08-14 使用者以「好 下一步」核准離線建立 component diagnosis。新增
  `diagnose-list-components` 與 Word action `diagnose-components-v2`，只以 read-only
  開啟三份來源，輸出固定 cell／border／shape IDs、數值／enum，以及立即 SHA-256 後的
  style／font 名稱與 daily header/body 子元件；不讀取或輸出 Word text、不建立 working
  copy／master／manifest，也不呼叫 calibration。Python 對 report 採 exact-schema
  allowlist，拒絕額外欄位，並以執行前後 SHA-256 偵測來源變更。舊 schema-2 inspection
  digests、`_normalized_layout_dict()` 與正式 comparison contract 均未修改。
- 本次只用 synthetic adapter 驗證，沒有啟動 Word、沒有讀取真實 LIST，也沒有建立新的
  private artifact。針對性測試原文為 `70 passed`；PowerShell parser 原文為
  `PowerShell parse OK`，`compileall OK`，`git diff --check` 通過；完整離線回歸原文為
  `469 passed, 3 skipped in 7.34s`。
- 2026-08-14 使用者明確核准「一次新的真實 read-only component diagnosis」。開工
  `git pull --ff-only` 回傳 `Already up to date.`；三份來源依序精確匹配既定 SHA-256
  與 `77,824／81,408／86,016` bytes，新 private 目標不存在，WINWORD 0。只執行一次
  `diagnose-list-components`，沒有 probe、retry 或 calibration；命令回傳 `status: ok`。
- 三份 component 數量完全相同且沒有 presence 差異：styles／fonts／paragraphs 各 19、
  borders 114、daily header/body 各 7、shapes 1。styles 19 格全部一致，證實舊
  `style_digest` 衝突是因舊 digest 同時混入 font／paragraph，而非 style 本身不同。
  Fonts 有 13 格不同且全為 sample-001／002 相同、sample-003 不同：12 格字級、3 格
  bold、4 格 color。Paragraphs 有 11 格不同，均涉及 line spacing，其中 1 格另有
  line-spacing rule 差異，且該格 sample-002 回傳 Word mixed/undefined sentinel
  `9999999`，不得當成可直接套用的標準值。
- Borders 只有 4 個 prototype side 不同，全部為 sample-001／002 相同、sample-003
  不同，差異僅 line width `12／12／4`。Daily header 7 格全為 sample-001／002 相同、
  sample-003 不同，差異來自 font 與 paragraph 子元件，style 相同；daily body 7 格的
  font 與 paragraph 都不同，其中 1 格 sample-001／002 相同、其餘 6 格三份皆不同。
  唯一 `floating-001` 三份皆存在，但 left/top/width/height 皆不同，尺寸依序為
  `95.4／83.95／103.4 pt` 正方形。
- 第一版唯讀差異彙總腳本因 `ConvertTo-Json -Depth` 陣列語法錯誤而產生無效零差異；
  沒有重新執行 Word action。修正後只重讀既有安全 JSON 並得到上述結果。後驗三份來源
  hash／size 均不變，WINWORD 0。全新 private 目錄只含 134,596-byte
  `component-diagnosis.json`，SHA-256 為
  `86a9cecab6d1b544ee62ebe336ad7368bb591fc072deeeecd1c66ffb5ba5f12a`；report 不含
  大寫 LIST 檔名、Downloads、`source_path` 或 Windows 路徑。本回合沒有程式碼變更，
  最近完整離線回歸維持 `469 passed, 3 skipped in 7.34s`。
- 2026-08-14 使用者以「好 下一步」核准純離線 normalization decision table 開發；
  開工 `git pull --ff-only` 回傳 `Already up to date.`。新增
  `build_component_normalization_decision_table()`：固定 19 個 prototype style/font/
  paragraph IDs、114 個 border IDs、daily header/body 各 7 個 IDs，以及非空且跨樣本一致的
  synthetic shape ID/kind；缺漏、多出、重複或 shape kind 不合法均 fail closed，不得由
  base 選擇修補。
- 完整一致的 bundle 標為 `PRESERVE_UNANIMOUS`；任何差異標為 `REQUIRES_OP_BASE`，OP
  日後必須以 exact source SHA-256 與 component-value SHA-256 綁定選擇。兩份相同不會
  觸發多數決。`9999999` 會把該來源列為不合格 base 並將整表分類為
  `BLOCKED_MIXED_VALUE`；floating shape 的 left/top/width/height 固定作為一個
  `geometry_bundle`，不得拼裝。Daily body 是 style/font/paragraph 決策後的 derived audit，
  不建立第二套可能互相矛盾的決策。
- 新政策文件為
  `docs/specs/2026-08-14-list-normalization-decision-table.md`。本回合沒有讀取真實 LIST、
  既有 private report、啟動 Word、執行 diagnosis/calibration 或修改正式 comparison；
  `_normalized_layout_dict()` 與 `compare_calibration_samples()` 未變。針對性測試原文為
  `35 passed`，`compileall OK`，`git diff --check` 通過；完整離線回歸原文為
  `476 passed, 3 skipped in 7.69s`。
- 2026-08-14 使用者以「好 下一步」核准純離線 normalization planner 開發；開工
  `git pull --ff-only` 回傳 `Already up to date.`。新增 strict
  `load_component_diagnosis_artifact()`，只接受 `diagnose-list-components` 產出的 exact
  schema-1／status／command／stage、三個唯一且非零 source SHA-256、Word version 與三份
  allowlisted component evidence；額外欄位、缺欄、錯誤 hash 或不合法 component 立即拒絕。
- 新增 `plan-list-normalization --component-report ... --private-dir ...`。Parser 不接受
  `--sample`，命令不建立 Word adapter、不呼叫 diagnosis/calibration，只在不存在的 private
  目錄 exclusive-create `normalization-decision-table.json`；非 ready classification 回傳
  `needs_review`／exit 20，完全一致才回傳 `ok`。輸入不合法時只移除空目錄，不覆蓋或刪除
  任何已有 artifact。
- Decision table 以 canonical JSON 計算 semantic SHA-256。OP-choice artifact exact schema
  只允許 table hash、原三個 source hashes 與 choices；每個 choice 必須完整且唯一對應一個
  decision ID，同時匹配 eligible source SHA-256 與該來源的 component-value SHA-256。
  缺漏、多餘、重複、額外欄位、table/source/component hash 不符、選到 mixed sentinel
  來源，或試圖用 choice 解決 component-contract conflict 都會拒絕。政策文件已補上 schema。
- 本回合僅建立 synthetic component report 驗證 planner，沒有讀取既有 private report、
  真實 LIST、啟動 Word 或執行 calibration；正式 comparison/calibration 接線未修改。
  針對性測試原文為 `62 passed`，`compileall OK`，`git diff --check` 通過；完整離線回歸
  原文為 `487 passed, 3 skipped in 7.55s`。
- 2026-08-14 使用者明確核准「讀取一次既有 private-safe component report，離線產生
  真實 normalization decision table」。開工 `git pull --ff-only` 回傳
  `Already up to date.`；前驗既有 report 為 134,596 bytes，SHA-256 精確匹配
  `86a9cecab6d1b544ee62ebe336ad7368bb591fc072deeeecd1c66ffb5ba5f12a`，新 private 目標
  不存在且 WINWORD 0。只執行一次 `plan-list-normalization`，沒有 retry、Word、
  diagnosis 或 calibration；受控回傳 `needs_review`／`BLOCKED_MIXED_VALUE`。
- 真實表共有 36 個 decisions：fonts 13、paragraphs 11、borders 4、daily header 7、
  shapes 1。35 個為 `REQUIRES_OP_BASE`；唯一 `BLOCKED_MIXED_VALUE` 是
  `paragraphs:table-001-row-002-column-003`，changed properties 為 line spacing points／
  rule，三份中有 2 個 eligible、1 個 ineligible source。另有 daily body 7 個
  `VERIFY_AFTER_COMPONENT_NORMALIZATION` derived audits，component-contract blocker 為 0。
  Unanimous preserved counts 為 styles 19、fonts 6、paragraphs 8、borders 110，其餘 0。
- 全新 private 目錄只含 53,469-byte `normalization-decision-table.json`；file SHA-256
  為 `995130a3b8e5a27c0a52b629ef53e3c1d79761bbd58ff43ee415eca7cccdfb27`，canonical
  decision-table SHA-256 為
  `a41ce44d79852c1e7407f0f8f03f30e8bfce13603ad68853966c6d4aaf0b50fe`。後驗來源 report
  hash 不變、WINWORD 0，目標沒有 master／manifest／config。本回合沒有程式碼變更，
  最近完整離線回歸維持 `487 passed, 3 skipped in 7.55s`。

## 下一步

真實 worksheet、OP-selected artifact、sample-001 欄寬決策與 fail-closed Gate C 整合均已
完成並通過離線回歸。read-only comparison 與 diagnostic-only working-copy normalization
也已各執行一次並通過；manifest evidence 修正後的新正式 Gate C 已成功建立並驗證
master／manifest。Gate V 亦已用 4／5／6／7／8／12 天 synthetic fixtures 完成真實
Word 視覺 QA。首次 Gate E 已獲核准，source-to-narration mapping 與新主機 config／Yating
diagnosis 已完成。下一步由 OP 提供同產品行程 PDF 或其他已核准來源以補「不可脫隊規範」
與「保險內容」，並提供 10 個當次 OP 欄位值；天氣與 14 個發音項目仍須 review。資料齊備
後才能建立新的 manifest、check-script 與本機 DRAFT render。
GitHub visibility 依使用者指示不變；`e0d1b60` public push 是收到風險警告後的單次
明確例外，不構成 Gate I 紀錄 commit 或後續 public push 授權。Cowell 部分維持到
立益公司電腦 clone、
先跑完整離線測試，再由 OP 登入受控 Chrome，依序驗證 auth status 與 rooms preview。

## 阻塞點

本機無科威登入，因此真實頁面結構與正式 rooms apply 尚未驗證。正式
apply 必須在公司環境針對最終 preview 另行取得當次明確核准。

GitHub 遠端於 2026-08-13 即時驗證仍為 public。依私有產品與「不可把內容複製到
公開處」規則，正常情況在 repo 重新驗證為 private 前不得 push；使用者本次在明知
衝突後明確要求直接 push，因此僅本次依反迎合條款記錄為違規例外。

Gate I 已完成，沒有剩餘安裝阻塞。OP 已用 hash-bound choices 解決既有八個 schema-2
field conflicts；manifest evidence 修正已經新正式 Gate C 實證通過，master／manifest
均已建立並完成 hash／fingerprint 後驗，Gate C 不再阻塞。Gate V 多天數 Word 視覺 QA
亦已正式通過。首次 Gate E 已執行但在 render 前 fail closed：修正後仍有 2 個來源必要
事實缺漏、10 個 OP 欄位、1 個不可用天氣與 14 個發音 review。Yating 在 sandbox 外可用，
不再是主機阻塞。

說明會產生器 0.2.0 的 calibration、Word plan、workflow 與 packaging 沒有已知技術阻塞；
首次真實 Gate E 揭露的 compound notice 與標準 headings mapping 已修正；
URL-only 正式頁已
驗證可建立 `DRAFT_READY` 草稿，但該產品仍須 OP 從大阪／東北／北海道明確確認
`product_region`，不能跳過此人工欄位。完整
6–8 分鐘正式版本尚未產生；Task 6 JMA parser、離線選擇與 Task 9 orchestration 已
完成；LIST Word COM／私有範本／多天數視覺驗證已實跑通過，正式資料取得亦已成功，
但 Gate E 端對端 render 尚未越過 narration readiness gate。
第一批 alias 只有 synthetic 大阪
案例；仙台、札幌等城市必須取得 JMA 預報區證據與測試後才能加入。掃描型無文字
PDF 會明確
阻塞並要求另行 OCR review。Azure 已移出第一階段自動流程；任何未來雲端 TTS 與
自動 LINE 傳送仍是獨立核准關卡。

本次 Gate E capability diagnosis 證實 Microsoft Yating 只在 sandbox 內偽陰性；sandbox 外
正式 probe 為 `ok`，不需恢復／安裝且不得 fallback 到 Hanhan。`pdftoppm` 可用、Word COM
已註冊且 Gate C hidden owned probe 已以 Word `16.0` 實跑，私人 master、PDF render 與逐頁
視覺 QA 均已在 Gate V 驗證；`ffmpeg` 仍未設定。
Task 11 隔離安裝已證明新 `briefing.exe` 可啟動，且顯式 config 可載入外部
`pdftoppm`；私有範本契約及 Word 實機 render 仍未驗證。
0.2.0 的任意天數與安全續頁邏輯已在 synthetic／mock 離線測試完成，但尚未代表
私人 LIST master 已建立或 Word 視覺驗收已通過；三份樣本的實際校準另屬 Gate C。
若樣本除日數、內容及可證明的自適應排版外仍有無法歸一的結構差異，校準必須
fail closed 並請使用者決定，不能自行挑一份或平均差異。
安裝 ffmpeg、再次 live 官網 request、首次實際 JMA 預報 request、任何雲端 TTS、LINE、
影片與部署都不包含在本次剩餘授權內，必須各自另行確認。
