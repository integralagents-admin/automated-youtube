---
name: youtube-pipeline
description: Process clips and record them in a posting schedule.
version: 0.2.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, Posting Schedule, Shorts, Longform Clips, Google Drive, Google Sheets]
    related_skills: []
---

# YouTube Pipeline Skill

Run the queued-video processor, create verified Short and longform outputs, and record each output in the Posting Schedule Google Sheet. This workflow no longer uploads or schedules videos on YouTube. It stores the verified Google Drive clip link, title, video type, and thumbnail link for later human or downstream publishing.

The current processor skill is named `raw-video-processesor`; preserve that exact spelling when invoking it.

## When to Use

- The user asks to run the video queue and prepare clips for posting.
- The user wants Shorts and longform clips added to the posting schedule.
- A processed batch needs its Drive links and thumbnail links recorded.
- Do not use this skill to publish, schedule, delete, or modify YouTube videos.

## Prerequisites

- `raw-video-processesor` and its dependencies are available.
- Google OAuth token at `$HERMES_HOME/google_token.json` with Drive and Sheets access.
- All Drive IDs, spreadsheet IDs, and folder names live in `~/.hermes/skills/media/automated-youtube/config.yaml`. Resolve them with `scripts/load_config.py`. Override any value per-run by setting `AUTOYT__<SECTION>__<KEY>` (see `scripts/README.md`). Never hard-code IDs from a previous run.
- Required config keys before starting:
  - `posting_schedule.spreadsheet_id`, `.spreadsheet_url`, `.tab_name`
  - `posting_schedule.required_columns` (defaults to `Title`, `Video Link`, `Video Type`, `Thumbnail Link`, `Posted`)
  - `drive.thumbnails_root_folder_name`
  - `drive.queues_root_folder_id`
  - `paths.google_api_script`
- Each batch thumbnail folder: `<YYYY-MM-DD> — <source title> — <source file ID>`.
- Longform thumbnail filenames identify their paired video: `<batch slug> — <clip number> — <youtube title slug> — thumbnail.png` or `.jpg`.

## How to Run

Use `terminal` with the processor and a small authenticated Google API client. Use `read_file` for processor manifests. Use `vision_analyze` and the `longform-thumbnail-analysis` skill for longform thumbnails. Use Sheets `values.get` and `values.append` or `values.update` for the posting schedule. Never call `youtube.videos().insert`, `youtube.videos().delete`, or YouTube scheduling APIs in this workflow.

## Procedure

1. **Run the raw processor.** Invoke `raw-video-processesor`, which selects the oldest active queue video, runs the Short and longform clipping workflows, verifies local outputs and Drive uploads, and applies its source-cleanup gate. Completion criterion: the processor succeeds and provides manifests with every verified clip’s local path and Drive file ID/link.

2. **Collect every verified clip.** Read the processor manifests and create `clips_to_schedule.json` containing every verified Short and longform clip exactly once. Preserve type, title, local path, source title, source file ID, Drive file ID, and Drive `webViewLink`. Do not silently omit clips or add outputs from prior batches. Completion criterion: the collected count equals the processor’s verified output count.

3. **Ensure the Sheet schema.** Read `<TAB>!1:1` using `posting_schedule.tab_name`. If the sheet is empty, write the headers from `posting_schedule.required_columns`. If headers exist, preserve existing columns and add any missing required columns to the right. Do not overwrite existing posting rows. Completion criterion: the first row contains every entry of `posting_schedule.required_columns` in their recorded positions.

4. **Prepare titles and thumbnail links.** Use transcript-grounded, viewer-intent titles for every clip. For each longform clip, invoke `longform-thumbnail-analysis`, render and visually verify one thumbnail, upload it to the batch thumbnail folder, and read back its Drive link. Shorts have an empty thumbnail link unless a verified thumbnail was explicitly created. Completion criterion: every longform item has one verified thumbnail link; every Short has either a verified thumbnail link or an explicit blank value.

5. **Build posting rows.** Map each verified clip to exactly one row:

   - `Title`: the final clip title.
   - `Video Link`: the verified Drive `webViewLink` for the rendered clip, never an unverified local path and never a fabricated YouTube link.
   - `Video Type`: exactly `Short` or `Long`.
   - `Thumbnail Link`: the verified Drive thumbnail link for longform clips, or blank when no thumbnail applies.

   Completion criterion: each row has four fields in the required order and every nonblank link was read back from Drive.

