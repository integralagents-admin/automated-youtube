---
name: youtube-channel-repurposing
description: "Use for YouTube long-to-short content repurposing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, content repurposing, shortform, longform, editing, channel operations, yt-dlp, video-use]
    related_skills: [youtube-content, video-use]
---

# YouTube Channel Repurposing

Operate a repeatable editorial pipeline for a channel that turns long recordings (typically 40+ minutes) into useful, publishable YouTube assets. The default channel context is **Operator Maxxing**: business tactics for online businesses, info businesses, and agencies.

This is an editorial-and-production umbrella. Use `youtube-content` for transcript extraction and text transformations, and `video-use` for the actual conversation-driven video editing pipeline. Keep source media, transcripts, edit decision lists, renders, thumbnails, and publishing metadata organized per project.

## When to Use

Use this skill when a user wants to turn one or more long recordings into YouTube Shorts, other shortform clips, or 2–15 minute videos; build a clip package; create a source-to-edit workflow; or prepare repurposed assets and publishing metadata for an online-business channel.

## Outputs

For each source recording, aim to create a small content package rather than one arbitrary cut:

- **Shortform:** vertical-first clips for Shorts/Reels/TikTok-style distribution. Each clip should have one clear idea, a strong opening, fast comprehension, and a decisive ending.
- **Mid/longform:** 2–15 minute YouTube videos, usually one argument or tactic per video. Preserve enough context to make the piece useful without requiring the 40+ minute source.
- **Editorial metadata:** working title, hook, promise, audience, source timestamps, description, CTA, chapter markers where relevant, and a publish-status record.

Do not assume every source supports a fixed number of clips. Inventory first, then propose a package based on the strongest complete ideas.

## Standard workflow

1. **Ingest and inventory**
   - Identify the source file or URL, duration, speaker(s), topic, and intended audience.
   - If the source is online and the user has authority to download it, use the installed `yt-dlp` checkout or environment. Preserve the source URL and download metadata.
   - Never start rendering before confirming which source(s) are in scope.

2. **Transcribe and segment**
   - Prefer word-level timestamps when available; retain speaker labels and meaningful audio events.
   - Before any paid transcription, estimate provider usage against the available quota. If the source exceeds the remaining quota, stop before transcription and preserve the source; never proceed with partial or fabricated timing.
   - Break the source into complete ideas: setup, insight, example/proof, and takeaway.
   - Mark candidate hooks, quotable lines, transitions, repetitions, filler, and sections that depend on missing context.
   - Keep source timestamps attached to every candidate so edits remain auditable.

3. **Select and package**
   - Rank candidates by clarity of promise, practical value, novelty, emotional energy, and standalone completeness.
   - For each candidate, write a one-line premise and intended viewer outcome before cutting.
   - Separate clips that need minimal trimming from clips that need restructuring, narration, graphics, or additional context.
   - Avoid manufacturing claims or stitching sentences together in a way that changes the speaker's meaning.

4. **Design the edit**
   - Ask for or infer the target format, aspect ratio, tone, subtitle style, CTA, and branding; state assumptions when not specified.
   - For shortform, prioritize the hook in the first seconds, remove dead air and filler, maintain visual change without distracting from the idea, and end on a takeaway or next action.
   - For shortform captions, use one serialized visual line at a time; prevent overlapping subtitle events and position the caption center at the lower one-third mark of a 1080×1920 frame (`y=1280`, one-third of the frame height up from the bottom). The active word may pop and recolor while inactive words remain white.
   - For 2–15 minute videos, prioritize a clear promise, economical context, concrete examples, a logical progression, and a satisfying conclusion.
   - Use `video-use`'s confirm-before-execute pattern: propose the strategy and cut list, wait for approval when the decision is material, then render.

5. **Render and self-check**
   - Render into a project-local output directory; keep the source repository clean.
   - Check every cut for jump cuts, audio pops, clipped words, subtitle errors, bad framing, accidental overlays, and continuity problems.
   - Verify that the exported file opens, has expected duration/aspect ratio, and contains the intended audio and subtitles.
   - Re-render after correcting defects; do not declare completion from file existence alone.

