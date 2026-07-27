# Bug: HotkeyListener mutates shared state from two threads without a lock

## Problem
`RedictumApp` guards its state machine with `_state_lock` and documents the threading model
(`redictum:4342-4347`). `HotkeyListener` does not: `_is_holding`, `_hold_timer` and
`_pending_mode` are read and written from both the pynput listener thread (`_on_press`,
`_on_key_release`) and the `threading.Timer` thread (`_fire_hold`) with no synchronisation
(`redictum:3271-3313`).

`_fire_hold` publishes its state in three separate steps:

```python
self._is_holding = True      # 3288
self._hold_timer = None      # 3289
self._on_hold(...)           # 3291
```

Releasing the key inside that window lets `_on_key_release` observe `_is_holding == True` and
call `on_release` *before* `_on_hold` has started the recorder. Traced consequence:

1. `_on_release` runs first, finds the app state still `IDLE`, and returns early
   (`redictum:4391-4394`) — the pipeline is never launched.
2. `_on_hold` then runs and starts the recorder, moving the app to `RECORDING`.
3. Nothing will ever stop that recording: the key is already up, so no further release event
   is coming.

The stuck state resolves only on the next press+release cycle (the new press is ignored
because the state is not `IDLE`, the new release runs the pipeline over an over-long
recording). The window is a few milliseconds wide, exactly at the `hotkey_hold_delay`
boundary, which is why it has not been observed in practice.

## Expected
Give `HotkeyListener` its own lock and make the hold/release transition atomic: whichever
thread wins should see a consistent (`_is_holding`, `_hold_timer`) pair, and a release that
arrives before `on_hold` has fired must either cancel the hold outright or be deferred until
after the recorder actually started.

## Note
Not reproduced live — derived from reading the code. Worth reproducing by shrinking
`hotkey_hold_delay` and scripting press/release at exactly that delay (xdotool) before fixing,
so the fix can be proven.
