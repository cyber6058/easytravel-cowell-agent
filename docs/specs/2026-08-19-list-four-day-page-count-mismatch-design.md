# LIST 4-day exported-page authority design

## Status

Offline diagnosis and the selected correction design were written on
2026-08-19. OP approved this document on 2026-08-19; the separate offline
implementation plan is waiting for OP approval. Production, tests, Word COM,
and another reproduction remain unchanged and unauthorized.

## Authorized scope

This turn is limited to the retained 4-day failure evidence, offline source and
DOCX inspection, this written design, `STATUS.md`, and a local documentation
commit.

It does not authorize editing production or tests, starting Word, reading or
changing the private master or calibration, generating DRAFT artifacts,
NewAmazing or JMA GET, Yating, ffmpeg, LINE, Cowell, deploy, publish, push, or
any external write.

## Latest live evidence

The single authorized 4-day post-fix Word reproduction crossed the previous
T4/R1/C2 highlight blocker and created a 32,768-byte `LIST.docx`. It then
failed in `render_list_word_for_qa` with:

```text
expected_page_count=2
ValueError: Word report and PDF LIST page count do not match
1 failed in 35.45s
WORD_REPRO_EXIT=1
```

The run was not retried. Its temporary PDF and render report were removed by
the existing temporary-directory cleanup, so the PDF inspection's exact page
count is no longer directly observable. The failure proves only that it was
not 2.

The retained output contains `LIST.docx` but no PDF, PNG, or QA index.
Postflight returned WINWORD to the existing baseline of 1 and confirmed that
the private master and calibration manifest were unchanged.

## Existing data flow

The value named `expected_page_count` is not an independent expectation:

1. `patch_list_template.ps1` saves and reopens the DOCX, calls Word
   `ComputeStatistics(wdStatisticPages)`, and writes that value as
   `computed_page_count` in the patch report.
2. `build_list_word()` copies the report value into
   `ListWordBuildResult.computed_page_count`.
3. `LocalRenderBackend.render_word()` passes that same observation to
   `render_list_word_for_qa()` as `expected_page_count`.
4. `render_list_template.ps1` independently calls the same Word statistic
   before `ExportAsFixedFormat()` and writes another
   `computed_page_count`.
5. Python opens the exported PDF with PyMuPDF and compares its actual page
   count with the two Word statistics.

The workflow therefore promotes one pre-export Word observation into an
independent expected value, then compares another pre-export observation from
the same API against it. Agreement between the two Word values does not prove
the exported artifact has that many pages.

## Offline retained-artifact evidence

Read-only OOXML inspection of the retained DOCX found:

```text
docProps/app.xml Pages=1
body paragraphs=7
tables=4
table rows=4,3,5,1
manual page breaks=0
last rendered page breaks=0
pageBreakBefore=0
section properties=1
```

The daily table has one repeated header plus four non-splittable day rows. The
single section has an empty first-page header and a primary continuation
header, as designed. No structural second-page instruction was found.

The saved `Pages=1` property is Word-authored artifact metadata, but it can be
stale and is not sufficient to replace rendered QA. Combined with the live
fact that the exported PDF was not 2 pages, it strongly supports a one-page
artifact. Because the temporary PDF is gone, `PDF page_count=1` remains an
inference rather than a directly observed fact.

## Offline feedback loop and test gap

The exact Word-to-PDF path cannot be rerun in this turn. A deterministic,
no-COM retained-artifact check compares the recorded expected value with the
saved DOCX page metadata and goes red:

```text
RECORDED_EXPECTED_PAGE_COUNT=2
SAVED_DOCX_METADATA_PAGES=1
OFFLINE_PAGE_CONTRACT_MISMATCH=1
```

Three focused existing contracts still pass:

```text
..... [100%]
```

Those tests currently prove that:

- patch pagination is measured after SaveAs and reopen;
- `build_list_word()` accepts Word report page counts independent of day
  count; and
- an explicit expected count mismatch is rejected before publishing.

They do not model the observed case in which the Word statistic is 2, the
exported PDF has a different actual count, and no independent page-count
expectation exists. That missing seam allowed the patch statistic to be
misnamed and reused as an expectation.

## Diagnostic conclusion

