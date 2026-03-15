# Bug: No visual distinction between transcribe and translate modes

## Problem
In interactive mode with live console output, the "Recording..." and "Processing..." indicators look identical for transcribe (Insert) and translate (Ctrl+Insert) modes. The user cannot tell which mode is active until the final result appears.

The mode is only shown at the very end in the `Transcribed: translate, 12 chars` line — too late to be useful.

## Example output
Transcribe mode:
```
● Recording...
⟳ Processing...
✓ "Вторая проверка."
  Transcribed: transcribe, 16 chars
```

Translate mode (looks the same until the last line):
```
● Recording...
⟳ Processing...
✓ "Third check."
  Transcribed: translate, 12 chars
```

## Expected
Mode should be visible from the start — e.g.:
- `● Recording... (transcribe)` vs `● Recording... (translate)`
- Or different color/icon for translate mode