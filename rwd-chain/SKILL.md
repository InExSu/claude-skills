---
name: rwd-chain
license: MIT
description: >
  Apply this skill when the user writes pipeline/chain execution code, sequential
  function runners with error handling, decorator-wrapped steps, or asks to implement
  "rwd", "chain of decorators", "pipeline with profiling", or "NS_Container pattern".
  Language-agnostic: works in JS, PHP, Python, Go. Uses Hungarian notation
  (s_Error, a_Log, f_RWD_Start_Time). Do NOT apply without explicit activation
  or clear pipeline/chain context.
---

# RWD Chain Pattern (universal)

## Core idea

Линейный конвейер: каждый шаг — декорируемая функция, мутирующая ОДИН общий
контейнер (`NS_Container` / `ns`). Если шаг выставил `s_Error` — цепочка
останавливается. Язык не важен — меняются только синтаксис и API времени/памяти.

---

## 1. NS_Container

Один мутабельный объект, создаётся один раз:

```php
$ns = [
    's_Error'          => '',      // '' = ОК, не пусто = стоп
    'f_RWD_Start_Time' => 0.0,
    'a_Log'            => [],
    'a_Profile'        => [],
    // + доменные поля проекта
];
```

JS/Python: те же поля в классе `NS_Container` / dict.

---

## 2. v_RWD() — декоратор-исполнитель

```php
function v_RWD(callable $c_Fn, array &$ns): void {
    if ($ns['s_Error'] !== '') return;

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
    v_RWD('v_step_One_RWD', $ns);
    v_RWD('v_step_Two_RWD', $ns);
    v_RWD('v_step_Three_RWD', $ns);
    // v_RWD('v_optional_RWD', $ns); // закомментировано = отключено
    v_RWD('v_profile_RWD', $ns);
}
```

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

Шаги НЕ бросают исключения. При ошибке выставляют `s_Error` и возвращаются:

```php
function v_sheet_Load_RWD(array &$ns): void {
    $a_Data = loadSheet();
    if ($a_Data === []) {
        $ns['s_Error'] = 'v_sheet_Load_RWD: empty data';
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
        $ns['s_Error'] = $o_Result['error'];
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
длительность, пик памяти, итог, финальный статус цепочки).

---

## Правила

**НАДО:**
- Шаги принимают и мутируют `ns` — не возвращают значений
- Шаги вызываются только через `v_RWD()`
- Имена шагов: `v_` + `_RWD`
- Поля контейнера с венгерской нотацией: `s_Error`, `a_Log`, `f_RWD_Start_Time`
- Ошибка останавливает цепочку через `s_Error`, а не исключения
- `v_profile_RWD` всегда последний

**НЕЛЬЗЯ:**
- Бросать исключения внутри шагов
- Вызывать `v_RWD_Start` / `v_RWD_Finish` вручную
- Пропускать `v_RWD()` для любого шага
- Возвращать данные из шагов — используйте `ns`
- Использовать `null` — вместо этого пустые значения: `''`, `0`, `[]`, `0.0`

---

## Активация

```
@rwd
```

или "rwd chain", "pipeline с декораторами", "NS_Container pattern"
