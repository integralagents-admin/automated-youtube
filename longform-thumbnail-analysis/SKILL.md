---
name: longform-thumbnail-analysis
description: Select transcript-backed thumbnail moments and captions.
version: 0.1.0
author: Xavier O, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [YouTube, Thumbnails, Longform Video, Transcripts, Google Drive]
    related_skills: []
---

# Longform Thumbnail Analysis Skill

Select strong thumbnail frames from longform clips, then create concise transcript-backed overlay captions with one emphasized word. The workflow is designed for business interviews, podcasts, and educational clips. It produces a 16:9 image, stores it in the correct Google Drive batch folder, and makes the paired video unambiguous from the filename.

## When to Use

- A longform clip needs a YouTube thumbnail.
- A batch of longform clips needs thumbnail concepts, rendered images, or Drive uploads.
- A user provides reference thumbnails and wants their visual rules applied.
- Do not use for Shorts thumbnails, unrelated image editing, or captions unsupported by the transcript.

## Prerequisites

- A playable longform MP4 and its transcript with word or phrase timestamps.
- `ffmpeg` and `ffprobe` available through `terminal`.
- `vision_analyze` available for frame and reference-image review.
- Google OAuth credentials with Drive write access at `$HERMES_HOME/google_token.json`.
- A stable source title, source ID, clip number, and YouTube title.
- The thumbnail font is **Google Sans Bold 700** (`GoogleSans-Bold.ttf`). Install it at the path returned by `transcription.google_sans_font_path` in `config.yaml` (default `~/.local/share/fonts/GoogleSans-Bold.ttf`); the shared renderer falls back to `ComicRelief-Bold.ttf` if Google Sans is missing. Source the file manually from a licensed copy of the Google Sans family — it is not on public CDNs.
- A thumbnail renderer. **Use `../scripts/render_thumbnail.py`** at the bundle root for the standard pipeline: it applies a subtle dark bottom gradient, a soft drop shadow on the caption, the Google Sans Bold 700 + emphasis-word treatment in one call, and matches the design rules below. Do not reinvent the styling in each skill — that drift is what produced mismatched thumbnails across the pipeline before.
- All Drive IDs, spreadsheet IDs, and folder names live in `~/.hermes/skills/media/automated-youtube/config.yaml`. Resolve them with `scripts/load_config.py`. Override any value per-run by setting `AUTOYT__<SECTION>__<KEY>` (see `scripts/README.md`).
- Required config keys before starting:
  - `drive.thumbnails_root_folder_name`
  - `drive.queues_root_folder_id`
  - `paths.google_api_script`

## References

- `../scripts/render_thumbnail.py` — shared thumbnail styler used by both this skill and the `youtube-scheduler` fallback path. Public API: `render(base_image, caption, emphasis_word, output_path, emphasis_color="#FFD21F")`.
- `../scripts/load_config.py` and `../scripts/README.md` — bundle config and override rules.

## Reference Design Rules

Use the supplied reference thumbnails as a style guide, not as content to copy:

- Use a 16:9 canvas and large mobile-readable typography.
- Prefer one emotionally legible face or two faces with clear conversational tension.
- Choose expressions such as surprise, concern, intensity, disagreement, curiosity, or engaged explanation.
- Keep backgrounds simple, dark, or strongly contrasted with the subject.
- Use concise overlay copy, normally 3–6 words.
- Use **Google Sans Bold 700** (`GoogleSans-Bold.ttf`) for all overlay text. The renderer will fall back to Comic Relief Bold if Google Sans is not installed, but the design assumes Google Sans.
- Place the caption horizontally across the bottom of the image over a *subtle* dark horizontal gradient — the gradient is intentionally faint (peak ~43% opacity) so the text lifts off the source frame without dimming the subject.
- Use generous safe padding: at least 7% of canvas width on the left and right, and at least 6% of canvas height above the bottom edge.
- Keep the caption to one or two horizontal lines, centered or optically balanced across the lower third.
- Use bold white text with a **soft drop shadow** (offset + Gaussian blur), not a hard outline. The shadow is what gives the text legibility against the subtle gradient.
- Emphasize exactly one important word with a contrasting color, commonly yellow.
- Keep the bottom caption clear of faces, hands, logos, and other important visual details; reposition or crop the selected frame when needed.
- Prefer tension, a warning, a surprising claim, or a concrete business problem over a generic topic label.

## How to Run

Use `terminal` for frame extraction, probing, rendering, and local verification. Use `read_file` for transcript and manifest inspection. Use `vision_analyze` to inspect reference images, candidate frames, and final thumbnails. Use the Google Workspace Drive wrapper or an authenticated Python client through `terminal` for folder creation, upload, and read-back verification.

## Procedure

1. **Normalize the batch.** Record the source title, source file ID, clip number, local video path, transcript path, YouTube title, and batch folder ID. Create or reuse the Drive folder whose name comes from `drive.thumbnails_root_folder_name`, then create or reuse a child folder named `<YYYY-MM-DD> — <source title> — <source file ID>`. Completion criterion: the batch metadata contains stable IDs and paths.

