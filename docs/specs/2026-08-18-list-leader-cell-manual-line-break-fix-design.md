# LIST leader cell manual-line-break fix design

## Status

Selected design and written specification approved by the OP on 2026-08-18.
This is a narrow bug-fix addendum to
`2026-08-18-list-word-output-normalization-design.md`.

## Observed failure

The authorized 4-day Word reproduction failed at write time with
`LIST_CELL_EXTRA_PARAGRAPH_SET_T1_R2_C3`. Table 1, row 2, column 3 is the
ordinary cell containing the tour-leader name and Taiwan phone number.

An offline reproduction using the real 4-day synthetic patch-plan path ran
three times and produced `U+000D` in that cell each time. The existing
PowerShell structure test remained green because it checks the range mutation
but does not inspect the patch payload. This is consistent with Word treating
the embedded carriage return as a second paragraph.

## Required presentation

The tour-leader name and Taiwan phone number remain on two visible lines. They
must be represented by one Word paragraph containing an explicit manual line
break (`U+000B`), not by two paragraphs. The cell must not have a blank line
after the phone value.

## Considered approaches

1. Replace the intentional carriage return at the Python plan-builder source
   with a manual line break and reject paragraph/cell markers at the plan
   boundary. This is selected because it preserves the intended display and
   keeps the Word adapter fail closed.
2. Convert all carriage returns inside the PowerShell adapter. This was
   rejected because it would silently normalize malformed or OP-supplied
   values and obscure their source.
3. Permit two paragraphs only for T1/R2/C3. This was rejected because it
   violates the approved one-paragraph ordinary-cell contract.

## Selected design

`_build_header_cells` will compose the leader cell as:

```text
領隊姓名：<value><U+000B>*台灣手機：<value>
```

The patch-plan boundary will validate every ordinary `CellPatch.text` before
returning the plan:

- `U+000D` carriage return is forbidden;
- `U+000A` line feed is forbidden;
- `U+0007` Word cell marker is forbidden;
- `U+000B` manual line break is allowed; and
- validation errors identify the contract only and never include field values.

No automatic conversion is performed. Invalid text fails closed before Word
COM starts. Header-paragraph handling remains unchanged because it already uses
`U+000B` for the separately approved long group-name split.

`Set-ListCell`, its Word range boundaries, the paragraph-count assertion, the
private canonical master, and the calibration manifest remain unchanged.

## Test design

The implementation uses the existing offline feedback loop as a regression:

1. Build the real 4-day synthetic patch plan.
2. Assert T1/R2/C3 contains exactly one `U+000B` between the two labels and no
   `U+000D`, `U+000A`, or `U+0007`.
3. Assert all ordinary cells reject each forbidden marker at the plan boundary
   without including the rejected value in the error.
4. Preserve the existing PowerShell test proving `Set-ListCell` writes only the
   visible range and asserts one paragraph.
5. Run focused Word-plan/adapter tests, the complete offline suite, PowerShell
   parser validation, `compileall`, and `git diff --check`.

Tests must not weaken, skip, or remove the existing one-paragraph assertion.

## Scope and authorization boundary

The offline implementation may modify only repository Python tests/source,
this design's implementation plan, and `STATUS.md`, then create local commits.
It does not authorize reading or modifying the private master/calibration,
starting Word COM, running a private Word reproduction, accessing NewAmazing
or JMA, using Yating or ffmpeg, installing dependencies, syncing installed
runtime, LINE, Cowell, deploy, publish, push, or any external write.

After the full offline suite passes, work stops. A post-fix Word reproduction
requires a new explicit authorization and remains the only way to verify that
the private master no longer fails at T1/R2/C3 and that the final visual output
has the intended two-line leader cell without a trailing blank line.

## Acceptance criteria

Offline acceptance requires all of the following:

- the actual 4-day synthetic plan carries `U+000B`, not `U+000D`, at T1/R2/C3;
- every ordinary cell is protected from CR, LF, and the Word cell marker;
- the adapter's one-paragraph fail-closed assertion remains intact;
- focused and complete offline validation passes; and
- no private file, Word process, network source, installed runtime, or external
  system is touched.

Word success remains unverified until a separately approved private-master
reproduction completes and its generated DOCX/PDF/PNG evidence is inspected.