6. **Append idempotently.** Before appending, read the existing posting rows and identify duplicates by the tuple `(Title, Video Link)`. Append only rows not already present. Preserve all existing rows and their values. Completion criterion: every verified clip appears exactly once for this batch and rerunning the pipeline appends zero duplicates.

7. **Verify the external sheet state.** Read back the exact appended range and compare values cell-by-cell with the intended rows. Confirm that titles, Drive links, type labels, and thumbnail links match. Completion criterion: every intended row is present with exact values and no unrelated row was changed.

8. **Report the batch.** Return the source title, total verified Shorts, total verified longform clips, rows appended, rows skipped as duplicates, the spreadsheet link, and the thumbnail folder link. Do not report YouTube upload or publication status because this workflow does not perform those actions.

## Sheet Contract

The required columns come from `posting_schedule.required_columns` in `config.yaml`. Today that is:

```text
Title | Video Link | Video Type | Thumbnail Link | Posted
```

Example rows:

```text
How to Build a Personal Brand Without Forcing Content | https://drive.google.com/file/d/.../view | Long | https://drive.google.com/file/d/.../view
The Content Mistake That Keeps You Invisible | https://drive.google.com/file/d/.../view | Short |
```

`Video Link` always points to the verified Drive-rendered clip. `Thumbnail Link` points to the verified Drive thumbnail when applicable.

## References

- `~/.hermes/skills/media/automated-youtube/references/runbook-interactive-run.md` — end-to-end interactive runbook with breakpoints, the per-source folder bootstrap pattern, and the driver-script gotchas.
- `~/.hermes/skills/media/automated-youtube/references/runbook-batch-layout.md` — the per-batch file layout (`batch.json`, `selected.json`, `uploads.json`, etc.) a previous run leaves in the work directory.
- `~/.hermes/skills/media/automated-youtube/references/runbook-google-sheets-verify.md` — the append-and-verify pattern, including the trailing-empty-cell trap when comparing the intended range to the read-back JSON.
- `~/.hermes/skills/media/automated-youtube/references/runbook-driver-patterns.md` — the reusable shell + Python driver shapes, including source-trash verification.

## Idempotency and Safety

- Never upload or schedule a video on YouTube in this workflow.
- Never delete or modify existing spreadsheet rows.
- Append only verified Drive outputs.
- Skip an existing `(Title, Video Link)` pair rather than creating a duplicate.
- Never fabricate Drive links, YouTube links, titles, transcript claims, or thumbnail links.
- Preserve successful manifest entries if a later Sheet append or verification fails.
- Never expose OAuth tokens, API keys, cookies, or client secrets.

## Pitfalls

- **Empty trailing cells look like a mismatch after append.** The Sheets `values.get` response drops trailing empty cells in each row, so a 5-column row with an empty `Posted` returns as a 4-element list. Do not fail the verify step on a length difference in trailing columns; compare column-by-column and treat absent trailing cells as empty strings.
- **A successful `drive upload` is not a verified upload.** Always re-fetch with `drive get` and assert the returned `name`, `parents[0]`, and non-trashed state match the intended target. The `drive upload` response can lag on the parent link.
- **Folder creation can race.** A folder returned from `drive create-folder` is sometimes missing its parent immediately on read-back. Re-read each folder with `drive get` before persisting its ID in any manifest.
- **`drive get` omits the `trashed` field after a successful trash.** Use the `trashed = true` listing plus the non-trashed queue listing to verify a source trash. Do not trust a single `drive get` response.
- **Per-clip self-evaluation is not built into the renderer.** The `render_vertical.py` helper writes per-clip `mp4` and `ass` files and a `render_manifest.json`, but does not run any per-clip quality gate. If a session needs to enforce hook quality or subtitle timing, do that check explicitly after rendering and before uploading.
- **Do not assume `youtube-pipeline` covers the rendering itself.** This skill describes what to record and where; the actual rendering, uploading, and folder bootstrap live in `raw-video-processesor`, `longform-to-shortfrom`, `longform-to-clipped-longform`, and `longform-thumbnail-analysis`. Read those before an interactive run.

## Verification

The final report is valid only when:

- The processor’s verified clip count matches the collected clip count.
- Every clip has a verified Drive file ID and `webViewLink`.
- Every longform clip with a thumbnail has a verified thumbnail Drive file ID and link.
- `Sheet1` contains the required headers.
- Every intended row was read back exactly after append.
- Duplicate detection was applied before writing.
- No YouTube upload or scheduling API was called.
