# Feature: Cover the threaded runtime, not just the logic

## Problem
Coverage is 83% with a 75% gate, 574 unit tests, ruff clean — and the *uncovered* 17% is not
random. From `--cov-report=term-missing`, the untested regions are almost exactly the
concurrent and long-running parts:

- `_main_loop` (4286-4361) — component wiring and the state machine setup
- `run_interactive` (3878-3912)
- `_on_release` (4391-4400) — the hand-off from the listener thread to the pipeline thread
- `_capture_hotkey` (3542-3598)
- installer / diagnostics paths (968-1020, 1069-1075, 3996-4004, …)

So the test suite proves the *logic* is right and says nothing about *thread interleaving* —
which is where the defects actually live. Both problems found on 2026-07-27
(`bug-2026-07-27-cuda-oom-no-cpu-fallback.md`, `bug-2026-07-27-hotkey-listener-race.md`) sit
in that band: one in an untested runtime failure path, one in an untested race.

## Idea
Test the state machine directly, without real audio or real keys:

1. **Listener state machine** — drive `HotkeyListener._on_press` / `_fire_hold` /
   `_on_key_release` by hand from separate threads, with the callbacks recording their order.
   Assert the invariant: `on_release` is never delivered for a hold whose `on_hold` has not
   returned, and every `on_hold` is eventually followed by exactly one `on_release`.
2. **App state machine** — call `_on_hold` / `_on_release` with fake backends and assert
   `IDLE → RECORDING → PROCESSING → IDLE` never skips or sticks, including the failure paths
   (recorder raises, transcriber raises, pipeline raises unexpectedly).
3. **Failure-injection backends** — a `TranscriberBackend` that raises `RedictumError`, one
   that returns blank, one that hangs until timeout. These are cheap now that every backend is
   an ABC, and they cover the paths that only real hardware failures reach today.
4. **Stress the boundary** — press/release at exactly `hotkey_hold_delay` in a loop
   (fake clock or very small delay) to make narrow races reproducible.

## Related
`feature-2026-02-21-e2e-multi-env-testing.md` covers the neighbouring axis — hostile
*environments* (broken devices, PEP 668, PipeWire vs PulseAudio) through smarter fakes.
This one is about hostile *timing* inside the process. Complementary, not overlapping.

## Complexity
Medium. No new infrastructure needed — the backend ABCs already provide the seams; it is
writing tests that assert ordering instead of results.
