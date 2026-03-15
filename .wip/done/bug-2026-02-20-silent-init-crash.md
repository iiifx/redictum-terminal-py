# BUG: Молчаливый крэш при инициализации — ни ошибки, ни лога

> Дата: 2026-02-20
> Источник: логи тестировщика
> Статус: анализ
> Приоритет: высокий

## Проблема

Скрипт запускается, пишет `"Interactive mode started"` и `"Language auto-detected"`, затем молча умирает. Нет стектрейса, нет сообщения, нет лога ошибки. Пользователь не понимает, что происходит, и перезапускает раз за разом.

## Подтверждение из реальных логов

8 запусков подряд — все мёртвые:

```
17:24:07 [INFO] Interactive mode started (PID 22713)
17:24:07 [INFO] Language auto-detected from locale: 'en'
                                                          ← тишина, процесс умер
17:24:53 [INFO] Interactive mode started (PID 30683)
17:24:53 [INFO] Language auto-detected from locale: 'en'
                                                          ← опять тишина
...повторяется 8 раз...

17:30:04 [INFO] Interactive mode started (PID 31797)
17:30:04 [INFO] Language auto-detected from locale: 'en'
17:30:04 [INFO] Hotkey listener started                   ← 9-я попытка — наконец заработал
```

Между `"Language auto-detected"` и `"Hotkey listener started"` — вызовы `init()` / `init_quick()` / `_deps_ok()` / `_main_loop()`. Что-то падает в этом промежутке.

## Вероятные причины

1. **Зависимости не установлены** — `_deps_ok()` возвращает False, `init()` запускает диагностику, промпт `y/n` → пользователь жмёт Ctrl+C или n → молчаливый выход
2. **pynput не установлен** — `from pynput.keyboard import ...` внутри `_main_loop()` бросает ImportError → не поймано
3. **X11 проблема** — pynput Listener не может подключиться к дисплею → exception в треде
4. **Exception в `init()`** — любая непойманная ошибка между логированием locale и созданием listener

## Фикс

1. Обернуть весь путь от `init()` до `_main_loop()` в try/except с логированием:

```python
try:
    if self._is_initialized():
        self._config = self.init_quick()
        if not self._deps_ok(self._config):
            self._config = self.init()
    else:
        self._config = self.init()
    self._main_loop(stop_event)
except Exception:
    logging.exception("Fatal error during startup")
    _rprint("[red]Fatal error. Check logs for details.[/red]")
    sys.exit(1)
```

2. Добавить логирование ключевых этапов:

```python
logging.info("Checking dependencies...")
logging.info("Dependencies OK, starting main loop...")
logging.info("Hotkey listener started...")
```

Чтобы по логу было видно, на каком именно этапе скрипт умер.
