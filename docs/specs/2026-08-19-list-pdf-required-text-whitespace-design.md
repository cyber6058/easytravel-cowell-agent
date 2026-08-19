# LIST PDF required-text layout-whitespace normalization design

## Status

The OP approved the recommended design in conversation on 2026-08-19. This
written specification is awaiting review. No implementation has started.

## Authorized scope

This turn may inspect repository source, tests, the retained 4-day failure
evidence, and project documentation. It may write this specification and
`STATUS.md`, then create a local documentation commit.

It does not authorize production or test edits, Word COM, another integration
run, a new DOCX/PDF/PNG, private master or calibration changes, NewAmazing or
JMA GET, Yating, ffmpeg, LINE, Cowell, deploy, publish, or push.

## Observed defect

The single authorized 4-day Word selector ran exactly once:

```text
test_calibrated_master_renders_gate_v_day_counts[4]
LIST_PDF_REQUIRED_TEXT_MISSING
1 failed in 32.29s
```

The run was not retried. It preserved these same-run artifacts:

- `day-004/LIST.docx`;
- `day-004/failed-qa/LIST-qa.failed.pdf`;
- `day-004/failed-qa/failure.json`.

The failure report identified the complete dynamic 4-day service-fee paragraph
as the sole missing `required_text` value. Read-only inspection proved:

1. the exact contiguous target exists in the generated DOCX;
2. the PDF is a valid one-page A4 portrait document with no images;
3. the PDF text contains the same non-whitespace characters in the same order;
4. Word inserted a layout line break between `每人每天` and `新台幣`;
5. the raw target is absent, but the target matches after whitespace removal.

The relevant extracted PDF text is:

```text
每人每天
新台幣 300 元，四天共新台幣 1,200 元
```

The current aggregate check uses raw substring comparison:

```python
whole_text = "\n".join(page_texts)
missing_required_text = tuple(
    dict.fromkeys(
        value for value in required_text if value not in whole_text
    )
)
```

This makes a valid Word layout wrap indistinguishable from missing content.
The failure-evidence feature behaved correctly: normal PDF, PNG, and QA index
were not published after inspection failed.

## Goals

1. Treat PDF layout whitespace as irrelevant only for aggregate
   `required_text` presence checks.
2. Continue requiring the complete non-whitespace character sequence in the
   original order.
3. Preserve original required tokens in missing-token diagnostics and failed
   evidence.
4. Preserve every page-specific, structural, visual, publication, and
   no-retry contract.
5. Make the correction completely testable offline without Word.

## Non-goals

This design does not:

- change generated LIST content or the private master;
- alter spaces, line breaks, fonts, tables, pagination, or PDF bytes;
- normalize punctuation, case, Unicode width, accents, digits, or symbols;
- use Unicode compatibility normalization such as NFKC;
- ignore missing or reordered non-whitespace characters;
- relax continuation-page identity/header checks;
- relax day-token occurrence or day-page mapping checks;
- change A4 geometry, image-count, page-count, PNG, or QA-index rules;
- change failure-report schemas, error codes, or successful artifact names;
- add retry, fallback, overwrite, or automatic recovery;
- authorize another Word run or any external integration.

## Considered approaches

### 1. Canonical whitespace-free comparison for aggregate required text

Create comparison-only copies of the PDF text and each required token by
removing every character Python treats as whitespace. Use those copies for
presence checks while retaining all original values for evidence.

Advantages:

- directly matches the observed Word/PyMuPDF behavior;
- handles line breaks, spaces, tabs, and other layout whitespace consistently;
- preserves every non-whitespace character and its order;
- requires one small private helper and one focused decision point;
- is easy to prove with deterministic unit tests.

Trade-off: differences made only of whitespace are intentionally outside this
aggregate content check. Visual rendering QA remains responsible for layout.

### 2. Remove line-break characters only

Strip `\r` and `\n` before comparison.

Advantage: narrower tolerance.

Rejected because PDF extraction may represent equivalent layout separation as
spaces, tabs, or other Unicode whitespace. It would fix the retained artifact
but leave the same class of false negative unresolved.

### 3. Build a whitespace-tolerant regular expression per token

Escape each non-whitespace character and allow arbitrary whitespace between
them.

Advantage: the tolerance is explicit in the pattern.

Rejected because it implements the same semantics with more code, more
escaping risk, and less readable failure analysis.

## Selected design

Approach 1 is selected.

### Private comparison helper

Add one private helper in `word_qa.py`, conceptually:

```text
compact_layout_whitespace(value) = concatenate(value.split())
```

The helper uses Python's standard Unicode whitespace classification through
`str.split()` with no separator. It does not perform case folding, punctuation
removal, Unicode normalization, transliteration, or character replacement.

Examples:

| Input | Comparison value |
|---|---|
| `每人每天\n新台幣 300 元` | `每人每天新台幣300元` |
| `JX820` | `JX820` |
| `JX 820` | `JX820` |
| `ＪＸ820` | `ＪＸ820` |

The third example is intentionally equivalent for this aggregate presence
check. The fourth remains different because full-width characters are not
whitespace.

### Input validation

`required_text` remains a non-empty tuple of non-empty strings. In addition,
each value must contain at least one non-whitespace character after comparison
normalization.

A whitespace-only token fails before opening or inspecting the PDF with the
existing safe input-validation message:

