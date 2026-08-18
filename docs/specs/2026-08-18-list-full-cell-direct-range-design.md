# LIST full-cell direct range retreat design

## Status

Offline diagnosis and the selected correction design were written on
2026-08-18. OP approved this document on 2026-08-18 for creation of an offline
implementation plan only. It does not authorize production or test changes,
Word COM, or another reproduction.

## Authorized scope

This turn is limited to offline diagnosis of the T4/R1/C2 full-cell direct
highlight failure, this written design, `STATUS.md`, and a local documentation
commit.

It does not authorize editing production or tests, running Word, reading or
changing the private master or calibration, generating DRAFT artifacts,
NewAmazing or JMA GET, Yating, ffmpeg, LINE, Cowell, deploy, publish, push, or
any external write.

## Latest live evidence

The single authorized boundary-split 4-day Word reproduction passed the five
embedded highlighted cells and failed at the first full-cell token:

```text
LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2
```

The exact result was:

```text
WORD_GENERATION_FAILED
HRESULT=-2146233087
RETURN_CODE=30
STAGE=run-action
1 failed in 23.37s
```

The run was not retried. It produced no DOCX, PDF, or PNG. Postflight returned
WINWORD to the existing baseline of 1 and confirmed the private master hash,
schema-2 calibration, normalized structure, and pdftoppm remained normal.

Because T4/R1/C2 is the first exact full-cell token after five embedded cases,
the result supports the restored embedded Find boundary and isolates the
remaining failure to the full-cell direct path.

## Feedback-loop boundary

The only loop that exercises the exact Word failure is the separately approved
4-day integration test. Its one-run authorization has been consumed, and this
turn explicitly excludes Word. Therefore this diagnosis can explain the
observed contradiction and design a falsifiable correction, but cannot claim
that Word has been fixed.

The current four relevant offline tests all pass:

```text
.... [100%]
```

That green result is a test gap. The tests verify the current source statements
and a text-code-point model; they do not model Word's compound cell end marker
and range-coordinate behavior.

## Offline diagnostic findings

### The direct branch did not record a match

`Set-TokenHighlight` throws the caller-bound T4/R1/C2 code only when
`$matches` remains zero after both paths. In the direct branch, `$matches` is
set to 1 only when:

```powershell
[string]$visibleRange.Text -ceq $Token
```

The latest error therefore proves that the direct exact comparison was false;
it is not evidence that assigning `$WdYellow` threw or silently failed.

### The immediately preceding End-minus-one comparison passed

Before highlighting, `Set-ListCell` reacquires the same cell and executes:

```powershell
$postRange = $cell.Range.Duplicate
$postRange.End = [int]$postRange.End - 1
if ([string]$postRange.Text -cne [string]$Patch.text) {
    throw "LIST_CELL_TEXT_MISMATCH"
}
```

The Word run reached `Set-TokenHighlight`, so this exact assertion passed at
T4/R1/C2. The patch plan also proves
`Patch.text == Patch.highlight_text == WAITING_FOR_OP` for that cell.
Consequently a duplicate bounded by one Word position from the cell end is the
strongest available live-proven exact-text range.

### The helper subtracts text code points from Word positions

`Get-ListVisibleRangeEnd` reads `Range.Text`, counts every trailing `U+000D`
and `U+0007`, then subtracts that count from `Range.End`.

This works for a paragraph range: its one textual `U+000D` terminator occupies
one retreat from `Range.End`. A Word cell exposes `U+000D U+0007` in
`Range.Text`, but the passing `Set-ListCell` assertion proves that one
`Range.End` retreat already produces the exact visible cell text. The cell's
two textual marker code points therefore cannot be treated as two independent
range positions.

For T4/R1/C2, the helper retreats two positions while the live-proven cell
operation retreats one. It removes one additional visible token position.

### Offline compound-marker model

A no-COM range-like model used a seven-position token, a paragraph text tail
of `U+000D`, and a cell text tail of `U+000D U+0007`. The cell model's marker
range span is one, derived from the live `Set-ListCell` exact-text invariant.
The current helper produced:

