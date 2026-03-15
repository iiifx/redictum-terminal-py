# Bug: Thread safety gaps in pipeline and sound notifier

## Problem 1: SoundNotifier._ensure_tones() race

`_ensure_tones()` is called from `_play()`, which runs from multiple threads
(pipeline thread, hold callback thread). If two threads call `_play()` for the
first time simultaneously:

```python
def _ensure_tones(self):
    if self._sounds:       # Thread A: empty → proceed
        return             # Thread B: empty → proceed (race!)
    self._temp_dir = ...   # Both threads create temp dirs
    for name, samples in _generate_tones().items():
        self._sounds[name] = ...  # Dict mutation from two threads
```

Result: double temp dir creation, dict corruption, orphaned temp files.

### Fix

Use `threading.Lock`:
```python
def __init__(self, ...):
    self._init_lock = threading.Lock()

def _ensure_tones(self):
    if self._sounds:
        return
    with self._init_lock:
        if self._sounds:  # double-check
            return
        # ... generate tones
```

## Problem 2: Pipeline accesses shared state without sync

`_run_pipeline()` runs in a daemon thread and accesses instance attributes
(`self._recorder`, `self._notifier`, `self._housekeeper`, etc.) that were
set up in `_main_loop()`. These are effectively read-only after init, so
this is **safe in practice** — but there's no guarantee or documentation.

More concerning: `self._recorder.stop()` is called from pipeline thread,
while `_on_hold` could theoretically call `self._recorder.start()` if the
state lock window allows it. The state machine prevents this in normal flow,
but a thread scheduling edge case could cause issues.

### Fix

Document the threading model with a comment. Consider making recorder
start/stop themselves thread-safe (internal lock).

## Problem 3: Graceful shutdown polling

`_graceful_shutdown()` waits for pipeline completion with a busy loop:
```python
while time.monotonic() < deadline:
    with self._state_lock:
        if self._state == STATE_IDLE:
            break
    time.sleep(0.5)
```

This works but is wasteful. A `threading.Event` set by `_run_pipeline`
in its `finally` block would be cleaner and more responsive.

### Fix

Add `self._pipeline_done = threading.Event()` — set in `_run_pipeline` finally,
wait in `_graceful_shutdown`.

## Impact

- Problem 1: potential crash on first use if two hotkey events fire simultaneously
- Problem 2: theoretical, not observed in practice
- Problem 3: cosmetic, 500ms worst-case delay on shutdown

## Verification

- Unit test for SoundNotifier: concurrent _play() calls don't crash
- Stress test: rapid key press/release cycles → no deadlock or crash
