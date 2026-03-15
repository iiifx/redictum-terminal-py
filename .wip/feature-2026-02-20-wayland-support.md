# FEATURE: Поддержка Wayland

> Дата: 2026-02-20
> Статус: идея
> Зависит от: `feature-2026-02-24-backend-strategy-pattern.md` (внедрять только после бэкендов)

## Контекст

Сейчас: X11 only. Используются xclip, xdotool, pynput через X11.
Wayland набирает долю: Ubuntu 22.04+ по умолчанию Wayland, Fedora давно на Wayland.

## Подход

Определять тип сессии через `XDG_SESSION_TYPE`:

```python
session = os.environ.get("XDG_SESSION_TYPE", "x11")
```

### Замены для Wayland

| X11 | Wayland | Пакет |
|---|---|---|
| xclip | wl-copy / wl-paste | wl-clipboard |
| xdotool | wtype или ydotool | wtype / ydotool |
| pynput (X11 backend) | pynput (Wayland?) или evdev напрямую | — |

### Проблемы

- pynput: частичная поддержка Wayland, глобальные хоткеи могут не работать без root
- ydotool: требует ydotoold демон
- wtype: работает только в некоторых композиторах

### PipeWire

paplay (PulseAudio) — PipeWire обратно совместим через pipewire-pulse. Скорее всего работает без изменений, стоит проверить.

## Prerequisite

**Реализовывать только после `feature-2026-02-24-backend-strategy-pattern.md`.**

Wayland-поддержка = новые бэкенды (`WaylandClipboard`, `WtypePaste` и т.д.),
которые подключаются через Platform Factory. Без слоя абстракций пришлось бы
добавлять if-ветки внутрь существующих классов — это путь к каше.

Порядок:
1. Внедрить Backend Strategy Pattern (ABC + Platform Factory)
2. Текущий X11-код → `X11Clipboard`, `XdotoolPaste`
3. Добавить `WaylandClipboard` (wl-copy/wl-paste), `WtypePaste` (wtype/ydotool)
4. Platform Factory: авто-детект через `XDG_SESSION_TYPE`
