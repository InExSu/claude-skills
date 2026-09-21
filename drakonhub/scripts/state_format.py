#!/usr/bin/env python3
"""state_format: машины состояний (.sm) -> Mermaid.

ДРАКОН описывает поток управления, а не состояния как сущности — для
жизненных циклов отдельный вспомогательный формат. Цель — Mermaid
`stateDiagram-v2` (рендерится GitHub прямо в Markdown).

Грамматика:

    # Заголовок
    [*] --> Created: создать
    Created --> Paid: оплата
    Paid --> Shipped: отгрузить
    Shipped --> [*]
    state Paid {
        [*] --> Pending
        Pending --> Confirmed: подтвердить
        Confirmed --> [*]
    }

Только стандартная библиотека.
"""

import re

TRANSITION_RE = re.compile(r"^(\[\*\]|[\w.\-]+)\s*-->\s*(\[\*\]|[\w.\-]+)"
                           r"(?:\s*:\s*(.+?))?\s*$")
STATE_RE = re.compile(r"^state\s+([\w.\-]+)\s*\{\s*$", re.IGNORECASE)
STATE_ALIAS_RE = re.compile(r"^state\s+\"(.+?)\"\s+as\s+([\w.\-]+)\s*$", re.IGNORECASE)


class StateError(Exception):
    pass


def parse_sm(text):
    """Разобрать .sm. Вернуть (items, errors)."""
    items, errors = [], []
    declared, used = set(), set()
    depth = 0
    title_seen = False
    initial_seen = False
    for lineno, raw in enumerate(text.split("\n"), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if title_seen or items:
                errors.append("строка %d: заголовок # только первой строкой" % lineno)
            else:
                items.append({"kind": "title", "text": line[1:].strip(), "line": lineno})
                title_seen = True
            continue
        if line == "}":
            if depth == 0:
                errors.append("строка %d: } без открытого state {" % lineno)
            else:
                depth -= 1
                items.append({"kind": "end", "line": lineno})
            continue
        match = STATE_ALIAS_RE.match(line)
        if match:
            alias = match.group(2)
            declared.add(alias)
            items.append({"kind": "state_alias", "name": alias,
                          "label": match.group(1), "line": lineno})
            continue
        match = STATE_RE.match(line)
        if match:
            name = match.group(1)
            declared.add(name)
            depth += 1
            items.append({"kind": "state", "name": name, "line": lineno})
            continue
        match = TRANSITION_RE.match(line)
        if match:
            source, target, label = match.groups()
            if source == "[*]":
                if depth == 0:
                    initial_seen = True
            else:
                used.add(source)
                if depth == 0:
                    declared.add(source)
            if target != "[*]":
                used.add(target)
            items.append({"kind": "transition", "from": source, "to": target,
                          "text": (label or "").strip(), "line": lineno})
            continue
        errors.append("строка %d: не разобрана: %r" % (lineno, line))
    if depth != 0:
        errors.append("state { не закрыт (нет })")
    if not any(i["kind"] == "transition" for i in items):
        errors.append("нет ни одного перехода")
    if not initial_seen:
        errors.append("нет начального состояния ([*] --> ...)")
    for name in sorted(used - declared):
        errors.append("переход ссылается на необъявленное состояние %s" % name)
    return items, errors


def check_state(text, label="диаграмма"):
    items, errors = parse_sm(text)
    return ["%s: %s" % (label, e) for e in errors], []


def state_to_mermaid(text):
    """Преобразовать .sm в текст Mermaid. Бросает StateError при ошибках."""
    items, errors = parse_sm(text)
    if errors:
        raise StateError("; ".join(errors))
    lines = ["stateDiagram-v2"]
    depth = 0
    for item in items:
        kind = item["kind"]
        pad = "    " * (depth + 1)
        if kind == "title":
            lines.append("%% " + item["text"])
        elif kind == "state_alias":
            lines.append('%sstate "%s" as %s' % (pad, item["label"], item["name"]))
        elif kind == "state":
            lines.append("%sstate %s {" % (pad, item["name"]))
            depth += 1
        elif kind == "transition":
            label = ": " + item["text"] if item["text"] else ""
            lines.append("%s%s --> %s%s" % (pad, item["from"], item["to"], label))
        elif kind == "end":
            depth = max(depth - 1, 0)
            lines.append("%s}" % ("    " * (depth + 1)))
    return "\n".join(lines)


def state_to_dsl(text):
    """Канонический .sm (для read)."""
    items, errors = parse_sm(text)
    if errors:
        raise StateError("; ".join(errors))
    out, depth = [], 0
    for item in items:
        kind = item["kind"]
        pad = "  " * depth
        if kind == "title":
            out.append("# " + item["text"])
        elif kind == "state_alias":
            out.append('%sstate "%s" as %s' % (pad, item["label"], item["name"]))
        elif kind == "state":
            out.append("%sstate %s {" % (pad, item["name"]))
            depth += 1
        elif kind == "transition":
            label = ": " + item["text"] if item["text"] else ""
            out.append("%s%s --> %s%s" % (pad, item["from"], item["to"], label))
        elif kind == "end":
            depth = max(depth - 1, 0)
            out.append("%s}" % ("  " * depth))
    return "\n".join(out)
