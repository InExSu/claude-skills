---
name: rwd-chain
description: >
  Apply this skill when the user writes pipeline/chain execution code, sequential
  function runners with error handling, decorator-wrapped steps, or asks to implement
  "rwd", "chain of decorators", "pipeline with profiling", or "NS_Container pattern".
  Works in any language (PHP, Python, JS/TS, Go, etc.).
  Do NOT apply without explicit activation or clear pipeline/chain context.
  Use together with hungarian-notation skill.
---

# RWD Chain Pattern

## Core Idea

A linear railway pipeline where each step is a **decorated callable**. Steps share a single
mutable container (`NS_Container`). If any step sets an error — all subsequent steps are skipped.

```
v_RWD(v_step_One_RWD, ns)
v_RWD(v_step_Two_RWD, ns)   ← skipped if step_One set ns.s_Error
v_RWD(v_step_Three_RWD, ns) ← skipped if step_One or step_Two set ns.s_Error
```

## Three Components

### 1. NS_Container

Shared mutable state passed through every step. All fields follow Hungarian notation.

Required fields:
- `s_Error` — string, empty = OK; non-empty = chain halts
- `f_RWD_Start_Time` — float, set by decorator before each step
- `a_Log` — append-only string log
- `a_Profile` — append-only profiling records

```php
// PHP
class NS_Container {
    public string $s_Error            = '';
    public float  $f_RWD_Start_Time = 0.0;
    public array  $a_Log              = [];
    public array  $a_Profile          = [];
    // + domain fields per project
}
```

```python
# Python
from dataclasses import dataclass, field

@dataclass
class NS_Container:
    s_Error:            str   = ''
    f_RWD_start_time: float = 0.0
    a_log:              list  = field(default_factory=list)
    a_profile:          list  = field(default_factory=list)
```

```ts
// TypeScript
interface NS_Container {
    s_Error:           string;
    f_RWDStartTime:  number;
    a_log:             string[];
    a_profile:         ProfileEntry[];
    [key: string]:     unknown;
}
```

### 2. v_RWD() — Run With Decorator

The only way to execute a step. Never call steps directly.

```
v_RWD(c_fn, ns):
    if ns.s_Error is set → return immediately
    s_name = resolve callable name
    v_RWD_Start(s_name, ns)
    c_fn(ns)
    v_RWD_Finish(s_name, ns)
```

```php
// PHP
function v_RWD(callable $c_Fn, NS_Container &$ns): void
{
    if ($ns->s_Error !== '') {
        return;
    }
    $s_Name = s_callable_Name_Get($c_Fn);
    v_RWD_Start($s_Name, $ns);
    $c_Fn($ns);
    v_RWD_Finish($s_Name, $ns);
}
```

```python
# Python
def v_RWD(c_fn: Callable, ns: NS_Container) -> None:
    if ns.s_Error:
        return
    s_name = c_fn.__name__
    v_RWD_start(s_name, ns)
    c_fn(ns)
    v_RWD_finish(s_name, ns)
```

```ts
// TypeScript
function v_RWD(c_fn: (ns: NS_Container) => void, ns: NS_Container): void {
    if (ns.s_Error !== '') return;
    const s_name = c_fn.name;
    v_RWDStart(s_name, ns);
    c_fn(ns);
    v_RWDFinish(s_name, ns);
}
```

### 3. Decorators — v_RWD_Start / v_RWD_Finish

**v_RWD_Start** — records start time, prints and logs START:
```
[HH:MM:SS] START: step_name
```

**v_RWD_Finish** — calculates duration, prints FINISH with metrics, logs, profiles:
```
[HH:MM:SS] FINISH: step_name (0.0123 sec | mem: 4 MB | peak: 6 MB)
```

If `ns.s_Error` is set after the step — prints ERROR block and appends to `ns.a_Log`.

Always appends to `ns.a_Profile[]`:
```
{ s_function, f_duration, i_memory, i_memory_peak, s_error, f_timestamp }
```

## Chain Assembly

```php
// PHP — main entry point
function v_main_RWD_Chain(NS_Container $ns): void
{
    v_RWD(v_step_One_v_RWD(...),   $ns);
    v_RWD(v_step_Two_v_RWD(...),   $ns);
    v_RWD(v_step_Three_v_RWD(...), $ns);
    // v_RWD(v_optional_v_RWD(...), $ns);  ← commented out = disabled
    v_RWD(v_profile_v_RWD(...),    $ns);
}
```

