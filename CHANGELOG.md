# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Runtime state file (`.state`): replaces `.initialized` marker with persistent JSON state
  (version tracking, build metadata, UI state)

### Fixed
- Daemon mode (`start`) no longer runs interactive setup when not initialized —
  prints error and exits instead of hanging on prompts with `stdin=/dev/null`
- E2E tests: place fake whisper-cli and model at default config paths so first-run
  init passes without interactive prompts

### Changed
- Rename `docker/` → `e2e/` to reflect the directory's purpose (E2E test infrastructure)

## [1.2.1] - 2026-02-22

### Fixed
- Fix `os.umask(0)` in daemon mode: all files were created world-writable (now `0o022`)
- Fix PID file created without explicit permissions: use atomic `O_EXCL` creation with `0o644`
- Add apt package name validation in `_install_apt()` to prevent command injection (defense-in-depth)
- Reject invalid boolean values in config instead of silently treating them as `false`

## [1.2.0] - 2026-02-22

### Added
- `./redictum setup` subcommand to re-run optional dependency setup (force-check all features, re-enable on install)
- Startup detection of missing optional tools: warns and offers to install/disable when a dependency disappears after setup
- Logging for subcommands (`setup`, `whisper`, `language`): each creates a labeled log file (`redictum_setup_*.log`, etc.)
- Language selector wizard: `./redictum language` to change transcription language
- First-run language prompt: offer to change auto-detected language on first start
- Comprehensive diagnostics logging: dependency checks, package installation, and user prompt responses are now written to the log file
- System information logged at startup: OS, kernel, Python, GPU, CUDA, RAM, locale
- Language-dependent prompts (`LANGUAGE_PROMPTS`): 15 built-in prompts auto-selected by transcription language (en, zh, hi, es, ar, fr, pt, ru, de, ja, uk, ko, it, tr, pl)

### Changed
- Make paplay, ffmpeg, xdotool optional with interactive prompts; choice persisted in config
- Remove `rich` from mandatory pip dependencies (plain-text fallback already exists)
- Defer cmake/build-essential install to whisper.cpp build step

### Fixed
- Abort setup when user declines critical dependencies instead of entering broken main loop
- Fix race condition: read `_current_mode` under `state_lock` in `on_release()`
- Validate whisper CLI and model paths on startup with clear error messages
- Increase clipboard restore delay from 200ms to 300ms; add configurable `paste_restore_delay`
- Validate config value types on load: reject invalid int/float with clear error message
- Add silence detection (RMS energy gate) to prevent whisper hallucinations on silent recordings
- Refactor `_main_loop` monolith into focused methods: `_on_hold`, `_on_release`, `_run_pipeline`, `_graceful_shutdown`
- Fix English prompt overriding `-l ru` on large whisper models: auto-select prompt by language
- Suppress false `[ERROR] arecord exited with code 1` on normal recording stop (SIGTERM is expected)

## [1.1.0] - 2026-02-21

### Fixed
- Show "Download whisper model?" instead of "Install whisper.cpp?" when only model is missing
- Prevent transcript log failure from blocking clipboard paste (catch OSError separately)
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
- CLI config overrides: `--set section.key=value` to override any config option at runtime
- Auto-discover existing whisper models when configured model is missing (offer to pick or download new)
- Dev sandbox for interactive first-run testing in Docker (`sandbox/sandbox.sh`)
- Per-session log files with timestamp (`redictum_YYYYMMDD_HHMMSS.log`) and rotation
- Show config file path and examples after first run

### Changed
- Migrate config from YAML to INI format (`config.yaml` → `config.ini`); removes PyYAML dependency
- Config structure flattened to 2 levels: `[section]` + `group_key` (e.g., `[dependency] whisper_cli`)
- All string values support optional double quotes (stripped automatically on read)
- Existing `config.yaml` is auto-migrated to `config.ini` on first load (backup saved as `.yaml.bak`)
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
