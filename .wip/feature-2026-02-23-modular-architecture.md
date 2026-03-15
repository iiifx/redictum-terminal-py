# Feature: Modular architecture with single-file delivery

## Goal

Split the monolithic `redictum` (3584 lines, 17 classes) into proper Python modules
for development, testing, and maintainability — while preserving the single-file
deployment experience for end users via zipapp build.

## Current state

One file → 17 classes + 8 functions + tone synthesis → hard to navigate, test, extend.
Architecture score: 60/100, maintainability: 55/100.

## Target structure

```
src/redictum/
├── __init__.py          # VERSION, constants, RedictumError
├── __main__.py          # CLI entry point (build_parser, main)
├── app.py               # RedictumApp orchestrator
├── config.py            # ConfigManager, DEFAULT_CONFIG, DEFAULT_CONFIG_INI
├── state.py             # StateManager
├── daemon.py            # Daemon (double-fork, PID, signals)
├── diagnostics.py       # Diagnostics, optional dep checks
├── whisper_installer.py # WhisperInstaller, CUDA detection
├── audio.py             # AudioRecorder, AudioProcessor, has_speech
├── transcriber.py       # Transcriber, BLANK_MARKERS
├── clipboard.py         # ClipboardManager
├── hotkey.py            # HotkeyListener
├── sound.py             # SoundNotifier, _generate_tones
├── housekeeping.py      # Housekeeping, _log_transcript, FileRotation
├── language.py          # Language wizard, LANGUAGE_PROMPTS, LANGUAGE_NAMES, _detect_language
└── ui.py                # _rprint, _confirm, _show_language_status
```

Each file: 100–400 lines. Clean imports, clear boundaries.

## Build: zipapp

```bash
# build.sh
python -m zipapp src/redictum -o redictum -p "/usr/bin/env python3"
chmod +x redictum
```

Result: `./redictum` — a zip archive with shebang, executed directly by Python.
User experience unchanged: `curl -o redictum ... && chmod +x redictum && ./redictum`.

## Key problems to solve

### 1. Path(__file__) in zipapp

Current code uses `Path(__file__).resolve().parent` to find script directory.
In zipapp, `__file__` points inside the zip — config.ini, audio/, logs/ won't be found.

**Fix**: use `sys.argv[0]` for script directory resolution:
```python
script_dir = Path(sys.argv[0]).resolve().parent
```
Works in both zipapp and direct module execution. Must be tested thoroughly.

### 2. Two test targets

- **Modules** — unit tests during development (fast, isolated)
- **Built file** — E2E tests to verify assembly didn't break anything

E2E already exists (Docker). Build step must run before E2E:
```bash
# In e2e/Dockerfile or docker-compose.yml:
RUN python -m zipapp src/redictum -o redictum -p "/usr/bin/env python3"
```

### 3. Deferred imports

Current pattern: `import json` inside methods to avoid startup crash if optional
dependency is missing. This works fine in zipapp (Python resolves imports from zip).
No changes needed.

### 4. conftest.py import mechanism

Current `conftest.py` uses `importlib.machinery.SourceFileLoader` to load the
extensionless `redictum` script. After modularization, tests import normally:
```python
from redictum.config import ConfigManager
from redictum.app import RedictumApp
```
conftest.py simplifies dramatically.

### 5. GitHub transparency

Source code on GitHub: `src/redictum/*.py` (readable, navigable).
Built artifact: in GitHub Releases as downloadable file.
README updated: "Download from Releases" or "Build from source".

### 6. CI integration

GitHub Actions builds the artifact automatically:
```yaml
- run: python -m zipapp src/redictum -o redictum -p "/usr/bin/env python3"
- uses: actions/upload-artifact@v4
  with:
    name: redictum
    path: redictum
```

Release workflow attaches built `redictum` to GitHub Release tags.

## Expected impact on quality score

| Criterion        | Before | After |
|------------------|--------|-------|
| Architecture     | 60     | 80    |
| Maintainability  | 55     | 78    |
| Testing          | 68     | 78    |
| Type safety      | 76     | 82    |
| Readability      | 78     | 82    |
| Deployment       | 88     | 85    |
| **Average**      | **~71**| **~82** |

Combined with bug fixes and other improvements: **~85**.

## Prerequisites

Complete these first (they improve the code within the monolith and carry over):
1. Thread safety fixes (bug-2026-02-23-thread-safety-gaps)
2. Dedup optional deps (feature-2026-02-23-dedup-optional-deps)
3. Config type inference (feature-2026-02-23-config-type-inference)
4. Test coverage + CI (feature-2026-02-23-test-coverage-ci)

## Migration plan

1. Create `src/redictum/` package structure
2. Move classes one by one, starting from leaves (no internal deps):
   - `ui.py` (no deps on other modules)
   - `sound.py`, `clipboard.py`, `housekeeping.py`
   - `audio.py`, `transcriber.py`, `hotkey.py`
   - `config.py`, `state.py`, `language.py`
   - `daemon.py`, `diagnostics.py`, `whisper_installer.py`
   - `app.py` (depends on everything)
   - `__main__.py` (CLI entry point)
3. Update all tests to use normal imports
4. Add `build.sh` with zipapp
5. Verify E2E with built artifact
6. Update Dockerfile, docker-compose.yml
7. Update README, AGENTS.md

## Risk

- Medium-high: touches every part of the codebase
- Mitigated by: moving one module at a time, running tests after each step
- `Path(__file__)` change is the highest-risk item — must be tested on real system
- zipapp edge cases: encoding, binary resources (none currently)

## Verification

- All 287 unit tests pass (with normal imports)
- All 13 E2E tests pass (with built zipapp)
- `./redictum` works identically: interactive, daemon, all subcommands
- `Path(__file__)` resolution correct: config.ini, .state, audio/, logs/ found
- Build reproducible: same source → same artifact (modulo timestamps)
