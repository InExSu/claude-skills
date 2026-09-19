---
name: pure-functions
license: MIT
description: Чистые функции на JavaScript/TypeScript. Формат ok/error, предусловия/постусловия/инварианты, запрещённые конструкции, композиция. Используй при написании любых функций на JS/TS.
---

# Pure Functions — JavaScript/TypeScript

## 7 аксиом

1. Функция — отображение входов → выходы
2. Детерминизм (один вход → один выход)
3. Без побочных эффектов
4. Одна ответственность
5. Предусловия защищают вход
6. Постусловия защищают выход
7. Инварианты защищают процесс

---

## Формат возврата

```ts
type Result<T> = { ok: true; value: T } | { ok: false; error: string };

// Успех
return { ok: true, value: m_result };

// Ошибка
return { ok: false, error: `fn_name: описание, got: ${m_x}` };
```

---

## Шаблон функции

```ts
function f_product_PriceGet(a_product: { s_sku: string; f_price: number }): Result<number> {
    // 1. ПРЕДУСЛОВИЯ
    if (a_product.f_price === undefined || a_product.f_price === null) {
        return { ok: false, error: 'f_product_PriceGet: missing f_price' };
    }
    if (typeof a_product.f_price !== 'number' || isNaN(a_product.f_price)) {
        return { ok: false, error: `f_product_PriceGet: not a number, got: ${a_product.f_price}` };
    }

    // 2. ТЕЛО
    const f_result = a_product.f_price;

    // 3. ПОСТУСЛОВИЯ
    if (f_result <= 0) {
        return { ok: false, error: `f_product_PriceGet: must be positive, got: ${f_result}` };
    }

    return { ok: true, value: f_result };
}
```

---

## Предусловия

```ts
function f_math_Divide(f_a: number, f_b: number): Result<number> {
    if (f_b === 0) {
        return { ok: false, error: 'f_math_Divide: f_b is zero' };
    }

    const f_result = f_a / f_b;

    if (!isFinite(f_result)) {
        return { ok: false, error: `f_math_Divide: not finite, got: ${f_result}` };
    }

    return { ok: true, value: f_result };
}
```

---

## Инварианты (в циклах)

```ts
function f_math_Sum(a_numbers: unknown[]): Result<number> {
    if (a_numbers.length === 0) {
        return { ok: false, error: 'f_math_Sum: empty array' };
    }

    let f_total = 0;

    for (let i = 0; i < a_numbers.length; i++) {
        const m_n = a_numbers[i];
        // инвариант: m_n — число
        if (typeof m_n !== 'number' || isNaN(m_n)) {
            return { ok: false, error: `f_math_Sum: non-numeric at ${i}, got: ${m_n}` };
        }
        f_total += m_n;
    }

    return { ok: true, value: f_total };
}
```

---

## Именование ошибок

```
// Плохо
'Invalid value'

// Хорошо
'f_product_PriceGet: f_price must be positive, got: -5'
'f_product_PriceGet: missing key f_price'
'a_price_CommandsBuild: item 3: f_product_PriceGet: missing key f_price'
```

---

## Композиция

```ts
function a_price_CommandBuild(a_item: Item): Result<PriceCommand> {
    const a_quantity = a_quantity_Validate(a_item.m_quantity);
    if (!a_quantity.ok) return a_quantity;

    const a_price = f_offer_PriceCalc(a_item.f_basePrice, a_quantity.value);
    if (!a_price.ok) return a_price;

    return {
        ok: true,
        value: {
            s_method: 'catalog.price.update',
            a_params: { i_id: a_item.i_priceId, a_fields: { f_price: a_price.value } },
        },
    };
}
```

---

## Работа с коллекциями

```ts
function a_price_CommandsBuild(a_items: Item[]): Result<PriceCommand[]> {
    if (a_items.length === 0) {
        return { ok: false, error: 'a_price_CommandsBuild: empty' };
    }

    const a_commands: PriceCommand[] = [];

    for (let i = 0; i < a_items.length; i++) {
        const a_command = a_price_CommandBuild(a_items[i]);
        if (!a_command.ok) {
            return { ok: false, error: `a_price_CommandsBuild: item ${i}: ${a_command.error}` };
        }
        a_commands.push(a_command.value);
    }

    return { ok: true, value: a_commands };
}
```

---

## Запрещённые конструкции

| Конструкция | Почему | Замена |
|-------------|--------|--------|
| `null` | Маскирует отсутствие | `{ ok: false, error }` |
| `?.` / `??` | Скрывает отсутствие | Явная проверка + `return` |
| `any` без проверок | Тип неизвестен | `typeof`, `Array.isArray()` |
| `throw new Error` | Разрывает поток | `return { ok: false, error }` |
| `console.log` | Побочный эффект | Убрать; логировать в оркестраторе |
| I/O, HTTP, fetch | Побочный эффект | Вынести в оркестратор |
| `Math.random()`, `Date.now()` | Нарушает детерминизм | Передавать как параметр |

---

## Чеклист

- [ ] Все параметры с префиксами: `i_`, `f_`, `s_`, `b_`, `a_`, `o_`, `m_`
- [ ] Функции: `{ReturnType}_{Object}_{Verb}`
- [ ] Ключи объектов с префиксами
- [ ] Нет `null`
- [ ] Нет `?.` / `??` внутри чистой функции
- [ ] Нет побочных эффектов
- [ ] Нет `Math.random()`, `Date.now()`
- [ ] Предусловия в начале
- [ ] Постусловия перед `return`
- [ ] Точные типы (интерфейсы, без `any`)
- [ ] Каждый `return` — `{ ok, value/error }`
- [ ] Ошибки: `fn: описание, got: ${value}`
- [ ] Одна функция = одно преобразование
- [ ] При композиции проверять `ok` на каждом шаге

---

## Главный принцип

> **Функция доказывает свою правильность через структуру.**

Прошла предусловия → детерминированное преобразование → прошла постусловия → без побочных эффектов → математически верна.
```