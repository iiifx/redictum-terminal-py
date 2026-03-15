# Feature: Auto-infer config value types from DEFAULT_CONFIG

## Problem

`ConfigManager` maintains three manual frozensets to know how to parse INI values:

```python
_BOOL_KEYS: frozenset[str] = frozenset({
    "recording_normalize", "recording_silence_detection",
    "paste_auto", "sound_signal_start", ...
})
_INT_KEYS: frozenset[str] = frozenset({
    "whisper_timeout", "sound_signal_volume", ...
})
_FLOAT_KEYS: frozenset[str] = frozenset({
    "hotkey_hold_delay", "paste_restore_delay",
})
```

These must be **manually kept in sync** with `DEFAULT_CONFIG`. If someone adds
a new boolean key to `DEFAULT_CONFIG` but forgets to add it to `_BOOL_KEYS`,
it silently gets parsed as a string ("true" instead of `True`).

This is a maintainability trap — no compiler or linter catches the mismatch.

## Solution

Derive types automatically from `DEFAULT_CONFIG` values:

```python
@classmethod
def _infer_type(cls, key: str) -> type:
    """Infer expected type for a config key from DEFAULT_CONFIG."""
    for section in DEFAULT_CONFIG.values():
        if isinstance(section, dict) and key in section:
            return type(section[key])
    return str  # fallback

@classmethod
def _parse_value(cls, key: str, raw: str) -> Any:
    value = cls._strip_quotes(raw)
    expected = cls._infer_type(key)
    if expected is bool:
        ...
    elif expected is int:
        ...
    elif expected is float:
        ...
    return value
```

Then delete `_BOOL_KEYS`, `_INT_KEYS`, `_FLOAT_KEYS` entirely.

## Alternative: keep frozensets but validate at import time

```python
# At module level, after DEFAULT_CONFIG:
_ALL_BOOL = frozenset(
    k for section in DEFAULT_CONFIG.values() if isinstance(section, dict)
    for k, v in section.items() if isinstance(v, bool)
)
assert _ALL_BOOL == ConfigManager._BOOL_KEYS, f"Mismatch: {_ALL_BOOL ^ ConfigManager._BOOL_KEYS}"
```

Simpler, catches drift immediately, zero runtime cost.

## Recommendation

Option 1 (auto-infer) is cleaner — removes ~20 lines of manual lists.
Option 2 (assert) is safer if there are keys where the default type differs
from the desired parse type (none currently).

## Impact

- Removes ~20 lines of fragile manual type lists
- New config keys automatically get correct type parsing
- Zero risk of "forgot to add to frozenset" bugs

## Verification

- All existing ConfigManager tests pass
- Add test: every key in DEFAULT_CONFIG round-trips correctly through parse_value
- Add test: no key is missing from type inference
