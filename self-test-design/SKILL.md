---
name: self-test-design
description: Design and build software like reliable hardware devices — with testability engineered in from the start (Design-For-Test), not bolted on afterward. Apply when architecting programs, modules, games, services, or APIs; when discussing "self-testing", "built-in test", "самотестирование", reliability, QA automation, flaky behavior, or state-machine bugs. Also applies to any test strategy discussion — the golden rule (verify absence of unwanted behavior, not just presence of wanted behavior) is universal.
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

## Чек-лист при старте

- [ ] Определён `TestPort` для класса модулей
- [ ] Есть явная стадия "boot" с `markReady()`
- [ ] Есть heartbeat/watchdog для долгих процессов
- [ ] Заведены fault-коды (диапазоны)
- [ ] Есть golden vectors для детерминированной логики
- [ ] Составлена таблица переходов состояний
- [ ] Тестовый код отделён от продакшена (флаг сборки)
- [ ] Каждый тест проверяет весь снимок, а не одно поле
```