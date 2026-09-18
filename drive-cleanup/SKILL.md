---
name: drive-cleanup
description: Trash Drive videos whose schedule dates have passed.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Google Drive, Google Sheets, cleanup, video]
    related_skills: [google-workspace]
---

# Drive Cleanup Skill

Use this skill to reconcile the Posting Schedule spreadsheet with Google Drive and trash videos whose scheduled dates are already past. The operation is intentionally limited to reversible Drive trashing: never permanently delete files, and never alter the spreadsheet.

## When to Use

- The user explicitly asks to run Drive cleanup against the Posting Schedule sheet.
- A scheduled job explicitly invokes this cleanup.
- Do not use for deleting arbitrary Drive files, changing schedule rows, or permanently deleting files.

## Prerequisites

- Google Workspace authentication with Drive and Sheets scopes.
- All Drive IDs, spreadsheet IDs, and folder names live in `~/.hermes/skills/media/automated-youtube/config.yaml`. Resolve them with `scripts/load_config.py`. Override any value per-run by setting `AUTOYT__<SECTION>__<KEY>` (see `scripts/README.md`). Never hard-code IDs from a previous run.
- Required config keys before starting:
  - `posting_schedule.spreadsheet_name` (used as the search match target)
  - `posting_schedule.spreadsheet_id` (when known — bypasses name search)
  - `posting_schedule.tab_name`
  - `paths.google_api_script`

Before the first API call, run `terminal(command="python <paths.google_api_script expanded>/../scripts/setup.py --check")` to confirm Drive and Sheets scopes are authenticated. Stop if authentication is unavailable.

## How to Run

Run the workflow through Hermes' `terminal` tool. Resolve every key with `scripts/load_config.py` so swapping IDs is a one-line config edit.

```bash
BUNDLE="$HERMES_HOME/skills/media/automated-youtube"
GAPI="python $($BUNDLE/scripts/load_config.py paths.google_api_script)"
SHEET_NAME="$($BUNDLE/scripts/load_config.py posting_schedule.spreadsheet_name)"
SHEET_ID="$($BUNDLE/scripts/load_config.py posting_schedule.spreadsheet_id)"
TAB_NAME="$($BUNDLE/scripts/load_config.py posting_schedule.tab_name)"

$GAPI drive search "name = '$SHEET_NAME'" --raw-query --max 20
$GAPI sheets get "$SHEET_ID" "$TAB_NAME!A:Z"
$GAPI drive get FILE_ID
$GAPI drive delete FILE_ID
```

## Procedure

1. Check Google authentication. Completion criterion: setup reports `AUTHENTICATED` or `AUTHENTICATED (partial)` with Drive and Sheets scopes.
2. Search Drive for an exact spreadsheet name of `posting_schedule.spreadsheet_name`. If `posting_schedule.spreadsheet_id` is already known and resolves cleanly, prefer the ID and skip the name search. If the name search returns zero or multiple plausible spreadsheets, stop and report the candidates rather than guessing. Completion criterion: exactly one source spreadsheet is selected by ID.

3. Read the sheet's used range on tab `posting_schedule.tab_name`. If the spreadsheet contains multiple tabs, identify the tab containing schedule rows and headers such as `Posted`, `Date`, `Scheduled`, `Video`, `Filename`, `Drive ID`, or `Drive URL`. If no unambiguous schedule tab or date column exists, stop. Completion criterion: the selected tab, header row, date column, and video-identification column are recorded.

4. Obtain today's date in UTC. Parse each schedule date strictly, supporting ISO dates and unambiguous `MM/DD/YYYY` or `MM/DD/YY`; do not reinterpret ambiguous values silently. A row is eligible only when its parsed date is earlier than today. Completion criterion: every eligible row has a valid date and an identifiable video reference.
5. Resolve each eligible video. Prefer a Drive file ID parsed from a Drive URL or ID column. Otherwise use an exact filename match in Drive; do not use fuzzy or title-only matching. Exclude folders, the Posting Schedule spreadsheet, and non-video MIME types. Completion criterion: each candidate is classified as uniquely matched, already trashed, missing, ambiguous, or excluded.
6. Build a complete audit record containing source spreadsheet ID, tab, row number, schedule date, video reference, resolved Drive file ID/name, and reason. Write the audit record to a temporary local JSON file if the batch is large. Completion criterion: candidate count equals the number of classified eligible rows, with no silent omissions.
7. Trash every uniquely matched, non-trashed video using `$GAPI drive delete FILE_ID` without `--permanent`. This skill is authorized to proceed without an additional conversational confirmation when it was explicitly invoked for cleanup. Never call the permanent-delete form. Completion criterion: every intended unique file has a successful trash response.
8. Verify each mutation by fetching the exact Drive file ID or checking its trashed state through the Drive API. Completion criterion: every successful trash response is confirmed as trashed; report exceptions separately.
9. Report totals and an itemized exception list. Include the spreadsheet ID/tab, UTC cutoff date, trashed file IDs/names, already-trashed files, missing/ambiguous matches, and verification status.

## Quick Reference

- Source sheet: name `posting_schedule.spreadsheet_name`, ID `posting_schedule.spreadsheet_id`, tab `posting_schedule.tab_name`.
- Cutoff: schedule date `<` current UTC date.
- Match order: Drive ID/URL, then exact filename.
- Mutation: Drive trash only; omit `--permanent`.
- Never modify the sheet.
- Never fuzzy-match or permanently delete.

## Pitfalls

- A date equal to today is not past and must not be trashed.
- Use UTC consistently, including the cutoff reported to the user.
- Do not confuse a row's publish/post date with an upload or modified date from Drive.
- Duplicate spreadsheet names are unsafe; stop rather than select by recency.
- Duplicate filenames are unsafe unless the sheet provides an exact Drive ID or URL.
- A successful delete command is not sufficient; verify the file's trashed state.
- Keep API calls bounded and serial for mutations so partial batches can be reconciled.

## Verification

The run is complete only when the final report's trashed count, verified-trashed count, and exception count reconcile with the classified eligible rows. For each claimed deletion, the exact Drive file ID must be verified as trashed. If any verification fails, report the file ID and error and do not claim full completion.
