---
name: automated-youtube
description: Coordinate YouTube clipping, Drive, and posting workflows.
version: 0.2.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, video clipping, Drive, Sheets, automation]
    related_skills: []
---

# Automated YouTube Skill

Use this class-level umbrella for the complete Operator Maxxing YouTube production system: source retrieval, transcript-backed clipping, thumbnail creation, Drive storage, Posting Schedule maintenance, publishing operations, and cleanup. The component workflows live together under this skill directory; use the narrow component only when the request is clearly limited to one stage.

This umbrella does not replace verification. Every rendered clip, Drive upload, Sheet write, YouTube operation, and cleanup mutation must retain its component's read-back and idempotency rules.

## When to Use

- Running or scheduling the end-to-end YouTube clipping and posting preparation system.
- Coordinating source intake, Short/longform generation, thumbnails, Drive, Sheets, and cleanup.
- Diagnosing which component owns a pipeline failure.
- Do not use for unrelated video editing, arbitrary Drive cleanup, or generic Google Workspace work.

## Component Map

The component directories are under this skill directory:

- `longform-to-shortfrom` — standalone Short extraction and rendering.
- `longform-to-clipped-longform` — transcript-backed 2–15 minute topic clips.
- `raw-video-processesor` — oldest-queue processor that invokes both clip workflows.
- `video-use` — conversation-driven editing helpers and rendering environment.
- `yt-dlp` — source retrieval checkout used by the video workflows.
- `longform-thumbnail-analysis` — transcript-backed thumbnail moment and caption selection.
- `video-content-repurposing` — verified repurposing workflow and recovery patterns.
- `youtube-channel-repurposing` — channel-level editorial and production operations.
- `youtube-content` — transcript extraction and text transformations.
- `youtube-content-operations` — publishing operations and retry/auth handling.
- `youtube-video-naming` — viewer-intent title generation.
- `youtube-pipeline` — process clips, verify Drive outputs, and append Posting Schedule rows.
- `youtube-scheduler` — publish/schedule unposted rows when explicitly requested.
- `drive-cleanup` — trash videos whose Posting Schedule dates have passed.
- `google-workspace` — authenticated Drive and Sheets API wrapper.
- `cloud-file-lifecycle` — auditable cloud-file lifecycle and Drive verification.

For component-specific rules, read that component's `SKILL.md` from this directory before acting. Preserve the literal component spelling `raw-video-processesor`.

## Centralized Configuration

Every Drive ID, spreadsheet ID, and folder name used by the components lives in `config.yaml` at the bundle root. Resolve values with `scripts/load_config.py`:

```bash
$HERMES_HOME/skills/media/automated-youtube/scripts/load_config.py \
    posting_schedule.spreadsheet_id \
    drive.queues_root_folder_id \
    drive.source_queue_folder_id
```

### Override rules

- **Per-run override:** set an environment variable of the form `AUTOYT__<SECTION>__<KEY>` (for example `AUTOYT__DRIVE__QUEUES_ROOT_FOLDER_ID`). The loader maps dots to double underscores and uppercases the path. Env vars win over `config.yaml`.
- **Bundle root override:** if the bundle is moved (or you want to test a fork without mutating the live config), set `AUTOYT_BUNDLE_ROOT=/absolute/path/to/bundle` before running `load_config.py`. The loader resolves `config.yaml` from that directory.
- **Python helper:** `from scripts.load_config import cfg; cfg("drive.queues_root_folder_id")`. Same precedence: env var > `config.yaml` > `default` argument.
- **Required vs default:** pass `required=True` to raise `KeyError` instead of returning `""`. Use this for IDs that must be present before any Drive write.

### Component contract

Components must not hard-code IDs from a previous run. If a component needs a value, it must call `load_config.py` or the Python `cfg(...)` helper at the top of its procedure. When updating a component, replace inline IDs with the matching `cfg("section.key")` reference; never edit one without editing the other, or the bundle drifts back to hard-coded values.

### Tilde expansion guarantee

Values in `config.yaml` are returned with `os.path.expanduser` applied, so a key like `paths.video_use_repo: "~/.hermes/..."` resolves to an absolute path for any caller — bash scripts, Python helpers, subprocesses. Do not strip the leading `~` from `config.yaml` entries thinking it's redundant; a non-shell caller will receive a literal `~/...` string and `open()` will fail. Conversely, do not remove the `os.path.expanduser` call from `cfg()` thinking it's a hack — without it, the loader is unusable from Python.

### Work-root convention

`paths.work_root` is the shared workspace root for every batch (default `~/.hermes/workspaces/automated-youtube`). `paths.work_root_template` is `{work_root}/{slug}` and is what each component should derive its per-video directory from. Do not invent a new per-skill working directory under the bundle; one shared root keeps cleanup, debugging, and quota tracking trivial.

### What lives in `config.yaml` today

