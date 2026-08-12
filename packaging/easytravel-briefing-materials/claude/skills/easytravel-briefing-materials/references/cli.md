# CLI workflow

The installed runtime is isolated from other EasyTravel tools:

```powershell
$briefingPython = "$env:LOCALAPPDATA\EasyTravelBriefing\app\.venv\Scripts\python.exe"
$configPath = "$env:LOCALAPPDATA\EasyTravelBriefing\config.toml"
```

Use `& $briefingPython -m travel_briefing.cli` for every command. Prefer
`--format json` so the conversation can read paths and states without scraping
free text. Do not echo source contents or OP values.

## Local capability check

```powershell
& $briefingPython -m travel_briefing.cli doctor --format json
```

`doctor` enumerates Yating, Word registration, pdftoppm, and configured ffmpeg.
It does not start Word, synthesize speech, install anything, or make a network
request. A warning is an unavailable capability, not permission to add a fallback.

## Prepare a new run

Use at least one of `--url` and `--pdf`:

```powershell
& $briefingPython -m travel_briefing.cli prepare `
  --url $productUrl `
  --pdf $pdfPath `
  --output-dir $outputRoot `
  --format json
```

Supplying `--url` performs a live allowlisted GET and therefore requires its own
current approval. PDF-only preparation is local. Every call creates a new
`<product-code>/<timestamp>` directory; never choose an existing run directory.

## Apply reviewed OP decisions

Create local UTF-8 JSON files under the ignored output root, then revise without
refetching:

```powershell
& $briefingPython -m travel_briefing.cli prepare `
  --previous-manifest $previousManifest `
  --op-values $opValuesJson `
  --conflict-decisions $conflictDecisionsJson `
  --output-dir $outputRoot `
  --format json
```

Either decision file may be omitted. At least one is required, and every supplied
file must name the same currently reviewed draft ID. Revision creates a new run
and a new draft ID.

## Check the narration

Write the script inside the ignored run area, then validate it:

```powershell
& $briefingPython -m travel_briefing.cli check-script `
  --manifest $manifest `
  --script $scriptPath `
  --output-dir $outputRoot `
  --format json
```

The content-addressed report contains issue codes and hashes, not the full script.
Do not render audio until `ready` is true.

## Render a DRAFT

After approval to use the private template, Word COM, and local Yating:

```powershell
& $briefingPython -m travel_briefing.cli render `
  --manifest $manifest `
  --script $scriptPath `
  --config $configPath `
  --tts yating `
  --format json
```

The command creates a new version. Review its new manifest; do not reuse the
source manifest ID. A DRAFT result still requires visual and listening review.

## Confirm the exact DRAFT locally

After the OP explicitly names the reviewed draft ID:

```powershell
& $briefingPython -m travel_briefing.cli render `
  --manifest $draftManifest `
  --script $sameScriptPath `
  --output-dir $outputRoot `
  --confirm-draft-id $exactDraftId `
  --format json
```

Confirmation does not rerun Word or Yating and does not send or upload anything.

## Exit codes

| Code | Meaning | Action |
| --- | --- | --- |
| `0` | Command completed | Still inspect the returned status and artifacts |
| `20` | Review required | Preserve partial safe output and resolve review items |
| `30` | Source or adapter failure | Do not invent a substitute source or retry an unknown write |
| `40` | Invalid or stale input | Correct the path, schema, or draft binding |
| `50` | Unexpected internal error | Preserve state and diagnose without exposing private content |
