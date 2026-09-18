---
name: youtube-scheduler
description: Schedule unposted sheet videos one hour apart.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, Scheduling, Google Sheets, Google Drive]
    related_skills: []
---

# YouTube Scheduler Skill

Read the Operator Maxxing Posting Schedule sheet, select the first eight rows whose `Posted` cell is empty, upload and schedule those Drive-hosted videos on YouTube, verify each scheduled resource, and write the scheduled date as `MM/DD` into the corresponding `Posted` cell. This skill publishes to YouTube; it is separate from the clip-production pipeline that only records Drive links in the sheet.

## When to Use

- The user asks to schedule or publish the next unposted videos from the Posting Schedule sheet.
- The sheet contains verified Drive video links and a `Posted` column.
- Do not use for processing raw source videos, generating clips, or changing already marked rows.

## Prerequisites

- Google OAuth token at `$HERMES_HOME/google_token.json` with Drive, Sheets, and YouTube upload scopes.
- YouTube Data API v3 enabled for the active Google Cloud project.
- All Drive IDs, spreadsheet IDs, and folder names live in `~/.hermes/skills/media/automated-youtube/config.yaml`. Resolve them with `scripts/load_config.py`. Override any value per-run by setting `AUTOYT__<SECTION>__<KEY>` (see `scripts/README.md`). Never hard-code IDs from a previous run.
- Required config keys before starting:
  - `posting_schedule.spreadsheet_id`, `.spreadsheet_url`, `.tab_name`
  - `posting_schedule.required_columns` (must include `Title`, `Video Link`, `Video Type`, `Thumbnail Link`, `Posted`)
  - `youtube.default_category_id`, `.default_privacy_status`
  - `youtube.first_clip_offset_minutes` (default `20`)
  - `youtube.later_clip_spacing_minutes` (default `60`)
  - `youtube.max_rows_per_run` (default `8`)
  - `youtube.time_zone` (default `UTC`)
  - `paths.google_api_script`
- Each `Video Link` must be a verified Drive URL for a playable MP4.
- **Every row is expected to have a verified thumbnail on YouTube.** When the row's `Thumbnail Link` cell contains a verified Drive image URL, the scheduler downloads that image and sets it as the video's `thumbnails.default` via `videos().update(snippet.thumbnails)`. When the cell is empty (which is normal for Shorts in the current pipeline), the scheduler falls back to a generated thumbnail: a single frame captured from the source video at `youtube.thumbnail_fallback_offset_seconds` (default `3`) and rendered through `longform-thumbnail-analysis` style typography — Comic Relief Bold 700, lower-third caption over a dark gradient, one emphasized word. Every YouTube video leaves this run with a visible thumbnail; never upload a video without one.

## How to Run

Use `terminal` with an authenticated Python client using `googleapiclient`, `MediaFileUpload`, and the Google Sheets API. Read the complete sheet range before selecting rows. Download each selected Drive video to a temporary work directory or use an existing verified local path. Use `youtube.videos().insert(part='snippet,status')` for resumable uploads and `youtube.videos().list(part='snippet,status', id=...)` for read-back verification. Use Sheets `values.update` only after the corresponding YouTube read-back passes.

## Procedure

1. **Read and validate the sheet schema.** Read `<TAB>!A:Z` using `posting_schedule.tab_name`, locate headers by name rather than assuming fixed positions, and confirm that every entry of `posting_schedule.required_columns` exists. Add a missing `Posted` header only if it is absent; never overwrite an existing header or row. Completion criterion: column indexes are recorded and all data rows can be addressed by row number.

2. **Select up to `youtube.max_rows_per_run` eligible rows.** Scan data rows from top to bottom. Select up to the configured maximum number of rows where `Posted` is empty and `Title`, `Video Link`, and `Video Type` are nonempty. Preserve sheet order. Do not select rows already marked, even if their YouTube upload cannot be found without a separate reconciliation request. Completion criterion: the selected row numbers and exact source values are stored in a run manifest.

3. **Capture one baseline in `youtube.time_zone`.** Capture the runtime instant once immediately before scheduling. Assign the first selected video `publishAt = baseline + youtube.first_clip_offset_minutes`; assign each subsequent selected video exactly `youtube.later_clip_spacing_minutes` after the previous selected video. Use `Z` timestamps derived from `youtube.time_zone` and preserve the baseline and schedule in `youtube_scheduler_manifest.json`. If fewer than the configured maximum rows are eligible, schedule only the available rows and report the count.

