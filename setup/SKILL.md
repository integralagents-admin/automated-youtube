---
name: automated-youtube-setup
description: Use when installing or repairing the automated-youtube pipeline. Install and verify all system tools, Python packages, video-use, Google OAuth, and ElevenLabs configuration.
version: 1.0.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [YouTube, setup, yt-dlp, ffmpeg, ElevenLabs, Google Workspace, Sheets]
    related_skills: [youtube-pipeline, youtube-source-downloader, google-workspace, raw-video-processesor]
---

# Automated YouTube Setup

## Overview

This is the first-time setup and repair checklist for the `automated-youtube` bundle. It installs the tools used by source intake, transcription, clip rendering, Drive uploads, and Sheets recording. Run it before the first live pipeline execution and after changing machines, Python environments, or repository revisions.

The bundle has four dependency layers:

1. **System tools:** Git, Python, FFmpeg/ffprobe, yt-dlp, and optionally Node.js/npm for animation slots.
2. **Python packages:** the `video-use` editor dependencies plus the pinned Google Workspace client packages and PyYAML.
3. **Repositories and files:** the `video-use` checkout, Google OAuth credentials/token, and the ElevenLabs `.env` file.
4. **Service access:** YouTube/Drive/Sheets OAuth and a working ElevenLabs API key.

Do not run a paid transcription as an installation test. Verify the helper and media tools first; reserve Scribe usage for a real pipeline run.

## When to Use

- The automated YouTube pipeline is being installed on a new machine.
- A live run fails with a missing executable, Python module, credential, or API key.
- `video-use` or its dependencies were updated.
- The pipeline must be handed to another Hermes profile or workstation.

Do not use this skill to change source channels, spreadsheet IDs, posting schedules, or clip policy. Those belong in the bundle `config.yaml` and pipeline skills.

## Canonical paths and configuration

Resolve paths through the bundle config rather than hard-coding them in workflow logic:

```bash
BUNDLE="${HERMES_HOME:-$HOME/.hermes}/skills/media/automated-youtube"
PYTHON="${HERMES_PYTHON:-${HERMES_HOME:-$HOME/.hermes}/hermes-agent/venv/bin/python}"
VIDEO_USE="$("$PYTHON" "$BUNDLE/scripts/load_config.py" paths.video_use_repo | sed 's/^[^=]*=//')"
```

For the current macOS profile, the stable checkout is:

```text
the local `video-use` checkout configured by `paths.video_use_repo`
```

The checkout must contain `SKILL.md`, `helpers/`, `pyproject.toml`, and `.env` at its root. All generated editing output belongs in the input video's `edit/` directory, never in the repository.

The bundle config owns these values:

- `paths.video_use_repo`: stable `video-use` checkout.
- `paths.yt_dlp_binary`: yt-dlp executable.
- `paths.ffmpeg_binary` and `paths.ffprobe_binary`: media executables used by source intake.
- `transcription.elevenlabs_env_file`: root `.env` containing the ElevenLabs key.
- `source_tracking.*`: source ledger, channel list, and rotation state.
- `posting_schedule.*`: clip schedule spreadsheet.

## 1. Install system packages

### macOS (Homebrew)

Install Homebrew first if `brew` is unavailable. Then run:

```bash
brew install git python@3.11 ffmpeg yt-dlp
```

Recommended optional tools:

```bash
brew install uv node
```

`git`, `python@3.11`, `ffmpeg`, and `yt-dlp` are required. `ffmpeg` supplies both `ffmpeg` and `ffprobe`. `uv`, Node.js, and npm are optional for the base pipeline; Node.js/npm become required only when using HyperFrames or Remotion animation slots.

If Homebrew is installed outside the current shell PATH, initialize it before verification:

```bash
eval "$(brew shellenv)"
```

Do not install Manim, HyperFrames, or Remotion globally during base setup. They are optional and should be installed lazily inside the animation slot that needs them. Manim can be installed from the `video-use` optional dependency when a Manim slot is actually required.

