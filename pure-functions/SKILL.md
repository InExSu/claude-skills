---
name: pure-functions
description: Правила написания чистых функций на PHP и JavaScript/TypeScript. Используй этот скилл всегда, когда пишешь или рефакторишь функции на PHP или JS/TS — при валидации данных, обработке коллекций, композиции функций, или когда нужно избежать побочных эффектов. Включает шаблон с предусловиями/постусловиями/инвариантами, формат возврата ok/error, запрещённые конструкции и чеклист для обоих языков.
---

# Скилл: Чистые функции — PHP и JavaScript

## Аксиомы

1. **Функция — это отображение входов в выходы**
2. **Один вход → один выход** (детерминизм)
3. **Никаких побочных эффектов**
4. **Одна функция — одна ответственность**
5. **Предусловия защищают вход**
6. **Постусловия защищают выход**
7. **Инварианты защищают процесс**

---

## Возврат результата

Единый формат для обоих языков: `{ ok: true, value }` или `{ ok: false, error }`.

**PHP**
```php
return ['ok' => true, 'value' => $m_result];
return ['ok' => false, 'error' => 'fn_name: описание, got: ' . $m_x];
```

**JS/TS**
```ts
return { ok: true, value: m_result };
return { ok: false, error: `fn_name: описание, got: ${m_x}` };
```

В TypeScript — типизировать через дискриминированный union:
```ts
type Result<T> = { ok: true; value: T } | { ok: false; error: string };
```

---

## Шаблон функции

**PHP**
```php
/**
 * @param array{s_sku: string, f_price: float} $a_product
 * @return array{ok: true, value: float}|array{ok: false, error: string}
 */
function f_product_PriceGet(array $a_product): array
{
    // 1. ПРЕДУСЛОВИЯ
    if (!isset($a_product['f_price'])) {
        return ['ok' => false, 'error' => 'f_product_PriceGet: missing key f_price'];
    }
    if (!is_float($a_product['f_price'])) {
        return ['ok' => false, 'error' => "f_product_PriceGet: f_price not float, got: {$a_product['f_price']}"];
    }

    // 2. ТЕЛО
    $f_result = $a_product['f_price'];

    // 3. ПОСТУСЛОВИЯ
    if ($f_result <= 0.0) {
        return ['ok' => false, 'error' => "f_product_PriceGet: f_price must be positive, got: {$f_result}"];
    }

    return ['ok' => true, 'value' => $f_result];
}
```

**JS/TS**
```ts
function f_product_PriceGet(a_product: { s_sku: string; f_price: number }): Result<number> {
    // 1. ПРЕДУСЛОВИЯ
    if (a_product.f_price === undefined || a_product.f_price === null) {
        return { ok: false, error: 'f_product_PriceGet: missing f_price' };
    }
    if (typeof a_product.f_price !== 'number' || isNaN(a_product.f_price)) {
        return { ok: false, error: `f_product_PriceGet: f_price not a number, got: ${a_product.f_price}` };
    }

    // 2. ТЕЛО
    const f_result = a_product.f_price;

    // 3. ПОСТУСЛОВИЯ
    if (f_result <= 0) {
        return { ok: false, error: `f_product_PriceGet: f_price must be positive, got: ${f_result}` };
    }

    return { ok: true, value: f_result };
}
```

---

## Предусловия (защита входа)

Проверяют входные данные до любых вычислений. Если вход невалиден — сразу `return`.

**PHP**
```php
function f_math_Divide(float $f_a, float $f_b): array
{
    if ($f_b === 0.0) {
        return ['ok' => false, 'error' => 'f_math_Divide: f_b is zero'];
    }

    $f_result = $f_a / $f_b;

    if (!is_finite($f_result)) {
        return ['ok' => false, 'error' => "f_math_Divide: result is not finite, got: {$f_result}"];
    }

    return ['ok' => true, 'value' => $f_result];
}
```

