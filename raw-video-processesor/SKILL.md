---
name: raw-video-processesor
description: Process a locally downloaded YouTube source through both clip workflows.
version: 0.2.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Video Processing, YouTube, Shorts, Longform Clips, Automation]
    related_skills: [youtube-source-downloader]
---

# Raw-Video-Processesor Skill

Process one locally downloaded YouTube source through the current Short and longform clipping workflows. Source intake is owned by `youtube-source-downloader`; this processor must not select from or download a Drive bucket. It preserves the local source on failure and deletes it only after both clip workflows, Drive read-backs, and the Posting Schedule verification succeed.

Preserve the exact component spelling `raw-video-processesor` when invoking this skill.

## When to Use

- `youtube-source-downloader` has produced a verified `source_manifest.json` and local media file.
- The user asks to extract both Shorts and topic-focused longform clips.
- A prior run needs to resume from a preserved local source.
- Do not use this skill to choose a YouTube channel, publish videos, or trash remote source files.

## Prerequisites

- A source manifest from `$HERMES_HOME/skills/media/automated-youtube/youtube-source-downloader`.
- A playable local source with verified video and audio streams.
- `longform-to-shortfrom` and `longform-to-clipped-longform` available.
- Drive and Sheets OAuth access for clip uploads and Posting Schedule writes.
- `paths.work_root`, `paths.google_api_script`, `paths.video_use_repo`, and `paths.yt_dlp_repo` resolved through `scripts/load_config.py`.
- `ffmpeg` and `ffprobe` available.

## Procedure

1. **Load the source manifest.** Confirm the local path exists, the recorded video ID is present, and the path is inside the run work directory. Do not substitute a different file. Completion criterion: the exact source path and video ID are recorded in the processing manifest.

2. **Run the shortform workflow.** Apply `longform-to-shortfrom` to the local source, render the selected vertical clips, upload them to the configured Drive structure, and read back every claimed Drive file. Completion criterion: the Short manifest reports success and every claimed output has a verified Drive ID/link.

3. **Run the clipped-longform workflow.** Apply `longform-to-clipped-longform` to the same local source and transcript, render coherent 2–15 minute topic clips, upload them beneath the configured longform parent, and read back every upload. Completion criterion: the longform manifest reports success, its source folder is verified, and every output has a verified Drive ID/link.

4. **Run the Posting Schedule stage.** Apply `youtube-pipeline` to the two verified output manifests. It must append only nonduplicate clip rows to the Posting Schedule spreadsheet resolved from private configuration and read back the exact written cells. Completion criterion: all intended rows are verified or the run stops with the source preserved.

5. **Write the combined success gate.** Create `combined_verification.json` containing the source video ID, local path, Short and longform manifests, Drive read-backs, sheet read-backs, reconciled counts, and `deletion_eligible`. Set `deletion_eligible: true` only when every required stage passed.

6. **Delete the local source after the gate.** If and only if `deletion_eligible` is true, delete the exact local path from the source manifest and verify it is absent. Update the manifest with `local_source_deleted: true`. Do not delete the source when any stage fails; preserve it for retry and report its path.

## Failure and idempotency rules

- Never select a different source to compensate for a processing failure.
- Never rerun successful uploads blindly; inspect manifests and skip verified Drive IDs.
- Never delete the local source before all external read-backs pass.
- Never trash or permanently delete a remote YouTube/Drive source in this workflow.
- Preserve successful manifests when a later stage fails.
- Never fabricate Drive links, YouTube IDs, titles, or verification results.

## Verification checklist

- [ ] Source manifest video ID and local path match the file processed.
- [ ] Shortform outputs are locally verified and read back from Drive.
- [ ] Longform outputs are locally verified and read back from Drive.
- [ ] Posting Schedule rows use the correct spreadsheet and are read back exactly.
- [ ] `combined_verification.json` reconciles all counts.
- [ ] Local deletion occurred only with `deletion_eligible: true` and was verified.
