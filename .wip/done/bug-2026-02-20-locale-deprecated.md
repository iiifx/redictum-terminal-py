# BUG: locale.getdefaultlocale() deprecated (Python 3.11+)

> Дата: 2026-02-20
> Источник: репорт от тестировщика
> Статус: анализ, тривиальный фикс

## Ошибка

```
[user log removed]
DeprecationWarning: 'locale.getdefaultlocale' is deprecated and slated for removal in Python 3.15.
Use setlocale(), getencoding() and getlocale() instead.
```

## Причина

`locale.getdefaultlocale()` deprecated с Python 3.11 (PEP 597). Будет удалён в Python 3.15.

Наш код (строка 1324):
```python
loc = locale.getdefaultlocale()[0] or os.environ.get("LANG", "")
```

## Фикс

Простая замена — одна строка:

```python
# Было (deprecated):
loc = locale.getdefaultlocale()[0] or os.environ.get("LANG", "")

# Вариант A — locale.getlocale():
loc = locale.getlocale()[0] or os.environ.get("LANG", "")

# Вариант B — напрямую через env (рекомендуется):
loc = os.environ.get("LANG", "") or os.environ.get("LC_ALL", "")
```

Вариант B предпочтительнее: мы и так делаем fallback на `LANG`, а `locale.getlocale()` может вернуть `(None, None)` если локаль не настроена. Переменная `LANG` надёжнее и не зависит от версии Python.

## Приоритет

Низкий — warning, не ошибка. Но фикс на 10 секунд, можно исправить сразу.
