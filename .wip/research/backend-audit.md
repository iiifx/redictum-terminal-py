# Backend Audit — Intermediate Notes

## Architecture Overview

7 backends total. 6 follow the 3-layer pattern (ABC → Implementation → Orchestrator).
1 deviates (`HttpFetcherBackend` — no orchestrator).

All pipeline backends wired in `_main_loop`. HttpFetcher wired in `RedictumApp.__init__`.

---

## Backend 1: AudioRecorderBackend

- **ABC**: `AudioRecorderBackend` — line 2070
  - `start(self, output_path: Path) -> None`
  - `stop(self) -> int | None`
  - `cancel(self) -> None`
- **Impl**: `ArecordRecorder` — line 2086
  - `__init__(self, device: str)`
  - Owns subprocess.Popen, termination with timeout + kill fallback
  - STOP_TIMEOUT = 5, CANCEL_TIMEOUT = 2
- **Orchestrator**: `AudioRecorder` — line 2141
  - `__init__(self, output_dir: Path, backend: AudioRecorderBackend)`
  - Generates timestamped filenames, file validation, logging
- **Wiring** (`_main_loop`, line 4311):
  ```python
  rec_backend = ArecordRecorder(self._audio_cfg["recording_device"])
  self._recorder = AudioRecorder(audio_dir, rec_backend)
  ```

---

## Backend 2: AudioProcessorBackend

- **ABC**: `AudioProcessorBackend` — line 2193
  - `normalize(self, input_path: Path, output_path: Path) -> bool`
- **Impl**: `FfmpegProcessor` — line 2208
  - No `__init__` (stateless), TIMEOUT = 60
- **Orchestrator**: `AudioProcessor` — line 2244
  - `__init__(self, backend: AudioProcessorBackend)`
  - Speech detection (RMS), output path generation, logging
- **Wiring** (`_main_loop`, line 4313):
  ```python
  self._processor = AudioProcessor(FfmpegProcessor())
  ```

---

## Backend 3: TranscriberBackend

- **ABC**: `TranscriberBackend` — line 2453
  - `transcribe(self, audio_path: Path, language: str, prompt: str | None, translate: bool) -> str`
- **Impl**: `WhisperCliTranscriber` — line 2474
  - `__init__(self, whisper_cli: str, model_path: str, timeout: int = 120)`
  - Validates CLI exists + executable, model file exists (raises RedictumError)
- **Orchestrator**: `Transcriber` — line 2541
  - `__init__(self, backend: TranscriberBackend, language: str, prompt: str = "")`
  - Prompt resolution, blank filtering, translate-mode logic
- **Wiring** (`_main_loop`, lines 4314–4320):
  ```python
  tr_backend = WhisperCliTranscriber(
      dep["whisper_cli"], dep["whisper_model"],
      timeout=dep.get("whisper_timeout", 120),
  )
  self._transcriber = Transcriber(
      tr_backend, language, prompt=dep.get("whisper_prompt", ""),
  )
  ```

---

## Backend 4: ClipboardBackend

- **ABC**: `ClipboardBackend` — line 2604
  - `copy(self, text: str) -> None`
  - `paste(self) -> None`
  - `get_targets(self) -> list[str]`
  - `save_target(self, target: str) -> bytes | None`
  - `restore_target(self, target: str, data: bytes) -> None`
- **Impl**: `XclipBackend` — line 2628
  - No `__init__` (stateless), has `_SAFE_TARGET` regex
- **Orchestrator**: `ClipboardManager` — line 2727
  - `__init__(self, backend: ClipboardBackend)`
  - Target filtering, save/restore logic
- **Wiring** (`_main_loop`, line 4322):
  ```python
  self._clipboard = ClipboardManager(XclipBackend())
  ```

---

## Backend 5: VolumeBackend

- **ABC**: `VolumeBackend` — line 2796
  - `get_volume(self) -> int | None`
  - `set_volume(self, percent: int) -> None`
- **Impl**: `PactlVolumeBackend` — line 2808
  - No `__init__` (stateless)
- **Orchestrator**: `VolumeController` — line 2842
  - `__init__(self, backend: VolumeBackend, volume_level: int)`
  - Multi-instance locking, reduce/restore logic
