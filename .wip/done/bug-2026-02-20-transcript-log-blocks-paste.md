# BUG: Ошибка записи транскрипта блокирует вставку текста

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: высокий

## Проблема

`_log_transcript()` вызывается ДО `clipboard.paste()`. Если диск полный или папка удалена — `OSError`, и текст не вставляется, хотя транскрипция прошла успешно. Лог транскрипций и вставка не должны быть связаны.

## Код

Строки ~2155-2170 (worker):
```python
_log_transcript(transcripts_dir, final_text)   # ← может бросить OSError
saved = clipboard.save()
clipboard.copy(final_text)
clipboard.paste()                               # ← никогда не выполнится
```

## Фикс

Обернуть `_log_transcript` в try/except отдельно:

```python
try:
    _log_transcript(transcripts_dir, final_text)
except OSError:
    logging.exception("Failed to write transcript log")

saved = clipboard.save()
clipboard.copy(final_text)
clipboard.paste()
```
