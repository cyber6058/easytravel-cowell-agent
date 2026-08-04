# EasyTravel Cowell Agent rules

This repository is the dedicated private EasyTravel/立益 product.

## Scope

- Prepare a validated official 19-column Cowell roster from passport files.
- For an order already created by the OP, import all missing names only when
  none currently match, then apply room assignments.
- If all names already match, apply room assignments only.
- Partial name matches always block.
- Support every existing Cowell cabin; multiple placeholder cabins require an
  OP-supplied source-sequence-to-cabin map.
- Adult/child/infant differences are warnings only. Preserve Cowell values.

Never add group creation, order creation, payments, seat inventory, reports, or
unrelated Cowell discovery without a new approved design.

## Safety

- Run parse and plan offline before any Cowell access.
- Preview is read-only. Every apply requires the exact final confirmation and
  current operator approval.
- Never store credentials or passenger PII in Git.
- Never commit passport images, extracted JSON, rooming files, generated XLSX,
  browser profiles, sessions, or live Cowell responses.
- Do not retry an unknown write result. Read current state first.

## Verification and handoff

- Read STATUS.md before editing.
- Run the complete offline test suite after code changes.
- Validate the Skill and build package before release changes.
- Update STATUS.md with current state, work completed, next step, and blockers.
- Pull before work; when a remote exists, commit and push completed changes.
