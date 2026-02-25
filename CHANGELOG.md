# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Live console output in interactive mode: real-time status during recording,
  processing, and transcription. Respects `--verbose` and `--quiet`
- `update` command shows release notes from GitHub before the confirmation prompt
- `hotkey` command — interactive push-to-talk hotkey reassignment
- Mouse button support in hotkeys (back, forward, middle and combos with modifiers)

### Changed
- Extract `SoundPlayerBackend` ABC from `SoundNotifier`: platform-specific `paplay` logic moved to `PaplayPlayer`, tone generation stays in `SoundNotifier`

### Fixed
- Volume not fully restored when multiple redictum instances run simultaneously

## [1.7.0] - 2026-02-24

### Changed
- Deduplicate optional dependency checking: three methods (`_check_optional_sound`,
  `_check_optional_normalize`, `_check_optional_paste`) replaced with a single generic
  `_check_optional_dep` driven by declarative `_OptionalDep` dataclass
- Extract `_display_language` / `_confirm_and_save_language` helpers to remove
  duplicated language display+save code from `run_language` and `_first_run_language_check`
- Extract `_rotate_dir` helper to deduplicate `rotate_audio`, `rotate_transcripts`,
  `rotate_logs`
- Extract `_record_run_timestamp` and `_fix_optional_mismatch` helpers to deduplicate
  shared blocks in `run_interactive` and `run_start`
- Rename `--config` flag to `--reset-config` for clarity; restrict to interactive
  mode only — using with subcommands now prints an error instead of silently
  deleting config
- Auto-infer config value types from `DEFAULT_CONFIG`: replace manual `_BOOL_KEYS`,
  `_INT_KEYS`, `_FLOAT_KEYS` frozensets with a single `_KEY_TYPES` dict derived
  automatically from default values — new config keys get correct type parsing
  without manual registration

## [1.6.0] - 2026-02-24

### Added
- Auto-reduce system volume during recording to prevent mic picking up speaker audio
  (music, YouTube, Meet). Volume drops to a configurable percentage of current level
  and restores immediately when recording stops. Config: `recording_volume_reduce`,
  `recording_volume_level` in `[audio]` section. Enabled by default (30%)
- Auto-sync config file after update: missing keys are added from the current template
  with default values, user settings preserved. Backup saved as `config.ini.bak`
- Ruff linter (`ruff.toml`): rules E, F, W, I, UP, B with Python 3.10 target
- pytest-cov coverage reporting with 75% minimum threshold
- 95 new unit tests: VolumeController, ConfigManager.sync(), SoundNotifier,
  HotkeyListener runtime, Daemon lifecycle, RedictumApp pipeline
- GitHub Actions CI: lint → test → e2e pipeline (`.github/workflows/ci.yml`)
- Dev dependencies file (`requirements-dev.txt`): pytest, pytest-cov, ruff

### Fixed
- Fix regex injection in `ConfigManager.update()` and YAML migration: backslashes in
  config values (e.g. Windows paths) could crash or corrupt the config file
- Truncated stderr in error messages now shows last 500 chars (tail) instead of first 200 (head),
  capturing the actual root cause (e.g. CUDA errors) instead of generic prefixes
- Full stderr/stdout is now logged on failure for whisper-cli, ffmpeg, and cmake —
  previously lost due to truncation
- Fix `raise` without `from` in exception chains (5 places) — proper exception chaining per B904

## [1.5.0] - 2026-02-24

### Added
- `--verbose (-v)` and `--quiet (-q)` CLI flags for output verbosity control

## [1.4.0] - 2026-02-24

### Added
- `update` command — check for new releases and update the script in-place with SHA-256 verification

## [1.3.0] - 2026-02-24

### Added
- Runtime state file (`.state`): replaces `.initialized` marker with persistent JSON state
  (version tracking, build metadata, UI state)
- `whisper` command: "Rebuild whisper.cpp?" option — rebuild with or without CUDA at any time
- `whisper` command: "Change model?" option — switch model without reinstalling
- `whisper` command: models are preserved across rebuilds (backup + restore)

### Fixed
- Daemon mode (`start`) no longer runs interactive setup when not initialized —
  prints error and exits instead of hanging on prompts with `stdin=/dev/null`
- `StateManager.save()` is now atomic (tmpfile + rename) — prevents `.state`
  corruption if process is killed during write
- Fix `SoundNotifier._ensure_tones()` race condition: concurrent threads could
  create duplicate temp dirs and corrupt the tone cache
- Replace busy-loop polling in `_graceful_shutdown()` with `threading.Event` for
  instant pipeline completion detection
- `has_speech()` now parses WAV chunks properly instead of hardcoding 44-byte header
  skip — prevents garbage RMS values on files with extra metadata chunks
- GPU detection: verify actual GPU backend via test transcription instead of only
  checking ldd — eliminates false "CUDA active" when GPU is linked but not working
- Remove quotes from whisper language prompts — model was hallucinating
  guillemets/brackets around transcribed text
- E2E tests: place fake whisper-cli and model at default config paths so first-run
  init passes without interactive prompts

### Changed
- `whisper` wizard: reorder steps — build decisions before model selection and GPU probe
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
