# Bug: WAV header size hardcoded to 44 bytes in has_speech()

## Problem

`AudioProcessor.has_speech()` (line ~2011) skips the WAV header with `f.seek(44)`:

```python
with open(audio_path, "rb") as f:
    f.seek(44)  # skip WAV header
    data = f.read()
```

44 bytes is the **minimum** WAV header (RIFF + fmt + data chunk headers). But real WAV
files can have additional chunks before the `data` chunk (e.g., `LIST`, `INFO`, `fact`).
If arecord or ffmpeg writes extra metadata, `has_speech()` will read non-PCM bytes as
audio samples, producing garbage RMS values.

In practice, arecord typically writes a clean 44-byte header, so this hasn't caused
visible bugs yet. But it's fragile and incorrect by spec.

## Fix

Parse the WAV file properly: read RIFF header, scan chunks until `data` is found,
then read PCM samples from the correct offset.

```python
def has_speech(audio_path: Path, threshold: float = SILENCE_RMS_THRESHOLD) -> bool:
    with open(audio_path, "rb") as f:
        # Validate RIFF header
        riff = f.read(12)
        if len(riff) < 12 or riff[:4] != b"RIFF" or riff[8:12] != b"WAVE":
            return False
        # Scan chunks until "data"
        while True:
            chunk_hdr = f.read(8)
            if len(chunk_hdr) < 8:
                return False
            chunk_id = chunk_hdr[:4]
            chunk_size = struct.unpack("<I", chunk_hdr[4:8])[0]
            if chunk_id == b"data":
                data = f.read(chunk_size)
                break
            f.seek(chunk_size, 1)  # skip non-data chunk
    # ... rest of RMS calculation
```

## Impact

Low risk currently (arecord output is clean), but prevents silent corruption
if audio pipeline changes.

## Verification

- Unit test: create WAV with extra chunks before `data`, verify has_speech() works
- Unit test: standard 44-byte header still works
- E2E: all tests pass
