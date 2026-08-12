# EasyTravel Briefing Materials

This isolated Windows application prepares reviewable travel briefing artifacts
from one NewAmazing URL, one local itinerary PDF, or both. It contains only the
`travel_briefing` package and briefing-specific scripts and configuration. The
supported render route uses LIST Word and Microsoft Yating; the package does not
ship a Hanhan execution script or expose Hanhan as a render choice.

Run `briefing doctor`, then use the installed `easytravel-briefing-materials`
Skill for the guarded `prepare -> check-script -> render -> confirm` workflow.
Every source decision is manifest-bound. Missing data, conflicts, unavailable
weather, template drift, Word QA failure, speech failure, or missing MP3 remains
review work and is never guessed or silently replaced.

Configuration is stored at
`%LOCALAPPDATA%\EasyTravelBriefing\config.toml`. Source PDFs, the private LIST
template, decision JSON, manifests, scripts, Word/PDF/PNG files, and audio remain
outside this application and must not be committed or uploaded.

The application never sends LINE messages, uses cloud speech, creates videos,
or performs external publication. A local `CONFIRMED` state is not distribution.
