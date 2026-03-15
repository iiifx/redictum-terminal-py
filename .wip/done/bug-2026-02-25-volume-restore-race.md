# Bug: Volume not fully restored with multiple instances

## Symptom

When two redictum instances run simultaneously (e.g., one from ~/bin, one from
the repo), system volume gets progressively quieter after each recording cycle.

## Root Cause

Race condition in `VolumeController.reduce()` / `restore()`:

1. Instance A: saves volume (36%), reduces to 10%
2. Instance B: saves volume (10% — already reduced!), reduces to 3%
3. Instance A: restores to 36%
4. Instance B: restores to 10% ← should be 36%

Each instance saves the *current* volume (which may already be reduced by
another instance) rather than the *original* pre-reduction value.

## Fix

Shared lock file in `XDG_RUNTIME_DIR` (per-user, secure):
- JSON: `{"volume": "36%", "pids": [1234, 5678]}`
- First instance to reduce: saves original volume + its PID
- Subsequent instances: add PID to list, don't overwrite original
- On restore: remove PID; if last PID → restore original, delete file
- Dead PID cleanup on every acquire (handles crashes)
- File locking via `fcntl.flock` for atomicity

## Security Considerations

- File in XDG_RUNTIME_DIR (mode 0700 per-user) or /tmp with uid suffix
- File created with mode 0o600
- Validate all data read from file (PIDs must be ints, volume must match `\d+%`)
- Best-effort: any lock/file failure → skip volume control, never break recording
