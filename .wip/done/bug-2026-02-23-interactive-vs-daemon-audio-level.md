# Bug: Audio level drastically different between interactive and daemon modes

## Reported by
[user data removed]

## Status
Needs confirmation — user may have changed microphone/volume between attempts.

## Symptom
Same session (Feb 23), same microphone (presumably):
- **Interactive mode** (logs 1-2): RMS 90–197, all below threshold 200 → silence detected
- **Daemon mode** (logs 4-5): RMS 1420–29045, well above threshold → transcription works

Audio is ~10-100x quieter in interactive mode than daemon mode.

## Evidence

### Interactive mode (`_151933.log`):
```
Audio RMS: 124.6 (threshold: 200.0) → silence
Audio RMS: 90.9  (threshold: 200.0) → silence
Audio RMS: 197.1 (threshold: 200.0) → silence
```

### Daemon mode (`_152220.log`):
```
Audio RMS: 23711.8 (threshold: 200.0) → OK
Audio RMS: 1420.3  (threshold: 200.0) → OK
Audio RMS: 12535.4 (threshold: 200.0) → OK
```

## Possible causes
1. User changed microphone input or volume between attempts (not a bug)
2. Different audio device selection in interactive vs daemon mode
3. PulseAudio/PipeWire routing differs when running in foreground vs background
4. `arecord` parameters differ between modes

## Next steps
- Ask user if they changed microphone or volume settings between attempts
- If reproducible: check how recording is initiated in both modes, compare `arecord` invocation
- Check if PulseAudio source differs (pactl list sources)
