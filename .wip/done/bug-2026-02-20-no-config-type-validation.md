# BUG: Нет валидации типов в конфиге

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: средний

## Проблема

После загрузки config.yaml нет проверки типов. Если пользователь ошибётся (`hold_delay: "fast"`, `timeout: null`, `max_files: "all"`), приложение крашится глубоко в коде с непонятным трейсбеком (`TypeError` в `threading.Timer()` или `subprocess.run(..., timeout=...)`).

## Затронутые параметры

- `hold_delay` → `threading.Timer(hold_delay, ...)` — нужен float
- `timeout` → `subprocess.run(..., timeout=timeout)` — нужен int/float
- `signal_volume` → `int(volume) / 100 * 65536` — нужен int
- `max_files` → `len(files) - max_files` — нужен int
- `sample_rate` → передаётся в arecord — нужен int

## Фикс

Добавить валидацию после `load()`:

```python
def _validate(self, config: dict) -> None:
    """Validate config value types. Raise RedictumError on mismatch."""
    checks = [
        (["input", "hotkey", "hold_delay"], (int, float), "must be a number"),
        (["dependency", "whisper", "timeout"], (int, float), "must be a number"),
        (["notification", "sound", "signal_volume"], int, "must be an integer"),
        (["storage", "audio", "max_files"], int, "must be an integer"),
        (["storage", "transcripts", "max_files"], int, "must be an integer"),
    ]
    for path, expected_type, msg in checks:
        value = config
        for key in path:
            value = value.get(key, {})
        if value and not isinstance(value, expected_type):
            raise RedictumError(
                f"Config '{'.'.join(path)}': {msg}, got {type(value).__name__}"
            )
```
