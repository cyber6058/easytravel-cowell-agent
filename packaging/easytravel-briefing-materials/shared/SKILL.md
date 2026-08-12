---
name: easytravel-briefing-materials
description: >-
  Use when EasyTravel/立益 OP provides a NewAmazing product URL or itinerary PDF
  and asks for 說明會資料, LIST Word, Yating narration, MP3/WAV/TXT/SRT,
  review, or local confirmation.
---

# EasyTravel Briefing Materials

Use the installed `briefing` CLI as the deterministic boundary. Use the
conversation only to collect OP decisions and write a narration script from the
generated narration input. Keep every source, decision, script, and artifact local.

Set the runtime command to:

```powershell
$briefingPython = "$env:LOCALAPPDATA\EasyTravelBriefing\app\.venv\Scripts\python.exe"
```

Read [CLI workflow](references/cli.md) before the first command. Read
[sources and OP review](references/sources-and-op-review.md) before preparing or
revising a manifest. Read [narration policy](references/narration-policy.md)
before writing the script. Read
[audio and template](references/audio-and-template.md) before any render or
confirmation.

## Required scope

Handle one NewAmazing product at a time. First-stage regions are Osaka, Tohoku,
and Hokkaido. Require a NewAmazing HTTPS URL, a local itinerary PDF, or both.

Never infer a missing fact. Preserve an unknown, conflict, unavailable forecast,
or unsupported source as review work. PDF facts win for the same trip; the
website supplies current notices; only approved official weather evidence may
populate weather. Bind every OP value and conflict decision to the exact draft ID.

## Workflow

- `briefing prepare`: create a new manifest, review, and narration input. Stop
  for missing OP fields, conflicts, unavailable weather, or source failure.
- `briefing check-script`: validate the locally written narration. Stop until
  every blocking issue is cleared.
- `briefing render`: create DRAFT Word and local Yating artifacts. Stop for
  Word, visual, audio, duration, subtitle, or MP3 failure.
- `briefing render --confirm-draft-id`: copy an exact verified DRAFT into local
  CONFIRMED artifacts. Stop unless the OP gives current explicit approval for
  that exact draft ID.

1. Run `doctor`. It may enumerate local capabilities, but it does not authorize
   Word automation, speech synthesis, source requests, or installation.
2. Before a live NewAmazing or JMA request, state the exact read-only request and
   obtain current explicit approval. Do not treat an earlier URL, design approval,
   or another gate as authorization.
3. Run `prepare` into a new local output directory. Review `review.md` and
   `narration-input.json`; do not treat `DRAFT_READY` as final approval.
4. Collect only explicit OP values and `use_a` or `use_b` conflict decisions.
   Revise from the reviewed manifest without refetching sources.
5. If narration input is ready, write the eight-section script using only its
   markers and protected facts. Run `check-script` until it returns ready.
6. Obtain current explicit approval before starting Word COM or local Yating.
   Render once. On an unknown Word or audio result, inspect the new manifest and
   partial artifacts. Do not retry an unknown result.
7. Visually inspect the Word QA image and listen to the relevant audio. Automated
   checks do not replace OP review. Keep a blocked artifact blocked.
8. Show the draft ID, status, review path, completed artifact paths, warnings, and
   exact confirmation action. Confirm only with the same checked script and the
   exact draft ID named by the OP.
9. Report local paths and verification state. The OP manually chooses whether to
   distribute any confirmed file.

## Safety boundaries

- Never send LINE messages, upload artifacts, publish files, or trigger a deploy.
- Never use cloud TTS, paid resources, Azure Speech, or automatic voice fallback.
  Microsoft Yating is the only automatic local voice.
- Never substitute Hanhan, generate a video, or add a virtual presenter.
- Never install ffmpeg, fetch a new source, start Word COM, or synthesize speech
  merely because another workflow stage was approved.
- Never overwrite a source PDF, private LIST template, existing run directory, or
  existing confirmed artifact.
- Never commit source PDFs, templates, manifests, scripts, audio, Word/PDF/PNG QA,
  OP decision files, or any traveler or staff data.
- Never expose names, phone values, source document contents, or narration text in
  routine logs or the final summary.

## Common mistakes

- Reusing decisions after the manifest changed: create decision JSON with the
  currently reviewed draft ID.
- Writing from `review.md`: write only from `narration-input.json` so prohibited
  values never enter the script.
- Treating exit code `20` as success: it means review remains.
- Confirming after a partial render: confirmation requires successful Word QA,
  Yating artifacts, MP3, zero blocking conflicts, and zero required yellow fields.
- Sending a confirmed MP3 automatically: confirmation changes only local state.
