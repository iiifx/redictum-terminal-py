# CLAUDE.md

> Project map for AI agents. Keep this file up-to-date as the project evolves.

## Project Overview
System-wide voice-to-text CLI utility for Linux. Captures hotkeys, records microphone audio, transcribes via whisper.cpp, and pastes text into active input. Supports two modes: transcription (Insert) and translate-to-English (Ctrl+Insert).

## Tech Stack
- **Language:** Python 3.10+ (stdlib + pynput)
- **CLI Framework:** argparse (stdlib)
- **Config:** configparser (stdlib, INI format with comments, `config.ini` next to script)
- **State:** JSON file (`.state`) via `StateManager` — version tracking, build metadata, UI state
- **Audio Recording:** arecord (ALSA utils, via subprocess)
- **Audio Processing:** FFmpeg (via subprocess)
- **Transcription:** whisper.cpp CLI (downloaded as tarball, built locally)
- **Keyboard Hotkeys:** pynput
- **Clipboard:** xclip / xdotool (via subprocess)
- **Terminal UI:** rich (optional, plain-text fallback)
- **Architecture:** Single-file executable (`redictum`)

## Project Structure
```
redictum-terminal-py/
├── redictum                  # Main executable (chmod +x, single file, ~4500 lines)
├── CLAUDE.md                 # This file — project structure map
├── CHANGELOG.md              # Keep a Changelog format + SemVer
├── README.md                 # GitHub README
├── LICENSE                   # MIT
├── docker-compose.yml        # E2E test runner
├── release-checksum.sh       # Generate redictum.sha256 for releases
├── pytest.ini                # Pytest configuration
├── requirements-dev.txt      # Dev dependencies (pytest, coverage, ruff)
├── ruff.toml                 # Ruff linter configuration
├── .coveragerc               # Coverage configuration
├── .gitignore
├── .github/
│   └── workflows/ci.yml      # CI pipeline
├── tests/                    # Unit tests (pytest, 502 tests)
│   ├── conftest.py
│   ├── test_app.py
│   ├── test_app_pipeline.py
│   ├── test_audio_processor.py
│   ├── test_audio_recorder.py
│   ├── test_clipboard_manager.py
│   ├── test_config_manager.py
│   ├── test_config_manager_sync.py
│   ├── test_daemon.py
│   ├── test_daemon_lifecycle.py
│   ├── test_diagnostics.py
│   ├── test_diagnostics_logging.py
│   ├── test_directory_manager.py
│   ├── test_helpers.py
│   ├── test_hotkey_listener.py
│   ├── test_hotkey_runtime.py
│   ├── test_housekeeping.py
│   ├── test_language_selector.py
│   ├── test_sound_notifier.py
│   ├── test_state_manager.py
│   ├── test_transcriber.py
│   ├── test_hotkey_command.py
│   ├── test_update.py
│   ├── test_verbose_quiet.py
│   └── test_volume_controller.py
├── e2e/                      # E2E test infrastructure (Docker, 19 tests)
│   ├── Dockerfile
│   ├── run_e2e.sh
│   ├── fake-arecord
│   ├── fake-paplay
│   └── fake-whisper-cli
├── sandbox/                  # Dev sandbox for interactive testing in Docker
│   ├── Dockerfile.sandbox
│   └── sandbox.sh
├── .wip/                     # WIP docs: bugs, features, ideas (gitignored)
│   ├── bug-*.md              # One bug per file
│   ├── feature-*.md          # One feature per file
│   ├── done/                 # Completed items
│   └── research/             # Research notes
├── .claude/                  # Claude Code configuration + skills
└── .venv/                    # Python virtual environment

# Generated at runtime (next to redictum script):
├── config.ini                # User-editable config (INI, auto-generated on first run)
├── .state                    # Runtime state (JSON, managed by StateManager)
├── audio/                    # Recorded audio files (rotated)
├── transcripts/              # Daily transcription logs
└── logs/                     # Per-session log files (rotated)
```

## Key Entry Points
| File | Purpose |
|------|---------|
| `redictum` | Main CLI entry point (argparse, all classes in one file) |
| `config.ini` | Runtime config, auto-generated with comments (INI format) |
| `.state` | Runtime state (JSON), managed by `StateManager` |

