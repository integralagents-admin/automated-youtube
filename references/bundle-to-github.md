# Bundle → GitHub workflow

Push the `automated-youtube` skill bundle from disk to a new or existing GitHub repo.

## When to use

- A user wants the local bundle on GitHub for sharing, backup, or machine cloning.
- The bundle has been reorganized and needs to be re-published.
- A new skill was added to the bundle and should be versioned.

## Goals

- One private or public repo contains every Hermes skill component, the umbrella `SKILL.md`, and the `references/` files.
- The nested git-tool repos (`video-use/`, `yt-dlp/`) do NOT get pushed — they carry their own upstream histories.
- The `video-use/.venv/` is excluded so the repo stays small and free of binaries.

## Step-by-step

1. Resolve the GitHub token. On this machine it lives at `~/.hermes/.env` under the name `GITHUB_API_TOKEN` (not `GITHUB_TOKEN`). Read it as:

   ```bash
   awk -F= '/^GITHUB_API_TOKEN=/ {print $2}' ~/.hermes/.env
   ```

   Future machines may rename this — if the regex returns nothing, list the actual key names first with `grep -E '^GITHUB_[A-Z_]*TOKEN=' ~/.hermes/.env | cut -d= -f1`.

2. Derive the GitHub login from the API so the script picks the right namespace.

   ```bash
   curl -sS -H "Authorization: Bearer $TOKEN" https://api.github.com/user \
     | python -c 'import json,sys;print(json.load(sys.stdin)["login"])'
   ```

3. If the repo does not already exist, create it private with `auto_init=true` and `license_template=mit`. Use the API, not the dashboard.

4. Materialize a staging directory from the bundle. Copy, do NOT `mv`. `mv` leaves the live bundle without its umbrella `SKILL.md` and `references/` if the script aborts. The reusable script in `scripts/bundle_to_github.sh` uses `cp -a` so a halfway failure is recoverable and the live source is untouched.

5. Exclude the nested repos and the venv with a `.gitignore`:

   ```gitignore
   video-use/
   yt-dlp/
   .venv/
   __pycache__/
   *.pyc
   ```

6. `git init -b main`, commit, then `git push -u origin main --force`. The `--force` is safe because there is no remote history you can clobber — push the same way on every rerun.

7. Verify by listing the live remote tree (`/git/trees/main?recursive=1`) and confirming every directory under the bundle is represented plus the duplicate `references/references/...` file does not exist.

## Pitfalls

- Inline `terminal` payloads that combine `set -e`, multi-step shell, and `exit_code` capture can be refused by the shell parser as "Nested executable body could not be resolved". Always:
  - Write the workflow to `/tmp/...sh` (or `.hermes/cache/...`) and run `bash /tmp/...sh`.
  - Or invoke via `terminal(command="...", background=true)` with `notify=true` when the script is bounded and may run >600s.
  - Pair long background pushes with `process(action="wait")` rather than blocking the foreground.
- The .env variable name is `GITHUB_API_TOKEN`, not `GITHUB_TOKEN`. A bare `^GITHUB_TOKEN=` grep returns empty and silently fails authentication downstream.
- Do NOT `mv` the umbrella `SKILL.md` or `references/` into the staging directory. The result is silent loss of those files from the live bundle if the script errors out. Use `cp -a`.
- A naïve `cp -r src/* dst/` against a source that itself has a `references/` directory will produce `dst/references/references/...`. Always iterate with `shopt -s dotglob nullglob` + a per-entry `name` comparison when filtering.
- Always re-run `du -sh` before the push. Forgetting the cumulative size of `video-use/.venv/` (504 MB) or the `yt-dlp` checkout (93 MB) will inflate the repo to hundreds of MB.
- The GitHub fine-grained PAT must have `contents: write` on the target repo; legacy classic tokens need `repo`. Without write, `git push` returns `403` after a `200` on `/user`.
- Force push needs a separate user approval in Hermes. If force-push is blocked, stop and ask the user — never retry inline.
- After the first push, re-verify the remote tree explicitly. A buggy script (verified 2026-09-08) initially published without `youtube-content/` because the copy loop used a hardcoded list that did not include it.

## Verification

After a successful push:

- `git ls-tree --name-only origin/main` lists every directory present in the live bundle (excluding `video-use/` and `yt-dlp/`).
- `/git/trees/main?recursive=1` returns no path under `references/references/`.
- The umbrella's top-level `SKILL.md` and `references/component-layout.md` are present exactly once each.
- A user with no token can still `git clone` the repo (read-only is the minimum bar) or the token is recorded as the personal access token used to push.
