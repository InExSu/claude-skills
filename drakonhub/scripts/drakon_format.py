#!/usr/bin/env python3
"""drakon_format: общее ядро скилла drakonhub.

Загрузка, проверка, построение и сериализация диаграмм ДРАКОН (.drakon)
и ментальных карт (.graf) редактора DrakonHub (Степан Митькин).

Только стандартная библиотека Python 3 (json, re, sys, html, textwrap).

Соглашения формата (проверены по drakon_examples и исходникам редактора):
  * Корень: {"type": "drakon", "items": {id: item}, "style": "..."}.
  * Ветка 0 (branchId 0) — главная; силуэт — ветки 0..N-1.
  * question: flag1=1 означает one="да", two="нет" (и наоборот при flag1=0).
  * select.one — первый case; case.two — следующий case (у последнего нет).
  * loopbegin/loopend — скобки цикла; явное ребро назад — только arrow-loop.
  * comment висит на узле (comment.one), в поток не входит.
  * duration живёт в action.side; callout и header — вне потока.
"""

import json
import re

# --------------------------------------------------------------------------
# Типы иконок и их связи
# --------------------------------------------------------------------------

ICON_TYPES = {
    "action", "question", "select", "case", "branch", "header", "end",
    "comment", "loopbegin", "loopend", "arrow-loop", "duration", "callout",
    "insertion", "address", "simpleinput", "simpleoutput",
    "input", "output", "shelf", "process",
    # таймеры и критические секции (движок DrakonHub)
    "timer", "pause", "ctrlstart", "ctrlend",
    # параллельные процессы
    "junction", "parbegin", "parend",
    # служебные и mind-map
    "params", "drakon-image", "idea", "ridea", "conclusion",
}

# Поля-ссылки на другие узлы (обязательные). "side" — опциональная ссылка action.
LINK_FIELDS = {
    "action": ("one",),
    "question": ("one", "two"),
    "select": ("one",),
    "case": ("one",),
    "branch": ("one",),
    "comment": ("one",),
    "loopbegin": ("one",),
    "loopend": ("one",),
    "arrow-loop": ("one",),
    "insertion": ("one",),
    "address": ("one",),
    "simpleinput": ("one",),
    "simpleoutput": ("one",),
    "input": ("one",),
    "output": ("one",),
    "shelf": ("one",),
    "process": ("one",),
    "timer": ("one",),
    "pause": ("one",),
    "ctrlstart": ("one",),
    "ctrlend": ("one",),
    "parbegin": ("one",),
    "parend": ("one",),
}

# Узлы, участвующие в потоке управления (достижимость от веток, выход в end).
FLOW_TYPES = set(ICON_TYPES) - {
    "header", "comment", "callout", "duration", "params", "drakon-image",
    "idea", "ridea", "conclusion",
}

# Узлы без исходящих рёбер.
SINK_TYPES = {"header", "end", "callout", "duration", "params", "drakon-image",
              "idea", "ridea", "conclusion"}

# Слова, запрещённые в вопросах по правилам ДРАКОН (вопрос — атомарный).
QUESTION_FORBIDDEN = (
    (re.compile(r"\bи\b", re.IGNORECASE), '"и"'),
    (re.compile(r"\bили\b", re.IGNORECASE), '"или"'),
    (re.compile(r"\bне\b|\bнет\b|\bnever\b|\bnot\b", re.IGNORECASE), 'отрицание'),
    (re.compile(r"\band\b|\bor\b", re.IGNORECASE), '"and/or"'),
)


# --------------------------------------------------------------------------
# Загрузка / сохранение
# --------------------------------------------------------------------------

