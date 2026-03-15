# Bug: PID file created without explicit permissions, potential TOCTOU race

**Source:** Copilot security audit PR #2
**Severity:** MEDIUM
**Status:** pending

## Problem

`Daemon._write_pid()` uses `Path.write_text()` which:
1. Creates the file with default permissions (umask-dependent)
2. Has a TOCTOU gap between existence check in `start()` and write in `_write_pid()`

```python
# Current code
def _write_pid(self) -> None:
    self._pid_path.write_text(f"{os.getpid()}\n")
```

## Impact

- With `os.umask(0)` (the other bug), PID file is world-writable → another
  user could overwrite it and trick `stop()` into killing the wrong process
- Even after umask fix, there's a small TOCTOU window between checking if
  daemon is running and writing the new PID

## Proposed fix

Use `os.open()` with `O_EXCL` for atomic creation + explicit permissions:

```python
def _write_pid(self) -> None:
    pid = os.getpid()
    flags = os.O_WRONLY | os.O_CREAT
    try:
        fd = os.open(str(self._pid_path), flags | os.O_EXCL, 0o644)
    except FileExistsError:
        # File exists — truncate after stale check in start()
        fd = os.open(str(self._pid_path), flags | os.O_TRUNC, 0o644)
    try:
        os.write(fd, f"{pid}\n".encode("utf-8"))
    finally:
        os.close(fd)
```

## Notes

- This fix pairs with the umask fix (bug-2026-02-22-umask-world-writable)
- After both fixes: PID file is always 644 regardless of umask
- The O_EXCL path is defensive — in normal flow, start() already checks
  for stale PID and removes it before calling _write_pid()
- Copilot's implementation looks correct, just needs review for edge cases
