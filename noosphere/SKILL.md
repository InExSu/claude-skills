---
name: noosphere
license: MIT
description: >
  Use when designing global state management — creating a single shared state object/store
  (Noosphere State, `ns`) as the single source of truth. Any language (JS, PHP, Python, Go).
  Trigger on "design state architecture", "single source of truth", «спроектируй архитектуру
  состояния», «нужен единый источник истины», «глобальное состояние», "ns pattern", or when
  refactoring scattered state into one place. Do NOT apply to pure functions that only
  operate on their own arguments — they must stay independent of `ns`.
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

- `null` допустим в состоянии `ns` как маркер «ещё не установлено» — это состояние, а не возвращаемое значение. В чистых функциях (см. скилл `pure-functions`) `null` запрещён; используйте типизированные пустые значения (`''`, `0`, `[]`, `false`). В конвейере `rwd-chain` поле `o_Error = null` — единственное исключение для доменных данных.
- В этом проекте рекомендуемый способ мутаций общего `ns` — конвейер RWD (см. скилл `rwd-chain`): цепочка шагов с профилированием и остановкой по ошибке.

## Before / After: scattered state → unified ns

### Before — state scattered across globals

```javascript
let currentUser = null;
let cartItems = [];
let appStatus = 'idle';
let lastError = null;

function login(user) {
  currentUser = user;
  appStatus = 'logged_in';
}

function addToCart(item) {
  cartItems.push(item);
}

function checkout() {
  if (!currentUser) { lastError = 'not logged in'; return false; }
  if (cartItems.length === 0) { lastError = 'empty cart'; return false; }
  // ... process ...
  return true;
}
```

### After — single `ns` object

```javascript
const ns = {
  user: null,
  cart: [],
  status: 'idle',
  error: null,
};

function setUser(ns, user) {
  ns.user = user;
  ns.status = 'logged_in';
}

function addToCart(ns, item) {
  ns.cart.push(item);
}

function checkout(ns) {
  if (!ns.user) { ns.error = 'not logged in'; return false; }
  if (ns.cart.length === 0) { ns.error = 'empty cart'; return false; }
  // ... process ...
  return true;
}
```
