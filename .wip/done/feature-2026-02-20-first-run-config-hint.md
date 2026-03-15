# FEATURE: Подсказка о настройке после первого запуска

> Дата: 2026-02-20
> Статус: идея

## Контекст

После первого запуска скрипт проходит диагностику, ставит зависимости, собирает whisper — и сразу стартует. Пользователь не знает, что можно перенастроить хоткеи, язык, громкость звуков и т.д.

## Идея

В конце первого запуска (после `init()`, перед запуском listener) показать краткую подсказку — 1-2 примера, путь к конфигу.

## Реализация

### Где показывать

В `run_interactive()` и `run_start()` — после `init()`, только при первом запуске (когда `.initialized` ещё не существовал до этого вызова).

### Что показывать

```
  Configuration: ~/redictum/config.yaml
  Examples:
    • Change hotkey:  key: "F12"          (default: Insert)
    • Change language: language: "en"      (default: auto)
```

### Код

```python
def _show_config_hint(self, config: dict) -> None:
    """Show config file location and examples after first run."""
    config_path = self._config_mgr.config_path
    _rprint(f"\n[bold]Configuration:[/bold] {config_path}")
    _rprint("  Examples:")
    _rprint('    • Change hotkey:   [cyan]key: "F12"[/cyan]          (default: Insert)')
    _rprint('    • Change language: [cyan]language: "en"[/cyan]      (default: auto)')
    _rprint("")
```

### Когда показывать

Метод `init()` уже вызывает `_mark_initialized()`. Можно проверить флаг до и после:

```python
was_initialized = self._is_initialized()
config = self.init()
if not was_initialized:
    self._show_config_hint(config)
```

## Соображения

- Показывать ТОЛЬКО при первом запуске, не при каждом
- Текст краткий — 3 строки, не стена текста
- Примеры выбрать самые полезные (hotkey + language — то, что чаще всего меняют)
