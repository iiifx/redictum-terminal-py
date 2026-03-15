# Feature: Microphone test & selection command

## Summary

New subcommand `./redictum microphone` — interactive wizard to list available
microphones, test recording with a live RMS level meter, and save the selected
device to config.

## Motivation

- User reported 10-100x audio level difference between modes (bug turned out to be
  external — likely wrong mic or volume). A built-in mic test would help diagnose
  such issues instantly.
- Currently `recording_device` is auto-detected at first run and saved as "pulse"
  or "default" — no way to pick a specific device or verify it works.

## UX Flow

1. List available audio sources (PulseAudio sources via `pactl list sources short`
   and/or ALSA devices via `arecord -l`)
2. User selects a device from numbered list
3. 5-second recording test with live RMS bar in terminal:
   ```
   Speak into the microphone... (5 sec)
   [████████████░░░░░░░░░░░░░░░░░░] RMS: 4520
   ```
4. After test: show summary (average RMS, peak RMS, comparison with silence
   threshold)
5. Ask "Save this microphone to config?" → write `recording_device` to config.ini

## Technical Notes

- `arecord -D <device> -f S16_LE -r 16000 -c 1 -t raw` with stdout pipe
- Read PCM chunks (~100ms = 1600 samples) in a loop
- Calculate RMS per chunk: `(sum(s*s) / n) ** 0.5` (same as AudioProcessor.has_speech)
- Render live bar with Rich (already a dependency) — `Live` display or `\r` overwrite
- Duration: 5 seconds (configurable?)
- After test, show: avg RMS, peak RMS, silence threshold (200), verdict
  (good / too quiet / silent)

## Edge Cases

- No PulseAudio → fall back to ALSA device list
- Selected device fails to record → show error, let user pick another
- User has only one device → skip selection, go straight to test

## Integration

- Register `microphone` subcommand in `build_parser()`
- Add `run_microphone()` method to `RedictumApp`
- Does NOT require initialization — works standalone (like `setup`, `whisper`,
  `language`)
