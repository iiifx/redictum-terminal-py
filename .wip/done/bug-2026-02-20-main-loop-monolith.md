# BUG: _main_loop — 150-строчный монолит с вложенными closure

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: низкий

## Проблема

Метод `_main_loop()` (~150 строк) содержит:
- State machine (IDLE → RECORDING → PROCESSING → IDLE)
- Два вложенных closure (`on_hold`, `on_release`)
- Worker thread внутри closure (`def worker()` внутри `on_release`)
- Shutdown-логику с 30-секундным ожиданием
- Инициализацию всех компонентов

Тяжело читается, тяжело тестировать, тяжело отлаживать.

## Фикс

Извлечь `worker` в метод класса `Pipeline` или хотя бы в отдельный метод `_run_pipeline()`. State machine вынести в отдельный класс `StateMachine` с методами `try_start()`, `finish()`, `is_idle()`.

Это рефакторинг без изменения поведения — можно делать постепенно.
