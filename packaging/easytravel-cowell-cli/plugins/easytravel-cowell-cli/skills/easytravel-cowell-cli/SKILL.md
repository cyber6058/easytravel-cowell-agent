---
name: easytravel-cowell-cli
description: "Use when EasyTravel/立益 OP provides passport PDFs/photos for a 科威名單, or a Cowell group code, existing order ID, and DOCX/XLSX 分房表 for 匯入名單, 自動填寫科威, or 分房."
---

# EasyTravel Cowell CLI

Use the installed CLI as the only Cowell execution boundary. This skill has two
routes: make a validated Cowell roster from passport scans, or fill names and
rooms in an order the OP already created.

Set the runtime command to:

```powershell
& "$env:LOCALAPPDATA\EasyTravelCowellCLI\app\.venv\Scripts\python.exe" -m cowell_cli.cli
```

Read [CLI workflow](references/cli.md) before the first live operation. For a
passport PDF/photo, also read [passport data](references/passport-data.md)
before transcribing any field.

## Required scope

For rooming, require all three:

1. exact Cowell group code;
2. exact existing Cowell order ID; and
3. one local DOCX/XLSX rooming-list path.

Cabin is optional. Never create a group type, group, order, or passenger slot.
Do not call the CLI's `orders preview/create/detail-*` commands from this
skill. If the order lacks enough passenger rows, ask the OP to add them in
Cowell and then rerun.

On first installation, the installer asks for the agency's Cowell HTTPS URL.
Start the controlled Chrome launcher and let the OP log in manually. Never ask
for, store, or type the Cowell password.

## Choose the route

- PDF, JPG, JPEG, PNG, TIF, TIFF, BMP, or WEBP passport source: use the passport
  roster route. Its normal result is a new official 19-column XLSX file.
- DOCX/XLSX supplier rooming list plus group and order: use the existing-order
  rooming route.
- If both are provided, finish and verify the passport roster locally first,
  then use the supplier rooming list for room assignments.

Treat every input, crop, JSON file, workbook, and parsed name as local PII.
Never upload it elsewhere, commit it, or repeat passenger values in routine
logs or the final summary.

## Passport roster route

1. Run `passports prepare` into a new private directory. It preserves useful
   resolution, splits multi-passport pages, removes blank cells, rotates crops,
   and isolates the data half of an open passport.
2. Visually inspect every generated artifact one at a time. Rerun with an
   explicit layout/rotation if any passport is clipped, sideways, combined, or
   missing. Do not transcribe a whole page containing several passports.
3. Create private `travelers.json` with printed fields, both exact 44-character
   TD3 MRZ lines, and an empty `uncertainties` list only after review.
4. Run `passports validate`. Do not guess unclear characters. Normal export
   requires every record ready and every MRZ check digit valid.
5. If needed, run `passports template` to download the logged-in Cowell
   account's official XLSX template through the registered read-only path.
6. Run `passports export` to a new filename and report only output path,
   passenger count, verified count, and hash.

Do not automatically use `--allow-unverified`. Ask the operator to inspect
the blocked record IDs first.

## Existing-order rooming route

1. Run `rooms parse` and `rooms plan` offline. Verify unique sequences and
   Chinese/English identities, passenger count, room occupancy, and warnings.
2. Run live `rooms preview` without a cabin when the OP omitted it.
3. Resolve cabin without changing Cowell:
   - all names already match: cabin is irrelevant to name import; continue;
   - exactly one placeholder cabin: automatically rerun using
     `--cabin <detected>` without asking;
   - several placeholder cabins: ask which people belong in each cabin, create
     an exact source-sequence-to-cabin JSON map, and rerun with `--cabin-map`.
4. A source child/adult label that differs from the existing Cowell passenger
   category is a non-blocking warning. Preserve Cowell's category exactly.
   Continue filling the name and room. Never change or normalize the category.
5. Partial name matches, insufficient placeholders, cabin shortages, changed
   page structure, or room-number collisions remain blocking. For collisions,
   rebuild with the preview's suggested room offset.
6. Show the final group, order, source hash, counts, selected cabins, target
   room numbers, category warnings, and exact confirmation. Obtain current
   explicit approval before `rooms apply`; a prior request or confirmation for
   another plan is not reusable.
7. Apply once and require fresh read-back counts for passenger identities, room
   assignments, and notes to equal the source count. On an unknown response,
   do not retry; read Cowell first.

## Safety

- Preserve every unrelated group, order, passenger field, category, and room.
- Import names only when none match and the selected placeholder set is exact.
  Partial import and partial rooming are prohibited.
- Never infer passport, identity, date, sex, phone, email, category, or cabin.
- Never treat a category mismatch as permission to edit the Cowell category.
- A preview and exact confirmation are required for every business write.
- Stop on expired session, permission differences, changed controls, unknown
  write results, or incomplete read-back.

Report group/order identifiers and counts, cabins, room numbers, warnings,
confirmation, and verification status. Do not report passenger names or
passport values in the final summary.
