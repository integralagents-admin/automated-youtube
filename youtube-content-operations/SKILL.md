---
name: youtube-content-operations
description: Operate YouTube content pipelines with verified retries.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, content operations, uploads, scheduling, OAuth, idempotency]
    related_skills: []
---

# YouTube Content Operations Skill

Run reliable, resumable YouTube content operations across queue selection, clip publishing, title updates, OAuth recovery, schedule construction, and source cleanup. This umbrella skill complements specialized clipping and naming skills; it does not replace transcript-based editorial selection or rendering.

## When to Use

- A processed batch needs uploads, scheduling, retries, title updates, or reconciliation.
- A YouTube pipeline stopped partway through and successful uploads must be preserved.
- A Drive queue contains previously processed sources that remain active until cleanup.
- Google OAuth credentials need to be renewed for Drive and YouTube operations.

Do not use this skill to invent clip content, bypass upload verification, permanently delete sources, or rerun expensive transcription without checking preserved artifacts.

## Prerequisites

- A machine-readable source manifest and local clip paths.
- Google OAuth credentials with Drive and `youtube.force-ssl` scopes.
- A source-specific work directory containing render and upload manifests.
- The relevant clipping and title-naming skills when editorial work is required.

## Queue Idempotency

1. List active Drive videos under the configured queue parent ordered by `createdTime asc`.
2. Enumerate prior `queue_manifest.json` files and build a set of source IDs already processed.
3. Select the oldest active source whose ID is not already represented by a completed or in-progress run.
4. If a processed source remains active because cleanup was deferred, do not select it again merely because it is oldest.
5. Record the selected file ID, name, parent, timestamp, size, and work directory before downloading.

## Upload and Schedule Procedure

1. Read the existing YouTube manifest before any upload.
2. Skip every clip with a verified YouTube ID and preserve its title, schedule, and read-back record.
3. Retry only failed or not-attempted clips; never rerun the whole batch to compensate for one failure.
4. Capture one UTC baseline for each fresh scheduling run. The first Short and first longform clip use baseline +20 minutes; later Shorts use 60-minute spacing and later longform clips use 120-minute spacing.
5. If old slots are now in the past, assign fresh future slots to the remaining track items. Do not alter already verified videos unless explicitly requested.
6. Upload with `privacyStatus: private`, the exact future `publishAt`, and `selfDeclaredMadeForKids: false` unless instructed otherwise.
7. Read every returned video through `videos.list` and confirm channel ownership, title, privacy state, and exact `publishAt` before marking it verified.
8. Persist the manifest after each item so an interruption cannot lose successful IDs.

## Upload-Limit Recovery

Treat `uploadLimitExceeded` as a partial-run boundary, not as permission to duplicate or delete anything. Preserve verified items, record failed titles and exact errors, and stop the cleanup gate while any clip remains failed. Retry the remaining set later with a new future schedule if the previous slots have passed.

## Title Updates

When renaming verified videos, update only the intended `snippet.title` while preserving descriptions, tags, category, privacy, and schedule. Read all target videos before and after the update. If a batch update partially succeeds, audit live titles by ID, repair only mismatches, and then synchronize local manifests with the live state.

## OAuth Recovery

For web OAuth clients, register the exact HTTPS redirect URI in Google Cloud and request both Drive and YouTube scopes. Generate a fresh authorization URL with PKCE, save the pending state and verifier, exchange the complete callback URL, and verify YouTube access with `channels.list`. A general Workspace check may report missing unrelated scopes even when YouTube access is valid; test the specific API required by the pipeline.

## Cleanup Gate

Trash the raw Drive source only after all of the following are true:

- Every selected Short and longform output passed local verification.
- Every Drive upload has a read-back record.
- Every required YouTube upload is verified or the user explicitly accepts an incomplete run without cleanup.
- The exact source ID and original queue parent still match the manifest.
- The source is moved to reversible Drive trash, never permanently deleted.
- Direct metadata read-back confirms `trashed: true`, and a parent-folder listing confirms it no longer appears among active files.

If the verification query syntax fails, do not infer success or retry blindly. Read the exact file by ID and verify the parent listing without an unsupported ID predicate.

## Verification

A completed operation must reconcile these counts programmatically:

- rendered outputs
- Drive uploads and read-backs
- YouTube attempted, verified, failed, and not-attempted items
- live YouTube read-backs
- source active/trashed state

The final report must distinguish scheduled-private videos from videos that are already public, list remaining failures, and never claim source cleanup when `source_still_in_queue` is true.

## References

- `references/youtube-retry-and-auth.md` — reusable retry, OAuth, and verification patterns from prior pipeline runs.