def load_doc(path):
    """Прочитать .drakon / .graf файл, вернуть dict. Бросает ValueError."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise ValueError("файл не найден: %s" % path)
    except json.JSONDecodeError as exc:
        raise ValueError("невалидный JSON в %s: %s" % (path, exc))
    if not isinstance(data, dict):
        raise ValueError("%s: корень должен быть объектом" % path)
    return data


def save_doc(doc, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=4)
        handle.write("\n")


def items_of(doc):
    items = doc.get("items")
    return items if isinstance(items, dict) else {}


def flow_successors(items, node_id):
    """Исходящие рёбра потока для узла (one/two; comment прозрачен)."""
    node = items.get(node_id)
    if node is None:
        return []
    if node.get("type") == "comment":
        target = node.get("one")
        return [target] if isinstance(target, str) and target in items else []
    if node.get("type") in SINK_TYPES:
        return []
    out = []
    for field in ("one", "two"):
        target = node.get(field)
        if isinstance(target, str) and target in items:
            out.append(target)
    return out


# --------------------------------------------------------------------------
# check: структурная проверка диаграммы
# --------------------------------------------------------------------------

def check_drakon(doc, label="диаграмма"):
    """Вернуть (errors, remarks) — списки строк."""
    errors, remarks = [], []
    if not isinstance(doc, dict):
        return ["%s: корень не объект" % label], []
    if doc.get("type") != "drakon":
        errors.append('%s: type должен быть "drakon", а не %r' % (label, doc.get("type")))
    items = items_of(doc)
    if not items:
        return errors + ["%s: пустые или отсутствующие items" % label], remarks

    style = doc.get("style", "")
    if not isinstance(style, str):
        errors.append("%s: style должен быть строкой" % label)
    elif style.strip():
        try:
            parsed = json.loads(style)
            if not isinstance(parsed, dict):
                errors.append("%s: style должен быть JSON-объектом в строке" % label)
        except ValueError:
            errors.append("%s: style не парсится как JSON" % label)

    for node_id, node in items.items():
        if not isinstance(node, dict):
            errors.append("%s: узел %s не объект" % (label, node_id))
            continue
        kind = node.get("type")
        if kind not in ICON_TYPES:
            errors.append("%s: узел %s: неизвестный тип %r" % (label, node_id, kind))
            continue
        content = node.get("content", "")
        if not isinstance(content, str):
            errors.append("%s: узел %s: content должен быть строкой" % (label, node_id))
        node_style = node.get("style", "")
        if not isinstance(node_style, str):
            errors.append("%s: узел %s: style должен быть строкой" % (label, node_id))
        for field in LINK_FIELDS.get(kind, ()):
            target = node.get(field)
            if target is None:
                errors.append("%s: узел %s (%s): нет обязательного поля %s"
                              % (label, node_id, kind, field))
            elif not isinstance(target, str) or target not in items:
                errors.append("%s: узел %s (%s): %s указывает на несуществующий узел %r"
                              % (label, node_id, kind, field, target))
        side = node.get("side")
        if side is not None:
            if kind != "action":
                errors.append("%s: узел %s (%s): side бывает только у action"
                              % (label, node_id, kind))
            elif not isinstance(side, str) or side not in items:
                errors.append("%s: узел %s: side указывает на несуществующий узел %r"
                              % (label, node_id, side))
            elif items[side].get("type") != "duration":
                errors.append("%s: узел %s: side должен указывать на duration" % (label, node_id))
        if kind == "branch":
            branch_id = node.get("branchId")
            if not isinstance(branch_id, int) or isinstance(branch_id, bool):
                errors.append("%s: ветка %s: branchId должен быть целым числом" % (label, node_id))
        if kind == "callout":
            for field in ("left", "top", "width", "height", "px", "py", "zIndex"):
                value = node.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append("%s: выноска %s: поле %s должно быть числом"
                                  % (label, node_id, field))

    headers = [i for i, n in items.items() if isinstance(n, dict) and n.get("type") == "header"]
    ends = [i for i, n in items.items() if isinstance(n, dict) and n.get("type") == "end"]
    branches = [(i, n) for i, n in items.items()
                if isinstance(n, dict) and n.get("type") == "branch"]
    if len(headers) != 1:
        errors.append("%s: должен быть ровно один header, найдено %d" % (label, len(headers)))
    if len(ends) != 1:
        errors.append("%s: должен быть ровно один end, найдено %d" % (label, len(ends)))
    if not branches:
        errors.append("%s: нет ни одной ветки (branch)" % label)
    else:
        ids = sorted(n.get("branchId") for _, n in branches
                     if isinstance(n.get("branchId"), int) and not isinstance(n.get("branchId"), bool))
        if len(ids) != len(branches):
            pass  # уже сообщено выше
        elif len(set(ids)) != len(ids):
            errors.append("%s: дублирующиеся branchId" % label)
        elif ids and ids[0] == 0 and ids != list(range(len(ids))):
            errors.append("%s: разрывы в нумерации веток: %s" % (label, ids))
        elif ids and ids[0] != 0:
            remarks.append("%s: силуэт без главной ветки 0 (нативный стиль редактора)" % label)

    # select -> case, case -> case
    for node_id, node in items.items():
        if not isinstance(node, dict):
            continue
        if node.get("type") == "select":
            first = node.get("one")
            if isinstance(first, str) and first in items:
                if items[first].get("type") != "case":
                    errors.append("%s: select %s должен указывать на case" % (label, node_id))
        if node.get("type") == "case":
            nxt = node.get("two")
            if isinstance(nxt, str) and nxt in items:
                if items[nxt].get("type") != "case":
                    errors.append("%s: case %s: two должен вести на case" % (label, node_id))

    # duration обязан быть привязан ровно к одному action.side
    referenced = set()
    for node_id, node in items.items():
        if isinstance(node, dict) and node.get("type") == "action" and isinstance(node.get("side"), str):
            referenced.add(node["side"])
    for node_id, node in items.items():
        if isinstance(node, dict) and node.get("type") == "duration" and node_id not in referenced:
            errors.append("%s: duration %s ни к чему не привязан (нет action.side)" % (label, node_id))

    # arrow-loop без текста
    for node_id, node in items.items():
        if isinstance(node, dict) and node.get("type") == "arrow-loop":
            if node.get("content", "") not in ("", None):
                errors.append("%s: arrow-loop %s должен быть без текста" % (label, node_id))

    if errors:
        return errors, remarks

    # --- анализ потока ---
    flow_ids = [i for i, n in items.items()
                if isinstance(n, dict) and n.get("type") in FLOW_TYPES]
    entries = [i for i, _ in branches]
    reachable = set()
    stack = list(entries)
    while stack:
        current = stack.pop()
        if current in reachable or current not in items:
            continue
        reachable.add(current)
        stack.extend(flow_successors(items, current))
    for node_id in flow_ids:
        if node_id not in reachable:
            errors.append("%s: узел %s недостижим ни из одной ветки" % (label, node_id))

    end_id = ends[0] if ends else None
    if end_id is not None:
        through = [i for i, n in items.items()
                   if isinstance(n, dict)
                   and (n.get("type") in FLOW_TYPES or n.get("type") == "comment")]
        can_finish = {end_id}
        changed = True
        while changed:
            changed = False
            for node_id in through:
                if node_id not in can_finish and \
                        any(s in can_finish for s in flow_successors(items, node_id)):
                    can_finish.add(node_id)
                    changed = True
        for node_id in flow_ids:
            if node_id not in can_finish:
                errors.append("%s: из узла %s нет пути в end" % (label, node_id))

    # циклы допустимы только через явные линейные иконки:
    # arrow-loop (переход), loopbegin/loopend (скобки цикла)
    def find_bad_cycle():
        color = {}
        trail = []
        allowed = {"arrow-loop", "loopbegin", "loopend"}

        def visit(node_id):
            color[node_id] = 1
            trail.append(node_id)
            for succ in flow_successors(items, node_id):
                if items[succ].get("type") not in FLOW_TYPES \
                        and items[succ].get("type") != "comment":
                    continue
                if color.get(succ) == 1:
                    cycle = trail[trail.index(succ):] + [succ]
                    natural = items[succ].get("type") == "branch"
                    if not natural and not any(
                            items[c].get("type") in allowed for c in cycle):
                        return cycle
                elif color.get(succ) is None:
                    found = visit(succ)
                    if found:
                        return found
            trail.pop()
            color[node_id] = 2
            return None

        for node_id in flow_ids:
            if color.get(node_id) is None:
                found = visit(node_id)
                if found:
                    return found
        return None

    bad_cycle = find_bad_cycle()
    if bad_cycle:
        errors.append("%s: неструктурированный цикл без arrow-loop: %s"
                      % (label, " -> ".join(bad_cycle)))

    # --- языковые правила ДРАКОН ---
    for node_id, node in items.items():
        if not isinstance(node, dict):
            continue
        content = node.get("content", "")
        if not isinstance(content, str) or not content.strip():
            continue
        if node.get("type") == "question":
            for pattern, name in QUESTION_FORBIDDEN:
                if pattern.search(content):
                    remarks.append("%s: вопрос %s содержит %s: %r"
                                   % (label, node_id, name, content))
                    break
        if node.get("type") == "action" and content.strip().endswith((".", ":", ";")):
            remarks.append("%s: действие %s лучше без знака в конце: %r"
                           % (label, node_id, content))
    return errors, remarks


def check_graf(doc, label="карта"):
    errors = []
    if not isinstance(doc, dict):
        return ["%s: корень не объект" % label]
    if doc.get("type") != "graf":
        errors.append('%s: type должен быть "graf"' % label)
    items = items_of(doc)
    if not items:
        return errors + ["%s: пустые items" % label]
    for node_id, node in items.items():
        if not isinstance(node, dict):
            errors.append("%s: узел %s не объект" % (label, node_id))
            continue
        if node.get("type") not in ("idea", "ridea", "conclusion"):
            errors.append("%s: узел %s: неизвестный тип %r" % (label, node_id, node.get("type")))
        if not isinstance(node.get("content", ""), str):
            errors.append("%s: узел %s: content должен быть строкой" % (label, node_id))
        parent = node.get("parent")
        if parent != "root" and (not isinstance(parent, str) or parent not in items):
            errors.append("%s: узел %s: parent указывает на несуществующий узел" % (label, node_id))
    # ацикличность
    for node_id in items:
        seen, current = set(), node_id
        while isinstance(current, str) and current in items and current != "root":
            if current in seen:
                errors.append("%s: цикл в parent у узла %s" % (label, node_id))
                break
            seen.add(current)
            current = items[current].get("parent")
    return errors


# --------------------------------------------------------------------------
# DSL: компактный текст вместо ручного JSON
#
#   # Заголовок            заголовок диаграммы (первая строка)
#   > Комментарий          иконка-комментарий к следующему узлу
#   * Выноска              свободная выноска
#   @ Ветка                ветка силуэта (без @ — одна неявная ветка 0)
#   Действие               action
#   ? Вопрос?              question
#     да: / нет:           ветки вопроса (также yes:/no:)
#   $ Выбор                select
#     = Вариант            case (пустой = вариант по умолчанию)
#   ~ Цикл                 loopbegin...loopend (тело — вложенные строки)
#   ^                      стрелка-переход; внутри ~ — возврат к началу цикла
#   % Длительность         side-подпись действия (ребёнок действия)
#   + Вставка / & Адрес    insertion / address
# --------------------------------------------------------------------------

class DslError(Exception):
    pass


MARKER_STARTS = set("#>*@$=~?%+&^<>!")


def escape_content(text):
    """Экранировать контент для DSL: бэкслэши, переводы строк, ведущий маркер."""
    escaped = text.replace("\\", "\\\\").replace("\n", "\\n")
    if escaped[:1] in MARKER_STARTS:
        escaped = "\\" + escaped
    return escaped


def unescape_content(text):
    """Обратное преобразование escape_content."""
    if len(text) > 1 and text[0] == "\\" and text[1] in MARKER_STARTS:
        text = text[1:]
    out, i = [], 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in ("\\", "n"):
            out.append("\\" if text[i + 1] == "\\" else "\n")
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


class Line:
    __slots__ = ("kind", "text", "children", "lineno")

    def __init__(self, kind, text):
        self.kind = kind
        self.text = text
        self.children = []


def parse_dsl(text):
    """Разобрать DSL-текст в дерево Line. Бросает DslError."""
    raw = []
    for lineno, source in enumerate(text.split("\n"), 1):
        if not source.strip():
            continue
        expanded = source.expandtabs(4)
        indent = len(expanded) - len(expanded.lstrip(" "))
        body = expanded.strip()
        if body.startswith("#"):
            kind, content = "title", body[1:].strip()
        elif body.startswith(">"):
            kind, content = "comment", body[1:].strip()
        elif body.startswith("*"):
            kind, content = "callout", body[1:].strip()
        elif body.startswith("@"):
            kind, content = "branch", body[1:].strip()
        elif body.startswith("$"):
            kind, content = "select", body[1:].strip()
        elif body.startswith("="):
            kind, content = "case", body[1:].strip()
        elif body.startswith("~"):
            kind, content = "loop", body[1:].strip()
        elif body.startswith("?"):
            kind, content = "question", body[1:].strip()
        elif body.startswith("%"):
            kind, content = "duration", body[1:].strip()
        elif body.startswith("<<"):
            kind, content = "simpleinput", body[2:].strip()
        elif body.startswith(">>"):
            kind, content = "simpleoutput", body[2:].strip()
        elif body.startswith("+"):
            kind, content = "insertion", body[1:].strip()
        elif body.startswith("&"):
            kind, content = "address", body[1:].strip()
        elif body.startswith("!pause "):
            kind, content = "pause", body[7:].strip()
        elif body.startswith("!timer "):
            kind, content = "timer", body[7:].strip()
        elif body.startswith("!endctrl "):
            kind, content = "ctrlend", body[9:].strip()
        elif body.startswith("!ctrl "):
            kind, content = "ctrlstart", body[6:].strip()
        elif body == "!par" or body.startswith("!par "):
            kind, content = "par", body[4:].strip()
        elif body.rstrip(":").strip().lower() in ("ветка", "branch") and body.rstrip().endswith(":"):
            kind, content = "parbranch", ""
        elif body in ("^", "^ "):
            kind, content = "jump", ""
        elif body.rstrip(":").strip().lower() in ("да", "нет", "yes", "no") and body.rstrip().endswith(":"):
            word = body.rstrip(":").strip().lower()
            kind = "yes" if word in ("да", "yes") else "no"
            rest = body.split(":", 1)[1].strip()
            if rest:
                raise DslError("строка %d: после %s: не должно быть текста" % (lineno, body))
            content = ""
        else:
            kind, content = "action", body
        if kind not in ("yes", "no", "jump"):
            content = unescape_content(content)
        raw.append((indent, kind, content, lineno))

    roots = []
    stack = [(-1, roots)]
    for indent, kind, content, lineno in raw:
        if kind == "title" and (roots or indent != 0):
            raise DslError("строка %d: заголовок # только первой строкой" % lineno)
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise DslError("строка %d: неверный отступ" % lineno)
        node = Line(kind, content)
        node.lineno = lineno
        stack[-1][1].append(node)
        if kind != "title":
            stack.append((indent, node.children))
    return roots


class Builder:
    def __init__(self):
        self.items = {}
        self.counter = 0
        self.loop_stack = []

    def new_id(self):
        self.counter += 1
        return str(self.counter)

    def add(self, kind, **fields):
        node_id = self.new_id()
        node = {"type": kind, "style": ""}
        node.update(fields)
        self.items[node_id] = node
        return node_id


def build_diagram(roots):
    """Построить .drakon dict из дерева Line. Бросает DslError."""
    builder = Builder()
    end_id = builder.add("end")
    title = ""
    top = list(roots)
    if top and top[0].kind == "title":
        title = top[0].text
        top = top[1:]
    header_id = builder.add("header")
    if title:
        builder.items[header_id]["content"] = title
    doc = {"type": "drakon", "items": builder.items, "style": ""}
    if title:
        doc["name"] = title

    for node in top:
        if node.kind == "callout":
            builder.add("callout", content=node.text,
                        left=600, top=40, width=160, height=40, px=-60, py=20, zIndex=1)

    branches = [n for n in top if n.kind == "branch"]
    if branches:
        if any(n.kind not in ("branch", "callout", "comment") for n in top):
            raise DslError("верхний уровень: либо ветки @, либо общий поток без них")
        pending = []
        for node in top:
            if node.kind == "comment":
                pending.append(node)
            elif node.kind == "branch":
                entry = build_block(builder, node.children, end_id)
                branch_id = builder.add("branch", branchId=0,
                                        content=node.text, one=entry or end_id)
                for comment in pending:
                    builder.add("comment", content=comment.text, one=branch_id)
                pending = []
        for comment in pending:
            builder.add("comment", content=comment.text, one=end_id)
    else:
        implicit = Line("branch", "")
        implicit.children = [n for n in top if n.kind != "callout"]
        entry = build_block(builder, implicit.children, end_id)
        builder.add("branch", branchId=0, one=entry or end_id)

    # перенумеровать ветки по порядку создания
    branch_ids = [i for i, n in builder.items.items() if n["type"] == "branch"]
    for number, node_id in enumerate(branch_ids):
        builder.items[node_id]["branchId"] = number
    return doc


def build_block(builder, lines, cont):
    """Построить цепочку; вернуть entry (или None для пустой). Справа налево."""
    nxt = cont
    for line in reversed(lines):
        nxt = build_construct(builder, line, nxt)
    return nxt


def build_construct(builder, line, cont):
    kind, text = line.kind, line.text
    if kind == "comment":
        return builder.add("comment", content=text, one=cont)
    if kind == "callout":
        builder.add("callout", content=text,
                    left=600, top=40, width=160, height=40, px=-60, py=20, zIndex=1)
        return cont
    if kind == "action":
        side = None
        for child in line.children:
            if child.kind != "duration":
                raise DslError("у действия только %%-подпись, а не %r" % child.kind)
            side = builder.add("duration", content=child.text)
        fields = {"content": text, "one": cont}
        if side is not None:
            fields["side"] = side
        return builder.add("action", **fields)
    if kind in ("insertion", "address", "simpleinput", "simpleoutput",
                 "input", "output", "shelf", "process",
                 "timer", "pause", "ctrlstart", "ctrlend"):
        if line.children:
            raise DslError("%r не имеет вложенных строк" % kind)
        native = {"simpleinput": "simpleinput", "simpleoutput": "simpleoutput",
                  "input": "input", "output": "output"}.get(kind, kind)
        return builder.add(native, content=text, one=cont)
    if kind == "par":
        parend = builder.add("parend", one=cont)
        branches = []
        for child in line.children:
            if child.kind != "parbranch":
                raise DslError("у параллельного блока только ветка: подблоки")
            entry = build_block(builder, child.children, parend) or parend
            branches.append(entry)
        if len(branches) < 2:
            raise DslError("у параллельного блока минимум две ветки")
        prev = None
        for index in reversed(range(len(branches))):
            fields = {"one": branches[index]}
            if index == 0 and text:
                fields["content"] = text
            if prev is not None:
                fields["two"] = prev
            prev = builder.add("parbegin", **fields)
        return prev
    if kind == "branch":
        entry = build_block(builder, line.children, cont)
        return builder.add("branch", branchId=0, content=text, one=entry or cont)
    if kind == "question":
        yes_lines, no_lines = [], []
        for child in line.children:
            if child.kind == "yes":
                yes_lines.extend(child.children)
            elif child.kind == "no":
                no_lines.extend(child.children)
            else:
                raise DslError("у вопроса только да:/нет: блоки")
        yes_entry = build_block(builder, yes_lines, cont)
        no_entry = build_block(builder, no_lines, cont)
        return builder.add("question", flag1=1, content=text,
                           one=yes_entry or cont, two=no_entry or cont)
    if kind == "select":
        cases = [c for c in line.children if c.kind == "case"]
        if not cases or len(cases) != len(line.children):
            raise DslError("у выбора только = варианты")
        first_id, prev_id = None, None
        for case in cases:
            body = build_block(builder, case.children, cont)
            case_id = builder.add("case", content=case.text, one=body or cont)
            if prev_id is not None:
                builder.items[prev_id]["two"] = case_id
            if first_id is None:
                first_id = case_id
            prev_id = case_id
        return builder.add("select", content=text, one=first_id)
    if kind == "loop":
        loop_end = builder.add("loopend", one=cont)
        loop_begin = builder.add("loopbegin", content=text, one=loop_end)
        builder.loop_stack.append((loop_end, loop_begin))
        body = build_block(builder, line.children, loop_end)
        builder.items[loop_begin]["one"] = body or loop_end
        builder.loop_stack.pop()
        return loop_begin
    if kind == "jump":
        if line.children:
            target = builder.loop_stack[-1][1] if builder.loop_stack else cont
            entry = build_block(builder, line.children, target)
            return builder.add("arrow-loop", one=entry or target)
        target = cont
        if builder.loop_stack and target == builder.loop_stack[-1][0]:
            target = builder.loop_stack[-1][1]
        return builder.add("arrow-loop", one=target)
    if kind == "duration":
        raise DslError("% вне действия запрещён")
    raise DslError("неизвестная конструкция: %r" % kind)


# --------------------------------------------------------------------------
# Сериализатор: диаграмма -> DSL (каноническая форма)
# --------------------------------------------------------------------------

def compute_ipdom(items, flow_ids, end_id):
    """Непосредственные пост-доминаторы (итеративный data-flow, графы маленькие)."""
    nodes = [n for n in flow_ids if n in items]
    universe = set(nodes) | {end_id}
    pdom = {n: set(universe) for n in nodes}
    if end_id in items:
        pdom[end_id] = {end_id}
    succs = {n: [s for s in flow_successors(items, n) if s in universe] for n in nodes}
    if end_id in items:
        succs[end_id] = []
    for _ in range(len(nodes) + 2):
        changed = False
        for node in nodes:
            if node == end_id:
                continue
            if succs[node]:
                merged = set(universe)
                for succ in succs[node]:
                    merged &= pdom.get(succ, set(universe))
            else:
                merged = {end_id} if end_id in items else set()
            new = {node} | merged
            if new != pdom[node]:
                pdom[node] = new
                changed = True
        if not changed:
            break
    ipdom = {}
    for node in nodes:
        strict = pdom[node] - {node}
        best = None
        for cand in strict:
            if all(other == cand or cand in pdom.get(other, set()) for other in strict):
                best = cand
                break
        ipdom[node] = best
    return ipdom


class Serializer:
    def __init__(self, items):
        self.items = items
        self.lines = []
        self.emitted = set()
        self.comment_map = {}
        for node_id, node in items.items():
            if node.get("type") == "comment":
                target = node.get("one")
                if isinstance(target, str):
                    self.comment_map.setdefault(target, []).append(node_id)
        flow_ids = [i for i, n in items.items() if n.get("type") in FLOW_TYPES]
        ends = [i for i, n in items.items() if n.get("type") == "end"]
        self.ipdom = compute_ipdom(items, flow_ids, ends[0] if ends else None)

    def emit(self, indent, text):
        self.lines.append("  " * indent + text)

    def emit_comments(self, target, indent):
        for comment_id in sorted(self.comment_map.get(target, [])):
            self.emit_comments(comment_id, indent)
            content = self.items[comment_id].get("content", "")
            self.emit(indent, "> " + escape_content(content))
            self.emitted.add(comment_id)

    def question_sides(self, node):
        if node.get("flag1"):
            return node.get("one"), node.get("two")
        return node.get("two"), node.get("one")

    def ser_seq(self, start, stop, indent):
        current = start
        while current and current != stop and current not in self.emitted:
            node = self.items.get(current)
            if node is None:
                return
            kind = node.get("type")
            if kind == "end":
                return
            if kind in ("comment", "callout", "duration", "header"):
                current = node.get("one")
                continue
            if kind == "loopend":
                current = node.get("one")
                continue
            self.emitted.add(current)
            self.emit_comments(current, indent)
            content = node.get("content", "")
            if kind in ("action", "insertion", "address", "simpleinput",
                          "simpleoutput", "input", "output", "shelf", "process",
                          "timer", "pause", "ctrlstart", "ctrlend"):
                prefix = {"action": "", "insertion": "+ ", "address": "& ",
                          "simpleinput": "<< ", "simpleoutput": ">> ",
                          "input": "<< ", "output": ">> ",
                          "timer": "!timer ", "pause": "!pause ",
                          "ctrlstart": "!ctrl ", "ctrlend": "!endctrl "}.get(kind, "")
                self.emit(indent, prefix + escape_content(content))
                side = node.get("side")
                if isinstance(side, str) and side in self.items:
                    self.emitted.add(side)
                    self.emit(indent + 1, "% " + escape_content(
                        self.items[side].get("content", "")))
                current = node.get("one")
            elif kind == "parbegin":
                self.emit(indent, "!par " + escape_content(content))
                # цепочка parbegin: ветки — их one; слияние — parend, куда ведут ветки
                par_nodes, branches, tail = [], [], current
                while isinstance(tail, str) and tail in self.items \
                        and self.items[tail].get("type") == "parbegin" \
                        and tail not in par_nodes:
                    par_nodes.append(tail)
                    branches.append(self.items[tail].get("one"))
                    tail = self.items[tail].get("two")
                conv = None
                for entry in branches:
                    target = self.items.get(entry, {}).get("one") if entry else None
                    if isinstance(target, str) and target in self.items \
                            and self.items[target].get("type") == "parend":
                        conv = target
                        break
                if conv is None:
                    conv = self.ipdom.get(current)
                for par_id in par_nodes:
                    self.emitted.add(par_id)
                for entry in branches:
                    self.emit(indent + 1, "ветка:")
                    self.ser_subtree(entry, conv, indent + 2)
                if isinstance(conv, str) and conv in self.items:
                    self.emitted.add(conv)
                current = conv
            elif kind == "parend":
                current = node.get("one")
            elif kind == "arrow-loop":
                self.emit(indent, "^")
                current = node.get("one")
            elif kind == "branch":
                self.emit(indent, "@ " + escape_content(content))
                current = node.get("one")
                indent += 1
            elif kind == "question":
                self.emit(indent, "? " + escape_content(content))
                yes_id, no_id = self.question_sides(node)
                conv = self.ipdom.get(current)
                self.emit(indent + 1, "да:")
                self.ser_subtree(yes_id, conv, indent + 2)
                self.emit(indent + 1, "нет:")
                self.ser_subtree(no_id, conv, indent + 2)
                current = conv
            elif kind == "select":
                self.emit(indent, "$ " + escape_content(content))
                conv = self.ipdom.get(current)
                case_id = node.get("one")
                while isinstance(case_id, str) and case_id in self.items \
                        and self.items[case_id].get("type") == "case" \
                        and case_id not in self.emitted:
                    self.emitted.add(case_id)
                    self.emit_comments(case_id, indent + 1)
                    self.emit(indent + 1, "= " + escape_content(
                        self.items[case_id].get("content", "")))
                    self.ser_subtree(self.items[case_id].get("one"), conv, indent + 2)
                    case_id = self.items[case_id].get("two")
                current = conv
            elif kind == "loopbegin":
                self.emit(indent, "~ " + escape_content(content))
                conv = self.ipdom.get(current)
                self.ser_subtree(node.get("one"), conv, indent + 1)
                current = conv
            else:
                current = node.get("one")

    def ser_subtree(self, start, stop, indent):
        if start and start != stop:
            self.ser_seq(start, stop, indent)


def encounter_order(items, branch_ids):
    """Порядок веток для сериализации: сначала источники, потом обход one-first.

    Источник — ветка, в которую нет прыжков из других веток (обычно главная).
    Порядок детерминирован структурой графа и контентом, поэтому одинаков
    для исходной и пересобранной диаграмм.
    """
    reaching = {}
    for root in branch_ids:
        seen, found, stack = set(), set(), [root]
        while stack:
            current = stack.pop()
            if current in seen or current not in items:
                continue
            seen.add(current)
            if items[current].get("type") == "branch" and current != root:
                found.add(current)
            stack.extend(flow_successors(items, current))
        reaching[root] = found

    def skey(branch_id):
        return (items[branch_id].get("content", ""), branch_id)

    sources = [b for b in branch_ids
               if not any(b in reaching[o] for o in branch_ids if o != b)]
    roots = sorted(sources, key=skey) + \
        sorted([b for b in branch_ids if b not in sources], key=skey)
    order, seen = [], set()
    for root in roots:
        stack = [root]
        while stack:
            current = stack.pop()
            if current in seen or current not in items:
                continue
            seen.add(current)
            if items[current].get("type") == "branch":
                order.append(current)
            stack.extend(reversed(flow_successors(items, current)))
    return order


def diagram_to_dsl(doc):
    """Диаграмма -> канонический DSL-текст. Бросает DslError."""
    items = items_of(doc)
    if not items:
        raise DslError("пустые items")
    headers = [n for n in items.values() if n.get("type") == "header"]
    branches = [(i, n) for i, n in items.items() if n.get("type") == "branch"]
    if len(headers) != 1:
        raise DslError("нужен ровно один header")
    if not branches:
        raise DslError("нет ни одной ветки")
    ser = Serializer(items)
    title = doc.get("name") or headers[0].get("content", "")
    if title:
        ser.emit(0, "# " + escape_content(title))
    ordered = encounter_order(items, [i for i, _ in branches])
    single_implicit = len(ordered) == 1 and not items[ordered[0]].get("content", "")
    for node_id in ordered:
        branch = items[node_id]
        if node_id in ser.emitted:
            continue
        if single_implicit:
            base = 1
        else:
            ser.emit_comments(node_id, 0)
            ser.emit(0, "@ " + branch.get("content", ""))
            base = 1
        ser.emitted.add(node_id)
        if single_implicit:
            ser.emit_comments(node_id, 1)
        ser.ser_seq(branch.get("one"), None, base)
    for node_id in sorted(ser.items):
        node = ser.items[node_id]
        if node.get("type") == "callout" and node_id not in ser.emitted:
            ser.emitted.add(node_id)
            ser.emit(0, "* " + escape_content(node.get("content", "")))
    return "\n".join(ser.lines)


def graf_to_outline(doc):
    """Ментальная карта -> план текстом."""
    items = items_of(doc)
    children = {}
    for node_id, node in items.items():
        parent = node.get("parent", "root")
        children.setdefault(parent, []).append(node_id)
    for key in children:
        children[key].sort(key=lambda i: (items[i].get("ordinal", 0), i))
    lines = []

    def visit(node_id, depth):
        node = items[node_id]
        lines.append("  " * depth + "- " + node.get("content", ""))
        for child in children.get(node_id, []):
            visit(child, depth + 1)

    for root in children.get("root", []):
        visit(root, 0)
    return "\n".join(lines)