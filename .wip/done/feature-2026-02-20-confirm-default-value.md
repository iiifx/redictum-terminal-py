# FEATURE: Дефолтное значение в промптах y/n

> Дата: 2026-02-20
> Статус: идея

## Проблема

Все промпты `[y/n]` без дефолта. Пустой Enter = No (не матчит "y"/"yes"), но пользователь этого не видит. Неудобно — приходится каждый раз набирать "y".

## Стандарт для CLI

Заглавная буква — дефолт по Enter:
- `[Y/n]` — Enter = Yes
- `[y/N]` — Enter = No

## Реализация

### Изменить `_confirm()`

```python
def _confirm(prompt: str, default: bool = False) -> bool:
    """Ask user y/n. Capital letter = default on Enter."""
    hint = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"{prompt} {hint}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not answer:
        return default
    return answer in ("y", "yes")
```

### Использование

```python
# Дефолт Yes — Enter = согласие
if _confirm("Install missing dependencies?", default=True): ...

# Дефолт No — Enter = отказ
if _confirm("Install CUDA toolkit?", default=False): ...

# Без дефолта (как сейчас) — Enter = No (обратная совместимость)
if _confirm("Do something?"): ...
```

Конкретные дефолты для каждого промпта определяются при реализации.

### UX

Было:
```
Install missing dependencies? [y/n]: _
```

Станет:
```
Install missing dependencies? [Y/n]: _
```

Пользователь просто жмёт Enter — и всё ставится. Быстрее, интуитивнее.

## Бонус

Вынести `_confirm()` в модульную функцию (сейчас дублируется в Diagnostics и WhisperInstaller — см. `bug-2026-02-20-confirm-method-duplicated.md`). Два бага чинятся одним рефакторингом.
