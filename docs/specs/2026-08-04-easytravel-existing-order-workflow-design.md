# EasyTravel existing-order workflow design

Date: 2026-08-04
Target release: EasyTravel Cowell CLI 0.3.2

## Outcome

Ship one integrated `easytravel-cowell-cli` Skill for 立益旅行社 with two
operator routes:

1. prepare a validated official 19-column Cowell roster from passport PDFs or
   photos; and
2. fill passenger names and room assignments in an order the OP already
   created, or apply only room assignments when the names already exist.

The Skill must never create a group, order, or passenger slot. The generic CLI
may retain its legacy order-creation commands for backward compatibility, but
the EasyTravel Skill must not call or advertise them.

## Required rooming inputs

The existing-order route requires an exact Cowell group code, exact existing
order ID, and one local DOCX/XLSX rooming-list file. The OP creates the order
and enough passenger rows first. If usable rows are insufficient, preview must
stop and ask the OP to correct the order in Cowell.

## Existing-order behavior

Parse the source offline, then run a live read-only preview that selects one
state:

- **Empty names:** when none of the source names exists and the selected Cowell
  rows are usable placeholders, import every Chinese/English name and then
  apply every room assignment.
- **Names already imported:** when every source passenger matches exactly one
  Cowell passenger, skip name import and apply only room assignments.
- **Unsafe mixed state:** partial matches, ambiguous identities, insufficient
  placeholders, or page-contract drift stop without writing. Never overwrite a
  named passenger or partially complete a file.

## Cabin handling

Any cabin already present in the Cowell order is supported.

- With all names matched, continue without a cabin argument.
- With placeholders in exactly one cabin, detect it and rebuild the plan bound
  to that cabin.
- With placeholders across several cabins, ask the OP which source passenger
  sequence belongs to each cabin. Continue only with an exact map covering
  every source passenger once.
- Preserve Cowell cabin values. Never infer, normalize, or edit them.

## Passenger-category handling

Adult, child, and infant rows are all supported. A difference between the
source honorific/category and Cowell is a non-blocking warning. Continue to
fill the name and room while preserving Cowell's category exactly; never
change or normalize it.

## Write boundary and verification

Every write requires a fresh preview and exact confirmation bound to the group,
order, source hash, cabin mapping, room offset, and deterministic plan. Apply
at most once after current operator approval. Fresh Cowell read-back must show
passenger identities, room assignments, and room notes all equal the source
count. After an unknown response, read state first and do not retry blindly.

Inputs and generated PII remain local. Never commit or routinely report names,
passport values, source files, workbooks, or private cabin maps.

## Package and compatibility

- Build `EasyTravel-Cowell-CLI-0.3.2.zip` as one integrated Skill.
- Keep passport-roster and existing-order rooming routes separate inside it.
- Retain generic legacy order-creation CLI commands for compatibility.
- Remove order creation from all EasyTravel-facing instructions and examples.
- Preserve the legacy `CowellAgent-0.2.0.zip`; do not modify it in place.

## Verification

Automated tests must prove:

- empty names select complete name import plus rooming;
- all matched names select rooming-only with no name-import request;
- partial matches remain blocked;
- one placeholder cabin is detected and bound before writing;
- multiple placeholder cabins block until an exact complete map is supplied;
- adult/child/infant mismatches warn without blocking and preserve Cowell data;
- insufficient rows, ambiguity, collisions, drift, and incomplete read-back
  fail closed;
- EasyTravel documentation exposes no supported order-creation route; and
- the full suite, package validators, build, version check, and changed-file
  PII scan pass.

No live Cowell request or write is required for this release. Any future live
non-idempotent apply remains a separate target-specific approval gate.

## Acceptance criteria

Given group code, existing order ID, and rooming file, the Skill returns either
a verified complete name import plus rooming, verified room-only assignment, or
a clear no-write blocker. Existing Cowell rows of any cabin and adult, child,
or infant category are supported under the preservation rules above.
