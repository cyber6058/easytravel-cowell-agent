# NewAmazing missing departure-date parser design

## Status

Approved design for a narrow parser-drift fix. This document contains only
synthetic contract details and no live product identifiers or source content.

## Problem

The approved live-card parser expects both `.departure_date` and `.return_date`
inside `.product_basic_info`. A current product page preserves the product
container, duration, product identity, flights, and daily itinerary, but omits
the `.departure_date` element. The parser therefore fails closed at the
`產品資訊` anchor even though the first flight still provides a traceable
departure date.

## Chosen behavior

Keep `.return_date` as the required source for the positive trip-day count. For
the departure date:

1. Parse flights before finalizing product dates.
2. When `.departure_date` exists, parse it exactly as before.
3. When `.departure_date` is absent, use the first parsed flight's date. This is
   a source-bound fact from the same approved page, not an inferred value from
   the product code or current date.
4. Compute the return date as `departure date + day count - 1`.
5. Require the first flight date to equal the selected departure date and the
   last flight date to equal the computed return date.
6. Keep the existing requirement that daily cards are consecutive and their
   count equals the parsed trip-day count.

The parser must remain independent of fixed 4-, 5-, or 6-day templates. Any
positive day count is accepted only when the flight and daily-card invariants
agree.

## Failure behavior

Continue to return `PARSE_CONTRACT_CHANGED` when:

- duration is missing or invalid;
- no flights are present;
- an explicit departure date conflicts with the first flight;
- the last flight conflicts with the computed return date;
- daily-card count or ordering conflicts with the trip-day count; or
- another required live-card contract is missing.

Do not parse a date from the product code, page retrieval time, price area,
free-form text, or a different source. Do not weaken existing source-integrity
checks.

## Test seam

Test through the public `parse_newamazing_html()` interface with the existing
de-identified live-card fixture:

- remove only the `.departure_date` element and verify that departure and
  return dates come from the first flight plus the source day count;
- retain the existing explicit-date and flight-date mismatch coverage;
- add or retain a last-flight mismatch assertion so the fallback cannot hide a
  shortened or extended trip;
- run the focused NewAmazing parser suite, then the complete offline suite.

After tests pass, update only the installed parser module, re-run the installed
doctor, and use the separately authorized final live DRAFT request. The live
response remains temporary and is not committed or retained.
