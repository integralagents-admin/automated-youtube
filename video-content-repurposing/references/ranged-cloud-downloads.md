# Ranged Cloud Downloads

Use this pattern when a cloud-hosted video is large or a normal download wrapper times out.

## Recipe

1. Read provider metadata first and record the exact expected byte size.
2. Download fixed byte ranges with an authenticated session, writing to `<output>.part`.
3. Resume from the existing `.part` size; never restart or append from an unverified offset.
4. Require a non-empty response for every range and stop on a short response unless it is the final range.
5. Rename `.part` to the final output only when its size exactly equals provider metadata.
6. Run `ffprobe` and verify complete duration plus both audio and video streams.

## Integrity Rules

- Keep access tokens, cookies, and authorization headers out of logs and manifests.
- Do not call a partial file a successful download merely because `ffprobe` can parse its header.
- If the provider does not expose reliable size metadata, verify completion with its checksum or a provider-supported download status before editing.
- Use bounded retries for transient range failures; preserve the current verified byte offset between retries.
