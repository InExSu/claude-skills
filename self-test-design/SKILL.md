---
name: self-test-design
license: MIT
description: >
  Design and build software like reliable hardware — with testability engineered in from
  the start (Design-For-Test, BIST/POST, TestPort contract, state-transition tables), not
  bolted on afterward. Use when architecting programs, modules, games, services, or APIs;
  when discussing "self-testing", "built-in test", «самотестирование», reliability, QA
  automation, flaky behavior, or state-machine bugs. The golden rule is universal: verify
  the absence of unwanted behavior, not just the presence of wanted behavior.
  «тестируемость архитектуры», «Design-For-Test», «TestPort», «встроенное самотестирование».
---

# Self-Test Design (программы как устройства)

## Философия

Надёжные устройства не тестируют «снаружи» через дырочку в корпусе — тестируемость встроена в схему: BIST, POST, JTAG, коды неисправностей, watchdog. Тест — не последний этап, а часть архитектуры.

Применяй к программам:
- Модуль должен **сам** говорить «я в порядке» или «вот код неисправности»
- Тестируемость — требование к архитектуре с первого дня

---

## Золотое правило тестирования

> **Проверяй не только наличие желаемого поведения, но и отсутствие нежелательного.**

**Следствия:**

1. **Проверяй весь снимок состояния**, а не только ожидаемое поле
2. **Тестируй переходы между состояниями** — баги живут там, а не в стационарных состояниях
3. **Используй state transition table** — для пары (состояние, событие) фиксируй ожидаемые (новое состояние, побочные эффекты, вывод)

---

## Архитектурный паттерн: TestPort

Единый контракт для всех модулей:

```
TestPort {
  markReady()                     // модуль прошёл инициализацию
  heartbeat()                     // "я жив" — периодически
  reportFault(code, message, ctx) // стандартизированная ошибка
  assertGolden(name, actual, expected) // сверка с эталоном
  assertStateTransition(event, before, after) // сверка перехода
  getStatus() -> { stage, faultCount }
}
```

---

## Коды неисправностей

Числовые коды вместо строк (для агрегации):

| Диапазон | Категория | Примеры |
|----------|-----------|---------|
| 1xx | Контракт/интерфейс | зависимость не найдена, метод отсутствует |
| 2xx | Рантайм | исключение, rejected promise |
| 3xx | Вывод | пустой результат, не отрисовалось |
| 4xx | Логика | детерминированный расчёт неверен |
| 5xx | Время | таймаут, зависание, дедлок |

---

## Тестовые тиры (от дешёвого к дорогому)

1. **Статика** (линтер, типы) — секунды
2. **Контракт** — наличие файлов, полей, точек входа
3. **POST** — модуль запускается, `markReady()`, heartbeat
4. **State-transition / property-based** — таблица переходов или fuzz-тест
5. **Полевая телеметрия / canary** — реальные пользователи, малый % трафика

---

## Паттерн «guard + счётчик + z-срезы»

Для игр и симуляций, где важна проходимость/безопасность в пространстве:

1. **Срез, а не всё окно.** Проверяй инвариант на каждом поперечном срезе (z-кластере) отдельно. Суммировать все препятствия в окне 45 м — значит складывать то, что игрок проходит в разное время, и получать ложные тупики.
2. **Планирование по срезу.** При порождении препятствия смотри занятость именно его среза и оставляй хотя бы одну свободную полосу. Учитывай не только «свои» объекты, но и обычный поток.
3. **Guard как страховка, а не как решение.** Предохранитель (осадить, раздвинуть) обязан существовать, но его срабатывания считаются и выводятся в диагностику. Ноль срабатываний в штатной игре — критерий приёмки; рост счётчика — сигнал о редком сценарии, для которого нужен новый детерминированный тест.
4. **Счётчик — часть контракта.** `guardHits`, `blocked`, `formed` должны быть доступны через BIST-хук, а не только в логах.
5. **Отрицательный контроль.** Подложи заведомо непроходимый срез и докажи, что guard срабатывает и восстанавливает инвариант.

