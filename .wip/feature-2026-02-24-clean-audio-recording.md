# Feature: Clean Audio Recording (Noise/Interference Reduction)

**Created:** 2026-02-24
**Priority:** High (directly impacts usability in real-world scenarios)

## Problem

Redictum becomes unusable in two common scenarios:

1. **Google Meet / conferences** — microphone picks up voices of other participants
   playing through speakers, Whisper transcribes everyone instead of just the user
2. **Music playback** — loud music from speakers bleeds into the microphone,
   Whisper produces garbage output

Both problems stem from the same root cause: the microphone captures computer's
audio output (speakers/headphones leak) along with the user's voice.

## Proposed Solutions

Five approaches were identified. They are not mutually exclusive — some can be
combined, and some may work better as separate configurable features.

---

### 1. PulseAudio Echo Cancellation (`module-echo-cancel`)

PulseAudio has a built-in echo cancellation module that creates a virtual audio
source. It subtracts the speaker output signal from the microphone input in
real-time — exactly what's needed for the conference scenario.

**Implementation idea:**
- Redictum loads `module-echo-cancel` at startup, creating a virtual source
- Recording uses the virtual source instead of raw `pulse`
- Module is unloaded on exit

```bash
# Load echo cancellation module
pactl load-module module-echo-cancel source_name=redictum_clean

# Record from the clean source
arecord -D pulse.redictum_clean ...

# Unload on exit
pactl unload-module module-echo-cancel
```

**Pros:**
- Removes exactly what's playing through speakers (music, Meet voices, YouTube)
- User continues to hear everything normally — no audio interruption
- Real-time processing, no post-recording delay
- Built into PulseAudio, no extra dependencies

**Cons:**
- PulseAudio-specific (won't work with raw ALSA)
- May slightly degrade voice quality compared to clean recording in silence
- Module loading/unloading needs careful lifecycle management

**Best for:** Conferences (user keeps hearing others while recording clean voice)

---

### 2. Noise Suppression (RNNoise)

Neural network-based noise suppression via PulseAudio plugin. RNNoise is trained
to isolate human speech from background noise.

**Implementation idea:**
- Load `module-rnnoise-source` to create a denoised virtual source
- Record from that source

```bash
pactl load-module module-rnnoise-source source_name=redictum_denoised
```

**Pros:**
- Excellent at suppressing non-speech noise (music, ambient sounds, hum)
- Real-time processing

**Cons:**
- Other people's voices are also "speech" — RNNoise may not filter them out
- Requires external package (`pulseaudio-plugin-rnnoise` or similar)
- Not available on all distros out of the box

**Best for:** Background noise, music (less effective for other voices)

---

### 3. FFmpeg Post-Processing Filters

Apply noise reduction to the recorded WAV file before sending to Whisper, using
ffmpeg's audio filters. This extends the existing normalization pipeline.

**Implementation idea:**
- Add noise reduction filter step between recording and Whisper
- Use `afftdn` (spectral denoising) or `anlmdn` (non-local means denoising)

```bash
# Spectral noise reduction
ffmpeg -i input.wav -af "afftdn=nf=-25" output.wav

# Non-local means denoising
ffmpeg -i input.wav -af "anlmdn" output.wav

# Can be combined with existing loudnorm
ffmpeg -i input.wav -af "afftdn=nf=-25,loudnorm" output.wav
```

**Pros:**
- No PulseAudio module management needed
- ffmpeg is already a dependency for normalization
- Simple to implement — extends existing pipeline

**Cons:**
- Post-processing doesn't know what was playing through speakers — generic denoising
- Won't effectively remove clear speech from other people
- Adds processing time to the pipeline

**Best for:** Mild background noise, hum, ambient sounds

---

### 4. Audio Source Selection (Manual/Interactive)

Let the user choose which PulseAudio source to record from. Power users may
already have echo cancellation or noise suppression configured system-wide —
they just need to point Redictum at the right source.

**Implementation idea:**
- New command: `redictum --sources` — list available PulseAudio sources
- Config option: `recording_device = <specific_source_name>`
- Interactive picker during first setup or via config

```bash
# List available sources
pactl list sources short

# User picks one, Redictum saves to config
recording_device = alsa_input.usb-Blue_Yeti-00.analog-stereo
```

**Pros:**
- Maximum flexibility — works with any user-configured audio setup
- Respects existing system-level audio processing
- Simple implementation

**Cons:**
- Requires user to understand PulseAudio sources
- Doesn't solve the problem by itself — just enables other solutions

**Best for:** Advanced users who already have their audio pipeline configured

---

### 5. ~~Mute~~ Reduce System Volume During Recording — DONE

When recording starts — mute (or minimize) the system audio output. When
recording stops — restore the previous volume. If speakers are silent, the
microphone has nothing extra to pick up.

**Implementation idea:**
- On record start: save current volume/mute state, then mute
- On record stop: restore previous state

```bash
# Save state and mute
pactl get-sink-volume @DEFAULT_SINK@   # remember
pactl get-sink-mute @DEFAULT_SINK@     # remember
pactl set-sink-mute @DEFAULT_SINK@ 1   # mute

# After recording — restore
pactl set-sink-mute @DEFAULT_SINK@ 0   # unmute (or restore previous state)
pactl set-sink-volume @DEFAULT_SINK@ <saved_volume>
```

**Pros:**
- Trivial implementation (5-10 lines of code)
- Zero extra dependencies (pactl already available)
- 100% guaranteed — silent speakers = no interference
- No quality degradation of voice recording whatsoever
- Works against any noise source — music, Meet, YouTube, notifications

**Cons:**
- User doesn't hear anything during recording (2-5+ seconds of silence)
- During conferences: miss what others are saying while recording
- May be surprising if the user forgets this is enabled
- Longer recordings = longer audio blackout

**Best for:** Music, YouTube, any non-interactive audio. Less ideal for live
conferences where hearing others is important.

> **Implemented** (2026-02-24): `VolumeController` class with relative volume
> reduction (`recording_volume_reduce`, `recording_volume_level` config keys).
> Reduces to X% of current volume (default 30%), restores on stop. Thread-safe,
> idempotent, best-effort (pactl failures don't break recording).

---

## Combination Strategy

These solutions are **not mutually exclusive**. Possible combinations:

- **Mute (5) + Echo Cancel (1):** Mute for casual use (music/YouTube), echo
  cancel for conferences — user picks mode based on scenario
- **Echo Cancel (1) + FFmpeg filters (3):** Echo cancel removes speaker bleed in
  real-time, ffmpeg cleans up residual noise in post-processing
- **Source Selection (4) as base:** Always let user pick a source, other features
  build on top

## Open Questions

- Should these be a single configurable feature (`recording_noise_reduction`)
  with modes (`off`, `mute`, `echo_cancel`, `rnnoise`)?
- Or separate independent features that can be combined?
- Do we need a runtime toggle (e.g., hotkey to switch modes on the fly)?
- PipeWire compatibility — modern distros are migrating from PulseAudio to
  PipeWire. Echo cancel and RNNoise work differently there. Need to investigate.
- Should mute mode offer "reduce to X%" as alternative to full mute?
