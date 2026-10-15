---
name: youtube-source-downloader
description: Select and download the newest unprocessed video from rotating YouTube channels.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, yt-dlp, source intake, Sheets, deduplication]
    related_skills: [youtube-pipeline, raw-video-processesor]
---

# YouTube Source Downloader

Select the next source video from a rotating array of YouTube channel pages, skip every video ID already recorded in the source-tracking spreadsheet, download the newest eligible video with `yt-dlp`, and append its metadata only after the local download succeeds. This skill supplies the local source to `youtube-pipeline`; it does not upload, publish, or schedule the source on YouTube.

## Current configuration

The bundle configuration is the source of truth. The initial array is:

```python
SOURCES = ["https://www.youtube.com/@DroppingInPodcast/videos"]
```

The source-tracking spreadsheet is configured under `source_tracking` in `config.yaml`, and the Posting Schedule is configured separately under `posting_schedule`. Do not hard-code either spreadsheet ID in workflow commands. Add future channels to `source_tracking.sources`; the rotation state advances only after a successful source selection/download record.

## When to Use

- A pipeline run needs a fresh local YouTube source instead of a Drive queue item.
- A source must be deduplicated by YouTube video ID against the source-tracking sheet.
- A new channel should be added to the rotation without changing the processing workflow.
- Do not use this skill to upload or publish videos, modify existing YouTube videos, or delete remote source videos.

## Prerequisites

- `$HERMES_HOME/google_token.json` with YouTube, Drive/Sheets access.
- `yt-dlp` and `ffprobe` available on `PATH`, or the bundle's configured yt-dlp checkout available.
- `ffmpeg` available for yt-dlp post-processing when the selected format requires merging.
- `source_tracking.spreadsheet_id`, `.tab_name`, `.required_columns`, `.sources`, and `.rotation_state_file` resolve through `scripts/load_config.py`.
- A per-run local work directory under `paths.work_root`.

## Procedure

1. **Load configuration and state.** Resolve the source-tracking sheet, channel array, candidate limit, and rotation state file. Read the rotation index; if it is missing or invalid, start at index zero. Completion criterion: the run records the ordered source list and starting index in its manifest.

2. **Read the tracking sheet.** Read the configured tab's existing values, locate the `Video ID` column by header, and build a set of recorded IDs. If the sheet is empty, treat the required headers as the schema to initialize after the first successful download. Do not infer deduplication from title, URL, or filename.

3. **Rotate channel candidates.** Visit channels in cyclic order beginning at the saved index. For each channel, use `yt-dlp --flat-playlist --dump-single-json --skip-download --playlist-end <candidate_limit> <channel-url>` and normalize each entry to its canonical 11-character YouTube ID, watch URL, title, channel, and published timestamp. Sort candidates by published timestamp descending and choose the first ID absent from the tracking set. Continue to the next channel if a channel has no eligible candidate. Completion criterion: exactly one unrecorded video ID is selected, with source metadata captured in `source_manifest.json`.

4. **Download locally.** Download the canonical watch URL with `yt-dlp --no-playlist --merge-output-format mp4` into the run's dedicated work directory. Never use browser cookies silently. Run `ffprobe` and require a nonzero playable file containing both video and audio streams. Completion criterion: `source_manifest.json` contains the final local path, byte size, duration, video/audio stream evidence, and the selected video ID.

5. **Record after download.** Append one row to the source-tracking sheet only after local verification succeeds. Write only the first four columns: `Video ID`, canonical `Source URL`, channel, and title. Keep published time, UTC download time, absolute local path, status, probe evidence, and other operational metadata in `source_manifest.json`; never append those fields to the spreadsheet. Read the appended A:D range back and compare each cell; if the write or read-back fails, preserve the local source and mark the run as `recording_failed` rather than proceeding silently. Completion criterion: the exact video ID is present in the sheet with a verified four-column row.

6. **Advance rotation state.** Persist the next channel index only after the download and sheet read-back succeed. A failed channel inspection, download, or sheet write must not advance the index. Completion criterion: the state file records the next index and the selected video ID.

7. **Hand off to the pipeline.** Invoke `raw-video-processesor`/`youtube-pipeline` with the local source manifest. The clipping workflows must use the downloaded local path and retain their existing local verification, Drive upload, thumbnail, and Posting Schedule read-back rules. Completion criterion: both Short and longform workflows produce their verified manifests and the Posting Schedule uses the privately configured spreadsheet.

8. **Delete the local source only after processing succeeds.** Require both clip workflows, all Drive read-backs, and the Posting Schedule verification to pass. Then delete only the exact local source path recorded in `source_manifest.json`, verify it is absent, and retain the manifest with `local_source_deleted: true`. If any stage fails, preserve the local source and report its path for retry/diagnosis.

## Script

The bundled helper implements selection, download, Sheet append, and read-back:

```bash
BUNDLE="$HERMES_HOME/skills/media/automated-youtube"
WORK="$($BUNDLE/scripts/load_config.py paths.work_root)/$(date -u +%Y%m%dT%H%M%SZ)-source"
mkdir -p "$WORK"

$BUNDLE/youtube-source-downloader/scripts/select_and_download.py \
  --work-dir "$WORK"
```

The helper does not delete the downloaded source. Deletion belongs to the post-processing success gate above.

## Sheet contract

Required source-tracking columns written by this workflow:

```text
Video ID | Source URL | Channel | Title
```

The sheet may contain additional legacy columns after column D, but this workflow must leave them untouched and must never write values into them.

The source sheet is an intake ledger, not the Posting Schedule. Never append clip rows to it. Clip rows go only to `posting_schedule.spreadsheet_id` after the current pipeline verifies Drive outputs.

## Failure and idempotency rules

- Deduplicate only by exact YouTube video ID.
- Never append a source row before the local file passes `ffprobe`.
- Never advance rotation state after a failed download or unverified Sheet write.
- Preserve the local file after any downstream failure so the pipeline can resume without downloading a different source.
- Never delete a local source before both clip workflows and all external read-backs pass.
- Never fabricate timestamps, titles, IDs, Drive links, or YouTube links.
- Never use permanent remote deletion or YouTube upload APIs in this skill.

## Verification checklist

- [ ] Candidate list was fetched from the configured channel rotation.
- [ ] Selected ID was absent from the source-tracking sheet before download.
- [ ] Downloaded file is playable with video and audio streams.
- [ ] Only columns A:D were appended and read back exactly; operational metadata remains in `source_manifest.json`.
- [ ] Rotation state advanced only after recording succeeded.
- [ ] Both clip workflows and Posting Schedule writes were verified before local deletion.
- [ ] Local source deletion was limited to the recorded path and verified.