2. **Probe the clip.** Run `ffprobe` and confirm the file has video and audio, a valid duration, and a 16:9 or otherwise inspectable source frame. Completion criterion: the media probe passes before frame analysis begins.

3. **Find visual candidates.** Extract frames at regular intervals plus transcript-defined moments around the hook, central claim, conflict, example, and payoff. Prefer frames with clear faces, readable expressions, natural eye direction, uncluttered backgrounds, and enough negative space for text. Do not choose a frame where a speaker is cut off, blurred, eyes are closed, or the composition makes the overlay unreadable. Completion criterion: retain at least three candidate frames or document why fewer exist.

4. **Review candidates visually.** Use `vision_analyze` on the candidate contact sheet and, when needed, individual frames. Score each candidate for subject visibility, emotional clarity, contrast, composition, text-safe space, and fit with the clip’s promise. For two-person clips, preserve both speakers when the tension or exchange is central. Completion criterion: one primary frame and one backup frame are selected with written reasons.

5. **Read the transcript around the selected frame.** Inspect the surrounding transcript and timestamps. Identify the strongest self-contained promise, conflict, warning, or mechanism. The thumbnail caption must be supported by the spoken content and must not invent a claim. Completion criterion: the caption has a transcript citation interval and a one-sentence rationale.

6. **Write overlay options.** Produce three concise caption options, each normally 3–6 words. Favor question-led, warning-led, surprising-claim, or contrarian wording. Select exactly one important word for colored emphasis. Reject captions that merely repeat the YouTube title, use vague clickbait, require unseen context, or contain more than one emphasized word. Completion criterion: the chosen caption is specific, readable at thumbnail size, and transcript-backed.

7. **Render the thumbnail.** Create a 1280×720 or 1920×1080 PNG/JPEG. Use the selected frame as the base and add a *subtle* dark horizontal bottom gradient (~120 px tall, peak ~43% opacity black) that just lifts the text off the source frame without dimming the subject. Render the caption horizontally across the lower third with **Google Sans Bold 700** (`GoogleSans-Bold.ttf` — falls back to Comic Relief Bold), generous left/right and bottom padding, bold white text, a soft drop shadow (offset + Gaussian blur), and exactly one contrasting emphasized word. Keep the face unobstructed; if the caption conflicts with the subject, adjust line breaks, crop, or gradient strength rather than shrinking the text until it is unreadable. Completion criterion: the output has the requested dimensions, a valid image stream, one or two readable horizontal caption lines, the specified font, a subtle bottom gradient (not heavy), and safe padding.

8. **Name deterministically.** Use a filename that identifies the exact paired video without opening the file:

   `<batch slug> — <clip number> — <youtube title slug> — thumbnail.png`

   Normalize only filesystem-unsafe separators while preserving the meaningful title words. Never use `thumbnail.png`, `final.png`, or another generic name. Completion criterion: filename contains batch identity, clip number, and title slug.

9. **Review the final image.** Use `vision_analyze` on the rendered thumbnail. Confirm the face or faces are visible, the caption is legible, the emphasized word is visibly a different color, no text is clipped, and the image communicates the clip’s promise without unsupported claims. Fix and rerender up to three times. Completion criterion: final review passes all checks.

10. **Upload and verify Drive state.** Upload the image to the batch child folder. Read the returned file ID back and confirm the exact filename, image MIME type, parent folder, non-trashed state, and expected file size. Record the Drive ID, web link, selected frame timestamp, caption, emphasized word, transcript interval, and verification result in `thumbnail_manifest.json`. Completion criterion: every longform clip has exactly one verified thumbnail artifact.

## Caption Contract

```json
{
  "clip_id": "long-01",
  "frame_timestamp": 18.42,
  "caption": "YOUR CONTENT IS BORING",
  "emphasis_word": "BORING",
  "emphasis_color": "#FFD21F",
  "transcript_interval": [12.1, 24.8],
  "rationale": "The speaker explains why generic content fails to hold attention."
}
```

## Verification

For each thumbnail, verify:

```bash
ffprobe -v error -show_entries stream=codec_type,width,height -of json '<thumbnail>.png'
```

Then use `vision_analyze` to confirm:

- 16:9 dimensions.
- Face or faces are visible and not unintentionally cut off.
- Expression matches the clip’s emotional promise.
- Caption is rendered in Google Sans Bold 700 (or the configured fallback).
- Caption is horizontal and sits over a subtle bottom gradient in the lower third.
- At least 7% side padding and 6% bottom padding are preserved.
- Exactly one word is emphasized in another color.
- Caption is supported by the transcript.
- Filename identifies the paired video.
- Drive read-back confirms the correct batch folder and non-trashed image.

## Pitfalls

- Never invent a dramatic claim that the transcript does not support.
- Do not select a visually attractive frame that has no relationship to the clip’s actual promise.
- Avoid tiny text, long sentences, multiple highlighted words, low contrast, and text over eyes or mouths.
- Do not confuse the YouTube title with the thumbnail caption; the thumbnail should add tension or a complementary promise.
- Do not overwrite another batch’s thumbnail or reuse a generic filename.
- Do not upload an image before the final visual review and Drive read-back verification.
- Keep source videos and credentials out of the thumbnail folder.
