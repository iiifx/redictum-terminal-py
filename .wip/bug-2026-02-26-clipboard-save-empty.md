# Bug: Clipboard save fails when clipboard is empty

## Problem
`Clipboard save failed: xclip returned 0` appears in logs when clipboard is empty (e.g., after system reboot). Exit code 0 means xclip succeeded, but the save logic treats it as a failure.

## Reproduction
1. Reboot machine (clipboard is empty)
2. Run redictum, record and transcribe
3. Log shows: `Clipboard save failed: xclip returned 0`

## Expected
Empty clipboard should be handled gracefully — no error, no warning. Save/restore should simply skip when there's nothing to save.

## Log evidence
```
2026-02-26 05:26:02 [WARNING] Clipboard save failed: xclip returned 0
```