#!/usr/bin/env python3
"""sequence_format: диаграммы последовательности (.seq) -> Mermaid.

ДРАКОН не выражает линии жизни и порядок сообщений между участниками —
для этого отдельный вспомогательный формат. Цель — Mermaid `sequenceDiagram`
(его рендерит GitHub прямо в Markdown).

Грамматика (отступы необязательны, блоки — по ключевым словам):

    # Заголовок
    participant A [as Alias]
    participant B
    A -> B: запрос            сплошная стрелка
    B --> A: ответ            пунктирная стрелка
    alt условие
      ...
    else иначе
      ...
    end
    opt условие / loop условие / par
      ...
    end
    note over A: текст
    note right of A: текст
    note left of A: текст

Только стандартная библиотека.
"""

import re

MSG_RE = re.compile(r"^([^\s:]+)\s*(-->|->)\s*([^\s:]+)\s*:\s*(.+?)\s*$")
PART_RE = re.compile(r"^participant\s+([^\s]+)(?:\s+as\s+(.+?))?\s*$", re.IGNORECASE)
NOTE_RE = re.compile(r"^note\s+(over|right\s+of|left\s+of)\s+([^\s:]+)\s*:\s*(.+?)\s*$",
                     re.IGNORECASE)
BLOCK_OPEN = {"alt", "opt", "loop", "par", "critical", "break"}
BLOCK_LABEL = re.compile(r"^(alt|opt|loop|par|critical|break)\s+(.+?)\s*$", re.IGNORECASE)
ELSE_RE = re.compile(r"^else(?:\s+(.+?))?\s*$", re.IGNORECASE)


class SeqError(Exception):
    pass


def parse_seq(text):
    """Разобрать .seq. Вернуть (items, errors). items — список dict."""
    items, errors = [], []
    # стек открытых блоков: [{"keyword": ..., "has_else": bool}]
    stack = []
    participants = {}
    title_seen = False
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
        low = line.lower()
        if low == "end":
            if not stack:
                errors.append("строка %d: end без открытого блока" % lineno)
            else:
                frame = stack.pop()
                if frame["keyword"] == "alt" and not frame["has_else"]:
                    errors.append("строка %d: закрывается alt без else" % lineno)
                items.append({"kind": "end", "line": lineno})
            continue
        match = ELSE_RE.match(line)
        if match:
            if not stack or stack[-1]["keyword"] != "alt":
                errors.append("строка %d: else только внутри alt" % lineno)
            else:
                stack[-1]["has_else"] = True
            items.append({"kind": "else", "text": (match.group(1) or "").strip(),
                          "line": lineno})
            continue
        match = BLOCK_LABEL.match(line)
        if match:
            keyword = match.group(1).lower()
            stack.append({"keyword": keyword, "has_else": False})
            items.append({"kind": "block", "keyword": keyword,
                          "text": match.group(2).strip(), "line": lineno})
            continue
        if low in BLOCK_OPEN:
            errors.append("строка %d: у блока %s нет условия" % (lineno, line))
            continue
        match = PART_RE.match(line)
        if match:
            name = match.group(1)
            if name in participants:
                errors.append("строка %d: участник %s объявлен дважды" % (lineno, name))
            else:
                participants[name] = match.group(2)
                items.append({"kind": "participant", "name": name,
                              "alias": (match.group(2) or "").strip(), "line": lineno})
            continue
        match = NOTE_RE.match(line)
        if match:
            where = re.sub(r"\s+", " ", match.group(1).lower())
            target = match.group(2)
            if target not in participants:
                errors.append("строка %d: примечание ссылается на необъявленного "
                              "участника %s" % (lineno, target))
            items.append({"kind": "note", "where": where, "target": target,
                          "text": match.group(3).strip(), "line": lineno})
            continue
        match = MSG_RE.match(line)
        if match:
            sender, arrow, receiver, body = match.groups()
            for who in (sender, receiver):
                if who not in participants:
                    errors.append("строка %d: сообщение ссылается на необъявленного "
                                  "участника %s" % (lineno, who))
            items.append({"kind": "message", "from": sender, "to": receiver,
                          "dashed": arrow == "-->", "text": body.strip(),
                          "line": lineno})
            continue
        errors.append("строка %d: не разобрана: %r" % (lineno, line))
    for frame in stack:
        errors.append("блок %s не закрыт (нет end)" % frame["keyword"])
    if not any(i["kind"] == "message" for i in items):
        errors.append("нет ни одного сообщения")
    if not any(i["kind"] == "participant" for i in items):
        errors.append("нет ни одного участника (participant)")
    return items, errors


def check_sequence(text, label="диаграмма"):
    items, errors = parse_seq(text)
    return ["%s: %s" % (label, e) for e in errors], []


def _alias(name, alias):
    return "%s as %s" % (name, alias) if alias else name


def sequence_to_mermaid(text):
    """Преобразовать .seq в текст Mermaid. Бросает SeqError при ошибках."""
    items, errors = parse_seq(text)
    if errors:
        raise SeqError("; ".join(errors))
    lines = ["sequenceDiagram"]
    depth = 0
    for item in items:
        kind = item["kind"]
        pad = "    " * (depth + 1)
        if kind == "title":
            lines.append("%% " + item["text"])
        elif kind == "participant":
            lines.append("%sparticipant %s" % (pad, _alias(item["name"], item["alias"])))
        elif kind == "message":
            arrow = "-->>" if item["dashed"] else "->>"
            lines.append("%s%s%s%s: %s" % (pad, item["from"], arrow, item["to"],
                                           item["text"]))
        elif kind == "note":
            where = {"over": "over", "right of": "right of", "left of": "left of"}[
                item["where"]]
            lines.append("%sNote %s %s: %s" % (pad, where, item["target"], item["text"]))
        elif kind == "block":
            lines.append("%s%s %s" % (pad, item["keyword"], item["text"]))
            depth += 1
        elif kind == "else":
            lines.append("%selse%s" % ("    " * depth,
                                       " " + item["text"] if item["text"] else ""))
        elif kind == "end":
            depth = max(depth - 1, 0)
            lines.append("%send" % ("    " * (depth + 1)))
    return "\n".join(lines)


def sequence_to_dsl(text):
    """Канонический .seq (для read)."""
    items, errors = parse_seq(text)
    if errors:
        raise SeqError("; ".join(errors))
    out, depth = [], 0
    for item in items:
        kind = item["kind"]
        pad = "  " * depth
        if kind == "title":
            out.append("# " + item["text"])
        elif kind == "participant":
            out.append("%sparticipant %s" % (pad, _alias(item["name"], item["alias"])))
        elif kind == "message":
            arrow = "-->" if item["dashed"] else "->"
            out.append("%s%s %s %s: %s" % (pad, item["from"], arrow, item["to"],
                                           item["text"]))
        elif kind == "note":
            out.append("%snote %s %s: %s" % (pad, item["where"], item["target"],
                                             item["text"]))
        elif kind == "block":
            out.append("%s%s %s" % (pad, item["keyword"], item["text"]))
            depth += 1
        elif kind == "else":
            out.append("%selse%s" % ("  " * (depth - 1) if depth else "",
                                     " " + item["text"] if item["text"] else ""))
        elif kind == "end":
            depth = max(depth - 1, 0)
            out.append("%send" % ("  " * depth))
    return "\n".join(out)
