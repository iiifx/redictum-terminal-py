# BUG: Тихий отказ записи — нет обратной связи пользователю

> Дата: 2026-02-20
> Источник: code review + логи тестировщика
> Статус: анализ
> Приоритет: высокий

## Проблема

Если `arecord` стартует, но устройство неправильное или занято — он выдаёт пустой файл. Код тихо логирует "Recording produced no audio" и возвращается в idle. Пользователь зажал кнопку, подождал, отпустил — ничего не произошло. Ни error-тона, ни сообщения.

## Подтверждение из реальных логов

Логи тестировщика (`redictum.log`) показали **12 попыток записи подряд — все провалены**:

```
17:32:20 [INFO] Recording started: rec_20260220_173220.wav
17:32:23 [WARNING] Recording produced no audio
...
17:38:15 [INFO] Recording started: rec_20260220_173815.wav
17:38:15 [WARNING] Recording produced no audio    ← arecord умер мгновенно
```

Ноль успешных транскрипций за всю сессию. Ни одного `"Recording stopped"`, ни `"Audio normalized"`, ни `"Transcribed"`. Пользователь пробовал ~12 раз и не получил ни одного сообщения об ошибке.

Запись и "no audio" в одну секунду (17:38:15) — `arecord` умирает мгновенно при старте. Вероятная причина: устройство `pulse` недоступно (PipeWire без PulseAudio-совместимости или нет звукового устройства).

## Код

Строки 2130-2135 (worker):
```python
audio_path = recorder.stop()
if audio_path is None:
    logging.warning("Recording produced no audio")
    with state_lock:
        state = STATE_IDLE
    return                    # ← тихий возврат, нет error-тона
```

## Фикс

1. Добавить error-тон при пустой записи:

```python
if audio_path is None:
    logging.warning("Recording produced no audio — device may be busy or misconfigured")
    notifier.play_error()
    with state_lock:
        state = STATE_IDLE
    return
```

2. Проверять `returncode` процесса `arecord` после `stop()` и логировать stderr:

```python
def stop(self) -> Path | None:
    ...
    if self._process.returncode != 0:
        logging.error("arecord exited with code %d", self._process.returncode)
    ...
```

3. После N неудачных записей подряд — показать пользователю сообщение о проверке аудиоустройства.

## Связанные баги

- `bug-2026-02-20-arecord-device-incompatible.md` — устройство `pulse` может не работать на PipeWire-системах
- `bug-2026-02-20-recorder-crash-stuck-state.md` — если arecord бросает exception, state зависает
