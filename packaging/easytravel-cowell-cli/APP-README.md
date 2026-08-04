# EasyTravel Cowell CLI

This package provides one integrated Skill for 立益旅行社:

1. prepare a validated official 19-column Cowell roster from passport PDFs or
   photos; and
2. fill passenger names and room assignments in an order the OP already
   created, or apply rooms only when all names already exist in Cowell.

The EasyTravel workflow requires an exact group code, existing order ID, and
local DOCX/XLSX rooming file. It never creates a group, order, or passenger
slot. If rows are missing, the OP corrects the order in Cowell and reruns the
preview.

## Rooming workflow

Run offline parsing and planning first:

```powershell
python -m cowell_cli.cli rooms parse "<ROOMING_FILE>" --format json
python -m cowell_cli.cli rooms plan "<ROOMING_FILE>" --group-code <GROUP> --order-id <ORDER> --format json
```

Then run the read-only live preview:

```powershell
python -m cowell_cli.cli rooms preview "<ROOMING_FILE>" --group-code <GROUP> --order-id <ORDER> --format json
```

If none of the source names exists, a valid plan imports every name and then
applies every room. If all names already match, it skips name import and applies
rooms only. Partial matches always stop without writing.

One placeholder cabin is detected automatically and must be bound to the final
plan. Several cabins require an exact source-sequence-to-cabin JSON map from
the OP. Adult, child, and infant differences are warnings only; existing Cowell
categories and cabins are preserved.

Every apply requires the exact confirmation from the final preview and current
operator approval. A fresh Cowell read-back must verify all names, room
assignments, and notes. Never retry an unknown result without reading state.

## Passport roster workflow

Use `passports prepare`, visually inspect every resulting passport image,
record printed fields and both MRZ lines locally, then run `passports validate`
and `passports export`. Normal export requires valid TD3 MRZ check digits and
no unresolved uncertainty. Generated images, JSON, and workbooks are private
local PII and must never be committed.

## Safety

- Let the OP log in manually through the controlled Chrome profile.
- Never request, store, or type a Cowell password.
- Never infer or change passport data, identity, cabin, or passenger category.
- Never partially import names or rooms.
- Stop on permission differences, changed controls, ambiguous identities,
  insufficient rows, collisions, or incomplete read-back.
