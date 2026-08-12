# Audio and template boundary

## Local configuration

The installer creates `%LOCALAPPDATA%\EasyTravelBriefing\config.toml` once and
does not overwrite it. The file contains only:

- a local output root;
- one private `LIST-master.docx` `master_path`;
- one private schema 2 `calibration_manifest` path;
- an existing `pdftoppm.exe` path; and
- an optional existing `ffmpeg.exe` path.

Never put the private master, calibration manifest, their contents, generated
artifacts, or OP data in the package or Git. The runtime validates both hashes
and never selects a template by day count.

## Word

The current one-request DRAFT authorization allows rendering to start one hidden,
owned Word instance. It opens the canonical LIST master read-only, creates a new
DOCX, dynamically creates the verified number of daily rows, and checks the
table, anchor, merged-cell, QR, section, A4 portrait, calibration hash, and
layout contracts. Word decides the page count from content; long trips continue
at normal readable settings.

Automated checks do not prove visual correctness. Inspect every QA page at
readable resolution for cropping, table borders, merged cells, first-page QR,
continuation identity/header, daily rows, and yellow fields. Never confirm a
draft with an unviewed Word QA page.

## Audio

Microsoft Yating (`zh-TW`) is the only automatic voice. The workflow performs
one continuous local synthesis and uses exact SSML bookmarks for SRT timing.
It validates PCM WAV structure, bookmark order, transcript and artifact hashes,
and an actual duration from 360 through 480 seconds.

Do not switch to Hanhan, cloud TTS, Azure, another voice, or estimated subtitle
timing. If Yating is absent or the bookmark/audio result is unknown, keep safe
Word, narration, and review artifacts and stop.

MP3 is derived only from the verified WAV through an already configured ffmpeg.
Do not install ffmpeg as a side effect. If ffmpeg is missing, preserve the DRAFT
WAV, TXT, and SRT for review. A missing MP3 still blocks confirmation.

## Confirmation

Confirmation requires all of the following:

- a successful `DRAFT_READY` render manifest and unchanged script hash;
- the exact current draft ID;
- no unresolved blocking conflict;
- all required OP fields confirmed with no yellow highlight;
- completed Word, Word PDF/every QA page, WAV, MP3, TXT, SRT, and audio metadata;
  and
- current OP approval after visual and listening review.

Confirmation creates a new local run, removes the `DRAFT_` filename prefix, and
copies verified artifacts without rerunning Word or speech. It does not authorize
LINE, upload, publication, deployment, or any other external write.
