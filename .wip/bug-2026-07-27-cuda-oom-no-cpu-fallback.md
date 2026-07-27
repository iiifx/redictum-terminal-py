# Bug: CUDA out-of-memory kills transcription instead of falling back to CPU

## Problem
The GPU backend is decided once at install time (`_probe_gpu_backend`, `redictum:1270`) and
trusted forever after. But free VRAM is a runtime property: any other GPU consumer (a game,
a browser with hardware acceleration) can leave too little memory for the whisper encoder.

When that happens `whisper-cli` aborts inside `ggml_cuda_pool_vmm::alloc` and
`WhisperCliTranscriber.transcribe` (`redictum:2531`) treats the non-zero exit code as fatal.
Every recording fails until the user manually frees VRAM. The transcription is lost —
there is no retry, no CPU fallback, no VRAM pre-check.

Note: `whisper-cli -ng` (no GPU) transcribes the very same file successfully in a couple of
seconds on this machine, so a fallback is cheap and usable, not a theoretical escape hatch.

## Reproduction
1. Occupy most of the VRAM (8 GB card: a game taking ~4.5 GB, plus browser/compositor ~2.3 GB)
2. Hold `Insert`, speak, release
3. Every attempt fails; freeing VRAM restores normal operation

## Log evidence
```
[INFO] Audio RMS: 817.8 (threshold: 200.0)
[INFO] Transcribing: rec_..._norm.wav (translate: False)
[ERROR] whisper-cli stderr:
/home/.../whisper-cli: failed to process audio
RedictumError: whisper-cli failed (code 10): ... failed to process audio
```
Next attempt in the same session died harder (SIGSEGV after the CUDA abort):
```
RedictumError: whisper-cli failed (code -11):
```
Manual run of the same file shows the real cause, which the pipeline never surfaces:
```
ggml/src/ggml-cuda/ggml-cuda.cu:96: CUDA error
#4 ggml_cuda_pool_vmm::alloc(unsigned long, unsigned long*)
#5 ggml_cuda_op_mul_mat_cublas
```

## Expected
Recognise GPU-allocation failure and retry the same audio with `-ng` (CPU) instead of losing
the recording. Transcription becomes slower, not broken. The fallback should be logged
(and ideally reported once in the console) so the slowdown is explainable.

Open questions:
- Detect by parsing stderr for `CUDA error` / `out of memory`, or retry on *any* failure once
  with `-ng`? The second is simpler and degrades gracefully for unrelated GPU faults too.
- Should the fallback stick for the rest of the session (avoid paying the failed GPU attempt
  on every subsequent recording), and reset on next start?
- Optional pre-check: `nvidia-smi --query-gpu=memory.used,memory.total` before the run.

## Related
`feature-2026-02-26-cuda-diagnostics.md` covers the *static* CUDA problem (driver vs toolkit
vs linked runtime mismatch). This bug is the *dynamic* one — the build is correct and the GPU
works, there is simply not enough free VRAM right now. Both should end up in the same
"GPU is not usable → keep working on CPU" path.
