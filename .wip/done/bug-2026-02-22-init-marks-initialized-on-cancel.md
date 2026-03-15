# Bug: init() marks .initialized even when user cancels dependency install

## Severity: Medium-High

## Problem

When the user declines to install missing dependencies during first-run,
`init()` still calls `_mark_initialized()` and proceeds to start `main_loop()`.

Two consequences:

### 1. First run: main loop starts without dependencies

User says "no" to everything → script enters main loop anyway:

```
Missing apt: ['ffmpeg', 'xclip', 'xdotool', 'cmake', 'build-essential']
Missing pip: ['pynput', 'rich']
Prompt: 'Install missing dependencies?' → no
Whisper CLI: missing
Prompt: 'Install whisper.cpp?' → no
Interactive mode started (PID 7)    ← should NOT happen
Starting main loop...               ← will crash on first hotkey (no pynput)
```

Without pynput there's no hotkey listener. Without xdotool/xclip — no paste.
Without whisper — no transcription. The app is non-functional but pretends
to be running.

### 2. Second run: full diagnostics re-triggered (correct but noisy)

Because `.initialized` exists but `_deps_ok()` returns `False`, the second
run correctly falls into `init()` again. This is the right behavior — but
it means the `.initialized` marker from the first run was a lie.

## Root cause

`init()` unconditionally calls `_mark_initialized()` at the end:

```python
def init(self) -> dict[str, Any]:
    config = self._load_config()
    self._dir_mgr.ensure()
    diag = Diagnostics(config, self._config_mgr)
    diag.run_stage1()       # critical checks — raises on failure
    diag.run_stage2()       # installable deps — user can decline
    diag.check_whisper()    # whisper — user can decline
    self._mark_initialized()  # ← always runs, even if user said "no"
    return self._load_config()
```

Stage 1 raises on failure (correct). But Stage 2 and whisper silently
continue on user decline — the marker gets written regardless.

## Reproduction (sandbox)

```bash
cd sandbox && ./sandbox.sh
# Say "n" to all prompts
# Observe: script enters main loop, likely crashes or hangs
```

## Sandbox log evidence

First run log (`redictum_20260222_184251.log`):
```
18:42:53 [INFO] Missing apt: ['ffmpeg', 'xclip', 'xdotool', 'cmake', 'build-essential']
18:42:53 [INFO] Missing pip: ['pynput', 'rich']
18:43:00 [INFO] Prompt: '\nInstall missing dependencies?' → no
18:43:00 [INFO] Whisper CLI: ... — missing
18:43:05 [INFO] Prompt: '\nInstall whisper.cpp?' → no
18:43:10 [INFO] Interactive mode started (PID 7)   ← BAD
18:43:10 [INFO] Starting main loop...              ← BAD
```

## Fix options

### Option A: Don't mark initialized if critical deps missing

After `run_stage2()` and `check_whisper()`, check `_deps_ok()` before
marking. If deps are missing — warn and exit (or warn and don't mark).

### Option B: Exit early when user declines required dependencies

Make `run_stage2()` return a status. If user declined and required packages
are still missing — print a clear message and `sys.exit(1)`.

### Option C: Mark initialized, but don't start main loop

Keep the marker logic, but add a `_deps_ok()` check before entering
main_loop in `run_interactive()` / `run_start()`. If deps aren't met —
print what's missing and exit.

**Recommendation:** Option B or C — the user should see a clear message
like "Cannot start: missing pynput, xdotool. Run again to install."
