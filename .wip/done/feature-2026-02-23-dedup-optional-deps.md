# Feature: Deduplicate optional dependency checking

## Problem

Three methods in `Diagnostics` follow the exact same pattern:
- `_check_optional_sound()` (~50 lines)
- `_check_optional_normalize()` (~30 lines)
- `_check_optional_paste()` (~30 lines)

Pattern:
1. Config-guard: skip if feature disabled (unless `force=True`)
2. Check if tool exists (`shutil.which`)
3. If present: print checkmark, re-enable on `force`
4. If missing: offer to install (apt package)
5. If declined/failed: disable feature in config

Total: ~110 lines of nearly identical code, differing only in:
- Tool name (`paplay` / `ffmpeg` / `xdotool`)
- Apt package name (`pulseaudio-utils` / `ffmpeg` / `xdotool`)
- Feature description ("Sound notifications" / "Audio normalization" / "Auto-paste")
- Config keys to update
- Config guard keys to check

## Solution

Extract a generic `_check_optional_dep()` method:

```python
@dataclass
class OptionalDep:
    tool: str                     # binary name for shutil.which
    package: str                  # apt package name
    label: str                    # human-readable feature name
    config_keys: dict[str, bool]  # {config_key: default_enabled_value}
    guard_keys: tuple[str, ...]   # keys to check for config-guard

OPTIONAL_DEPS = [
    OptionalDep("paplay", "pulseaudio-utils", "Sound notifications",
                {"sound_signal_start": True, "sound_signal_done": True,
                 "sound_signal_error": True, "sound_signal_processing": False},
                ("sound_signal_start", "sound_signal_processing",
                 "sound_signal_done", "sound_signal_error")),
    OptionalDep("ffmpeg", "ffmpeg", "Audio normalization",
                {"recording_normalize": True}, ("recording_normalize",)),
    OptionalDep("xdotool", "xdotool", "Auto-paste",
                {"paste_auto": True}, ("paste_auto",)),
]
```

Then `run_optional()` iterates over `OPTIONAL_DEPS` and calls one method.

## Also: language display/save duplication

`_first_run_language_check()` and `run_language()` share logic for:
- Displaying selected language + prompt
- Saving to config with `_config_mgr.update()`

Extract a `_save_language(lang, prompt)` helper to remove ~15 lines of duplication.

## Impact

- ~110 → ~40 lines (optional deps)
- ~15 lines saved (language)
- Adding new optional deps becomes one-liner (add to `OPTIONAL_DEPS` list)
- Easier to test: one method to verify, parametrized tests

## Verification

- All existing unit tests pass
- E2E tests pass
- Manual: `./redictum setup` still offers install/disable for each optional dep
