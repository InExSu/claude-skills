---
name: orca-ade
license: MIT
description: >
  Использование Orca ADE (Agent Development Environment) из агента через CLI `orca`:
  репозитории, worktree, терминалы, субагенты (TUI-агенты в первом терминале), их запуск,
  ожидание готовности, чтение вывода, докрутка задач, закрытие и уборка. Применяй, когда
  пользователь просит «используй субагентов», «сделай через Orca», «запусти воркера в
  отдельном worktree», «handoff», «передай другому агенту», или когда нужно распараллелить
  независимые проверки/прогоны в изолированных чекаутах.
---

# Orca ADE — агентная работа через CLI

## Когда применять

- Нужны субагенты: отдельные TUI-агенты в своих worktree с задачей и контролем результата.
- Нужна изоляция: прогон тестов/скриптов в отдельном чекауте, чтобы не трогать рабочую копию.
- Нужен handoff: передать работу другому агенту/воркспейсу и не ждать её сам.
- Нужны терминалы под управлением: долгие команды с чтением вывода после завершения.

## 0. Разрешить исполняемый файл и загрузить актуальный гайд

```bash
# Исполняемый: ORCA_CLI_COMMAND из окружения > orca-dev (dev-сборка) > orca.
# Не запускай bare `orca` на Linux вне терминалов Orca — там это скринридер GNOME.
orca --version
orca skills get orca-cli --json   # версия-совместимый гайд; флаги сверяй с `orca <cmd> --help`
```

## 1. Репозиторий: добавить проект, найти id

```bash
orca repo add --path /abs/path/to/repo --json     # идемпотентно; вернёт repo.id
orca repo list --json
```

`repo.id` нужен во всех командах ниже. Путь — абсолютный.

## 2. Worktree: чекаут под задачу

```bash
# Создать чекаут от базовой ветки репо (для субагентов — вместе с агентом, см. §4):
orca worktree create --repo id:<repoId> --name <task-name> --json

# Список, текущий, процессы, удалить:
orca worktree list --repo id:<repoId> --json
orca worktree current --json
orca worktree ps --json
orca worktree rm --worktree id:<repoId>::<worktreePath> --force --json
```

Адрес worktree — всегда полный `<repoId>::<worktreePath>` (из `worktree.id`).
Сокращать до `<repoId>` нельзя. Селекторы: `id:...`, `path:...`, `name:...`, `branch:...`, `active`.

Заметки:
- `--setup skip` — не выполнять repo setup-хуки при создании.
- Пробные/временные worktree удаляй сразу (`worktree rm --force`), чтобы не засорять список.
- Ветку пробы создают вида `InExSu/<name>` — она локальная, `worktree rm` убирает её вместе с чекаутом.

## 3. Терминалы: запуск, чтение, закрытие

```bash
orca terminal list --worktree id:<repoId>::<worktreePath> --json
orca terminal read --terminal <handle> --json              # вывод терминала (с cursor для докрутки)
orca terminal send --terminal <handle> --text "cmd" --enter --json
orca terminal wait --terminal <handle> --for exit --timeout-ms 60000 --json
orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 120000 --json
orca terminal close --terminal <handle> --json
```

Правила:
- `--terminal` можно опускать — тогда берётся активный терминал текущего worktree.
- Долгие команды лучше сразу писать так, чтобы вывод остался: `cmd > /tmp/out.log 2>&1; echo exit=$?`.
- `terminal close` останавливает PTY; для закрытия всех терминалов worktree — `--worktree ... --all`.
- Вывод read идёт и в `text` (JSON), и в plain-режиме: для grep-фильтров используй plain `orca terminal read`.

## 4. Субагенты: какой TUI-агент реально доступен

Критический урок этого проекта: **Orca разрешает агента, но исполняемого файла может не быть в PATH** —
сессия «стартует», а в терминале падает `command not found: <agent>`. Всегда проверяй до запуска:

```bash
# 1) Есть ли бинарник:
which claude codex gemini omp amp droid 2>/dev/null

# 2) Разрешён ли агент в Orca — пробным create (см. §5), с немедленной уборкой при отказе.
```

Запуск субагента в новом worktree (агент получает первый терминал — отдельный `terminal create`
для того же агента НЕ делать):

```bash
orca worktree create \
  --repo id:<repoId> --name <task-name> --agent <agentId> --setup skip \
  --prompt "<подробный бриф задачи: шаги, ограничения, что доложить>" \
  --json
```

Ответ: `result.worktree.id` и `result.agentTerminalHandle` (в старых версиях `result.startupTerminal.handle`).

Запуск субагента в текущем чекауте (без нового worktree):

```bash
orca terminal create --worktree active --command "<agent>" --json
```

## 5. Контроль субагента: ожидание готовности и чтение результата

```bash
# Дождаться, пока TUI агента загрузится, прежде чем слать ввод:
orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 120000 --json
# Читай `result.satisfied`, а не факт печати: таймаут всё равно печатает JSON.

orca terminal read --terminal <handle> 2>/dev/null | tail -40
```

- Промпт, отправленный в ещё не готовый TUI, теряется. Сначала `wait tui-idle`, потом `send`.
- Если после старта в терминале `command not found: <agent>` — агент не установлен. Закрой
  терминал, удали worktree и перезапусти на другом агенте (§7). Не ретраи тот же агент.
- Для задач с длительными шагами (тесты, анализы) жди циклом: `wait tui-idle` → read → если
  агент ещё работает, подожди и повтори.

## 6. Бриф субагента (проверено на этой задаче)

Хороший бриф — это протокол, а не описание. В него входят:

1. Роль и контекст: репо, коммит/HEAD, что уже сделано.
2. Правила безопасности: «файлы не менять», «никаких --update», «внешние системы не трогать» —
   прямо и категорично, отдельной строкой.
3. Пронумерованные шаги с точными командами и ожидаемым результатом каждого.
4. Какой результат доложить: «exit-код каждой команды», «только новые замечания, не старые»,
   «финальная строка строго ВЕРДИКТ: ЗЕЛЕНО/КРАСНО».
5. Подводные камни окружения (например, «файл X вне git — скопируй командой cp из пути Y»).

Финальная строка с фиксированным вердиктом упрощает автоматический парсинг ответа.

## 7. Уборка: закрыть терминалы, удалить worktree

```bash
orca terminal close --terminal <handle> --json
orca worktree rm --worktree id:<repoId>::<worktreePath> --force --json
```

Массовое закрытие `--all` может вернуть ошибку, если PTY не подтвердились — не считается
успехом и не ретраится на другом хосте. Закрывай по одному `--terminal`.

## 8. Сообщения и координация (если нужна переписка воркеров)

Для обмена сообщениями, задач-очередей и координатор-циклов — скилл `orchestration`
(`orca orchestration ...`). Для простых параллельных задач достаточно §4–§5.

## 9. Мини-чеклист перед сдачей

- [ ] Репо добавлен, `repoId` записан
- [ ] Бинарник агента проверен через `which` ДО create
- [ ] Промпт отправлен только после `wait tui-idle` → `satisfied: true`
- [ ] Результат прочитан и доложен пользователю
- [ ] Терминалы закрыты, временные worktree удалены
