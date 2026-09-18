---
name: longform-to-clipped-longform
description: Turn linked videos into useful 2–15 minute topic clips.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Longform Video, Topic Clips, Video Editing, yt-dlp, Google Drive]
    related_skills: []
---

# Longform-to-Clipped-Longform Skill

Turn a user-supplied video link into useful 2–15 minute clips for Operator Maxxing. Retrieve the source from Google Drive, YouTube, or another supported URL, transcribe it with ElevenLabs Scribe, use the model to find coherent topic sections with useful or insightful information, render each section, and upload the verified clips to a source-specific child folder inside the fixed Google Drive longform-clips folder.

## When to Use

- The user supplies a link to a longform video and wants topic-focused clips.
- The desired outputs are longer clips, normally 2–15 minutes, rather than Shorts.
- Don't use for isolated one-line highlights, full-video reposts, or clips without a coherent topic.

## Prerequisites

- `yt-dlp`, `ffmpeg`, and `ffprobe` available through `terminal`. Resolve `yt-dlp`'s absolute path from `paths.yt_dlp_repo` (or `which yt-dlp`).
- The installed `video-use` repository and its Python environment. Resolve its absolute path from `paths.video_use_repo`.
- `ELEVENLABS_API_KEY` in the `video-use` `.env` or environment; resolve the path from `transcription.elevenlabs_env_file` and the key name from `transcription.elevenlabs_env_key`. Never print the key.
- Google OAuth token at `$HERMES_HOME/google_token.json` with Drive access.
- All Drive IDs, spreadsheet IDs, and folder names live in `~/.hermes/skills/media/automated-youtube/config.yaml`. Resolve them with `scripts/load_config.py`. Override any value per-run by setting `AUTOYT__<SECTION>__<KEY>` (see `scripts/README.md`).
- Required config keys before starting:
  - `drive.longform_clips_parent_folder_id` (the stable parent for all uploads)
  - `drive.queues_root_folder_id`
  - `paths.google_api_script`, `paths.video_use_repo`, `paths.yt_dlp_repo`
  - `paths.work_root_template`
  - `transcription.elevenlabs_env_file`, `transcription.elevenlabs_env_key`
- A writable work directory outside the `video-use` checkout.

## How to Run

Use `terminal` for retrieval, probing, transcription, and rendering. Use `read_file` for packed transcripts and manifests. Use the model directly for topic segmentation and editorial judgment. Use the Google Workspace `google_api.py` wrapper through `terminal` for Drive downloads, uploads, and read-back verification.

## Quick Reference

```bash
# Resolve bundle paths and the google_api script path once.
BUNDLE="$HERMES_HOME/skills/media/automated-youtube"
GAPI="python $($BUNDLE/scripts/load_config.py paths.google_api_script)"
VIDEO_USE_DIR="$($BUNDLE/scripts/load_config.py paths.video_use_repo)"

# Google Drive source
terminal(command="$GAPI drive download '<FILE_ID>' --output '<work>/source.mp4'", timeout=1800)

# Other supported sources
terminal(command="yt-dlp --format 'bv*+ba/b' --merge-output-format mp4 --output '<work>/source.%(ext)s' '<VIDEO_URL>'", timeout=1800)

# Transcript
terminal(command="python '$VIDEO_USE_DIR/helpers/transcribe.py' '<work>/source.mp4' --edit-dir '<work>/edit'", timeout=1800)
terminal(command="python '$VIDEO_USE_DIR/helpers/pack_transcripts.py' --edit-dir '<work>/edit'", timeout=120)

# Accurate section render
terminal(command="ffmpeg -y -ss '<start>' -i '<work>/source.mp4' -t '<duration>' -c:v libx264 -c:a aac '<work>/clips/<clip>.mp4'", timeout=1800)

# Upload to the source-specific child folder created during the run
terminal(command="$GAPI drive upload '<clip>.mp4' --parent '<CHILD_FOLDER_ID>'", timeout=1800)
```

## Procedure

1. **Normalize the link and work directory.** Preserve the exact user link in `manifest.json`, derive a safe source slug, and keep source, transcript, clips, and manifests together outside the skill checkout. Completion criterion: the source link and work directory are recorded before retrieval.

2. **Retrieve the source.** For a Google Drive link, extract the file ID and use the authenticated Drive download command. For YouTube or another yt-dlp-supported URL, use yt-dlp. For a direct media URL, download only when access is public or the user supplied credentials. Optional owner-only cookie files may be passed explicitly to yt-dlp; never access browser cookies silently. Completion criterion: `ffprobe` reports a playable video and audio stream, and the local source size is nonzero.

3. **Transcribe once at word granularity.** Use ElevenLabs Scribe through the installed `video-use` helper, cache the JSON transcript, and pack it for model reading. Never retranscribe an unchanged source. Completion criterion: the cached transcript contains word timestamps and the packed transcript has been written.

4. **Map the topic structure.** Read the packed transcript and segment the entire source into topic blocks. Identify sections that answer a question, teach a framework, explain a tactic, compare options, describe a mechanism, or deliver a useful story with a clear lesson. Do not select sections solely because they contain a punchline.

