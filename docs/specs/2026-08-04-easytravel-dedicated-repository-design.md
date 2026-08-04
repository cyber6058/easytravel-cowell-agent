# EasyTravel dedicated repository design

Date: 2026-08-04
Target repository: `cyber6058/easytravel-cowell-agent`
Required visibility: private

## Outcome

Create a self-contained repository for 立益旅行社 that another computer and
Agent can clone, install, test, and extend without access to the broader
`cowell-cli` development repository.

The repository contains source code, tests, installation packaging, operating
instructions, and safety rules for two integrated workflows:

1. passport PDF/photo to validated official 19-column Cowell roster; and
2. existing Cowell group/order plus DOCX/XLSX rooming list to complete name
   import and rooming, or rooming only when every name already exists.

## Local and remote identity

- Local path: `C:\Users\cance\projects\easytravel-cowell-agent`
- GitHub repository: `cyber6058/easytravel-cowell-agent`
- GitHub visibility: private before the first push
- Git history: new and independent; do not copy `.git` from `cowell-cli`
- Product name: `easytravel-cowell-agent`
- Internal Python package name: retain `cowell_cli` initially to minimize
  migration risk

The current `cowell-cli` remote and history remain unchanged.

## Included product surface

The dedicated CLI exposes only the commands required by the product:

- `doctor`
- `auth status`
- `passports prepare`
- `passports validate`
- `passports template`
- `passports export`
- `rooms parse`
- `rooms plan`
- `rooms preview`
- `rooms apply`

The repository includes the controlled-Chrome launcher, local configuration,
the EasyTravel installer/plugin/Skill, required runtime modules, relevant
tests, synthetic or sanitized structural fixtures, the approved workflow
specifications, and a resumable `STATUS.md`.

## Excluded product surface

Do not copy or expose:

- group, group-type, order, or passenger-slot creation;
- payment, Followme, OPS, scheduling, LINE, seat-reporting, badge-reporting, or
  finance workflows;
- unrelated discovery scripts, specifications, fixtures, or historical status;
- live passenger names, passport values, business documents, cookies,
  credentials, tokens, private keys, browser profiles, or local config;
- `.git`, `.venv`, `dist`, `tmp`, caches, coverage files, egg-info, or
  compiled files from the source repository.

If a shared low-level module contains unrelated command registration, split or
prune the public command surface while preserving the tested implementation
needed by passports and existing-order rooming.

## Existing-order behavior

- Require exact group code, existing order ID, and local rooming file.
- With zero source-name matches and enough selected placeholders, import every
  name and then apply every room assignment.
- With all source names matched, skip name import and apply rooms only.
- With partial matches, ambiguity, insufficient placeholders, collisions,
  contract drift, or incomplete read-back, stop without writing.
- Support every existing Cowell cabin. Auto-bind one placeholder cabin; require
  an exact source-sequence map when several cabins exist.
- Treat adult, child, and infant differences as warnings. Preserve the existing
  Cowell cabin and category values.
- Require a fresh preview, current exact confirmation, one bounded apply, and
  fresh read-back.

## Passport behavior

- Prepare one upright useful-resolution image per passport.
- Require visual inspection plus printed-field and TD3 MRZ validation.
- Never guess unresolved fields or export unverified data by default.
- Use the logged-in account's official template through the registered
  read-only operation.
- Keep all images, JSON, and output workbooks local and untracked.

## Repository instructions

Create a project-specific `AGENTS.md` that requires:

- no live Cowell request or write without an explicit target and current
  approval;
- no credentials or PII in Git, logs, fixtures, or final summaries;
- tests and package verification after code changes;
- `STATUS.md` updates that record exact state, verification, next step, and
  blockers;
- private-only GitHub visibility and explicit approval for later pushes.

The README explains local development, package building, company-computer
installation, clone/pull workflow, and the boundary between offline tests,
read-only preview, and live apply.

## Extraction method

Use an allowlist from the verified 0.3.2 source rather than copying the whole
repository and deleting afterward. Copy the minimum coherent module set, then
run import collection and tests to discover missing dependencies. Add only
dependencies required by an included command.

Do not copy the 0.3.2 ZIP as the source of truth. The ZIP may be included only
as a reproducible build output outside Git; the repository owns source,
packaging instructions, and tests.

## Verification

Before the first commit:

- collect and run the dedicated test suite;
- confirm the CLI help exposes only the approved command surface;
- validate the Skill and plugin metadata;
- build a fresh install ZIP;
- verify runtime/plugin versions and ZIP path safety;
- verify no cache, compiled, egg-info, or source-repository history appears;
- scan every tracked file for credentials and PII;
- run `git diff --check` and review the complete tracked file list.

No Cowell connection is required for repository extraction. Tenant UI and
permission compatibility remain unverified until the company computer runs a
read-only preview.

## GitHub publication

1. Initialize the new local Git repository and commit the verified source.
2. Create `cyber6058/easytravel-cowell-agent` with private visibility and no
   generated README, license, or gitignore.
3. Query GitHub after creation and require `visibility=PRIVATE`.
4. Add that exact repository as the new repo's `origin`; never change the
   existing `cowell-cli` origin.
5. Push only after local verification and the visibility check succeed.
6. At the agency, invite the company GitHub account as a collaborator. Use the
   company account on the company computer to clone or pull.

## Company-computer acceptance

On the company computer:

1. clone the private repository;
2. read `AGENTS.md`, `README.md`, and `STATUS.md`;
3. install dependencies and run the offline suite;
4. build the package and compare the expected structure;
5. start controlled Chrome and let the OP log in manually;
6. run `doctor`, `auth status`, offline parsing, and a read-only rooming
   preview against an OP-created order;
7. record interface/permission differences before changing adapters;
8. obtain a separate exact confirmation before any non-idempotent apply.

## Extension boundary

Future EasyTravel features are developed in this dedicated repository when
they belong to the same passport/roster/existing-order operator product. A new
feature that introduces another external system, separate credentials, or an
independent operational lifecycle receives its own design boundary before code
is added.

## Acceptance criteria

The task is complete when the new local repository is self-contained, its
dedicated tests and package checks pass, its tracked files are PII/credential
clean, GitHub reports the remote as private, the verified main branch is pushed,
and the company-computer handoff can be followed without access to the original
`cowell-cli` repository.
