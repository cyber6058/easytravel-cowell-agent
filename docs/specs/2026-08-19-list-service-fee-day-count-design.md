# LIST dynamic service-fee notice design

## Status

The OP approved this written specification in conversation on 2026-08-19.
The corresponding offline implementation plan is now written and awaits a
separate OP approval. No production or test implementation has been authorized
or performed.

## Authorized scope

This design is limited to the fixed service-fee sentence preserved from the
calibrated LIST master and the offline contracts required to render that
sentence from the trip's actual day count.

This turn may read repository source, tests, the retained synthetic 4-day QA
evidence, and project documentation. It may write this specification and
`STATUS.md`, then create a local documentation commit.

It does not authorize production or test edits, private master or calibration
changes, Word COM, a new DOCX/PDF/PNG, NewAmazing or JMA GET, Yating, ffmpeg,
LINE, Cowell, deploy, publish, push, or another integration run.

## Observed defect

The single authorized 4-day Word integration run succeeded:

```text
1 passed in 33.42s
WORD_REPRO_EXIT=0
```

The same-run DOCX, one-page PDF, PNG, and schema-2 QA index passed the selected
layout contracts: the QR was removed, the first-page identity block used the
available width, every non-title PDF span was 12 pt, and non-title table cells
had no extra paragraph.

Manual content QA found a separate contradiction. The product was
`合成大阪4日`, while the preserved notice still stated:

```text
六天共新台幣 1,800 元
```

The same paragraph states that the fee is NTD 300 per person per day. The
calculated 4-day total is therefore NTD 1,200. The PDF contained the fixed
6-day text and did not contain the calculated 4-day text.

The retained generated DOCX exposes the complete canonical source paragraph
as:

```text
2. 本行程不接受在台灣事先支付導遊司機的服務費，因為尚未服務，本行程導遊司機的服務費每人每天新台幣300元，六天共新台幣1,800元，請一律在日本當地支付給導遊
```

This defect does not invalidate the page-authority or layout fixes. It does
block the artifact from being used as correct briefing material.

## Existing behavior and gap

The fixed sentence is not present in Python or PowerShell source. It is static
body text inherited from the private master.

The current schema-3 `ListPatchPlan` supports only:

- four header paragraph patches;
- table-cell patches;
- table, QR, font, pagination, and layout contracts.

The Word adapter does not have a safe locator or patch type for an ordinary
main-story body paragraph. A global replacement of `六天` or `1,800` would be
outside the current contract and could modify unrelated content.

## Approved business rule

1. The Japan tour-guide and driver service fee is fixed at NTD 300 per person
   per trip day.
2. `BriefingDraft.product.day_count` is the only day-count authority.
3. The total is calculated as `day_count * 300`; no total is copied from the
   master or guessed from dates.
4. The day count is rendered in standard Traditional Chinese numerals. The
   implementation must not whitelist common products such as 4, 5, 6, 7, 8,
   or 12 days.
5. Currency uses an Arabic number with thousands separators and the approved
   visible style `新台幣 1,200 元`.
6. The complete generated clause for a 4-day trip is:

   ```text
   每人每天新台幣 300 元，四天共新台幣 1,200 元
   ```

7. Examples do not define an allowlist:

   | `day_count` | Chinese day text | Total | Generated dynamic clause |
   |---:|---|---:|---|
   | 1 | 一天 | 300 | `一天共新台幣 300 元` |
   | 4 | 四天 | 1,200 | `四天共新台幣 1,200 元` |
   | 10 | 十天 | 3,000 | `十天共新台幣 3,000 元` |
   | 12 | 十二天 | 3,600 | `十二天共新台幣 3,600 元` |
   | 21 | 二十一天 | 6,300 | `二十一天共新台幣 6,300 元` |

8. A non-positive or non-integer day count fails before a Word job is written.
   Existing `Product` and LIST plan validation remain the first line of
   defense; the formatter validates its own direct input as well.

## Considered approaches

### 1. Calibrated body-paragraph patch in the generated plan

Add one typed body-paragraph patch whose source identity and target text are
both explicit. The Word adapter locates exactly one main-story paragraph,
checks the complete source text, replaces only its visible range, and verifies
the result after SaveAs/reopen.

Advantages:

- derives every document from the existing canonical master;
- does not require private recalibration;
- detects missing, duplicated, or changed source text;
- preserves the paragraph mark and surrounding document structure;
- can be validated offline before another separately authorized Word run.

Cost: the plan, adapter, report, and tests need a new explicit contract.

### 2. Recalibrate a master containing placeholders

Change the private master to contain day-count and total placeholders, then
create a new calibration manifest.

Advantages: the editable location is visually explicit in the master.

Costs: it changes the private source of truth, requires a separate calibration
gate, and expands a one-paragraph defect into master lifecycle work.

### 3. Global text replacement

Search the document for `六天` and `1,800` and replace both strings.

