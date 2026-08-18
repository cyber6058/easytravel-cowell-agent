# LIST full-cell highlight range design

## Status

Offline diagnosis and selected design written on 2026-08-18. The OP approved
this written specification on 2026-08-18. The diagnosis remains bounded by the
no-Word authorization; implementation requires separate approval of the
offline implementation plan. No production implementation is authorized by
this document alone.

## Observed failure

The single authorized 4-day post-fix Word reproduction failed at:

```text
LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T4_R1_C2
```

The reproduction was not retried. It created no DOCX, PDF, or PNG. Postflight
confirmed that the owned Word process was cleaned up and the private master and
calibration remained unchanged.

T4/R1/C2 maps to `_build_guide_cells` and the unconfirmed
`emergency_contact_name`. For the synthetic draft, both the cell text and its
highlight token are the same seven-code-point `WAITING_FOR_OP` value.

## Offline diagnostic findings

The 4-day patch plan has seven highlighted ordinary cells in execution order:

- five T1 cells contain the token inside longer labeled text;
- T1/R2/C3 contains the same token twice and therefore exercises the existing
  repeated-Find loop; and
- T4/R1/C2 and T4/R1/C3 are the only cells whose complete visible text equals
  the highlight token.

The Word run reached T4/R1/C2. Therefore all five earlier embedded-token cells,
including the two-occurrence cell, passed `Set-TokenHighlight`. T4/R1/C2 is the
first full-cell token.

Before highlighting, `Set-ListCell` reacquires the cell, proves that it has one
paragraph, and compares the written visible text exactly with `Patch.text`.
Those checks passed in the Word run. Offline plan inspection also proved that
T4/R1/C2 `text` and `highlight_text` have identical code points. A missing or
mis-encoded token is therefore not supported by the current evidence.

The shared highlight helper currently uses this fixed boundary:

```text
Range.End - 1
```

A Word paragraph range ends in `U+000D`, so subtracting one removes its only
terminator. A Word cell range ends in `U+000D U+0007`, so subtracting one
removes only the cell marker and leaves `U+000D` inside the Find range. The
offline boundary model produced:

```text
PARAGRAPH_FULL current=visible length
CELL_EMBEDDED current=visible length + 1 CR
CELL_FULL     current=visible length + 1 CR
```

The first five embedded matches can succeed before the first whole-cell match
encounters this boundary shape.

Private-master OOXML inspection found that T4/R1/C2 and T4/R1/C3 both start
with two empty paragraphs and have the same normalized cell XML after width and
revision identifiers are removed. Their shared source topology may contribute
to Word range behavior, but it does not explain a C2-only defect; C2 is simply
processed before C3. The write-time one-paragraph assertion also proves that
the extra source paragraph does not survive as an ordinary output paragraph.

## Diagnostic conclusion and confidence

The best-supported root-cause inference is a boundary-sensitive Word Find
failure when the token is the complete visible cell text and the search range
still includes the cell's terminal paragraph mark.

This is an inference, not a live Word proof. The no-Word diagnostic boundary
prevents repeated reproduction or a one-variable COM probe. A later separately
authorized 4-day reproduction is required to prove that the selected change
crosses T4/R1/C2.

Lower-ranked alternatives are:

1. residual source-cell paragraph topology affects Find after replacement;
2. state inherited by Word Find changes whole-cell behavior; or
3. token encoding differs at runtime.

The first two remain possible but are weaker than the boundary explanation.
The third is contradicted by the exact post-write comparison, equal code points,
and earlier successful uses of the same token.

## Considered fixes

1. Build a terminator-aware visible range and directly highlight it when its
   complete text equals the token; use the existing Find loop only for embedded
   tokens. This is selected because it bypasses the exact Word Find shape that
   failed while preserving the proven multi-match path.
2. Only strip both cell terminators and continue using Find for every token.
   This is smaller, but without Word it cannot prove that a whole-range Find
   will succeed after the boundary change.
3. Special-case T4 guide cells in `Set-ListCell`. This is rejected because it
   hard-codes template coordinates and leaves every future full-cell unknown
   field exposed to the same failure.

## Selected design

Add `Get-ListVisibleRangeEnd` immediately before `Set-TokenHighlight`.

The helper:

- receives only a range-like object;
- reads `Start`, `End`, and `Text`;
- walks backward over terminal `U+000D` and `U+0007` code points, decrementing
  the visible end once per marker;
