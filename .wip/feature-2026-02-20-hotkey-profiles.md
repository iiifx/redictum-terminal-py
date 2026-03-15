# FEATURE: Множественные хоткеи / языковые профили

> Дата: 2026-02-20
> Статус: идея

## Контекст

Сейчас: два режима — Insert (transcribe на языке из конфига), Ctrl+Insert (translate на английский).

## Идея

Несколько комбинаций для разных действий:
- `Insert` → transcribe на русском
- `Ctrl+Insert` → translate на английский
- `Alt+Insert` → transcribe на английском (другой язык)
- `Shift+Insert` → transcribe на украинском

Или: переключаемые профили языков одним хоткеем.

## Реализация (набросок)

```yaml
input:
  hotkeys:
    - key: "Insert"
      mode: "transcribe"
      language: "ru"
    - key: "ctrl+Insert"
      mode: "translate"
    - key: "alt+Insert"
      mode: "transcribe"
      language: "en"
```

## Соображения

- Нужно переработать HotkeyListener для динамических комбинаций
- Prompt должен подбираться по языку хоткея (связь с feature-2026-02-20-language-prompts.md)
- Усложняет UI — нужно показывать текущий профиль
