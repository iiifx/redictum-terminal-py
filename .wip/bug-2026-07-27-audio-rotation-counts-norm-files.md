# Bug: audio_max_files counts normalized copies, so it keeps half as many recordings

## Problem
Each recording produces two files on disk: `rec_<ts>.wav` and `rec_<ts>_norm.wav`
(`AudioProcessor.normalize`, `redictum:2263`). Rotation globs `*.wav`
(`Housekeeping.rotate_audio`, `redictum:3485`), so with the default
`audio_max_files = 50` the tool actually retains ~25 recordings, not 50.

The config comment says "Maximum number of audio files to keep (oldest are deleted)" — literally
true, but it reads as "recordings", which is what the user is thinking in.

## Expected
Pick one and make it consistent:
- treat a recording as one unit (rotate by the raw file and delete its `_norm` companion
  along with it), or
- keep counting files, and reword the config comment so the number is not misread.

## Note
Cosmetic. Recorded for completeness — no data loss beyond a shorter audio history than the
setting suggests.
