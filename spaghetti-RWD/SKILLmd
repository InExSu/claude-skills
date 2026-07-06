---
name: spaghetti-RWD
description: >
  Apply this skill when the user asks to "разобрать спагетti", "разбить функцию",
  "переделать спагетти", decompose a monolithic function, or activates via
  @spaghetti or "разбей по RWD". Splits a single sprawling function into a chain
  of single-responsibility steps sharing one state object, run through a
  common step-runner. Do NOT apply without explicit activation — this changes
  control flow, not just naming.
---

# Spaghetti Refactor (RWD pattern)

## Core Principle
One monolithic function = many hidden responsibilities glued together with
shared local variables and nested `if`s. Refactor by:
1. Pulling every distinct responsibility into its own function.
2. Passing a single shared state object (`ns`) between them instead of
   local variables.
3. Each step function **mutates `ns`** and returns nothing (or returns
   early via guard clause).
4. Replacing nested `if` blocks with guard clauses (`if (!x) { ...; return }`).
5. Chaining the steps through one orchestrator function that calls each
   step via a common runner (`rwd`), in order.

## What counts as "one responsibility"
Split whenever the code:
- fetches/reads something (sheet, file, API, DB) → own step
- validates/guards a precondition → folded into the step that needs it,
  as an early return, not a separate step unless validation is reused
- transforms/builds data → own step
- reports/logs → own step
- writes/persists → own step

Rule of thumb: if you can describe the block in one short verb phrase
("get sheet", "read header", "build rows", "log result"), it's a
candidate step.

## Step function shape
```js
function <verb><Noun>_RWD(ns) {
  // read whatever it needs from ns
  // guard clauses first, with early return
  if (!ns.something) {
    ns.somethingElse = <safe empty value>
    return
  }
  // do exactly one thing
  ns.<field> = <result>
}
```
Rules:
- Name = `verb + Noun + _RWD` (e.g. `getResultSheet_RWD`, `buildResultRows_RWD`).
- Takes only `ns`. No other parameters.
- No nested `if`: use guard clauses that `return` early instead.
- On failure, set a conventional error field (`ns.s_Error` or similar,
  matching whatever the codebase already uses) and `return` — never throw
  unless the surrounding codebase throws elsewhere.
- One `console.log` / side effect per step at most, isolated in its own
  step if the original function had logging mixed into logic.

## Orchestrator function
```js
function <original_Name>_RWD(ns) {
  rwd(<step1>_RWD, ns)
  rwd(<step2>_RWD, ns)
  rwd(<step3>_RWD, ns)
  rwd(<step4>_RWD, ns)
}
```
- Keeps the original function's name and signature (`ns` in, nothing out) —
  callers don't need to change.
- Body is *only* a flat list of `rwd(step, ns)` calls, in the same order
  the logic happened in the original spaghetti.
- No branching inside the orchestrator. If the original had a branch that
  skips certain steps, keep that as a guard clause *inside* the relevant
  step (check `ns.o_sheet` inside `getExistingHeader_RWD`, not as an `if`
  in the orchestrator).

## Runner (`rwd`)
Assume a runner already exists with signature `rwd(fn, ns, label?)` that:
- calls `fn(ns)`,
- optionally logs `label`,
- (commonly) stops the chain early if `ns.s_Error` got set.

Don't reinvent it per refactor — reuse the existing `rwd`. Only write one
if the codebase doesn't have it yet, and keep it minimal:
```js
function rwd(fn, ns, label) {
  if (ns.s_Error) return
  if (label) console.log(label)
  fn(ns)
}
```

## Empty values
Use the codebase's existing convention for "nothing here" (often `null`
in vanilla JS, or a typed empty value if the project uses Hungarian
notation / TS-strict style). Don't invent a new convention mid-refactor —
match whatever the file already does elsewhere.

## Rules (for AI)
MUST:
- Preserve exact original behavior and execution order.
- Keep the public entry point's name and signature unchanged.
- Give each step function a name that reads as a single verb phrase.
- Replace nested conditionals with guard clauses.
MUST NOT:
- Introduce new dependencies between steps beyond the shared `ns` object.
- Merge two distinct responsibilities back into one step "for brevity".
- Change error-handling semantics (what triggers an error, what value
  is stored) unless asked.
- Silently rename the shared state object or its existing fields.

## Activation
```
@spaghetti
```
or: "разбери спагетти по RWD", "раздели эту функцию на шаги"