4. **Resolve and validate each Drive source.** Extract the Drive file ID from each `Video Link`, read its metadata, and verify it is non-trashed, has the expected parent or an accessible Drive location, and is a playable video. Download it if no verified local path is available. Completion criterion: every selected row has a verified local MP4 before its upload is attempted.

5. **Resolve and validate each thumbnail.** Extract the Drive file ID from `Thumbnail Link` when present. Read its metadata and verify it is non-trashed, an image (`mimeType` starts with `image/`), and at least 1280px on the long edge. Download it for upload. When the cell is empty, capture a single frame from the downloaded source video at `youtube.thumbnail_fallback_offset_seconds` (default `3`) using `ffmpeg`, then run **`scripts/render_thumbnail.py`** at the bundle root — it applies the same Comic Relief Bold + bottom-gradient + emphasis-word treatment used by `longform-thumbnail-analysis`. Pick one emphasis word from the title (the longest alphabetic word; never the whole title, which would highlight everything). Persist the rendered image as `<batch-slug>/<row>-<title-slug>-thumbnail.png` in `drive.thumbnails_root_folder_name`. Completion criterion: every row has a verified local image before its YouTube upload begins.

5a. **Prepare upload metadata.** Use the sheet `Title` exactly as the YouTube title unless it exceeds the platform limit, in which case shorten it without changing the claim and record the final title. Set `categoryId` to `youtube.default_category_id`. Set `privacyStatus` to `youtube.default_privacy_status`, set the exact future `publishAt`, and set `selfDeclaredMadeForKids` to `false`. Use the sheet `Video Type` to select appropriate metadata, but do not invent claims or descriptions unsupported by the row and source.

6. **Upload sequentially and verify.** Upload each selected video with resumable media upload. Immediately call `videos.list` and verify resource existence, channel ownership, final title, `privacyStatus: private`, and exact `publishAt`. A successful `videos.insert` response without matching read-back is not success. Then set the thumbnail with **`youtube.thumbnails().set(videoId=<ID>, media_body=MediaFileUpload(thumb_path, mimetype='image/png'))`** — this is the cleanest API for replacing a YouTube thumbnail; `videos().update(part='snippet', ...)` will silently ignore an inline `media_body` and leave the existing thumbnail in place. Re-read with `videos.list(part='snippet,status')` and accept the result when `snippet.thumbnails.default` (or any of `medium`/`high`/`standard`/`maxres`) is populated — the very first read-back after `set()` often only has `default`/`medium`/`high` and the higher resolutions arrive a beat later. **Never claim success without at least one `thumbnail_keys` entry; that is the failure signal that means no thumbnail is attached.** Record the video ID, watch URL, schedule, thumbnail source (`sheet_cell` / `generated_fallback`), thumbnail asset ID, thumbnail_keys, and read-back result in the manifest. Completion criterion: each successful row has a verified YouTube ID, an attached verified thumbnail, and the exact schedule.

7. **Write the scheduled date after verification.** Only after a video’s YouTube read-back passes, write the scheduled date in `MM/DD` format into that row’s `Posted` column. Use the date of the scheduled `publishAt` interpreted in `youtube.time_zone`. Read the exact cell back and verify it equals the intended `MM/DD`. Never mark a row before the corresponding upload is verified. Completion criterion: every row marked in `Posted` has a verified scheduled YouTube resource.

8. **Handle failures idempotently.** If an upload fails, leave its `Posted` cell empty, record the exact error, and continue only if the next upload can be safely assigned the next schedule slot according to the run policy. Do not retry a verified upload or create duplicates. If a failure makes the schedule ambiguous, stop and preserve the manifest for a later retry. Completion criterion: the manifest distinguishes `verified`, `failed`, and `not_attempted`, and sheet write-backs exist only for verified uploads.

9. **Verify the final state.** Re-read the selected rows from Sheets and every verified YouTube ID from the API. Confirm that each successful row’s `Posted` value matches the UTC scheduled date and that no unselected row changed. Completion criterion: the manifest totals match the read-back totals and all external writes are verified.

## Sheet Contract

```text
Title | Video Link | Video Type | Thumbnail Link | Posted
```