5. **Select clippable sections by opportunity quality.** Prefer sections between 2 and 15 minutes with one dominant topic or a tightly related set of topics. Seek range across the source: different business themes, problems, audiences, frameworks, examples, and insight types. Do not target, pad, or promise a fixed number of clips. Render as many sections as genuinely meet the editorial bar after the entire source has been reviewed; render fewer when only a few sections are strong and render more when the source supports more distinct valuable sections. **For a typical Operator Maxxing longform source, expect between 2 and 15 longform clips per run**, scaled by opportunity quality: a focused 30-minute source usually yields 2–3, while a chaptered 60+ minute source may yield 5 or more. Never pad to a count; never truncate a strong set early. The ideal opening is, in order of preference, a stated question, clear topic introduction, surprising claim, tension, or concrete problem. Unlike the shortform workflow, lack of a strong hook is not disqualifying when the section is coherent and valuable: start at the earliest point that preserves understanding, even if it begins with a brief transition. Never begin with extended pondering, dead air, or filler when a clean topic start is available. End after the explanation, example, framework, or conclusion is complete; do not cut immediately after the first claim.

   Record every plausible section in `candidates.json` with `id`, `start`, `end`, `duration_seconds`, `topic`, `opening_type`, `opening_cut_note`, `summary`, `key_insight`, `standalone_context`, `quote`, `why_it_works`, `confidence`, and `source_url`. Use exact word-boundary timestamps and preserve enough setup. Keep rejected and borderline sections in the manifest with rejection reasons. Completion criterion: the final selected set contains only distinct quality-approved sections between 120–900 seconds, has useful topical range, and includes a written value and context justification for each selection.

6. **Render each section.** Extract each selected range into its own MP4 with accurate start and end points. Preserve the source’s native aspect ratio and resolution unless the user requests a different format. Do not stretch or crop away meaningful visual information. Apply audio encoding suitable for playback and use short fades only when an edit boundary would otherwise pop. Completion criterion: every candidate has a playable local MP4 with duration within one second of its target range.

7. **Self-evaluate.** Check the first 30 seconds, one midpoint, and final 30 seconds of every clip. Confirm the topic is clear, the section is not a random excerpt, the information is useful, and the ending resolves naturally. Check for mid-word cuts, dead air, accidental topic changes, audio pops, and corrupted frames. Fix and re-render up to three times. Completion criterion: `verification.json` records a pass for every rendered clip.

8. **Create the source-specific Drive folder and upload.** Resolve the stable parent ID from `drive.longform_clips_parent_folder_id` and never upload clips directly into it. Search for a child folder named `<YYYY-MM-DD> — <source title> — <source ID or slug>`; create it if absent, persist its ID in `drive.json`, and read it back to verify its parent is the configured longform-clips folder. Upload every verified clip to that child folder with names such as `01 — Demand vs Supply Constraints.mp4`. Upload `candidates.json` and `verification.json` into the same child folder when useful for auditability. Read every returned file ID back with `drive get` and confirm its parent folder, name, MIME type, and nonzero size. Completion criterion: the source-specific child folder exists under the configured parent and every verified clip has a confirmed Drive file ID and link inside that child folder.

9. **Report the completed run.** State the source, candidate count, rendered count, uploaded count, skipped sections and reasons, and the Drive links. Never claim completion from an upload response alone; use the read-back records.

## Editorial Output Contract

The candidate manifest is valid JSON with seconds as numbers:

```json
[
  {
    "id": "section-01",
    "start": 145.03,
    "end": 455.24,
    "duration_seconds": 310.21,
    "topic": "How to make livestream content perform after the live ends",
    "opening_type": "topic_intro",
    "opening_cut_note": "Starts on the clean topic introduction and excludes the preceding transition.",
    "summary": "A practical set of livestream packaging, promotion, scheduling, and post-production lessons.",
    "key_insight": "Treat the livestream like a normal video and keep value per second high.",
    "standalone_context": "The speaker explicitly introduces the lessons from the livestream experiment before listing them.",
    "quote": "You still want to treat it like a regular YouTube video.",
    "why_it_works": "Coherent topic, practical examples, and a complete beginning-to-end explanation.",
    "confidence": 0.94,
    "source_url": "<exact user link>"
  }
]
```

## Pitfalls

- Do not force every section to have a dramatic hook; coherent value is sufficient for longform clips.
- Do not keep an awkward pondering opening when a clean topic start exists.
- Do not cut a section below two minutes merely to create a tighter edit; merge adjacent phrases from the same topic or reject it.
- Do not combine unrelated Q&A answers just to reach the minimum duration.
- Never target a fixed number of longform clips or pad the output with weak sections; the approved count is whatever survives the editorial review.
- Prefer range across business themes, problems, audiences, frameworks, examples, and insight types; avoid publishing near-duplicate sections.
- Never fabricate timestamps, quotes, summaries, or insights; map each to transcript words.
- Never cut inside a word or end before the explanation resolves.
- Do not upload source videos, failed renders, API keys, cookies, or temporary files.
- Do not claim a Drive upload succeeded without reading the exact file back.

## Verification

Run these checks through `terminal`:

```bash
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height:format=duration -of json '<clip>.mp4'
```

Every uploaded clip must have valid audio/video streams, a duration between 120 and 900 seconds, a coherent topic manifest entry, a passing verification record, and a Drive read-back record whose parent is the source-specific child folder. The child folder must itself be verified as a child of `drive.longform_clips_parent_folder_id`; clips must not be uploaded directly to the configured parent.
