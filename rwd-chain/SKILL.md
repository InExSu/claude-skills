---
name: rwd-chain
license: MIT
description: >
  Apply this skill when the user writes pipeline/chain execution code, sequential
  function runners with error handling, decorator-wrapped steps, or asks to implement
  "rwd", "chain of decorators", "pipeline with profiling", or "NS_Container pattern".
  Language-agnostic: works in JS, PHP, Python, Go. Uses Hungarian notation
  (o_Error, a_Log, f_RWD_Start_Time). Do NOT apply without explicit activation
  or clear pipeline/chain context.
---

# RWD Chain Pattern (universal)

## Core idea

Линейный конвейер: каждый шаг — декорируемая функция, мутирующая ОДИН общий
контейнер (`NS_Container` / `ns`). Если шаг выставил ошибку (`o_Error`) — цепочка
останавливается. Язык не важен — меняются только синтаксис и API времени/памяти.

---

## 1. NS_Container

Один мутабельный объект, создаётся один раз:

```php
$ns = [
    'o_Error'           => null,   // null = ОК, массив = ошибка (см. 6.1)
    'f_RWD_Start_Time'  => 0.0,
    'a_Log'             => [],
    'a_Profile'         => [],
    // + доменные поля проекта
];
```

JS/Python: те же поля в классе `NS_Container` / dict.

---

## 2. v_RWD() — декоратор-исполнитель

```php
function v_RWD(callable $c_Fn, array &$ns): void {
    if (b_Has_Error($ns)) return;

    v_RWD_Start($c_Fn, $ns);
    $c_Fn($ns);
    v_RWD_Finish($c_Fn, $ns);
}
```

---

## 3. Декораторы

Start/Finish пишут в лог и профиль: время старта, длительность, пик памяти, ошибка.
API времени/памяти зависит от языка:

| Язык | Время | Память |
|---|---|---|
| JS | `performance.now()` | `process.memoryUsage()` |
| PHP | `microtime(true)` | `memory_get_peak_usage()` |
| Python | `time.perf_counter()` | `tracemalloc` |
| Go | `time.Now()` | `runtime.ReadMemStats` |

---

## 4. Сборка цепочки

```php
function v_main_RWD_Chain(array &$ns): void {
    v_RWD(v_step_One_RWD(...), $ns);
    v_RWD(v_step_Two_RWD(...), $ns);
    v_RWD(v_step_Three_RWD(...), $ns);
    // v_RWD(v_optional_RWD(...), $ns); // закомментировано = отключено
    v_RWD(v_profile_RWD(...), $ns);
}
```

### 4.1. Как передавать шаг (язык-специфично)

Шаг передаётся как **значение функции**, а не строка с именем: строка не даёт
статической проверки — опечатка всплывёт только в рантайме, IDE и рефакторинг
не видят имя.

| Язык | Способ | Пример |
|---|---|---|
| PHP 8.1+ | first-class callable `(...)` | `v_RWD(v_step_One_RWD(...), $ns)` |
| JS / Python | ссылка на функцию | `rwd(stepOne, ns)` |
| Go | значение функции | `rwd(stepOne, ns)` |

---

## 5. Именование шагов

`v_` + домен + `_Action` + `_RWD`:

| Что делает | Имя функции |
|---|---|
| Загружает данные | `v_sheet_Data_Load_RWD` |
| Обогащает данными | `v_KPP_Enrich_RWD` |
| Сохраняет результат | `v_sheet_Data_Save_RWD` |
| Профиль | `v_profile_RWD` |

---

## 6. Обработка ошибок

Шаги НЕ бросают исключения. Ошибка — структурированный объект `o_Error`
(код, сообщение, шаг, время, стек), а не голая строка. Ключи `o_Error`
пишутся ТОЛЬКО внутри `v_Error_Set()` — это убирает риск опечаток вида
`s_Error` vs `s_error` и сохраняет контекст.

### 6.1. Структура ошибки и доступ

