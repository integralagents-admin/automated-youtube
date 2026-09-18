# Validated Runbook: Queue Processing and Publishing

This reference records tested patterns from Operator Maxxing queue runs.

## Large Drive downloads

- Record the exact Drive file ID, parent, `createdTime`, and provider byte size before downloading.
- Use a `.part` file and ranged streaming in bounded chunks. Resume from the current byte offset after transient HTTPS read timeouts.
- Replace the `.part` file only after the final byte count exactly matches Drive metadata and `ffprobe` confirms audio and video streams.

## Transcription quota recovery

- Estimate provider usage before sending a long source to paid transcription.
- If quota is insufficient, stop before the API call, preserve the local source, and retry the unchanged source after quota recovery.
- Cache word timestamps and pack the transcript once; do not re-download or retranscribe unchanged media.

## YouTube upload-limit recovery

- Persist a machine-readable manifest after every upload and verify each video with `videos.list`.
- On `uploadLimitExceeded`, stop the cleanup gate, keep the source in the queue, and resume only failed assets after the limit clears.
- Never duplicate IDs already marked `verified` and never rerun production solely because publishing was partially blocked.

## Scheduling policy

Capture one UTC baseline per run. Schedule the first Short and first longform clip at baseline +20 minutes. Schedule later Shorts one hour apart within the Short track and later longform clips two hours apart within the longform track. Use YouTube `privacyStatus: private` plus future `publishAt`; verify the returned resource before reporting it.

## Caption policy

For 1080×1920 Shorts, serialize subtitle events so only one visual line is active at a time. Place the caption center at `\pos(540,1280)`, the lower one-third mark (one-third of frame height up from the bottom). Inactive words are white; the active word gets accent color and a slight scale pop.
