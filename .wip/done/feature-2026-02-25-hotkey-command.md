# Feature: Hotkey Command

## Summary

New CLI command `redictum hotkey` — interactive hotkey reassignment directly from the terminal, without manually editing the config file.

## Motivation

Currently, to change the hotkey, the user must open `config.ini`, remember the exact key name format (`Insert`, `ctrl+F12`, etc.), and edit the value manually. This is inconvenient and error-prone. An interactive command solves this by capturing the actual keypress.

## Current State

- Two hotkeys in `[input]` section of `config.ini`:
  - `hotkey_key` — main record hotkey (default: `Insert`)
  - `hotkey_translate_key` — record + translate hotkey (default: `ctrl+Insert`)
- `HotkeyListener` already uses `pynput` for global key capture
- `_parse_combo()` / `_parse_key()` parse string → pynput Key objects
- Need the reverse: pynput Key objects → string

## User Flow

1. User runs `redictum hotkey`
2. Display current hotkeys:
   ```
   Current hotkeys:
     1. Record:    Insert
     2. Translate: ctrl+Insert
   ```
3. Prompt: "Which hotkey to change? [1/2, default=cancel]:"
4. Prompt: "Press the new hotkey..."
   - Capture keypress via `pynput.keyboard.Listener` (one-shot mode)
   - Detect modifiers (ctrl, alt, shift) + trigger key
   - Convert back to string format (e.g., `ctrl+F12`)
5. Display: "New hotkey: ctrl+F12. Save? [y/N]"
6. On confirm — save to config via `ConfigManager`
7. If daemon is running — suggest restart: "Daemon is running. Restart to apply? [y/N]"

## Technical Plan

### 1. Reverse key-to-string converter

Add a method to convert pynput key objects back to the string format used in config. Essentially the inverse of `_parse_key()` — map `Key.insert` → `"Insert"`, `Key.f12` → `"F12"`, `KeyCode(char='a')` → `"a"`, etc.

### 2. One-shot key capture

Use `pynput.keyboard.Listener` to:
- Track currently held modifiers (ctrl, alt, shift)
- On trigger key press — record the combo
- On trigger key release — stop listener, return result
- Timeout after ~10 seconds if no key pressed (cancel)

### 3. New method `run_hotkey()`

- Show current hotkeys (read from config)
- Numbered menu to pick which one to change (or cancel)
- Call the one-shot capture
- Show the captured combo, ask for confirmation
- Save to config
- Check if daemon is running (PID file) — suggest restart

### 4. CLI argument

Add `hotkey` subcommand to argparse, dispatch to `run_hotkey()`.

### 5. Edge cases

- Ignore lone modifier presses (ctrl alone = not a valid hotkey, wait for a real key)
- Single key without modifiers is valid (e.g., `Insert`, `F12`, `Pause`)
- Handle Escape as cancel
- Handle `KeyboardInterrupt` / `EOFError` gracefully
- Skip prompts in quiet mode (exit with message)
- Empty string for `hotkey_translate_key` means disabled — offer as option

## Out of Scope

- Changing `hotkey_hold_delay` (keep in config only — too rare to need interactive change)
