# BUG: Английский prompt перебивает язык на модели large-v3

> Дата: 2026-02-20
> Источник: собственное тестирование
> Статус: заблокирован — зависит от `feature-2026-02-20-language-prompts.md`

## Симптомы

Пользователь говорит по-русски, НЕ зажимает Ctrl (режим transcribe, не translate), но whisper выдаёт текст на английском.

## Конфигурация при воспроизведении

- Модель: `ggml-large-v3.bin` (~3.1 GB, самая большая)
- Язык: `auto` → определяется как `ru`
- Prompt: `"Proper conversational speech with correct punctuation: commas, periods, question marks and exclamation marks. Anglicisms, technical terms and abbreviations are used."`

## Команда whisper в transcribe mode

```
whisper-cli -m large-v3.bin -f audio.wav --no-timestamps -np -l ru \
  --prompt "Proper conversational speech..."
```

## Причина

Модель `large-v3` (полная, 3.1 GB) сильнее реагирует на язык prompt, чем turbo-варианты. Видит длинный английский prompt → решает, что контекст английский → выдаёт английский текст, игнорируя `-l ru`.

Тот же класс бага, что `--translate` + `--prompt` = сломано (уже задокументировано). Prompt у whisper перебивает языковые настройки.

С `large-v3-turbo-q5_0` (547 MB, дефолтная) эффект слабее — она менее чувствительна.

## Варианты фикса

1. **Не передавать prompt когда язык не английский** — консистентно с translate mode, минимальное изменение
2. **Языко-зависимые промпты** — `LANGUAGE_PROMPTS` dict, авто-выбор по языку (см. `feature-2026-02-20-language-prompts.md`)
3. **Убрать дефолтный prompt вообще** — самый простой, но теряем улучшение пунктуации для английского

Рекомендация: вариант 2 (решает проблему и улучшает опыт для всех языков).

## Зависимость

Этот баг будет решён в рамках фичи `feature-2026-02-20-language-prompts.md` —
языко-зависимые промпты автоматически устранят конфликт английского prompt с `-l ru`.
Перепроверить и закрыть после внедрения фичи.

## Связанные документы

- `feature-2026-02-20-language-prompts.md` — реализация языко-зависимых промптов
- `feature-2026-02-21-language-selector.md` — интерактивный выбор языка (тоже требует промпты)
