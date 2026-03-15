# Feature: Backend Strategy Pattern для системных операций

> Дата: 2026-02-24
> Статус: идея, требует обсуждения деталей реализации

## Цель

Ввести слой абстракций (ABC + стратегии) между бизнес-логикой приложения и системными
вызовами (subprocess). Публичный интерфейс одинаковый — реализация подставляется
в зависимости от окружения (X11/Wayland, Linux/macOS, наличие утилит).

## Мотивация

**Не кроссплатформенность, а удобство разработки:**

1. **Тестируемость** — Fake-бэкенды (in-memory) позволяют тестировать бизнес-логику
   без Docker, Xvfb и фейков в /usr/local/bin/. Просто pytest.
2. **Отладка** — каждый бэкенд маленький и изолированный (50-100 строк). Проблема
   с xclip → смотришь только X11Clipboard, а не весь ClipboardManager.
3. **Изменения** — добавить Wayland = новый класс, старый X11-код не трогаем
   (Open/Closed principle).
4. **Будущее** — macOS (далеко), PipeWire, другие compositor'ы — новые бэкенды,
   публичный API тот же.

## Абстракции

### 1. ClipboardBackend

```python
class ClipboardBackend(ABC):
    @abstractmethod
    def copy(self, text: str) -> None: ...

    @abstractmethod
    def paste(self) -> None: ...  # simulate Ctrl+V

    @abstractmethod
    def save(self) -> tuple[str, bytes] | None: ...

    @abstractmethod
    def restore(self, snapshot: tuple[str, bytes]) -> None: ...
```

Реализации: `X11Clipboard`, `WaylandClipboard`, `FakeClipboard`

### 2. RecorderBackend

```python
class RecorderBackend(ABC):
    @abstractmethod
    def start(self, output_path: Path) -> None: ...

    @abstractmethod
    def stop(self) -> Path | None: ...

    @abstractmethod
    def cancel(self) -> None: ...
```

Реализации: `AlsaRecorder`, `FakeRecorder`

### 3. SoundPlayerBackend

```python
class SoundPlayerBackend(ABC):
    @abstractmethod
    def play(self, wav_path: Path, volume: int) -> None: ...
```

Реализации: `PulseAudioPlayer`, `FakePlayer`

### 4. AudioProcessorBackend

```python
class AudioProcessorBackend(ABC):
    @abstractmethod
    def normalize(self, input_path: Path, output_path: Path) -> bool: ...
```

Реализации: `FfmpegProcessor`, `NoOpProcessor` (когда ffmpeg нет), `FakeProcessor`

### 5. TranscriberBackend

```python
class TranscriberBackend(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, translate: bool) -> str: ...
```

Реализации: `WhisperCppTranscriber`, `FakeTranscriber`

### 6. FetcherBackend

```python
class FetcherBackend(ABC):
    @abstractmethod
    def download(self, url: str, dest: Path) -> None: ...

    @abstractmethod
    def fetch_text(self, url: str) -> str: ...
```

Реализации: `CurlFetcher`, `WgetFetcher`, `FakeFetcher`

### 7. Platform Factory

```python
class Platform:
    """Определяет окружение и создаёт нужные бэкенды."""

    @staticmethod
    def detect() -> Platform: ...

    def create_clipboard(self) -> ClipboardBackend: ...
    def create_recorder(self, ...) -> RecorderBackend: ...
    def create_sound_player(self) -> SoundPlayerBackend: ...
    def create_processor(self) -> AudioProcessorBackend: ...
    def create_transcriber(self, ...) -> TranscriberBackend: ...
    def create_fetcher(self) -> FetcherBackend: ...
```

## Что это меняет практически

| Сценарий | Сейчас | После |
|---|---|---|
| Юнит-тест логики записи | Docker + Xvfb + fakes | pytest + FakeRecorder |
| Баг с Wayland | "Не работает" — ищи где | WaylandClipboard — 50 строк |
| Добавить Wayland | if-ветки в ClipboardManager | Новый класс, старый код не трогаем |
| Добавить macOS (потом) | Переписывать половину | Новые бэкенды, API тот же |
| Тест "тишина → не вставляется" | E2E в контейнере | FakeRecorder(silence) + FakeClipboard |

## Порядок реализации

Итерационно, по одной подсистеме за раз:

1. **Clipboard** — самая болезненная (Wayland на горизонте, 4 метода, X11 TARGETS)
2. **Recorder + Player** — следующие по важности
3. **Processor + Transcriber** — для полноты тестирования
4. **Fetcher** — наименее критичный (curl/wget уже работают)

Каждый шаг — отдельный коммит/релиз. Текущий код просто становится конкретной
реализацией (X11Clipboard, AlsaRecorder, PulseAudioPlayer).

## Связанные фичи

- `feature-2026-02-20-wayland-support.md` — Wayland-бэкенды будут строиться на этой архитектуре
- `feature-2026-02-23-modular-architecture.md` — модуляризация + бэкенды дополняют друг друга

## Открытые вопросы (обсудить перед реализацией)

- Точные сигнатуры методов ABC (какие параметры на уровне интерфейса, какие — внутри бэкенда)
- Где живёт конфигурация бэкенда (device, timeout, volume — передавать в конструктор или в методы)
- Как Platform Factory взаимодействует с ConfigManager (авто-детект vs ручной выбор в конфиге)
- Нужен ли fallback-механизм (X11 → Wayland автоматом, или ошибка + подсказка)
- Уровень детализации Fake-бэкендов (минимальный stub vs configurable mock)
