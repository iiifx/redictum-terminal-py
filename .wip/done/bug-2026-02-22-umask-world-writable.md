# Bug: Daemon creates world-writable files via os.umask(0)

**Source:** Copilot security audit PR #2
**Severity:** HIGH
**Status:** pending

## Problem

In `Daemon.start()`, the double-fork daemonization code calls `os.umask(0)`.
This means all files created by the daemon process (logs, audio recordings,
transcripts, PID file) have no permission restrictions — any user on the
system can read, write, and delete them.

```python
# Current code (line ~1744)
os.setsid()
os.umask(0)  # ← everything world-writable
```

## Impact

- Log files, audio recordings, and transcripts are accessible to all users
- PID file can be overwritten by another user → daemon hijack
- Only affects daemon mode (`./redictum start`), not interactive mode

## Proposed fix

```python
os.umask(0o022)  # owner=rwx, group/other=r-x (standard daemon umask)
```

This gives files 644 and directories 755 by default — owner can write,
others can only read. Standard practice for daemon processes.

## Notes

- Simple one-line change, zero risk of breaking anything
- Interactive mode is not affected (inherits shell umask)
