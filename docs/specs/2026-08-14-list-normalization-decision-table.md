# LIST normalization decision table

## Purpose

This policy converts an allowlisted component-diagnosis report into a reviewable
decision table. It does not normalize a document, select a base sample, relax the
schema-2 comparison contract, or authorize Word access or calibration.

## Contract-fixed facts

The component identity sets are fixed by the existing LIST prototype contract:

- 19 prototype cells for style, font, and paragraph evidence;
- six border sides for each prototype cell, for 114 border components;
- seven daily-header and seven daily-body cells; and
- at least one shape, with the same synthetic shape IDs and shape kinds in all
  three samples.

A missing, additional, duplicate, or renamed component ID is a contract conflict.
A shape-kind change is also a contract conflict. Neither can be normalized by an
OP base choice.

The product contract does not currently prescribe a font size, line spacing,
border width, or floating-shape geometry. Those values must not be invented from
the samples.

## Decision rules

| Observation | Decision-table status | Rule |
| --- | --- | --- |
| Complete component bundles are identical | `PRESERVE_UNANIMOUS` | Keep the common value. |
| A style, font, paragraph, border, or daily-header bundle differs | `REQUIRES_OP_BASE` | OP must select one exact source SHA-256 for the complete bundle. |
| Two samples agree and one differs | `REQUIRES_OP_BASE` | Agreement is evidence, not authority; no majority selection. |
| A component contains Word sentinel `9999999` | `BLOCKED_MIXED_VALUE` | The affected source is ineligible as that bundle's base. |
| Floating-shape geometry differs | `REQUIRES_OP_BASE` | Select left, top, width, and height as one geometry bundle. Never mix coordinates. |
| Daily-body digest differs | `VERIFY_AFTER_COMPONENT_NORMALIZATION` | It is derived from the prototype style/font/paragraph decisions and is verified afterward, not decided independently. |
| Component identity or shape kind differs | `COMPONENT_CONTRACT_CONFLICT` | Stop; a new approved design is required. |

Every decision is bound to the three source SHA-256 values and to a SHA-256 of
each allowlisted component bundle. A later OP-decision artifact must name the
decision ID, one eligible source SHA-256, and its matching component-value
SHA-256. Choosing by filename, sample order, median, majority, or convenience is
not valid.

## Offline artifacts

`plan-list-normalization` accepts only an existing `component-diagnosis.json`
with the exact schema emitted by `diagnose-list-components`. It never accepts
LIST paths and does not construct a Word adapter. It writes one exclusively
created `normalization-decision-table.json` in a new private directory.

The semantic decision-table SHA-256 is calculated from canonical JSON. An OP
choice artifact has exactly these fields:

```json
{
  "schema_version": 1,
  "decision_table_sha256": "<sha256>",
  "source_sha256": ["<sample-001>", "<sample-002>", "<sample-003>"],
  "choices": [
    {
      "decision_id": "<family:synthetic-component-id>",
      "selected_source_sha256": "<eligible-source-sha256>",
      "selected_component_value_sha256": "<bound-component-sha256>"
    }
  ]
}
```

Validation rejects unknown fields, a mismatched table hash or source set,
missing, extra, or duplicate choices, an ineligible mixed-value source, and a
component-value hash that does not belong to the selected source. A component
contract conflict cannot be resolved with an OP-choice artifact.

`prepare-list-normalization-choices` accepts only an existing strict component
report and its exactly matching strict decision table. It does not accept LIST
paths or construct a Word adapter. In a new private directory it exclusively
creates:

- `normalization-choice-worksheet.json`, with fixed `sample-001` through
  `sample-003` labels, the bound source and component hashes, changed-property
  names, and only the corresponding allowlisted numeric, enum, or digest values;
  and
- `normalization-choices.blank.json`, with one intentionally blank hash-bound
  choice for every decision.

The worksheet never records source filenames or paths and never recommends a
sample. A sentinel-bearing option remains visible as evidence but has
`eligible_as_base: false`. The blank choice artifact is deliberately invalid
until the OP fills every selected source SHA-256 and matching component-value
SHA-256 from an eligible worksheet option.

## Gate C integration

`calibrate-list` may accept a strict decision table, a completed strict choice
artifact, and an explicit width-base sample together. Omission of any one input
rejects the normalization request before Word access. The table source hashes
must match the three current calibration source hashes in order.

The current approved implementation is deliberately narrower than arbitrary
per-component mixing: every selected component source and the width-base source
must resolve to one complete source layout. Calibration copies that source and
uses its complete schema-2 normalized layout as the master target. This covers
only the eight already diagnosed formatting conflicts; any new schema-2 field
conflict remains a contract error before the calibration mutation. The master
must still reproduce the selected source's normalized structure fingerprint,
and all existing dynamic-token, source-mutation, exclusive-create, and manifest
checks remain unchanged.

## Gate boundary

The decision table is offline evidence only. Calibration remains blocked until:

1. there are no component-contract blockers;
2. every `REQUIRES_OP_BASE` decision has an explicit bound OP choice;
3. no chosen bundle contains the mixed-value sentinel;
4. daily-body derived audits can be checked after normalization; and
5. a separate Gate C calibration approval is granted.

The calibration implementation must still pass the unchanged schema-2 comparison
and calibrated-master validation. This policy is not permission to omit or weaken
either check.
