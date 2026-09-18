---
name: raw-video-processesor
description: Process the oldest queued video through both clip workflows.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Video Processing, Drive Queue, Shorts, Longform Clips, Automation]
    related_skills: []
---

# Raw-Video-Processesor Skill

Process the oldest video waiting in the configured Google Drive queue for Operator Maxxing. Download it, run the current shortform workflow (`longform-to-shortfrom`, the skill formerly named `longform-to-shortform`) and `longform-to-clipped-longform`, verify both completed successfully, and only then move the original Drive file to trash. Never delete or trash the source when either workflow fails or verification is incomplete.

## When to Use

- The user asks to process the oldest queued video in the configured Drive folder.
- The queue folder contains raw longform video files awaiting both shortform and longer topic-clip production.
- Don't use for a specific manually selected video, permanent deletion, or processing only one output format.

## Prerequisites

- Google OAuth token at `$HERMES_HOME/google_token.json` with Drive access.
- Google Workspace `google_api.py` available through `terminal`. Resolve its absolute path from `paths.google_api_script`.
- The skills `longform-to-shortfrom` and `longform-to-clipped-longform` available in the active profile.
- `yt-dlp`, `ffmpeg`, `ffprobe`, and the installed `video-use` environment. Resolve absolute paths from `paths.yt_dlp_repo` and `paths.video_use_repo`.
- `ELEVENLABS_API_KEY` in the `video-use` `.env` or environment; resolve the path from `transcription.elevenlabs_env_file` and the key name from `transcription.elevenlabs_env_key`. Never print it.
- All Drive IDs, spreadsheet IDs, and folder names live in `~/.hermes/skills/media/automated-youtube/config.yaml`. Resolve them with `scripts/load_config.py`. Override any value per-run by setting `AUTOYT__<SECTION>__<KEY>` (see `scripts/README.md`).
- Required config keys before starting:
  - `drive.source_queue_folder_id` (the queue this processor polls)
  - `drive.longform_clips_parent_folder_id`
  - `paths.google_api_script`, `paths.video_use_repo`, `paths.yt_dlp_repo`

## How to Run

Use `terminal` for Drive listing/download, media processing, probing, and Drive deletion. Use `read_file` for manifests and verification records. Follow both source skills’ procedures exactly. Use Drive trash rather than permanent deletion so the operation remains reversible.

## Quick Reference

```bash
# List oldest video candidate
BUNDLE="$HERMES_HOME/skills/media/automated-youtube"
GAPI="python $($BUNDLE/scripts/load_config.py paths.google_api_script)"
QUEUE_ID="$($BUNDLE/scripts/load_config.py drive.source_queue_folder_id)"

terminal(command="$GAPI drive search \"'$QUEUE_ID' in parents and mimeType contains 'video/' and trashed = false\" --raw-query --max 100", timeout=120)

# Download selected Drive file
terminal(command="$GAPI drive download '<FILE_ID>' --output '<work>/source.mp4'", timeout=1800)

# Trash only after both workflows pass
terminal(command="$GAPI drive delete '<FILE_ID>'", timeout=120)
```

## Procedure

1. **Check prerequisites and queue state.** Confirm Drive authentication and that both current skills are available. Resolve the queue folder ID from `drive.source_queue_folder_id`. Query only non-trashed video files whose parent matches that ID and select the file with the oldest `modifiedTime`; the standard `drive search` listing returns `modifiedTime` but not `createdTime`, and `createdTime` filtering requires an additional request per file. Record the selected file's `modifiedTime`, `createdTime` (if available), name, MIME type, and parent in `queue_manifest.json`. Completion criterion: exactly one source file is selected with its ID, name, MIME type, parent, and timestamp recorded in `queue_manifest.json`.

2. **Download without changing the queue.** Read the selected file metadata, download it into a dedicated work directory, and verify the local file with `ffprobe`. Do not trash, rename, or modify the Drive source during this step. Completion criterion: the local source is playable, has audio and video streams, and the downloaded byte count is nonzero.

3. **Run the shortform workflow.** Apply the current skill named `longform-to-shortfrom` (the prior `longform-to-shortform` skill was renamed with that exact spelling). Analyze the transcript for standalone, hook-first Shorts, render the selected clips with the required vertical subtitle treatment, upload them to the Shorts Drive structure, and produce a machine-readable result manifest. Completion criterion: the shortform workflow reports success, every selected clip passes its own verification, and every claimed upload has a verified Drive file ID and link.

4. **Run the clipped-longform workflow.** Apply `longform-to-clipped-longform` to the same local source and transcript. Identify coherent 2–15 minute topic sections, create or reuse a source-specific child folder beneath the parent resolved from `drive.longform_clips_parent_folder_id`, render the sections, upload them there, and verify each upload. Completion criterion: the clipped-longform workflow reports success, the child folder is verified under the configured parent, and every claimed upload has a verified Drive file ID and link inside that child folder.

5. **Perform a combined success gate.** Write `combined_verification.json` containing the source file ID, source metadata, both workflow result manifests, counts of rendered and verified outputs, and all Drive IDs/links. Require all of the following before deletion: both workflows exited successfully; both produced at least one verified output or explicitly documented a valid zero-output result; no required verification check failed; all uploads were read back; and no output is merely a local or unverified artifact. Completion criterion: `combined_verification.json` has `deletion_eligible: true` and records no failures.

6. **Trash the original source only after the gate.** Use the reversible Drive delete/trash operation on the exact selected file ID. Do not use `--permanent`. Then read the file back and verify it is either `trashed: true` or absent from the non-trashed queue query. Completion criterion: the exact source file no longer appears as an active child of `drive.source_queue_folder_id` and its deletion response/read-back is recorded.

7. **Stop safely on any failure.** If downloading, transcription, either workflow, upload verification, or the combined success gate fails, do not trash the source. Record the failure, preserve the work directory for diagnosis, and report the source ID and exact failing stage. Completion criterion: every non-deletion run ends with `deletion_eligible: false` and the source remains active in the queue.

## Failure and Idempotency Rules

- Select by exact Drive file ID, never by a mutable filename at deletion time.
- Re-read metadata immediately before deletion and confirm the ID, name, and original queue parent still match `queue_manifest.json`.
- If the source has already been trashed or moved, stop; do not delete another file to compensate.
- If a prior run produced verified outputs but did not delete the source, do not blindly duplicate uploads. Inspect its manifests and either resume the missing stage or ask for direction.
- “Workflow ran” is not success: require output verification and Drive read-back records.
- Never permanently delete the source, output clips, manifests, or folders.

## Verification

The final report is valid only when it includes:

- The selected source file ID and original queue parent.
- Shortform workflow success and verified output count.
- Clipped-longform workflow success, child-folder ID, and verified output count.
- `combined_verification.json` with `deletion_eligible: true`.
- Drive read-back evidence that the exact source file is trashed and no longer active in the queue.
