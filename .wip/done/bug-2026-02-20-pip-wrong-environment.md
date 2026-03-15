# BUG: pip install использует pip из PATH вместо текущего Python

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: средний

## Проблема

`_install_pip()` вызывает `["pip", "install", ...]`. Если пользователь в virtualenv — `pip` из PATH может указывать на системный Python. Пакеты установятся не туда.

## Код

Строки 529-531:
```python
def _install_pip(self, packages: list[str]) -> bool:
    cmd = ["pip", "install", *packages]
```

## Фикс

```python
cmd = [sys.executable, "-m", "pip", "install", *packages]
```

Гарантирует, что пакеты ставятся в тот же Python, который запустил скрипт.
