# Feature: Comprehensive diagnostics logging

## Problem

During first-run initialization, Diagnostics runs dependency checks, asks
user questions, installs packages — but **none of this is logged**. The log
file is only initialized **after** `init()` completes, so all `logging.*`
calls during diagnostics would go nowhere.

If a user sends us their log for troubleshooting, we see only
`Interactive mode started` — no idea what happened during setup, what was
installed, what failed, or what the user chose.

## Three gaps to close

### 1. Package installation logging

Currently zero `logging.*` calls in `Diagnostics`. Need to log:

- Each dependency check result (found / missing)
- Which packages were offered for installation
- `apt install` / `pip install` command, exit code, stderr on failure
- PEP 668 fallback chain: which step succeeded or all failed
- Audio device auto-detection: which candidates were tried, which worked
- Whisper.cpp check: CLI and model paths, found or missing
- Final summary: all deps OK / some failed

### 2. User prompt/response logging

Every `_confirm()` call during init should be logged:

- "Install missing dependencies?" → user answered Y/N
- "Download whisper model?" → user answered Y/N
- "Install whisper.cpp?" → user answered Y/N
- Any other y/n prompt during setup

Format: `logging.info("User prompt: %r → %s", prompt, "yes"/"no")`

This is essential for remote troubleshooting — without it we can't tell
if the user skipped something intentionally or never saw the prompt.

### 3. System information at startup

Log hardware/software environment on first line of every session:

- OS: distro name + version (e.g., "Linux Mint 21.3 / Ubuntu 22.04")
- Kernel: `uname -r`
- Python: `sys.version`
- GPU: NVIDIA model if present (`nvidia-smi --query-gpu=name --format=csv,noheader`)
- CUDA: version if available (`nvcc --version` or `nvidia-smi`)
- RAM: total (from `/proc/meminfo`)
- Display server: X11/Wayland, `$DISPLAY` value
- Locale: `$LANG`

This lets us understand the user's environment from logs alone, without
asking them to run extra commands.

## Implementation notes

**Key blocker**: `setup_logging()` is called **after** `init()` in both
`run_interactive()` and `run_start()`. Need to move it **before** `init()`
so that diagnostics logging actually reaches the log file.

Sequence should be:
1. `setup_logging()` — open log file
2. `_log_system_info()` — write environment snapshot
3. `init()` / diagnostics — all checks and installs are now logged
4. Continue to main loop

For `_confirm()` logging — can add `logging.info` directly inside the
shared `_confirm()` function so ALL prompts are automatically logged,
not just diagnostics ones.

## Priority

Medium — not blocking any functionality, but significantly improves
our ability to diagnose user issues remotely.