- **Wiring** (`_main_loop`, lines 4325–4331, conditional):
  ```python
  if self._audio_cfg.get("recording_volume_reduce", True):
      vol_backend = PactlVolumeBackend()
      self._volume_ctl = VolumeController(
          vol_backend, self._audio_cfg.get("recording_volume_level", 30),
      )
  else:
      self._volume_ctl = None
  ```

---

## Backend 6: SoundPlayerBackend

- **ABC**: `SoundPlayerBackend` — line 3036
  - `play(self, wav_path: Path, volume: int) -> None`
- **Impl**: `PaplayPlayer` — line 3044
  - `__init__(self)` — internal `_warned` flag
- **Orchestrator**: `SoundNotifier` — line 3081
  - `__init__(self, backend: SoundPlayerBackend, volume: int = 30)`
  - WAV tone generation (lazy), feedback sounds
- **Wiring** (`_main_loop`, lines 4323–4324):
  ```python
  sound_backend = PaplayPlayer()
  self._notifier = SoundNotifier(sound_backend, volume=self._sound_cfg.get("sound_signal_volume", 30))
  ```

---

## Backend 7: HttpFetcherBackend (DEVIATION)

- **ABC**: `HttpFetcherBackend` — line 3601
  - `fetch_text(self, url: str, timeout: int = 10) -> str`
  - `download_to_file(self, url: str, dest: Path, timeout: int = 120) -> None`
- **Impl**: `CurlWgetFetcher` — line 3621
  - No `__init__` (stateless), auto-detects curl vs wget
- **Orchestrator**: **NONE** — RedictumApp uses directly
- **Wiring** (`RedictumApp.__init__`, line 3685):
  ```python
  self._fetcher: HttpFetcherBackend = CurlWgetFetcher()
  ```
  Used in `_fetch_latest_version` (line 4165) and `_download_to_file` (line 4185).

---

## Audit Findings

### P1 — Фундаментальные правила (влияют на всё остальное)

#### 1. Валидация в `__init__` — если бэкенд создан, он обязан работать

Инвариант: **создание бэкенда = гарантия работоспособности**. Если зависимость
отсутствует — бэкенд не должен создаваться (ошибка или пропуск на этапе wiring).
Не нужно проверять доступность при каждом вызове.

Текущее состояние:
- `WhisperCliTranscriber` — **соблюдает** (проверяет CLI + модель в `__init__`)
- `ArecordRecorder` — не проверяет `arecord`
- `FfmpegProcessor` — проверяет `shutil.which("ffmpeg")` при каждом вызове вместо `__init__`
- `XclipBackend` — не проверяет `xclip` / `xdotool`
- `PactlVolumeBackend` — не проверяет `pactl`
- `PaplayPlayer` — не проверяет `paplay`
- `CurlWgetFetcher` — не проверяет `curl` / `wget`

**Действие**: добавить валидацию в `__init__` всех бэкендов. Убрать runtime-проверки
(например, `shutil.which` в `FfmpegProcessor.normalize`).

#### 2. Один бэкенд = одна утилита: CurlWgetFetcher

`CurlWgetFetcher` содержит `if shutil.which("curl") ... elif shutil.which("wget")`
при каждом вызове. Это два бэкенда в одном.

**Действие**: разделить на `CurlFetcher` и `WgetFetcher`. При wiring проверить
что доступно и создать нужный.

#### 3. Один бэкенд = одна утилита: XclipBackend

`XclipBackend` использует **две** разных утилиты:
- `xclip` — чтение/запись clipboard (обязательная зависимость)
- `xdotool` — симуляция Ctrl+V для auto-paste (опциональная зависимость)

При этом `xdotool` — опциональный (`_OPTIONAL_DEPS`, `paste_auto = true/false`),
а `xclip` — обязательный (`APT_PACKAGES`). Один бэкенд смешивает обязательную
и опциональную функциональность.

**Действие**: продумать разделение. Возможные варианты — вынести paste в отдельный
бэкенд, или разделить `ClipboardBackend` на два ABC (clipboard data + paste action).
Решение требует проработки.

### P2 — Структура (добавить недостающее)

#### 4. Опциональные бэкенды создаются безусловно

