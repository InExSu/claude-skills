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
from sequence_format import (  # noqa: E402
    SeqError,
    check_sequence,
    sequence_to_mermaid,
)
from state_format import (  # noqa: E402
    StateError,
    check_state,
    state_to_mermaid,
)

# Геометрия в стиле DrakonHub: плотные иконки, вертикальный шкворень.
ICON_W, ICON_H = 196, 52
COL_PITCH, ROW_PITCH = 230, 78
MARGIN = 24
TITLE_H = 34

# Цвета иконок (fill, stroke) — как в экспорте редактора.
ICON_COLORS = {
    "branch": ("#eef3f8", "#8fa6bd"),
    "question": ("#fff7e6", "#d79b00"),
    "select": ("#fff7e6", "#d79b00"),
    "end": ("#3c4858", "#3c4858"),
    "comment": ("#fbfbf5", "#b8b89a"),
    "callout": ("#fbfbf5", "#b8b89a"),
    "duration": ("#fbfbf5", "#b8b89a"),
    "timer": ("#fffdbd", "#c9c98f"),
    "pause": ("#fffdbd", "#c9c98f"),
    "ctrlstart": ("#fffdbd", "#c9c98f"),
    "ctrlend": ("#fffdbd", "#c9c98f"),
}
DEFAULT_COLORS = ("#ffffff", "#4a5b6d")
LINE_COLOR = "#3c4858"
BACK_COLOR = "#b9c2cf"
TEXT_COLOR = "#22303d"


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
            elif kind == "parbegin":
                branches, chain, parend = self.par_branches(current)
                for index, par_id in enumerate(chain):
                    self.place(par_id, col + index)
                    self.reserve(col + index, row + 1)
                for index, branch in enumerate(branches):
                    self.walk(branch, col + index, stop=parend)
                deepest = max(self.cursors.get(col + index, row + 1)
                              for index in range(len(branches)))
                if isinstance(parend, str) and parend in self.items:
                    self.pos[parend] = (col, deepest)
                    self.cursors[col] = deepest + 1
                    self.max_col = max(self.max_col, col)
                    current = self.items[parend].get("one")
                else:
                    current = None
                last_row = deepest
            else:
                current = node.get("one")
        return last_row

    def par_branches(self, start):
        """Ветки цепочки parbegin, узлы цепочки и узел слияния parend."""
        branches, chain, tail = [], [], start
        while isinstance(tail, str) and tail in self.items \
                and self.items[tail].get("type") == "parbegin":
            chain.append(tail)
            branches.append(self.items[tail].get("one"))
            tail = self.items[tail].get("two")
        parend, node_id, seen = None, branches[0] if branches else None, set()
        while isinstance(node_id, str) and node_id in self.items and node_id not in seen:
            seen.add(node_id)
            if self.items[node_id].get("type") == "parend":
                parend = node_id
                break
            node_id = self.items[node_id].get("one")
        return branches, chain, parend


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


def node_center(col, row):
    """Центр иконки в пикселях (верхний отступ — под заголовок)."""
    cx = MARGIN + ICON_W // 2 + col * COL_PITCH
    cy = MARGIN + TITLE_H + ICON_H // 2 + row * ROW_PITCH
    return cx, cy


def node_box(col, row):
    """Прямоугольник иконки (left, top, right, bottom)."""
    cx, cy = node_center(col, row)
    return cx - ICON_W // 2, cy - ICON_H // 2, cx + ICON_W // 2, cy + ICON_H // 2


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
        cx, cy = node_center(col, row)
        print("%s [%s] (%d, %d) x=%d y=%d %s"
              % (node_id, node.get("type"), col, row, cx, cy, node.get("content", "")))


GLYPH = {
    "action": "rect",
    "question": "diamond",
    "select": "diamond",
    "case": "rect",
    "branch": "rect",
    "loopbegin": "stadium",
    "loopend": "stadium",
    "arrow-loop": "dot",
    "end": "stadium",
    "insertion": "rect",
    "address": "rect",
    "comment": "note",
    "callout": "note",
    "timer": "stadium",
    "pause": "stadium",
    "ctrlstart": "stadium",
    "ctrlend": "stadium",
    "simpleinput": "parallelogram",
    "simpleoutput": "parallelogram",
    "input": "parallelogram",
    "output": "parallelogram",
    "shelf": "rect",
    "process": "rect",
    "parbegin": "rect",
    "parend": "rect",
    "header": "rect",
    "params": "note",
    "drakon-image": "rect",
}


def node_shape(node):
    return GLYPH.get(node.get("type"), "rect")


def node_colors(node):
    return ICON_COLORS.get(node.get("type"), DEFAULT_COLORS)


def node_text(node):
    """Подпись иконки с учётом типа (end — без текста, но с подписью)."""
    kind = node.get("type")
    content = node.get("content", "")
    if kind == "end":
        return content or "Конец"
    return content


def wrap_text(text, width_chars=26):
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


