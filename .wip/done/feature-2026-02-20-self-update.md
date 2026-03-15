# FEATURE: Самообновление (self-update)

> Дата: 2026-02-20
> Обновлено: 2026-02-24
> Статус: утверждён

## Контекст

Сейчас обновление ручное: `curl -fsSL ... -o ~/redictum/redictum`.
Конфиг лежит отдельно и не затрагивается, но пользователь об этом не знает.

## Команда

```bash
./redictum update    # проверить + обновить (одна команда)
```

Без `--check` — одна команда делает всё: проверяет, показывает, спрашивает, обновляет.

## Флоу

1. Показать текущую версию
2. Запрос к GitHub Releases API → получить latest tag
3. Сравнить версии (semver) → если не новее → "Уже актуальная версия", выход
4. Показать новую версию, спросить подтверждение (y/n)
5. Пользователь отказался → выход
6. Проверить, не запущен ли демон → если запущен → "Остановите демон перед обновлением", выход
7. Скачать `redictum.sha256` из релиза (эталонный хэш)
8. Скачать `redictum` во временный файл
9. Посчитать SHA-256 временного файла
10. Сравнить хэши → не совпали → "Ошибка: хэш не совпадает, файл повреждён", удалить tmp, выход
11. Хэши совпали → бэкап текущего скрипта (`redictum.bak`) → замена → `chmod 755`
12. Сообщение об успешном обновлении, выход

## Сравнение версий

Semver-сравнение (major.minor.patch), без внешних зависимостей:

```python
def _compare_versions(a: str, b: str) -> int:
    """Return -1 if a < b, 0 if a == b, 1 if a > b."""
    ta = tuple(int(x) for x in a.split("."))
    tb = tuple(int(x) for x in b.split("."))
    return (ta > tb) - (ta < tb)
```

Защита от даунгрейда: если текущая версия новее GitHub — не обновлять.

## Верификация целостности (SHA-256)

- В каждом релизе публикуется файл `redictum.sha256` с хэшем скрипта
- Процесс релиза: `sha256sum redictum > redictum.sha256`, приложить к релизу
- При обновлении: скачать `.sha256`, скачать скрипт, сверить
- SHA-256 — современный стандарт, надёжнее MD5

## Бэкап

- Перед заменой: `shutil.copy2(script, script.bak)`
- Откат одной командой: `mv ~/redictum/redictum.bak ~/redictum/redictum`
- Бэкап перезаписывается при каждом обновлении (хранится только предыдущая версия)

## Таймауты и ошибки

- Таймаут на сетевые запросы (curl) — не зависаем при недоступности GitHub
- Нет интернета → внятное сообщение об ошибке
- Не удалось скачать `.sha256` → ошибка, не продолжаем
- Не удалось скачать скрипт → ошибка, не продолжаем

## Демон

- Если демон запущен — НЕ обновляем
- Сообщаем: "Остановите демон (`./redictum stop`) перед обновлением"
- Не останавливаем демон автоматически — это решение пользователя

## Конфиг

Конфиг (INI) лежит отдельно от скрипта — обновление его не затрагивает.
Новые параметры в новой версии → fallback на дефолты из кода (уже работает).
Перегенерация конфига: `./redictum --config start` (уже есть).

## UX-примеры

```
$ ./redictum update
  Current version: 1.3.0
  Checking for updates...
  New version available: 1.4.0
  Update? [y/n]: y
  Downloading...
  Verifying checksum...
  ✓ Updated: 1.3.0 → 1.4.0
  Backup saved: ~/redictum/redictum.bak
```

```
$ ./redictum update
  Current version: 1.4.0
  Checking for updates...
  Already up to date.
```

```
$ ./redictum update
  ...
  Update? [y/n]: y
  Daemon is running. Stop it first: ./redictum stop
```

```
$ ./redictum update
  ...
  Downloading...
  Verifying checksum...
  ✗ Checksum mismatch — download may be corrupted. Aborting.
```

## CLI

```python
# В build_parser():
sub.add_parser("update", help="Update to the latest version")

# В main():
if args.command == "update":
    run_update()
```

## Процесс релиза (дополнение)

К текущему процессу добавляется шаг генерации чексуммы:

```bash
sha256sum redictum > redictum.sha256
# Приложить redictum.sha256 как asset к GitHub Release
```
