# LIST embedded Find boundary split design

## Status

Offline diagnosis and selected correction design were written on 2026-08-18.
This document awaits OP review. It does not authorize implementation, Word
COM, or another reproduction.

## Authorized scope

This turn is limited to offline diagnosis of the T1/R2/C2 embedded-highlight
regression, this written design, `STATUS.md`, and a local documentation commit.
No production source or test is changed by this document.

The turn does not authorize Word, private-master or calibration access, DRAFT
generation, NewAmazing or JMA GET, Yating, ffmpeg, LINE, Cowell, deploy,
publish, push, or any external write.

## Observed regression

The earlier single authorized 4-day Word run before the full-cell change passed
all five embedded highlighted cells and stopped at the first full-cell token:

```text
LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2
```

The full-cell correction then added a terminator-aware visible boundary and a
direct-highlight path. Its single authorized post-fix 4-day reproduction failed
at the first embedded highlighted cell:

```text
LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T1_R2_C2
```

The run stopped before T4/R1/C2, produced no DOCX, PDF, or PNG, and was not
retried. Therefore the direct full-cell path is not yet proven in Word.

## Feedback-loop boundary

The only red-capable live feedback loop is the already-consumed Word
integration reproduction. This turn cannot run it again because Word is
explicitly excluded. Offline Git comparison, source-contract tests, and a
range-boundary model can rank causes and define a falsifiable correction, but
they cannot prove Word behavior.

The current targeted offline tests pass:

```text
... [100%]
```

That green result is diagnostic evidence of a test gap, not evidence that the
Word regression is resolved. The source-contract test currently checks that
the Find statements exist, but it also expects the newly shared visible
boundary. It does not distinguish the known-good embedded Find boundary from
the full-cell direct-highlight boundary.

## Differential findings

Before the full-cell change, every non-empty token used:

```powershell
$boundary = [int]$Range.End - 1
$search.SetRange($cursor, $boundary)
```

After the change, both the exact full-cell comparison and embedded Find use:

```powershell
$boundary = Get-ListVisibleRangeEnd -Range $Range
```

The offline boundary model shows:

```text
HIGHLIGHT_COUNT=7
T1_R2_C2:SHAPE=EMBEDDED:OCCURRENCES=1:CURRENT_FIND_EXTRA=0:LEGACY_FIND_EXTRA=1:SELECTED=FIND
T1_R2_C3:SHAPE=EMBEDDED:OCCURRENCES=2:CURRENT_FIND_EXTRA=0:LEGACY_FIND_EXTRA=1:SELECTED=FIND
T1_R3_C1:SHAPE=EMBEDDED:OCCURRENCES=1:CURRENT_FIND_EXTRA=0:LEGACY_FIND_EXTRA=1:SELECTED=FIND
T1_R4_C1:SHAPE=EMBEDDED:OCCURRENCES=1:CURRENT_FIND_EXTRA=0:LEGACY_FIND_EXTRA=1:SELECTED=FIND
T1_R4_C2:SHAPE=EMBEDDED:OCCURRENCES=1:CURRENT_FIND_EXTRA=0:LEGACY_FIND_EXTRA=1:SELECTED=FIND
T4_R1_C2:SHAPE=FULL:OCCURRENCES=1:CURRENT_FIND_EXTRA=0:LEGACY_FIND_EXTRA=1:SELECTED=DIRECT
T4_R1_C3:SHAPE=FULL:OCCURRENCES=1:CURRENT_FIND_EXTRA=0:LEGACY_FIND_EXTRA=1:SELECTED=DIRECT
PARAGRAPH_LEGACY_MINUS_VISIBLE=0
CELL_LEGACY_MINUS_VISIBLE=1
PROPOSED_DIRECT_COUNT=2
PROPOSED_FIND_COUNT=5
```

A paragraph range ends in one `U+000D`, so `End - 1` and the computed visible
end are equal. A cell range ends in `U+000D U+0007`; `End - 1` removes only the
cell marker and leaves the terminal paragraph mark in the search range, while
the visible end removes both markers. Consequently the full-cell change altered
only the cell Find input. It did not alter the effective header-paragraph Find
boundary.

The content-shape plan remains seven highlighted ordinary cells: five embedded
cases use Find and two exact full-cell cases use the direct path. T1/R2/C3
contains two occurrences and continues to exercise cursor advancement.

## Ranked hypotheses

1. **Boundary regression:** excluding the terminal `U+000D` from an embedded
   cell Find range makes Word fail to find T1/R2/C2. This is best supported by
   the one-variable source differential and the before/after Word failure
   positions.
2. **Pre-Find range-state side effect:** duplicating, reading, bounding, and
   releasing the visible range before Find perturbs Word COM state. This is
   plausible but less directly supported.
3. **Text or token mutation:** T1/R2/C2 content changed. This is weak because
   the plan evidence and post-write exact assertions contradict it.