def shape_svg(shape, left, top, right, bottom):
    """SVG-фигура иконки по её типу."""
    width, height = right - left, bottom - top
    cx, cy = (left + right) / 2.0, (top + bottom) / 2.0
    if shape == "diamond":
        hw, hh = width / 2.0, height / 2.0
        return ('<polygon points="%g,%g %g,%g %g,%g %g,%g"'
                % (cx, cy - hh, cx + hw, cy, cx, cy + hh, cx - hw, cy))
    if shape == "stadium":
        return ('<rect x="%g" y="%g" width="%g" height="%g" rx="%g"'
                % (left, top, width, height, height / 2.0))
    if shape == "parallelogram":
        skew = height * 0.35
        return ('<polygon points="%g,%g %g,%g %g,%g %g,%g"'
                % (left + skew, top, right, top, right - skew, bottom, left, bottom))
    if shape == "dot":
        return '<circle cx="%g" cy="%g" r="9"' % (cx, cy)
    return ('<rect x="%g" y="%g" width="%g" height="%g" rx="3"'
            % (left, top, width, height))


def text_svg(cx, cy, lines, max_lines=3):
    shown = lines[:max_lines]
    step = 15
    start = cy - (len(shown) - 1) * step / 2.0 + 4
    return "".join(
        '<text x="%g" y="%g" font-size="12" fill="%s" text-anchor="middle">%s</text>'
        % (cx, start + index * step, TEXT_COLOR, html.escape(line))
        for index, line in enumerate(shown))


def edge_path(points, back=False):
    """Ортогональная ломаная по точкам со стрелкой в конце."""
    color = BACK_COLOR if back else LINE_COLOR
    dash = ' stroke-dasharray="5 4"' if back else ""
    d = "M " + " L ".join("%g %g" % (x, y) for x, y in points)
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="1.6" '
            'marker-end="url(#arw)"%s/>' % (d, color, dash))


def render_svg(doc):
    items = items_of(doc)
    layout = build_layout(doc)
    cols, rows = grid_size(layout)
    channel_x = MARGIN + ICON_W + (cols - 1) * COL_PITCH + 24
    width = channel_x + MARGIN
    height = MARGIN * 2 + TITLE_H + rows * ROW_PITCH
    headers = [n for n in items.values() if n.get("type") == "header"]
    title = headers[0].get("content", "") if headers else ""

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'font-family="Arial, Helvetica, sans-serif">' % (width, height),
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<defs><marker id="arw" markerWidth="9" markerHeight="7" refX="8" refY="3.5" '
        'orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="%s"/></marker></defs>'
        % LINE_COLOR,
    ]
    if title:
        parts.append('<text x="%d" y="%d" font-size="15" font-weight="bold" '
                     'fill="%s">%s</text>'
                     % (MARGIN, MARGIN + 14, TEXT_COLOR, html.escape(title)))

    gap = 12.0

    def edge(from_id, to_id):
        if from_id not in layout.pos or to_id not in layout.pos:
            return
        fcol, frow = layout.pos[from_id]
        tcol, trow = layout.pos[to_id]
        fx1, fy1, fx2, fy2 = node_box(fcol, frow)
        tx1, ty1, tx2, ty2 = node_box(tcol, trow)
        fcx, fcy = (fx1 + fx2) / 2.0, (fy1 + fy2) / 2.0
        tcx, tcy = (tx1 + tx2) / 2.0, (ty1 + ty2) / 2.0
        if tcol == fcol:
            if trow == frow + 1:
                parts.append(edge_path([(fcx, fy2), (tcx, ty1)]))
            elif trow > frow:
                parts.append(edge_path(
                    [(fcx, fy2), (fcx, fy2 + gap), (channel_x, fy2 + gap),
                     (channel_x, ty1 - gap), (tcx, ty1 - gap), (tcx, ty1)]))
            else:
                parts.append(edge_path(
                    [(fcx, fy1), (fcx, fy1 - gap), (channel_x, fy1 - gap),
                     (channel_x, ty2 + gap), (tcx, ty2 + gap), (tcx, ty2)], back=True))
            return
        trunk = (tx1 - gap) if tcol > fcol else (tx2 + gap)
        if trow == frow:
            x_from = fx2 if tcol > fcol else fx1
            x_to = tx1 if tcol > fcol else tx2
            parts.append(edge_path([(x_from, fcy), (x_to, tcy)]))
        elif trow > frow:
            parts.append(edge_path(
                [(fcx, fy2), (fcx, fy2 + gap), (trunk, fy2 + gap),
                 (trunk, ty1), (tcx, ty1)]))
        else:
            parts.append(edge_path(
                [(fcx, fy1), (fcx, fy1 - gap), (trunk, fy1 - gap),
                 (trunk, ty2), (tcx, ty2)], back=True))

    for node_id, node in items.items():
        if node_id not in layout.pos:
            continue
        kind = node.get("type")
        if kind in ("comment", "callout", "duration", "header"):
            continue
        if kind == "question":
            yes, no = (node.get("one"), node.get("two")) if node.get("flag1") \
                else (node.get("two"), node.get("one"))
            edge(node_id, yes)
            edge(node_id, no)
        elif kind == "select":
            case = node.get("one")
            while isinstance(case, str) and case in items \
                    and items[case].get("type") == "case":
                edge(node_id, case)
                case = items[case].get("two")
        elif kind == "parbegin":
            edge(node_id, node.get("one"))
            if node.get("two"):
                edge(node_id, node.get("two"))
        else:
            edge(node_id, node.get("one"))

    # --- иконки (поверх рёбер) ---
    for node_id, (col, row) in sorted(layout.pos.items(),
                                      key=lambda pair: (pair[1][1], pair[1][0])):
        node = items[node_id]
        kind = node.get("type")
        if kind == "header":
            continue
        left, top, right, bottom = node_box(col, row)
        fill, stroke = node_colors(node)
        shape = node_shape(node)
        cx, cy = node_center(col, row)
        if kind == "comment" or kind == "callout" or kind == "duration":
            # примечание: компактная плашка слева, без текста в потоке
            lines = wrap_text(node.get("content", ""))
            parts.append(shape_svg(shape, left, top, right, bottom)
                         + ' fill="%s" stroke="%s" stroke-width="1.2" stroke-dasharray="4 3"/>'
                         % (fill, stroke))
            parts.append(text_svg(cx, cy, lines, max_lines=2))
            continue
        if kind == "end":
            parts.append(shape_svg(shape, left, top, right, bottom)
                         + ' fill="%s" stroke="%s" stroke-width="1.5"/>' % (fill, stroke))
            parts.append('<text x="%g" y="%g" font-size="13" fill="#ffffff" '
                         'text-anchor="middle">%s</text>'
                         % (cx, cy + 4, html.escape(node_text(node))))
            continue
        lines = wrap_text(node_text(node))
        parts.append(shape_svg(shape, left, top, right, bottom)
                     + ' fill="%s" stroke="%s" stroke-width="1.5"/>' % (fill, stroke))
        parts.append(text_svg(cx, cy, lines))
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
    return '%s["%s"]' % (mermaid_id(node_id), label)


