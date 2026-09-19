#!/usr/bin/env python3
"""Repository consistency check for skill folders, their frontmatter and the READMEs.

Validates the rules of the Agent Skills specification that apply to this
repository, plus the documentation invariants the READMEs promise:

  * every skill folder contains a SKILL.md with YAML frontmatter;
  * `name` matches the folder name and is 1-64 chars of [a-z0-9-] with no
    leading, trailing or doubled hyphen;
  * `description` is present, non-empty and at most 1024 characters;
  * `license` is declared, so the license travels with a folder that is copied
    on its own;
  * both README files link to every skill and their `skills-N` badge matches
    the number of skills in the repository.

A SKILL.md longer than 500 lines is reported as a warning: the specification
recommends moving reference material into separate files.

Standard library only, no network access.

Usage:
    python3 .github/scripts/check_skills.py
"""

import os
import pathlib
import re
import sys

SKIP_DIRS = {".git", ".github"}
NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
BADGE_NUMBER = re.compile(r"badge/[^)?\s]*?-(\d+)-blue")
DESCRIPTION_LIMIT = 1024
SKILL_LINES_WARNING = 500
BLOCK_MARKERS = (">", "|", ">-", "|-", ">+", "|+")

problems = []
warnings = []


def report(path, message):
    problems.append(message)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::error file={path}::{message}")
    else:
        print(f"ERROR {path}: {message}")


def warn(path, message):
    warnings.append(message)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::warning file={path}::{message}")
    else:
        print(f"WARNING {path}: {message}")


def read_frontmatter(path):
    """Return the lines of the YAML frontmatter of a SKILL.md, or None."""
    lines = path.read_text(encoding="utf-8").split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index]
    return None


def field_value(frontmatter, key):
    """Return the value of a scalar field, the joined block value, or None."""
    for index, line in enumerate(frontmatter):
        match = re.match(rf"^{key}:\s*(.*)$", line)
        if match is None:
            continue

        value = match.group(1).strip()
        if value not in BLOCK_MARKERS:
            return value.strip("\"'")

        block = []
        for following in frontmatter[index + 1:]:
            if following.strip() and not following.startswith((" ", "\t")):
                break
            block.append(following.strip())
        return " ".join(part for part in block if part)
    return None


RELATIVE_LINK = re.compile(r"\]\((?!https?:|#|mailto:)([^)\s]+)\)")
FENCED_CODE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def strip_code(text):
    """Remove fenced and inline code, so examples are not read as real links."""
    return INLINE_CODE.sub("", FENCED_CODE.sub("", text))


def find_skills(root):
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and path.name not in SKIP_DIRS and not path.name.startswith(".")
    )


def check_markdown_links(root):
    """Every relative link in the repository documentation must resolve."""
    for document in sorted(root.rglob("*.md")):
        if ".git" in document.parts:
            continue
        text = document.read_text(encoding="utf-8")
        for target in RELATIVE_LINK.findall(strip_code(text)):
            path = (document.parent / target.split("#")[0]).resolve()
            if not path.exists():
                report(document, f"relative link does not resolve: {target}")


def check_skill(skill):
    skill_md = skill / "SKILL.md"
    if not skill_md.exists():
        report(skill, "folder has no SKILL.md")
        return

    frontmatter = read_frontmatter(skill_md)
    if frontmatter is None:
        report(skill_md, "no YAML frontmatter (the file must start with ---)")
        return

    name = field_value(frontmatter, "name")
    if name is None:
        report(skill_md, "frontmatter has no name")
    elif not NAME_PATTERN.fullmatch(name) or len(name) > 64:
        report(
            skill_md,
            f"name `{name}` is invalid: 1-64 characters of lowercase letters, digits "
            "and single hyphens only",
        )
    elif name != skill.name:
        report(skill_md, f"name `{name}` does not match folder `{skill.name}`")

    description = field_value(frontmatter, "description")
    if description is None:
        report(skill_md, "frontmatter has no description")
    elif not description:
        report(skill_md, "description is empty")
    elif len(description) > DESCRIPTION_LIMIT:
        report(
            skill_md,
            f"description is {len(description)} characters, the limit is {DESCRIPTION_LIMIT}",
        )

    if field_value(frontmatter, "license") is None:
        report(skill_md, "frontmatter has no license (expected `license: MIT`)")

    allowed_tools = field_value(frontmatter, "allowed-tools")
    if allowed_tools is not None:
        if "," in allowed_tools:
            report(
                skill_md,
                "allowed-tools must be space-separated per the specification "
                f"(found commas): {allowed_tools}",
            )
        if allowed_tools in ("", "[]"):
            report(skill_md, "allowed-tools is present but empty")

    line_count = len(skill_md.read_text(encoding="utf-8").split("\n"))
    if line_count > SKILL_LINES_WARNING:
        warn(
            skill_md,
            f"SKILL.md is {line_count} lines; the specification recommends keeping it "
            f"under {SKILL_LINES_WARNING} and moving detail into a reference file",
        )


def check_readme(readme, skills, expected_count):
    if not readme.exists():
        report(readme, "README is missing")
        return

    text = readme.read_text(encoding="utf-8")
    for skill in skills:
        if f"]({skill.name}/SKILL.md)" not in text:
            report(readme, f"catalog does not link to {skill.name}")

    numbers = {int(value) for value in BADGE_NUMBER.findall(text)}
    if not numbers:
        report(readme, "no `skills-N` badge found")
    elif numbers != {expected_count}:
        report(
            readme,
            f"badge says {sorted(numbers)}, but the repository has {expected_count} skills",
        )


def main():
    root = pathlib.Path(__file__).resolve().parents[2]
    skills = find_skills(root)

    for skill in skills:
        check_skill(skill)

    for readme_name in ("README.md", "README.ru.md"):
        check_readme(root / readme_name, skills, len(skills))

    check_markdown_links(root)

    for message in warnings:
        print(f"warning: {message}")

    if problems:
        print(f"\n{len(problems)} problem(s) found")
        return 1

    print(f"OK: {len(skills)} skills, frontmatter and README catalog are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())