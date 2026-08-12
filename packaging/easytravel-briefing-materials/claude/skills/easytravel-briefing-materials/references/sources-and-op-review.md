# Sources and OP review

## Source boundary

- Accept one `https://www.newamazing.com.tw/` product URL, one local itinerary
  PDF, or both.
- Treat the PDF as authoritative for the same trip's dates, flights, days,
  meals, hotels, and cities. Use the website for current product notices.
- Keep a URL-only product region unknown unless the page states it or the OP
  explicitly chooses Osaka, Tohoku, or Hokkaido for the current draft.
- A PDF-only run does not authorize searching for or fetching a matching page.
- Version 0.2.0 does not silently fetch or inject JMA data. Keep weather in
  review until an approved enrichment step supplies official evidence.
- Never retain raw HTML or JMA XML. The local manifest stores hashes, locations,
  parser versions, timestamps, and bounded field evidence.

The NewAmazing fetcher allows HTTPS only, one same-host redirect, no retries,
and a bounded response. A changed page contract, ambiguous product, scanned PDF,
unsupported region, or conflicting trip fact remains blocked or reviewable.

## OP values

Use only fields listed in the current `review.md`. Store the JSON under the local
ignored output root and do not quote its values in routine logs.

```json
{
  "draft_id": "<CURRENT-DRAFT-ID>",
  "values": {
    "meeting_time": "<OP-CONFIRMED-VALUE>",
    "product_region": "大阪"
  }
}
```

Allowed required fields are `meeting_time`, `meeting_place`,
`tour_leader_name`, `tour_leader_phone`, `identification_or_luggage_tag`,
`airport_representative`, `emergency_contact_name`, `emergency_contact_phone`,
and `alternate_hotel`. `product_region` is accepted only when the current
manifest explicitly requests it. Do not add fields or use placeholder text as a
confirmed value.

## Conflict decisions

Use the exact conflict field names shown in the current review. Choose one
recorded side; do not type a third value into conflict decisions.

```json
{
  "draft_id": "<CURRENT-DRAFT-ID>",
  "decisions": {
    "product.departure_date": "use_a",
    "days": "use_b"
  }
}
```

Both OP values and conflict decisions are stale after any new manifest version.
If both files are supplied in one revision, bind both to the previous manifest;
the workflow safely rebinds the second operation after applying the first.

## Review rules

- Read source IDs, locations, retrieval times, warnings, OP fields, and every
  blocking conflict before progressing.
- Keep missing or disputed values out of narration. Do not use the losing side
  of a resolved conflict.
- Treat `DRAFT_READY` as structurally reviewable, not complete or distributable.
- Report only draft ID, status, issue codes, safe paths, counts, and next gate.
  Do not repeat staff names, telephone values, PDF text, or full narration.
