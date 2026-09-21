#!/usr/bin/env python3
"""drakon_render: раскладка силуэта в сетку, SVG и Mermaid.

Использование (из папки скилла):
  python3 scripts/drakon_render.py svg diagram.drakon out.svg      # картинка
  python3 scripts/drakon_render.py map diagram.drakon              # карта координат
  python3 scripts/drakon_render.py mermaid diagram.drakon out.mmd  # диаграмма Mermaid

Правила раскладки: поток сверху вниз, главная ветка — слева,
ответвления (нет-ветки вопросов, варианты выбора, тела циклов) — вправо.
«Чем правее, тем хуже».

Только стандартная библиотека.
"""

import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drakon_format import (  # noqa: E402
    DslError,
    FLOW_TYPES,
    check_drakon,
    compute_ipdom,
    items_of,
    load_doc,
)

CELL_W, CELL_H = 220, 110
BOX_W, BOX_H = 180, 64
MARGIN = 30


class Layout:
    def __init__(self, items):
        self.items = items
        self.pos = {}      # id -> (col, row)
        self.cursors = {}  # col -> следующая свободная строка
        self.max_col = -1
        self.ipdom = {}

    def place(self, node_id, col):
        row = self.cursors.get(col, 0)
        self.pos[node_id] = (col, row)
        self.cursors[col] = row + 1
        self.max_col = max(self.max_col, col)
        return row

    def reserve(self, col, row):
        self.cursors[col] = max(self.cursors.get(col, 0), row)

    def walk(self, node_id, col, stop=None):
        """Идти по one вниз; ответвления — вправо. Возвращает последний ряд."""
        current, last_row = node_id, 0
        while current and current != stop and current not in self.pos:
            node = self.items.get(current)
            if node is None:
                break
            kind = node.get("type")
            if kind == "end":
                row = self.place(current, col)
                return row
            if kind in ("comment", "callout", "duration", "header"):
                current = node.get("one")
                continue
            if kind == "loopend":
                row = self.place(current, col)
                current = node.get("one")
                last_row = row
                continue
            if kind == "branch":
                current = node.get("one")
                continue
            row = self.place(current, col)
            last_row = row
            if kind in ("action", "insertion", "address", "arrow-loop"):
                current = node.get("one")
            elif kind == "question":
                conv = self.ipdom.get(current)
                if node.get("flag1"):
                    main, side = node.get("one"), node.get("two")
                else:
                    main, side = node.get("two"), node.get("one")
                self.reserve(col + 1, row + 1)
                self.walk(side, col + 1, stop=conv)
                current = main
            elif kind == "select":
                conv = self.ipdom.get(current)
                case = node.get("one")
                self.reserve(col + 1, row + 1)
                while isinstance(case, str) and case in self.items \
                        and self.items[case].get("type") == "case" \
                        and case not in self.pos:
                    self.place(case, col + 1)
                    self.reserve(col + 2, self.cursors[col + 1])
                    self.walk(self.items[case].get("one"), col + 2, stop=conv)
                    case = self.items[case].get("two")
                current = conv
            elif kind == "loopbegin":
                conv = self.ipdom.get(current)
                last_row = self.walk(node.get("one"), col, stop=conv)
                current = conv
            else:
                current = node.get("one")
        return last_row


def build_layout(doc):
    items = items_of(doc)
    ends = [i for i, n in items.items() if n.get("type") == "end"]
    flow_ids = [i for i, n in items.items() if n.get("type") in FLOW_TYPES]
    layout = Layout(items)
    layout.ipdom = compute_ipdom(items, flow_ids, ends[0] if ends else None)
    branches = [(i, n) for i, n in items.items() if n.get("type") == "branch"]

    def key(pair):
        bid = pair[1].get("branchId")
        return (bid if isinstance(bid, int) and not isinstance(bid, bool) else 10 ** 9,
                pair[0])

    col = 0
    for node_id, branch in sorted(branches, key=key):
        if node_id in layout.pos:
            continue
        layout.walk(branch.get("one"), col)
        col = layout.max_col + 1
    for node_id, node in items.items():
        if node.get("type") in FLOW_TYPES and node.get("type") != "end" \
                and node_id not in layout.pos:
            layout.walk(node_id, col)
            col = layout.max_col + 1
    return layout


def grid_size(layout):
    cols = layout.max_col + 1
    rows = 0
    for _, row in layout.pos.values():
        rows = max(rows, row + 1)
    return max(cols, 1), max(rows, 1)


