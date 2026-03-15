# FEATURE: Упрощение зависимостей (optional dependencies)

> Дата: 2026-02-20
> Статус: проектирование

## Цель

Минимизировать количество промптов при первом запуске. Сделать необязательные зависимости опциональными — скрипт работает без них, но с ограничениями.

## Анализ зависимостей

### Обязательные (нельзя убрать)

| Зависимость | Тип | Почему обязательна |
|---|---|---|
| Python 3.10+ | runtime | Сам скрипт |
| arecord (ALSA) | Stage 1 apt | Запись аудио — ядро функционала |
| X11 (DISPLAY) | Stage 1 env | Хоткеи (pynput) + clipboard (xclip) |
| xclip | Stage 2 apt | Копирование в clipboard — ядро функционала |
| pynput | Stage 2 pip | Глобальные хоткеи — ядро функционала |
| PyYAML | Stage 2 pip | Чтение config.yaml |

### Можно сделать опциональными

| Зависимость | Сейчас | Предложение | Без неё |
|---|---|---|---|
| paplay | Stage 1, fail-fast | Мягкая проверка | Работа без звуковых уведомлений |
| ffmpeg | Stage 2, обязательная | Опциональная | Пропускаем нормализацию, сырой WAV в whisper |
| xdotool | Stage 2, обязательная | Опциональная | Копируем в буфер без авто-вставки Ctrl+V |
| rich | Stage 2, pip | Убрать из PIP_PACKAGES | Graceful degradation уже есть (plain print) |

### Перенести (deferred install)

| Зависимость | Сейчас | Предложение | Когда нужна |
|---|---|---|---|
| cmake | Stage 2, каждый запуск | Только при сборке | `./redictum whisper` → `_build()` |
| build-essential | Stage 2, каждый запуск | Только при сборке | `./redictum whisper` → `_build()` |

## Итоговый эффект

### Было (первый запуск)

```
sudo apt install ffmpeg xclip xdotool cmake build-essential   # 5 пакетов
pip install pynput rich PyYAML                                  # 3 пакета
```

### Станет

```
sudo apt install xclip                                          # 1 пакет
pip install pynput PyYAML                                       # 2 пакета
```

cmake + build-essential → позже, только при `./redictum whisper`.
ffmpeg, xdotool, paplay, rich → опциональные, скрипт работает без них.

## Подход: интерактивные промпты при первом запуске

Не тихая деградация, а осознанный выбор пользователя. При первом запуске спрашиваем про каждую опциональную возможность. Ответ сохраняется в конфиг — повторно не спрашиваем.

### UX первого запуска

```
Sound notifications (requires paplay)?  [Y/n]: y
  ✓ paplay found

Audio normalization (requires ffmpeg)?  [Y/n]: y
  Installing ffmpeg...

Auto-paste via Ctrl+V (requires xdotool)?  [Y/n]: y
  ✓ xdotool found
```

Если юзер отвечает No:
- Зависимость не ставится
- Соответствующая настройка выключается в конфиге
- Скрипт работает без этой функции

### Связь: промпт → конфиг → поведение

| Промпт | Конфиг | Зависимость | При "No" |
|--------|--------|-------------|----------|
| Sound notifications? | `sound.enabled: false` | paplay | Звуки отключены |
| Audio normalization? | `audio.normalize: false` | ffmpeg | Сырой WAV в whisper |
| Auto-paste? | `clipboard.auto: false` | xdotool | Только копирование в буфер |

Дефолт везде Yes — для большинства юзеров всё включено. Опытный юзер на минимальной системе может отказаться.

## Реализация

### paplay — интерактивная проверка

```python
def _check_optional_sound(self) -> None:
    if shutil.which("paplay"):
        _rprint("  [green]✓[/green] PulseAudio (paplay)")
        return
    if _confirm("  Sound notifications (requires paplay)?", default=True):
        # установить pulseaudio-utils
        ...
    else:
        _rprint("  [dim]Sound notifications disabled[/dim]")
        # Выключить в конфиге: sound.enabled = false
```

### ffmpeg — интерактивная проверка

```python
def _check_optional_normalize(self) -> None:
    if shutil.which("ffmpeg"):
        _rprint("  [green]✓[/green] ffmpeg")
        return
    if _confirm("  Audio normalization (requires ffmpeg)?", default=True):
        # установить ffmpeg
        ...
    else:
        _rprint("  [dim]Normalization disabled[/dim]")
        # Выключить в конфиге: audio.normalize = false
```

### xdotool — интерактивная проверка

```python
def _check_optional_paste(self) -> None:
    if shutil.which("xdotool"):
        _rprint("  [green]✓[/green] xdotool")
        return
    if _confirm("  Auto-paste via Ctrl+V (requires xdotool)?", default=True):
        # установить xdotool
        ...
    else:
        _rprint("  [dim]Auto-paste disabled, text copied to clipboard only[/dim]")
        # Выключить в конфиге: clipboard.auto = false
```

### cmake + build-essential — перенести в WhisperInstaller

Убрать из `APT_PACKAGES`. Проверять только в `_build()`:
```python
def _build(self, use_cuda: bool) -> None:
    missing = []
    if not shutil.which("cmake"):
        missing.append("cmake")
    if not self._check_dpkg("build-essential"):
        missing.append("build-essential")
    if missing:
        # offer to install...
```

### Runtime проверки (safety net)

Даже если зависимость включена в конфиге, но бинарник пропал — не падаем:

```python
# AudioProcessor.normalize():
if not shutil.which("ffmpeg"):
    logging.warning("ffmpeg not found, skipping normalization")
    return input_path

# ClipboardManager.paste():
if not shutil.which("xdotool"):
    logging.warning("xdotool not found, skipping auto-paste")
    return
```

Двойная защита: промпт при установке + проверка при использовании.
