---
name: hungarian-notation
license: MIT
description: >
  Apply this skill when the user requests Hungarian notation, prefix-typed naming,
  or activates via @hungarian or "венгерская нотация". Covers variables, functions,
  object keys, class properties, and constants in ANY language (JS, PHP, Python, Go).
  Do NOT apply without explicit activation — this is an opt-in coding style.
---

# Hungarian Notation (universal)

## Core principle

Every identifier carries a type prefix. The prefixes are language-neutral; only the
casing style of the host language applies (camelCase / snake_case / PascalCase).

## Prefix table

| Prefix | Type     | Example             |
|--------|----------|---------------------|
| `a_`   | array    | `a_Items`           |
| `b_`   | boolean  | `b_IsActive`        |
| `c_`   | callable | `c_Fn`              |
| `f_`   | float    | `f_Price`           |
| `i_`   | integer  | `i_Count`           |
| `m_`   | mixed    | `m_Value`           |
| `o_`   | object   | `o_User`            |
| `r_`   | result   | `r_Result`          |
| `s_`   | string   | `s_Name`            |
| `v_`   | void     | `v_user_Save` (fn)  |

Exceptions: global objects `ns` (Noosphere) and `rwd` (railway decorator) keep **no** prefix.

## Variables / parameters / keys

Prefix applies to: variables, function parameters, object keys, class properties, array keys.

```php
$a_Items     = [];
$b_IsActive  = true;
$i_Count     = 10;
$s_Name      = 'John';
$o_User      = new User();
$f_Price     = 99.99;
```

## Functions

Structure: `{ReturnType}_{Object}_{Verb}`.
Approved verbs: `Get` `Set` `Load` `Save` `Create` `Update` `Delete` `Check` `Validate` `Process` `Calc` `Format` `Find`

```php
function s_user_NameGet(int $i_UserId): string { ... }
function b_user_Exists(int $i_UserId): bool { ... }
function v_user_Save(array $a_Data): void { ... }
```

Casing follows the host language (camelCase in JS/TS, snake_case in PHP/Python, etc.) — prefixes stay identical.

## Constants

The name includes the stored value as suffix: `MAX_USERS_100`, `APP_NAME_MyApp`.
In typed languages keep the type prefix: `i_MAX_USERS_100 = 100` (JS); in PHP constants carry no `$`.

## Exceptions

Loop counters `i`, `j`, `k` are allowed bare — no prefix required.

## Rules

MUST:
- prefix every variable, parameter, function, object key, class property;
- use approved verbs in function names.

MUST NOT:
- use postfixes instead of prefixes;
- use `goto`;
- use `null` — use typed empty values (`''`, `0`, `[]`, `false`) instead.

## Activation

```
@hungarian
```

or: "стиль кода венгерская нотация"