The root contract defect is not that 4 days were planned as 2 pages. The patch
plan contains no page-count prediction. The defect is that Word's
`ComputeStatistics` result was promoted from a layout observation to the
authoritative exported-artifact page count.

The retained run proves that this statistic can disagree with the PDF
produced by the same Word session. It is therefore unsuitable as the final QA
authority by itself.

This conclusion does not prove why Word returned 2. Possible internal causes
include pagination cache state, first-page-versus-primary header layout, or a
pre-export calculation that changes during fixed-format export. Distinguishing
those Word internals is unnecessary for a safe correction because the PDF,
PNG set, and QA index are the actual reviewed artifacts.

## Ranked hypotheses

1. **Pre-export Word page statistics are not export-grounded.** If this is the
   cause, using the inspected PDF as canonical will accept the retained
   one-page shape while keeping all content and per-page checks active.
2. **Export refreshes pagination after the statistic is read.** Moving the
   statistic after export might make it 1, but the current evidence does not
   prove the same API becomes reliable after that ordering change.
3. **The PDF inspector undercounted pages.** This is weak: PyMuPDF reads the
   PDF page tree directly, and existing synthetic 1/2/3-page tests pass. A
   malformed or empty extra page would still appear in `document.page_count`.
4. **Four days genuinely require two pages.** This conflicts with the saved
   one-page metadata, absence of page-break structures, ordinary synthetic
   content, and the integration contract that this 4-day fixture is one page.

## Considered corrections

1. **Make the inspected exported PDF canonical and keep Word statistics as
   diagnostics.** This is selected. It directly measures the reviewed output
   and preserves PDF-to-PNG-to-index equality plus day-token page validation.
2. **Move `ComputeStatistics` after `ExportAsFixedFormat` and retain strict
   equality.** This is smaller in concept but remains dependent on the same
   API that produced the false count. It risks another Word-only iteration
   without improving content validation.
3. **Hard-code 4/5-day cases to one page or trust `docProps/app.xml`.** This is
   rejected because pagination must remain content-driven for every positive
   trip length, and saved metadata is not a rendered-artifact authority.
4. **Only improve the mismatch error.** Safe counts would aid diagnosis but
   would not let a valid exported artifact complete QA, so this is not a
   correction by itself.

## Selected design

The exported PDF inspection becomes the canonical final page-count evidence.
Word's patch and render `computed_page_count` values remain positive,
schema-validated diagnostic observations; neither is silently relabeled as an
independent expected value.

`LocalRenderBackend.render_word()` must stop passing
`built.computed_page_count` as `expected_page_count`. The backend has no
independent page-count requirement because the approved layout is
content-driven.

`render_list_word_for_qa()` must follow this order:

1. run the bounded Word render adapter once;
2. validate the render report schema, positive Word statistic, PDF existence,
   and exact PDF byte count;
3. inspect the PDF with PyMuPDF;
4. when the caller supplied no independent `expected_page_count`, use
   `inspection.page_count` as the required artifact page count;
5. when a caller deliberately supplied an independent positive
   `expected_page_count`, retain strict equality with the inspected PDF;
6. validate required text, A4 geometry, image policy, continuation identity,
   daily header, and every date token against the PDF pages;
7. render exactly `inspection.page_count` PNGs in one bounded pdftoppm call;
8. require contiguous non-empty PNGs and publish a QA index whose page count
   and page list exactly match the PDF; and
9. return `pdf_inspection.page_count` as the artifact page count while
   retaining the render report's `computed_page_count` only as diagnostic
   evidence in `ListWordQaResult`.

The existing `day_page_map` remains a fail-closed cross-check. If Word says a
day starts on page 2 but the PDF has one page, or if its unique date token is
not on the reported page exactly once, QA still fails. This prevents the
selected design from hiding a real missing or moved page.

No day-count branch is added. The current synthetic Gate V expectations remain
unchanged: its ordinary 4/5-day fixtures must produce one page, while its
longer fixtures exercise natural continuation behavior.

## Superseded page-count clause

This design changes only the earlier requirement that Word
`ComputeStatistics`, PDF count, and PNG count must always be numerically equal.
The retained artifact demonstrates that Word's statistic can be a false
positive even when the exported page set is different.

The replacement acceptance chain is:

```text
inspected PDF page count
  = contiguous PNG count
  = QA index page count
  = published WordRenderEvidence.page_count
```

