# Per-batch file layout

What a finished interactive pipeline run leaves in the work directory, and what each file is for. A future session inspecting `~/.hermes/workspaces/automated-youtube/<slug>/` should be able to reconstruct the batch from these files alone.

## Root files

- `source.mp4` — the downloaded source video. Keep it locally until the source has been trashed on Drive; deleting it locally is fine once Drive trash is verified.
- `batch.json` — the per-batch metadata. Fields:
  - `source_id`, `source_name`, `source_modified_time`, `source_parent`
  - `today_utc` — the date used to name the per-source folders (UTC).
  - `shortform_folder_id`, `longform_folder_id`, `thumbnail_folder_id` — the three per-source child folders, each read back from Drive after creation.
  - `work_dir` — absolute path to this batch directory.
- `plan.md` — the editorial selection in human-readable form: per-clip title, type, source range, output filename. Produced before rendering.
- `selected.json` — Short-form candidates as a JSON array, schema documented in `longform-to-shortfrom/SKILL.md`.
- `longform_selected.json` — long-form candidates as a JSON object with a top-level `longform` array. Mirrors the schema documented in `longform-to-clipped-longform/SKILL.md`.
- `uploads.json` — final per-file upload results. Each entry includes the local path, target folder ID, final filename, returned Drive ID, `webViewLink`, and the `drive get` read-back fields (`readback_name`, `readback_parent`, `verified`).
- `verification.json` — per-clip self-evaluation results, if the session ran the gate.
- `combined_verification.json` — the gate's combined manifest, written by `raw-video-processesor` after both clip workflows succeed. Contains `deletion_eligible: true|false`.

## Per-format subdirectories

- `edit/` — the transcript workflow's outputs.
  - `edit/takes_packed.md` — phrase-level transcript the model reads.
  - `edit/transcripts/<source>.json` — the raw word-level JSON from ElevenLabs Scribe.
- `shorts/` — rendered Shorts.
  - `<id>.mp4` — the rendered 1080×1920 MP4 with subtitles baked in.
  - `<id>.ass` — the subtitle file (kept for audit; not uploaded by default).
- `clips/` — rendered longform clips.
  - `<NN> — <title>.mp4` — the rendered 1920×1080 (or source-aspect) MP4.
- `thumbnails/` — rendered longform thumbnails.
  - `<NN> — <title> — thumbnail.png` — the 1280×720 PNG with bottom gradient and one contrast-emphasized word.

## What to keep, what to clean

- Keep `batch.json`, `plan.md`, `selected.json`, `longform_selected.json`, `uploads.json`, `verification.json`, and `combined_verification.json`. They are the audit trail.
- Keep `edit/takes_packed.md` and `edit/transcripts/<source>.json` until the source has been trashed on Drive and the trash is verified — they are the only record of the transcript used to make the clips.
- Delete the rendered MP4s and the source MP4 after the source is trashed and uploads are verified. The Drive copies are the canonical assets from then on.

## Naming conventions

- Shorts filenames inside `shorts/` are `<id>.mp4` (e.g. `short-01.mp4`). Their uploaded name on Drive can be the human-friendly title (`01 — You Will Probably Make Exactly $0.mp4`).
- Longform filenames inside `clips/` use the leading zero-padded index (`01 —`, `02 —`, `03 —`) followed by the human-friendly title. The same name is used on Drive.
- Thumbnail filenames mirror the longform: `<NN> — <title> — thumbnail.png`.
- Per-source Drive child folders are named `<YYYY-MM-DD> — <source title> — <source file ID>` and live under the global Shorts / Longform / Thumbnails root folders.