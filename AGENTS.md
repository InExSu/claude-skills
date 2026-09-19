# AGENTS.md — как читать этот репозиторий из агента

Этот репозиторий — набор скиллов в формате открытого стандарта [Agent Skills](https://agentskills.io)
([спецификация](https://github.com/agentskills/agentskills), тег `MIT`).

## Что здесь устроено

- Каждый скилл — папка `<имя-скилла>/SKILL.md`. Имя во frontmatter (`name`) всегда
  совпадает с именем папки; формат имён: строчные буквы, цифры, одиночные дефисы.
- Перед использованием скилла прочитай из его `SKILL.md`:
  - `description` — когда применять и, что не менее важно, когда **не** применять;
  - `allowed-tools` — только в `ru-psychoagent` и `if-condition-refactor`; это поле
    в стандарте экспериментальное, поддерживается не всеми агентами, и его содержимое
    влияет только на предодобрение инструментов, а не на доступность скилла;
  - `license` — во всех скиллах `MIT`.
- Не предполагай, что все инструменты/расширения твоего агента доступны другим
  агентам: этот репозиторий сознательно избегает агент-специфичных полей
  (`disable-model-invocation`, `context: fork`, хуки). Единственное исключение —
  `mcp__*` в `allowed-tools` у `ru-psychoagent`, имеющее смысл только в агентах
  с MCP-поддержкой и таким синтаксисом; игнорируй его, если твой агент его не понимает.
- Относительные пути внутри одного скилла всегда ведут внутрь его же папки
  (исключение — `drakonhub` с подпапками `reference/`, `scripts/`, `templates/`).
  Копирование папки скилла целиком ничего не ломает.

## Как подключиться

- Отдай агенту файл `SKILL.md` (или папку скилла целиком) на чтение, либо скопируй
  папку в каталог скиллов твоего агента. Проверочные точки из каталога:
  `README.md` / `README.ru.md` (EN/RU).
- Для `drakonhub` скрипты требуют только Python 3 и стандартную библиотеку
  (`json`, `re`, `sys`, `textwrap`); сетевых запросов нет. Проверки:
  `python3 scripts/drakon_tool.py check templates/choice-and-loop.drakon`,
  `python3 scripts/drakon_dsl.py roundtrip templates/minimal.drakon`,
  `python3 scripts/drakon_render.py svg templates/silhouette.drakon /tmp/out.svg`.

## Каталог (кратко)

Testing: `tdd-bugfix`, `quality-tests`, `self-test-design`. Architecture:
`pure-functions`, `if-condition-refactor`, `noosphere`,
`state-machine-if-improves-understanding`, `spaghetti-rwd`. Naming: `hungarian-notation`
(opt-in), `constant-naming-convention`, `token-economy`. Pipelines: `rwd-chain`.
Agents: `ru-psychoagent`. Diagrams: `drakonhub` (DSL → JSON-диаграмма ДРАКОН,
просмотр на https://drakonhub.com).
