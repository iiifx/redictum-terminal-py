# BUG: dpkg -s build-essential проверяется при каждом запуске

> Дата: 2026-02-20
> Источник: code review
> Статус: анализ
> Приоритет: низкий

## Проблема

`_deps_ok()` при каждом не-первом запуске проверяет все `APT_PACKAGES`, включая `build-essential` через `dpkg -s`. Это лишний subprocess на каждый старт для пакета, который нужен ТОЛЬКО для сборки whisper.cpp.

## Связь

Пересекается с `feature-2026-02-20-optional-dependencies.md` — cmake и build-essential планируется вынести из Stage 2 в WhisperInstaller.

## Фикс

Убрать cmake и build-essential из `APT_PACKAGES`. Проверять только в `WhisperInstaller._build()`.
