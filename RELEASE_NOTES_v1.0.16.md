# Highlight Video Studio v1.0.16

## Highlights

- Added a dedicated Image AI provider with its own OpenAI-compatible endpoint, API key, and model selection.
- Added image-model discovery and a real generation probe through `/images/generations`.
- Added compatibility fallback for providers that return generated images through chat completions.
- Preserved the free and reliable video-frame thumbnail fallback when Image AI is disabled or unavailable.
- Added task-specific model routing for website articles and First Comments.
- Protected saved LLM and Image AI credentials: raw API keys are never returned to the browser.

## Rendering and subtitles

- Fixed highlight fallback and LLM under-return handling so the pipeline returns the exact requested clip count (bounded to 1–10 clips).
- Added source-caption collision cleanup for vertical renders before applying the new karaoke subtitle layer.
- Improved kinetic karaoke subtitles with three-word chunks, yellow active-word emphasis, and Windows-compatible Arial fallback.
- Reuses YouTube caption timestamps when available, avoiding repeated Whisper transcription for every rendered clip.
- Bundles `faster-whisper` and the local Small model so clean/offline-capable installations can transcribe videos without downloadable captions.
- Tuned NVENC/CPU rendering for faster output while retaining H.264/AAC compatibility and `faststart`.

## Publishing and packaging

- Fixed batch publishing to resolve real Page Tokens from the token vault instead of using masked browser values.
- Preserved First Comment and LLM Comment scheduling options.
- Installer includes portable Python, FFmpeg/FFprobe, Node.js, yt-dlp, required Python packages, and the local speech-recognition model.
- Installer upgrades preserve existing configuration and user data.

## Verification

- Python compile check: passed.
- Release guards: 14/14 passed.
- Exact-count fallback check: requested 3 clips, returned 3.
- 1080×1920 render canary generated and visually inspected, including source-caption cleanup and karaoke subtitle burn-in.
- Latest production code was exercised successfully in the installed application with HTTP health 200.

## Installation testing note

The prior v1.0.15 installer was successfully tested as an in-place upgrade. The final v1.0.16 installer was rebuilt and its payload/code was verified, but this exact final executable has not yet completed a separate clean-PC or full end-to-end overwrite installation test after the last rebuild.
