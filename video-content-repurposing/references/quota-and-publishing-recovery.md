# Quota and Publishing Recovery

## Transcription quota recovery

A long source can download successfully while transcription is rejected by provider quota. Treat this as a resumable stage boundary:

1. Keep the local source and queue record.
2. Record the provider error and required/remaining quota in the run manifest.
3. Do not start editorial selection on a partial transcript.
4. After quota is increased, rerun the transcription helper against the unchanged local source and reuse the cached result for all downstream workflows.
5. Verify word-level timestamps and packed-transcript coverage before rendering.

In the tested run, a 105m53s source required 1,941 ElevenLabs credits while only 672 remained. After quota recovery, transcription completed with 48,475 word timestamps.

## Large Drive download recovery

For multi-gigabyte Drive sources, ordinary requests may time out while reading a large range. Preserve the `.part` file and resume from its exact byte count. Use smaller streamed ranges, a connect/read timeout, and bounded retries for transient request errors. After completion, compare the local byte count with Drive metadata before probing media.

## Scheduled YouTube publishing

Capture the UTC baseline once before the first upload. Derive slot `n` as `baseline + interval * (n + 1)`. For scheduled public release, the API payload must use `privacyStatus: private` with a future `publishAt`; verify the returned resource with `videos.list` and confirm channel ownership, title, privacy state, and exact publish time.

Write the manifest after every upload. If YouTube returns `uploadLimitExceeded` or another non-transient account quota error, retain verified IDs, mark the failed item, and stop source cleanup. Do not retry all uploads or rerun the processor; the next run should resume only the failed item after the limit is cleared. A successful upload response alone is insufficient without read-back verification.