```php
/** Есть ли ошибка (предикат). */
function b_Has_Error(array $ns): bool {
    return $ns['o_Error'] !== null;
}

/** Выставить ошибку: код + сообщение; шаг и стек берутся автоматически. */
function v_Error_Set(array &$ns, string $s_Code, string $s_Message): void {
    $a_Trace = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS, 4);
    $ns['o_Error'] = [
        's_Code'    => $s_Code,
        's_Message' => $s_Message,
        's_Step'    => $a_Trace[1]['function'] ?? '',
        'f_Time'    => microtime(true),
        'a_Stack'   => $a_Trace,
    ];
}

/** Человекочитаемое представление ошибки для логов. */
function s_Error_Get(array $ns): string {
    $o_E = $ns['o_Error'];
    return sprintf('[%s] %s: %s', $o_E['s_Step'], $o_E['s_Code'], $o_E['s_Message']);
}
```

Предикат `b_Has_Error()` используется в раннере; `s_Error_Get()` — в декораторах
и профиле. В JS/Python/Go роль `debug_backtrace` играют `Error().stack` / `traceback` /
`runtime.Callers`.

### 6.2. Пример шага

```php
function v_sheet_Load_RWD(array &$ns): void {
    $a_Data = loadSheet();
    if ($a_Data === []) {
        v_Error_Set($ns, 'EMPTY_DATA', 'v_sheet_Load_RWD: empty data');
        return;
    }
    $ns['a_Data'] = $a_Data;
}
```

---

## 7. Анти-спагетти (SRP внутри шагов)

Шаг только оркестрирует; тяжёлая логика — в чистых помощниках, возвращающих `ok/error`:

```php
function v_price_Build_RWD(array &$ns): void {
    $o_Result = a_price_Commands_Build($ns['a_Items']);
    if (!$o_Result['ok']) {
        v_Error_Set($ns, 'BUILD_FAILED', $o_Result['error']);
        return;
    }
    $ns['a_Commands'] = $o_Result['value'];
}

function a_price_Commands_Build(array $a_Items): array {
    $a_Commands = [];
    foreach ($a_Items as $i => $a_Item) {
        $o_Cmd = a_price_Command_Build($a_Item);
        if (!$o_Cmd['ok']) {
            return ['ok' => false, 'error' => "item $i: {$o_Cmd['error']}"];
        }
        $a_Commands[] = $o_Cmd['value'];
    }
    return ['ok' => true, 'value' => $a_Commands];
}

function a_price_Command_Build(array $a_Item): array {
    $f_Total = $a_Item['price'] * ($a_Item['qty'] ?? 1);
    if ($f_Total <= 0) {
        return ['ok' => false, 'error' => 'non-positive total'];
    }
    return ['ok' => true, 'value' => $f_Total];
}
```

---

## 8. Профилирование (v_profile_RWD)

Финальный шаг всегда последний: выводит таблицу `a_Profile` (статус OK/ERR,
длительность, пик памяти, итог, финальный статус цепочки; при ошибке — код и
сообщение через `s_Error_Get()`).

---

## Правила

**НАДО:**
- Шаги принимают и мутируют `ns` — не возвращают значений
- Шаги вызываются только через `v_RWD()`
- Шаги передаются как **значения функций**, а не строки: в PHP 8.1+ — first-class callable `v_RWD(v_step_One_RWD(...), $ns)`; в JS/Python/Go — прямая ссылка
- Имена шагов: `v_` + `_RWD`
- Поля контейнера с венгерской нотацией: `o_Error`, `a_Log`, `f_RWD_Start_Time`
- Ошибка останавливает цепочку через `o_Error`, а не исключения
- Ошибку выставлять только через `v_Error_Set()`; читать только через `b_Has_Error()` / `s_Error_Get()`
- `v_profile_RWD` всегда последний

**НЕЛЬЗЯ:**
- Бросать исключения внутри шагов
- Вызывать `v_RWD_Start` / `v_RWD_Finish` вручную
- Пропускать `v_RWD()` для любого шага
- Возвращать данные из шагов — используйте `ns`
- Писать/читать ключи `o_Error` вручную мимо `v_Error_Set()` / `b_Has_Error()`
- Использовать `null` в доменных данных — вместо этого пустые значения: `''`, `0`, `[]`, `0.0` (исключение: `o_Error` = null означает «ошибки нет»)

---

## Активация

```
@rwd
```

или "rwd chain", "pipeline с декораторами", "NS_Container pattern"
