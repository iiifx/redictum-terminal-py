#!/bin/bash
# Dev sandbox — interactive first-run testing in clean Docker

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Building sandbox image..."
docker build -t redictum-sandbox -f "$SCRIPT_DIR/sandbox/Dockerfile.sandbox" "$SCRIPT_DIR/sandbox"

# Detect GPU (need both nvidia-smi and Docker NVIDIA runtime)
NVIDIA_FLAG=""
if command -v nvidia-smi &>/dev/null && docker info 2>/dev/null | grep -qi nvidia; then
    NVIDIA_FLAG="--gpus all"
    echo "NVIDIA GPU detected, passing --gpus all"
elif command -v nvidia-smi &>/dev/null; then
    echo "NVIDIA GPU found, but Docker NVIDIA runtime not available (install nvidia-container-toolkit)"
fi

echo "Starting interactive sandbox (Ubuntu 22.04, clean)..."
echo "  Mount: $SCRIPT_DIR/redictum → /opt/redictum/redictum (read-only)"
echo "  Passthrough: X11, PulseAudio, /dev/snd"
echo ""
echo "  Ctrl+C — stop redictum, then 'exit' to destroy container"
echo ""

# Allow local X11 connections from Docker
xhost +local: >/dev/null 2>&1 || true

# Remove stale container if exists (e.g. after Docker hang)
docker rm -f redictum-sandbox >/dev/null 2>&1 || true

docker run -it --rm \
    --name redictum-sandbox \
    --hostname sandbox \
    -v "$SCRIPT_DIR/redictum:/opt/redictum/redictum:ro" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "/run/user/$(id -u)/pulse:/run/pulse" \
    -v "$HOME/.config/pulse/cookie:/root/.config/pulse/cookie:ro" \
    -v redictum-apt-cache:/var/cache/apt \
    -v redictum-pip-cache:/root/.cache/pip \
    -e DISPLAY="$DISPLAY" \
    -e PULSE_SERVER=unix:/run/pulse/native \
    -e PULSE_COOKIE=/root/.config/pulse/cookie \
    --device /dev/snd \
    $NVIDIA_FLAG \
    redictum-sandbox \
    bash -c './redictum; exec bash'

# Revoke local X11 access
xhost -local: >/dev/null 2>&1 || true