Word's `computed_page_count` remains recorded in memory as a diagnostic. The
PDF-to-day-map and PDF-to-date-token checks continue to bind Word layout
semantics to the exported artifact. All other dynamic LIST, typography, QR,
content, A4, continuation, and fail-closed requirements remain unchanged.

## Error and compatibility behavior

- Missing, empty, wrong-size, or unreadable PDF remains blocking.
- Invalid render-report schema or non-positive Word statistic remains
  blocking; only numeric inequality with the inspected PDF becomes
  non-authoritative.
- A truly independent explicit expected count still blocks on mismatch.
- PDF/PNG/index count mismatch remains blocking.
- Missing required text, unexpected images, wrong A4 geometry, invalid
  continuation header, missing/duplicate date token, or invalid day page map
  remains blocking.
- Legacy single-PNG mode still accepts only an inspected one-page PDF.
- No exception may include itinerary text, OP values, private paths, or source
  content. Page-count diagnostics are safe integers.
- Patch-plan schema, render-report schema, generator version, Word ownership,
  timeout, no-retry behavior, private master, calibration, QR removal,
  12-point typography, paragraph normalization, and content do not change.

## Future implementation test design

Implementation must be test-first at the existing QA and backend seams.

### Red regression in `test_word_qa.py`

Create an adapter whose render report says 2 while it writes a valid one-page
synthetic PDF. Call `render_list_word_for_qa()` without an independent
`expected_page_count`. The expected result is successful publication of one
PDF page, one PNG, and an index with `page_count=1`, while
`result.computed_page_count` retains the diagnostic value 2.

The test must fail against current code with:

```text
Word report and PDF LIST page count do not match
```

Retain the existing explicit-mismatch test. It supplies
`expected_page_count=2` for a one-page PDF and must continue to fail before
publication.

### Backend composition regression

Make the synthetic build result report 2 and the synthetic QA result report an
inspected one-page PDF. Assert that `LocalRenderBackend` does not pass
`expected_page_count`, and that returned `WordRenderEvidence.page_count` is 1.

### Unchanged controls

- 1/2/3-page PDF inspection and pdftoppm page-set tests;
- day-page-map and unique date-token checks;
- render-report schema and byte-count checks;
- content-driven pagination tests that allow 7/8-day outcomes to depend on
  Word layout rather than day count;
- PowerShell pagination-order and ownership contracts; and
- the opt-in 4/5/6/7/8/12-day Gate V integration test.

After the minimal change, run the two focused unit files, all Word/LIST focused
tests, the complete offline suite, `compileall`, PowerShell parser checks,
static non-change checks, and `git diff --check`. No test may be weakened,
skipped, or deleted.

## Implementation scope boundary

A future offline implementation plan may propose changes only to:

- `src/travel_briefing/workflow.py`;
- `src/travel_briefing/word_qa.py`;
- `tests/unit/travel_briefing/test_local_backend.py`;
- `tests/unit/travel_briefing/test_word_qa.py`;
- the approved plan/spec status and `STATUS.md`.

`word_list.py`, both Word PowerShell adapters, calibration, private artifacts,
formatting, and integration expectations are unchanged controls. If
implementation evidence requires changing any of them, stop and return for a
new scope review instead of expanding the patch.

Offline implementation approval will not authorize Word, another
reproduction, private-master or calibration mutation, DRAFT generation, GET,
JMA, Yating, ffmpeg, LINE, Cowell, deploy, publish, push, or any external
write.

## Acceptance criteria

The future correction is acceptable only when:

- no Word statistic is passed as an independent expected page count;
- the inspected PDF controls the PNG set, QA index, and published page count;
- explicit independent expectations remain strict;
- Word diagnostic page counts remain positive and available without deciding
  artifact validity;
- day-page-map and date-token validation still catch missing or moved pages;
- no hard-coded day-count pagination rule is added;
- all focused and complete offline validation passes;
- no production file outside the four-file implementation scope changes; and
- Word success remains unverified until a separately authorized single 4-day
  reproduction produces DOCX, PDF, PNGs, and a QA index.

## Review gate

OP approved this document on 2026-08-19 with:

```text
同意此書面規格，開始建立離線實作計畫
```

That approval authorized only creation of the separate offline implementation
plan. It did not authorize editing production or tests, running Word, or any
later integration.