- `posting_schedule`: spreadsheet name/ID/URL, tab name, required columns.
- `drive`: three parent folder IDs (`queues_root_folder_id`, `source_queue_folder_id`, `longform_clips_parent_folder_id`) and three global folder names (`shortform_root_folder_name`, `longform_root_folder_name`, `thumbnails_root_folder_name`).
- `youtube`: cadence knobs (max rows per run, first/later clip spacing, default privacy, category ID, time zone).
- `paths`: `google_api_script`, `video_use_repo`, `yt_dlp_repo`, `work_root_template`, `bundle_root`.
- `transcription`: ElevenLabs `.env` path and key name.

When you add a new Drive ID or folder name to a component, add it to `config.yaml` first, then have the component read it.

## Canonical Flow

1. **Intake:** identify the oldest eligible source. The selection key is **`modifiedTime`**, not `createdTime` — the standard `drive search` listing returned by `google_api.py` exposes `modifiedTime` only; `createdTime` filtering requires an extra `files.get` per row and is not worth the cost. Always record both timestamps in the queue manifest when available, and document the fallback in the run report. Preserve the source URL/file ID and full metadata.
2. **Retrieve:** use authenticated Drive download for Drive sources and the bundled `yt-dlp` checkout for supported public URLs. Never access browser cookies silently.
3. **Transcribe:** use cached, word-level, verbatim transcripts from `video-use`; do not normalize fillers or retranscribe unchanged sources.
4. **Select and render:** choose transcript-backed standalone or topic-focused clips, snap cuts to word boundaries, pad edges, apply required audio fades, and keep subtitles last in the filter chain.
5. **Verify local output:** use `ffprobe` plus rendered-output visual/timeline checks before upload.
6. **Upload to Drive:** upload each verified clip and thumbnail, retain returned IDs/links, and read metadata back.
7. **Record the sheet:** append only verified rows to `Posting Schedule`, deduplicated by `(Title, Video Link)`, then read back exact written cells.
8. **Publish only when requested:** the pipeline stage records Drive links; the scheduler/publishing stage is separate and must verify each external resource before marking the sheet.
9. **Clean up:** invoke `drive-cleanup` only for explicitly authorized cleanup; trash is reversible and permanent deletion is prohibited by default.

### Safe interactive stopping points

When the user runs "the pipeline" interactively (vs. a scheduled cron tick), `raw-video-processesor` does not finish in one turn. Three well-defined breakpoints leave the bundle in a fully verified, restorable state:

1. **After intake + retrieval:** source downloaded, `ffprobe` passes, `queue_manifest.json` written. No Drive writes, no transcription cost. Source is still in the queue.
2. **After transcription:** `edit/takes_packed.md` cached locally, no Drive writes beyond folder bootstrap. The source is still in the queue.
3. **After folder bootstrap:** the three per-source folders (Shorts, Longform, Thumbnails) exist on Drive and have been read back. The source is still in the queue.

The natural stop after each breakpoint is **"stop here and report, the source is still in the queue"**. After step 3, pause before editorial selection — it consumes the running model's time, picks clips the user may want to override, and uploads to Drive are non-reversible (only the source trash is reversible). For interactive runs, ask before proceeding past the folder-bootstrap gate.

## Cross-Component Invariants

- Preserve exact identifiers and filenames; never repair malformed tokens silently.
- Never fabricate Drive or YouTube links.
- Keep source media, transcripts, EDLs, renders, thumbnails, and manifests separated per batch.
- Preserve successful manifest entries when a later stage fails.
- Mutations are serial and bounded; retries must be idempotent.
- Never overwrite existing Posting Schedule rows or clear existing dates.
- Report attempted, verified, failed, skipped, and not-attempted counts so totals reconcile.
- Do not expose OAuth tokens, API keys, cookies, or client secrets.

## Automation and Scheduling

Scheduled runs must use a self-contained prompt and load this umbrella plus any required component skill. Pipeline preparation must not call YouTube upload or scheduling APIs. Drive cleanup must use reversible Trash only. Any job that changes external state must verify the exact target afterward and report exceptions.

## References

- `references/component-layout.md` — canonical directory layout, component ownership, and migration notes.
- `references/sheets-and-drive-gotchas.md` — Sheets/Drive API workarounds (trailing-empty-cell truncation, single-cell update syntax, trash-verification pattern, etc.).
- `references/bundle-to-github.md` — how to stage the bundle and push to GitHub, including the GITHUB_API_TOKEN rename and the duplicate-references trap.
- `references/runbook-interactive-run.md` — end-to-end script pattern for interactive pipeline runs, with every gotcha this bundle has hit.

## Verification

A coordinated run is complete only when every stage's own completion criterion passes and the final report reconciles source count, rendered clip count, Drive upload count, sheet row count, and any publishing or cleanup mutations. If a component cannot be discovered or loaded, stop and report the missing component rather than improvising a replacement.