Advantage: minimal code.

Rejected because it is not bound to one semantic paragraph, cannot distinguish
template drift from a valid target, and can modify unrelated text.

## Selected design

Approach 1 is selected.

### Pure formatter

Add one pure formatter in `word_list.py` that accepts `day_count` and returns
the complete approved service-fee paragraph text.

The formatter owns:

- the constant daily fee, NTD 300;
- Traditional Chinese integer formatting for positive trip lengths;
- `day_count * 300` calculation;
- thousands separators;
- the full static prefix and suffix of the service-fee notice.

It must not read the master, dates, web notices, OP fields, locale settings, or
environment variables. It must not silently fall back to Arabic day text.

The implementation may use a deterministic place-value algorithm rather than
a dependency. It must accept every positive integer accepted by `Product` and
must not introduce a new maximum trip length. The offline tests exhaustively
check 1 through 366 in addition to exact boundary examples; the algorithm,
rather than a duration lookup table, handles larger positive integers.

### Typed plan contract

Introduce a typed body paragraph patch, conceptually:

```text
BodyParagraphPatch
  field_id = "service_fee_notice"
  anchor_prefix = "2. 本行程不接受在台灣事先支付導遊司機的服務費"
  expected_source_text = complete calibrated source paragraph
  text = complete generated target paragraph
```

`ListPatchPlan` contains exactly one `body_paragraphs` entry with that field
ID. The plan becomes schema 4 and the generator becomes `list-word/4` so an old
adapter cannot silently accept the new semantics. The patch report also
becomes schema 4.

The Python plan builder validates:

- exactly one supported body patch exists;
- `field_id`, anchor, expected source, and target are non-empty strings;
- the target contains the formatted daily fee, Chinese day count, and computed
  total exactly once;
- the target has no Word paragraph, cell, or manual-line-break markers;
- the source and target are different;
- the body patch does not overlap header or table patch contracts.

### Word source locator

The PowerShell adapter searches only the main document story. It does not use a
document-wide replace and does not search headers, footers, or table cells.

It enumerates paragraph candidates by the approved stable anchor prefix, then
requires:

1. exactly one candidate;
2. the candidate's visible text, excluding the paragraph mark, exactly equals
   `expected_source_text`;
3. the candidate range is non-empty and ends before its paragraph mark;
4. the candidate is outside all Word tables.

Zero candidates, multiple candidates, source-text drift, an invalid range, or
a table-contained candidate fails closed before text mutation.

### Bounded replacement

The adapter duplicates the verified paragraph range, retreats exactly one Word
range position to exclude the paragraph mark, and assigns the generated full
text to that duplicate.

It does not delete or insert a paragraph, use `ReplaceAll`, rebuild the body,
or change the private master. Existing output-font handling subsequently
applies the 12-pt non-title contract to the generated notice.

The patch is applied after source inspection and before output presentation,
pagination, SaveAs, and PDF rendering. It is therefore included in final
pagination and visual QA.

### Post-save evidence

After SaveAs and reopening the generated DOCX, the adapter repeats the bounded
lookup and requires:

- the generated target paragraph exists exactly once;
- the original fixed source paragraph does not survive;
- the paragraph remains outside tables;
- the paragraph mark is intact;
- the main-story paragraph count has not changed;
- the paragraph's visible characters satisfy the 12-pt non-title policy.

The patch report records `patched_body_paragraph_count = 1`. Python requires
that exact value when reading the report. The report schema is incremented with
the plan schema.

### PDF artifact authority

`LocalRenderBackend.render_word()` adds the complete generated service-fee
paragraph, or an exact stable calculated clause from it, to `required_text`
before calling `render_list_word_for_qa()`.

PyMuPDF must therefore find the calculated 4-day/NTD 1,200 text in the actual
exported PDF. A correct DOCX report without matching exported text still
fails. The existing PDF page count, A4, no-image, day-page-map, PNG set, and QA
index contracts remain unchanged.

## Error contract

New failures use safe codes without document text, paths, or COM object dumps:

- `LIST_SERVICE_FEE_PLAN_INVALID`
- `LIST_SERVICE_FEE_SOURCE_PARAGRAPH_MISSING`
- `LIST_SERVICE_FEE_SOURCE_PARAGRAPH_MULTIPLE`
- `LIST_SERVICE_FEE_SOURCE_PARAGRAPH_CHANGED`
- `LIST_SERVICE_FEE_RANGE_INVALID`
- `LIST_SERVICE_FEE_SOURCE_IN_TABLE`
- `LIST_SERVICE_FEE_POST_REOPEN_MISSING`
- `LIST_SERVICE_FEE_POST_REOPEN_MULTIPLE`
- `LIST_SERVICE_FEE_POST_REOPEN_CHANGED`
- `LIST_SERVICE_FEE_PARAGRAPH_COUNT_CHANGED`