**JS/TS**
```ts
function f_math_Divide(f_a: number, f_b: number): Result<number> {
    if (f_b === 0) {
        return { ok: false, error: 'f_math_Divide: f_b is zero' };
    }

    const f_result = f_a / f_b;

    if (!isFinite(f_result)) {
        return { ok: false, error: `f_math_Divide: result is not finite, got: ${f_result}` };
    }

    return { ok: true, value: f_result };
}
```

---

## Инварианты (защита процесса)

Утверждение, истинное на каждой итерации цикла.

**PHP**
```php
function f_math_Sum(array $a_numbers): array
{
    if ($a_numbers === []) {
        return ['ok' => false, 'error' => 'f_math_Sum: a_numbers is empty'];
    }

    $f_total = 0.0;

    foreach ($a_numbers as $i => $m_n) {
        // инвариант: $m_n — числовое значение
        if (!is_numeric($m_n)) {
            return ['ok' => false, 'error' => "f_math_Sum: non-numeric at index {$i}, got: {$m_n}"];
        }
        $f_total += (float) $m_n;
    }

    return ['ok' => true, 'value' => $f_total];
}
```

**JS/TS**
```ts
function f_math_Sum(a_numbers: unknown[]): Result<number> {
    if (a_numbers.length === 0) {
        return { ok: false, error: 'f_math_Sum: a_numbers is empty' };
    }

    let f_total = 0;

    for (let i = 0; i < a_numbers.length; i++) {
        const m_n = a_numbers[i];
        // инвариант: m_n — числовое значение
        if (typeof m_n !== 'number' || isNaN(m_n)) {
            return { ok: false, error: `f_math_Sum: non-numeric at index ${i}, got: ${m_n}` };
        }
        f_total += m_n;
    }

    return { ok: true, value: f_total };
}
```

---

## Именование ошибок

Формат: `function_name: описание проблемы, got: {фактическое значение}`

```
// Плохо — нет контекста
'Invalid value'

// Плохо — нет имени функции
'Price must be positive'

// Хорошо
'f_product_PriceGet: f_price must be positive, got: -5'

// Хорошо — без got, когда значение не нужно
'f_product_PriceGet: missing key f_price'

// Хорошо — при всплытии ошибки из вложенной функции
'a_price_CommandsBuild: item 3: f_product_PriceGet: missing key f_price'
```

---

## Композиция функций

Результат каждой функции проверяется перед передачей в следующую.

**PHP**
```php
/**
 * @param array{s_sku: string, m_quantity: mixed, f_base_price: float, i_price_id: int} $a_item
 * @return array{ok: true, value: array{s_method: string, a_params: array}}|array{ok: false, error: string}
 */
function a_price_CommandBuild(array $a_item): array
{
    $a_quantity = a_quantity_Validate($a_item['m_quantity'] ?? null);
    if (!$a_quantity['ok']) {
        return $a_quantity;
    }

    $a_price = f_offer_PriceCalc($a_item['f_base_price'], $a_quantity['value']);
    if (!$a_price['ok']) {
        return $a_price;
    }

    return [
        'ok'    => true,
        'value' => [
            's_method' => 'catalog.price.update',
            'a_params' => [
                'i_id'    => $a_item['i_price_id'],
                'a_fields' => ['f_price' => $a_price['value']],
            ],
        ],
    ];
}
```

**JS/TS**
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

Ошибка на любом элементе — немедленный возврат с индексом.

**PHP**
```php
/**
 * @param array<int, array{s_sku: string, m_quantity: mixed, f_base_price: float}> $a_items
 * @return array{ok: true, value: array<int, array>}|array{ok: false, error: string}
 */
function a_price_CommandsBuild(array $a_items): array
{
    if ($a_items === []) {
        return ['ok' => false, 'error' => 'a_price_CommandsBuild: a_items is empty'];
    }

    $a_commands = [];

    foreach ($a_items as $i => $a_item) {
        $a_command = a_price_CommandBuild($a_item);
        if (!$a_command['ok']) {
            return ['ok' => false, 'error' => "a_price_CommandsBuild: item {$i}: {$a_command['error']}"];
        }
        $a_commands[] = $a_command['value'];
    }

    return ['ok' => true, 'value' => $a_commands];
}
```

