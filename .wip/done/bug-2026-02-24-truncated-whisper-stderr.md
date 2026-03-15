# Bug: Truncated whisper-cli stderr hides actual CUDA error

**Created:** 2026-02-24
**Severity:** Medium (doesn't break functionality, but makes debugging very hard)

## Problem

When whisper-cli fails, Redictum logs only the first 200 characters of stderr:

```python
# redictum:2434-2437
raise RedictumError(
    f"whisper-cli failed (code {result.returncode}): "
    f"{result.stderr[:200]}"
)
```

In a real CUDA crash, the important error (e.g. "out of memory", "invalid device
function", "no kernel image") is printed early in stderr, but the ggml assert
message (`ggml-cuda.cu:96: CUDA error`) comes at the end. The 200-char truncation
often captures only the tail — the generic assert — and the actual root cause
is lost.

**Example from user log (2026-02-24):**
```
[user log removed]
whisper-cli failed (code -6): .../ggml-cuda/ggml-cuda.cu:96: CUDA error
```

The specific CUDA error code/message is nowhere to be seen.

## Fix

Log the **full** stderr to the log file, and show a reasonable portion in the
user-facing error message.

**Approach:**
1. Log full `result.stderr` via `logging.error()` — always available in the log
2. For the exception message, show the **last** N characters (tail) or extract
   the most relevant line, rather than the first 200 chars
3. Consider also logging `result.stdout` on failure — some tools print errors
   to stdout

```python
if result.returncode != 0:
    logging.error("whisper-cli stderr:\n%s", result.stderr)
    logging.error("whisper-cli stdout:\n%s", result.stdout)
    raise RedictumError(
        f"whisper-cli failed (code {result.returncode}): "
        f"{result.stderr.strip()[-500:]}"
    )
```
