# Google Sheets API gotchas

Workarounds for behaviours that bit us in the Posting Schedule scheduler and pipeline runs.

## `values.get` silently truncates trailing empty cells

After `values.append`, calling `values.get` on the appended range often returns one fewer cell per row than you wrote — trailing empty trailing cells are dropped. So a 5-column write followed by `values.get` of the same range returns `[[Title, Video Link, Video Type, Thumbnail Link]]` per row, with the `Posted` value omitted entirely (not present as `""`).

**Symptom:** `intentional_rows != readback_rows` even though every write succeeded.

**Fix:** when verifying an append, compare only the columns you actually wrote. Either:

1. Write only the columns you intend to fill, then read back the same range and compare exactly.
2. Pad your comparison to ignore the last column(s) when the source row has no value there.

## `values.update` on a single cell

Use a `A2:A2`-style range for a single-cell update; `A2:A1` is rejected. Always pass the values as a 2D array even for one cell: `--values '[["09/09"]]'`.

## `values.append` reports `updatedCells`, not the appended rows

`values.append` returns `{"updatedCells": N}` — N is cells, not rows. Compute the appended row count as `updatedCells / len(values_columns)` and confirm against your intended list.

## File ID parsing from a `webViewLink`

A Drive `webViewLink` looks like `https://drive.google.com/file/d/<FILE_ID>/view?...`. Use the regex `r"/d/([A-Za-z0-9_-]+)/"`. The `<FILE_ID>` is also the same as the `id` field on the `files.get` response.

## Authoritative state verification for Drive deletes

`drive.get` after a trash operation often returns `trashed: None` (the field isn't always present). The authoritative check is the `trashed = true` listing query — search Drive for `trashed = true` and look for the file ID in the result set.

## Sheets `id = '...'` query is not supported through the workspace wrapper

The Drive search wrapper accepts `id = '...'` and returns 400. For "is this file in trash" verification, fall back to the broad `trashed = true` listing and filter client-side.