The existing Word adapter wrapper may continue reporting its outer
`WORD_GENERATION_FAILED` envelope, but the inner safe code must identify the
first failing boundary. An unknown or timed-out Word result retains the
existing no-retry rule.

## Compatibility and unchanged behavior

The following remain unchanged:

- private master and calibration manifest bytes;
- master SHA-256 and normalized-structure checks;
- header paragraphs and title font preservation;
- QR removal and full-width first-page layout;
- 12-pt non-title policy;
- table shapes, merged cells, daily-row resizing, complete route titles, first
  supplier hotel, and O/X meal rules;
- missing OP field behavior and yellow highlights;
- Word ownership, timeout, exclusive output, SaveAs/reopen, pagination, PDF,
  PNG, and QA-index behavior;
- source access and all external approval gates.

No web notice or OP field can override the NTD 300/day rule under this design.
A future change to the fee is a business-rule change requiring a new approved
design; it is not inferred from source prose.

## Offline test design

Implementation remains test-first and does not start Word.

### Formatter and plan tests

Add cases for 1, 4, 5, 6, 7, 8, 10, 11, 12, 20, and 21 days. Require exact
Chinese day text, calculated total, thousands separators, full target
paragraph, one body patch, and no forbidden Word markers.

Add direct invalid-input tests for booleans, zero, and negative values. They
must fail before a job file or output is created. Run a deterministic loop for
every day count from 1 through 366 and require a non-empty Chinese day string,
the exact arithmetic total, and no duration allowlist behavior.

Existing arbitrary-day table-row tests remain and gain assertions that each
plan includes the matching service-fee target. There is no common-duration
allowlist.

### Adapter source-contract tests

Use the existing PowerShell source-contract test style to require:

- main-story-only paragraph enumeration;
- exact one-candidate checks;
- exact source-text comparison;
- explicit outside-table check;
- one-position paragraph-mark retreat;
- no `ReplaceAll` or document-wide wildcard replacement;
- pre-save replacement and post-reopen assertion;
- safe, boundary-specific error codes;
- unchanged header/cell setters and pagination ordering.

Run the PowerShell parser after the edit. These tests are structural controls;
they do not replace the later real Word integration gate.

### Report and workflow tests

Update synthetic adapter reports to the new schema and require
`patched_body_paragraph_count = 1`.

Backend composition tests require the calculated service-fee text in PDF
`required_text`. Negative tests prove a PDF containing the old 6-day sentence
but not the calculated target is rejected.

### Regression and non-change proof

Run:

- focused formatter, plan, PowerShell adapter, backend, and PDF QA tests;
- existing Word LIST and arbitrary-day pagination controls;
- complete offline test suite;
- Python compile checks;
- PowerShell parser checks;
- `git diff --check` and a baseline changed-file audit;
- WINWORD process-count checks proving offline implementation did not start
  Word.

Tests must not be weakened, skipped, or deleted to obtain green results.

## Future implementation boundary

An approved implementation plan may modify only the smallest coherent set:

- `src/travel_briefing/word_list.py`;
- `scripts/briefing/patch_list_template.ps1`;
- `src/travel_briefing/workflow.py`;
- directly relevant unit and integration contract tests;
- version/package metadata only if the plan proves it is required by the
  generator/schema increment;
- `STATUS.md` and the implementation plan/handoff documents.

It must not modify the private master, calibration manifest, unrelated parser,
narration, JMA, Cowell, LINE, deployment, or publication code.

Offline implementation approval will not authorize Word. After all offline
tests pass, any real Word verification needs a new exact one-run approval. A
failed or successful authorized selector is not retried under the same grant.

## Acceptance criteria

The future implementation is complete only when offline evidence proves:

1. `day_count` is the only day authority and NTD 300 is the only fee-rate
   authority.
2. Chinese day text and totals are correct for all approved boundary examples
   without a common-duration whitelist.
3. The plan contains exactly one typed service-fee body patch.
4. The adapter edits only one exact, outside-table main-story paragraph and
   preserves its paragraph mark.
5. Missing, duplicate, changed, in-table, invalid-range, and post-reopen
   mismatches fail with safe codes.
6. The generated DOCX report proves one body paragraph was patched.
7. PDF QA requires the calculated service-fee text.
8. Existing QR, 12-pt, no-extra-paragraph, arbitrary-day pagination, content,
   master-integrity, and no-retry contracts remain green.
9. The complete offline suite, compile, parser, diff, and WINWORD non-use gates
   pass with original outputs recorded.
10. No private or external integration is used during implementation.

A future Word run must additionally prove that the same DOCX/PDF/PNG set
contains the correct calculated notice and has no visual regression. Offline
green results alone cannot make that claim.

## Review gate

This written specification must be reviewed before an implementation plan is
created. Approval of this document authorizes planning only, not production or
test edits and not Word.

The exact next authorization is:

```text
同意此書面規格，開始建立離線實作計畫
```
