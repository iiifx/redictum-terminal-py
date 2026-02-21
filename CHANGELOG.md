# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Remove duplicate comments in default YAML config template (language, prompt)
- Extract duplicated `_confirm()` method into a shared module-level function
- Defer sound tone generation until first play (lazy init in SoundNotifier)
- Skip cmake/build-essential check on every startup (only check at first run)
- Use `sys.executable -m pip` instead of bare `pip` for correct environment
- Replace `bash -c` with list-based subprocess calls in CUDA installer (security)
- Use secure temp files (mkstemp) with guaranteed cleanup in CUDA and whisper installers
- Stop logging transcribed text to file (privacy); log character count instead
- Add missing logging to Transcriber, AudioRecorder, ClipboardManager, SoundNotifier

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
