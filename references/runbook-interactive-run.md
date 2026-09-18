# Interactive pipeline runbook

How to actually run the YouTube pipeline end-to-end from a chat session, with every gotcha this bundle has hit recorded. Read this before driving `raw-video-processesor` from an interactive turn.

## TL;DR

A pipeline run has three safe breakpoints. For interactive runs, stop after folder bootstrap and report. Source is still in the queue. Editorial selection is a separate decision.

## What you actually run, in order

1. **Resolve config once, up front.**
   - `BUNDLE=$HOME/.hermes/skills/media/automated-youtube`
   - Each config value prints as `dotted.key=value`. To capture just the value:
     ```bash
     get_cfg() { "$BUNDLE/scripts/load_config.py" "$1" | sed -n 's/^[^=]*=//p'; }
     GAPI="$(get_cfg paths.google_api_script)"
     ```
   - **Do not** use bare `$(load_config.py key)` and pass it to another `python` — the literal `key=value` line will be interpreted as a script path and you'll get `python: can't open file 'dotted.key=value'`.

2. **Check Drive auth.**
   - `python $HOME/.hermes/skills/media/automated-youtube/google-workspace/scripts/setup.py --check` should print `AUTHENTICATED: Token refreshed …`.
   - If it prints anything else, run the full OAuth setup flow in the `google-workspace` skill before any Drive operation.

3. **Pick the oldest queue video by `modifiedTime`.** Drive's `drive search` does not return `createdTime`. Order by `modifiedTime asc` and document the fallback in the run report.

4. **Download the source into the work root.**
   - Default work root: `~/.hermes/workspaces/automated-youtube/<slug>/` (shared, not per-skill).
   - One workspace root per batch keeps cleanup and quota tracking trivial.

5. **Transcribe with ElevenLabs Scribe via `video-use`.**
   - `python $VIDEO_USE_DIR/.venv/bin/python $VIDEO_USE_DIR/helpers/transcribe.py <source.mp4> --edit-dir <work>/edit`
   - `python $VIDEO_USE_DIR/.venv/bin/python $VIDEO_USE_DIR/helpers/pack_transcripts.py --edit-dir <work>/edit`
   - The `.venv/bin/python` is the venv's interpreter, not the system python — these helpers depend on it.

6. **Ensure the three per-source Drive folders exist.**
   - Shorts child: under `drive.shortform_root_folder_name`, parented by `drive.queues_root_folder_id`.
   - Longform child: under `drive.longform_clips_parent_folder_id`.
   - Thumbnails child: under `drive.thumbnails_root_folder_name`, parented by `drive.queues_root_folder_id`.
   - Always read each folder back (`drive get`) before persisting its ID. The `drive search` response is a population summary, not a guarantee.

7. **Stop here for interactive runs.** Report source ID, work directory, transcript location, and all three folder IDs. Ask before proceeding to editorial selection.

## Gotchas to bake into your driver script

- **Tilde expansion is required.** Every `paths.*` value in `config.yaml` starts with `~`. `load_config.py` runs values through `os.path.expanduser`, so Python callers get an absolute path. Bash callers that forget the expanduser guarantee will end up writing files to a literal `~/...` directory next to the cwd. Never strip the leading `~` from `config.yaml` thinking it is redundant.
- **The env var is `GITHUB_API_TOKEN`, not `GITHUB_TOKEN`.** Any bare `^GITHUB_TOKEN=` grep returns empty. Resolve with `awk -F= '/^GITHUB_API_TOKEN=/ {print $2}' ~/.hermes/.env` and never rename it.
- **Inline terminal payloads are often refused.** The shell parser blocks complex multi-step shell as "Nested executable body could not be resolved". Always:
  - Write the workflow to `/tmp/<name>.sh` and `bash /tmp/<name>.sh`.
  - Or `terminal(command="...", background=true)` + `process(action="wait")` for long bounded work.
  - Pair with `notify=true` if you want a notification on completion.
- **`tee` to `/tmp/<file>.log` can hit a permission refusal** if the file was created by another user or another uid run. Prefer `process(action="poll")` to read the running output directly; avoid the `tee` step.
- **Long-running driver = background.** Source downloads for 800 MB+ files take minutes. Transcription on a 60-minute video takes 1–2 minutes of ElevenLabs time plus local audio extraction. Drive folder lookups are slow. Always background the driver and poll.

## What "verified" means for each stage

- **Source downloaded:** `ffprobe` returns at least one `video` and one `audio` stream; `wc -c` matches the size in `drive get`.
- **Transcription cached:** `edit/takes_packed.md` exists and is non-empty; the `transcripts/<source>.json` is also non-empty.
- **Drive folders verified:** `drive get <folder-id>` returns the expected name and parent. A folder returned from `drive create-folder` is sometimes missing its parent immediately — read it back, do not trust the create response alone.
- **Source still in queue:** `drive search "<queue_id> in parents and mimeType contains 'video/' and trashed = false"` lists the source ID. Never trash before this returns success.

## What to never do

- Never trash the source before both clip workflows have produced verified outputs and the combined success gate has passed.
- Never upload to Drive without first reading the file metadata back.
- Never write to the Posting Schedule without first appending and re-reading the appended range.
- Never remove the `os.path.expanduser` from `cfg()` — it is load-bearing for non-shell callers.
- Never rename the env var to `GITHUB_TOKEN`. The bundle and the upstream `github-auth` skill both look for `GITHUB_API_TOKEN` on this machine.
- Never `mv` the umbrella `SKILL.md` or `references/` into a staging directory for a push — `cp -a` so a partial run leaves the live source intact.

## Verification before reporting

A run is fully verified only when:

- Source downloaded, `ffprobe` passes, file size matches Drive metadata.
- Transcript cached (`takes_packed.md` and JSON transcript both present).
- Three per-source folders exist and have been read back from Drive.
- No uploads beyond folder creation.
- Source still active in the queue (no premature trash).
- Reported counts equal reality: 1 source, 3 folders, 1 transcript, 0 clips uploaded, 0 sheet rows added.