```python
# Python
def v_main_rwd_chain(ns: NS_Container) -> None:
    v_RWD(v_step_one_RWD,   ns)
    v_RWD(v_step_two_RWD,   ns)
    v_RWD(v_step_three_RWD, ns)
    v_RWD(v_profile_RWD,    ns)
```

## Step Naming Convention

Steps follow Hungarian notation: `v_` prefix (void) + domain + action + `_RWD` suffix.

| Step does             | Function name               |
|-----------------------|-----------------------------|
| Load data from sheet  | `v_sheet_Data_Load_RWD`   |
| Enrich with KPP data  | `v_KPP_Enrich_RWD`        |
| Save results          | `v_sheet_Data_Save_RWD`   |
| Print profile summary | `v_profile_RWD`           |
| Print log dump        | `v_logs_RWD`              |

## v_profile_RWD — Built-in Last Step

Always add as the final step. Prints execution summary:

```
======================================================================
EXECUTION PROFILE
======================================================================
OK   v_sheet_Data_Load_RWD        | 0.1234 sec | 4 MB
OK   v_KPP_Enrich_RWD             | 0.8901 sec | 12 MB
ERR  v_sheet_Data_Save_RWD        | 0.0023 sec | 12 MB
----------------------------------------------------------------------
TOTAL: 1.0158 sec
PEAK MEMORY: 14 MB
======================================================================
```

## Error Handling Rules

- Steps MUST set `ns.s_Error` on failure — never throw/raise inside a step
- `rwd` checks `s_Error` BEFORE running the next step — chain halts automatically
- `v_RWD_Finish` detects and logs error AFTER the step that caused it
- `v_profile_RWD` always runs — checks `s_Error` itself and still prints full profile

```php
// Correct — set s_Error, return
function v_sheet_Data_Load_v_RWD(NS_Container $ns): void
{
    $a_Data = v_sheet_Load();
    if ($a_Data === []) {
        $ns->s_Error = 'v_sheet_Data_Load_RWD: empty response';
        return;
    }
    $ns->a_SheetData = $a_Data;
}
```

Теперь добавляю раздел в документ скилла `rwd-chain`. Поскольку это документ в сообщении пользователя (не файл на диске), возвращаю обновлённую версию.

Вот обновлённый скилл с новым разделом — вставь его между **"Error Handling Rules"** и **"s_callable_Name_Get (PHP)"**:

---

## No Spaghetti — SRP Function Chains

### Правило

Тело шага (`_RWD`-функции) **не может быть длинным процедурным блоком**. Каждый шаг — это оркестратор: он вызывает цепочку SRP-функций и пробрасывает ошибки в `ns.s_Error`.

```
step = orchestrator
     → pure fn 1 → check ok
     → pure fn 2 → check ok
     → pure fn 3 → check ok
     → write result to ns
```

### Что такое спагетти-шаг (ЗАПРЕЩЕНО)

```php
// ❌ ПЛОХО — один шаг делает всё сам: парсит, валидирует, считает, форматирует
function v_price_Build_RWD(NS_Container $ns): void
{
    $a_Items = $ns->a_RawItems;
    $a_Result = [];
    foreach ($a_Items as $i => $a_Item) {
        if (!isset($a_Item['price']) || !is_float($a_Item['price'])) {
            $ns->s_Error = "v_price_Build_RWD: item {$i}: invalid price";
            return;
        }
        $f_Price = $a_Item['price'] * ($a_Item['qty'] ?? 1); // ← скрытая логика
        if ($f_Price <= 0.0) {
            $ns->s_Error = "v_price_Build_RWD: item {$i}: non-positive total";
            return;
        }
        $a_Result[] = ['method' => 'price.update', 'params' => ['price' => $f_Price]];
    }
    $ns->a_Commands = $a_Result;
}
```

Проблемы: логика перемешана с итерацией, валидацией и форматированием. Невозможно тестировать части по отдельности. Изменение формата команды ломает всю функцию.

### Правильно — цепочка SRP-функций