```text
LIST PDF QA requires non-empty expected text
```

This prevents an empty normalized token from matching every document.

### Aggregate matching data flow

After all existing per-page A4, readable-text, and no-image checks pass:

1. join `page_texts` using the existing whole-document order;
2. derive one whitespace-free comparison copy of `whole_text`;
3. derive a whitespace-free comparison copy of each `required_text` value;
4. test each compact token against compact whole-document text;
5. collect genuinely missing original tokens in caller order;
6. deduplicate by the original token value exactly as today;
7. raise `_ListPdfRequiredTextError` only when that ordered tuple is non-empty.

The matching result is comparison-only. No normalized text is written to the
PDF, DOCX, JSON report, exception message, log, or QA index.

### Diagnostic behavior

When a token is genuinely missing, `missing_required_text` continues to
contain the original caller-supplied string, not its compact form. Existing
ordered-unique behavior remains unchanged.

For example, a target containing `新台幣` must still fail if the PDF contains
only `新台 300 元`. Removing a non-whitespace character, changing punctuation,
or changing character order cannot pass normalization.

The existing outer and inner failure contracts remain:

```text
WORD_GENERATION_FAILED
LIST_PDF_REQUIRED_TEXT_MISSING
```

The schema-1 failed-QA report and hash-bound PDF evidence remain unchanged.

### Strict checks that remain raw

Whitespace normalization must not be reused by these checks:

- `continuation_required_text` identity and daily headers on each continuation
  page;
- `day_tokens` regular-expression occurrence counts;
- `day_page_map` page placement;
- A4 portrait geometry;
- minimum per-page non-whitespace text count;
- zero-image policy;
- explicit expected page count;
- PNG page-set and schema-2 QA-index publication.

These checks have page-local or structural meaning. Applying aggregate
normalization to them would expand the fix beyond the observed defect.

## Compatibility and unchanged interfaces

No public function signature, dataclass, schema, error code, adapter contract,
or workflow input changes.

The following files remain unchanged during future implementation unless a new
design is approved:

- `src/travel_briefing/workflow.py`;
- `src/travel_briefing/word_list.py`;
- both PowerShell Word adapters;
- integration selector definitions;
- private master and calibration manifest;
- package and generator versions.

Existing successful callers receive the same `ListPdfInspection` values and
artifact paths.

## Offline test design

Implementation is test-first and does not start Word.

### Primary regression

Create a deterministic synthetic A4 PDF whose extracted text includes the
observed boundary:

```text
每人每天
新台幣 300 元，四天共新台幣 1,200 元
```

Pass the contiguous service-fee text as `required_text`. Before production
changes, the test must fail with `_ListPdfRequiredTextError`; after the minimal
change, it must return a valid inspection.

### Fail-closed controls

Add focused tests proving:

1. deleting one non-whitespace Chinese character still reports the original
   complete token as missing;
2. changing punctuation still reports the token as missing;
3. a whitespace-only required token is rejected as invalid input;
4. missing-token order and exact-original-value deduplication remain intact;
5. continuation identity/header checks do not gain whitespace tolerance;
6. day-token and day-page mapping checks remain unchanged.

### Existing regression controls

Run the existing PDF inspection, missing-token, failed-evidence, generic
inspection failure, collision, rollback, successful publication, page-count,
and workflow composition tests unchanged.

Then run:

- the complete offline test suite;
- Python compile checks;
- `git diff --check`;
- a changed-file audit against the implementation baseline;
- WINWORD process-count and opt-in checks proving Word was not started.

Tests must not be weakened, skipped, or deleted to obtain green results.

## Future implementation boundary

An approved implementation plan may modify only:

- `src/travel_briefing/word_qa.py`;
- `tests/unit/travel_briefing/test_word_qa.py`;
- the implementation plan and `STATUS.md` handoff documentation.

If implementation requires changing workflow composition, adapters, schemas,
the integration selector, master, or calibration, work stops for a new design
decision.

Offline implementation approval will not authorize Word. After all offline
tests pass, a real 4-day Word verification still requires a new exact one-shot
approval. Success or failure under that grant is not retried.

## Acceptance criteria

The future implementation is complete only when offline evidence proves:

1. the observed newline-wrapped service-fee text matches its contiguous
   required token;
2. spaces, tabs, and line breaks are ignored only by aggregate
   `required_text` presence checks;
3. all non-whitespace characters and their order remain exact;
4. whitespace-only expected values fail before PDF inspection;
5. genuine missing tokens retain their original values, input order, and
   deduplication behavior;
6. continuation, day-token, day-page, A4, image, page-count, PNG, and QA-index
   contracts remain strict and green;
7. failure evidence and error schemas remain byte-for-byte compatible in
   structure;
8. only the two authorized implementation files change;
9. the focused and complete offline suites, compile, diff, and WINWORD
   non-use gates pass with actual outputs recorded;
10. no private or external integration is used during implementation.

Offline green results alone do not prove that a future Word artifact is valid.
That claim requires a separately authorized real Word run and same-run visual
QA.

## Review gate

This written specification must be reviewed before an implementation plan is
created. Approval of this document authorizes planning only, not production or
test edits and not Word.

The exact next authorization is:

```text
同意此書面規格，開始建立離線實作計畫
```
