# BUG: Дублированный комментарий в YAML-шаблоне конфига

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: низкий

## Проблема

В `DEFAULT_CONFIG_YAML` два раза написан комментарий для поля `prompt`:

```yaml
    # Optional prompt to guide whisper transcription
    # Helps with domain-specific vocabulary and punctuation
    # Optional prompt to guide whisper transcription      ← дубликат
    # Helps with punctuation and domain-specific vocabulary
    prompt: "..."
```

Видно пользователю в `config.yaml`. Мелочь, но выглядит неаккуратно.

## Фикс

Удалить дублирующие строки, оставить один комментарий.