```php
// ✅ ХОРОШО — шаг только оркестрирует
function v_price_Build_RWD(NS_Container $ns): void
{
    $a_Commands = a_price_Commands_Build($ns->a_RawItems);
    if (!$a_Commands['ok']) {
        $ns->s_Error = $a_Commands['error'];
        return;
    }
    $ns->a_Commands = $a_Commands['value'];
}

// SRP-функции — каждая делает одно
function a_price_Commands_Build(array $a_Items): array
{
    if ($a_Items === []) {
        return ['ok' => false, 'error' => 'a_price_Commands_Build: empty items'];
    }

    $a_Commands = [];

    foreach ($a_Items as $i => $a_Item) {
        $a_Command = a_price_Command_Build($a_Item);
        if (!$a_Command['ok']) {
            return ['ok' => false, 'error' => "a_price_Commands_Build: item {$i}: {$a_Command['error']}"];
        }
        $a_Commands[] = $a_Command['value'];
    }

    return ['ok' => true, 'value' => $a_Commands];
}

function a_price_Command_Build(array $a_Item): array
{
    $f_Total = f_price_Total_Calculate($a_Item);
    if (!$f_Total['ok']) {
        return $f_Total;
    }

    return [
        'ok'    => true,
        'value' => ['method' => 'price.update', 'params' => ['price' => $f_Total['value']]],
    ];
}

function f_price_Total_Calculate(array $a_Item): array
{
    if (!isset($a_Item['price']) || !is_float($a_Item['price'])) {
        return ['ok' => false, 'error' => 'f_price_Total_Calculate: invalid price'];
    }
    if (!isset($a_Item['qty']) || !is_int($a_Item['qty']) || $a_Item['qty'] <= 0) {
        return ['ok' => false, 'error' => 'f_price_Total_Calculate: invalid qty'];
    }

    $f_Total = $a_Item['price'] * (float) $a_Item['qty'];

    if ($f_Total <= 0.0) {
        return ['ok' => false, 'error' => "f_price_Total_Calculate: non-positive total, got: {$f_Total}"];
    }

    return ['ok' => true, 'value' => $f_Total];
}
```

### Признаки спагетти внутри шага

| Симптом | Что сделать |
|---|---|
| Вложенные `foreach` + `if` в одной функции | Вынести итерацию и проверки в отдельные функции |
| Функция > ~25 строк тела | Разбить на SRP-функции |
| Комментарии `// шаг 1`, `// шаг 2` внутри функции | Каждый "шаг" — отдельная функция |
| Один `return` в конце большого блока | Ранние `return` при ошибке в каждой SRP-функции |
| Локальные переменные-флаги (`$b_Valid`, `$b_Found`) | Заменить на явный `return ['ok' => false, ...]` |

### Правило глубины

```
v_step_RWD          ← оркестратор (только вызовы + проброс ошибок)
  └─ a_*_Build      ← коллекция: итерация + делегирование
       └─ a_*_Build_Single  ← один элемент: композиция чистых функций
            └─ f_*_Calculate / s_*_Format / b_*_Validate  ← атомарные SRP
```

Максимальная глубина вложенности логики — 4 уровня. Если глубже — промежуточный уровень делает слишком много.

### Связь с pure-functions скиллом

SRP-функции внутри шага пишутся по правилам **pure-functions** скилла:
- возвращают `['ok' => bool, ...]`
- не мутируют `ns` напрямую (только `_RWD`-шаг пишет в `ns`)
- без побочных эффектов, без `throw`

---

Раздел намеренно разделяет **RWD как транспорт ошибок** и **SRP-функции как логику** — это позволяет тестировать бизнес-логику без поднятия всей цепочки.


## s_callable_Name_Get (PHP)

```php
function s_callable_Name_Get(callable $c_Fn): string
{
    if (is_array($c_Fn)) {
        $s_Class = is_string($c_Fn[0]) ? $c_Fn[0] : get_class($c_Fn[0]);
        return $s_Class . '::' . $c_Fn[1];
    }
    if ($c_Fn instanceof Closure) {
        $o_Ref  = new ReflectionFunction($c_Fn);
        $s_Name = $o_Ref->getName();
        return $s_Name !== '{closure}' ? $s_Name : '{closure}';
    }
    if (is_string($c_Fn)) {
        return $c_Fn;
    }
    return get_class($c_Fn) . '::__invoke';
}
```

## Rules (for AI)

MUST:
- All steps receive and mutate `ns` — no return values from steps
- All steps passed through `v_RWD()` — never called directly
- Steps named with `v_` prefix and `_RWD` suffix
- NS_Container fields follow Hungarian notation: `s_Error`, `a_Log`, `f_RWD_Start_Time`
- Profile records use prefixed keys: `s_function`, `f_duration`, `i_memory`, `s_error`
- Error stops chain via `ns.s_Error`, not exceptions
- `v_profile_RWD` is always the last step

MUST NOT:
- Throw exceptions inside steps (catch and set `ns.s_Error` instead)
- Call `v_RWD_Start` / `v_RWD_Finish` manually
- Skip `v_RWD()` wrapper for any step
- Return data from steps — use `ns` fields
- Use `null` — use typed empty values (`''`, `0`, `[]`, `0.0`) instead

## Activation

```
@rwd
```

or: "rwd chain", "pipeline с декораторами", "NS_Container pattern"
