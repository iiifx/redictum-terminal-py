# Bug: Error messages keep the tail of stderr, which hides the root cause

## Problem
`WhisperCliTranscriber.transcribe` builds the user-facing error from the *last* 500 characters
of stderr (`redictum:2536`):

```python
f"whisper-cli failed (code {result.returncode}): "
f"{result.stderr.strip()[-500:]}"
```

whisper.cpp prints the actual diagnosis first (`CUDA error: out of memory`, `ggml-cuda.cu:96`)
and then dumps a long ggml/gdb backtrace. So the tail contains everything except the reason,
and the user is shown the generic last line — `failed to process audio` — which misdescribes
the failure as an audio problem.

The full stderr *is* logged one line earlier (`redictum:2532`), so the information is not lost;
it is only lost on the way to the user, who then has no reason to open the log.

Same `[-500:]` pattern in `FfmpegProcessor.normalize` (`redictum:2239`) and in the cmake
configure error (`redictum:1614`) — ffmpeg is also a head-first reporter, so both are suspect.

## Expected
Show the part of stderr that carries the cause:
- prefer the head (first N lines) over the tail, or
- filter for the first line matching an error pattern (`error:`, `CUDA error`, `failed`), or
- show first N + last N with an elision marker.

Whatever the rule, the console message must let the user act without opening the log file.

## Note
Found while diagnosing `bug-2026-07-27-cuda-oom-no-cpu-fallback.md`: the misleading
"failed to process audio" sent the initial investigation towards the WAV file, which was
perfectly valid.