`Thumbnail Link` may be empty for Shorts (the scheduler falls back to a generated frame and writes the resulting image to the run's thumbnail folder, then attaches it to the YouTube video). For longform rows, the cell normally points to a verified Drive image rendered by `longform-thumbnail-analysis`; the scheduler downloads that image and sets it as `thumbnails.default` on YouTube. `Posted` is blank for unscheduled rows and contains only the scheduled UTC date formatted as `MM/DD` after YouTube verification. It must never contain a date for an upload that failed or was not read back.

## Scheduling Rules

- Select at most `youtube.max_rows_per_run` eligible rows in sheet order.
- First selected video: exactly baseline plus `youtube.first_clip_offset_minutes`.
- Each later selected video: exactly `youtube.later_clip_spacing_minutes` after the previous one.
- Use `Z` timestamps derived from `youtube.time_zone` for YouTube `publishAt`.
- Write only the scheduled date portion as `MM/DD`.
- The date is derived from the scheduled `publishAt`, not the upload time.
- Do not reschedule rows already marked in `Posted`.

## Idempotency and Safety

- Read the sheet before every run and skip nonempty `Posted` cells.
- Preserve the exact sheet row number for every selected video.
- Never write `Posted` before YouTube read-back verification.
- Never overwrite existing sheet rows or clear existing dates.
- Never upload the same verified row twice during one run.
- Do not expose OAuth tokens, API keys, cookies, client secrets, or raw authorization codes.
- If YouTube Data API access is disabled or quota is exceeded, stop or record failures without marking rows as posted.

## Verification

The final report must include:

- Spreadsheet URL.
- Baseline UTC timestamp.
- Selected row numbers and titles.
- Attempted, verified, failed, and not-attempted counts.
- YouTube video IDs and watch URLs for verified uploads.
- Exact `publishAt` timestamps.
- The `MM/DD` value written to each verified row.
- The thumbnail source for each row (`sheet_cell`, `generated_fallback`, or `previous_run`) and the asset ID used.
- Read-back evidence for both YouTube resources and Sheet cells, including the verified `snippet.thumbnails.default` URL for every upload.

## Pitfalls

- **`values.get` truncates trailing empty cells.** After `values.append` writes a 5-column row, re-reading the appended range returns a 4-element row when the `Posted` cell is empty. Comparing the entire row including `Posted` will produce a false "append failed" report. Either read back only the columns you wrote or pad your comparison to ignore the trailing empty. See `../references/sheets-and-drive-gotchas.md`.
- **`drive.get` after a trash call often returns `trashed: None`.** Trust the `trashed = true` broad listing as the authoritative post-trash state, not the single-file metadata.
- **`values.append` returns `updatedCells`, not row counts.** Compute `updatedCells / len(columns_written)` and compare against your intended list.
- **`id = '...'` in a Drive search query returns 400 through the workspace wrapper.** Use `trashed = true` and filter the result client-side.
- **YouTube thumbnails are not set by `videos().update(part='snippet', media_body=...)`.** That API accepts a media body in theory but YouTube silently ignores it, so the existing thumbnail stays. Use `youtube.thumbnails().set(videoId=..., media_body=MediaFileUpload(path, mimetype='image/png'))` instead. See step 6 above.
- **First read-back after `thumbnails().set()` often returns only 3 sizes.** `default`, `medium`, `high` arrive almost immediately; `standard` and `maxres` typically appear within a second or two. Verify by checking any one of the five keys is present — don't wait for `maxres`.
- **Empty `Thumbnail Link` cell is not a fail state for the scheduler.** The fallback path renders a styled frame from the source video at `youtube.thumbnail_fallback_offset_seconds`, uploads it to `drive.thumbnails_root_folder_name` for audit, and attaches it to the YouTube video. Never skip the row because the cell is empty.
- **Use the shared thumbnail styler, not a per-skill reinvention.** Both `longform-thumbnail-analysis` and the scheduler fallback call `scripts/render_thumbnail.py` to apply the subtle bottom gradient + soft drop shadow + Google Sans Bold 700 + emphasis-word treatment. Reimplementing the styling in another skill was the cause of the broken thumbnails across the pipeline earlier — centralize and reuse.

## References

- `../scripts/load_config.py` and `../scripts/README.md` — bundle config and override rules.
- `../scripts/render_thumbnail.py` — shared thumbnail styler used for the fallback path in step 5.
- `../references/sheets-and-drive-gotchas.md` — Sheets/Drive API workarounds.
