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

## Briefing scope

- Prepare reviewable briefing manifests, LIST Word drafts, narration scripts,
  Microsoft Yating audio, subtitles, and local confirmed artifacts for one
  NewAmazing product in Osaka, Tohoku, or Hokkaido.
- Use only an OP-provided NewAmazing URL, local itinerary PDF, approved JMA
  evidence, and explicit OP decisions bound to the current draft ID.
- Preserve missing or conflicting facts for review; never guess values or use an
  unapproved source, template, voice, or fallback.
- Never send LINE, upload artifacts, create video, use cloud TTS, deploy, or
  publish from the briefing workflow.
- Outside the one-request DRAFT rule below, source access, calibration,
  dependency installation, and confirmation remain separate approval gates.
- After 0.2.0 calibration, one explicit request that supplies a NewAmazing URL
  and/or PDF and asks to generate briefing materials authorizes one local DRAFT:
  the supplied source, canonical master, owned Word, pdftoppm, Microsoft Yating,
  and already configured ffmpeg. Do not repeat normal-stage approval prompts.
- That one-DRAFT boundary excludes calibration, live JMA, installation,
  CONFIRMED, LINE, upload, deploy, publish, push, and any Cowell access.

This briefing scope does not expand any Cowell read or write permission.

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
