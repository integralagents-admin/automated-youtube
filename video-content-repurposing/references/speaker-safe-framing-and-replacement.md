# Speaker-Safe Framing and Replacement Workflow

## Why fixed center crops fail

A 16:9 interview frame can place speakers far apart or off-center. A fixed `crop=1080:1920` center crop may remove one or both speakers even though the output remains technically valid 1080×1920 video.

## Validated safe default

For horizontal interview footage:

1. Split the source into background and foreground.
2. Scale/crop the background to fill 1080×1920 and apply blur.
3. Scale the complete source frame down to fit inside 1080×1920 without changing aspect ratio.
4. Overlay the fitted source over the blurred background.
5. Apply subtitles after the framing filter.

This preserves every speaker visible in the source frame. It may produce letterbox-style space around the fitted frame, but that is preferable to losing speakers.

Example FFmpeg filter structure:

```text
split=2[bg][fg];
[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:1[blur];
[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fit];
[blur][fit]overlay=(W-w)/2:(H-h)/2
```

## Review gate

Before upload, extract representative frames from the hook, middle, and payoff of every Short. Confirm that every relevant speaker is visible and not cut at the head or body. A montage is useful for batch review, but inspect individual frames when a speaker appears near an edge or when the clip changes camera framing.

Also verify with `ffprobe`:

- width: `1080`
- height: `1920`
- video stream present
- audio stream present
- playable duration

## Replacement protocol

If already-published Shorts are discovered to have bad framing:

1. Identify exact YouTube IDs and matching cloud-storage file IDs from manifests.
2. Read back each YouTube ID and storage ID before destructive actions.
3. Delete only the affected YouTube videos; move matching storage files to reversible trash rather than permanently deleting them.
4. Verify YouTube absence and storage `trashed=true` before rendering replacements.
5. Re-render with speaker-safe framing and complete technical/frame verification.
6. Upload replacements to the source-specific storage folder and read back parent, size, MIME type, and non-trashed state.
7. Schedule replacements only after the replacement manifest is complete. If YouTube returns an account upload limit, preserve the verified local/storage replacements and source; do not run source cleanup.

Persist separate replacement manifests so old IDs cannot be confused with replacement IDs.