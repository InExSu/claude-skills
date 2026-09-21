#!/bin/bash
# Link every skill into the agent's skills directory (~/.claude/skills).
#
# Two sources, both symlinked so updates are picked up automatically:
#   ~/.agents/skills   third-party skills from the community `skills` CLI
#                      (Orca, find-skills) — refreshed by `orca skills update`
#   this repository    its own skills, discovered next to this script
#
# Re-run after adding a skill or after a fresh clone. Idempotent.
# Override the target with SKILLS_TARGET.
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
TARGET="${SKILLS_TARGET:-$HOME/.claude/skills}"
COMMUNITY="$HOME/.agents/skills"

mkdir -p "$TARGET"

link() {  # link <source-dir> <name>
  ln -sfn "$1" "$TARGET/$2"
}

# 1. Community skills (auto-updated by the `skills` CLI / `orca skills update`).
if [ -d "$COMMUNITY" ]; then
  for dir in "$COMMUNITY"/*/; do
    [ -f "$dir/SKILL.md" ] || continue
    link "$COMMUNITY/$(basename "$dir")" "$(basename "$dir")"
  done
fi

# 2. This repository's own skills.
for dir in "$REPO"/*/; do
  name="$(basename "$dir")"
  case "$name" in .*) continue ;; esac
  [ -f "$dir/SKILL.md" ] || continue
  link "$REPO/$name" "$name"
done

echo "Linked into $TARGET:"
ls -l "$TARGET" | grep '^l' | sed 's/.* \([^ ]*\) -> \(.*\)/  \1 -> \2/'