def render_map(doc):
    """Текстовая карта координат: удобна агенту."""
    items = items_of(doc)
    layout = build_layout(doc)
    headers = [n for n in items.values() if n.get("type") == "header"]
    if headers and headers[0].get("content"):
        print("# " + headers[0]["content"])
    for node_id in sorted(layout.pos, key=lambda i: (layout.pos[i][1], layout.pos[i][0])):
        node = items[node_id]
        col, row = layout.pos[node_id]
        x = MARGIN + col * CELL_W + CELL_W // 2
        y = MARGIN + row * CELL_H + CELL_H // 2
        print("%s [%s] (%d, %d) x=%d y=%d %s"
              % (node_id, node.get("type"), col, row, x, y, node.get("content", "")))


GLYPH = {
    "action": ("rect", None),
    "question": ("diamond", "?"),
    "select": ("diamond", "$"),
    "case": ("rect", "= "),
    "loopbegin": ("rect", "~ "),
    "loopend": ("rect", "○ "),
    "arrow-loop": ("dot", "^"),
    "end": ("round", "END"),
    "insertion": ("rect", "+ "),
    "address": ("rect", "& "),
}


def node_shape(node):
    kind = node.get("type")
    return GLYPH.get(kind, ("rect", None))


def wrap_text(text, width_chars=22):
    words, lines, current = (text or "").split(), [], ""
    for word in words:
        if len(word) > width_chars:
            if current:
                lines.append(current)
                current = ""
            while len(word) > width_chars:
                lines.append(word[:width_chars])
                word = word[width_chars:]
            current = word
        elif len(current) + 1 + len(word) <= width_chars:
            current = (current + " " + word).strip()
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def render_svg(doc):
    items = items_of(doc)
    layout = build_layout(doc)
    cols, rows = grid_size(layout)
    width = MARGIN * 2 + cols * CELL_W
    height = MARGIN * 2 + rows * CELL_H
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">' % (width, height),
             '<rect width="100%%" height="100%%" fill="#ffffff"/>']
    headers = [n for n in items.values() if n.get("type") == "header"]
    if headers and headers[0].get("content"):
        parts.append('<text x="%d" y="22" font-size="16" font-weight="bold" '
                     'font-family="sans-serif">%s</text>'
                     % (MARGIN, html.escape(headers[0]["content"])))
    edges = []
    for node_id, (col, row) in layout.pos.items():
        node = items[node_id]
        kind = node.get("type")
        cx = MARGIN + col * CELL_W + CELL_W // 2
        cy = MARGIN + row * CELL_H + CELL_H // 2
        target = node.get("one")
        if isinstance(target, str) and target in layout.pos:
            tcol, trow = layout.pos[target]
            tx = MARGIN + tcol * CELL_W + CELL_W // 2
            ty = MARGIN + trow * CELL_H + CELL_H // 2
            x1, y1 = cx, cy + BOX_H // 2
            if trow > row or (trow == row and tcol != col):
                edges.append('<line x1="%d" y1="%d" x2="%d" y2="%d" '
                             'stroke="#000" stroke-width="2"/>' % (x1, y1, tx, ty - BOX_H // 2))
            else:
                edges.append('<line x1="%d" y1="%d" x2="%d" y2="%d" '
                             'stroke="#800" stroke-width="2" stroke-dasharray="6,4"/>' % (
                                 cx + BOX_W // 2, cy, tx + BOX_W // 2, ty))
        if kind == "question":
            for field in ("one", "two"):
                target = node.get(field)
                if isinstance(target, str) and target in layout.pos and field == "two":
                    tcol, trow = layout.pos[target]
                    tx = MARGIN + tcol * CELL_W + CELL_W // 2
                    ty = MARGIN + trow * CELL_H + CELL_H // 2
                    edges.append('<line x1="%d" y1="%d" x2="%d" y2="%d" '
                                 'stroke="#000" stroke-width="2"/>' % (
                                     cx + BOX_W // 2, cy, tx, ty - BOX_H // 2))
        if kind == "select":
            case = node.get("one")
            while isinstance(case, str) and case in layout.pos \
                    and items[case].get("type") == "case":
                tcol, trow = layout.pos[case]
                tx = MARGIN + tcol * CELL_W + CELL_W // 2
                ty = MARGIN + trow * CELL_H + CELL_H // 2
                edges.append('<line x1="%d" y1="%d" x2="%d" y2="%d" '
                             'stroke="#000" stroke-width="2"/>' % (
                                 cx + BOX_W // 2, cy, tx, ty - BOX_H // 2))
                case = items[case].get("two")
    parts.extend(edges)
    for node_id, (col, row) in layout.pos.items():
        node = items[node_id]
        kind = node.get("type")
        shape, mark = node_shape(node)
        cx = MARGIN + col * CELL_W + CELL_W // 2
        cy = MARGIN + row * CELL_H + CELL_H // 2
        raw = (mark or "") + node.get("content", "")
        text_lines = wrap_text(raw)
        shown = text_lines[:3]
        texts = "".join(
            '<text x="%d" y="%d" font-size="12" text-anchor="middle" '
            'font-family="sans-serif">%s</text>' % (
                cx, cy - (len(shown) - 1) * 8 + index * 16, html.escape(line))
            for index, line in enumerate(shown))
        if shape == "dot":
            parts.append('<circle cx="%d" cy="%d" r="10" fill="#fff" '
                         'stroke="#000" stroke-width="2"/>%s' % (cx, cy, texts))
        elif shape == "diamond":
            hw, hh = BOX_W // 2 + 8, BOX_H // 2 + 6
            parts.append('<polygon points="%d,%d %d,%d %d,%d %d,%d" fill="#fff" '
                         'stroke="#000" stroke-width="2"/>%s' % (
                             cx, cy - hh, cx + hw, cy, cx, cy + hh, cx - hw, cy, texts))
        elif shape == "round":
            parts.append('<rect x="%d" y="%d" width="%d" height="%d" rx="20" fill="#fff" '
                         'stroke="#000" stroke-width="2"/>%s' % (
                             cx - BOX_W // 2, cy - BOX_H // 2, BOX_W, BOX_H, texts))
        else:
            parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#fff" '
                         'stroke="#000" stroke-width="2"/>%s' % (
                             cx - BOX_W // 2, cy - BOX_H // 2, BOX_W, BOX_H, texts))
    parts.append("</svg>")
    return "\n".join(parts)


def mermaid_id(node_id):
    """Стабильный безопасный идентификатор для Mermaid."""
    return "n" + re.sub(r"[^0-9A-Za-z_]", "_", str(node_id))


def mermaid_escape(text):
    """Экранировать текст для подписи узла Mermaid."""
    text = (text or "").replace("\\", "\\\\").replace('"', "#quot;")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def mermaid_node(node_id, node):
    """Строка объявления узла Mermaid: id + форма + подпись."""
    kind = node.get("type")
    label = mermaid_escape(node.get("content", ""))
    if kind == "end":
        return '%s(["%s"])' % (mermaid_id(node_id), label or "КОНЕЦ")
    if kind == "question":
        return '%s{"%s"}' % (mermaid_id(node_id), label)
    if kind == "select":
        return '%s{"%s"}' % (mermaid_id(node_id), label)
    if kind == "case":
        return '%s["= %s"]' % (mermaid_id(node_id), label)
    if kind == "loopbegin":
        return '%s(["~ %s"])' % (mermaid_id(node_id), label)
    if kind == "loopend":
        return '%s(["~ /цикл"])' % mermaid_id(node_id)
    if kind == "arrow-loop":
        return '%s(("^"))' % mermaid_id(node_id)
    if kind == "insertion":
        return '%s["+ %s"]' % (mermaid_id(node_id), label)
    if kind == "address":
        return '%s["&amp; %s"]' % (mermaid_id(node_id), label)
    if kind in ("simpleinput", "input"):
        return '%s[/"%s"/]' % (mermaid_id(node_id), label)
    if kind in ("simpleoutput", "output"):
        return '%s[\\"%s"\\]' % (mermaid_id(node_id), label)
    if kind == "branch" and not label:
        return '%s["Ветка"]' % mermaid_id(node_id)
    return '%s["%s"]' % (mermaid_id(node_id), label)


def mermaid_resolve(items, node_id):
    """Пройти сквозь цепочки комментариев к первому узлу потока."""
    seen = set()
    while isinstance(node_id, str) and node_id in items and node_id not in seen:
        seen.add(node_id)
        if items[node_id].get("type") != "comment":
            return node_id
        node_id = items[node_id].get("one")
    return node_id


def render_mermaid(doc):
    """Диаграмма ДРАКОН -> текст Mermaid (flowchart TD)."""
    items = items_of(doc)
    lines = ["flowchart TD"]
    headers = [n for n in items.values() if n.get("type") == "header"]
    if headers and headers[0].get("content"):
        lines.append('  HEADER(["%s"])' % mermaid_escape(headers[0]["content"]))
    nodes = [(i, n) for i, n in items.items()
             if n.get("type") in FLOW_TYPES]
    branches = [(i, n) for i, n in items.items() if n.get("type") == "branch"]
    branch_ids = {i for i, _ in branches}

    def sort_key(pair):
        bid = pair[1].get("branchId")
        return (bid if isinstance(bid, int) and not isinstance(bid, bool) else 10 ** 9,
                pair[0])

    declared = set()

    def declare(node_id, node):
        if node_id in declared:
            return
        declared.add(node_id)
        lines.append("  " + mermaid_node(node_id, node))

    # узлы: сначала ветки, затем остальные
    for node_id, node in sorted(branches, key=sort_key):
        declare(node_id, node)
    for node_id, node in nodes:
        if node_id not in branch_ids:
            declare(node_id, node)

    def edge(source, target, label=None):
        target = mermaid_resolve(items, target)
        if not isinstance(target, str) or target not in items:
            return
        if target in ("header",):
            return
        arrow = " -- %s --> " % label if label else " --> "
        lines.append("  %s%s%s" % (mermaid_id(source), arrow, mermaid_id(target)))

    for node_id, node in items.items():
        kind = node.get("type")
        if kind in ("comment", "callout", "duration", "header"):
            continue
        if kind == "question":
            yes_id, no_id = (node.get("one"), node.get("two")) if node.get("flag1") \
                else (node.get("two"), node.get("one"))
            edge(node_id, yes_id, "Да")
            edge(node_id, no_id, "Нет")
        elif kind == "select":
            case = node.get("one")
            while isinstance(case, str) and case in items \
                    and items[case].get("type") == "case":
                edge(node_id, case)
                case = items[case].get("two")
        else:
            edge(node_id, node.get("one"))
    return "\n".join(lines)


def cmd_mermaid(src, dst):
    try:
        doc = load_doc(src)
    except ValueError as exc:
        print("ошибка: %s" % exc, file=sys.stderr)
        return 1
    if doc.get("type") != "drakon":
        print("ошибка: %s: mermaid только для .drakon" % src, file=sys.stderr)
        return 1
    errors, _ = check_drakon(doc, src)
    if errors:
        for message in errors:
            print("ошибка: %s" % message, file=sys.stderr)
        return 1
    text = render_mermaid(doc)
    with open(dst, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    print("OK: %s -> %s (%d иконок)"
          % (src, dst, len(doc["items"])))
    return 0


def cmd_svg(src, dst):
    try:
        doc = load_doc(src)
    except ValueError as exc:
        print("ошибка: %s" % exc, file=sys.stderr)
        return 1
    if doc.get("type") != "drakon":
        print("ошибка: %s: svg только для .drakon" % src, file=sys.stderr)
        return 1
    errors, _ = check_drakon(doc, src)
    if errors:
        for message in errors:
            print("ошибка: %s" % message, file=sys.stderr)
        return 1
    try:
        svg = render_svg(doc)
    except DslError as exc:
        print("ошибка: %s: %s" % (src, exc), file=sys.stderr)
        return 1
    with open(dst, "w", encoding="utf-8") as handle:
        handle.write(svg + "\n")
    cols, rows = grid_size(build_layout(doc))
    print("OK: %s -> %s (%dx%d клеток, %d иконок)"
          % (src, dst, cols, rows, len(doc["items"])))
    return 0


def cmd_map(src):
    try:
        doc = load_doc(src)
    except ValueError as exc:
        print("ошибка: %s" % exc, file=sys.stderr)
        return 1
    if doc.get("type") != "drakon":
        print("ошибка: %s: map только для .drakon" % src, file=sys.stderr)
        return 1
    errors, _ = check_drakon(doc, src)
    if errors:
        for message in errors:
            print("ошибка: %s" % message, file=sys.stderr)
        return 1
    try:
        render_map(doc)
    except DslError as exc:
        print("ошибка: %s: %s" % (src, exc), file=sys.stderr)
        return 1
    cols, rows = grid_size(build_layout(doc))
    print("OK: %s (%dx%d клеток, %d иконок)"
          % (src, cols, rows, len(doc["items"])), file=sys.stderr)
    return 0


def main(argv):
    if len(argv) == 4 and argv[1] == "svg":
        return cmd_svg(argv[2], argv[3])
    if len(argv) == 4 and argv[1] == "mermaid":
        return cmd_mermaid(argv[2], argv[3])
    if len(argv) == 3 and argv[1] == "map":
        return cmd_map(argv[2])
    print("использование:")
    print("  drakon_render.py svg     <вход.drakon> <выход.svg>")
    print("  drakon_render.py mermaid <вход.drakon> <выход.mmd>")
    print("  drakon_render.py map     <вход.drakon>")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))