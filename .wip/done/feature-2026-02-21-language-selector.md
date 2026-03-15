# FEATURE: Интерактивный выбор языка (language selector)

> Дата: 2026-02-21
> Статус: идея
> Связанная фича: `feature-2026-02-20-language-prompts.md` (авто-промпты по языку)

## Контекст

Сейчас язык определяется автоматически из системной локали (`LANG`). Пользователь может поменять в `config.yaml` вручную, но об этом нужно знать. Нет удобного способа выбрать язык из CLI.

## Идея

### 1. CLI-команда `./redictum language`

Интерактивный режим смены языка:

```
$ ./redictum language

Current language: ru (auto-detected)
Current prompt: "Правильная разговорная речь с корректной пунктуацией..."

Change language? [Y/n]: y

Popular languages:
  1. en — English
  2. ru — Русский
  3. uk — Українська
  4. de — Deutsch
  5. fr — Français
  6. es — Español
  7. pt — Português
  8. it — Italiano
  9. zh — 中文
  10. ja — 日本語
  11. ko — 한국어
  12. pl — Polski
  13. tr — Türkçe
  0. Other (enter code manually)

Select [1-13, 0]: 2

Language: ru
Prompt: "Правильная разговорная речь с корректной пунктуацией:
  запятые, точки, вопросительные и восклицательные знаки.
  Используются англицизмы, технические термины и сокращения."

Confirm? [Y/n]: y

✓ Language updated: ru
✓ Prompt updated automatically
  Config: ~/redictum/config.yaml
```

Если юзер выбирает "0" (Other):
```
Enter language code (e.g. "nl", "hi", "ar"): nl

Language: nl
Prompt: (no default prompt for "nl", whisper will use no prompt)

Confirm? [Y/n]: y
```

Если юзер отказывается на первом промпте:
```
Change language? [Y/n]: n

You can change the language at any time:
  • Run: ./redictum language
  • Edit: ~/redictum/config.yaml → language: "en"
```

### 2. Первый запуск — предложить сменить язык

После автодетекции языка, перед стартом:

```
Language detected: ru (from system locale)

Change language? [y/N]: n
```

Дефолт — No (автоопределение обычно правильное). Если юзер хочет сменить — переходит в тот же интерактивный выбор из списка.

## Связь с language-prompts

Фича `language-prompts` даёт словарь `LANGUAGE_PROMPTS` — промпт для каждого языка. Language selector использует этот же словарь:
- Выбрал язык из списка → промпт подставляется автоматически
- Выбрал язык "Other" (нет в словаре) → промпт пустой (whisper без подсказки)
- Пользователь всегда может переопределить промпт вручную в config.yaml

## Что меняется в конфиге

```yaml
dependency:
  whisper:
    language: "ru"       # было "auto", стало конкретный код
    prompt: ""           # пустая строка = автовыбор из LANGUAGE_PROMPTS
```

## CLI

```python
# В build_parser():
sub.add_parser("language", help="Change transcription language")

# В main():
if args.command == "language":
    app.run_language()
```

## Реализация run_language()

```python
def run_language(self) -> int:
    config = self._config_mgr.load()
    whisper = config.get("dependency", {}).get("whisper", {})
    current_lang = whisper.get("language", "auto")
    current_prompt = whisper.get("prompt", "")

    # Показать текущие настройки
    if current_lang == "auto":
        detected = _detect_language()
        _rprint(f"Current language: {detected} (auto-detected)")
    else:
        _rprint(f"Current language: {current_lang}")

    if current_prompt:
        _rprint(f'Current prompt: "{current_prompt[:80]}..."')
    else:
        resolved = LANGUAGE_PROMPTS.get(current_lang, "")
        if resolved:
            _rprint(f'Current prompt: "{resolved[:80]}..." (auto)')

    if not _confirm("Change language?", default=True):
        _rprint("\nYou can change the language at any time:")
        _rprint("  • Run: ./redictum language")
        _rprint(f"  • Edit: {self._config_mgr.path} → language: \"en\"")
        return EXIT_OK

    # Показать список
    languages = [
        ("en", "English"), ("ru", "Русский"), ("uk", "Українська"),
        ("de", "Deutsch"), ("fr", "Français"), ("es", "Español"),
        ("pt", "Português"), ("it", "Italiano"), ("zh", "中文"),
        ("ja", "日本語"), ("ko", "한국어"), ("pl", "Polski"),
        ("tr", "Türkçe"),
    ]
    _rprint("\nPopular languages:")
    for i, (code, name) in enumerate(languages, 1):
        _rprint(f"  {i:2d}. {code} — {name}")
    _rprint("   0. Other (enter code manually)")

    # Выбор
    choice = input("\nSelect [0-13]: ").strip()
    # ... парсинг выбора → new_lang

    # Показать промпт для подтверждения
    prompt = LANGUAGE_PROMPTS.get(new_lang, "")
    _rprint(f"\nLanguage: {new_lang}")
    if prompt:
        _rprint(f'Prompt: "{prompt}"')
    else:
        _rprint("Prompt: (none — whisper will use no prompt)")

    if not _confirm("Confirm?", default=True):
        return EXIT_OK

    # Сохранить в конфиг
    # ... обновить language, сбросить prompt на ""
    _rprint(f"\n✓ Language updated: {new_lang}")
    return EXIT_OK
```

## Соображения

- Список языков берётся из `LANGUAGE_PROMPTS` — одна точка правды
- Если демон запущен — предупредить, что изменения вступят в силу после перезапуска
- `language: "auto"` остаётся валидным значением — не ломаем обратную совместимость
- Команда `./redictum language` работает даже до первого запуска (не требует init)
