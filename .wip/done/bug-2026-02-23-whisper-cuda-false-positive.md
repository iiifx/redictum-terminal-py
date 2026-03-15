# Bug: Whisper CUDA check gives false positive

## Reported by
[user data removed]

## Symptom
- `./redictum whisper` wizard shows "✓ whisper.cpp (CUDA)" — all green
- Transcription takes ~22 seconds per short phrase (10-30 chars)
- Expected on GPU (RTX 4060): 1-3 seconds
- Whisper is clearly running on CPU despite CUDA "check passing"

## Root cause
`_is_cuda_linked()` (line 1160) checks via `ldd` whether the binary links against
CUDA/cuBLAS shared libraries. This is a **necessary but not sufficient** condition.

The binary can be linked against CUDA libs but still fall back to CPU at runtime if:
- CUDA runtime initialization fails silently
- Driver/toolkit version mismatch
- GPU memory allocation fails
- Wrong CUDA architecture for the GPU

Because `_is_cuda_linked` returns `True`, the wizard's `_reconfigure()` flow
(line 1115) prints "✓ whisper.cpp (CUDA)" and **never offers a rebuild**.

The user sees green checkmarks and has no idea GPU isn't actually being used.

## Evidence (user logs)

### Transcription times (daemon mode, all ~22s = CPU speed):
- `_152220.log`: 15:22:25→15:22:49 (24s), 15:23:13→15:23:35 (22s), etc.
- `_155954.log`: 16:00:04→16:00:26 (22s), 16:00:48→16:01:10 (22s)

### Additional problem in interactive mode:
- `_151933.log`: All recordings detected as silence (RMS 90-197, threshold 200)
  — separate from CUDA issue, likely microphone volume

### Old log (`redictum.log`, Feb 20):
- "Recording produced no audio" — possibly older version or audio device issue

## Fix options

### Option A: Runtime GPU test in wizard (recommended)
Run a short whisper-cli transcription on a tiny silent WAV and measure time.
If >N seconds, warn that GPU may not be active despite CUDA linkage.
Pros: actually tests real GPU usage. Cons: adds a few seconds to wizard.

### Option B: Check whisper-cli stderr for CUDA info
whisper.cpp prints backend info to stderr on startup (e.g. "CUDA" or "Metal").
Capture stderr from a test run and check for GPU backend confirmation.
Pros: fast, no need for timing heuristic. Cons: depends on whisper.cpp output format.

### Option C: Log transcription time + warn on slow
During normal operation, measure transcription duration and log a warning
if it exceeds a threshold (e.g. >10s for <5s audio = likely CPU).
Pros: catches the issue during actual use. Cons: warning comes late, after the fact.

### Recommended approach
Combine B (check stderr in wizard) + C (runtime timing warning).
This catches the problem both during setup and during normal use.

## Affected code
- `WhisperInstaller._is_cuda_linked()` — line 1160
- `WhisperInstaller._reconfigure()` — line 1115
- `Transcriber.transcribe()` — line 2204 (for runtime timing)
- `Diagnostics.check_whisper()` — line 1015 (startup check)
