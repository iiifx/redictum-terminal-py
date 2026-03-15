# Backend Strategy Pattern — Plan

> Status: COMPLETE (all 7 steps done)
> Created: 2026-02-25

## Done

### Step 1: SoundPlayerBackend (commit d164fd1)
- ABC: `SoundPlayerBackend` — `play(wav_path, volume)`
- Concrete: `PaplayPlayer` — paplay subprocess
- Orchestrator: `SoundNotifier` — tone generation, caching, delegates playback

### Step 2: AudioRecorderBackend (commit 78ca56c)
- ABC: `AudioRecorderBackend` — `start(output_path)`, `stop() -> int|None`, `cancel()`
- Concrete: `ArecordRecorder` — arecord subprocess lifecycle (start/stop/cancel with timeouts)
- Orchestrator: `AudioRecorder` — timestamped filenames, file validation, logging

---

## Remaining

### Step 3: AudioProcessorBackend

**Complexity:** low (1 method)

**ABC:**
```python
class AudioProcessorBackend(ABC):
    @abstractmethod
    def normalize(self, input_path: Path, output_path: Path) -> bool:
        """Normalize audio. Return True on success."""
```

**Concrete: `FfmpegProcessor`**
- Owns: `shutil.which("ffmpeg")` check, `subprocess.run(["ffmpeg", ...])` with loudnorm filter
- Constructor: none needed (stateless)

**Orchestrator: `AudioProcessor`**
- Keeps: `has_speech()` (pure Python WAV RMS calculation — no subprocess)
- Keeps: output path generation, logging, `_rprint` status messages
- Constructor: `__init__(self, backend: AudioProcessorBackend)`

**Instantiation in `_main_loop`:**
```python
# Before:
self._processor = AudioProcessor()
# After:
proc_backend = FfmpegProcessor()
self._processor = AudioProcessor(proc_backend)
```

---

### Step 4: TranscriberBackend

**Complexity:** medium (command building split)

**ABC:**
```python
class TranscriberBackend(ABC):
    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        language: str,
        prompt: str | None,
        translate: bool,
    ) -> str:
        """Return raw transcribed text."""
```

**Concrete: `WhisperCliTranscriber`**
- Owns: CLI path/model validation, command building (`-m`, `-f`, `--translate`, `-l`, `--prompt`), `subprocess.run()`
- Constructor: `__init__(self, whisper_cli: str, model_path: str, timeout: int = 120)`

**Orchestrator: `Transcriber`**
- Keeps: `_resolve_prompt()`, `BLANK_MARKERS` filtering, result cleanup
- Constructor: `__init__(self, backend: TranscriberBackend, language: str, prompt: str = "")`

**Instantiation in `_main_loop`:**
```python
# Before:
self._transcriber = Transcriber(dep["whisper_cli"], dep["whisper_model"], language, ...)
# After:
tr_backend = WhisperCliTranscriber(dep["whisper_cli"], dep["whisper_model"], timeout=...)
self._transcriber = Transcriber(tr_backend, language, prompt=dep.get("whisper_prompt", ""))
```

---

### Step 5: ClipboardBackend

**Complexity:** medium (5 methods, highest Wayland impact)

**ABC:**
```python
class ClipboardBackend(ABC):
    @abstractmethod
    def copy(self, text: str) -> None:
        """Copy text to clipboard."""

    @abstractmethod
    def paste(self) -> None:
        """Simulate paste (Ctrl+V or equivalent)."""

    @abstractmethod
    def get_targets(self) -> list[str]:
        """Return available clipboard MIME targets."""

    @abstractmethod
    def save_target(self, target: str) -> bytes | None:
        """Read raw clipboard data for a specific target."""

    @abstractmethod
    def restore_target(self, target: str, data: bytes) -> None:
        """Write raw data to clipboard for a specific target."""
```

**Concrete: `XclipBackend`**
- Owns: all `subprocess.run(["xclip", ...])` calls, `subprocess.run(["xdotool", ...])` for paste
- Owns: `time.sleep(0.05)` before paste (X11-specific timing)
- Constructor: none needed (stateless)

**Orchestrator: `ClipboardManager`**
- Keeps: `_SKIP_TARGETS`, `_SUPPORTED_PREFIXES`, target filtering/selection logic
- Keeps: `save()` orchestration (get_targets -> filter -> save_target)
- Keeps: `restore()` orchestration
- Constructor: `__init__(self, backend: ClipboardBackend)`

**Instantiation in `_main_loop`:**
```python
# Before:
self._clipboard = ClipboardManager()
# After:
clip_backend = XclipBackend()
self._clipboard = ClipboardManager(clip_backend)
```

---

### Step 6: VolumeBackend

**Complexity:** low (2 static methods -> 2 ABC methods)

**ABC:**
```python
class VolumeBackend(ABC):
    @abstractmethod
    def get_volume(self) -> int | None:
        """Return current system volume (0-100), or None on failure."""

    @abstractmethod
    def set_volume(self, percent: int) -> None:
        """Set system volume to percent (0-100)."""
```

**Concrete: `PactlVolumeBackend`**
- Owns: `subprocess.run(["pactl", "get-sink-volume", ...])` and `subprocess.run(["pactl", "set-sink-volume", ...])`
- Replaces current `VolumeController._get_current_volume()` and `._set_volume()` static methods

**Orchestrator: `VolumeController`**
- Keeps: all multi-instance coordination (fcntl file locking, PID tracking, `_shared_acquire`, `_shared_release`)
- Keeps: `_resolve_lock_path()`, `_pid_alive()`
- Constructor: `__init__(self, backend: VolumeBackend, volume_level: int)`

**Instantiation in `_main_loop`:**
```python
# Before:
self._volume_ctl = VolumeController(self._audio_cfg.get("recording_volume_level", 30))
# After:
vol_backend = PactlVolumeBackend()
self._volume_ctl = VolumeController(vol_backend, self._audio_cfg.get("recording_volume_level", 30))
```

---

### Step 7 (optional): HttpFetcherBackend

**Complexity:** low, **Priority:** low (update command only)

**ABC:**
```python
class HttpFetcherBackend(ABC):
    @abstractmethod
    def fetch_text(self, url: str, timeout: int = 10) -> str:
        """Fetch URL content as text."""

    @abstractmethod
    def download_to_file(self, url: str, dest: Path, timeout: int = 120) -> None:
        """Download URL to a local file."""
```

**Concrete: `CurlWgetFetcher`**
- Owns: `shutil.which("curl")` / `shutil.which("wget")` fallback, subprocess calls

**Orchestrator: stays inside `RedictumApp`**
- `_fetch_latest_version()` and `_download_to_file()` delegate to backend

Can be deferred — only used by update command, no Wayland motivation.

---

## Verification checklist (per step)

1. `ruff check redictum` — no new lint errors
2. `pytest tests/test_<module>.py -v` — all pass
3. `pytest tests/test_app_pipeline.py -v` — all pass
4. `pytest tests/ -v` — full suite passes

## CLAUDE.md updates (per step)

- Add ABC + Concrete to architecture table
- Update orchestrator description

## CHANGELOG.md (per step)

- Add entry under `[Unreleased] → Changed`
