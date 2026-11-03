---
name: if-condition-refactor
license: MIT
description: >
  Refactor complex if/switch conditions into readable predicate functions. Lowers
  cyclomatic complexity, improves testability, removes inlined business logic from
  conditions. Use when conditions are nested > 2 levels, have 2+ operands without
  grouping, repeat the same check, or contain ternaries with nesting/function calls.
  «Рефакторинг условий», «упростить if», «предикатные функции», «почистить if-else»,
  «complex conditionals», «extract predicate». Do NOT extract simple self-documenting
  conditions. Do NOT change logical behavior — only structure.
allowed-tools: Read Write Edit
---

# Refactor Complex Conditionals to Predicate Functions

## Алгоритм действий

1.  **Идентификация:** Найди условия с антипаттернами:
    -   Вложенность > 2 уровней
    -   Выражения с 2+ операндами (`&&`, `||`)
    -   Повторяющиеся сложные проверки
    -   Тернарники с вложенностью или вызовами функций

2.  **Извлечение:** Для каждого сложного условия:
    -   Создай чистую функцию с булевым возвращаемым типом
    -   Перенеси всю логику внутрь, сохранив граничные случаи
    -   Добавь JSDoc/docstring с описанием бизнес-правила
    -   Размести рядом с использованием или в `predicates.*` / `guards.*`

3.  **Замена:**
    -   Замени оригинальное условие на вызов новой функции
    -   Если условие дублировалось — замени ВСЕ вхождения
    -   НЕ меняй логическое поведение, только структуру

4.  **Верификация:**
    -   Запусти существующие тесты для подтверждения эквивалентности
    -   Убедись, что функция чистая (без побочных эффектов)
    -   Проверь сохранение type-safety и null-checks

## Ограничения

-   НИКОГДА не изменяй логическое поведение условия
-   Не извлекай простые и самодокументируемые условия
-   При сомнениях спроси пользователя перед рефакторингом критической логики
-   Предпочитай композицию глубокой вложенности внутри предиката

## Примеры

### Before: вложенное условие с бизнес-логикой

```javascript
function processOrder(order) {
  if (order.status === 'pending' && order.total > 0 &&
      order.items.length > 0 && !order.isCancelled) {
    if (order.user.verified && order.paymentMethod === 'card') {
      chargeCard(order);
    } else if (order.user.verified && order.paymentMethod === 'cash') {
      queueCashProcessing(order);
    }
  }
}
```

### After: предикатные функции

```javascript
function f_Order_Is_Processable(order) {
  return order.status === 'pending'
    && order.total > 0
    && order.items.length > 0
    && !order.isCancelled;
}

function f_User_Can_Pay_By_Card(order) {
  return order.user.verified && order.paymentMethod === 'card';
}

function f_User_Can_Pay_By_Cash(order) {
  return order.user.verified && order.paymentMethod === 'cash';
}

function processOrder(order) {
  if (!f_Order_Is_Processable(order)) return;

  if (f_User_Can_Pay_By_Card(order)) {
    chargeCard(order);
  } else if (f_User_Can_Pay_By_Cash(order)) {
    queueCashProcessing(order);
  }
}
```

### Before: тернарник с вызовами функций

```javascript
const label = user && user.profile && user.profile.name
  ? user.profile.name
  : (user && user.guest ? 'Guest' : 'Unknown');
```

### After: именованный предикат

```javascript
function f_User_Display_Name(user) {
  if (user?.profile?.name) return user.profile.name;
  if (user?.guest) return 'Guest';
  return 'Unknown';
}

const label = f_User_Display_Name(user);
```
