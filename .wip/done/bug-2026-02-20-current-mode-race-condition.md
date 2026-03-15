# BUG: _current_mode читается вне лока (race condition)

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: средний

## Проблема

В `on_release` переменная `_current_mode` читается после выхода из `state_lock`, хотя записывается под локом в `on_hold`. Теоретическая гонка на медленных системах.

## Код

Строки 2117-2123:
```python
def on_release(mode: str) -> None:
    with state_lock:
        if state != STATE_RECORDING:
            return
        state = STATE_PROCESSING
    captured_mode = _current_mode   # ← вне лока
```

## Фикс

Захватить `_current_mode` внутри `with state_lock:`:

```python
def on_release(mode: str) -> None:
    with state_lock:
        if state != STATE_RECORDING:
            return
        state = STATE_PROCESSING
        captured_mode = _current_mode   # ← под локом
```