Бэкенды делятся на обязательные и опциональные. Опциональные можно не создавать,
если зависимость не установлена или функция отключена в конфиге.

**Обязательные** (без них скрипт не работает):
- `ArecordRecorder` → `AudioRecorder` — нет записи = нет ничего
- `WhisperCliTranscriber` → `Transcriber` — нет транскрипции = нет результата

**Опциональные** (есть настройки/условия для отключения):

| Бэкенд | Условие отключения | Сейчас |
|--------|-------------------|--------|
| `FfmpegProcessor` | `recording_normalize = false` или ffmpeg не установлен | Создаётся всегда (строка 4313), проверка только при вызове (строка 4433) |
| `PactlVolumeBackend` | `recording_volume_reduce = false` | **Уже опционален** — `None` если выключен (строка 4325–4331) |
| `PaplayPlayer` | Все `sound_signal_*` выключены или paplay не установлен | Создаётся всегда (строка 4323) |
| `XclipBackend` | `paste_auto = false` — тогда save/paste/restore не нужны | Создаётся всегда (строка 4322). xclip обязателен (APT_PACKAGES), но xdotool опционален. При `paste_auto = false` используется только `copy()`, а `paste()`, `save()`, `restore()` — мёртвый код |
| `CurlWgetFetcher` | Нужен только для команды `update` | Создаётся в `__init__` (строка 3685) для всех режимов работы, включая interactive |

**Действие**: не создавать бэкенд, если он не нужен. Только `PactlVolumeBackend` уже
так работает. Остальные 4 опциональных бэкенда создаются безусловно.

#### 5. HttpFetcherBackend — нет оркестратора

Единственный бэкенд без промежуточного класса. `RedictumApp` вызывает
`self._fetcher.fetch_text()` / `self._fetcher.download_to_file()` напрямую.

**Действие**: добавить оркестратор, даже если роль минимальна. Единообразие
архитектуры важнее экономии на одном классе.

#### 6. HotkeyListener — не бэкенд, но должен стать

`HotkeyListener` напрямую завязан на `pynput` (X11). Для Wayland потребуется другая
реализация (libinput, DBus, evdev). Сейчас это единственный обязательный компонент
с внешней зависимостью, который не абстрагирован через ABC.

**Действие**: выделить `HotkeyListenerBackend` ABC, перенести pynput-логику
в конкретную реализацию (например, `PynputHotkeyListener`).

#### 7. `has_speech()` не относится к AudioProcessor

`AudioProcessor.has_speech()` — это `@staticmethod`, который парсит WAV и считает RMS.
Не использует бэкенд, не связан с нормализацией. Прицеплен к оркестратору случайно.

**Действие**: вынести из `AudioProcessor`. Куда именно — решить отдельно.

### P3 — Нейминг (делать последним, после всех структурных изменений)

#### 8. Нейминг реализаций — привести к единообразию

Часть реализаций сохраняют суффикс "Backend", часть — нет:
- **С суффиксом**: `XclipBackend`, `PactlVolumeBackend`
- **Без суффикса**: `ArecordRecorder`, `FfmpegProcessor`, `WhisperCliTranscriber`, `PaplayPlayer`, `CurlWgetFetcher`

**Действие**: выбрать единый стиль и переименовать.

#### 9. Нейминг оркестраторов — привести к единообразию

Текущие имена:
- `AudioRecorder`, `AudioProcessor`, `Transcriber`, `ClipboardManager`, `VolumeController`, `SoundNotifier`

Нет единого паттерна — используются разные суффиксы (Recorder, Processor, Manager,
Controller, Notifier) или вообще без суффикса (Transcriber).

**Действие**: выбрать единый стиль и переименовать.

---

## Выводы аудита

Обсудили вариант фабрики-класса (`BackendFactory`) для централизованного порождения
бэкендов. Решение: **перебор** — при одной реализации на бэкенд фабрика станет
богом-классом. Вместо этого — выделить метод `_build_pipeline()` в `RedictumApp`,
который собирает всю wiring-логику в одном месте. Полноценная фабрика понадобится
только когда появится реальный выбор реализаций из конфига.

Все 10 пунктов (9 findings + wiring) вынесены в рабочий документ:
`.wip/refactor-2026-02-26-backend-audit.md`
