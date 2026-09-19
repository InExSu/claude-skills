---
name: constant-naming-convention
license: MIT
description: Provides guidelines for naming constants descriptively, including their values, to improve code readability and maintainability. Use this skill when defining or refactoring constants in any codebase to ensure adherence to a clear naming standard. When Hungarian notation is active, constant names also carry a type prefix — see [hungarian-notation](../hungarian-notation/SKILL.md) for the prefix table.
---

# Constant Naming Convention

## Overview

This skill enforces a naming convention for constants to enhance code clarity and maintainability. Constants should be named descriptively, incorporating the value they store to make their purpose immediately understandable.

## Guidelines

- **Clarity and Explicitness:** Do not abbreviate or economize on letters in constant names. The name should clearly convey the constant's purpose.
- **Value Inclusion:** The numerical or significant value of the constant should be included in its name. This prevents ambiguity and makes the code self-documenting.
- **Type Prefixes:** When Hungarian notation is active (see [hungarian-notation](../hungarian-notation/SKILL.md), opt-in via `@hungarian`), constant names additionally carry a type prefix — `i_` for integers, `f_` for floats — while keeping the descriptive name and value suffix from the rules above.

### Example:

**Instead of this (❌ Bad):**

```javascript
const W = 680, G = 0.22;
```

**Use this (✅ Good):**

```javascript
const i_WIDTH_680 = 680, f_GRAVITY_0_22 = 0.22;
```
