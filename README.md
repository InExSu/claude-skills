<div align="center">

# 🧠 AI Agent Skills

**A curated collection of [Agent Skills](https://agentskills.io) for AI agents** — coding standards, testing discipline, architecture patterns, agent design and DRAKON diagram tooling. They work with any agent that implements the open standard, including [Claude Code](https://claude.com/claude-code).

[![Skills](https://img.shields.io/badge/skills-15-blue?style=flat-square)](#-skill-catalog)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-open%20standard-D97757?style=flat-square)](https://agentskills.io)
[![Python](https://img.shields.io/badge/python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](#-drakonhub-spotlight)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6%2B-F7DF1E?style=flat-square&logo=javascript&logoColor=black)](#-skill-catalog)
[![Markdown](https://img.shields.io/badge/docs-Markdown-000000?style=flat-square&logo=markdown&logoColor=white)](#-skill-catalog)

[![Last commit](https://img.shields.io/github/last-commit/InExSu/claude-skills?style=flat-square)](https://github.com/InExSu/claude-skills/commits/master)
[![Commit activity](https://img.shields.io/github/commit-activity/y/InExSu/claude-skills?style=flat-square)](https://github.com/InExSu/claude-skills/commits/master)
[![Repo size](https://img.shields.io/github/repo-size/InExSu/claude-skills?style=flat-square)](https://github.com/InExSu/claude-skills)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)
[![CI](https://github.com/InExSu/claude-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/InExSu/claude-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

**English** · [Русский](README.ru.md)

</div>

---

## 📖 What is this?

This repository is a set of **skills for AI agents that implement the [Agent Skills](https://agentskills.io) open standard**. A skill is a folder with a `SKILL.md` file whose YAML frontmatter contains a `name` and a `description`. The agent reads the description at startup and decides on its own whether the skill applies to the current task — so, once installed, the skills activate during normal conversation, without any special effort.

Most skills are **behavioral contracts**: they forbid a class of convenient-but-harmful shortcuts (tautological tests, patching code without a reproducing test, spaghetti functions, tokens spent on politeness). A few are **tooling**: `drakonhub` ships Python scripts, a file-format reference and ready-made templates.

```mermaid
flowchart LR
    A[User request] --> B{The agent matches<br/>skill description}
    B -->|relevant| C[Load SKILL.md]
    B -->|not relevant| D[Answer without the skill]
    C --> E{Rules and tools<br/>from the skill}
    E --> F[Constrained, verifiable result]
```

---

## 📚 Skill catalog

### 🧪 Testing & correctness

| Skill | What it enforces |
|---|---|
| **[tdd-bugfix](tdd-bugfix/SKILL.md)** | Bug fixing through a strict **RED → YELLOW → GREEN** cycle: first a failing test that reproduces the bug, then a minimal patch, then a clean refactor. Never patch source code before the red test exists. |
| **[quality-tests](quality-tests/SKILL.md)** | Tests that check behavior instead of inflating coverage. A diagnostic start table plus sections on antipatterns (tautological tests), what to test, and why a suite fails to catch bugs. |
| **[self-test-design](self-test-design/SKILL.md)** | Build software like reliable hardware: Design-For-Test, built-in self-test (BIST/POST), the `TestPort` contract, state-transition tables. The golden rule: verify the **absence of unwanted** behavior, not only the presence of wanted behavior. |

### 🏗️ Architecture & refactoring

| Skill | What it enforces |
|---|---|
| **[pure-functions](pure-functions/SKILL.md)** | 7 axioms for JavaScript/TypeScript functions: input→output mapping, determinism, no side effects, `ok/error` result format, preconditions/postconditions/invariants. |
| **[if-condition-refactor](if-condition-refactor/SKILL.md)** | Complex `if`/`switch` conditions become readable predicate functions — lower cyclomatic complexity, better testability, no inlined business logic inside conditions. |
| **[noosphere](noosphere/SKILL.md)** | A single source of truth: one global state object `ns`, initialized once, mutated through a defined interface. Pure functions must **not** depend on `ns`. |
| **[state-machine-if-improves-understanding](state-machine-if-improves-understanding/SKILL.md)** | A decision rule for when a Shalyto switch state machine is justified (non-linear transitions, retry loops, pagination) and when plain SRP code is the better answer. |
| **[spaghetti-rwd](spaghetti-rwd/SKILL.md)** | Splits a monolithic function into a chain of single-responsibility steps sharing one state object, executed by a common step runner. *(opt-in: `@spaghetti`)* |

### ✍️ Naming & style *(opt-in)*

| Skill | What it enforces |
|---|---|
| **[hungarian-notation](hungarian-notation/SKILL.md)** | Type prefixes for variables, functions, object keys, class properties and constants in any language. Explicit opt-in only. *(activate with `@hungarian`)* |
| **[constant-naming-convention](constant-naming-convention/SKILL.md)** | Constants named descriptively **including the value they hold**, so the code documents itself. |
| **[token-economy](token-economy/SKILL.md)** | Every token must earn its place: no politeness padding, no redundant restatement, in prompts, instructions, docs and code. |

### 🔗 Pipelines

| Skill | What it enforces |
|---|---|
| **[rwd-chain](rwd-chain/SKILL.md)** | JavaScript pipeline pattern: each step is a decorated function over a shared mutable `NS_Container`; any step setting `s_Error` halts the chain. Built-in profiling and logging fields. |

### 🤖 AI agents & 🐉 Diagrams

| Skill | What it enforces |
|---|---|
| **[ru-psychoagent](ru-psychoagent/SKILL.md)** | Architecture principles for AI agents drawn from the Russian psychological school — Luria, Vygotsky, Bernstein, Bakhtin: internal speech, sensorimotor loops, sense-making. |
| **[drakonhub](drakonhub/SKILL.md)** | Turns ordinary text into a JSON file containing a DRAKON diagram (`.drakon`) and structured mind maps (`.graf`): exact JSON schema, icon semantics, language rules, a validator and templates. Viewing — [DrakonHub](https://drakonhub.com/) by Stepan Mitkin. |

## 🐉 drakonhub spotlight

The only skill with executable tooling. It turns ordinary, human-readable text into a JSON file containing a DRAKON diagram. For viewing, use [DrakonHub](https://drakonhub.com/) by Stepan Mitkin.

**Language rules baked into the skill:** flow goes top-down with no arrows, branching only to the right, lines never cross, and "the further right, the worse" — the happy path goes straight down while failures drift right. Exactly one `end`, one icon = one step, actions in imperative mood, questions without *and* / *or* / *not*.

### Scripts (Python 3, standard library only — except the last one)

```bash
cd drakonhub

# 1. Validate a diagram against the DrakonHub import schema + DRAKON rules
python3 scripts/drakon_tool.py check templates/choice-and-loop.drakon
#   → OK: ошибок и замечаний нет

# 2. Read a diagram as indented pseudocode, split by silhouette branches
python3 scripts/drakon_tool.py read templates/minimal.drakon

# 3. Write diagrams in a compact DSL instead of hand-building JSON
python3 scripts/drakon_dsl.py to-drakon templates/workout.dsl out.drakon
python3 scripts/drakon_dsl.py to-dsl    out.drakon out.dsl
python3 scripts/drakon_dsl.py roundtrip templates/minimal.drakon
#   → OK: графы совпали (6 узлов)

# 4. Compute the silhouette layout and render it
python3 scripts/drakon_render.py svg templates/silhouette.drakon out.svg  # picture for humans
python3 scripts/drakon_render.py map templates/silhouette.drakon          # coordinate map for agents
#   → OK: templates/silhouette.drakon -> out.svg (7x6 клеток, 18 иконок)
```

### Catching hangs with the real engine

`check` only catches the traps that could be formalized. The editor can still hang on a diagram the checker calls valid — `layoutSilhouette` walks down, hits a back edge and walks again, forever.

```bash
python3 scripts/drakon_try.py render my.drakon   # OK nodes=94 | HANG | ERROR <reason>
python3 scripts/drakon_try.py stack  my.drakon   # where it hangs, via CDP Debugger.pause
```

This is the only script that leaves the standard library: it needs `git`, `node`, `playwright` and a chromium from the Playwright cache. On first run it clones `stepan-mitkin/drakonhub_desktop` into `drakonhub/.cache/` (gitignored) and serves it locally. Everything else in the skill works without it.

### Why the DSL exists

Hand-writing `.drakon` means inventing an `id` per icon and wiring `one` / `two` links by hand — an error-prone job for an LLM. The DSL describes the algorithm as indented text, and the converter assigns ids, builds the links and lays out the silhouettes itself:

```
# Тренировка
> Условие старта: спортзал, есть 40 минут
@ Разминка
  Выполнить суставную разминку
```

| File | Purpose |
|---|---|
| `SKILL.md` | The skill itself: rules, icon semantics, format schema |
| `reference/file-format.md` | Deep dive into the `.drakon` JSON format and edge cases |
| `scripts/drakon_tool.py` | `read` (pseudocode) and `check` (validation) |
| `scripts/drakon_dsl.py` | DSL ⇄ `.drakon` conversion and round-trip verification |
| `scripts/drakon_render.py` | Silhouette layout → SVG or coordinate map |
| `templates/*.drakon`, `templates/*.dsl` | Ready-made examples: minimal, choice-and-loop, silhouette, workout |

---

## 📂 Repository layout

```
claude-skills/
├── README.md                  ← you are here (English)
├── README.ru.md               ← Russian version
├── CONTRIBUTING.md            ← how to submit a skill or a fix
├── CONTRIBUTING.ru.md
├── CODE_OF_CONDUCT.md         ← Contributor Covenant 2.1
├── SECURITY.md                ← threat model and how to report
├── LICENSE                    ← MIT
├── .editorconfig
├── .github/
│   ├── workflows/ci.yml       ← checks every push and pull request
│   ├── ISSUE_TEMPLATE/        ← bug report and skill proposal forms, plus config.yml
│   ├── scripts/check_skills.py
│   └── PULL_REQUEST_TEMPLATE.md
├── AGENTS.md                  ← machine-readable notes for AI agents consuming this repo
├── gh.sh                      ← add-all / commit / push helper
├── constant-naming-convention/
│   └── SKILL.md
├── drakonhub/
│   ├── SKILL.md
│   ├── reference/file-format.md
│   ├── scripts/{drakon_tool,drakon_dsl,drakon_render}.py
│   ├── templates/{minimal,choice-and-loop,silhouette}.drakon
│                  workout.dsl
├── hungarian-notation/SKILL.md
├── if-condition-refactor/SKILL.md
├── noosphere/SKILL.md
├── pure-functions/SKILL.md
├── quality-tests/SKILL.md
├── ru-psychoagent/SKILL.md
├── rwd-chain/SKILL.md
├── self-test-design/SKILL.md
├── spaghetti-rwd/SKILL.md
├── state-machine-if-improves-understanding/SKILL.md
├── tdd-bugfix/SKILL.md
└── token-economy/SKILL.md
```

Every skill follows the same shape: one folder, one `SKILL.md`, YAML frontmatter with `name` + `description` (some also declare `allowed-tools`).

---

## 🚀 Getting started

Clone once, then point your agent at the folders:

```bash
git clone https://github.com/InExSu/claude-skills.git /tmp/claude-skills
```

The skills are ordinary folders; anything that implements the [Agent Skills](https://agentskills.io) standard can consume them. The exact place to put them depends on the agent — check its documentation for the skills directory. Two examples with Claude Code:

```bash
# every project: personal skills
mkdir -p ~/.claude/skills
cp -R /tmp/claude-skills/*/ ~/.claude/skills/

# one project only
mkdir -p .claude/skills
cp -R /tmp/claude-skills/*/ .claude/skills/
```

No registration step and no configuration file: if a folder with a `SKILL.md` is present where the agent looks for skills, the skill is installed.

To install a single skill, copy just its folder — it is self-contained (its reference material and scripts, if any, live inside the same folder):

```bash
cp -R /tmp/claude-skills/tdd-bugfix ~/.claude/skills/
```

### Using a skill with another agent

- A skill is the folder itself: give your agent `SKILL.md` (or the folder containing it) — as a file it can read, or by copying the folder into the skills directory your agent uses, as in the examples above. The layout an agent needs is always the same: `SKILL.md` plus, for `drakonhub`, its `reference/`, `scripts/` and `templates/` subfolders.
- Two things an agent may handle differently, worth knowing upfront: pre-approved tools (`allowed-tools` in two of these skills is marked experimental in the standard and supported unevenly across agents), and how the agent matches the `description` — the exact phrasings that trigger a skill live in each skill's frontmatter (see the skill table or run `skills-ref to-prompt <skill-dir>`).

---

## 🛠 Usage

1. **Just ask.** Descriptions are written to trigger on real phrasing: *"fix this bug"*, *"исправь баг"*, *"why don't my tests catch anything"*, *"сделай диаграмму алгоритма"*, *"разбей функцию"*. The matching skill loads itself.
2. **Opt-in skills** never fire on their own — they require an explicit activation token: `@hungarian` for Hungarian notation, `@spaghetti` for the RWD decomposition.
3. **Combine deliberately.** `tdd-bugfix` + `quality-tests`, or `spaghetti-rwd` + `noosphere` + `rwd-chain`, form a coherent workflow: decompose, agree on state, wire the pipeline.
4. **Point at a file.** For `drakonhub`, referencing a concrete `.drakon` file plus *"check it"* or *"render it"* selects the right script.

### Commit helper (this repository's local convention)

The `gh.sh` helper in the repository root stages everything, commits and pushes in one call:

```bash
./gh.sh "add DRAKON skills"    # git add -A . && git commit -m "$1" && git push
```

Use it only from this repository — and double-check `git status` before running it, since it adds **all** changes including unreviewed ones.

### Automated checks

CI runs on every push and pull request ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)). The same commands work locally:

```bash
python3 .github/scripts/check_skills.py       # frontmatter, README catalog, relative links
cd drakonhub
for f in templates/*.drakon; do python3 scripts/drakon_tool.py check "$f"; done
python3 scripts/drakon_dsl.py roundtrip templates/minimal.drakon
python3 scripts/drakon_render.py svg templates/silhouette.drakon /tmp/out.svg
```

---

## 🤝 Contributing

Pull requests are welcome — from a typo fix to a whole new skill. Read **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full process: what makes a good `description`, the content guidelines, the checks to run before submitting, and what gets merged fastest. The pull request template asks for the problem the change solves and when the skill should **not** fire.

A new skill is just a folder with a `SKILL.md`:

```markdown
---
name: my-skill
description: >
  Precise trigger conditions — when to use it, and just as importantly when NOT to.
---

# My Skill

## Rules
...
```

Guidelines that keep this collection useful:

- **The description is the API.** Be explicit about triggers *and* exclusions; skills that fire everywhere are skills that fire nowhere.
- **Enforce, don't advise.** Prefer prohibitions ("never patch before a failing test exists") over gentle recommendations.
- **Show bad and good.** Before/after code pairs teach far better than abstractions.
- **State the scope.** Note the language or framework a skill applies to, so it does not leak into unrelated work.

---

## 📄 License

[MIT](LICENSE) © 2026 Michael Popov (InExSu)

In plain terms: use it, fork it, ship it inside your own product, modify it, sell it. The only obligations are keeping the copyright notice and license text along with the copy. There is no warranty.

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

Contributions are accepted under the same license — see [CONTRIBUTING.md](CONTRIBUTING.md).

<div align="center">

**[⬆ back to top](#-ai-agent-skills)** · [Русская версия](README.ru.md)

</div>
---