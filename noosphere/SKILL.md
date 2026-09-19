---
name: noosphere
license: MIT
description: >
  Use when designing global state management for an application — creating
  a single shared state object/store (Noosphere State, `ns`) that acts as
  the single source of truth. Trigger on requests like "спроектируй
  архитектуру состояния", "нужен единый источник истины", "глобальное
  состояние", "ns pattern", or when refactoring scattered state into one
  place. Do NOT apply to pure functions that only operate on their own
  arguments — they must stay independent of `ns`.
---

# Noosphere State (ns)

Архитектура: единый источник истины — объект/массив `ns`, хранящий всё
глобальное состояние системы.

## Правила

1. `ns` инициализируется один раз, на старте программы.
2. Читать и изменять `ns` может любая функция, которой это нужно —
   через явную передачу `ns` аргументом или через замыкание.
3. Чистые функции (pure functions), работающие только со своими
   аргументами, не должны взаимодействовать с `ns`.
4. Изменения `ns` должны быть явными и предсказуемыми — никаких
   скрытых побочных эффектов внутри случайных функций.

## Пример (JS)

```js
const ns = {
  user: null,
  cart: [],
  status: "idle",
};

function setUser(ns, user) {
  ns.user = user;
}
```
