#!/usr/bin/env python3
"""Select, download, and record one fresh YouTube source for the pipeline."""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Reuse the bundle's centralized config loader.
BUNDLE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BUNDLE / "scripts"))
from load_config import cfg  # noqa: E402

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def col_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def canonical_id(entry: dict[str, Any]) -> str | None:
    raw = str(entry.get("id") or entry.get("url") or "")
    if VIDEO_ID_RE.fullmatch(raw):
        return raw
    match = re.search(r"(?:v=|youtu\.be/|shorts/|/embed/)([A-Za-z0-9_-]{11})", raw)
    return match.group(1) if match else None


def published_key(entry: dict[str, Any]) -> tuple[int, str]:
    timestamp = entry.get("timestamp")
    if isinstance(timestamp, (int, float)):
        return int(timestamp), str(entry.get("upload_date") or "")
    date = str(entry.get("upload_date") or "")
    try:
        return int(datetime.strptime(date, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp()), date
    except ValueError:
        return 0, date


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return json.loads(completed.stdout)


def load_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    token_path = home / "google_token.json"
    creds = Credentials.from_authorized_user_file(str(token_path))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        os.chmod(token_path, 0o600)
    if not creds.valid:
        raise RuntimeError(f"Google token is not valid: {token_path}")
    return creds


def sheets_service():
    from googleapiclient.discovery import build
    return build("sheets", "v4", credentials=load_credentials(), cache_discovery=False)


def get_rows(service, spreadsheet_id: str, tab: str) -> list[list[str]]:
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"{tab}!A:Z"
    ).execute()
    return result.get("values", [])


def ensure_headers(service, spreadsheet_id: str, tab: str, required: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{tab}!A1:{col_name(len(required))}1",
            valueInputOption="RAW",
            body={"values": [required]},
        ).execute()
        return required
    headers = list(rows[0])
    missing = [header for header in required if header not in headers]
    if missing:
        headers.extend(missing)
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{tab}!A1:{col_name(len(headers))}1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()
    return headers


def append_source(service, spreadsheet_id: str, tab: str, headers: list[str], metadata: dict[str, str]) -> list[str]:
    # The source-tracking sheet intentionally receives only its first four
    # columns. Download timestamps, local paths, status, and probe evidence
    # remain in source_manifest.json rather than being written to Sheets.
    write_headers = headers[:4]
    row = [metadata.get(header, "") for header in write_headers]
    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{tab}!A:D",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
    updated = result.get("updates", {}).get("updatedRange")
    if not updated:
        raise RuntimeError("Sheets append returned no updated range")
    readback = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=updated
    ).execute().get("values", [])
    if not readback or [str(x) for x in readback[0]] != row:
        raise RuntimeError(f"Source row read-back mismatch for {metadata['Video ID']}")
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--yt-dlp", default=cfg("paths.yt_dlp_binary", "yt-dlp"))
    parser.add_argument("--ffprobe", default=cfg("paths.ffprobe_binary", "ffprobe"))
    args = parser.parse_args()
    work = Path(args.work_dir).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)

    sources = ast.literal_eval(cfg("source_tracking.sources", required=True))
    if not isinstance(sources, list) or not sources:
        raise RuntimeError("source_tracking.sources must be a non-empty array")
    limit = int(cfg("source_tracking.candidate_limit", 50))
    state_path = Path(cfg("source_tracking.rotation_state_file", required=True)).expanduser()
    if not state_path.is_absolute():
        state_path = Path(cfg("paths.work_root", required=True)).expanduser() / state_path
    state = json.loads(state_path.read_text()) if state_path.exists() else {"next_index": 0}
    start = int(state.get("next_index", 0)) % len(sources)
    sheet_id = cfg("source_tracking.spreadsheet_id", required=True)
    tab = cfg("source_tracking.tab_name", "Sheet1")
    required = ast.literal_eval(cfg("source_tracking.required_columns", required=True))
    service = sheets_service()
    rows = get_rows(service, sheet_id, tab)
    headers = ensure_headers(service, sheet_id, tab, required, rows)
    id_index = headers.index("Video ID")
    recorded = {str(row[id_index]) for row in rows[1:] if len(row) > id_index and row[id_index]}

    selected: tuple[int, dict[str, Any], str, dict[str, Any]] | None = None
    for offset in range(len(sources)):
        source_index = (start + offset) % len(sources)
        listing = run_json([
            args.yt_dlp, "--flat-playlist", "--dump-single-json", "--skip-download",
            "--playlist-end", str(limit), sources[source_index],
        ])
        candidates = sorted(listing.get("entries") or [], key=published_key, reverse=True)
        for entry in candidates:
            video_id = canonical_id(entry)
            if video_id and video_id not in recorded:
                selected = (source_index, entry, video_id, listing)
                break
        if selected:
            break
    if selected is None:
        raise RuntimeError("No unrecorded video was found in the configured channel rotation")

    selected_source_index, entry, video_id, listing = selected
    source_url = f"https://www.youtube.com/watch?v={video_id}"
    output_template = str(work / f"{video_id}.%(ext)s")
    run_env = os.environ.copy()
    ffmpeg_path = str(Path(cfg("paths.ffmpeg_binary", "ffmpeg")).expanduser().parent)
    run_env["PATH"] = ffmpeg_path + os.pathsep + run_env.get("PATH", "")
    subprocess.run([
        args.yt_dlp, "--no-playlist", "--merge-output-format", "mp4",
        "--output", output_template, source_url,
    ], check=True, env=run_env)
    candidates = [p for p in work.glob(f"{video_id}.*") if p.suffix.lower() not in {".json", ".part"}]
    if not candidates:
        raise RuntimeError("yt-dlp completed but no downloaded media file was found")
    local_path = max(candidates, key=lambda path: path.stat().st_size)
    if local_path.stat().st_size <= 0:
        raise RuntimeError("Downloaded media file is empty")
    probe = subprocess.run([
        args.ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type",
        "-of", "json", str(local_path),
    ], check=True, capture_output=True, text=True)
    probe_data = json.loads(probe.stdout)
    stream_types = {stream.get("codec_type") for stream in probe_data.get("streams", [])}
    if not {"video", "audio"}.issubset(stream_types):
        raise RuntimeError(f"Downloaded media lacks video/audio streams: {sorted(stream_types)}")
    duration = str(probe_data.get("format", {}).get("duration") or "")

    metadata = {
        "Video ID": video_id,
        "Source URL": source_url,
        "Channel": str(entry.get("channel") or listing.get("channel") or sources[selected_source_index]),
        "Title": str(entry.get("title") or ""),
        "Published At": str(entry.get("upload_date") or entry.get("timestamp") or ""),
        "Downloaded At": utc_now(),
        "Local Path": str(local_path),
        "Status": "Downloaded",
    }
    append_source(service, sheet_id, tab, headers, metadata)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"next_index": (selected_source_index + 1) % len(sources), "last_video_id": video_id, "updated_at": utc_now()}, indent=2))
    manifest = {
        "source": metadata,
        "probe": {"duration_seconds": duration, "stream_types": sorted(stream_types), "bytes": local_path.stat().st_size},
        "rotation_start_index": start,
        "selected_source_index": selected_source_index,
        "local_source_deleted": False,
    }
    (work / "source_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
