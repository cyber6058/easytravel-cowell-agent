# LIST PDF QA failure evidence and missing-token diagnostics design

## Status

The OP selected approach A and approved the design in conversation on
2026-08-19. This written specification is awaiting review. No implementation
has started.

## Authorized scope

This turn may inspect the retained one-shot failure evidence, repository source,
tests, and documentation. It may write this specification and `STATUS.md`, then
create a local documentation commit.

It does not authorize production or test edits, Word COM, a new DOCX/PDF/PNG,
private master or calibration access, NewAmazing or JMA GET, Yating, ffmpeg,
LINE, Cowell, deploy, publish, push, or another integration run.

## Observed failure

The single authorized 4-day selector ran exactly once:

```text
test_calibrated_master_renders_gate_v_day_counts[4]
ValueError: LIST QA PDF is missing required text
1 failed in 42.37s
```

The run was not retried. Word exited and the private master and calibration
hashes remained unchanged.

The output retained only `day-004/LIST.docx`. Read-only DOCX inspection found
the product code, both flight numbers, and the complete dynamic 4-day service
fee paragraph, including `四天共新台幣 1,200 元`. The temporary PDF was removed
when `render_list_word_for_qa()` left its `TemporaryDirectory`, so the evidence
cannot identify which required token was missing from the exported PDF.

The current PDF inspection uses an aggregate condition:

```python
if any(value not in whole_text for value in required_text):
    raise ValueError("LIST QA PDF is missing required text")
```

It neither records the missing values nor publishes the failed PDF.

## Offline feedback loop

A deterministic no-Word harness created a synthetic A4 PDF containing the
product code and one flight number while omitting `JX821` and
`SERVICE-FEE-TOKEN`. The harness ran three times and produced the same opaque
message every time:

```text
ATTEMPT_1=LIST QA PDF is missing required text
ATTEMPT_2=LIST QA PDF is missing required text
ATTEMPT_3=LIST QA PDF is missing required text
AssertionError: RED: missing token identities are not exposed
```

This loop reproduces the diagnostic defect, not the deleted real PDF. It is
fast, deterministic, agent-runnable, and does not start Word. The future unit
test will replace this throwaway harness.

## Goals

1. Identify every missing `required_text` value in deterministic input order.
2. Preserve a valid Word-exported PDF when deterministic PDF inspection fails.
3. Keep failed evidence separate from successful PDF, PNG, and QA-index names.
4. Prevent overwriting or mixing evidence from different attempts.
5. Preserve the existing success path and every Word no-retry boundary.
6. Make the behavior fully testable with the synthetic render adapter.

## Non-goals

This design does not:

- determine the missing token from the already deleted 4-day PDF;
- change the content, layout, QR, font, paragraph, pagination, or service-fee
  contracts;
- change Word ownership, timeout, SaveAs, render-report, or unknown-result
  handling;
- preserve a PDF from an unknown Word result or an invalid render report;
- treat a pdftoppm or PNG-publication failure as a PDF-inspection failure;
- add retry, overwrite, cleanup of prior runs, or automatic recovery;
- change private calibration, workflow inputs, or external integrations.

## Considered approaches

### A. Dedicated failed-QA directory with PDF and structured report

On deterministic PDF-inspection failure, publish the failed PDF and a
hash-bound JSON report below `failed-qa/`. Keep all normal QA output names
absent.

Advantages:

- preserves the artifact needed for exact offline diagnosis;
- makes failure status unambiguous;
- provides machine-readable missing-token evidence;
- prevents a failed PDF from being mistaken for a successful QA artifact.

Cost: adds one failure-artifact schema and exclusive publication path.

### B. Failed PDF beside the normal output without a report

Publish only `LIST-qa.failed.pdf` next to the requested PDF and place token
details in the exception.

Advantage: fewer files.

Rejected because a later process cannot verify the reason, hash, or completion
state without reconstructing it from transient console output.

### C. Richer exception without PDF preservation

Return the missing tokens but continue deleting the temporary PDF.

Advantage: smallest code change.

Rejected because the next diagnosis would still lack the exported artifact
needed to distinguish content loss, line wrapping, glyph substitution, and
text-extraction behavior.

## Selected design

Approach A is selected.

### Output paths and success/failure separation

For an existing requested success path such as:

```text
day-004/LIST-qa.pdf
```

