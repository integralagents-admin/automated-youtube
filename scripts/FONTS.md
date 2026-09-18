# Fonts

The shared thumbnail styler (`scripts/render_thumbnail.py`) prefers **Google Sans
Bold 700** and falls back to Comic Relief Bold if it's missing.

## Install Google Sans Bold 700 (manual)

Google Sans is not on a public CDN at the exact Workspace font. The closest
publicly available font that ships under the "Google Sans" name on Google Fonts
is **Google Sans Flex**, which is what's currently installed at
`~/.local/share/fonts/GoogleSans-Bold.ttf` on this machine. It looks very
close to Workspace Google Sans in metric and style, but it is not the exact
same font binary. If you have the genuine Workspace font, drop it at the
same path with the same filename and the renderer will pick it up
immediately — no code change needed.

```bash
# After copying GoogleSans-Bold.ttf to ~/.local/share/fonts/, verify the renderer picks it up:
python3 ~/.hermes/skills/media/automated-youtube/scripts/render_thumbnail.py \
    ~/.hermes/workspaces/automated-youtube/thumbnail_backfill/row10-frame.jpg \
    "DISCOVER DONT INVENT" "INVENT" /tmp/test_thumb.png
```

## Search order

```python
GOOGLE_SANS_BOLD_CANDIDATES = (
    "~/.local/share/fonts/GoogleSans-Bold.ttf",
    "~/.local/share/fonts/Google Sans Bold.ttf",        # macOS-style with space
    "~/Library/Fonts/GoogleSans-Bold.ttf",
)
```

If none of those exist, the renderer falls back to
`~/.local/share/fonts/ComicRelief-Bold.ttf` so the pipeline never breaks.

## Sourcing the font

The Workspace Google Sans TTF comes from:

- macOS: `/Library/Fonts/GoogleSans-Bold.ttf` on any machine signed into Google Workspace.
- Windows: `%APPDATA%\Google\Fonts\` on a Workspace-signed PC.
- Google Fonts today only ships a near-equivalent ("Google Sans Flex") at
  <https://fonts.google.com/specimen/Google+Sans+Flex>.

## Manual install recipe

```bash
cp GoogleSans-Bold.ttf ~/.local/share/fonts/GoogleSans-Bold.ttf
python3 ~/.hermes/skills/media/automated-youtube/scripts/render_thumbnail.py
# A FileNotFoundError with a clear message is raised if no candidate exists.
```