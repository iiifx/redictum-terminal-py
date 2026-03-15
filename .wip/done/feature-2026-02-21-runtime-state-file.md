# FEATURE: Runtime state file (.state)

> Дата: 2026-02-21
> Статус: идея

## Контекст

Сейчас `.initialized` — просто флаг-файл с датой. Между запусками нет места для хранения технических данных рантайма. Конфиг (`config.yaml`) — пользовательский, трогать его для внутренних нужд нельзя.

## Идея

Заменить `.initialized` на полноценный state-файл (`.state`), хранящий технические метаданные между запусками.

## Формат: JSON

Стандартный модуль `json` — встроен в Python, без внешних зависимостей (в отличие от YAML/PyYAML). Файл технический, человеку его редактировать не нужно → комментарии не требуются → JSON идеально подходит.

Альтернативы:
- `configparser` (INI) — встроенный, но плоский (нет вложенности)
- `tomllib` — встроен с Python 3.11, но только чтение (нет writer в stdlib)
- `shelve` / `dbm` — бинарный, нечитаемый

JSON — лучший баланс: встроенный, читаемый, поддерживает вложенность.

## Структура

```json
{
  "version": "1.0.0",
  "initialized_at": "2026-02-21T14:30:00",
  "last_run": "2026-02-21T16:45:00",
  "python_version": "3.12.0",
  "whisper_build": "cuda",
  "cuda_version": "12.8",
  "config_hint_shown": true
}
```

## Что хранить

| Поле | Тип | Зачем |
|------|-----|-------|
| `version` | str | Версия redictum. Self-update: с какой обновились |
| `initialized_at` | str (ISO) | Дата первого запуска (заменяет `.initialized`) |
| `last_run` | str (ISO) | Последний запуск. "Давно не запускал — обновись?" |
| `python_version` | str | На чём собирались. Обновил Python → предупредить |
| `whisper_build` | str | "cuda" / "cpu". Появилась CUDA → предложить пересборку |
| `cuda_version` | str | Версия CUDA при сборке. Обновил драйвер → пересобрать |
| `config_hint_shown` | bool | Показывали ли подсказку о конфиге |

## API

```python
import json

class StateManager:
    """Read/write runtime state (.state JSON file)."""

    def __init__(self, base_dir: Path) -> None:
        self._path = base_dir / ".state"

    def load(self) -> dict:
        if not self._path.exists():
            return {}
        with open(self._path) as f:
            return json.load(f)

    def save(self, state: dict) -> None:
        with open(self._path, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        return self.load().get(key, default)

    def set(self, key: str, value) -> None:
        state = self.load()
        state[key] = value
        self.save(state)
```

## Миграция

При первом запуске после обновления:
1. Если `.initialized` существует, а `.state` нет → мигрировать (прочитать дату из `.initialized`, создать `.state`, удалить `.initialized`)
2. Если ничего нет → первый запуск, создать `.state` с нуля

## Соображения

- Файл технический — не документировать для пользователя
- При ошибке чтения (битый JSON) — пересоздать с нуля, не падать
- `last_run` обновлять при каждом запуске
- `version` обновлять при каждом запуске (может измениться после self-update)
