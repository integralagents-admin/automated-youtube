# Driver-script patterns

Reusable shapes for the bash + Python scripts that drive the automated-youtube bundle from an interactive turn. These patterns are the lessons this bundle has hit, not a theory of pipelines.

## Run bash scripts via a file, not inline

The shell parser blocks complex multi-step shell as "Nested executable body could not be resolved". Always write the workflow to `/tmp/<name>.sh` and run `bash /tmp/<name>.sh`. Never try to `terminal(command="set -euo pipefail; mkdir -p …; for x in …; do …; done")` inline.

For long-running bounded work, run the script in the background and poll:

```bash
terminal(command="bash /tmp/run.sh", background=true)
# then
process(session_id, action="wait", timeout=180)
```

If the script may exceed the foreground 600s timeout, use `background=true` from the start.

## Capture config values via `get_cfg`

`load_config.py key` prints `dotted.key=value` on stdout. Capture only the value:

```bash
get_cfg() { "$BUNDLE/scripts/load_config.py" "$1" | sed -n 's/^[^=]*=//p'; }
GAPI="$(get_cfg paths.google_api_script)"
```

Never do `VAR="$(load_config.py key)"` and then `python "$VAR"` — the captured `dotted.key=value` line will be treated as a script path and you'll see `python: can't open file 'dotted.key=value'`.

## Quote filenames with non-ASCII characters

Pipeline filenames contain em-dashes (`—`). `ls` calls without quoting, or pipeline `for` loops over `*.mp4` without quoting inside the loop, will trip over a literal em-dash. Always quote:

```bash
for f in "$WORK/clips"/*.mp4; do
    upload_one "$f" "$LONGFOLDER" "$(basename "$f")" "long"
done
```

`upload_one "$f" "..." "..."` only works because every argument is quoted. A bare `for f in $WORK/clips/*.mp4` produces a glob expansion that the shell tokenizes correctly for `*.mp4` but breaks inside an `ls`-based helper. The simplest rule is "every expansion is quoted".

## Verify uploads, not just create them

`drive upload` returns the new file ID, but the parent link can lag. Always re-read with `drive get` and assert:

- `name` matches the intended filename
- `parents[0]` matches the intended folder ID
- `trashed` is `false`

A `drive get` that does not match means the upload landed in the wrong place or got auto-trashed by a parent rule. Stop and report.

## Verify source trash by listing, not by `drive get`

`drive get` omits the `trashed` field after a successful trash. Use two listings:

1. `drive search "trashed = true"` and confirm the source ID appears in the result.
2. `drive search "<queue_id> in parents and mimeType contains 'video/' and trashed = false"` and confirm the source ID is absent.

Both must pass before the source is considered trashed. The single `drive delete` response is not proof — it is a request acknowledgment.

## Background long-running work and poll

800 MB+ downloads, multi-hour renders, and full pipeline runs routinely exceed the foreground 600s cap. Always run them in the background and poll:

```bash
terminal(command="bash /tmp/pipeline_run.sh <source-id>", background=true)
```

Then poll with `process(session_id, action="poll", timeout=180)` until `status: "exited"`. Watch the `output_preview` field for progress signals. Do not loop on `poll` with a tight timeout; one poll per minute is fine.

## PyYAML lives outside `video-use/.venv`

The `video-use/.venv` interpreter is the right Python for ElevenLabs Scribe and the render helper, but it does NOT have PyYAML installed. Drivers that need to read `config.yaml` should use the system Python (the `hermes-agent/venv` Python at `~/.hermes/hermes-agent/venv/bin/python3`, which has `import yaml` working) or `python3` directly.

The bundle's own `load_config.py` works fine from either Python as long as the dependency is present. If you must run from `video-use/.venv/bin/python`, install PyYAML into it first: `$VIDEO_USE_DIR/.venv/bin/pip install pyyaml`.

## Never `mv` the live bundle into a staging directory

When pushing the bundle to GitHub, copy it (`cp -a`) rather than move it. A `mv` followed by an aborted script leaves the live `automated-youtube/` directory without its umbrella `SKILL.md` and `references/`. `cp -a` is reversible.

## Run a background script for the final Drive ops

Upload jobs are slow (multi-MB to multi-GB), and the foreground terminal tool times out after 600s. The pattern that worked:

```bash
# Stage the work locally; verify file existence before backgrounding
test -f "$WORK/clips/03 — The Offer Stack.mp4" && \
    test "$(stat -c%s "$WORK/clips/03 — The Offer Stack.mp4")" -gt 100000000

# Background the upload driver
terminal(command="bash /tmp/upload_all.sh", background=true)
process(session_id, action="wait", timeout=600)
```

If a long-form encode finishes late, poll the file size in a separate `terminal` call before kicking off the upload, so the upload does not race the encode.