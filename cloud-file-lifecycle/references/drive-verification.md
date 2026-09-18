# Google Drive State Verification Notes

## Why broad-state filtering is useful

The compatibility wrapper's `drive get FILE_ID` response may omit the `trashed` field even after a successful reversible delete. Do not infer the state from unchanged metadata or from the mutation response alone.

Use a supported broad query for the authoritative state population:

```bash
GAPI="python ${HERMES_HOME:-$HOME/.hermes}/skills/media/automated-youtube/google-workspace/scripts/google_api.py"
$GAPI drive search "trashed = true" --raw-query --max 100
```

Parse the JSON result and filter locally by the exact expected file IDs. Compare the resulting ID set with the intended mutation set. This avoids relying on unsupported query predicates such as `id = 'FILE_ID'`, which can return Drive API `400 Invalid Value` errors through this wrapper.

## Reconciliation checklist

- Keep the expected IDs in a set.
- Count matching IDs returned by the trashed listing.
- Report missing expected IDs as unverifiable, not successful.
- Preserve the returned name, MIME type, and web link for the audit report.
- Use a larger or paginated listing when the candidate population can exceed the requested page size.

This technique is specific to verification of Drive state; it does not justify broad deletion queries or fuzzy matching.
