#!/usr/bin/env bash
# Stage the automated-youtube Hermes skill bundle and push it to GitHub.
#
# - Reads GITHUB_API_TOKEN from ~/.hermes/.env (not GITHUB_TOKEN).
# - Excludes the nested video-use/.venv/ and the entire video-use/ and
#   yt-dlp/ git checkouts from the push.
# - Uses cp -a in the live->staging copy so a partial run never destroys
#   the live source.
# - Force-pushes main; refuses to clobber any other branch.
#
# Usage:
#   bash scripts/bundle_to_github.sh <github-name> [public|private]
#
# Defaults to private. Pass `public` to make the repo public.
set -euo pipefail

REPO_NAME="${1:-automated-youtube}"
VISIBILITY="${2:-private}"

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ENV_FILE="$HERMES_HOME/.env"
BUNDLE="$HERMES_HOME/skills/media/automated-youtube"
STAGING="$HERMES_HOME/.cache/automated-youtube-push"

if [ ! -d "$BUNDLE" ]; then
  echo "missing bundle directory: $BUNDLE" >&2; exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "missing $ENV_FILE" >&2; exit 1
fi

TOKEN="$(awk -F= '/^GITHUB_API_TOKEN=/ {print $2}' "$ENV_FILE" || true)"
if [ -z "$TOKEN" ]; then
  echo "could not read GITHUB_API_TOKEN from $ENV_FILE" >&2; exit 1
fi

is_private="$( [ "$VISIBILITY" = "private" ] && echo true || echo false )"

api="https://api.github.com"
login="$(curl -sS -H "Authorization: Bearer $TOKEN" "$api/user" \
  | python -c 'import json,sys;print(json.load(sys.stdin)["login"])')"
echo "github_login=$login  repo=$login/$REPO_NAME  visibility=$VISIBILITY"

# Create the repo if it does not exist; idempotent on rerun.
case "$(curl -sS -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer $TOKEN" "$api/repos/$login/$REPO_NAME")" in
  200) echo "repo exists — reusing" ;;
  404)
    body="$(python -c "import json;print(json.dumps({'name':'$REPO_NAME','description':'Operator Maxxing automated YouTube skill bundle','private':$is_private,'auto_init':True,'license_template':'mit'}))")"
    resp="$(curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H 'Accept: application/vnd.github+json' \
          -d "$body" "$api/user/repos")"
    if printf '%s' "$resp" | grep -q '"message"'; then
      echo "create failed: $resp" >&2; exit 1
    fi
    echo "repo created: https://github.com/$login/$REPO_NAME"
    ;;
  *) echo "unexpected GitHub status when probing repo" >&2; exit 1 ;;
esac

# Materialize the staging directory without touching the live source.
rm -rf "$STAGING"
mkdir -p "$STAGING"
shopt -s dotglob nullglob
for entry in "$BUNDLE"/*; do
  name="$(basename "$entry")"
  case "$name" in
    video-use|yt-dlp) continue ;;
  esac
  cp -a "$entry" "$STAGING/$name"
done

cat > "$STAGING/.gitignore" <<'EOF'
# External tool checkouts — not part of this skills bundle.
video-use/
yt-dlp/
.venv/
__pycache__/
*.pyc
EOF

cd "$STAGING"
[ ! -d .git ] && git init -b main >/dev/null
git config user.name "Xavier O"
git config user.email "xavier.o@users.noreply.github.com"
git add -A
git commit -m "Sync automated-youtube bundle" -q || echo "no changes to commit"

git remote remove origin 2>/dev/null || true
git remote add origin "https://$TOKEN@github.com/$login/$REPO_NAME.git"
git push -u origin main --force
echo "push_complete=ok  remote=https://github.com/$login/$REPO_NAME"