def mermaid_transparent(node):
    """Ветка без подписи — служебная точка входа, в потоке прозрачна."""
    return node.get("type") == "branch" and not mermaid_escape(node.get("content", ""))


def mermaid_resolve(items, node_id):
    """Пройти сквозь комментарии и безымянные ветки к узлу потока."""
    seen = set()
    while isinstance(node_id, str) and node_id in items and node_id not in seen:
        seen.add(node_id)
        node = items[node_id]
        if node.get("type") == "comment" or mermaid_transparent(node):
            node_id = node.get("one")
            continue
        return node_id
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
        if node_id in declared or mermaid_transparent(node):
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
        if items[target].get("type") in ("header",):
            return
        arrow = " -- %s --> " % label if label else " --> "
        lines.append("  %s%s%s" % (mermaid_id(source), arrow, mermaid_id(target)))

    for node_id, node in items.items():
        kind = node.get("type")
        if kind in ("comment", "callout", "duration", "header"):
            continue
        if mermaid_transparent(node):
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

    # заголовок — в точку входа (первую ветку)
    if headers and headers[0].get("content"):
        entry = None
        for node_id, _ in sorted(branches, key=sort_key):
            entry = mermaid_resolve(items, node_id)
            if entry in declared:
                break
        if entry in declared:
            lines.append("  HEADER --> %s" % mermaid_id(entry))
    return "\n".join(lines)


def cmd_mermaid(src, dst):
    lowered = src.lower()
    if lowered.endswith(".seq") or lowered.endswith(".sm"):
        return cmd_mermaid_aux(src, dst)
    try:
        doc = load_doc(src)
    except ValueError as exc:
        print("ошибка: %s" % exc, file=sys.stderr)
        return 1
    if doc.get("type") != "drakon":
        print("ошибка: %s: mermaid для .drakon, .seq или .sm" % src, file=sys.stderr)
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


def cmd_mermaid_aux(src, dst):
    """Mermaid для вспомогательных форматов .seq (sequenceDiagram) и .sm (stateDiagram)."""
    try:
        with open(src, encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        print("ошибка: файл не найден: %s" % src, file=sys.stderr)
        return 1
    is_seq = src.lower().endswith(".seq")
    try:
        if is_seq:
            errors, _ = check_sequence(text, src)
        else:
            errors, _ = check_state(text, src)
        if errors:
            for message in errors:
                print("ошибка: %s" % message, file=sys.stderr)
            return 1
        out = sequence_to_mermaid(text) if is_seq else state_to_mermaid(text)
    except (SeqError, StateError) as exc:
        print("ошибка: %s: %s" % (src, exc), file=sys.stderr)
        return 1
    with open(dst, "w", encoding="utf-8") as handle:
        handle.write(out + "\n")
    kind = "sequenceDiagram" if is_seq else "stateDiagram-v2"
    print("OK: %s -> %s (%s)" % (src, dst, kind))
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
    print("  drakon_render.py mermaid <вход.drakon|.seq|.sm> <выход.mmd>")
    print("  drakon_render.py map     <вход.drakon>")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))