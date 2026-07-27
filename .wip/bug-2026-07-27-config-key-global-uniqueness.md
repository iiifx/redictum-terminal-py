# Bug: Config keys must be globally unique, and nothing enforces it

## Problem
Config handling is key-based, not `(section, key)`-based, in three places:

- `_set_ini_value` (`redictum:583`) rewrites a value with a `^key\s*=` regex over the whole
  file text and `count=1` — the first match anywhere wins, regardless of section.
- `_KEY_TYPES` (`redictum:318`) is a flat `{key: type}` map built from all sections at once,
  so two sections cannot declare the same key with different types.
- `sync()` (`redictum:468-490`) compares flat *sets* of key names to decide what is missing and
  re-applies user values by bare key name.

Today this works only because the default keys happen to be prefixed by their area
(`whisper_*`, `recording_*`, `hotkey_*`, `paste_*`, `sound_*`, `*_max_files`). The invariant is
stated once, in the `update()` docstring ("Key names must be unique across the entire config"),
and is enforced by nothing.

Adding a plausible key — say `[audio] timeout` next to `[dependency] whisper_timeout`, or the
same `timeout` in two sections — makes writes land in the wrong section silently, and
`sync()` will happily copy one section's value into the other's slot.

## Expected
Either enforce the invariant or remove it:
- cheap: assert uniqueness at import time (a self-check over `DEFAULT_CONFIG` that raises if a
  key appears in two sections), so the mine explodes in tests instead of in a user's config;
- proper: make the INI writer section-aware (track the current `[section]` header while
  scanning lines) and key the type map by `(section, key)`.

The cheap version alone would already be enough to keep the current design honest.

## Note
Latent — no user-visible symptom today. Recorded so the constraint is not rediscovered the
hard way when a new config option gets added.