```text
TOKEN_RANGE_SPAN=7
PARAGRAPH_TEXT_TERMINATOR_CODEPOINTS=1
PARAGRAPH_RANGE_TERMINATOR_SPAN=1
PARAGRAPH_CURRENT_VISIBLE_SPAN=7
CELL_TEXT_TERMINATOR_CODEPOINTS=2
CELL_RANGE_TERMINATOR_SPAN=1
CELL_CURRENT_VISIBLE_SPAN=6
CELL_EXPECTED_VISIBLE_SPAN=7
CELL_OVER_RETREAT=1
SELECTED_DIRECT_END_RETREAT=1
WINWORD_COUNT_BEFORE_MODEL=1
WINWORD_COUNT_AFTER_MODEL=1
```

This model is not Word proof; its purpose is to make the contradiction between
text code points and range positions explicit.

## Diagnostic conclusion and confidence

The best-supported cause is that `Get-ListVisibleRangeEnd` over-retreats a
cell range by one position. The direct duplicate consequently omits the final
visible character, exact equality is false, and execution falls back to the
already-known whole-cell Word Find shape, which records no match.

Confidence is high as an inference because all of the following must be true in
the same live execution:

- `Set-ListCell` with `End - 1` exactly matched `Patch.text`;
- `Patch.text` exactly equaled the highlight token;
- the helper changed only the direct boundary to an effective `End - 2`; and
- the direct equality did not set `$matches`.

It remains falsifiable. If the selected one-position direct range still fails
at T4/R1/C2 in a later separately authorized Word run, compound-marker
over-retreat is not the complete cause and no retry is permitted.

## Ranked hypotheses

1. **Compound-marker over-retreat.** If this is the cause, using the same
   duplicate `End - 1` operation that passed `Set-ListCell` will make the
   direct text equal the token and bypass Find.
2. **`SetRange` versus direct `End` mutation.** Word may treat a bounded cell
   duplicate differently when `SetRange` is called. Reusing direct `End`
   mutation also removes this unproven difference without adding another
   variable.
3. **Runtime token or cell mutation.** If content changes between the
   post-write assertion and highlight call, the one-position range will still
   differ. This is weak because the calls are adjacent and use the same cell,
   patch, and token.
4. **Highlight assignment failure.** This cannot explain the safe-code error:
   `$matches = 1` follows the assignment inside the equality branch, while the
   observed code requires the equality branch not to record a match.

## Considered corrections

1. **Reuse the live-proven duplicate `End - 1` operation and remove the
   helper.** This is selected. It has the smallest semantic surface, matches
   the immediately preceding passing assertion, avoids translating text code
   points into Word positions, and preserves the separate Find boundary.
2. **Keep the helper but special-case `U+000D U+0007` as one range position.**
   This can produce the same end coordinate, but retains a one-consumer
   abstraction based on the exact text/range mapping that caused the bug.
3. **Pass a pre-bounded range from `Set-ListCell` into the highlight helper.**
   This couples COM ownership and cleanup across callers, complicates header
   paragraphs, and expands the change beyond the isolated helper.
4. **Special-case T4 guide cells.** This is rejected because the defect is a
   full-cell content shape, not a template coordinate.

## Selected design

Remove `Get-ListVisibleRangeEnd`; it has only one production caller and its
text-code-point abstraction is invalid for the observed Word cell range.

Keep `$findBoundary = [int]$Range.End - 1` unchanged for embedded and repeated
Find. Do not merge the direct and Find paths even though their final numeric
end is expected to match; their operations and evidence remain distinct.

In `Set-TokenHighlight`, retain failure-code validation and the empty-token
return. For a non-empty token:

1. initialize the existing cursor, match counter, and visible duplicate;
2. duplicate the supplied paragraph or cell range;
3. calculate one direct end retreat from the duplicate's own `End`;
4. fail with the existing safe code `LIST_HIGHLIGHT_RANGE_INVALID` if the
   retreated end would be less than `Start`;
5. assign the retreated value directly to `$visibleRange.End`;
6. compare its text with the token using the existing case-sensitive exact
   equality;
7. on equality, apply `$WdYellow` and record exactly one match without Find;
8. release the duplicate in the existing `finally`; and
9. only when no direct match was recorded, run the unchanged Find/cursor loop
   through `$findBoundary`.

The essential source shape is:

```powershell
$findBoundary = [int]$Range.End - 1
$visibleRange = $Range.Duplicate
$directEnd = [int]$visibleRange.End - 1
if ($directEnd -lt [int]$visibleRange.Start) {
    throw "LIST_HIGHLIGHT_RANGE_INVALID"
}
$visibleRange.End = $directEnd
```

The variable name may follow existing PowerShell conventions, but there must
be one and only one direct retreat. Do not inspect or trim `Range.Text` to
derive a Word coordinate.

