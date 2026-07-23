---
name: rwd-chain
description: >
  Apply this skill when the user writes pipeline/chain execution code, sequential
  function runners with error handling, decorator-wrapped steps, or asks to implement
  "rwd", "chain of decorators", "pipeline with profiling", or "NS_Container pattern".
  JavaScript implementation only. Uses Hungarian notation (s_Error, a_Log, f_RWD_Start_Time).
  Do NOT apply without explicit activation or clear pipeline/chain context.
---

# RWD Chain Pattern (JavaScript)

## Core Idea

Линейный конвейер, где каждый шаг — декорируемая функция. Шаги разделяют один мутабельный контейнер `NS_Container`. Если любой шаг устанавливает `s_Error` — цепочка останавливается.

```
v_RWD(v_step_One_RWD, ns)
v_RWD(v_step_Two_RWD, ns)   // пропускается, если step_One установил ns.s_Error
v_RWD(v_step_Three_RWD, ns) // пропускается
```

---

## 1. NS_Container

```javascript
class NS_Container {
  constructor() {
    this.s_Error = '';              // пусто = ОК, не пусто = стоп
    this.f_RWD_Start_Time = 0.0;
    this.a_Log = [];
    this.a_Profile = [];
    // + доменные поля проекта
  }
}
```

---

## 2. v_RWD() — декоратор-исполнитель

```javascript
function v_RWD(c_Fn, ns) {
  if (ns.s_Error !== '') return;

  const s_Name = s_callable_Name_Get(c_Fn);
  v_RWD_Start(s_Name, ns);
  c_Fn(ns);
  v_RWD_Finish(s_Name, ns);
}
```

---

## 3. Декораторы

```javascript
function v_RWD_Start(s_Name, ns) {
  ns.f_RWD_Start_Time = performance.now();
  const s_Msg = `[${new Date().toTimeString().slice(0, 8)}] START: ${s_Name}`;
  console.log(s_Msg);
  ns.a_Log.push(s_Msg);
}

function v_RWD_Finish(s_Name, ns) {
  const f_Duration = (performance.now() - ns.f_RWD_Start_Time) / 1000;
  const i_Memory = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);
  const i_Memory_Peak = Math.round(process.memoryUsage().heapTotal / 1024 / 1024);

  let s_Msg = `[${new Date().toTimeString().slice(0, 8)}] FINISH: ${s_Name} (${f_Duration.toFixed(4)} sec | mem: ${i_Memory} MB | peak: ${i_Memory_Peak} MB)`;

  if (ns.s_Error !== '') {
    s_Msg += `\n  ⚠️ ERROR: ${ns.s_Error}`;
    ns.a_Log.push(`  ERROR: ${ns.s_Error}`);
  }

  console.log(s_Msg);
  ns.a_Log.push(s_Msg);

  ns.a_Profile.push({
    s_function: s_Name,
    f_duration: f_Duration,
    i_memory: i_Memory,
    i_memory_peak: i_Memory_Peak,
    s_error: ns.s_Error,
    f_timestamp: Date.now() / 1000
  });
}
```

---

## 4. Сборка цепочки

```javascript
function v_main_RWD_Chain(ns) {
  v_RWD(v_step_One_RWD, ns);
  v_RWD(v_step_Two_RWD, ns);
  v_RWD(v_step_Three_RWD, ns);
  // v_RWD(v_optional_RWD, ns); // закомментировано = отключено
  v_RWD(v_profile_RWD, ns);
}
```

---

## 5. Именование шагов

`v_` + `domain` + `_Action` + `_RWD`

| Что делает | Имя функции |
|---|---|
| Загружает данные | `v_sheet_Data_Load_RWD` |
| Обогащает данными | `v_KPP_Enrich_RWD` |
| Сохраняет результат | `v_sheet_Data_Save_RWD` |
| Профиль | `v_profile_RWD` |

---

## 6. v_profile_RWD — встроенный финальный шаг

