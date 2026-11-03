---
name: constant-naming-convention
license: MIT
description: >
  Naming constants descriptively, including the value they hold, so the code documents itself.
  Use when defining or refactoring constants in any codebase. «Имена констант», «constant naming»,
  «naming convention». Do NOT apply to loop variables, function parameters, or mutable state —
  only to true constants. When Hungarian notation is active (@hungarian), constant names also
  carry a type prefix — see [hungarian-notation](../hungarian-notation/SKILL.md).
---

# Constant Naming Convention

## Rule

Constants are named descriptively, **including the value they hold**. The name answers two questions at once: what is this constant for, and what is its value? This makes the code self-documenting — a reader sees the value without jumping to the definition.

## Guidelines

- **No abbreviations.** `W` could mean width, weight, warning. `i_WIDTH_680` is unambiguous.
- **Include the numerical or significant value in the name.** This prevents ambiguity and makes the code self-documenting.
- **Type prefixes** (only when `@hungarian` is active): `i_` for integers, `f_` for floats, `s_` for strings, `b_` for booleans.

## Examples

### Bad → Good

```javascript
// ❌ Bad — what are these?
const W = 680;
const G = 0.22;
const T = 30000;
const C = "#ff0000";

// ✅ Good — self-documenting
const i_WIDTH_680 = 680;
const f_GRAVITY_0_22 = 0.22;
const i_TIMEOUT_MS_30000 = 30000;
const s_COLOR_RED_FF0000 = "#ff0000";
```

### Without Hungarian notation

```javascript
// ❌ Bad
const MAX = 100;
const URL = "https://api.example.com";

// ✅ Good
const MAX_RETRIES_100 = 100;
const API_URL_https_api_example_com = "https://api.example.com";
```

## Anti-patterns

- `const MAGIC = 42` — the value is hidden behind a generic name.
- `const TIMEOUT = 30000` — is it ms or seconds? Include the unit: `i_TIMEOUT_MS_30000`.
- `const DATA = []` — what data? Use a descriptive name.
- Renaming a constant everywhere when its value changes — **yes, that's the point.** If `MAX_USERS_100` becomes 200, you rename it to `MAX_USERS_200`, and every reference updates. This forces a conscious review of all call sites when a threshold changes. If that's too much friction for your project, this skill is not for you — use `@constant-naming-convention` opt-in only when value-in-name adds safety.

## Trade-off

Embedding the value in the name means changing the value requires renaming the constant everywhere. This is **intentional**: it forces a review of every call site when a threshold or limit changes. If your constant changes frequently, consider whether it should be a configuration value instead of a constant.

## Checklist

- [ ] Every constant name includes its significant value
- [ ] No single-letter or abbreviated constant names
- [ ] Units included where applicable (MS, PX, SEC)
- [ ] If `@hungarian` is active, type prefix is present
