# Вспомогательные форматы: `.seq` и `.sm`

ДРАКОН — основной формат скилла: он описывает поток управления и проверяется
жёстко (`check` + `roundtrip` + прогон движком). Но две вещи в него не ложатся
по своей природе:

- **линии жизни** — порядок сообщений между участниками во времени
  (протоколы, API, OAuth). ДРАКОН рисует управляющий граф, а не обмен
  репликами между сущностями;
- **состояния как сущности** — жизненный цикл объекта, где важны сами
  состояния и переходы между ними, а не последовательность шагов.

Для них — два вспомогательных текстовых формата. Их цель — **Mermaid**
(`sequenceDiagram` и `stateDiagram-v2`), который GitHub рендерит прямо
в Markdown. У них нет промежуточного JSON и `roundtrip`: `check` проверяет
структуру, `mermaid` выдаёт результат.

## `.seq` — диаграмма последовательности

```
# OAuth 2.0: обмен кода на токен
participant User
participant Browser
participant AuthServer

User -> Browser: открыть приложение
Browser -> AuthServer: GET /authorize?code_challenge=...
AuthServer --> Browser: форма входа
alt код выдан
  AuthServer --> Browser: 302 redirect_uri?code=...
  Browser -> AuthServer: POST /token + code_verifier
else доступ запрещён
  AuthServer --> Browser: 403 access_denied
end
loop обновление токена
  Browser -> AuthServer: POST /token + refresh_token
end
note over AuthServer: код живёт 10 минут
```

Синтаксис:

| Конструкция | Mermaid |
|---|---|
| `participant A` / `participant A as Alias` | `participant A as Alias` |
| `A -> B: текст` | `A->>B: текст` |
| `A --> B: текст` | `A-->>B: текст` (пунктир) |
| `alt условие` … `else` … `end` | `alt` / `else` / `end` |
| `opt` / `loop` / `par` / `critical` / `break` … `end` | одноимённо |
| `note over A: текст` / `note right of A:` / `note left of A:` | `Note over/right of/left of A: текст` |

Правила `check`:

- участник объявлен (`participant`) до первого упоминания в сообщении
  или примечании;
- у блока `alt` обязателен `else` (требование Mermaid);
- блоки закрыты `end`, `else` — только внутри `alt`;
- нет дублей `participant`; есть хотя бы одно сообщение и один участник.

## `.sm` — машина состояний

```
# Жизненный цикл заказа
[*] --> Created: создать заказ
Created --> Paid: оплата получена
Created --> Cancelled: отмена до оплаты
Paid --> Shipped: отгрузить
Shipped --> Delivered: доставка
Delivered --> [*]
Cancelled --> [*]
```

Синтаксис:

| Конструкция | Mermaid |
|---|---|
| `[*] --> X` | начальное состояние |
| `X --> [*]` | конечное состояние |
| `A --> B: текст` | переход с подписью |
| `state X {` … `}` | композитное состояние |
| `state "Читаемое имя" as X` | псевдоним состояния |

Правила `check`:

- есть начальное состояние `[*] -->`;
- каждая цель перехода объявлена (участвует в переходах или как `state`);
- `state { }` закрыт;
- есть хотя бы один переход.

## Когда что использовать

| Задача | Формат |
|---|---|
| Алгоритм, инструкция, runbook, поток управления | `.drakon` |
| Разбор темы, структура документа | `.graf` |
| Протокол, API, обмен сообщениями во времени | `.seq` |
| Жизненный цикл, состояния и переходы | `.sm` |
| Роли, события, таймеры процесса | не сюда (BPMN) |

## Команды

```bash
python3 scripts/drakon_tool.py check  flow.seq
python3 scripts/drakon_tool.py read   flow.seq
python3 scripts/drakon_render.py mermaid flow.seq out.mmd

python3 scripts/drakon_tool.py check  order.sm
python3 scripts/drakon_tool.py read   order.sm
python3 scripts/drakon_render.py mermaid order.sm out.mmd
```

Примеры — `templates/oauth2-flow.seq`, `templates/order-state.sm`.
