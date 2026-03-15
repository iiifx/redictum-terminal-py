# Feature: Sandbox Mode — transcription inside Docker

## Idea

Run heavy dependencies (whisper.cpp, ffmpeg, model) inside a Docker container,
keeping the host clean. Only lightweight packages on the host (pynput, xclip,
xdotool, paplay, arecord, rich, PyYAML).

## Architecture

**Host (native):**
- pynput — hotkey listener (needs X11)
- arecord — microphone recording (needs ALSA/PulseAudio)
- paplay — sound feedback (needs PulseAudio)
- xclip/xdotool — clipboard/typing (needs X11)
- python3, rich, PyYAML — script and UI

**Container (daemon):**
- whisper.cpp — build and runtime
- whisper model (~547 MB+)
- ffmpeg — audio normalization
- cmake, build-essential, git — build tools

## Flow

1. `redictum start` → spawns Docker container as background service
2. User presses hotkey → host records WAV via arecord
3. Host sends WAV to container (mounted volume or Unix socket)
4. Container: ffmpeg normalize → whisper transcribe → return text
5. Host receives text → xdotool type

## Key Insight: Pre-built Docker Image

The Docker image can be pre-built with whisper.cpp + model baked in and pushed
to a registry (Docker Hub / GitHub Container Registry). Users just `docker pull`
instead of building for 40 minutes. Like a .deb package but for the entire
environment.

Variants:
- `redictum-sandbox:cpu` — CPU-only whisper build
- `redictum-sandbox:cuda` — CUDA-enabled build (larger image, needs nvidia-container-toolkit)

## Implementation Notes

- Two transcription backends: `native` (current) and `docker`
- IPC options: mounted volume (simplest), Unix socket, gRPC
- Config: `dependency.whisper.backend: "native" | "docker"`
- Must support both modes — Docker is not always available
- GPU passthrough: requires nvidia-container-toolkit on host

## Complexity

High. This is essentially a second operating mode for the entire app.
Cleanest approach: extract transcription (ffmpeg + whisper) into a module
with clear interface "WAV in → text out", then implement native and docker
backends. Rest of the code stays unchanged.

## Open Questions

- Minimum Docker version required?
- Image size budget (CPU vs CUDA)?
- How to handle Docker not installed (graceful fallback to native)?
- Auto-detect Docker and suggest sandbox mode on first run?
