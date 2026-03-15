# Feature: Live console output in interactive mode

## Goal

Interactive mode (`./redictum`) should provide real-time visual feedback in the
console — state changes, processing progress, and transcribed text. Daemon mode
stays silent (logs only to file).

## Current behavior

Both modes are functionally identical — the main loop runs the same way, all
output goes only to the log file. The user has no visibility into what's happening
in interactive mode.

## Desired behavior (interactive mode)

Display in console:

- **State transitions**: idle → recording → processing → idle
  - e.g. `[Recording...]`, `[Processing...]`, `[Idle]`
- **Hotkey events**: when key is pressed/released
- **Transcription result**: the recognized text, printed after each cycle
- **Errors**: paste failures, whisper timeouts, etc.

Daemon mode: no console output, everything goes to the log file only.

## Design considerations

- How to format output: simple text lines? Rich status bar? Spinner?
- Should transcription text be visually distinct from status messages?
- Handling long transcriptions: truncate or wrap?
- Should we show recording duration / silence detection info?
- Integration with sound notifications: visual + audio feedback together
- Consider `--verbose` / `--quiet` flags for controlling output level
- Think about whether the banner + "Press Ctrl+C to stop" is enough of a
  differentiator or if we need a persistent status line
