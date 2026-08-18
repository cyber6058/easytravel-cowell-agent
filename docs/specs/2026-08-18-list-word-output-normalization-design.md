# LIST Word output normalization design

## Status

Selected design for review. The OP selected output-time normalization and
confirmed all three presentation rules. This specification contains no live
URL, product identifier, private template content, OP values, or generated
artifact.

## Problem and evidence

The current Word generator copies the calibrated LIST master, fills the copy,
then preserves the master's upper-right QR code and several inherited font
sizes. It also assigns every ordinary cell as `text + CR + cell marker`.
Read-only OOXML inspection of an existing generated draft showed that nearly
every filled ordinary cell contains an additional empty trailing paragraph.

The requested output contract is:

1. remove the upper-right QR code and its text wrapping from every generated
   Word document;
2. use 12 pt for every visible character except the first-line title
   `日本精緻假期`, whose calibrated master size remains unchanged; and
3. remove the generated empty trailing paragraph after filled cell values,
   while preserving automatic wrapping and intentional line breaks inside long
   content.

The canonical private master must remain unchanged. The previous two blocked
drafts are evidence that the common Word QA path needs fresh verification, but
this design does not assume that the presentation changes will fix that blocker.

## Scope

This change covers only the LIST Word output generator and its deterministic
Word/PDF QA contracts:

- output-copy QR removal;
- fixed output font size with one exact title exception;
- ordinary-cell text replacement without an extra trailing paragraph;
- pagination after those changes;
- Word evidence, PDF inspection, packaging documentation, and tests that encode
  the new output contract.

It does not modify or recalibrate the private master, change source parsing,
merge facts, narration, Yating, JMA, OP values, confirmation rules unrelated to
Word, ffmpeg, LINE, upload, publication, deployment, push, or Cowell. It does
not authorize a formal URL GET or a private-master Word integration run.

## Selected architecture

Use output-time normalization inside the owned Word patch operation:

1. validate the read-only source master with the existing calibration hashes,
   structure fingerprint, table anchors, and required QR candidate;
2. copy the master to a new exclusive working document;
3. resize daily rows and fill header/cell content;
4. remove only QR candidates anchored inside the calibrated top header cell;
5. normalize cell paragraphs and document fonts;
6. apply pagination guards and calculate pages using the final presentation;
7. save, reopen, inspect, and render that same artifact for QA.

No post-save OOXML mutation is permitted. The document used for Word page
counts, day-page mapping, PDF export, PNG review, and delivery must be the same
normalized artifact.

## Master and QR contract

The private master remains the visual and structural source of truth. Source
inspection continues to require the square graphic candidate count anchored
inside the top merged header cell to equal the count recorded by calibration.
A missing or extra source QR means the master or calibration drifted and must
fail closed.

After source validation, the patch operation deletes every detected square QR
candidate in that header cell, including its floating or inline shape object and
therefore its text-wrapping effect. It must not delete shapes elsewhere in the
document. Output inspection requires exactly zero header QR candidates.

The removal intentionally leaves no reserved blank area. Word repaginates after
deletion, so the group code and group name may use the full merged-cell width.
The Word generator version changes from `list-word/2` to `list-word/3`, and the
patch-plan/report schema changes to version 3. The private calibration manifest
remains at its existing schema and is not rewritten. The report policy changes
from `first_page_only` to `removed`; an old runtime must not accept the new
incompatible plan or report as the old output contract.

PDF QA must no longer require a first-page image. The QR is the only image
expected in the current calibrated LIST master, so the final output PDF must
contain exactly zero images. Word evidence records the zero count and fails if
a QR candidate or image survives.

## Font contract

After all content and continuation headers have been created, set every visible
text range in the generated document to exactly 12 pt. This includes:

- fixed labels and table headers;
- group code, group name, departure, meeting, flight, itinerary, hotel, meal,
  guide, and yellow review values;
- every normal and continuation page; and
- continuation-page identity/header text.

The sole exception is the visible text of header-cell paragraph 1. It must still
equal `日本精緻假期` and retain its calibrated master font size. Paragraph marks
and cell markers are not visible text and are not part of the exception.