## BIST-хуки для браузерных проб

Игру нельзя проверять «снаружи» только по canvas. Добавляй штатные хуки в `window.__GAME` (или аналог):

```
getState()        // экран, очки, скорость, дистанция
crashState()      // срезы, проходимые полосы, guardHits, события
audioState()      // состояние AudioContext, gain, hidden, allowed
mirrorState()     // направления камер, видимость, отсутствие убранных узлов
toneProbe(...)    // детерминированный вызов сигнала для антидребезга
```

Правила:

1. Хук возвращает **примитивы и массивы**, а не живые объекты Three.js.
2. Хук не меняет состояние (кроме явных `*Probe`).
3. Хук доступен всегда, но тяжёлый журнал — только под `?debug=1`.
4. Проба читает хук и проверяет числа; скриншот — дополнение.
5. У каждого хука есть отрицательный сценарий: убранный узел отсутствует, скрытая вкладка даёт gain 0, непроходимый срез даёт `blocked > 0` до срабатывания guard.

## Чек-лист при старте

- [ ] Определён `TestPort` для класса модулей
- [ ] Есть явная стадия "boot" с `markReady()`
- [ ] Есть heartbeat/watchdog для долгих процессов
- [ ] Заведены fault-коды (диапазоны)
- [ ] Есть golden vectors для детерминированной логики
- [ ] Составлена таблица переходов состояний
- [ ] Тестовый код отделён от продакшена (флаг сборки)
- [ ] Каждый тест проверяет весь снимок, а не одно поле
- [ ] Инвариант проверяется по срезам, а не по всему окну сразу
- [ ] Guard имеет счётчик и отрицательный контроль
- [ ] BIST-хуки отдают примитивы и не мутируют состояние

---

## Пример: модуль корзины с TestPort (JavaScript)

```javascript
// cart.js
class Cart {
  constructor() {
    this.items = [];
    this.status = 'idle';
    this.faultCode = 0;
    this.ready = false;
  }

  // --- TestPort ---
  markReady() { this.ready = true; this.status = 'ready'; }
  heartbeat() { return this.ready && this.faultCode === 0; }
  reportFault(code, msg) { this.faultCode = code; this.status = 'fault'; }
  getStatus() { return { stage: this.status, faultCount: this.faultCode }; }

  // --- Business logic ---
  addItem(item) {
    if (!this.ready) { this.reportFault(101, 'not ready'); return; }
    if (!item || !item.id) { this.reportFault(401, 'invalid item'); return; }
    this.items.push(item);
  }

  removeItem(itemId) {
    const before = this.items.length;
    this.items = this.items.filter(i => i.id !== itemId);
    if (this.items.length === before) { this.reportFault(301, 'item not found'); }
  }
}

// cart.test.js
function testCartTransitions() {
  const cart = new Cart();
  // POST: module boots
  cart.markReady();
  assert(cart.getStatus().stage === 'ready');

  // Golden vector: add item, verify full snapshot
  cart.addItem({ id: 'A1', name: 'Apple', qty: 2 });
  assertDeepEqual(cart, {
    items: [{ id: 'A1', name: 'Apple', qty: 2 }],
    status: 'ready', faultCode: 0, ready: true,
  });

  // State transition: remove → verify absence of unwanted side effects
  const snapshot = JSON.stringify(cart);
  cart.removeItem('A1');
  assert(cart.items.length === 0);
  assert(cart.faultCode === 0, 'faultCode should be 0 after successful removal');
  assert(cart.status === 'ready', 'status should remain ready');

  // Negative test: invalid item triggers fault, no silent corruption
  cart.addItem(null);
  assert(cart.faultCode === 401);
  assert(cart.items.length === 0, 'invalid item must not be added');
}
```