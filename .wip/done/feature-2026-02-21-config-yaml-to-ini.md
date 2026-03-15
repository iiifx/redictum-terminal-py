# Feature: Переход конфига с YAML на INI

## Мотивация

- PyYAML — внешняя зависимость, которую нужно ставить через pip/apt
- INI парсится встроенным `configparser` — ноль зависимостей
- Конфиг простой (3 уровня вложенности), INI покрывает его полностью
- Секции INI = текущие вложенные группы YAML

## Текущий конфиг (YAML)

```yaml
dependency:
  whisper:
    cli: "~/whisper.cpp/build/bin/whisper-cli"
    model: "~/whisper.cpp/models/ggml-large-v3-turbo-q5_0.bin"
    language: "auto"
    prompt: ""
    timeout: 120

audio:
  recording:
    device: "auto"
    normalize: true

input:
  hotkey:
    key: "Insert"
    hold_delay: 0.6
    translate_key: "ctrl+Insert"

clipboard:
  auto: true
  prefix: ""
  postfix: ""

sound:
  volume: 30
  signal_start: true
  signal_processing: false
  signal_done: true
  signal_error: true
```

## Предлагаемый INI формат

```ini
[whisper]
cli = ~/whisper.cpp/build/bin/whisper-cli
model = ~/whisper.cpp/models/ggml-large-v3-turbo-q5_0.bin
language = auto
prompt =
timeout = 120

[recording]
device = auto
normalize = true

[hotkey]
key = Insert
hold_delay = 0.6
translate_key = ctrl+Insert

[clipboard]
auto = true
prefix =
postfix =

[sound]
volume = 30
signal_start = true
signal_processing = false
signal_done = true
signal_error = true
```

## Что нужно сделать

1. Переписать `ConfigManager` — `configparser` вместо PyYAML
2. Типизация значений (configparser всё возвращает строками) — нужен свой слой:
   - `getboolean()` для bool
   - `getint()` для int
   - `getfloat()` для float
   - Остальное — строки
3. Обновить `DEFAULT_CONFIG` и шаблон
4. Миграция: если существует `config.yaml` → прочитать, сконвертировать в INI, удалить yaml
5. Убрать PyYAML из `PIP_PACKAGES` и `PIP_APT_FALLBACK`
6. Обновить тесты `test_config_manager.py`
7. Обновить комментарии в шаблоне (INI поддерживает `; comment` и `# comment`)

## Риски

- **Обратная совместимость**: нужна миграция для существующих юзеров (config.yaml → config.ini)
- **Типизация**: configparser не различает типы — нужен свой слой преобразования
- **Комментарии**: configparser теряет комментарии при записи (нужен свой writer или сохранять шаблон как строку, как сейчас с YAML)
- **Вложенность**: YAML имеет 3 уровня (`dependency.whisper.cli`), INI — только 2 (`[section].key`). Нужно уплощить структуру

## Выигрыш

- Минус одна внешняя зависимость (PyYAML)
- Быстрее first-run (не надо pip install PyYAML)
- Формат знаком всем (ini = стандарт для конфигов)

## Приоритет

Средний. Убирает зависимость, но требует миграции и переписывания ConfigManager.
