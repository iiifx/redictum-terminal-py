# AGENTS.md

> Project map for AI agents. Keep this file up-to-date as the project evolves.

## Project Overview
System-wide voice-to-text CLI utility for Linux. Captures hotkeys, records microphone audio, transcribes via whisper.cpp, and pastes text into active input.

## Tech Stack
- **Language:** Python 3.10+ (stdlib only, no external dependencies)
- **CLI Framework:** argparse (stdlib)
- **Audio Recording:** arecord (ALSA utils, via subprocess)
- **Audio Processing:** FFmpeg (via subprocess)
- **Transcription:** whisper.cpp CLI
- **Keyboard Hotkeys:** pynput
- **Clipboard:** xclip / xdotool (via subprocess)
- **Config Format:** JSON (config.json next to script)
- **Architecture:** Single-file executable (`redictum`)

## Project Structure
```
redictum-terminal-py/
├── .ai-factory/              # AI Factory project configuration
│   └── DESCRIPTION.md        # Project specification and tech stack
├── .agents/                  # External skills from skills.sh
│   └── skills/
│       ├── python-packaging/
│       └── python-testing-patterns/
├── .claude/                  # Claude Code configuration
│   └── skills/               # AI agent skills (local + symlinked)
├── .gitignore                # Git ignore rules
├── .venv/                    # Python virtual environment (Python 3.10)
├── AGENTS.md                 # This file — project structure map
├── redictum                  # Main executable (chmod +x, single file)
├── config.json               # Generated on first run, user-editable
├── audio/                    # Recorded audio files (auto-created)
├── transcripts/              # Transcription output (auto-created)
└── logs/                     # Log files (auto-created)
```

## Key Entry Points
| File | Purpose |
|------|---------|
| `redictum` | Main CLI entry point (argparse, all classes in one file) |
| `config.json` | Runtime config, auto-generated from DEFAULT_CONFIG |

## CLI Commands
| Command | Description |
|---------|-------------|
| `./redictum` | Interactive mode (init config + dirs) |
| `./redictum start` | Start daemon |
| `./redictum stop` | Stop daemon |
| `./redictum status` | Show daemon status |
| `./redictum --version` | Print version |
| `./redictum --help` | Show help |

## Code Architecture (inside `redictum`)
| Class | Status | Purpose |
|-------|--------|---------|
| `ConfigManager` | **Working** | Load/generate/merge config.json |
| `DirectoryManager` | **Working** | Create audio/, transcripts/, logs/ |
| `RedictumApp` | **Working** | Orchestrator, wires components |
| `Diagnostics` | **Working** | Check external dependencies, auto-install |
| `Daemon` | **Working** | PID file, double-fork daemon, signal handling |
| `AudioRecorder` | **Working** | Record via arecord (start/stop/cancel) |
| `AudioProcessor` | **Working** | Normalize via ffmpeg loudnorm |
| `Transcriber` | **Working** | Transcribe via whisper-cli |
| `ClipboardManager` | **Working** | xclip copy + xdotool paste |
| `SoundNotifier` | **Working** | WAV feedback tones via paplay |
| `HotkeyListener` | **Working** | Push-to-talk via pynput (hold delay) |
| `Housekeeping` | **Working** | Rotate audio files, clean logs (stub) |

## AI Context Files
| File | Purpose |
|------|---------|
| AGENTS.md | This file — project structure map |
| .ai-factory/DESCRIPTION.md | Project specification and tech stack |
