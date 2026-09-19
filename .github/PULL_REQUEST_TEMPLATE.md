<!--
  Thanks for the pull request! Keep it short — a reviewer needs the problem
  and the scope, not a restatement of the diff.
  / Спасибо за pull request! Пишите кратко — ревьюеру нужны проблема и объём
  правки, а не пересказ диффа.
-->

## What this changes
<!-- Which skill or file, and what it does now that it did not before. -->
<!-- Какой скилл или файл, и что он теперь делает такого, чего не делал раньше. -->

## Problem it solves
<!-- The failure mode this prevents: what went wrong, or what a skill/user
     would do incorrectly without this change. -->
<!-- Какой режим отказа это предотвращает: что шло не так или что скилл
     сделал бы неправильно без этой правки. -->

## When it should NOT apply
<!-- Required for new skills and for changes to a skill's `description`.
     Explicit exclusions are what keep a skill from loading in every session. -->
<!-- Обязательно для новых скиллов и правок `description`. Явные исключения —
     то, что не даёт скиллу грузиться в каждой сессии. -->

## Checklist

- [ ] One skill / one concern per pull request
- [ ] `name` matches the folder name (lowercase, `-` separated)
- [ ] `description` states triggers **and** exclusions, in the phrasings people actually use
- [ ] Catalog tables and the `skills-N` badge updated in **both** `README.md` and `README.ru.md` (if a skill was added or renamed)
- [ ] No third-party dependencies added to `drakonhub` scripts
- [ ] No unrelated formatting churn, no `.DS_Store` / backups / build artifacts

## Checks (required for `drakonhub` changes)

<!-- Paste the output. All three must report OK. -->
```bash
cd drakonhub
python3 scripts/drakon_tool.py check templates/choice-and-loop.drakon
python3 scripts/drakon_dsl.py roundtrip templates/minimal.drakon
python3 scripts/drakon_render.py svg templates/silhouette.drakon /tmp/out.svg
```

```
<!-- output here / вывод здесь -->
```

## Notes for the reviewer
<!-- Optional: trade-offs, alternatives you rejected, anything you are unsure about. -->
<!-- Необязательно: компромиссы, отвергнутые варианты, сомнительные места. -->