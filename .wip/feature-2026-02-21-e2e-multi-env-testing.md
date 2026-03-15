# Feature: E2E тестирование в разных окружениях

## Идея

Расширить E2E тесты, чтобы покрывать нестандартные ситуации:
сломанные аудио-устройства, разные дистрибутивы, PEP 668, PipeWire vs PulseAudio.

## Вариант A: Умные fakes (минимальные затраты)

Сделать `fake-arecord` управляемым через env-переменные:

```bash
FAKE_ARECORD_MODE=ok     # default — валидный WAV
FAKE_ARECORD_MODE=fail   # exit 1 (сломанное устройство)
FAKE_ARECORD_MODE=empty  # пустой файл (нет микрофона)
```

Новые тесты в существующем E2E скрипте:
- Audio device auto-detect при сломанном arecord
- Empty recording → error tone + warning в логе
- Recorder crash recovery (state не зависает)

Плюсы: быстро, один образ, без новых Dockerfile.
Минусы: не покрывает реальные различия между дистрибутивами.

## Вариант B: Матрица Docker-образов

Несколько Dockerfile для разных окружений:

| Образ | База | Особенности |
|-------|------|-------------|
| `e2e-ubuntu-22.04` | Ubuntu 22.04 | PulseAudio, Python 3.10, pip без PEP 668 |
| `e2e-ubuntu-24.04` | Ubuntu 24.04 | PipeWire, Python 3.12, PEP 668 |
| `e2e-mint-21` | Linux Mint 21 | PulseAudio, основная целевая платформа |
| `e2e-mint-22` | Linux Mint 22 | PipeWire, PEP 668, основная будущая платформа |
| `e2e-debian-12` | Debian 12 | PipeWire, PEP 668 |

Что тестируется:
- First-run flow на каждой платформе
- PEP 668 fallback chain (apt → pip → --break-system-packages)
- Audio device auto-detection (pulse vs default vs pipewire)
- Daemon lifecycle
- Различия в системных пакетах

Плюсы: реальное покрытие, ловит платформенные баги.
Минусы: долгая сборка, много образов, нужен CI pipeline.

## Вариант C: Комбинация A + B

1. Сначала реализовать вариант A (умные fakes) — быстрый win
2. Позже добавить вариант B — матрица образов в CI (GitHub Actions)

## Связанные баги

- `bug-2026-02-20-arecord-device-incompatible` — auto-detect решает проблему
- `bug-2026-02-20-pip-pep668-externally-managed` — PEP 668 fallback
- `bug-2026-02-20-silent-recording-failure` — error tone на пустую запись

## Приоритет

Средний. Полезно для качества, но текущие E2E покрывают основной flow.
