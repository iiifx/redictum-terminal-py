# Feature: CUDA/GPU diagnostics and self-repair

## Problem
After NVIDIA driver update, CUDA toolkit version may become incompatible with the driver,
or whisper.cpp may be linked against the wrong CUDA. The user gets silent CPU fallback
with ~100x performance degradation and no clear explanation why.

Currently requires manual debugging: `nvidia-smi`, `nvcc --version`, `ldd whisper-cli`,
rebuilding whisper.cpp with correct paths — a lot of "dancing with a tambourine".

## Part 1: CUDA diagnostics

Add GPU/CUDA health checks to `./redictum whisper` command and/or startup diagnostics.

Checks to implement:
1. **GPU presence** — `nvidia-smi` available and returns success
2. **Driver version** — parse from `nvidia-smi` output
3. **Max supported CUDA** — parse "CUDA Version" from `nvidia-smi` (driver capability)
4. **CUDA Toolkit installed** — `nvcc --version`, parse release version
5. **Toolkit ≤ driver capability** — compare versions (toolkit must not exceed driver's CUDA)
6. **Whisper linked to CUDA** — `ldd whisper-cli | grep libcudart`, check presence
7. **Linked CUDA version matches toolkit** — `libcudart.so.XX` major version matches `nvcc`
8. **CUDA runtime works** — quick whisper test run, check stderr for `ggml_cuda_init`

Diagnostic output examples:
```
✓ GPU: NVIDIA GeForce RTX 4070 (driver 590.48.01)
✓ CUDA capability: 13.1
✓ CUDA Toolkit: 12.8 (≤ 13.1, OK)
✓ whisper-cli linked: libcudart.so.12
✗ CUDA version mismatch: whisper linked to CUDA 11, toolkit is 12.8
  → Rebuild whisper.cpp: ./redictum whisper --rebuild
```

## Part 2: CUDA Toolkit management (research needed)

Explore possibility of managing CUDA Toolkit installation similar to how we manage
whisper.cpp (download, build, configure).

Questions to research:
- Can we install CUDA Toolkit locally (not system-wide) without sudo?
- NVIDIA provides runfile installers with `--toolkit --toolkitpath=<path>` — viable?
- Can we download just the minimal runtime (libcudart + nvcc) without full toolkit?
- Size concerns — full CUDA Toolkit is ~4 GB, minimal runtime is ~200 MB
- How to make CMake find our local CUDA: `-DCUDAToolkit_ROOT=<path>`
- Auto-rebuild whisper.cpp after CUDA update

Potential flow:
```
./redictum whisper
  → detects CUDA mismatch
  → offers: "CUDA 11 is outdated. Install CUDA 12.8 locally? [Y/n]"
  → downloads minimal CUDA runtime to ~/whisper.cpp/cuda/ (or similar)
  → rebuilds whisper.cpp with correct CUDA path
  → verifies GPU works
```

## Complexity
- Part 1 (diagnostics): Easy/Medium — all data available via CLI
- Part 2 (CUDA management): Hard — needs research, platform-specific, large downloads
