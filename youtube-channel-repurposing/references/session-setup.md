# Session setup: Operator Maxxing repurposing stack

Validated during the initial channel setup session.

## Repositories and paths

- `yt-dlp`: `~/.hermes/skills/media/automated-youtube/yt-dlp`
  - Origin: `https://github.com/yt-dlp/yt-dlp.git`
  - Verify with: `git -C ~/.hermes/skills/media/automated-youtube/yt-dlp status --short --branch`
- `video-use`: `~/.hermes/skills/media/automated-youtube/video-use`
  - Origin: `https://github.com/browser-use/video-use.git`
  - Environment: `~/.hermes/skills/media/automated-youtube/video-use/.venv`
  - Verify with: `git -C ~/.hermes/skills/media/automated-youtube/video-use status --short --branch`

## Setup pattern

From the `video-use` repository:

```bash
uv sync
uv pip install --python .venv/bin/python -e ../yt-dlp
.venv/bin/python helpers/timeline_view.py --help
ffprobe -version
.venv/bin/yt-dlp --version
```

The whole `video-use` directory, not only `SKILL.md`, must be registered because the editing helpers are siblings of the skill file. In this session it was linked at:

```text
~/.hermes/skills/video-use -> ~/.hermes/skills/media/automated-youtube/video-use
```

`uv sync` may create an untracked `uv.lock`; do not commit it without an explicit repository-maintenance decision.

## Credentials and transcription

`video-use` uses ElevenLabs Scribe for word-level transcription. An `ELEVENLABS_API_KEY` was not configured during setup. Do not attempt transcription until the user supplies or explicitly authorizes use of the key. Never print, commit, or include the key in project artifacts.

## Verification evidence

The following checks passed in the setup session:

- `timeline_view.py --help`
- `ffprobe -version`
- yt-dlp installed from the local checkout and executed successfully
- Hermes symlink resolved to `~/.hermes/skills/media/automated-youtube/video-use`