For paragraph ranges, one retreat removes terminal `U+000D`. For cell ranges,
it reuses the exact operation already proven by the same-cell post-write
assertion. Spaces, tabs, and `U+000B` inside the visible content remain
untouched.

## Error and compatibility behavior

- Invalid caller-bound `FailureCode` still throws
  `LIST_HIGHLIGHT_CONTEXT_INVALID` before empty-token return.
- An impossible range retreat throws only `LIST_HIGHLIGHT_RANGE_INVALID` and
  does not include token, cell text, or OP content.
- Empty tokens remain no-ops after failure-code validation.
- Exact full-cell tokens use direct highlight and never depend on Find.
- Embedded and repeated tokens retain the live-proven `End - 1` Find boundary,
  Find settings, counter, and cursor advancement.
- Zero matches retain the caller-bound header or cell-coordinate code.
- `Set-HeaderParagraph`, `Set-ListCell`, safe-code wiring, patch-plan schema,
  report schema, generator version, QR policy, 12-point typography, paragraph
  rules, pagination, layout, private master, and calibration do not change.

## Future implementation test design

Implementation must be test-first and remain at the already approved adapter
source-contract seam. Replace the incorrect helper model with a red regression
that requires the live-proven direct range operation:

1. `Get-ListVisibleRangeEnd` function and call are absent;
2. the direct duplicate computes exactly one `End - 1` retreat;
3. safe invalid-range validation occurs before assigning the duplicate end;
4. direct equality, `$WdYellow`, `$matches = 1`, and `finally` cleanup stay in
   their current order;
5. `$findBoundary = [int]$Range.End - 1`, the Find settings, and cursor loop
   remain unchanged;
6. `Set-ListCell` retains its existing one-position write and post-write
   exact-text checks;
7. the direct helper contains no `Trim`, `TrimEnd`, terminal-code-point loop,
   coordinate special case, or OP content in errors; and
8. the content-shape control remains five embedded Find cases, two exact direct
   cases, and two occurrences in T1/R2/C3.

The new source-contract test must fail against current commit `bafc06b` because
the text-counting helper still exists and the direct duplicate does not mutate
its own `End` by one.

After the minimal source change, run the focused adapter and patch-plan tests,
the PowerShell parser, a no-COM compound-marker model, the complete offline
suite, `compileall`, static/non-change checks, and `git diff --check`. No test
may be weakened, skipped, or deleted.

The offline model must use independent text-code-point and range-position
counts. It must prove that one paragraph retreat preserves seven token
positions and one cell retreat also preserves seven, while the removed
text-counting algorithm would preserve only six for a compound cell marker.

## Scope and authorization boundary

This diagnostic turn may write only this specification and `STATUS.md`, then
create a local documentation commit. It does not authorize implementation.

A later approved offline implementation plan may propose changes only to:

- `scripts/briefing/patch_list_template.ps1`;
- `tests/unit/travel_briefing/test_windows_word.py`;
- this plan/spec status and `STATUS.md`.

It should use `tests/unit/travel_briefing/test_word_list.py` only as an
unchanged content-shape control. Any need to modify that file, a caller, schema,
formatting contract, private artifact, or installed runtime requires a new
scope review.

Offline implementation approval will not authorize Word, another reproduction,
private-master or calibration mutation, DRAFT generation, GET, JMA, Yating,
ffmpeg, LINE, Cowell, deploy, publish, push, or any external write.

## Acceptance criteria

The future correction is acceptable only when:

- direct full-cell comparison uses the same one-position range retreat already
  proven by `Set-ListCell`;
- no text-code-point count is converted into a Word range coordinate;
- exact full-cell highlighting bypasses Find;
- embedded/repeated Find behavior and safe failure codes remain unchanged;
- no coordinate or field-specific branch is added;
- helper removal and the one-position direct operation are explicitly locked
  by red-then-green tests;
- all offline validation passes without Word or private-artifact access;
- content, schema, formatting, calibration, and output contracts do not
  change; and
- Word success remains unverified until a separately authorized single 4-day
  reproduction crosses T4/R1/C2 and produces renderable artifacts.

## Review gate

OP approved this document on 2026-08-18 using the following phrase. That
approval authorizes creation of an offline implementation plan only and does
not authorize editing production code or tests:

```text
同意此書面規格，開始建立離線實作計畫
```
