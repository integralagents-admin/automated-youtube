---
name: cloud-file-lifecycle
description: Manage cloud files with auditable lifecycle workflows.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cloud storage, Drive, files, lifecycle, verification]
    related_skills: [google-workspace]
---

# Cloud File Lifecycle Skill

Use this class-level skill for repeatable cloud-file lifecycle operations: inventory, eligibility analysis, reversible cleanup, archival, and post-mutation verification. It emphasizes deterministic identifiers, explicit scope, bounded mutations, and reconciled audit reports. Provider-specific commands belong to the relevant integration skill; this skill governs the workflow around them.

## When to Use

- Cleaning up or archiving files based on a schedule, age, status, or other structured source.
- Reconciling a cloud file inventory against a spreadsheet, database, or manifest.
- Performing a batch lifecycle mutation that must be safe, reversible, and verifiable.
- Do not use for permanent deletion unless a separate workflow explicitly requires it and has a dedicated safety review.

## Prerequisites

- An authenticated provider integration skill, such as `google-workspace`.
- A structured source defining eligibility and a provider-side file identifier or exact matching key.
- A stated cutoff timezone and deletion mode.

For Google Drive workflows, read `references/drive-verification.md` before implementing or troubleshooting verification logic.

## Procedure

1. Establish the actor, provider, source dataset, cutoff timezone, and mutation mode. Completion criterion: all five are recorded before mutation.
2. Inventory the source rows and normalize only documented date formats. Preserve row numbers and source values in the audit record. Completion criterion: every source row is classified as eligible, ineligible, invalid, or incomplete.
3. Resolve targets by immutable provider ID first. If an ID is unavailable, require an exact unique match on a documented key such as filename; never fuzzy-match. Completion criterion: every eligible row is uniquely matched, already in the target state, missing, ambiguous, or excluded.
4. Exclude the source document, folders, non-target MIME types, and any files outside the declared scope. Completion criterion: exclusions are counted and explainable.
5. For destructive or state-changing operations, prefer the provider's reversible state (for example, Trash) and never silently escalate to permanent deletion. Completion criterion: the exact mutation command and reversibility are recorded.
6. Apply mutations serially or in a bounded batch with per-item results. Completion criterion: each intended target has a success or error result tied to its provider ID.
7. Verify by reading the provider's authoritative state, not by trusting the mutation response alone. If a convenience metadata endpoint omits the state field, use a provider query that returns the target-state population and filter locally by exact IDs. Completion criterion: verified-state count plus exceptions reconciles with mutation results.
8. Report the source, cutoff, totals, changed items, already-compliant items, and exceptions. Completion criterion: no eligible row is silently omitted and all claimed changes are independently verified.

## Quick Reference

- ID-first resolution.
- Exact matching only as fallback.
- Reversible mutation by default.
- Serial mutations with per-item results.
- Read-back verification from authoritative state.
- Reconcile declared totals programmatically.
- Never modify the source manifest unless explicitly requested.

## Pitfalls

- A successful mutation response is not proof that the provider persisted the desired state.
- Metadata wrappers may omit fields needed for verification; switch to a state-filtered listing rather than guessing from unchanged metadata.
- Provider query languages may not support equality on synthetic fields such as file ID; validate query syntax and use a supported broad state query with local exact-ID filtering when needed.
- Dates without a year require an explicit, documented year policy; do not infer across year boundaries silently.
- Duplicate source records must not cause duplicate mutations; deduplicate by immutable provider ID while preserving all source row references.
- Counts in the final report are hard assertions and must be computed from collected results.

## Verification

A lifecycle run is complete only when the number of classified eligible rows equals the sum of uniquely changed, already-compliant, missing, ambiguous, excluded, and failed items, and every claimed state change has a successful authoritative read-back. Report the exact provider IDs for failures and unverifiable results.
