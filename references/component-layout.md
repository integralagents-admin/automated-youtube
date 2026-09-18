# Automated YouTube Component Layout

## Canonical location

All components belong under:

```text
$HERMES_HOME/skills/media/automated-youtube/
```

The directory contains both Hermes skill directories and the two local repositories used by the video stack:

```text
automated-youtube/
├── automated-youtube/SKILL.md
├── cloud-file-lifecycle/
├── drive-cleanup/
├── google-workspace/
├── longform-thumbnail-analysis/
├── longform-to-clipped-longform/
├── longform-to-shortfrom/
├── raw-video-processesor/
├── video-content-repurposing/
├── video-use/
├── youtube-channel-repurposing/
├── youtube-content/
├── youtube-content-operations/
├── youtube-pipeline/
├── youtube-scheduler/
├── youtube-video-naming/
└── yt-dlp/
```

`~/.hermes/skills/video-use` is a compatibility symlink to the `video-use/` repository in this directory. Do not delete or repoint it without verifying the helper environment afterward.

## Discovery note

The umbrella is the class-level entry point. If a component is not returned by the skill catalog after a filesystem reorganization, use the umbrella's component map and read the component's local `SKILL.md` by path in an ordinary task. Do not silently substitute a different component or claim that the component is unavailable until the path has been checked.

## Path maintenance

When moving the repositories, update operational references that contain their old locations. Prefer `$HERMES_HOME` or `~/.hermes`-relative paths over machine-specific absolute paths. Keep `video-use`'s environment and `yt-dlp` checkout as siblings so editable-install instructions such as `uv pip install --python .venv/bin/python -e ../yt-dlp` remain valid.

## Post-move verification

Verify all of the following after a move:

1. Every listed component directory contains its expected `SKILL.md` or repository files.
2. The compatibility symlink resolves to the new `video-use` path.
3. `video-use/.venv/bin/python helpers/timeline_view.py --help` succeeds.
4. The `yt-dlp` checkout reports a version.
5. Existing cron jobs still resolve their attached skill names.
6. No visible operational reference still points to the old repository paths.

An untracked `uv.lock` created by `uv sync` is repository state, not a reason to undo the move; preserve it and do not commit it without an explicit maintenance decision.
