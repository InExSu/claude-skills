---
name: hungarian-notation
description: >
  Apply this skill when the user requests Hungarian notation, prefix-typed naming,
  or activates via @hungarian or "венгерская нотация". Covers variables, functions,
  object keys, class properties, and constants in any language (JS, PHP, Python, etc.).
  Do NOT apply without explicit activation — this is an opt-in coding style.
---

# Hungarian Notation (Universal)

## Core Principle

Every identifier carries a type prefix. No exceptions except loop counters and constants (see §7).

## Prefix Table

| Prefix | Type         | Example                   |
|--------|--------------|---------------------------|
| `i_`   | integer      | `i_Count = 10`            |
| `f_`   | float        | `f_Price = 99.99`         |
| `s_`   | string       | `s_Name = 'John'`         |
| `b_`   | boolean      | `b_IsActive = true`       |
| `a_`   | array / list | `a_Items = []`            |
| `o_`   | object       | `o_User = new User()`     |
| `m_`   | mixed        | `m_Value = getData()`     |
| `v_`   | void         | `v_user_Save` (functions) |
| `c_`   | callable     | `c_Fn = trim`             |

Here's the translation:

---

**Exception for `ns`:**

`ns` is a reserved name for the global **NooSphere** object in my programs. It remains unchanged — the `o_` prefix MUST NOT be applied to it.

That is:
- ✅ `ns` — allowed (global NooSphere object)
- ❌ `o_ns` — DO NOT use, do not rename

All other objects receive the `o_` prefix as usual.

## Variables

```js
let i_UserId   = 1;
let s_UserName = 'John';
let f_Price    = 99.99;
let b_IsActive = true;
let a_Roles    = ['admin', 'user'];
let o_Profile  = { s_city: 'Moscow' };
```

## Functions — `{ReturnType}_{Object}_{Verb}`

Structure: `{ReturnType}_{Object}_{Verb}`

| Function            | Returns |
|---------------------|---------|
| `a_user_DataLoad`   | array   |
| `s_user_NameGet`    | string  |
| `i_user_AgeGet`     | integer |
| `b_user_Exists`     | boolean |
| `o_user_Create`     | object  |
| `v_user_Save`       | void    |
| `f_order_TotalCalc` | float   |
| `b_form_Validate`   | boolean |

Approved verbs: `Get` `Set` `Load` `Save` `Create` `Update` `Delete` `Check` `Validate` `Process` `Calc` `Format` `Find`

```js
function a_user_DataLoad() {
    return { i_id: 1, s_name: 'John' };
}

function s_user_NameGet(i_UserId) {
    return 'John';
}

function b_user_Exists(i_UserId) {
    return i_UserId > 0;
}
```

## Object Keys

```js
let o_User = {
    i_id:       1,
    s_name:     'John Doe',
    f_salary:   50000.00,
    b_isActive: true,
    a_roles:    ['admin', 'user'],
    o_profile:  { s_city: 'Moscow' }
};
```

## Class Properties

```js
class User {
    i_id       = 0;
    s_name     = '';
    f_balance  = 0.0;
    b_isActive = false;
    a_roles    = [];

    a_user_DataGet() {
        return { i_id: this.i_id, s_name: this.s_name };
    }

    v_user_Save() { /* persists */ }
}
```

## Constants

Include the value in the name as a suffix:

```js
const i_MAX_USERS_100  = 100;
const s_APP_NAME_MyApp = 'MyApp';
```

## Exceptions

Loop counters `i`, `j`, `k` are allowed bare — no prefix required.

## Rules (for AI)

MUST:
- Prefix every variable, parameter, function, object key, class property
- Use approved verb list for function names

MUST NOT:
- Use postfixes instead of prefixes
- Use `goto`
- Use `null` — use typed empty values (`''`, `0`, `[]`, `false`) instead

## Activation

```
@hungarian
```

or: "стиль кода венгерская нотация"