### Debian/Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv ffmpeg
python3 -m pip install --user yt-dlp
```

### Arch Linux

```bash
sudo pacman -S --needed git python ffmpeg yt-dlp
```

Completion criterion: `git --version`, `python3 --version`, `ffmpeg -version`, `ffprobe -version`, and `yt-dlp --version` all exit successfully.

## 2. Clone or update video-use

The official repository and stable path are:

```bash
mkdir -p "$HOME/Developer"
if test -d "$HOME/Developer/video-use/.git"; then
  git -C "$HOME/Developer/video-use" pull --ff-only
else
  git clone https://github.com/browser-use/video-use "$HOME/Developer/video-use"
fi
```

Keep the whole repository together. Do not copy only `SKILL.md`; the helpers must remain beside it. Set `paths.video_use_repo` in the bundle config to this checkout.

Completion criterion: `$VIDEO_USE/SKILL.md`, `$VIDEO_USE/helpers/transcribe.py`, `$VIDEO_USE/helpers/render.py`, and `$VIDEO_USE/pyproject.toml` exist, and `git -C "$VIDEO_USE" remote get-url origin` reports `https://github.com/browser-use/video-use`.

## 3. Install Python packages

Use the same Python interpreter that runs the pipeline. Prefer a project environment with `uv`; otherwise use the Hermes runtime venv.

```bash
cd "$VIDEO_USE"
if command -v uv >/dev/null 2>&1; then
  uv sync
else
  "$PYTHON" -m pip install -e .
fi
```

`video-use/pyproject.toml` requires:

- `requests` — ElevenLabs Scribe API calls.
- `librosa` — audio analysis.
- `matplotlib` — timeline/visual diagnostics.
- `pillow` — image and frame handling.
- `numpy` — numerical/audio processing.

The `video-use` optional animation dependency is `manim`; install it only for a Manim animation slot:

```bash
cd "$VIDEO_USE"
"$PYTHON" -m pip install -e '.[animations]'
```

The automated-youtube bundle additionally requires:

- `PyYAML` — centralized `config.yaml` loading.
- Google Workspace dependencies installed by the bundled setup script:
  - `google-api-python-client==2.194.0`
  - `google-auth==2.55.1`
  - `google-auth-oauthlib==1.3.1`
  - `google-auth-httplib2==0.3.1`
  - `httplib2==0.32.0`
  - `pyasn1==0.6.4`

Install the Google dependencies through the bundle, not ad-hoc unpinned versions:

```bash
"$PYTHON" "$BUNDLE/google-workspace/scripts/setup.py" --install-deps
"$PYTHON" -m pip install PyYAML
```

Completion criterion: the following import check exits successfully:

```bash
"$PYTHON" - <<'PY'
import yaml, requests, librosa, matplotlib, PIL, numpy
import googleapiclient, google.auth, google_auth_oauthlib, httplib2, pyasn1
print("Python dependencies: OK")
PY
```

## 4. Configure ElevenLabs transcription

`video-use/helpers/transcribe.py` uses ElevenLabs Scribe for word-level timestamps, speaker diarization, and audio events. Put the key in the repository root, never in a generated video folder or committed file:

```bash
printf 'ELEVENLABS_API_KEY=%s\n' '<KEY>' > "$VIDEO_USE/.env"
chmod 600 "$VIDEO_USE/.env"
```

If the key is already supplied in the environment, the helper can use `ELEVENLABS_API_KEY` without a dotenv file. Never print the key, include it in a command transcript, commit `.env`, or send it in a chat message.

Check presence without revealing its value:

```bash
if grep -q '^ELEVENLABS_API_KEY=.' "$VIDEO_USE/.env" 2>/dev/null; then
  echo "ElevenLabs key present"
else
  echo "ElevenLabs key missing"
fi
```

An optional quota-free credential check can call `https://api.elevenlabs.io/v1/user`; construct the `xi-api-key` header in a process without printing it. A `200` confirms the key; `401` means it is invalid or expired. Do not run transcription merely to test installation.

Completion criterion: the configured dotenv path exists, is mode `600` or otherwise private, and contains a non-empty `ELEVENLABS_API_KEY` without exposing the value.

## 5. Configure Google OAuth

