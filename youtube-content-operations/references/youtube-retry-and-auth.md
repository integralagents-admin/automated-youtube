# YouTube Retry and Auth Reference

## Resumable retry pattern

1. Read the source-specific `youtube_pipeline_manifest.json`.
2. Filter to `status != verified` and keep verified IDs untouched.
3. Check whether each stored `publishAt` is still in the future.
4. If not, capture one new UTC baseline and recompute only the remaining track slots.
5. Upload one item at a time with resumable `MediaFileUpload`.
6. Immediately call `videos.list(part='id,snippet,status')` and compare channel ID, title, privacy status, and `publishAt`.
7. Persist after each item.

## Web OAuth recovery pattern

Use a Google Cloud OAuth client of type **Web application** when the redirect is an HTTPS domain. Register the exact URI, including path and trailing slash behavior. Request both:

- `https://www.googleapis.com/auth/drive`
- `https://www.googleapis.com/auth/youtube.force-ssl`

Generate a PKCE authorization URL, persist `state`, `code_verifier`, and `redirect_uri`, then exchange the entire callback URL. Verify with a YouTube `channels.list(part='id', mine=True)` call rather than relying only on a generic Workspace check.

## Upload-limit behavior

`uploadLimitExceeded` can occur after a valid prefix of a batch has uploaded. Treat the prefix as successful only after read-back. Leave failed items in the manifest, do not re-upload verified IDs, do not delete YouTube videos, and do not trash the Drive source. A later retry should use future publish times for remaining items.

## Drive trash verification

Drive search queries may reject an `id` predicate. Verify cleanup by:

- `files.get(fileId=SOURCE_ID, fields='id,name,parents,trashed')`
- listing active children under the original queue parent
- checking that the exact source ID is absent from that listing

Use reversible trash, not permanent deletion, unless the user explicitly requests permanent deletion.
