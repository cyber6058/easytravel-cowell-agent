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
