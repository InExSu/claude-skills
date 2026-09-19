# Security Policy

## What this repository is

This repository contains Markdown skill definitions and three Python scripts under `drakonhub/scripts/`. The scripts use the standard library only (`json`, `re`, `sys`, `textwrap`) and make **no network requests**. No credentials, tokens or personal data are handled anywhere in the repository.

That makes the realistic attack surface small, and it is worth being precise about it instead of copying a generic template.

## Supported versions

Only the current `master` branch is supported. There are no released versions and no maintenance branches.

## What is in scope

1. **Path handling in the scripts.** `drakon_dsl.py` accepts an output path, and `drakon_render.py` writes an SVG. Writing outside the path the user passed, or overwriting a file the user did not name, is a vulnerability.
2. **Input that never terminates.** A crafted `.drakon`, `.graf` or `.dsl` file that makes a script hang, recurse without bound, or exhaust memory. The scripts walk graph links (`one`, `two`, `case`, `branchId`) and a cycle in that graph must not be fatal.
3. **Crash on malformed input.** A stack trace with absolute paths, or a traceback where a diagnostic message is expected, is a bug worth reporting — `drakon_tool.py check` is supposed to report problems, not raise.
4. **Prompt injection through skill content.** Every `SKILL.md` is loaded into an agent's context, and `allowed-tools` pre-approves tools for the turn the skill runs. A skill that grants broad tool access, or instructions in a skill body that redirect an agent towards destructive actions, is a security issue rather than a style issue. Report it.
5. **Supply chain.** A skill or script that starts depending on a third-party package, or that downloads something at run time, contradicts what this repository promises.

## What is out of scope

- Diagrams themselves. A `.drakon` file describes someone's process; the content of an algorithm is not a security boundary.
- The absence of a feature, unless it leads to silent data loss.
- Anything requiring the attacker to already have write access to your machine or agent configuration.

## How to report

Use [GitHub's private vulnerability reporting](https://github.com/InExSu/claude-skills/security/advisories/new) for anything that could put other users at risk. If that is not available to you, email **InExSu@bk.ru**.

Please include:

- the exact command you ran, or the request you gave an agent;
- the input file, or a minimal reproduction of it;
- the output you got, the output you expected, and your OS and `python3 --version`.

Please do not open a public issue for items 1–3 until they are fixed, and give a reasonable window before disclosing.

## What to expect

This is a small project maintained on a best-effort basis. Typical handling:

| Stage | Target |
|---|---|
| Acknowledgement | within 7 days |
| Assessment and a decision on a fix | within 14 days |
| Fix and a public note, if warranted | as soon as a fix is ready |

If a report is declined, you will get the reasoning rather than silence.

## For contributors

If your change touches `drakonhub/scripts/`, keep the properties this policy relies on: standard library only, no network access, no writes outside the requested paths, and termination on cyclic input. The CI job described in [CONTRIBUTING.md](CONTRIBUTING.md) checks the mechanics, not the security properties — those are on the reviewer and on you.