- does not trim spaces, tabs, `U+000B` manual line breaks, or any visible text;
- returns the visible end as an integer; and
- throws fixed `LIST_HIGHLIGHT_RANGE_INVALID` if the original or computed
  range bounds are inconsistent.

The helper is deliberately independent of Word methods. It can be exercised
offline with a synthetic object exposing `Start`, `End`, and `Text`.

`Set-TokenHighlight` retains its current mandatory, allowlisted `FailureCode`
validation before the empty-token return. For a non-empty token it then:

1. obtains the terminator-aware visible end;
2. duplicates the supplied range and bounds the duplicate to exactly the
   visible text;
3. compares visible text and token with case-sensitive exact equality;
4. when they are equal, applies `$WdYellow` to that visible duplicate and
   records one match without invoking Word Find;
5. otherwise releases the visible duplicate and runs the existing Find loop
   between `Range.Start` and the same terminator-aware visible end; and
6. throws the existing caller-bound `FailureCode` if neither path records a
   match.

The full-cell path is content-shape based, not coordinate based. T4/R1/C2 and
T4/R1/C3 use it today; any future full-cell token receives the same behavior.
The five embedded cells continue to use Word Find, including the two-match
T1/R2/C3 case.

All temporary COM duplicates introduced by the full-cell path must be released
in `finally`. The existing cursor advancement, Find text, forward direction,
no-wrap setting, yellow color, match counter, and contextual failure codes stay
unchanged for the embedded path.

## Error and compatibility behavior

- Invalid `FailureCode` still throws `LIST_HIGHLIGHT_CONTEXT_INVALID` before an
  empty token can return.
- Invalid range bounds throw only `LIST_HIGHLIGHT_RANGE_INVALID`; token or cell
  content is never included.
- Empty tokens remain a no-op and do not inspect or highlight the range after
  failure-code validation.
- Exact full-cell tokens receive one direct highlight operation.
- Embedded tokens retain the existing one-or-more Find behavior.
- Zero matches retain the caller-bound header paragraph or cell coordinate
  code.
- Patch-plan schema, report schema, generator version, private master,
  calibration manifest, output layout, font, QR, paragraph, pagination, and
  Python adapter parsing do not change.

## Test design

Offline implementation tests must prove:

1. the 4-day synthetic plan has five embedded highlighted cells followed by
   exactly two full-cell highlighted cells at T4/R1/C2 and T4/R1/C3;
2. T4/R1/C2 text and token are exact and contain no terminator;
3. the visible-end helper removes paragraph `U+000D` and cell
   `U+000D U+0007`, but preserves spaces, tabs, and `U+000B`;
4. inconsistent synthetic bounds produce `LIST_HIGHLIGHT_RANGE_INVALID`;
5. exact full-cell equality takes the direct yellow-highlight path before any
   Find call;
6. embedded text still uses the existing Find statements and preserves the
   two-occurrence cursor loop;
7. the caller-bound safe-code validation and header/cell wiring remain
   unchanged; and
8. no test is weakened, skipped, or removed.

Run the focused patch-plan and PowerShell-adapter tests, a no-COM PowerShell
probe of the visible-end helper, the PowerShell parser, the complete offline
suite, `compileall`, static searches, and `git diff --check`.

## Scope and authorization boundary

This diagnostic turn may write only this specification and `STATUS.md`, then
create a local documentation commit. It does not authorize implementation.

A later approved offline implementation may modify only:

- `scripts/briefing/patch_list_template.ps1`;
- `tests/unit/travel_briefing/test_windows_word.py`;
- `tests/unit/travel_briefing/test_word_list.py`; and
- `STATUS.md` plus the approved implementation plan.

It does not authorize Word COM, another Word reproduction, private-master or
calibration mutation, DRAFT generation, NewAmazing or JMA access, Yating,
ffmpeg, installed-runtime sync, LINE, Cowell, deploy, publish, push, or any
external write.

After full offline validation, implementation must stop. A new single 4-day
Word reproduction remains a separate explicit authorization and must not be
retried after either success or failure.

## Acceptance criteria

The offline design is acceptable only when:

- full-cell highlighting never depends on Word Find;
- embedded and repeated-token highlighting keep the current Find contract;
- only terminal CR/BEL markers are excluded from the highlight range;
- exceptions contain bounded safe codes and no token or OP content;
- no output-content, layout, schema, calibration, or private artifact contract
  changes; and
- Word success remains explicitly unverified until a separately authorized
  reproduction passes and produces renderable artifacts.
