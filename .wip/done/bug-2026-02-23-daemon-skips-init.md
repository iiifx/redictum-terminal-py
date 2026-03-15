# Bug: Daemon mode must not run setup if not initialized

## Problem

When `./redictum start` is called and the app has never been initialized (no `.state`),
the daemon currently triggers the full `init()` flow — interactive prompts for installing
dependencies, whisper, etc. This breaks with `stdin=/dev/null` (EOF → decline → abort).

Daemon mode should refuse to start if setup hasn't been completed, and tell the user
to run `./redictum` (interactive) first.

## Expected behavior

- `./redictum start` without prior initialization → print error message, exit 1
- No prompts, no install attempts in daemon mode
- User runs `./redictum` interactively first → completes setup → then `./redictum start` works

## Verification

- Manual: `rm .state config.ini && ./redictum start` → should refuse, not prompt
- Manual: run interactive first, then daemon → should work
- E2E: check that T01 still passes (it pre-creates whisper fakes)
- Unit tests: add test for run_start() when not initialized
