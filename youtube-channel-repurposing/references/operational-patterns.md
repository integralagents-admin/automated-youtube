# Video Repurposing Operational Patterns

## Large Google Drive downloads

For large Drive media, ordinary wrapper downloads may exceed a foreground execution window. Use an authenticated `AuthorizedSession` request to `https://www.googleapis.com/drive/v3/files/<FILE_ID>?alt=media` with a `Range: bytes=<start>-<end>` header. Stream each 4 MiB response into `<output>.part`, resume from the existing byte count, retry transient request/connection timeouts up to five times with bounded backoff, and rename to the final path only when the byte count exactly matches Drive metadata. Probe the completed file with `ffprobe`; a partial MP4 can still appear probeable.

## Transcription quota gate

Before uploading audio to a paid transcription API, compare the source duration/estimated credits with the provider quota. If insufficient, stop before the paid request, preserve the source in its queue, and record `deletion_eligible: false`. Do not fabricate a transcript or infer exact word timings from an incomplete alternative.

## Shortform caption invariant

For 1080×1920 Shorts, generate one serialized subtitle event at a time. Prevent overlapping ASS dialogue events, use one visual line, and position the caption center around `(540,640)`—one-third of the frame height. Verify both the event intervals and a representative rendered frame.

## Transactional queue cleanup

Select queued media by exact Drive file ID, not filename. Store source metadata before processing. Require both shortform and 2–15 minute workflows to pass, all outputs to be verified, and all Drive uploads to be read back before moving the source to Drive trash. Re-read the exact source metadata immediately before deletion and verify it is trashed and absent from the active queue afterward.

## YouTube scheduled public releases

YouTube Data API scheduled publishing requires `status.privacyStatus = private` together with a future ISO 8601 `status.publishAt`. This is the API representation of a video that becomes public at the scheduled time. For the Operator Maxxing cadence, capture one UTC runtime baseline, set the first `publishAt` to baseline plus 20 minutes, and add exactly 20 minutes for each subsequent clip. Verify each returned video with `videos.list(part='snippet,status')`.