The selected correction tests hypothesis 1. If the next separately authorized
reproduction still fails at T1/R2/C2, hypothesis 1 is falsified for this
implementation and hypothesis 2 becomes primary. That run must stop without a
retry.

## Considered corrections

1. **Split the boundaries by operation.** Use a terminator-aware visible end
   for exact comparison and direct full-cell highlighting, but restore
   `Range.End - 1` for embedded Find. This is selected because it is the
   smallest change that restores the live-proven embedded input while
   preserving the full-cell bypass.
2. **Return both ends from a new boundary object or helper.** This centralizes
   the values but adds an abstraction with no second consumer and does not
   improve the behavior proof.
3. **Replace embedded Word Find with string indexes and range arithmetic.**
   This removes Find but introduces a larger unproven mapping between
   `Range.Text` indexes and Word range positions, especially for repeated
   tokens and `U+000B`.
4. **Revert the full-cell change.** This restores embedded behavior but returns
   to the known T4/R1/C2 full-cell failure and is therefore rejected.

## Selected design

Keep `Get-ListVisibleRangeEnd` unchanged. In `Set-TokenHighlight`, calculate two
explicitly named boundaries for a non-empty token:

```powershell
$visibleBoundary = Get-ListVisibleRangeEnd -Range $Range
$findBoundary = [int]$Range.End - 1
```

Use `$visibleBoundary` only to bound the duplicate used for exact visible-text
comparison and direct full-cell highlighting.

When the visible text equals the token with case-sensitive exact equality:

- apply `$WdYellow` directly to the visible duplicate;
- record exactly one match; and
- do not call Word Find.

When the visible text does not equal the token:

- release the visible duplicate through the current cleanup path;
- run the existing embedded Find loop with
  `$search.SetRange($cursor, $findBoundary)`;
- retain the current Find text, forward direction, no-wrap setting, cursor
  advancement, repeated-match behavior, yellow highlight, and match counter;
  and
- retain the existing caller-bound safe failure code when there are no
  matches.

The branch is selected by content shape, not by table, row, or column. The five
embedded cases use the legacy Find boundary; the two exact full-cell cases use
the visible direct path. Header-paragraph behavior remains unchanged because
its legacy and visible boundaries are equal.

Do not add another helper merely to carry the two integers. Do not change the
existing cleanup behavior for the visible duplicate or broaden this correction
into unrelated COM-object cleanup.

## Compatibility and non-goals

The correction must not change:

- `Set-HeaderParagraph` or `Set-ListCell` caller behavior;
- failure-code validation or caller-bound safe-code wiring;
- empty-token behavior;
- patch-plan or report schema, generator version, or Python parsing;
- output content, table structure, layout, QR policy, 12-point typography,
  paragraph rules, or pagination;
- the private master, calibration manifest, or normalized fingerprint; or
- any data-source, audio, video, delivery, deployment, or Cowell behavior.

No coordinate-specific fallback is permitted. No OP content or token may be
included in an exception.

## Future implementation test design

Implementation must be test-first. Update the adapter source-contract test so
it fails against the current implementation and explicitly proves both
boundaries:

1. `$visibleBoundary` is produced by `Get-ListVisibleRangeEnd` and bounds only
   the duplicate used by exact comparison/direct highlighting;
2. `$findBoundary` is assigned `[int]$Range.End - 1`;
3. embedded Find calls `$search.SetRange($cursor, $findBoundary)`;
4. the direct equality branch records one match without calling Find;
5. the embedded path retains its cursor loop and repeated-token behavior; and
6. no table/row/column special case is added.

Preserve or strengthen the content-shape control proving five Find cases and
two direct cases, including two occurrences at T1/R2/C3. Preserve the no-COM
helper cases proving that terminal CR/BEL are removed from visible ranges while
spaces, tabs, and `U+000B` are retained. Preserve safe-code validation and
header/cell caller-wiring tests.

After the minimal source change, run focused tests, the PowerShell parser, the
no-COM boundary model, the complete offline suite, `compileall`, static checks,
and `git diff --check`. Do not weaken, skip, or delete tests.

Offline implementation must stop after validation. A Word reproduction remains
a fresh, separate, single-use authorization.

## Acceptance criteria

The future correction is acceptable only when:

- exact full-cell highlighting never uses Word Find;
- embedded and repeated-token cell Find uses the legacy `End - 1` boundary;
- header-paragraph Find behavior is unchanged;
- the implementation contains no coordinate-specific case;
- tests explicitly distinguish visible/direct and embedded/Find boundaries;
- all offline validation passes without Word or private-artifact access;
- output, schema, formatting, calibration, and safe-code contracts are
  unchanged; and
- Word success remains labeled unverified until a separately authorized run
  crosses T1/R2/C2 and produces renderable artifacts.

## Review gate

OP approval of this document authorizes creation of an offline implementation
plan only. It does not authorize editing production code or tests. The next
approval phrase is:

```text
同意此書面規格，開始建立離線實作計畫
```
