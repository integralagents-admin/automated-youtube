# load_config

Single point of truth for every Drive ID, spreadsheet ID, and folder name
used by the automated-youtube skill bundle.

## How skills read values

```bash
# Resolve one or more dotted keys; prints `key=value` per line.
python "$HERMES_HOME/skills/media/automated-youtube/scripts/load_config.py" \
    posting_schedule.spreadsheet_id \
    drive.queues_root_folder_id
```

In Python (within a skill helper):

```python
from load_config import cfg
sheet_id = cfg("posting_schedule.spreadsheet_id")
```

## Overriding a value without editing `config.yaml`

Set an environment variable of the form `AUTOYT__<SECTION>__<KEY>`:

```bash
export AUTOYT__POSTING_SCHEDULE__SPREADSHEET_ID="new-sheet-id"
export AUTOYT__DRIVE__QUEUES_ROOT_FOLDER_ID="new-root-folder-id"
python scripts/load_config.py drive.queues_root_folder_id
# → drive.queues_root_folder_id=new-root-folder-id
```

Environment overrides win over `config.yaml`. Use this for one-off runs
or to point the bundle at a different Google account.

## When to change `config.yaml` directly

When you want the new IDs to persist across all future runs. Edit
`~/.hermes/skills/media/automated-youtube/config.yaml`, then run the skill.

## Where each key is used

| Key | Used by |
|---|---|
| `posting_schedule.spreadsheet_id` / `.spreadsheet_url` / `.tab_name` | `youtube-pipeline`, `youtube-scheduler`, `drive-cleanup` |
| `drive.queues_root_folder_id` | upload parents in every Drive write |
| `drive.source_queue_folder_id` | `raw-video-processesor` queue poll |
| `drive.shortform_root_folder_name` | `longform-to-shortfrom` |
| `drive.longform_root_folder_name` | `longform-to-clipped-longform` |
| `drive.thumbnails_root_folder_name` | `longform-thumbnail-analysis` |
| `youtube.*` | `youtube-scheduler` (cadence, privacy, category) |
| `paths.work_root_template` | clip workflows |
| `paths.bundle_root` / `.google_api_script` / `.video_use_repo` / `.yt_dlp_repo` | every component that calls the helper or checkouts |
| `transcription.*` | `longform-to-shortfrom`, `longform-to-clipped-longform`, `raw-video-processesor` |