**JS/TS**
```ts
function a_price_CommandsBuild(a_items: Item[]): Result<PriceCommand[]> {
    if (a_items.length === 0) {
        return { ok: false, error: 'a_price_CommandsBuild: a_items is empty' };
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

| Конструкция | Язык | Почему | Замена |
|-------------|------|--------|--------|
| `null` | PHP, JS | Маскирует отсутствие значения, приводит к `null`-propagation | `{ ok: true, value }` / `{ ok: false, error }` |
| `??` / `?? ''` / `?? []` | PHP | Скрывает отсутствие значения; `?? ''` и `?? []` маскируют ошибки пустыми строками/массивами | `isset()` + явный `return` с ошибкой |
| `?.` / `??` | JS | Скрывает отсутствие значения | Явная проверка + `return` |
| `@` | PHP | Подавляет ошибки | Проверка предусловий |
| `mixed` без `is_*` | PHP | Тип неизвестен | `is_int()`, `is_float()` и т.д. |
| `any` без проверок | TS | Тип неизвестен | `typeof`, `Array.isArray()` |
| Голый `array` без PHPDoc | PHP | Структура неизвестна | `@param array{key: type}` |
| `object` / `{}` без проверок | TS | Структура неизвестна | Интерфейс + проверки полей |
| `throw` / `throw new Error` | оба | Разрывает поток | `return { ok: false, error }` |
| `console.log`, `echo`, `var_dump` | оба | Побочный эффект вывода | Убрать; логировать в оркестраторе |
| I/O внутри функции | оба | Побочный эффект | Вынести в оркестратор |
| HTTP-запросы внутри функции | оба | Побочный эффект | Вынести в оркестратор |
| `Math.random()`, `Date.now()`, `rand()`, `time()` | оба | Нарушает детерминизм | Передавать как параметр |

> **Исключение для `??` / `?.`**: допустимы на уровне оркестратора при сборке входных данных — там они выражают намеренное значение по умолчанию, а не скрывают отсутствие. Но даже там `?? ''` / `?? []` запрещены — пустая строка или пустой массив как значение по умолчанию маскирует ошибку, её невозможно отличить от штатного пустого результата.

---

## Чеклист

- [ ] Все переменные и параметры имеют префикс типа (`i_`, `f_`, `s_`, `b_`, `a_`, `o_`, `m_`)
- [ ] Все функции именуются по схеме `{ReturnType}_{Object}_{Verb}`
- [ ] Все ключи объектов / массивов имеют префикс типа
- [ ] Нет `null` — ни в возврате, ни в параметрах, ни в теле
- [ ] Нет `?? ''` / `?? []` — пустые значения маскируют ошибку
- [ ] Нет `??` / `?.` без явной проверки внутри чистой функции
- [ ] Нет побочных эффектов (API, I/O, вывод, глобальные переменные)
- [ ] Нет недетерминированных вызовов (`rand`, `time`, `Math.random`, `Date.now`)
- [ ] Все предусловия — в начале функции
- [ ] Все постусловия — перед `return`
- [ ] Типы точны: PHPDoc `array{key: type}` / TS-интерфейсы, без `mixed`/`any`
- [ ] Каждый `return` — это `{ ok: bool, ... }`
- [ ] Ошибки содержат: имя функции + описание + фактическое значение
- [ ] Функция делает ровно одно преобразование
- [ ] При композиции каждый `ok` проверяется перед следующим шагом

---

## Главный принцип

> **Функция доказывает свою правильность через структуру.**

Если функция прошла все предусловия, выполнила детерминированное преобразование, прошла постусловия и не имела побочных эффектов — она математически верна для данного входа. Тесты дополняют эту уверенность на граничных значениях, но не заменяют структурную корректность.
