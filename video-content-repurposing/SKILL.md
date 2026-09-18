---
name: video-content-repurposing
description: Repurpose longform video into verified shortform assets.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Video, Repurposing, Shortform, Transcription, Captions, Cloud Storage]
    related_skills: []
---

# Video Content Repurposing Skill

Convert a user-provided longform video link into a set of independently understandable shortform assets. The workflow is source-agnostic: resolve the link through the appropriate authenticated provider or downloader, obtain word-level transcript timing, select clips with deliberate hooks and complete insights, render vertical outputs with animated captions, verify them, and deliver them to the requested cloud destination.

This is a class-level production workflow, not a platform-specific downloader. Keep provider quirks and session-specific recipes in `references/` rather than expanding the main procedure with one-off details.

## When to Use

- A user provides a longform video link and wants Shorts, Reels, TikToks, or other shortform derivatives.
- A podcast, interview, webinar, livestream, lecture, or business video contains multiple reusable ideas.
- Don't use for a single arbitrary trim, full-length publishing, or clips that cannot stand alone.

## Prerequisites

- `terminal` access to the source provider/downloader and `ffmpeg`/`ffprobe`.
- A word-level transcription provider and its credential in a secret store or provider-approved `.env`; never print or upload credentials.
- A writable per-source work directory outside the editing skill checkout.
- Authenticated cloud storage when the user requests uploads; check credentials before the first read or write.
- If a provider requires cookies, use only an explicitly supplied owner-only cookie file. Never inspect browser cookies without explicit user authorization.

## Procedure

1. **Resolve the exact link.** Preserve the original link in `manifest.json`. Detect the provider from the URL. Use the provider’s authenticated API for cloud-hosted files, a supported downloader for public media sites, or a direct media download only when access details were explicitly supplied. Completion criterion: the source is present locally and its expected size is known or independently verifiable.

2. **Verify source integrity.** Run `ffprobe` and require at least one video and one audio stream. For large cloud files, use resumable/ranged downloads when the ordinary wrapper is slow or times out; append only from the verified current byte offset and compare the final byte count with provider metadata. Completion criterion: the final file size matches metadata and `ffprobe` reads the complete duration.

3. **Transcribe once at word granularity.** Use verbatim word timestamps, speaker labels when available, and audio-event tags when useful. Cache the transcript by source identity and do not retranscribe an unchanged source. Completion criterion: the cached transcript contains usable word start/end times covering the source.

4. **Analyze the transcript for opportunities.** Use the running model to review the full transcript, not only the first apparent highlights. Candidates must contain a concrete insight, tactic, mechanism, example, warning, or mental model and must be understandable without unseen context. Record timestamp, quote, hook, insight, standalone rationale, and confidence in a machine-readable candidate manifest.

5. **Make the opening hook-first.** Treat the first seconds as an editorial gate. Prefer a stated question, explicit topic introduction, surprising claim, tension, or concrete problem. Start on the first useful hook words. Never begin with pondering, prefacing, pauses, throat-clearing, or filler such as “um,” “uh,” “well,” “so,” “I think,” or “let me see” while the speaker is still finding the point. If clean context cannot be achieved without awkward reconstruction, reject the candidate even when its later insight is valuable. Record `hook_type` and `opening_cut_note` for every candidate.

6. **Use transcript-safe boundaries.** Snap both edges to word boundaries, include only the setup required for comprehension, and end after the payoff. Do not cut inside words, remove the answer’s necessary setup, or leave unresolved references. Keep the normal target within 20–90 seconds unless a longer duration is necessary for a complete insight. Completion criterion: every selected candidate has a standalone-context justification and no pre-hook filler.

7. **Render for the target platform with speaker-safe framing.** Default to 9:16 at 1080×1920. Never use a fixed center crop for interviews, podcasts, or any shot containing multiple speakers unless a frame review proves every relevant speaker remains visible. The safe default is to fit the complete horizontal source frame inside the vertical canvas with a blurred full-frame background; preserve natural proportions and never stretch faces. Use speaker-aware cropping only when the active speaker is confidently localized and all speakers needed for the clip remain visible throughout the selected interval. Preserve intelligible audio and use short fades where cuts could pop. Apply captions after crop and other overlays. Completion criterion: every output is a playable MP4 with the intended dimensions and audio, and representative-frame review confirms each relevant speaker is visible and acceptably positioned.

   See `references/speaker-safe-framing-and-replacement.md` for the validated multi-speaker framing and replacement workflow.

