#!/usr/bin/env python3
"""Shared Operator Maxxing thumbnail styler.

Wraps the subtle bottom-gradient + Google Sans Bold 700 caption + emphasis-word
pipeline used by both `longform-thumbnail-analysis` (transcript-backed captions)
and the `youtube-scheduler` thumbnail-fallback path (generated captions from
the title).

Public API:
    render(base_image_path: str | Path, caption: str, emphasis_word: str,
            output_path: str | Path, emphasis_color: str = "#FFD21F") -> Path

The base image is resized to 1280x720, gets a thin (~120px) dark fade-up gradient
anchored at the lower edge, and has the caption rendered in Google Sans Bold
700 across the lower third with a soft drop shadow (offset + Gaussian blur,
not a hard outline). Word wrap is automatic: long captions drop to a smaller
font size; the wrapped total width must fit 1280 - 160px (8% side padding on
each side).

Environment:
    GoogleSans-Bold.ttf is expected at the path returned by `transcription.google_sans_font_path`
    in `config.yaml` (default: ~/.local/share/fonts/GoogleSans-Bold.ttf). If that file
    is missing, the renderer falls back to the next available Google Sans weight, then
    to ComicRelief-Bold.ttf at ~/.local/share/fonts/ComicRelief-Bold.ttf. PIL is required.

Pitfalls:
    - Use an explicit emphasis word. If you pass the whole caption, every word
      will be highlighted and the result will be visually broken.
    - Do not pass `caption` longer than 8 words; the renderer will keep shrinking
      the font size and may produce a cramped single line.
    - Returns the path to the rendered PNG.
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --- Font candidates (preferred first) ---
GOOGLE_SANS_BOLD_CANDIDATES = (
    Path(os.path.expanduser("~/.local/share/fonts/GoogleSans-Bold.ttf")),
    Path(os.path.expanduser("~/.local/share/fonts/Google Sans Bold.ttf")),
    Path(os.path.expanduser("~/Library/Fonts/GoogleSans-Bold.ttf")),
)
COMIC_RELIEF_BOLD = Path(os.path.expanduser("~/.local/share/fonts/ComicRelief-Bold.ttf"))

# --- Canvas + layout ---
CANVAS = (1280, 720)
GRADIENT_HEIGHT = 120  # thinner → subtler; was 220
GRADIENT_TOP = CANVAS[1] - GRADIENT_HEIGHT  # 600
GRADIENT_MAX_ALPHA = 110  # peak alpha 0–255; ~43% opacity black at the bottom edge
SIDE_PADDING = 0.07  # 7% left/right
CAPTION_BASELINE = 558  # y of the bottom line of glyphs
SAFE_BOTTOM_PCT = 0.06  # 6% above the bottom edge — keep text out of safe area

# --- Type scale ---
MIN_FONT = 36
DEFAULT_FONT = 64
FALLBACK_FONT = 48

# --- Shadow ---
SHADOW_OFFSET = (0, 3)  # px down
SHADOW_BLUR = 6  # px Gaussian blur radius
SHADOW_ALPHA = 215  # 0–255 — how dark the shadow itself is


def _resolve_font_path() -> Path:
    for cand in GOOGLE_SANS_BOLD_CANDIDATES:
        if cand.exists():
            return cand
    if COMIC_RELIEF_BOLD.exists():
        return COMIC_RELIEF_BOLD
    raise FileNotFoundError(
        "No thumbnail font found. Install GoogleSans-Bold.ttf or ComicRelief-Bold.ttf "
        f"under ~/.local/share/fonts/ (searched: "
        f"{', '.join(str(p) for p in GOOGLE_SANS_BOLD_CANDIDATES + (COMIC_RELIEF_BOLD,))})."
    )


def _resolve_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_resolve_font_path()), size)


def _fits(draw: ImageDraw.ImageDraw, words: list[str], font: ImageFont.FreeTypeFont) -> bool:
    widths = [draw.textlength(w, font=font) for w in words]
    space_w = draw.textlength(" ", font=font)
    total = sum(widths) + space_w * (len(words) - 1)
    return total <= CANVAS[0] * (1 - 2 * SIDE_PADDING)


def _pick_font(draw: ImageDraw.ImageDraw, words: list[str]) -> ImageFont.FreeTypeFont:
    if _fits(draw, words, _resolve_font(DEFAULT_FONT)):
        return _resolve_font(DEFAULT_FONT)
    if _fits(draw, words, _resolve_font(FALLBACK_FONT)):
        return _resolve_font(FALLBACK_FONT)
    return _resolve_font(MIN_FONT)


def _apply_gradient(img: Image.Image) -> None:
    """Subtle dark fade at the very bottom of the canvas.

    Peak alpha at the bottom edge is GRADIENT_MAX_ALPHA (default 110, ~43% black)
    and decreases linearly to 0 at GRADIENT_TOP. The gradient is intentionally
    weak so it just lifts the text off the source frame without dimming the
    subject.
    """
    grad = Image.new("RGBA", (CANVAS[0], GRADIENT_HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(GRADIENT_HEIGHT):
        # y=GRADIENT_HEIGHT-1 (bottom) -> max alpha; y=0 (top) -> 0 alpha
        t = y / (GRADIENT_HEIGHT - 1)
        alpha = int(GRADIENT_MAX_ALPHA * t)
        gd.line([(0, y), (CANVAS[0], y)], fill=(0, 0, 0, alpha))
    img.paste(grad, (0, GRADIENT_TOP), grad)


def _measure(draw: ImageDraw.ImageDraw, words: list[str], font: ImageFont.FreeTypeFont):
    widths = [draw.textlength(w, font=font) for w in words]
    space_w = draw.textlength(" ", font=font)
    total = sum(widths) + space_w * (len(words) - 1)
    return widths, space_w, total


def _draw_caption(img: Image.Image, caption: str, emphasis_word: str,
                  emphasis_color: str = "#FFD21F") -> None:
    draw = ImageDraw.Draw(img)
    words = caption.upper().split()
    emphasis_word = (emphasis_word or "").upper().strip(".,!?\"'")
    if not emphasis_word or emphasis_word not in words:
        emphasis_word = max(words, key=len) if words else ""

    font = _pick_font(draw, words)
    widths, space_w, total = _measure(draw, words, font)
    start_x = (CANVAS[0] - total) / 2
    y = CAPTION_BASELINE

    # --- Pre-compute per-word positions ---
    positions = []
    x = start_x
    for w, ww in zip(words, widths):
        positions.append((w, ww, x))
        x += ww + space_w

    # --- Render text twice: shadow pass, then colour pass on top ---
    # Shadow layer (drawn on a separate RGBA canvas so we can blur it cleanly).
    shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    for w, ww, x in positions:
        sd.text((x + SHADOW_OFFSET[0], y + SHADOW_OFFSET[1]), w, font=font, fill=(0, 0, 0, SHADOW_ALPHA))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR))
    img.paste(shadow_layer, (0, 0), shadow_layer)

    # Colour layer (the visible text on top of the shadow).
    for w, ww, x in positions:
        color = emphasis_color if w == emphasis_word else "white"
        draw.text((x, y), w, font=font, fill=color)


def render(base_image_path: str | Path,
           caption: str,
           emphasis_word: str,
           output_path: str | Path,
           emphasis_color: str = "#FFD21F") -> Path:
    base = Path(base_image_path)
    out = Path(output_path)
    if not base.exists():
        raise FileNotFoundError(f"base image missing: {base}")
    img = Image.open(base).convert("RGB").resize(CANVAS, Image.LANCZOS)
    _apply_gradient(img)
    _draw_caption(img, caption, emphasis_word, emphasis_color=emphasis_color)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 5:
        print("Usage: render_thumbnail.py <base.jpg> <caption> <emphasis> <out.png>", file=sys.stderr)
        sys.exit(2)
    render(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])