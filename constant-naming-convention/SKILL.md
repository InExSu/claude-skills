---
name: constant-naming-convention
description: Provides guidelines for naming constants descriptively, including their values, to improve code readability and maintainability. Use this skill when defining or refactoring constants in any codebase to ensure adherence to a clear naming standard.
---

# Constant Naming Convention

## Overview

This skill enforces a naming convention for constants to enhance code clarity and maintainability. Constants should be named descriptively, incorporating the value they store to make their purpose immediately understandable.

## Guidelines

- **Clarity and Explicitness:** Do not abbreviate or economize on letters in constant names. The name should clearly convey the constant's purpose.
- **Value Inclusion:** The numerical or significant value of the constant should be included in its name. This prevents ambiguity and makes the code self-documenting.

### Example:

**Instead of this (❌ Bad):**

```javascript
const W = 680, H = 450, GROUND = 390, G = 0.22;
```

**Use this (✅ Good):**

```javascript
const WIDTH_680 = 680, HEIGHT_450 = 450, GROUND_390 = 390, GRAVITY_0_22 = 0.22;
```
