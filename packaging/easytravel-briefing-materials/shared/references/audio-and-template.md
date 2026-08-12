# Audio and template boundary

## Local configuration

The installer creates `%LOCALAPPDATA%\EasyTravelBriefing\config.toml` once and
does not overwrite it. The file contains only:

- a local output root;
- the private LIST `.doc` or `.docx` path and its approved layout SHA-256;
- an existing `pdftoppm.exe` path; and
- an optional existing `ffmpeg.exe` path.

Never put the private template, its contents, generated artifacts, or OP data in
the package or Git. Never invent a layout fingerprint or accept the example's
zero placeholder as an approved fingerprint.

## Word

Rendering starts a hidden, owned Word instance only after current approval. It
opens the confirmed LIST template read-only, creates a new DOCX, and checks the
table, anchor, merged-cell, QR, section, A4 portrait, and layout fingerprint
contracts. It then creates a one-page PDF and PNG for QA.

Automated checks do not prove visual correctness. Inspect the PNG at readable
resolution for cropping, table borders, merged cells, QR code, daily rows, and
yellow fields. Never confirm a draft with an unviewed Word QA image.

## Audio

Microsoft Yating (`zh-TW`) is the only automatic voice. The workflow performs
one continuous local synthesis and uses exact SSML bookmarks for SRT timing.
It validates PCM WAV structure, bookmark order, transcript and artifact hashes,
and an actual duration from 360 through 480 seconds.

Do not switch to Hanhan, cloud TTS, Azure, another voice, or estimated subtitle
timing. If Yating is absent or the bookmark/audio result is unknown, keep safe
Word, narration, and review artifacts and stop.

MP3 is derived only from the verified WAV through an already configured ffmpeg.
Do not install ffmpeg as a side effect. A missing MP3 blocks confirmation even
when WAV, TXT, and SRT are valid.

## Confirmation

Confirmation requires all of the following:

- a successful `DRAFT_READY` render manifest and unchanged script hash;
- the exact current draft ID;
- no unresolved blocking conflict;
- all required OP fields confirmed with no yellow highlight;
- completed Word, Word PDF/PNG QA, WAV, MP3, TXT, SRT, and audio metadata; and
- current OP approval after visual and listening review.

Confirmation creates a new local run, removes the `DRAFT_` filename prefix, and
copies verified artifacts without rerunning Word or speech. It does not authorize
LINE, upload, publication, deployment, or any other external write.
