# Feature: Make transcript and audio retention a conscious choice

## Problem
Everything ever dictated is kept in plaintext next to the script:

- `transcripts/YYYY-MM-DD.txt` — one line per utterance, up to `transcripts_max_files = 50`
  daily files (in practice tens of KB per day of continuous use)
- `audio/*.wav` — the raw recordings themselves, up to `audio_max_files`

Directories are created with `mkdir(exist_ok=True)` (`DirectoryManager.ensure`,
`redictum:636-639`), so they inherit the default umask — `drwxrwxr-x` for the directories and
`-rw-rw-r--` for the files, i.e. readable by any other local account.

On a single-user laptop this is a non-issue, and the history is genuinely useful (it is how
today's failure was diagnosed). The point is that it is currently an *accident* of defaults
rather than a decision: a voice tool accumulates an unbounded, world-readable log of
everything its owner said near the microphone.

## Idea
Small, non-intrusive steps — no feature, just intent:

1. Create `transcripts/` (and `audio/`) with mode `0o700`, and write transcript files `0o600`.
   Costs nothing, changes nothing for the current user.
2. Document the retention explicitly in the config comments: say plainly that transcripts and
   raw audio are kept on disk and for how long.
3. Optional: `transcripts_max_files = 0` / `audio_max_files = 0` as "do not keep at all", for
   anyone who wants dictation without a paper trail.

## Complexity
Easy. Items 1–2 are a few lines each; item 3 needs a rotation edge case (`max_files = 0` must
mean "delete all", not "keep everything").
