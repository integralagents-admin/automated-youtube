---
name: youtube-pipeline
description: Process downloaded YouTube sources and record verified clips.
version: 0.3.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, Posting Schedule, Shorts, Longform Clips, Google Drive, Google Sheets]
    related_skills: [youtube-source-downloader, raw-video-processesor]
---

# YouTube Pipeline Skill

Run the local-source YouTube pipeline: select and download the newest unprocessed video from the rotating channel list, create verified Short and longform outputs, record those outputs in the Posting Schedule, and delete the local source only after every required verification passes. This workflow does not upload or schedule videos on YouTube.

The current processor is named `raw-video-processesor`; preserve that exact spelling.

## When to Use

- The user asks to run the end-to-end YouTube clipping pipeline.
- A fresh local source should be selected from configured YouTube channels.
- Verified Shorts and longform clips need to be added to the Posting Schedule.
- Do not use this skill to publish, schedule, or modify YouTube videos.

## Prerequisites

- `youtube-source-downloader`, `raw-video-processesor`, and their dependencies are available.
- Google OAuth credentials with YouTube, Drive, Sheets, and Docs access through the configured Hermes credential provider.
- `yt-dlp`, `ffmpeg`, and `ffprobe` are available.
- `source_tracking.spreadsheet_id` and `posting_schedule.spreadsheet_id` are resolved from private configuration or environment variables.
- All IDs, paths, sources, and tab names are read with `scripts/load_config.py`; never hard-code them in run commands.

## Procedure

1. **Select and download the source.** Run `youtube-source-downloader`. It rotates through `source_tracking.sources`, lists recent channel videos with `yt-dlp`, skips IDs already in the source-tracking sheet, downloads the newest eligible video to a dedicated local work directory, verifies it with `ffprobe`, appends its metadata to the source sheet, and reads the appended row back. Completion criterion: a verified `source_manifest.json` exists with the local path and source video ID.

2. **Process the local source.** Run `raw-video-processesor` against the source manifest. It applies `longform-to-shortfrom` and `longform-to-clipped-longform` to the same local file, verifies local renders, uploads outputs to Drive, and reads every upload back. Completion criterion: both workflows have successful verified manifests.

3. **Collect every verified clip.** Read both manifests and create `clips_to_schedule.json` containing each verified Short and longform clip exactly once. Preserve title, type, source video ID, Drive file ID, and Drive `webViewLink`. Completion criterion: collected count equals the sum of verified outputs in both manifests.

4. **Ensure the Posting Schedule schema.** Read `<TAB>!1:1` from the configured Posting Schedule. If empty, write `Title`, `Video Link`, `Video Type`, `Thumbnail Link`, and `Posted`; otherwise preserve existing columns and add only missing required columns. Completion criterion: every required column exists in its recorded position.

5. **Prepare rows.** Use transcript-grounded viewer-intent titles. Longform clips require one verified thumbnail link; Shorts may use a blank thumbnail value. Leave `Posted` blank for every row; only `youtube-scheduler` may write that column after verified YouTube scheduling. Each row must use the verified Drive clip link, never a local path or fabricated YouTube URL. Completion criterion: every verified clip maps to one complete row with an empty `Posted` cell.

6. **Append idempotently.** Read existing rows and deduplicate by `(Title, Video Link)`. Append only missing rows, preserve all existing values, and read the exact appended range back cell-by-cell. Treat omitted trailing empty cells as empty strings. Completion criterion: every intended row is present exactly once and no unrelated row changed.

7. **Close the source cleanup gate.** Write `combined_verification.json` with source, render, Drive, and Sheet evidence. Delete the local source only if all output and Sheet read-backs passed; otherwise preserve it for retry. Completion criterion: the source manifest records verified local deletion only after `deletion_eligible: true`.

8. **Report the batch.** Return the source title/ID, channel, verified Short count, verified longform count, source row status, Posting Schedule rows appended/skipped, spreadsheet link, and local cleanup status. Do not report YouTube publication status.

## Sheet contracts

### Source-tracking sheet

Configured under `source_tracking`; deduplication is by exact `Video ID`. The downloader appends source metadata after download and before clip processing.

### Posting Schedule

Configured under `posting_schedule` with the required columns:

```text
Title | Video Link | Video Type | Thumbnail Link | Posted
```

`Video Link` is always the verified Drive-rendered clip link. `Thumbnail Link` is a verified Drive thumbnail for longform clips or blank when not applicable.

## Safety and idempotency

- Never call `youtube.videos().insert`, YouTube scheduling APIs, or remote deletion APIs from this workflow.
- Never populate or modify `Posted`; that column belongs exclusively to `youtube-scheduler`.
- Never append a source row before local download verification.
- Never delete the local source before all clip and Sheet read-backs pass.
- Never overwrite existing Posting Schedule rows or clear existing dates.
- Preserve successful manifests if a later stage fails.
- Never fabricate IDs, links, titles, timestamps, or verification results.

## Verification checklist

- [ ] Source ID was absent from the tracking sheet before selection.
- [ ] Local source passed `ffprobe` and its metadata row was read back.
- [ ] Short and longform output counts reconcile with their manifests.
- [ ] Every Drive upload and thumbnail was read back.
- [ ] Posting Schedule uses the configured spreadsheet and exact rows were verified.
- [ ] Local source was deleted only after the combined success gate.