The pipeline needs Google OAuth for YouTube, Drive, Sheets, and Docs. The bundled Google skill stores credentials under the active Hermes home:

```text
$HERMES_HOME/google_client_secret.json
$HERMES_HOME/google_token.json
```

Check first:

```bash
"$PYTHON" "$BUNDLE/google-workspace/scripts/setup.py" --check
```

If unauthenticated, use the Google Workspace setup workflow and authorize the services required by the pipeline. At minimum, grant YouTube, Drive, Sheets, and Docs access as required by the current setup implementation. Then run `--check` again.

Completion criterion: the check reports authenticated access, and live read/write verification succeeds for the configured source-tracking and Posting Schedule spreadsheets. Never claim a sheet write succeeded without reading the written range back.

## 6. Verify the complete installation without spending transcription credits

Run all checks below:

```bash
# Executables
command -v git
command -v python3
command -v ffmpeg
command -v ffprobe
command -v yt-dlp

# Repository helpers
"$PYTHON" "$VIDEO_USE/helpers/timeline_view.py" --help >/dev/null
"$PYTHON" "$VIDEO_USE/helpers/render.py" --help >/dev/null
"$PYTHON" "$VIDEO_USE/helpers/transcribe.py" --help >/dev/null

# Bundle config and source downloader syntax
"$PYTHON" "$BUNDLE/scripts/load_config.py" paths.video_use_repo
"$PYTHON" -m py_compile "$BUNDLE/youtube-source-downloader/scripts/select_and_download.py"

# Google auth
"$PYTHON" "$BUNDLE/google-workspace/scripts/setup.py" --check
```

Completion criterion: every command exits zero, the config resolves to the intended checkout, and no secret is printed.

## 7. Optional animation packages

Install these only when a pipeline request actually needs them:

- **Manim:** `cd "$VIDEO_USE" && "$PYTHON" -m pip install -e '.[animations]'`.
- **HyperFrames:** use `npx --yes hyperframes ...` inside `edit/animations/slot_<id>/`.
- **Remotion:** scaffold or install it inside the individual slot with `npx create-video@latest` or a project-local dependency.
- **Node.js 22+:** required by current HyperFrames workflows.

Do not install these globally as part of the base YouTube pipeline setup.

## Common pitfalls

1. **Using a different Python than the pipeline.** Always install with `$PYTHON`; otherwise imports may work in one shell but fail in Hermes.
2. **Only copying `SKILL.md`.** The helpers, static assets, and `pyproject.toml` must remain in the same `video-use` directory.
3. **`ffmpeg` works but helpers report it missing.** The helpers invoke bare `ffmpeg`/`ffprobe`; initialize Homebrew’s shell environment or add their directory to PATH for the pipeline process.
4. **Putting `.env` in the bundle or footage folder.** Keep it at the `video-use` repository root and keep it out of Git.
5. **Installing Manim/Remotion/HyperFrames unnecessarily.** They are optional animation engines and increase setup complexity; install per slot.
6. **Skipping Google read-back.** OAuth authentication alone does not prove the configured spreadsheet is accessible or writable.
7. **Running a transcription test during setup.** ElevenLabs Scribe consumes quota; verify helper `--help` and credentials instead.
8. **Using the wrong source spreadsheet.** Source deduplication and Posting Schedule are separate sheets; resolve both from `config.yaml`.

## Verification checklist

- [ ] Homebrew or the platform package manager is installed.
- [ ] Git, Python, FFmpeg, ffprobe, and yt-dlp are executable.
- [ ] Stable `browser-use/video-use` checkout exists and contains its helpers.
- [ ] `video-use` Python dependencies are installed in the pipeline interpreter.
- [ ] Pinned Google Workspace dependencies and PyYAML are installed.
- [ ] ElevenLabs `.env` exists at the configured repo root and contains a private non-empty key.
- [ ] Google OAuth token/client files exist under the active Hermes home.
- [ ] Google setup check succeeds and configured Sheets are accessible.
- [ ] Helper `--help`, config loading, and source-downloader compilation pass.
- [ ] No secrets were printed, committed, or stored in generated media directories.
