---
name: noosphere
license: MIT
description: >
  Use when designing global state management for an application — creating
  a single shared state object/store (Noosphere State, `ns`) that acts as
  the single source of truth. Any language (JS, PHP, Python, Go). Trigger on
  requests like "спроектируй архитектуру состояния", "нужен единый источник
  истины", "глобальное состояние", "ns pattern", or when refactoring scattered
  state into one place. Do NOT apply to pure functions that only operate on
  their own arguments — they must stay independent of `ns`.
---

# Noosphere State (ns) — universal

Архитектура: единый источник истины — объект/массив `ns`, хранящий всё
глобальное состояние системы. Принципы не зависят от языка.

## Правила

1. `ns` инициализируется один раз, на старте программы.
2. Читать и изменять `ns` может любая функция, которой это нужно, —
   через явную передачу `ns` аргументом (по ссылке) или через замыкание.
3. Чистые функции (pure functions), работающие только со своими аргументами,
   не должны взаимодействовать с `ns`.
4. Изменения `ns` должны быть явными и предсказуемыми — никаких скрытых
   побочных эффектов внутри случайных функций.

## Примеры

JS:

```js
const ns = { user: null, cart: [], status: 'idle' };

function setUser(ns, user) {
  ns.user = user;
}
```

PHP:

```php
$ns = ['user' => null, 'cart' => [], 'status' => 'idle'];

function setUser(array &$ns, ?array $user): void {
    $ns['user'] = $user;
}
```

Python:

```python
ns = {"user": None, "cart": [], "status": "idle"}

def set_user(ns, user):
    ns["user"] = user
```

## Примечания

- `null` допустим в состоянии как маркер «ещё не установлено»; в кодовых путях
  предпочитайте типизированные пустые значения (`''`, `0`, `[]`, `false`).
- В этом проекте рекомендуемый способ мутаций общего `ns` — конвейер RWD
  (см. скилл `rwd-chain`): цепочка шагов с профилированием и остановкой по ошибке.