Existing adaptive daily layout profiles may retain safe line spacing, margins,
and paragraph-spacing values, but may not set any body text below or above 12
pt. The generator must not shrink daily rows to 10 or 9 pt to force a single
page. Longer content continues naturally to additional pages with repeated
identity and daily headers.

## Cell paragraph contract

`Set-ListCell` must replace the ordinary cell's complete content range while
excluding the terminal Word cell marker. It writes only the requested text and
does not append CR, BEL, another paragraph mark, or another cell marker.

After replacement, each ordinary patched cell must contain Word's single
required cell paragraph and no additional empty trailing paragraph. An
intentionally empty value may use that one required empty paragraph; a filled
value must not be followed by a second empty paragraph.

This normalization does not flatten content wrapping. Word may wrap long text
automatically. The group-name header may keep the existing manual line break
inside its single paragraph when the title-splitting contract requires it.
Merged cells, table geometry, borders, alignment, highlighting, and cell markers
remain unchanged.

## Validation and error handling

Keep source and output validation separate so the canonical contract is not
weakened:

- source master: calibrated hashes/fingerprint and anchors match, and the header
  QR candidate count equals the count recorded by calibration;
- output DOCX: table/anchor/section/A4 contracts match, header QR count is zero,
  all visible non-title text is 12 pt, the title size is unchanged, and patched
  cells have no extra trailing paragraph;
- output PDF: required text, page geometry, page count, continuation identity,
  repeated daily headers, and day-page map match; no preserved-QR image is
  required or accepted; and
- output PNGs: every page still requires human visual review for clipping,
  overlap, table borders, merged cells, freed header width, yellow fields, and
  continuation layout.

Any ambiguous shape, surviving QR, missing title, mixed non-title font size,
extra cell paragraph, Word error, PDF mismatch, or page-map mismatch blocks the
Word artifact. Do not silently retain the old QR/font/paragraph behavior and do
not retry an unknown Word result.

## Data flow

1. Load and validate the unchanged calibrated master.
2. Create an exclusive working copy.
3. Apply source-bound text and yellow placeholders.
4. Remove the header QR and release its wrapping area.
5. Normalize ordinary cells to one required paragraph.
6. Apply 12 pt globally except the fixed first-line title.
7. Repaginate, save, reopen, and compute page/day evidence.
8. Export the same DOCX to PDF and all-page PNG QA.
9. Mark Word completed only when structural and visual gates pass.

## Test contract

Use TDD and de-identified synthetic drafts before any private Word run:

- patch-plan/report contracts encode QR removal and reject old incompatible
  policy values;
- PowerShell adapter tests prove QR deletion is restricted to candidates inside
  the top header cell and that output inspection requires zero candidates;
- `Set-ListCell` no longer appends CR/BEL and preserves exactly one required
  paragraph for filled and empty ordinary cells;
- automatic wrapping and the existing group-name manual line break remain
  allowed;
- all fixed labels, values, yellow placeholders, daily rows, and continuation
  headers are 12 pt, while `日本精緻假期` retains its original size;
- adaptive profiles cannot reduce or increase visible body text away from 12
  pt;
- PDF QA accepts the intentional absence of the QR image while retaining every
  text, geometry, continuation, and day-page check;
- workflow evidence requires the new Word contract and still fails closed on
  missing PDF/PNG evidence; and
- packaging copies the updated runtime scripts and user-facing QR guidance.

Run focused Word plan/adapter/QA/workflow tests, then the complete offline suite,
compileall, package validation, and `git diff --check`. A later private-master
Word integration requires a separate current approval and must cover at least
4, 5, 6, 7, 8, and 12 day synthetic cases. Inspect every produced PNG; do not
claim the Word blocker is fixed until that integration actually passes.

## Acceptance criteria

The change is acceptable only when all of the following are verified:

- the canonical master and calibration files are byte-for-byte unchanged;
- generated DOCX/PDF output contains no header QR or reserved QR wrapping area;
- every visible character except `日本精緻假期` is exactly 12 pt;
- ordinary filled cells have no blank line after their value;
- automatic/intentional wrapping still works without clipping;
- arbitrary positive trip lengths remain supported with safe continuation
  pages; and
- Word, PDF, and all-page PNG evidence describes the same final artifact.
