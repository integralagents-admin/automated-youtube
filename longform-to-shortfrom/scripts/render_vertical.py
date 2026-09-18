#!/usr/bin/env python3
"""Render selected transcript-backed clips as 9:16 MP4s with word pop subtitles."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def ass_time(seconds: float) -> str:
    cs = int(round(max(0.0, seconds) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, centis = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{centis:02d}"


def clean_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").strip()


def words_in_range(transcript: dict, start: float, end: float) -> list[dict]:
    return [
        w for w in transcript.get("words", [])
        if w.get("type") == "word" and float(w.get("end", 0)) > start and float(w.get("start", 0)) < end
    ]


def write_ass(transcript: dict, start: float, end: float, path: Path) -> None:
    words = words_in_range(transcript, start, end)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920",
        "ScaledBorderAndShadow: yes", "WrapStyle: 2", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,DejaVu Sans,74,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80101010,1,0,0,0,100,100,0,0,1,5,2,5,80,80,0,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    cursor = 0.0
    for i in range(0, len(words), 3):
        chunk = words[i:i + 3]
        for active_idx, active in enumerate(chunk):
            local_start = max(cursor, 0.0, float(active["start"]) - start)
            next_start = float(chunk[active_idx + 1]["start"]) if active_idx + 1 < len(chunk) else min(end, float(active["end"]) + 0.35)
            local_end = max(local_start + 0.05, min(end - start, next_start - start))
            rendered = []
            for j, word in enumerate(chunk):
                text = clean_text(str(word.get("text", "")))
                if j == active_idx:
                    rendered.append(r"{\c&H0000FFFF&\fscx112\fscy112}" + text + r"{\c&H00FFFFFF&\fscx100\fscy100}")
                else:
                    rendered.append(text)
            local_end = max(local_start + 0.05, local_end)
            lines.append(f"Dialogue: 0,{ass_time(local_start)},{ass_time(local_end)},Default,,0,0,0,,{{\\pos(540,1280)}}{' '.join(rendered)}")
            cursor = local_end
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def subtitle_filter(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return f"subtitles='{value}'"


def framing_filter(use_blur_background: bool = False) -> str:
    """Use a centered crop by default; blur extension is an explicit fallback."""
    if not use_blur_background:
        # Scale the source to fill 1080x1920, then crop the horizontal sides.
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    return ("split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=20:1[blur];"
            "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fit];"
            "[blur][fit]overlay=(W-w)/2:(H-h)/2")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("transcript", type=Path)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--blur-background", action="store_true", help="Use blurred full-frame extension instead of the default centered crop")
    args = ap.parse_args()
    transcript = json.loads(args.transcript.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for clip in manifest:
        clip_id = re.sub(r"[^A-Za-z0-9_-]+", "-", clip["id"]).strip("-")
        start, end = float(clip["start"]), float(clip["end"])
        ass = args.output_dir / f"{clip_id}.ass"
        out = args.output_dir / f"{clip_id}.mp4"
        write_ass(transcript, start, end, ass)
        vf = f"{framing_filter(args.blur_background)},{subtitle_filter(ass)}"
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-i", str(args.source), "-t", str(end - start),
            "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        results.append({"id": clip["id"], "path": str(out), "ass": str(ass), "start": start, "end": end})
        print(f"rendered {clip['id']}: {out.name}")
    (args.output_dir / "render_manifest.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
