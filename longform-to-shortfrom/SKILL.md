---
name: longform-to-shortfrom
description: Turn linked longform videos into standalone shortform clips.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Longform Video, Shorts, Video Editing, yt-dlp, Subtitles, Google Drive]
    related_skills: []
---

# Longform-to-Shortfrom Skill

Turn user-supplied video links into finished vertical clips for Operator Maxxing. Retrieve the source from Google Drive, YouTube, or another supported URL, transcribe it with ElevenLabs Scribe, use the running model to select genuinely standalone moments, render every selected moment in 9:16 with animated word-level subtitles, and upload the results to a per-video Google Drive folder inside one global Operator Maxxing folder.

## When to Use

- The user supplies one or more video links and asks for Shorts or shortform clips.
- The source is a long interview, podcast, webinar, lecture, or business video with reusable insights.
- Don't use for unrelated video editing, full-length uploads, or clips that require context from an unseen section.

## Prerequisites

- `yt-dlp` and `ffmpeg`/`ffprobe` available through `terminal`. Resolve the absolute path from `paths.yt_dlp_repo` (or `which yt-dlp`).
- The `video-use` repository installed and its `.venv` available. Resolve its absolute path from `paths.video_use_repo`; never hard-code a machine path.
- `ELEVENLABS_API_KEY` in the `video-use` `.env` or in the environment. Resolve the `.env` location from `transcription.elevenlabs_env_file` and the key name from `transcription.elevenlabs_env_key`. Never print the key.
- Optional owner-only Netscape cookies at a user-supplied path when YouTube requires authentication. Treat cookies as secrets; never commit, upload, or print them.
- Google OAuth token at `$HERMES_HOME/google_token.json` with Drive access. Check with the Google Workspace setup utility before the first Drive operation.
- A writable working directory supplied by the user or created from `paths.work_root_template` (default `operator-maxxing/{slug}`); never write outputs into the `video-use` source checkout.
- All Drive IDs, spreadsheet IDs, and folder names live in `~/.hermes/skills/media/automated-youtube/config.yaml`. Resolve them with `scripts/load_config.py`. Override any value per-run by setting `AUTOYT__<SECTION>__<KEY>` (see `scripts/README.md`).
- Required config keys before starting:
  - `drive.shortform_root_folder_name` (the global Drive folder for this skill's outputs)
  - `drive.queues_root_folder_id`
  - `paths.google_api_script`, `paths.video_use_repo`, `paths.yt_dlp_repo`
  - `paths.work_root_template`
  - `transcription.elevenlabs_env_file`, `transcription.elevenlabs_env_key`

## How to Run

Use `terminal` for downloads, probing, transcription helpers, rendering, and verification. Use `read_file` for transcripts and candidate manifests. Use the Google Workspace `google_api.py` wrapper through `terminal` for Drive search, folder creation, and uploads. Use the model directly for editorial analysis; do not delegate the central clip-selection judgment to a blind heuristic.

## Quick Reference

```bash
BUNDLE="$HERMES_HOME/skills/media/automated-youtube"
GAPI="python $($BUNDLE/scripts/load_config.py paths.google_api_script)"
VIDEO_USE_DIR="$($BUNDLE/scripts/load_config.py paths.video_use_repo)"

# Retrieve a source: use google_api.py for Drive links, yt-dlp for supported sites
terminal(command="$GAPI drive download '<FILE_ID>' --output '<work>/source.mp4'", timeout=1800)
terminal(command="yt-dlp --format 'bv*+ba/b' --merge-output-format mp4 --output '<work>/source.%(ext)s' '<VIDEO_URL>'", timeout=1800)

# Probe and transcribe
terminal(command="ffprobe -v error -show_format -show_streams '<work>/source.mp4'", timeout=120)
terminal(command="python '$VIDEO_USE_DIR/helpers/transcribe.py' '<work>/source.mp4' --edit-dir '<work>/edit'", timeout=1800)

# Pack the word-level transcript for model reading
terminal(command="python '$VIDEO_USE_DIR/helpers/pack_transcripts.py' --edit-dir '<work>/edit'", timeout=120)

# Inspect a rendered output
terminal(command="ffprobe -v error -show_entries format=duration:stream=width,height -of json '<work>/shorts/<clip>.mp4'", timeout=120)
```

## Procedure

1. **Normalize input and establish the work directory.** Accept the exact URLs the user supplied. Create a filesystem-safe video slug from title/ID, preserve the original URL in `manifest.json`, and keep all temporary files under that video’s work directory. Completion criterion: every input URL has a distinct work directory and no source file is overwritten.

2. **Retrieve from the supplied video link.** Detect Google Drive file links and extract the file ID, then use the authenticated Google Workspace Drive download command. For YouTube and other yt-dlp-supported links, use yt-dlp; for a direct media URL, use an authenticated HTTP download only when the user supplied access details. If the user supplied an owner-only Netscape cookie file, pass it with `--cookies <path>`; otherwise do not attempt to access browser cookies. Retain source metadata and the exact original link. Completion criterion: a playable local source exists and `ffprobe` reports at least one video and one audio stream.

3. **Transcribe once, verbatim, at word granularity.** Resolve the ElevenLabs key from the `video-use` `.env` or environment, then run `helpers/transcribe.py` with the video’s edit directory. Cache the JSON transcript and never retranscribe an unchanged source. If the key is missing, stop before paid transcription and tell the user exactly what is missing. Completion criterion: a cached transcript JSON contains word timestamps; no key is ever written into the work directory or logs.

4. **Read and analyze the transcript with the model.** Pack the transcript with `helpers/pack_transcripts.py`, then read the resulting file. Identify all plausible moments, not merely the first few. A candidate must:
   - make sense without relying on the rest of the video;
   - **start at the beginning of a new topic, idea, or claim, never mid-thought.** The first 1–2 spoken seconds must tell a viewer who has never heard the source what is being said and why it matters. If a viewer joining at second one would need to rewind or guess at a pronoun reference ("this", "that approach", "the strategy"), the cut is wrong — move the start forward to the next true topic boundary or reject the candidate.
   - start intentionally with a hook: a stated question, a clear topic introduction, a surprising claim, a tension, or a concrete problem;
   - begin on the first useful words of that hook, not on the preceding hesitation or setup noise;
   - contain a concrete business insight, tactic, mechanism, example, warning, or useful mental model;
   - **reveal all context the viewer needs during the clip itself.** Topic change → include the new topic's setup. Claim → include the claim's frame. Tactic → include the trigger that made it relevant. If the speaker references a previous claim, scenario, or audience that has not appeared yet in the clip, extend the start forward (even a few extra seconds) until the reference stands on its own.
   - end at a clean word boundary after the payoff, without cutting the explanation short;
   - reject openings that begin with pondering, pauses, “um,” “uh,” “well,” “so,” “I think,” “let me see,” throat-clearing, greetings, sponsor reads, vague teasers, or other filler while the speaker is still finding the point;
   - avoid unresolved references and context such as “as I said earlier” or “this is why I tell people to …” when the antecedent is unseen; if the answer needs setup, include the question or topic statement rather than the speaker’s pre-answer hesitation;
   - normally fit 20–90 seconds, while allowing a longer clip when the insight genuinely needs it.

   For every candidate, first locate the earliest clean hook words, then set `start` to that word boundary. Do not use a technically earlier timestamp if it includes thinking sounds or filler. Record `hook_type` (`question`, `topic_intro`, `claim`, `tension`, or `problem`), `opening_cut_note` explaining why the opening starts where it does, and `topic_anchor` capturing the one-sentence statement the clip leads with — this is the sentence a fresh viewer must hear within the first two seconds. Reject any candidate whose `topic_anchor` cannot be stated cleanly from the words at `start`. Record candidates in `candidates.json` as an exhaustive JSON array with `id`, `start`, `end`, `hook`, `hook_type`, `opening_cut_note`, `topic_anchor`, `insight`, `standalone_context`, `quote`, `why_it_works`, `confidence`, and `source_url`. Use exact word-boundary timestamps from the transcript and 30–200ms edge padding only after the clean hook has been selected. Completion criterion: each candidate starts with an intentional hook, contains no pre-hook pondering or filler, has a written standalone-context justification, and the list has been reviewed for missed high-value moments.

5. **Select and order the final set by opportunity quality.** Remove near-duplicates and candidates whose value depends on missing context. Make the set have range across business themes, problems, audiences, hooks, and insight types rather than repeating one winning format. Do not target, pad, or promise a fixed number of clips. Render as many opportunities as genuinely meet the editorial bar after the full source has been reviewed; render fewer when the source has fewer strong moments and render more when it has more. Keep rejected and borderline candidates in the manifest with reasons. **For a typical Operator Maxxing longform source, expect between 2 and 15 Shorts per run**, scaled by opportunity quality: a 20-minute source rarely produces more than a handful, while a 60+ minute source may legitimately produce ten or more. Never pad the set to hit a count; never truncate a strong set early. Apply the **topic-boundary gate** one more time before finalizing: for every selected candidate, read the words at `start` and ask, "If a viewer joined at this exact second with no prior context, would they understand the speaker's first sentence?" If the answer is no, push `start` forward to the next clean topic boundary, drop the candidate, or splice in the missing setup from earlier in the source — but never ship a clip whose first sentence assumes invisible context. Completion criterion: `selected.json` contains the complete quality-approved set, every selected clip has a distinct valuable angle, every opening word is anchored to a clean topic boundary, and no selected clip has an unresolved-context warning.

6. **Create the per-video Drive folder.** Resolve the global folder name from `drive.shortform_root_folder_name`. Use the Google Workspace `google_api.py` Drive search to find it under the parent `drive.queues_root_folder_id`. If absent, create it; this is an explicitly authorized operation for this skill. Search within it for a folder named `<YYYY-MM-DD> — <source title> — <video ID>`; create it if absent. Persist returned folder IDs in `drive.json` and verify each folder by reading it back. Completion criterion: the global folder and this run’s child folder both exist and their IDs are recorded.

7. **Render each selected clip with crop-first framing.** For every selected candidate, use the source timestamps and render a vertical 9:16 output (1080×1920 preferred; 720×1280 acceptable for preview). The default is a clean centered horizontal crop that fills the 9:16 frame and keeps the primary subject centered, without any blurred background extension. Use the Gaussian-blurred full-frame background only when a centered crop would cut off a required speaker, remove essential visual context, or materially damage the composition; invoke the renderer’s explicit blur-background fallback and record the reason in the verification manifest. Never stretch faces. For multi-speaker shots, crop only when every required speaker remains visible. Preserve intelligible audio and apply short audio fades at boundaries. Completion criterion: every selected candidate has a playable MP4 whose `ffprobe` dimensions are exactly 9:16, and a frame review confirms the primary subject is centered and no required speaker or context is lost.

8. **Build animated word-level subtitles.** Create an ASS subtitle track from the cached word timestamps offset to each clip’s output timeline. Use readable two-to-four-word chunks on exactly one visual line. Subtitle events must be strictly serialized: at most one event may be active at any timestamp, with each event ending before the next begins; never allow overlapping dialogue events. Position the single caption line with its visual center at the lower one-third mark of the frame (`y=1280` in a 1080×1920 frame, one-third of the frame height up from the bottom), not at the top. The current word must visibly pop slightly (for example, a brief 108–115% scale transform) and change to an accent color; inactive words remain white with a dark outline/shadow. Apply subtitles after crop, overlays, and all other video filters. Completion criterion: every spoken word in the selected interval is covered by a non-overlapping timed subtitle event, only one line is visible at a time, the caption center is at approximately `y=1280`, and a rendered frame check confirms the active word differs in scale/color while inactive words are white.

9. **Self-evaluate before upload.** Inspect the first, hook, middle, payoff, and final seconds of every clip with `timeline_view.py` or extracted frames. Check: standalone comprehension, hook clarity, no mid-word cuts, readable subtitles, active-word timing, no subtitle clipping, no face distortion, no audio pop, and correct duration/aspect ratio. Fix and re-render failures, up to three passes. Completion criterion: `verification.json` records pass/fail checks for every clip and no failed clip is uploaded.

10. **Upload and verify.** Upload each verified MP4 to the per-video Drive folder with a descriptive name such as `01 — Client Acquisition Without More Leads.mp4`. Also upload `candidates.json`, `selected.json`, and `verification.json` when useful for auditability. Use `google_api.py drive upload`, then read each returned file ID back with `drive get`. Completion criterion: every verified clip has a Drive file ID, parent folder matching this run, and a working `webViewLink`.

11. **Report the run.** Return the source title/URL, number of candidates, number rendered, number uploaded, Drive folder link, and any skipped candidates with reasons. Do not claim a clip was uploaded without a verified Drive file ID and link.

## Editorial Output Contract

The model’s candidate manifest must be valid JSON and use seconds as numbers:

```json
[
  {
    "id": "clip-01",
    "start": 412.38,
    "end": 468.91,
    "hook": "Why most agencies never escape founder-led sales",
    "hook_type": "question",
    "opening_cut_note": "Starts on the first clean question word; excludes the preceding hesitation.",
    "insight": "A concrete mechanism for replacing founder sales with a repeatable acquisition system.",
    "standalone_context": "The first two sentences define the problem before the recommendation.",
    "quote": "...",
    "why_it_works": "Curiosity-led opening, complete explanation, actionable payoff.",
    "confidence": 0.91,
    "source_url": "<exact user URL>"
  }
]
```

## Pitfalls

- Subtitle events must never overlap; overlapping ASS dialogue events can create doubled captions.
- Keep subtitles to one visual line at a time and place their center at `y=1280` for 1080×1920 output—the lower one-third mark, one-third of the frame height up from the bottom.
- Never target a fixed number of Shorts or pad the output with weak opportunities; the approved count is whatever survives the editorial review.
- Prefer range across business themes, problems, audiences, hooks, and insight types; avoid publishing near-duplicate clips.
- Never fabricate timestamps, quotes, or insights; all must map to the cached transcript.
- Never cut inside a word or remove the setup needed to understand the claim.
- **Never start a clip half-way through an idea that isn't obviously clear.** A clip must begin at a clean topic boundary — a new claim, a new tactic, a new question, a new example — so the first sentence a viewer hears is self-contained. If the speaker opens with "that's why," "this matters because," or any pronoun reference to unseen context, move `start` forward until the sentence stands on its own, or drop the candidate. A clip whose first two seconds would confuse a fresh viewer is rejected regardless of how strong the rest of the passage is.
- **Always reveal context inside the clip itself.** If a candidate relies on a scenario, audience, or earlier claim that has not yet been spoken, extend the start forward to include that setup. The "include the question before the answer" rule applies broadly: any reference the viewer needs to understand the payoff must land inside the clip's boundaries, not before them.
- Never start a clip while the speaker is pondering, prefacing, hesitating, or using filler before the subject is clear. Move the start forward to the first clean hook word, even if that makes the clip shorter.
- Hook quality is a selection gate, not a cosmetic edit: reject a valuable passage if no clean standalone opening can be found without awkwardly reconstructing context.
- Platform auto-captions may be used only as a fallback for discovery; use ElevenLabs word timestamps for final subtitles when available.
- Do not upload failed renders, previews, source videos, API keys, or temporary files.
- Do not request YouTube or Drive permissions again if the existing Hermes token is valid; check first.
- Keep the global folder stable across runs. Only the child folder is source-video-specific.
- If a source is unavailable, age-restricted, private, or has no usable audio, report the exact blocker and do not invent a result.

## Verification

Run these checks through `terminal` and record the results:

```bash
ffprobe -v error -show_entries stream=codec_type,width,height:format=duration -of json '<clip>.mp4'
python '<VIDEO_USE_DIR>/helpers/timeline_view.py' '<clip>.mp4' 0 3
```

The final report is valid only when every selected clip has: a transcript-backed EDL, a verified 9:16 MP4, subtitle timing/render evidence, a passing self-evaluation record, and a verified Google Drive file ID/link.
