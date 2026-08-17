# NewAmazing time-only flight DRAFT design

## Status

Selected design for review. This document contains only synthetic contract
details and no live URL, product identifier, source value, or retained response.

## Problem and evidence

A current NewAmazing live-card omits `.departure_date`. Its duration remains a
positive day count, but every departure and arrival field in the flight table is
time-only `HH:MM`; none contains a date. The existing fallback therefore cannot
obtain a source-bound departure date from the first flight.

The parser must not derive a date from the product code, retrieval time, price,
free-form text, or another unapproved source. The requested behavior is to
produce a reviewable URL-only DRAFT while preserving every unknown date as an
explicit yellow review item. Such a DRAFT must not be confirmable.

## Scope

This change covers only:

- NewAmazing live-card flight values that are uniformly full datetime or
  uniformly time-only;
- propagation of genuinely missing web dates through merge and review;
- safe narration input when the departure date is unknown; and
- the local CONFIRMED guard for unresolved source dates.

It does not add a manual OP date field, infer dates, change PDF parsing, fetch a
different source, run live JMA, calibrate LIST, install dependencies, confirm,
send, upload, publish, deploy, push, or access Cowell. Resolving the date later
requires a new DRAFT from an approved source such as a local itinerary PDF.

## Parsing contract

### Flight date-time shapes

Normalize each flight value with the existing NFKC and whitespace rules, then
accept exactly one of these shapes:

1. full datetime: `YYYY/M/D HH:MM`, with the existing `.`, `/`, or `-` date
   separators; or
2. time-only: `HH:MM`.

Parse both departure and arrival values in every row. A page must be uniformly
dated or uniformly time-only across all flight rows and both fields. Mixed
shapes fail closed with `PARSE_CONTRACT_CHANGED` at `航班日期`. Malformed dates,
times, missing values, extra text, or unsupported shapes continue to fail
closed. `Flight.date` is the parsed departure date in dated mode and `""` in
time-only mode; departure and arrival times remain source-bound values.

### Product and daily dates

Resolve dates in this order:

1. If `.departure_date` exists, parse it as before and compute the return date
   from the positive source day count. In dated-flight mode, keep the existing
   first/last flight date consistency checks. In time-only mode, preserve the
   product dates but do not invent per-flight dates.
2. If `.departure_date` is absent and flights are dated, keep the current
   first-flight fallback and last-flight consistency check.
3. If `.departure_date` is absent and flights are time-only, set product
   departure and return dates to `""`; set every `Flight.date` and
   `ItineraryDay.date` to `""`.

Even when dates are unknown, the duration must remain a valid positive integer,
the page must contain at least one flight, and daily cards must be exactly the
consecutive sequence `1..day_count`. Route, meals, hotel, product identity, and
notice contracts remain unchanged. No logic may special-case 4-, 5-, 6-, or
any other fixed trip length.

## Merge and review behavior

When the selected web itinerary has blank product dates, add one
`SOURCE_DATE_MISSING` warning bound to the web source. The warning states that
the source did not publish a traceable trip date and OP review is required. It
does not block a URL-only `DRAFT_READY` state.

When a PDF and web page are supplied together, PDF facts remain authoritative.
Blank web product, flight, or daily dates represent missing web facts, not
contradictory values: retain the corresponding PDF dates, skip blank-date
conflicts, and add the same web-bound warning once. Nonblank disagreements keep
the existing blocking conflict behavior.

`review.md` must show the warning without exposing source contents. LIST Word
already renders a blank product departure date and blank daily dates as yellow
`待 OP 確認`; reuse that behavior rather than adding a new template path.

## Narration behavior

When the departure date is known, preserve the existing protected product/date
fact. When it is unknown:

- keep a source-bound protected fact containing only the product name;
- do not emit an empty sentence such as `出發日期為。`;
- add a nonblocking `MISSING_REQUIRED_FACT` review item for
  `product.departure_date`; and
- omit blank product, flight, and daily dates from pronunciation entries.

The narration input may remain `ready: true` when this is the only missing
source fact. Script validation must still require the protected product-name
fact and must not permit a guessed date.

## Confirmation guard

A DRAFT with blank product departure date, blank product return date, or any
blank daily date must be rejected by local confirmation with a specific
unresolved-source-date error. Time-only flight rows alone do not block
confirmation when product and daily dates came from an approved PDF or explicit
published product date. Existing conflict, OP-field, artifact, Word, audio, and
MP3 confirmation requirements remain unchanged.

## Data flow

1. The allowlisted gateway obtains one approved page without retry.
2. The live parser validates identity, duration, uniform flight shape, daily
   sequence, itinerary content, and notices.
3. Time-only plus no published departure date produces blank date fields, not
   inferred values.
4. Merge creates one source-bound missing-date warning and keeps the draft
   reviewable.
5. Narration includes the product name but excludes the unknown date.
6. Word displays existing yellow placeholders; local confirmation remains
   blocked until a new approved source supplies dates.

## Test contract

Use only de-identified synthetic fixtures and public behavior seams:

- `parse_newamazing_html()` accepts missing `.departure_date` plus uniform
  `HH:MM`, preserving times and producing blank product, flight, and daily dates;
- the same parser preserves dated behavior and explicit product-date behavior;
- mixed full-datetime/time-only rows, malformed time-only values, missing
  duration, flight absence, and daily count/order mismatch fail closed;
- `merge_briefing_sources()` produces one `SOURCE_DATE_MISSING` warning for a
  web-only draft and treats blank web dates as missing when a PDF supplies them;
- `build_narration_input()` emits product-only protected text, a nonblocking
  missing-date review item, and no blank date pronunciation entries;
- the existing LIST patch-plan seam continues to produce yellow product/day
  placeholders; and
- the workflow confirmation seam rejects a DRAFT with unresolved product or
  daily dates.

Run the focused parser, merge, narration, Word, and workflow suites, then the
complete offline suite, compileall, and `git diff --check`. After tests pass,
build the 0.2.0 package, update only the installed modules that changed, verify
installed hashes, and rerun offline `doctor`. Any later formal DRAFT GET remains
a separate single-use authorization and is never retried automatically.
