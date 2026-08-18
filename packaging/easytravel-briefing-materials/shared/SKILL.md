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

- `briefing prepare`: create a new manifest, review, and narration input. Missing
  OP fields, unavailable weather, and pronunciation review remain visible but
  allow a URL-only DRAFT; stop for conflicts, source integrity failure, or drift.
- `briefing check-script`: validate the locally written narration. Stop until
  every blocking issue is cleared.
- `briefing render`: create a QR-free output copy of the DRAFT Word and local
  Yating artifacts. Stop for Word, visual, speech, duration, or subtitle failure.
  Missing ffmpeg leaves MP3 incomplete but preserves a reviewable
  Word/WAV/TXT/SRT DRAFT.
- `briefing render --confirm-draft-id`: copy an exact verified DRAFT into local
  CONFIRMED artifacts. Stop unless the OP gives current explicit approval for
  that exact draft ID.

### One-request DRAFT authorization

When one user message supplies a NewAmazing URL, an itinerary PDF, or both and
explicitly asks to generate briefing materials, that message authorizes one
local DRAFT for those supplied sources. The bounded DRAFT may read the supplied NewAmazing URL or PDF, read the configured canonical LIST master, start an owned hidden Word instance, run configured pdftoppm, synthesize with Microsoft Yating,
and use configured ffmpeg when it is already present. Do not ask for another approval between these normal stages.

This authorization belongs only to the supplied sources and resulting draft. A
different source or changed facts require a new generation request. Stop once
and report all actionable exceptions when a source is ambiguous or untraceable,
sources conflict, a parser or template drifts, or QA fails. Missing values and
other actionable review items do not stop the source-bound local DRAFT.

It does not authorize LIST calibration, live JMA access, dependency installation,
CONFIRMED, LINE, email, upload, deploy, publish, push, or any Cowell access. These
remain separate current-approval boundaries.

1. Run `doctor`. It is an offline capability and hash probe. A warning does not
   authorize installation, fallback, calibration, or network access.
2. If the current message meets the One-request DRAFT authorization above, use
   its supplied URL and/or PDF without another normal-stage approval. Otherwise,
   do not fetch a source or start a DRAFT.
3. Run `prepare` into a new local output directory. Review `review.md` and
   `narration-input.json`; continue when `ready` is true even if nonblocking
   review items remain. Do not treat `DRAFT_READY` as final approval.
4. Collect only explicit OP values and `use_a` or `use_b` conflict decisions.
   Revise from the reviewed manifest without refetching sources.
5. If narration input is ready, write the eight-section script using only its
   markers and protected facts. Run `check-script` until it returns ready.
6. Under the same one-request authorization, render once with the canonical
   master, owned Word, pdftoppm, Yating, and configured ffmpeg. On an unknown Word
   or audio result, inspect the new manifest and partial artifacts. Do not retry an unknown result.
7. Visually inspect every Word QA page and listen to the relevant audio.
   Automated checks do not replace OP review. Keep a blocked artifact blocked.
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
- Never install ffmpeg or fetch a different source. Word and Yating are bounded
  to the one-request DRAFT authorization, not an unrelated approval.
- Never overwrite a source PDF, private LIST master, existing run directory, or
  existing confirmed artifact.
- Never commit source PDFs, masters, manifests, scripts, audio, Word/PDF/PNG QA,
  OP decision files, or any traveler or staff data.
- Never expose names, phone values, source document contents, or narration text in
  routine logs or the final summary.

## Common mistakes

- Reusing decisions after the manifest changed: create decision JSON with the
  currently reviewed draft ID.
- Writing from `review.md`: write only from `narration-input.json` so prohibited
  values never enter the script.
- Treating exit code `20` as either completion or an automatic stop: it means
  review remains; use narration input `ready` to decide whether a DRAFT may run.
- Confirming after a partial render: confirmation requires successful Word QA,
  Yating artifacts, MP3, zero blocking conflicts, and zero required yellow fields.
- Sending a confirmed MP3 automatically: confirmation changes only local state.
- Asking the user to select a 5/6/7 day template: runtime always uses the one
  calibrated master and the source's verified positive day count.