the deterministic PDF-inspection failure destinations are exactly:

```text
day-004/failed-qa/LIST-qa.failed.pdf
day-004/failed-qa/failure.json
```

The normal `LIST-qa.pdf`, `pages/page-*.png`, and `pages/index.json` remain
absent on this failure path. A successful run publishes the existing normal
artifacts and does not create `failed-qa`.

The entire `failed-qa` directory is an exclusive one-attempt marker. If it
already exists before the render adapter is called, the operation fails closed
before Word starts. It is never merged, reused, overwritten, or automatically
deleted. A new attempt therefore requires a new output root and separate
authorization rather than reusing failed evidence.

### Eligible failure boundary

Failure evidence is published only after all of the following are true:

1. the render adapter returned a known result;
2. the render report passed its existing schema checks;
3. the temporary PDF exists and is non-empty;
4. the PDF byte count matches the render report;
5. `inspect_list_pdf()` rejected that PDF with a deterministic inspection
   `ValueError`.

Unknown Word results, missing or empty PDFs, invalid render reports, and byte
count mismatches retain their existing handling and do not publish a
`failed-qa` directory. Later pdftoppm, PNG, index, or success-publication errors
also remain outside this design.

### Missing-token calculation

`inspect_list_pdf()` calculates missing required values before raising:

```text
missing_required_text = every required_text value absent from whole_text
```

The list preserves the first-occurrence order supplied by the caller and
contains each missing value once. It does not include matched tokens or the
complete extracted PDF text.

The missing-text branch raises an internal typed `ValueError` carrying the
tuple. Other existing deterministic inspection failures continue to use their
current messages.

The outer render function catches deterministic inspection `ValueError`s. It
uses the safe inner code `LIST_PDF_REQUIRED_TEXT_MISSING` when the typed tuple
is available; all other inspection failures use
`LIST_PDF_INSPECTION_FAILED` with an empty missing-token list.

### Failure report schema

`failure.json` has schema version 1 and exactly this shape:

```json
{
  "schema_version": 1,
  "status": "failed",
  "stage": "pdf-inspection",
  "error_code": "LIST_PDF_REQUIRED_TEXT_MISSING",
  "message": "LIST QA PDF is missing required text",
  "missing_required_text": ["JX821", "SERVICE-FEE-TOKEN"],
  "pdf": {
    "relative_path": "LIST-qa.failed.pdf",
    "bytes": 12345,
    "sha256": "64 lowercase hexadecimal characters"
  }
}
```

Every key is required. Unknown or invalid keys fail strict test fixtures. The
report contains no absolute path, complete PDF text, Word COM object dump,
environment value, private master path, or calibration path.

For a non-token inspection failure, `error_code` is
`LIST_PDF_INSPECTION_FAILED` and `missing_required_text` is an empty list. The
safe existing inspection message is retained in `message`.

### Exclusive publication and rollback

Failure evidence uses the existing exclusive-copy style:

1. create the previously absent `failed-qa` directory;
2. exclusively copy the temporary PDF to `LIST-qa.failed.pdf`;
3. verify the copied file's byte count and SHA-256;
4. exclusively write `failure.json` last as the completion marker.

If any publication or verification step fails, remove only files and the
directory created by that same helper, then raise. Because preflight requires
the directory to be absent, rollback cannot delete user-owned prior evidence.
Normal success artifacts remain absent throughout the failed publication.

### Error envelope

After successful failure-evidence publication,
`render_list_word_for_qa()` raises the existing `WordGenerationError` envelope
with outer code `WORD_GENERATION_FAILED`. Its details contain exactly:

```text
stage = "pdf-inspection"
error_code = safe inner code
missing_required_text = ordered list
failed_pdf = "failed-qa/LIST-qa.failed.pdf"
failure_report = "failed-qa/failure.json"
```

The original inspection exception remains the chained cause. This keeps the
CLI and integration test inside the existing `BriefingCliError` contract while
making the failure actionable. It does not add a retry or convert failure
evidence into success evidence.

## Compatibility and version boundaries

The future implementation is confined to failure diagnostics in
`word_qa.py`. The following remain unchanged:

- `LocalRenderBackend.render_word()` inputs and `required_text` construction;
- LIST generator `list-word/4` and plan/report schema 4;
- Word render-job and render-report schema 1;
- calibration schema 2 and `list-calibration/2`;
- persisted `WordRenderEvidence` schema 3;
- successful QA index schema 2;
- successful PDF/PNG publication and hashes;
- arbitrary positive trip lengths and content-driven pagination;
- QR removal, full-width identity block, 12-pt non-title text, and no-extra-
  paragraph contracts;
- private master and calibration hashes;
- all external approval gates and no-retry rules.

The only new versioned artifact is failure-report schema 1. No package,
workflow, generator, plan, or successful QA-index version increment is
required by this design.

## Offline test design

Implementation is test-first and must not start Word.

### Missing-token primary red

Replace the throwaway harness with a unit test that creates a synthetic A4 PDF
containing some required values and omitting at least two. Require the raised
typed value to expose exactly the missing values once and in caller order. The
current aggregate exception must make this test red before implementation.

### Failure publication primary red

Use `SyntheticRenderAdapter` to produce a valid PDF that omits required text.
Require:

- the adapter is called exactly once;
- `failed-qa/LIST-qa.failed.pdf` exists and is non-empty;
- `failure.json` has the exact schema-1 keys and ordered missing values;
- recorded byte count and SHA-256 match the retained PDF;
- the raised outer error is `WORD_GENERATION_FAILED` with the exact safe
  details;
- normal PDF, PNG, and QA index paths do not exist;
- temporary job files are removed by the existing lifecycle.

### General inspection failure

Produce a deterministic non-token PDF inspection failure and require the same
failed PDF/report publication with `LIST_PDF_INSPECTION_FAILED` and an empty
missing-token list.

### Collision and no-Word preflight

Pre-create `failed-qa` and require the function to fail before the synthetic
adapter records a job. Existing normal-output collision tests remain green.

### Success and rollback controls

Require a successful synthetic render to publish the current normal PDF, PNG
set, and index without creating `failed-qa`.

Inject one failure during failed-evidence publication and require rollback of
only newly created failure paths, no normal outputs, and no deletion outside
the fresh directory.

### Complete offline verification

Run:

- the new focused tests in `test_word_qa.py`;
- existing `test_word_qa.py` and `test_local_backend.py` controls;
- Word LIST workflow and integration-collection controls without setting the
  Word opt-in;
- the complete offline pytest suite;
- Python compile checks;
- `git diff --check` and a changed-file audit;
- WINWORD process counts before and after all tests.

Tests must not be weakened, skipped, or deleted to obtain green results.

## Future implementation boundary

An approved implementation plan may modify only:

- `src/travel_briefing/word_qa.py`;
- `tests/unit/travel_briefing/test_word_qa.py`;
- the implementation plan and `STATUS.md`.

If implementation proves that `workflow.py`, `errors.py`, public schemas,
successful artifact formats, the private master, or calibration must change,
stop and return to design review rather than expanding scope silently.

Offline implementation approval will not authorize Word. After all offline
tests pass, any real Word verification requires a new exact one-run approval.
A successful or failed selector is not retried under the same grant.

## Acceptance criteria

The future offline implementation is complete only when evidence proves:

1. missing required tokens are reported exactly once and in deterministic
   caller order;
2. a valid Word-exported PDF rejected by deterministic inspection is retained
   under the exact `failed-qa` paths;
3. `failure.json` strictly matches schema 1 and its hash and byte count bind it
   to the retained PDF;
4. token and non-token inspection failures use the correct safe inner codes;
5. the outer error remains `WORD_GENERATION_FAILED` with relative diagnostic
   paths and no private path or full extracted text;
6. normal PDF, PNG, and index artifacts remain absent on failure;
7. a pre-existing `failed-qa` directory blocks before any Word adapter call;
8. failure-publication rollback touches only newly created failure paths;
9. the successful QA path creates no failure directory and remains byte- and
   schema-compatible;
10. focused, unchanged-control, complete offline, compile, diff, and WINWORD
    non-use gates pass with original outputs recorded.

Offline green results do not prove the deleted 4-day PDF's missing token and do
not prove the real Word path fixed. Only a separately authorized future Word
run can create that evidence.

## Review gate

This written specification must be reviewed before an implementation plan is
created. Approval of this document authorizes planning only, not production or
test edits and not Word.

The exact next authorization is:

```text
同意此書面規格，開始建立離線實作計畫
```