```javascript
function v_profile_RWD(ns) {
  console.log('='.repeat(70));
  console.log('EXECUTION PROFILE');
  console.log('='.repeat(70));

  let f_Total = 0;
  let i_Peak = 0;

  for (const o of ns.a_Profile) {
    const s_Status = o.s_error !== '' ? 'ERR' : 'OK';
    console.log(`${s_Status}  ${o.s_function.padEnd(30)} | ${o.f_duration.toFixed(4)} sec | ${o.i_memory} MB`);
    f_Total += o.f_duration;
    i_Peak = Math.max(i_Peak, o.i_memory_peak);
  }

  console.log('-'.repeat(70));
  console.log(`TOTAL: ${f_Total.toFixed(4)} sec`);
  console.log(`PEAK MEMORY: ${i_Peak} MB`);
  console.log('='.repeat(70));
  console.log(ns.s_Error !== '' ? `\n❌ FAILED: ${ns.s_Error}` : '\n✅ SUCCESS');
}
```

---

## 7. Обработка ошибок

```javascript
// ✅ Правильно
function v_sheet_Load_RWD(ns) {
  const a_Data = loadSheet();
  if (a_Data.length === 0) {
    ns.s_Error = 'v_sheet_Load_RWD: empty data';
    return;
  }
  ns.a_Data = a_Data;
}

// ❌ Неправильно — бросать исключения
function v_sheet_Load_RWD(ns) {
  throw new Error('boom'); // так НЕЛЬЗЯ
}
```

---

## 8. Анти-спагетти (SRP внутри шагов)

**❌ Плохо — один шаг делает всё:**

```javascript
function v_price_Build_RWD(ns) {
  const a_Result = [];
  for (let i = 0; i < ns.a_Items.length; i++) {
    const a_Item = ns.a_Items[i];
    if (!a_Item.price || typeof a_Item.price !== 'number') {
      ns.s_Error = `item ${i}: invalid price`;
      return;
    }
    const f_Price = a_Item.price * (a_Item.qty || 1);
    if (f_Price <= 0) {
      ns.s_Error = `item ${i}: non-positive`;
      return;
    }
    a_Result.push({ method: 'price.update', params: { price: f_Price } });
  }
  ns.a_Commands = a_Result;
}
```

**✅ Хорошо — шаг только оркестрирует:**

```javascript
function v_price_Build_RWD(ns) {
  const o_Result = a_price_Commands_Build(ns.a_Items);
  if (!o_Result.ok) {
    ns.s_Error = o_Result.error;
    return;
  }
  ns.a_Commands = o_Result.value;
}

function a_price_Commands_Build(a_Items) {
  const a_Commands = [];
  for (let i = 0; i < a_Items.length; i++) {
    const o_Cmd = a_price_Command_Build(a_Items[i]);
    if (!o_Cmd.ok) return { ok: false, error: `item ${i}: ${o_Cmd.error}` };
    a_Commands.push(o_Cmd.value);
  }
  return { ok: true, value: a_Commands };
}

function a_price_Command_Build(a_Item) {
  const o_Total = f_price_Total_Calc(a_Item);
  if (!o_Total.ok) return o_Total;
  return { ok: true, value: { method: 'price.update', params: { price: o_Total.value } } };
}

function f_price_Total_Calc(a_Item) {
  if (!a_Item.price || typeof a_Item.price !== 'number') {
    return { ok: false, error: 'invalid price' };
  }
  const f_Total = a_Item.price * (a_Item.qty || 1);
  if (f_Total <= 0) return { ok: false, error: 'non-positive total' };
  return { ok: true, value: f_Total };
}
```

---

## 9. s_callable_Name_Get

```javascript
function s_callable_Name_Get(c_Fn) {
  if (c_Fn.name) return c_Fn.name;

  const s_Fn = c_Fn.toString();
  const a_Arrow = s_Fn.match(/^\(?([a-zA-Z_$][a-zA-Z0-9_$]*)\)?\s*=>/);
  if (a_Arrow) return a_Arrow[1] || '{arrow}';

  const a_Func = s_Fn.match(/^function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)/);
  if (a_Func) return a_Func[1];

  return '{anonymous}';
}
```

---

## Правила

**НАДО:**
- Шаги принимают и мутируют `ns` — без возврата значений
- Шаги вызываются только через `v_RWD()`
- Имена шагов: `v_` + `_RWD`
- Поля `NS_Container` с венгерской нотацией: `s_Error`, `a_Log`, `f_RWD_Start_Time`
- Ошибка останавливает цепочку через `ns.s_Error`, а не исключения
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
