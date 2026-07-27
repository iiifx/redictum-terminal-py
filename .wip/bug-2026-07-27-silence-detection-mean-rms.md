# Bug: Silence detection uses mean RMS of the whole file, so it depends on duration

## Problem
`AudioProcessor.has_speech` (`redictum:2274-2308`) computes one RMS value over the entire
recording and compares it to a fixed threshold:

```python
samples = struct.unpack(f"<{len(data) // 2}h", data)
rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
return rms > threshold
```

Averaging over the whole file makes the result duration-dependent. The same spoken phrase
passes in a 3-second recording and can fall below the threshold in a 40-second one, because
the silence around it dilutes the energy. The consequence is the worst possible one for a
dictation tool: the recording is silently dropped with `— Silence, skipped` and the user's
speech is gone.

The threshold is configurable (`recording_silence_threshold`), but no single value can be
correct for both short and long recordings — tuning it trades false "silence" on long
recordings against whisper hallucinations on genuinely silent short ones.

## Expected
Decide on peak energy, not average energy: split the samples into windows (e.g. 50–100 ms),
compute RMS per window, and treat the file as speech if *any* window (or the loudest few)
exceeds the threshold. That makes the decision independent of how much silence surrounds the
speech, and keeps the existing threshold semantics roughly intact for short clips.

## Secondary
The RMS loop is pure Python over every sample (480k samples for a 30 s recording at 16 kHz).
Windowing lets it bail out on the first loud window, so the common case gets cheaper rather
than more expensive.
