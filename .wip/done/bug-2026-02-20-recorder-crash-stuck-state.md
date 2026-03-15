# BUG: arecord crash оставляет приложение в зависшем состоянии

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: высокий

## Проблема

Если `recorder.start()` бросает исключение (устройство занято, нет прав, `arecord` не найден), состояние остаётся `STATE_RECORDING` навсегда. Хоткей больше не реагирует — приложение живое, но мёртвое.

## Код

Строки 2107-2112:
```python
def on_hold(mode: str) -> None:
    with state_lock:
        if state != STATE_IDLE:
            return
        state = STATE_RECORDING
        _current_mode = mode
    recorder.start()          # ← если тут exception — state навсегда RECORDING
```

Строки 1213-1230 — `AudioRecorder.start()`:
```python
self._process = subprocess.Popen(
    ["arecord", "-D", self._device, ...],
    ...
)
```

`Popen` может бросить `FileNotFoundError`, `OSError` (EBUSY), `PermissionError`. Ничего не поймано.

## Фикс

Обернуть `recorder.start()` в try/except, при ошибке вернуть state в IDLE:

```python
def on_hold(mode: str) -> None:
    with state_lock:
        if state != STATE_IDLE:
            return
        state = STATE_RECORDING
        _current_mode = mode
    try:
        recorder.start()
    except Exception:
        with state_lock:
            state = STATE_IDLE
        logging.exception("Failed to start recording")
        notifier.play_error()
```
