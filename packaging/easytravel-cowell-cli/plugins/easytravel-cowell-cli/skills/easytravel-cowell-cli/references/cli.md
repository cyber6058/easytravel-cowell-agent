# CLI workflow

Use the packaged runtime:

```powershell
$py = "$env:LOCALAPPDATA\EasyTravelCowellCLI\app\.venv\Scripts\python.exe"
```

All files below are local PII. Quote every Windows path and keep generated
images, JSON, and workbooks outside repositories.

## Browser and readiness

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\EasyTravelCowellCLI\Start-CowellBrowser.ps1"
& $py -m cowell_cli.cli doctor --format json
& $py -m cowell_cli.cli auth status --format json
```

If authentication is invalid, let the operator type credentials in the
controlled Chrome window. Never request, store, or type the password.

## Passport PDF or photos

The output directory must be new or empty:

```powershell
& $py -m cowell_cli.cli passports prepare "<PDF_OR_IMAGE>" --output-dir "<NEW_PRIVATE_DIR>" --format json
```

Inspect every artifact path from the JSON result. If automatic segmentation is
wrong, rerun into another new directory with an explicit
`--layout single|2x2|2x1|1x2` and/or `--rotate 0|90|180|270`.

After creating `travelers.json` according to
[passport data](passport-data.md), validate it:

```powershell
& $py -m cowell_cli.cli passports validate "<PRIVATE_DIR>\travelers.json" --format json
```

Require `ready_for_export=true` and every record to have
`mrz_check_digits_valid=true`. Download a fresh official template when one is
not already available:

```powershell
& $py -m cowell_cli.cli passports template --output "<PRIVATE_DIR>\cowell-template.xlsx" --format json
```

The template command is one registered read-only Cowell GET and refuses to
overwrite an existing file. Export to another new path:

```powershell
& $py -m cowell_cli.cli passports export "<PRIVATE_DIR>\travelers.json" --template "<PRIVATE_DIR>\cowell-template.xlsx" --output "<PRIVATE_DIR>\cowell-roster.xlsx" --format json
```

Do not use `--allow-unverified` automatically. It is an exceptional override
that needs the operator to review the exact blocked record IDs and explicitly
accept an unverified output.

## Existing-order rooming

The required inputs are `<GROUP>`, `<ORDER>`, and a local DOCX/XLSX file.
Start offline:

```powershell
& $py -m cowell_cli.cli rooms parse "<FILE>" --format json
& $py -m cowell_cli.cli rooms plan "<FILE>" --group-code <GROUP> --order-id <ORDER> --format json
```

Then perform a read-only live preview:

```powershell
& $py -m cowell_cli.cli rooms preview "<FILE>" --group-code <GROUP> --order-id <ORDER> --format json
```

Cabin handling:

- If all source names already match, no cabin argument is needed.
- If one placeholder cabin is reported, rerun automatically with that exact
  value, for example `--cabin Y`.
- If several cabins are reported, ask which source passengers belong in each
  cabin. Create a private JSON object keyed by source passenger sequence, for
  example `{"1":"Y","2":"C"}`, then pass
  `--cabin-map "<PRIVATE_MAP.json>"`.
- A source child/adult label that differs from Cowell is a warning only. Keep
  Cowell's existing category and continue.

If room collisions are reported, rerun with the exact
`--room-offset <suggested_room_offset>`. Every changed argument produces a
new confirmation.

Apply only after showing the final target, counts, cabin selection, target room
numbers, warnings, and exact confirmation, and receiving current explicit
approval:

```powershell
& $py -m cowell_cli.cli rooms apply "<FILE>" --group-code <GROUP> --order-id <ORDER> --cabin <CABIN> --room-offset <OFFSET> --confirm "<CONFIRMATION>" --format json
```

Use either `--cabin` or `--cabin-map`, matching the final preview. Success
requires passenger, room-assignment, and room-note verified counts to equal the
source passenger count. Never retry after an unknown write result; read Cowell
first.

## Fail closed

- `SOURCE_UNAVAILABLE`: start controlled Chrome or wait for another CLI run.
- `SESSION_EXPIRED`: let the operator log in and rerun.
- `PARSE_CONTRACT_CHANGED` / `WRITE_POLICY_BLOCKED`: stop; do not bypass.
- `VALIDATION_FAILED`: correct the reported source, placeholder, cabin, or
  room collision issue and rebuild the preview.
