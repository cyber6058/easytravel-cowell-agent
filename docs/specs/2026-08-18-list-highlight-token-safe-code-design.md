# LIST highlight-token safe-code localization design

## Status

Selected design approved in conversation on 2026-08-18; written review is
pending. This specification changes diagnostic classification only. It does
not change highlight content, search behavior, color, or document layout.

## Observed failure

The authorized 4-day post-fix Word reproduction crossed the prior
`LIST_CELL_EXTRA_PARAGRAPH_SET_T1_R2_C3` blocker and then failed during
`run-action` with `LIST_HIGHLIGHT_TOKEN_MISSING`.

`Set-TokenHighlight` is shared by two callers:

- `Set-HeaderParagraph`, which knows the header paragraph number; and
- `Set-ListCell`, which knows the table, row, and column.

The shared function currently discards that context and throws one generic
code. The evidence therefore cannot distinguish a header failure from an
ordinary cell failure and cannot safely identify the affected coordinate.

## Required diagnostic contract

A missing non-empty highlight token must produce exactly one of these forms:

```text
LIST_HIGHLIGHT_TOKEN_MISSING_HEADER_P<paragraph>
LIST_HIGHLIGHT_TOKEN_MISSING_CELL_T<table>_R<row>_C<column>
```

Header codes contain only the paragraph number. The header cell is fixed by
the existing contract, so repeating T1/R1/C1 adds no useful evidence. Ordinary
cell codes contain table, row, and column. All numeric components are positive
decimal integers.

Invalid or ambiguous diagnostic metadata must fail closed as:

```text
LIST_HIGHLIGHT_CONTEXT_INVALID
```

No code may include the token, patched text, OP value, field label, product
identifier, or any other potentially sensitive content.

## Considered approaches

1. Build a bounded safe code at the caller boundary and pass it into
   `Set-TokenHighlight`. This is selected because the callers already own the
   relevant coordinates and the shared function remains focused on highlight
   search.
2. Pass context plus paragraph/table/row/column directly into
   `Set-TokenHighlight`. This was rejected because it couples the search helper
   to both caller shapes and creates several optional parameters.
3. Catch the generic exception in each caller and rethrow a contextual code.
   This was rejected because a broad catch could misclassify another Word COM
   failure and would preserve the generic throw internally.

## Selected design

Add `Get-ListHighlightMissingCode` with these mutually exclusive modes:

- `HEADER`: requires `ParagraphNumber > 0`; table, row, and column must remain
  zero;
- `CELL`: requires table, row, and column greater than zero;
  `ParagraphNumber` must remain zero; and
- every other combination throws `LIST_HIGHLIGHT_CONTEXT_INVALID`.

The helper formats the exact codes above. It does not accept or inspect a
highlight token or text range.

`Set-TokenHighlight` receives a mandatory `FailureCode`. Before its existing
empty-token early return, it verifies that the code exactly matches one of the
two bounded formats and therefore also satisfies the adapter's existing
`[A-Z][A-Z0-9_]{1,79}` safe-code contract. An invalid string throws the fixed
context-invalid code rather than the supplied string.

For a non-empty token, the existing range boundary, Word Find loop, yellow
highlight application, and match count remain unchanged. Only the final
zero-match throw changes from the generic literal to the validated
`FailureCode`.

`Set-HeaderParagraph` builds a header code from its already validated paragraph
number. `Set-ListCell` builds a cell code from the existing table number and
patch row/column. Neither caller passes text into the code builder.

## Error and compatibility behavior

- Empty highlight tokens still perform no Word Find and return normally, but
  caller metadata is validated first.
- Non-empty tokens with at least one match behave exactly as before.
- Non-empty tokens with zero matches throw the contextual safe code.
- The standalone generic throw `LIST_HIGHLIGHT_TOKEN_MISSING` is removed from
  the runtime script; the phrase remains only as the prefix of the new codes
  and in tests/documentation.
- Patch-plan schema, report schema, generator version, private calibration, and
  Python adapter parsing do not change because the existing adapter code regex
  already accepts both new forms.

## Test design

Offline regression tests must prove:

1. the code builder returns exact header and cell examples;
2. zero/negative numbers, mixed header-plus-cell metadata, and unsupported
   context fail as `LIST_HIGHLIGHT_CONTEXT_INVALID`;
3. `Set-TokenHighlight` validates `FailureCode` before the empty-token return;
4. header and cell callers pass the exact context they own;
5. the runtime script contains no standalone generic throw;
6. representative generated codes satisfy the existing safe-code regex and
   are at most 80 characters; and
7. the existing Word Find/highlight statements remain unchanged.

Run the focused PowerShell-adapter tests, PowerShell parser, complete offline
suite, `compileall`, static searches, and `git diff --check`. Tests must not
weaken, skip, or remove any highlight, paragraph, text, QR, font, or pagination
assertion.

## Scope and authorization boundary

The later offline implementation may modify only the repository PowerShell
adapter test/source, this design's implementation plan, and `STATUS.md`, then
create local commits. It does not authorize reading or modifying the private
master/calibration, starting Word COM, running another Word reproduction,
accessing NewAmazing or JMA, using Yating or ffmpeg, installing dependencies,
syncing installed runtime, LINE, Cowell, deploy, publish, push, or any external
write.

After complete offline validation, work stops. A new 4-day Word reproduction
requires a separate explicit authorization and is the only way to learn which
new contextual code the private path actually produces.

## Acceptance criteria

The diagnostic change is acceptable only when:

- every missing-token failure identifies header paragraph or ordinary-cell
  coordinates without including field content;
- invalid context always produces the fixed context-invalid code;
- successful and empty-token highlight behavior is unchanged;
- focused and complete offline validation passes;
- the private master, calibration, installed runtime, and Word processes are
  untouched; and
- Word success remains explicitly unverified until a separately approved
  reproduction completes.