8. **Create animated word-level captions.** Generate ASS or an equivalent timed track from transcript words offset to each clip’s output timeline. Use readable chunks and safe margins. In the requested style, inactive words remain white with a dark outline/shadow while the current word briefly changes to an accent color and slightly enlarges. Verify at representative frames that the active word visibly differs and timing follows speech.

9. **Self-evaluate before delivery.** Inspect the hook, middle, payoff, and ending of every output. Check standalone comprehension, hook clarity, word-boundary cuts, caption legibility/timing, crop quality, audio pops, dimensions, and duration. Fix failures and rerender, with a bounded retry count. Completion criterion: a verification manifest records a pass for every delivered asset.

10. **Organize and deliver.** Maintain one stable global destination folder and create a child folder for each source. Upload only verified final assets and useful audit manifests. Read back each returned file/folder record by ID and verify its parent, name, MIME type, and link. Completion criterion: the reported count exactly matches the verified count in storage.

## Output Contracts

Candidate manifests should include:

```json
{
  "id": "clip-01",
  "start": 412.38,
  "end": 468.91,
  "hook": "The opening question or claim",
  "hook_type": "question",
  "opening_cut_note": "Starts on the first clean hook word; excludes hesitation.",
  "insight": "The concrete value delivered",
  "standalone_context": "Why this works without the rest of the source",
  "quote": "Transcript-backed excerpt",
  "confidence": 0.91,
  "source_url": "<exact user link>"
}
```

Verification manifests should include one record per selected asset with local path, duration, width, height, audio presence, subtitle evidence, self-evaluation result, and cloud file ID/link when uploaded.

## Pitfalls

- Do not fabricate transcript text, timestamps, file IDs, upload results, or verification outcomes.
- Do not treat a probeable partial download as complete; compare bytes with source metadata.
- Do not let a technically valid but weak opening pass merely because the later content is valuable.
- Do not use phrase-level timestamps when word-level timing is available.
- Do not upload sources, previews, temporary subtitle files, credentials, or failed renders.
- Do not claim a total without programmatically checking the enumerated records.
- Do not turn a provider-specific failure into a permanent rule; preserve only the tested recovery pattern in a reference file.

## Downstream Publishing and Failure Gates

When the workflow includes cloud publishing or scheduled release, separate the production gate from the publishing gate. First verify every rendered asset and every storage upload by reading the exact returned IDs back. Then capture one UTC scheduling baseline and derive all publish times from it; never let upload duration create schedule drift. For YouTube scheduled-public publishing, upload with `privacyStatus: private` and a future `publishAt`, then verify each resource with a read-back API call before treating it as complete.

Persist a machine-readable manifest after each asset so an interrupted or quota-limited run can resume without duplicating verified uploads. Distinguish `verified`, `failed`, and `not_attempted`. If a provider returns an account upload limit or another non-transient quota error, stop the destructive cleanup gate: preserve the source and all successful outputs, record the exact failed asset, and retry only that asset after the limit is cleared. Never trash the source merely because most outputs succeeded.

For long sources, a transcription quota failure is a pre-processing blocker, not a reason to discard the downloaded source. Preserve the local source and retry transcription after quota recovery; do not re-download or retranscribe unchanged sources unnecessarily.

## References

- See `references/ranged-cloud-downloads.md` for the resumable-download pattern and integrity checks.
- See `references/quota-and-publishing-recovery.md` for tested quota-recovery and scheduled-publishing manifest patterns.

## Verification

Use `terminal` to run `ffprobe` on every final MP4 and use `read_file` to inspect the candidate and verification manifests. Use the relevant cloud-storage read operation to verify every uploaded ID before reporting success.
