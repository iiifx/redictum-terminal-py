# FEATURE: CLI config overrides (параметры через строку запуска)

> Дата: 2026-02-21
> Статус: идея

## Контекст

Сейчас конфиг мерджится в два слоя: DEFAULT_CONFIG → config.yaml. Нет возможности перебить параметр одноразово при запуске — нужно редактировать файл.

## Идея

Третий слой: CLI-аргументы при запуске. Приоритет:

1. **CLI аргументы** — жёсткий override на один запуск
2. **config.yaml** — пользовательские настройки (persistent)
3. **DEFAULT_CONFIG** — дефолты в коде

## Применение

- **Отладка:** запустить с другим языком/моделью без правки конфига
- **Тесты:** E2E тесты передают параметры напрямую, без sed-правок config.yaml
- **Эксперименты:** попробовать настройку перед тем, как прописать в конфиг

## Синтаксис

> Точный формат CLI — TBD при реализации. Должен быть максимально удобным для пользователя. Варианты для рассмотрения:

```bash
# Вариант A: --set key=value (стандарт Helm/k8s)
./redictum start --set sound.signal_start=false

# Вариант B: -c key=value (короче)
./redictum start -c sound.signal_start=false

# Вариант C: --key value (плоские флаги для популярных параметров)
./redictum start --language en --no-sound --no-normalize

# Вариант D: комбинация — шорткаты для частых + --set для остального
./redictum start --lang en --set input.hotkey.hold_delay=0.5
```

Несколько override за раз:
```bash
./redictum start --set sound.signal_start=false --set audio.normalize=false
```

## Безопасность

### Валидация ключей
Принимаем ТОЛЬКО ключи, существующие в DEFAULT_CONFIG. Неизвестный ключ → ошибка с подсказкой:
```
Error: unknown config key "foo.bar"
Available keys: input.hotkey.key, input.hotkey.hold_delay, ...
```

### Валидация типов
Тип значения определяется по дефолту:
- `bool` (`true`/`false`) — для `signal_start`, `normalize`, `auto`
- `int` — для `max_files`, `signal_volume`
- `float` — для `hold_delay`
- `str` — для `key`, `language`, `prompt`, `cli`, `model`

Несовпадение типа → ошибка:
```
Error: "sound.signal_volume" expects integer, got "abc"
```

### Пути (cli, model)
CLI-аргументы приходят от того же юзера, который запускает скрипт. Это не новый вектор атаки (он может просто отредактировать config.yaml). Но: валидировать, что путь существует, если это path-параметр.

### Общие правила
- Никакого `eval()`/`exec()` — только безопасный парсинг типов
- Ограничение длины значения (500 символов)
- Dot-нотация для вложенных ключей — парсить только через split(".")
- Максимальная глубина = 3 (соответствует структуре конфига)

## Реализация (высокоуровнево)

```python
def _apply_overrides(config: dict, overrides: list[str]) -> dict:
    """Apply CLI overrides to merged config.

    Args:
        config: Already merged config (defaults + user yaml).
        overrides: List of "dotted.key=value" strings from CLI.

    Returns:
        Config with overrides applied.

    Raises:
        RedictumError: On unknown key or type mismatch.
    """
    for item in overrides:
        key, _, value = item.partition("=")
        # 1. Validate key exists in DEFAULT_CONFIG
        # 2. Get expected type from default value
        # 3. Parse value to expected type
        # 4. Set in config dict
    return config
```

В main():
```python
# После загрузки конфига:
config = config_mgr.load()  # defaults + yaml
if args.set:
    config = _apply_overrides(config, args.set)
```

## Соображения

- Override живёт только один запуск — не записывается в config.yaml
- В логе записывать, какие параметры были перебиты: `logging.info("Config override: %s = %s", key, value)`
- Не логировать значения path-параметров полностью (безопасность)
- В баннере при старте показывать, что есть overrides: `[overrides: 2]`
