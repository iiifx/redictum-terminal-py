# Redictum Terminal

**Simple. All-in-one. Run. Hold. Talk. Enjoy!**

Voice-to-text CLI for Linux. Hold a key, speak, release — transcribed text is pasted automatically.

Uses [whisper.cpp](https://github.com/ggerganov/whisper.cpp) for local speech recognition. No cloud APIs, everything runs on your machine.

## How it works

1. Hold `Insert` for 0.6s — recording starts (triple beep)
2. Speak into microphone
3. Release `Insert` — audio is normalized and sent to whisper.cpp
4. Transcribed text is copied to clipboard and auto-pasted

For **translate mode**, use `Ctrl+Insert` instead — speech is transcribed and translated to English.

## Installation

```bash
cd ~
curl -fsSL https://github.com/OWNER/REPO/raw/main/redictum -o redictum
chmod +x redictum
```

Run:

```bash
./redictum
```

On first run, the script will:
1. Check system dependencies (Python, PulseAudio, ALSA, X11)
2. Offer to install missing packages (`ffmpeg`, `xclip`, `xdotool`, `cmake`, etc.)
3. Install Python packages (`pynput`, `rich`, `PyYAML`)
4. Offer to build whisper.cpp (with CUDA if available)
5. Download a whisper model

### Requirements

- Linux (X11) — tested on Ubuntu 22.04 / Linux Mint 21.3
- Python 3.10+
- PulseAudio
- NVIDIA GPU (optional, for CUDA acceleration)

## Features

- **Push-to-talk** — hold `Insert` to record, release to transcribe and paste
- **Translate mode** — hold `Ctrl+Insert` to transcribe and translate to English
- **GPU acceleration** — CUDA support for fast transcription on NVIDIA GPUs
- **Auto-paste** — transcribed text goes to clipboard and is pasted via `Ctrl+V`
- **Clipboard preservation** — saves and restores your clipboard (text, images, binary)
- **Daemon mode** — runs in background, start/stop/status commands
- **Sound feedback** — distinct tones for recording, processing, done, error
- **Auto-setup** — installs dependencies, builds whisper.cpp, downloads models
- **Language auto-detection** — picks language from system locale, or set manually
- **Audio normalization** — ffmpeg loudnorm for consistent transcription quality
- **File rotation** — automatic cleanup of old audio and transcript files
- **YAML config** — fully configurable with comments, generated on first run

## Usage

```bash
# Interactive mode (foreground)
./redictum

# Daemon mode
./redictum start       # start background daemon
./redictum stop        # stop daemon
./redictum status      # check if daemon is running

# Whisper setup
./redictum whisper     # install/reconfigure whisper.cpp
```

## License

[MIT](LICENSE) — Vitaliy Khomenko, [Mojam](https://mojam.co)

Built with [Claude](https://claude.ai) by Anthropic.
