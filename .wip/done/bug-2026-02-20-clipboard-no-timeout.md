# BUG: clipboard.copy() и paste() без timeout

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: высокий

## Проблема

`copy()` и `paste()` вызывают `xclip`/`xdotool` через `subprocess.run` без timeout. Если X11 сессия упала (пользователь вышел из системы, а демон работает), процесс зависнет навсегда. При этом `save()` и `restore()` корректно используют `timeout=5`.

## Код

Строка ~1425 — `copy()`:
```python
subprocess.run(
    ["xclip", "-selection", "clipboard"],
    input=text.encode("utf-8"),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)   # ← нет timeout, нет check returncode
```

Строка ~1435 — `paste()`:
```python
subprocess.run(
    ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)   # ← нет timeout
```

## Фикс

Добавить `timeout=5` и обработку ошибок, как в `save()`/`restore()`:

```python
def copy(self, text: str) -> None:
    try:
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logging.warning("Clipboard copy failed: %s", exc)
```