6. **Queue and archive sources transactionally**
   - When processing a Drive queue, list active video files by `createdTime asc` and select the oldest by exact file ID, not filename.
   - Reuse a valid cached source/transcript and verified outputs when a prior attempt exists; do not duplicate uploads blindly.
   - Maintain separate source-specific child folders inside each stable output parent (for example, one child under the Shorts folder and one under the 2–15 minute clips folder). Never mix outputs from unrelated source videos or upload directly to a stable parent when child-folder organization is required.
   - Read back every output file and folder by ID, confirming parent, name, MIME type, nonzero size, and working link.
   - Treat source removal as a final transaction: write a combined verification manifest, require both format workflows and all uploads to pass, re-read the source metadata, then move only the exact source ID to reversible Drive trash. If any stage fails, preserve the source in the queue and retain the work directory for diagnosis.

## Batch queue processing

For an unattended source queue, the deletion gate is part of correctness, not cleanup. The run is eligible to archive a source only when `combined_verification.json` records the exact source ID and queue parent, successful shortform and 2–15 minute workflow results, verified child-folder uploads for both formats, and `deletion_eligible: true`. Use Drive trash rather than permanent deletion, then verify the source is trashed and absent from the active queue query. A query or upload timeout is not evidence of success; resume from known byte/file IDs and re-read state before continuing.

For long sources, estimate transcription usage before calling a paid provider. If the source exceeds the remaining quota, preserve the downloaded source and stop before transcription; after quota recovery, reuse the unchanged local source rather than re-downloading it. For large Drive files, use resumable ranged downloads with streamed chunks and bounded retries on transient read timeouts. Persist a manifest after each upload and read back each external ID before marking it verified. If YouTube returns `uploadLimitExceeded`, stop cleanup, preserve the source, retain successful IDs, and resume only failed assets after the limit clears; never duplicate verified uploads or rerun production just to compensate.

7. **Prepare publishing assets**
   - Produce title variants that make a specific promise without unsupported hype.
   - Write a concise description and CTA suited to the target viewer.
   - Include source timestamps and any required disclosure/attribution notes.
   - When scheduling YouTube releases, capture one UTC runtime baseline. Schedule the first Short and first longform clip both 20 minutes after that baseline. Schedule later Shorts exactly one hour apart within the Short track and later longform clips exactly two hours apart within the longform track. The first Short and first longform clip may intentionally share a timestamp; uniqueness is required within each track. The YouTube API requires scheduled uploads to be `private` with a future `publishAt`; verify the resource after upload and treat it as public only at the scheduled release time.
   - Track each derivative back to the original source and preserve the final file path.

## Content standards for Operator Maxxing

- Lead with a concrete business problem, mechanism, tactic, or decision—not generic motivation.
- Favor actionable details: who it is for, what to do, why it works, constraints, and an example.
- Preserve nuance around revenue, growth, acquisition, and agency claims; do not strengthen a claim merely to create a better hook.
- Make the viewer payoff legible in the title, opening, and edit structure.
- Prefer one sharp lesson per derivative over a shallow compilation of unrelated advice.

## Project layout

Use a directory per source/project, with outputs separate from tooling. A practical layout is:

```text
project/
  source/                 # downloaded or supplied originals
  transcript/             # raw and normalized transcripts
  candidates/             # timestamped segment inventory and rankings
  edit/                   # EDLs, previews, final renders, publish metadata
  project.md              # decisions, approvals, and persistent context
```

The `video-use` repository and its helpers should remain outside footage directories. Its normal output convention is `<videos_dir>/edit/`.

## Safety and rights

Only download or repurpose material the user owns, is authorized to use, or has permission to transform. Do not bypass access controls, paywalls, DRM, or platform restrictions. Treat API keys and cookies as secrets; keep them in environment files with restrictive permissions and never include them in transcripts, commits, logs, or responses.

## Verification checklist

Before handoff, confirm:

- Every output maps to a source timestamp range.
- The edit matches the requested duration and format.
- Audio, video, subtitles, and framing were inspected after rendering.
- The title/description/CTA match the actual content.
- No credentials or unintended source files were placed in output or version control.

## References

- Validated queue recovery, quota handling, caption placement, and two-track scheduling: `references/validated-runbook.md`
- Session setup and validated local paths: `references/session-setup.md`
- Tested operational patterns for large Drive media, transcription quotas, captions, queue cleanup, and YouTube scheduling: `references/operational-patterns.md`
- Use `youtube-content` for transcript retrieval and text-format output.
- Use `video-use` and always keep its `helpers/` directory alongside `SKILL.md` for editing operations.
