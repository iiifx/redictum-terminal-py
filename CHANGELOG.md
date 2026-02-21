# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Auto-detect working audio device on first run (`device: "auto"`) instead of hardcoding `pulse`
- Add timeout to clipboard copy/paste to prevent hanging when X11 session is lost
- Play error tone on empty recording instead of silent failure; log `arecord` exit code for diagnostics
- Catch fatal errors at top level: log full traceback and show user-visible message instead of silent death
- Recover from recorder crash: reset state to idle on `arecord` start failure instead of hanging forever
- Handle PEP 668 (`externally-managed-environment`): fallback chain apt → pip → `--break-system-packages`
- Fix first-run crash: defer `import yaml` until config file actually needs parsing
- Remove duplicate comments in default YAML config template (language, prompt)
- Extract duplicated `_confirm()` method into a shared module-level function
- Defer sound tone generation until first play (lazy init in SoundNotifier)
- Skip cmake/build-essential check on every startup (only check at first run)
- Use `sys.executable -m pip` instead of bare `pip` for correct environment
- Replace `bash -c` with list-based subprocess calls in CUDA installer (security)
- Use secure temp files (mkstemp) with guaranteed cleanup in CUDA and whisper installers
- Stop logging transcribed text to file (privacy); log character count instead
- Add missing logging to Transcriber, AudioRecorder, ClipboardManager, SoundNotifier
- Replace deprecated `locale.getdefaultlocale()` with `LANG`/`LC_ALL` env vars
- Include `_norm.wav` files in audio rotation (were accumulating indefinitely)
- Reap paplay child processes to prevent zombie accumulation

### Added
- Dev sandbox for interactive first-run testing in Docker (`sandbox/sandbox.sh`)
- Per-session log files with timestamp (`redictum_YYYYMMDD_HHMMSS.log`) and rotation
- Show config file path and examples after first run

### Changed
- Confirmation prompts now show default value (`[Y/n]` or `[y/N]`); Enter accepts default

## [1.0.0] - 2026-02-20

### Added
- Push-to-talk voice transcription (hold Insert key)
- Translate mode (hold Ctrl+Insert) — transcribe and translate to English
- Daemon mode: start, stop, status commands
- Whisper.cpp installer wizard with CUDA support and CPU fallback
- Audio normalization via ffmpeg loudnorm
- Clipboard save/restore (text, images, binary via X11 TARGETS)
- Sound notifications: 4 distinct tones (start, processing, done, error)
- File rotation for audio recordings and daily transcripts
- Language auto-detection from system locale
- YAML configuration with comments, generated on first run
- Auto-diagnostics and dependency installation (apt + pip)
- Graceful shutdown on SIGTERM/SIGINT
- Rich terminal UI (colors, spinners, icons) with plain-text fallback
- Application logging to logs/redictum.log
- `--config` flag to reset configuration
- `whisper` subcommand for install/check/reconfigure
- MIT license
