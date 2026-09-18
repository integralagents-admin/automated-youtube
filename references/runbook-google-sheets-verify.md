# Google Sheets append-and-verify pattern

How to append verified rows to `posting_schedule.spreadsheet_id` and prove the write actually landed. The `youtube-pipeline` and `drive-cleanup` skills both depend on this pattern.

## The pattern

1. Read the sheet with `sheets get <id> <tab>!A:Z`. Treat the first row as headers; every subsequent row is data.
2. Build the dedup set from `(Title, Video Link)` tuples of the existing data rows. New rows whose tuple is already in the set are skipped, not appended.
3. Build the candidate `new_rows` array. Every row has the full column count even when trailing cells are empty (e.g. `["Title", "Video Link", "Long", "Thumbnail Link", ""]`).
4. Call `sheets append <id> <tab>!A:E --values '<json>'` and verify the response includes `updatedCells` matching `len(new_rows) * len(headers)`.
5. Re-read the exact appended range: `sheets get <id> <tab>!A<start>:E<end>` where `start = len(existing_rows) + 1` and `end = start + len(new_rows) - 1`.

## The trailing-empty-cell trap

`values.get` (the underlying Sheets API call behind `sheets get`) returns trailing empty cells as absent, not as `""`. A row you appended as `["Title", "Video Link", "Long", "Thumbnail Link", ""]` reads back as `["Title", "Video Link", "Long", "Thumbnail Link"]`. Naive equality between `intended_rows` and `verified_rows` will fail by element count on the trailing column.

The fix is to compare column-by-column and treat a missing trailing element as `""`:

```python
def row_matches(intended, actual):
    return all((actual[i] if i < len(actual) else "") == intended[i]
               for i in range(len(intended)))

assert all(row_matches(n, v) for n, v in zip(new_rows, verified_rows))
```

## Re-read row indices

The sheet can have unrelated rows added or appended-to between your `existing_rows` snapshot and your append. Always derive `start_row` from `len(existing_rows) + 1` immediately after the read in the same Python process. If you read once, then append, then read again to verify, the second read might include the rows you just appended — re-derive `start_row` from the snapshot.

## What "verified" means here

- `sheets append` returned a response with `updatedCells` matching `len(new_rows) * column_count`.
- The re-read range returned `len(new_rows)` rows (some may have fewer elements due to the trailing-empty-cell behavior).
- The column-by-column match passed.
- No row in the previous data range changed (sample-check at least one prior row's `Title` and `Video Link` if you re-read the full tab).

## Common pitfalls

- Do not use `sheets update` to write to a "next free row" range. `update` writes exactly the values you pass; missing trailing cells are filled with `""`, which is fine, but the row you overwrite is the one at the target address, not the next free row. `append` is the correct primitive.
- Do not compute the `start_row` from a stale snapshot. If any earlier row was added between your read and your append, your verification will read the wrong range.
- Do not assume the API returns `""` for empty cells. It returns them as absent.
- Do not skip the read-back entirely. A successful `append` response is not proof of correct cell values — only the read-back is.

## Worked example

```python
import json, subprocess

GAPI = "..."  # resolved from paths.google_api_script
SHEET_ID = "..."  # resolved from posting_schedule.spreadsheet_id
TAB = "Sheet1"

# 1. Read existing
existing = json.loads(subprocess.check_output(
    ["python", GAPI, "sheets", "get", SHEET_ID, f"{TAB}!A:Z"], text=True))
existing_pairs = {(r[0], r[1]) for r in existing[1:]}

# 2. Build new rows (each has full column count)
new_rows = [["Title A", "https://drive...", "Short", "", ""],
            ["Title B", "https://drive...", "Long", "https://drive...", ""]]

# 3. Dedup
new_rows = [r for r in new_rows if (r[0], r[1]) not in existing_pairs]

# 4. Append
result = subprocess.run(
    ["python", GAPI, "sheets", "append", SHEET_ID, f"{TAB}!A:E",
     "--values", json.dumps(new_rows)], capture_output=True, text=True, check=True)

# 5. Re-read
start = len(existing) + 1
end = start + len(new_rows) - 1
verify = json.loads(subprocess.check_output(
    ["python", GAPI, "sheets", "get", SHEET_ID, f"{TAB}!A{start}:E{end}"], text=True))

# 6. Column-by-column verify
for i, (intended, actual) in enumerate(zip(new_rows, verify)):
    for j in range(len(intended)):
        actual_cell = actual[j] if j < len(actual) else ""
        assert actual_cell == intended[j], f"row {i} col {j}: {actual_cell!r} != {intended[j]!r}"
```