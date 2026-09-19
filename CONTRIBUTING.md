# Contributing

Thanks for wanting to improve these skills. Contributions of any size are welcome: a fixed typo, a sharper trigger phrase, a new skill, or tooling for an existing one.

**Русская версия:** [CONTRIBUTING.ru.md](CONTRIBUTING.ru.md)

By submitting a pull request you agree that your contribution is licensed under the [MIT License](LICENSE) that covers this repository.

---

## What a skill is

A skill is a folder in the repository root containing a `SKILL.md` file:

```markdown
---
name: my-skill
description: >
  Precise trigger conditions — when to use this skill, and just as importantly when NOT to.
---

# My Skill

## Rules
...
```

Claude Code scans folders for `SKILL.md` and reads `name` + `description` from the YAML frontmatter. If the folder is present, the skill is installed — there is no registry and no configuration file.

Required frontmatter keys:

| Key | Rules |
|---|---|
| `name` | Must match the folder name, lowercase, words separated by `-`. |
| `description` | The most important part of a skill — see below. |
| `allowed-tools` | Optional. Restricts the tools a skill may use, e.g. `Read, Write, Edit`. |

## Writing a description that works

`description` is not documentation — it is the **matching rule** that decides whether the skill loads at all.

- Cover the real phrasings a person would type, in both English and Russian if the skill applies to both: *"fix this bug"*, *"исправь баг"*.
- State exclusions explicitly. `tdd-bugfix` says outright that it must not be used for brand-new features; `noosphere` says pure functions must stay independent of `ns`.
- Say "Do NOT apply without explicit activation" when the skill changes control flow or naming style rather than fixing a defect.
- Keep it a paragraph. Frontmatter is loaded into context for every session.

## Content guidelines

1. **Enforce, don't advise.** A rule that can be checked beats a recommendation. Compare "consider extracting the condition" with "a condition with more than three operators must be extracted".
2. **Show bad and good.** Before/after code pairs carry more weight than abstract principles.
3. **Scope it.** Name the language or framework the skill applies to, so it does not leak into unrelated work.
4. **Do not duplicate.** Check the [skill catalog](README.md#-skill-catalog) first; extending an existing skill is often better than adding a near-duplicate.
5. **Keep it actionable in one file.** A skill should be readable in a single sitting. If it needs depth, add a `reference/` folder, as `drakonhub` does.

## Tooling and scripts

`drakonhub` is the only skill with executable code.

- Python 3, **standard library only** — no third-party dependencies.
- Every script must keep its usage docstring in the module header, since `python3 scripts/<name>.py` with no arguments prints `__doc__`.
- Scripts must be deterministic and produce no side effects outside the paths the user passes.

Before opening a pull request, run the checks the repository already ships:

```bash
cd drakonhub
python3 scripts/drakon_tool.py check templates/choice-and-loop.drakon
python3 scripts/drakon_dsl.py roundtrip templates/minimal.drakon
python3 scripts/drakon_render.py svg templates/silhouette.drakon /tmp/out.svg
```

All three must report `OK`. `roundtrip` is the important one: it converts `.drakon` → DSL → `.drakon` and compares the graphs, so a change in the converter that breaks links is caught immediately.

## Pull request process

1. Fork the repository and create a branch: `git checkout -b add/my-skill`.
2. Make the change. One skill or one concern per pull request.
3. Update the [skill catalog](README.md#-skill-catalog) in **both** `README.md` and `README.ru.md` if you added or renamed a skill — the tables and the `skills-N` badge count live there.
4. Run the checks above when your change touches `drakonhub`, and paste the output into the pull request description.
5. Open the pull request. Describe **what problem the skill solves** and **when it should not fire** — that is what a reviewer needs most.

### What gets a pull request merged fastest

- A clear problem statement: which failure mode the skill prevents.
- A description built on real phrasing, not invented examples.
- No unrelated formatting churn in files you did not otherwise need to touch.

### What is likely to be rejected

- A skill that restates general good practice without a checkable rule.
- A skill whose description matches everything, so it loads in every session.
- Third-party dependencies in `drakonhub` scripts.
- Committing `.DS_Store`, editor backups, or build artifacts — see [.gitignore](.gitignore).

## Reporting a problem

For a bug in a script, open an issue with the exact command, the file it was run against, and the output you got versus the output you expected. For a skill that behaves unexpectedly, include the request you made and what the skill did instead.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE). Copyright over contributed material is held by its authors; the repository-wide license notice applies to the combined work.