## CLI Commands
| Command | Description |
|---------|-------------|
| `./redictum` | Interactive mode (diagnostics, init, push-to-talk loop) |
| `./redictum start` | Start daemon |
| `./redictum stop` | Stop daemon |
| `./redictum status` | Show daemon status |
| `./redictum setup` | Re-run optional dependency setup |
| `./redictum language` | Change transcription language |
| `./redictum whisper` | Setup whisper.cpp (install, check, reconfigure) |
| `./redictum hotkey` | Change push-to-talk hotkey |
| `./redictum update` | Update to the latest version |
| `./redictum --reset-config` | Delete config + state, force full re-setup |
| `./redictum --set k=v` | Override any config option at runtime |
| `./redictum --verbose` | Verbose logging output |
| `./redictum --quiet` | Suppress non-essential output |
| `./redictum --version` | Print version |
| `./redictum --help` | Show help |

## Design Principles

1. **Single-file executable** — `redictum` is the only deliverable artifact. No install scripts, no archives, no pip. Just `curl + chmod +x` and it works.
2. **Subprocess over libraries** — minimal Python packages. Core work is done via subprocess and system CLI tools (arecord, ffmpeg, xclip, xdotool, paplay).
3. **Fail-fast diagnostics** — two-stage check at startup: critical deps (Python 3.10+, Linux, PulseAudio, ALSA, X11) fail immediately; installable deps (ffmpeg, xclip, pynput, rich) are offered for auto-install.
4. **Defaults hardcoded in code** — config is generated from code defaults (single source of truth). User only changes what they need. Missing keys fall back to defaults.
5. **Logic separated from I/O** — single-responsibility classes. Unit tests cover logic, not system calls.
6. **Code quality** — PEP 8, type hints everywhere, Google-style docstrings, typed exceptions (no bare `except:`), named constants (no magic numbers), ruff for linting.
7. **Graceful shutdown** — SIGTERM/SIGINT → stop recording → wait for transcription to finish → remove PID file → exit cleanly.

## Code Architecture (inside `redictum`)
| Class | Purpose |
|-------|---------|
| `RedictumApp` | Orchestrator, wires components, CLI dispatch |
| `ConfigManager` | Load/generate/merge config.ini (INI with comments, 2-level structure) |
| `StateManager` | Persistent JSON state file (.state): load/save/get/set |
| `DirectoryManager` | Create audio/, transcripts/, logs/ |
| `Diagnostics` | Check external dependencies, auto-install (apt/pip) |
| `WhisperInstaller` | Download tarball, build whisper.cpp, download models, CUDA support |
| `Daemon` | PID file, double-fork daemon, signal handling |
| `AudioRecorderBackend` | ABC for audio recording (start/stop/cancel lifecycle) |
| `ArecordRecorder` | ALSA arecord implementation via subprocess |
| `AudioRecorder` | Recording orchestrator — filenames, validation, logging (delegates to backend) |
| `AudioProcessorBackend` | ABC for audio normalization |
| `FfmpegProcessor` | FFmpeg loudnorm implementation via subprocess |
| `AudioProcessor` | Normalization orchestrator + speech detection (delegates to backend) |
| `TranscriberBackend` | ABC for speech-to-text transcription |
| `WhisperCliTranscriber` | whisper.cpp CLI implementation via subprocess |
| `Transcriber` | Transcription orchestrator — prompt resolution, blank filtering (delegates to backend) |
| `ClipboardBackend` | ABC for clipboard operations (copy, paste, save/restore targets) |
| `XclipBackend` | X11 clipboard via xclip + xdotool |
| `ClipboardManager` | Clipboard orchestrator — target filtering, save/restore logic (delegates to backend) |
| `VolumeController` | System volume save/restore during recording |
| `SoundPlayerBackend` | ABC for sound playback (play a WAV at a given volume) |
| `PaplayPlayer` | PulseAudio implementation via paplay |
| `SoundNotifier` | WAV feedback tones (lazy generation, delegates playback to SoundPlayerBackend) |
| `HotkeyListener` | Push-to-talk via pynput (keyboard + mouse buttons, hold delay, modifier combos, translate mode) |
| `Housekeeping` | Rotate audio + transcript + log files |
| `RedictumError` | Base exception class |
| `_OptionalDep` | Lazy-load optional dependencies (rich) |

## AI Context Files
| File | Purpose |
|------|---------|
| `CLAUDE.md` | This file — project structure map |
| `CHANGELOG.md` | Version history (Keep a Changelog format) |
