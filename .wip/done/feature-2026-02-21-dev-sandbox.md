# FEATURE: Dev sandbox (интерактивное тестирование в Docker)

> Дата: 2026-02-21
> Статус: в работе

## Контекст

На хосте разработчика все зависимости установлены — невозможно протестировать first-run flow с нуля. Нужна чистая комната, где можно пройти полный сценарий: диагностика → промпты → установка зависимостей → сборка whisper → запуск → проверка работы.

## Идея

Bash-скрипт `dev/sandbox.sh` — запускает интерактивный Docker-контейнер с чистым Ubuntu 22.04. Пробрасывает все устройства хоста (микрофон, дисплей, клавиатура) через Docker. Скрипт redictum монтируется с хоста.

## Требования

- Один запуск: `./dev/sandbox.sh`
- Чистый Ubuntu 22.04 (минимум: python3 + sudo)
- Полный first-run flow: все промпты, установка apt/pip, сборка whisper
- Рабочий микрофон, хоткеи, буфер обмена, звуки
- Ctrl+D — контейнер удаляется, хост не тронут
- Скрипт redictum монтируется с хоста (тестируем текущую версию)

## Проброс устройств

| Ресурс | Docker-флаг | Зачем |
|--------|-------------|-------|
| X11 display | `-v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY` | pynput (хоткеи), xclip (буфер) |
| PulseAudio | `-v /run/user/$UID/pulse:/run/pulse -e PULSE_SERVER=unix:/run/pulse/socket` | paplay (звуки), arecord через pulse |
| Звуковые устройства | `--device /dev/snd` | Микрофон |
| GPU (опционально) | `--gpus all` | CUDA-сборка whisper |

## Структура

```
dev/
    sandbox.sh          # Точка входа
    Dockerfile.sandbox  # Минимальный образ (python3 + sudo)
```

## UX

```bash
$ ./dev/sandbox.sh
Building sandbox image...
Starting interactive sandbox (Ubuntu 22.04, clean)...

root@sandbox:/opt/redictum# python3 ./redictum start
# ... полный first-run flow ...
# ... тестируем работу ...
# Ctrl+D — выход, контейнер удалён
```

## Dockerfile.sandbox

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev sudo curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/redictum
```

Минимальный набор: python3 (запуск скрипта), sudo (apt install внутри скрипта), curl/git (скачивание whisper.cpp).

## sandbox.sh

```bash
#!/bin/bash
# Dev sandbox — interactive first-run testing in clean Docker

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

docker build -t redictum-sandbox -f "$SCRIPT_DIR/dev/Dockerfile.sandbox" "$SCRIPT_DIR/dev"

docker run -it --rm \
    --name redictum-sandbox \
    -v "$SCRIPT_DIR/redictum:/opt/redictum/redictum:ro" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "/run/user/$(id -u)/pulse:/run/pulse" \
    -e DISPLAY="$DISPLAY" \
    -e PULSE_SERVER=unix:/run/pulse/socket \
    --device /dev/snd \
    ${NVIDIA_FLAG:-} \
    ubuntu:22.04 \
    bash
```

## Соображения

- Скрипт монтируется read-only (`:ro`) — не испортить оригинал
- GPU-флаг опционально: если `nvidia-smi` доступен на хосте, добавлять `--gpus all`
- apt cache не сохраняется между запусками (чистая комната каждый раз)
- Для экономии времени при повторных тестах можно кэшировать Docker-образ
- Whisper модель скачивается заново каждый раз (~1-3 GB) — это долго, но это реальный UX
