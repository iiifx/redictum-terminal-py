# Bug: Invalid boolean config values silently convert to False

**Source:** Copilot security audit PR #2
**Severity:** LOW
**Status:** pending

## Problem

`ConfigManager._parse_value()` for boolean keys uses:

```python
return value.lower() in ("true", "yes", "1", "on")
```

Any unrecognized value (e.g. `"maybe"`, `"tru"`, `"ues"`) silently becomes
`False`. User thinks the feature is enabled, but it's not.

For comparison, int and float keys already raise `RedictumError` on
invalid input — booleans should behave the same way.

## Proposed fix

```python
if key in cls._BOOL_KEYS:
    lower_val = value.lower()
    if lower_val in ("true", "yes", "1", "on"):
        return True
    if lower_val in ("false", "no", "0", "off"):
        return False
    raise RedictumError(
        f"Config '{key}': expected boolean (true/false), got '{value}'"
    )
```

## Compatibility note

This is technically a breaking change — if someone has a typo in their
config (e.g. `recording_normalize = ture`), it used to silently work
(as False), now it will crash with a clear error message.

This is the **correct** behavior — consistent with int/float validation
and better than silent misconfiguration.

## Notes

- Existing tests `test_bool_override_true` / `test_bool_override_false`
  should still pass (they use valid values)
- Need one new test: invalid bool value → RedictumError
- Check if any existing test relies on the silent-false behavior
