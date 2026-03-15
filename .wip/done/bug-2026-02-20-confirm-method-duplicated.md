# BUG: Метод _confirm() скопирован дважды

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: низкий

## Проблема

Идентичный метод `_confirm()` существует в двух классах:
- `Diagnostics._confirm()` (строка 550)
- `WhisperInstaller._confirm()` (строка 824)

Дублирование кода — при изменении нужно менять в двух местах.

## Фикс

Вынести в модульную функцию:

```python
def _confirm(prompt: str) -> bool:
    """Ask user y/n. Return False on EOF/Ctrl+C."""
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("y", "yes")
```

Использовать в обоих классах через `_confirm(prompt)` вместо `self._confirm(prompt)`.
