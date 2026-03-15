# Bug: StateManager read-modify-write is not atomic

## Problem

`StateManager.set()` does load → modify → save:

```python
def set(self, key, value):
    state = self.load()    # read
    state[key] = value     # modify
    self.save(state)       # write
```

If two processes (or threads) call `set()` concurrently, the second write
overwrites the first. Classic TOCTOU (time-of-check-to-time-of-use).

Current real-world risk is **low** — `set()` is only called from the main thread
during startup/shutdown. But with PID-in-state feature planned, concurrent access
becomes a real concern (daemon writing PID while interactive checks status).

## Scenarios

1. **Now**: `run_interactive()` and `run_start()` both call `_state_mgr.set("last_run", ...)`
   — safe because only one instance runs at a time.
2. **Future (PID in state)**: `daemon.start()` writes PID, `./redictum status` reads
   state — concurrent read/write → potential JSON corruption.

## Fix options

### Option A: Atomic write with rename (recommended)

```python
def save(self, state: dict) -> None:
    import json
    import tempfile
    data = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
    try:
        os.write(fd, data.encode("utf-8"))
        os.close(fd)
        os.rename(tmp, str(self._path))  # atomic on same filesystem
    except:
        os.close(fd) if not os.get_inheritable(fd) else None
        Path(tmp).unlink(missing_ok=True)
        raise
```

This ensures readers always see complete JSON (either old or new version).

### Option B: File locking (fcntl.flock)

More complex. Prevents concurrent writes but adds lock management overhead.
Overkill unless we need read-write serialization.

### Option C: Keep as-is, document the limitation

If PID stays in separate file, concurrent access to `.state` is unlikely.
Add a comment noting the non-atomic nature.

## Recommendation

Option A — atomic rename is simple, well-understood, and sufficient.
If PID-in-state feature is implemented, this becomes a prerequisite.

## Verification

- Unit test: write large state dict, verify no partial writes
- Crash test: kill process during save, verify file is either old or new (not corrupt)
