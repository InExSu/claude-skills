#!/usr/bin/env python3
"""Раскладка .drakon по правилам силуэта и два вида вывода.

    python3 drakon_render.py svg <in.drakon> <out.svg>   # картинка для человека
    python3 drakon_render.py map <in.drakon>             # карта координат для агента

Движок один: считает сетку (ветка -> колонка, иконка -> строка), потом
отрисовывает её либо в SVG, либо в текст.

Раскладка:
  * заголовки всех веток - на строке 0, слева направо по branchId;
  * вертел ветки идёт строго вниз по её колонке;
  * правая ветка вопроса (two) уходит вправо от поддерева one;
  * переход на другую ветку - пунктирная стрелка к её заголовку,
    внутрь чужой ветки не рекурсируем (иначе бесконечный цикл).

Два вида "посмотреть":
  * svg - чтобы человек увидел схему без DrakonHub;
  * map - таблица координат: агент может проверить правила DRAKON
    (старт слева сверху, ветвление вправо, нет пересечений) простым чтением.
"""

import json
import sys
import textwrap

CELL_W = 230      # ширина колонки, px
CELL_H = 78       # высота строки, px
PAD = 24
BOX_W = CELL_W - 34
BOX_H = CELL_H - 26

QUESTION = "question"
TERMINALS = ("branch", "end")


def strip_tags(text):
    out, in_tag = [], False
    for ch in text:
        if ch == "<":
            in_tag = True
        elif ch == ">":
            in_tag = False
        elif not in_tag:
            out.append(ch)
    return "".join(out)


def plain(item):
    content = item.get("content") or item.get("text") or ""
    return " ".join(strip_tags(str(content)).split())


# --------------------------------------------------------------- раскладка

class Layout:
    def __init__(self, diagram):
        self.items = diagram.get("items", {})
        self.nodes = []          # (iid, col, row, item)
        self.links = []          # (from_iid, to_iid, kind) kind: one|two|ref
        self.cols = 0
        self.rows = 0
        self.owner = {}          # iid -> branchId, чья это клетка
        self.cur_branch = None
        self.pending_loopend = []   # (loopend_id, col, row) циклов, тело которых рисуем

    # -- размеры поддерева -------------------------------------------

    def measure(self, iid, path):
        """(ширина в колонках, высота в строках) для цепочки от iid."""
        if not iid or iid in path:
            return (0, 0)
        item = self.items.get(iid)
        if not isinstance(item, dict):
            return (0, 0)
        typ = item.get("type")
        if typ == "branch":
            # переход на чужую ветку: стрелка идёт к её заголовку на строке 0,
            # отдельной клетки не занимает
            return (0, 0)
        # возврат на loopend текущего цикла: стрелка, а не клетка
        if iid in self.pending_loopend:
            return (0, 0)
        if typ == "end":
            return (1, 1)
        if typ == "duration":
            return (0, 0)
        path = path | {iid}

        if typ == QUESTION:
            w1, h1 = self.measure(item.get("one"), path)
            w2, h2 = self.measure(item.get("two"), path)
            return (max(1, w1) + max(0, w2), 1 + max(h1, h2))

        if typ == "select":
            # варианты раскладываются вправо друг за другом
            w, h = 1, 0
            case = item.get("one")
            while case and case not in path:
                node = self.items.get(case, {})
                wc, hc = self.measure(node.get("one"), path | {case})
                w += max(1, wc)
                h = max(h, hc)
                case = node.get("two")
            return (w, 1 + h)

        if typ == "loopbegin":
            w, h = self.measure(item.get("one"), path)
            end_id = self.find_loopend(iid)
            wa, ha = self.measure(self.items.get(end_id, {}).get("one"), path)
            return (max(1, w, wa), 1 + h + 1 + ha)

        w, h = self.measure(item.get("one"), path)
        return (max(1, w), 1 + h)

    def find_loopend(self, begin_id):
        first = self.items.get(begin_id, {}).get("one")
        if not first:
            return None

        def walk(cur, depth, seen):
            if cur is None or cur in seen:
                return None
            seen = seen | {cur}
            item = self.items.get(cur)
            if not isinstance(item, dict):
                return None
            typ = item.get("type")
            if typ in TERMINALS:
                return None
            if typ == "loopend":
                return cur if depth == 0 else None
            d = depth + 1 if typ == "loopbegin" else depth
            for field in ("one", "two"):
                found = walk(item.get(field), d, seen)
                if found:
                    return found
            return None

        return walk(first, 0, frozenset())

    # -- размещение ---------------------------------------------------

    def place(self, iid, col, row, path):
        if not iid or iid in path:
            return 1
        item = self.items.get(iid)
        if not isinstance(item, dict):
            return 1
        typ = item.get("type")
        if typ == "duration":
            return 0

        self.cols = max(self.cols, col + 1)
        self.rows = max(self.rows, row + 1)

        if typ == "end":
            self.nodes.append((iid, col, row, item))
            self.owner[iid] = self.cur_branch
            return 1
        if typ == "branch":
            # заголовок ветки уже нарисован на строке 0 - только стрелка
            return 0
        # возврат на loopend текущего цикла: клетка занята самим loopend,
        # из тела к нему идёт только стрелка
        if iid in self.pending_loopend:
            return 0

        path = path | {iid}
        self.nodes.append((iid, col, row, item))
        self.owner[iid] = self.cur_branch

        if typ == QUESTION:
            w1, _ = self.measure(item.get("one"), path)
            self.link(iid, item.get("one"), "one")
            self.link(iid, item.get("two"), "two")
            self.place(item.get("one"), col, row + 1, path)
            self.place(item.get("two"), col + max(1, w1), row + 1, path)
            return 1

        if typ == "select":
            self.nodes[-1] = (iid, col, row, item)
            case = item.get("one")
            offset = 1
            while case and case not in path:
                node = self.items.get(case, {})
                self.nodes.append((case, col + offset, row + 1, node))
                self.owner[case] = self.cur_branch
                self.cols = max(self.cols, col + offset + 1)
                self.rows = max(self.rows, row + 2)
                self.link(case, node.get("one"), "one")
                wc, _ = self.measure(node.get("one"), path | {case})
                self.place(node.get("one"), col + offset, row + 2, path | {case})
                offset += max(1, wc)
                case = node.get("two")
            return 1

        if typ == "loopbegin":
            end_id = self.find_loopend(iid)
            if end_id:
                self.pending_loopend.append(end_id)
            w, h = self.measure(item.get("one"), path)
            self.link(iid, item.get("one"), "one")
            self.place(item.get("one"), col, row + 1, path)
            if end_id:
                self.pending_loopend.pop()
                end_item = self.items[end_id]
                self.nodes.append((end_id, col, row + 1 + h, end_item))
                self.owner[end_id] = self.cur_branch
                self.rows = max(self.rows, row + 2 + h)
                self.link(end_id, end_item.get("one"), "one")
                self.place(end_item.get("one"), col, row + 2 + h, path)
            return 1 + h + 1

        self.link(iid, item.get("one"), "one")
        return 1 + self.place(item.get("one"), col, row + 1, path)

    def link(self, src, dst, kind):
        if src and dst:
            self.links.append((src, dst, kind))

    # -- общий вход ----------------------------------------------------

    def build(self):
        pairs = [(it.get("branchId", 0), iid)
                 for iid, it in self.items.items()
                 if isinstance(it, dict) and it.get("type") == "branch"]
        col = 0
        for branch_id, bid in sorted(pairs, key=lambda p: p[0]):
            item = self.items[bid]
            self.cur_branch = branch_id
            self.nodes.append((bid, col, 0, item))
            self.owner[bid] = branch_id
            self.cols = max(self.cols, col + 1)
            self.rows = max(self.rows, 1)
            self.link(bid, item.get("one"), "one")
            w, _ = self.measure(item.get("one"), {bid})
            self.place(item.get("one"), col, 1, {bid})
            col += max(1, w) + 1
        return self


# --------------------------------------------------------------- SVG

def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def wrap(text, per_line=26):
    if not text:
        return [""]
    lines = textwrap.wrap(text, per_line) or [""]
    return lines[:4]


class Svg:
    def __init__(self, layout, diagram):
        self.L = layout
        self.diagram = diagram
        self.pos = {}
        self.out = []

    def box(self, iid):
        for n in self.L.nodes:
            if n[0] == iid:
                _, col, row, _ = n
                return (PAD + col * CELL_W, PAD + row * CELL_H,
                        BOX_W, BOX_H)
        return None

    def render(self):
        L = self.L
        width = PAD * 2 + L.cols * CELL_W
        height = PAD * 2 + L.rows * CELL_H
        o = self.out
        o.append('<?xml version="1.0" encoding="UTF-8"?>')
        o.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
                 'viewBox="0 0 %d %d" font-family="Arial, Helvetica, sans-serif">'
                 % (width, height, width, height))
        o.append('<rect width="100%" height="100%" fill="#ffffff"/>')
        o.append('<defs><marker id="arw" markerWidth="9" markerHeight="7" '
                 'refX="8" refY="3.5" orient="auto">'
                 '<polygon points="0 0, 9 3.5, 0 7" fill="#3c4858"/></marker></defs>')

        for src, dst, kind in L.links:
            self.draw_link(src, dst, kind)

        for iid, col, row, item in L.nodes:
            self.draw_node(iid, col, row, item)

        o.append("</svg>")
        return "\n".join(o)

    def draw_link(self, src, dst, kind):
        a, b = self.box(src), self.box(dst)
        if not a or not b:
            return
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        x1, y1 = ax + aw / 2, ay + ah
        x2, y2 = bx + bw / 2, by
        item = self.L.items.get(dst, {})
        ref = item.get("type") == "branch"
        color = "#b9c2cf" if ref else "#3c4858"
        dash = ' stroke-dasharray="5 4"' if ref else ""
        if x1 == x2:
            d = "M %g %g L %g %g" % (x1, y1, x2, y2 - 3)
        else:
            mid = y1 + (y2 - y1) / 2
            d = "M %g %g L %g %g L %g %g L %g %g" % (x1, y1, x1, mid, x2, mid, x2, y2 - 3)
        self.out.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.6"%s '
                        'marker-end="url(#arw)"/>' % (d, color, dash))

    def draw_node(self, iid, col, row, item):
        x = PAD + col * CELL_W
        y = PAD + row * CELL_H
        typ = item.get("type")
        text = plain(item)
        o = self.out

        if typ == "branch":
            o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="4" '
                     'fill="#eef3f8" stroke="#8fa6bd" stroke-width="1.5"/>'
                     % (x, y, BOX_W, BOX_H))
            self.text_block(x, y, text or ("Ветка %s" % item.get("branchId")), bold=True)
            return
        if typ == "end":
            o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" '
                     'fill="#3c4858" stroke="#3c4858"/>'
                     % (x + BOX_W / 4, y + BOX_H / 4, BOX_W / 2, BOX_H / 2, BOX_H / 4))
            return

        if typ == QUESTION:
            cx, cy = x + BOX_W / 2, y + BOX_H / 2
            o.append('<polygon points="%g,%g %g,%g %g,%g %g,%g" fill="#fff7e6" '
                     'stroke="#d79b00" stroke-width="1.5"/>'
                     % (cx, y, x + BOX_W, cy, cx, y + BOX_H, x, cy))
            self.text_block(x, y, text, width=BOX_W - 28)
            return

        if typ == "case":
            o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3" '
                     'fill="#f2f8ff" stroke="#6f9fd8" stroke-width="1.2"/>'
                     % (x, y, BOX_W, BOX_H * 0.7))
            self.text_block(x, y, text or "остальные", width=BOX_W - 16, small=True)
            return

        if typ == "select":
            o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3" '
                     'fill="#f2f8ff" stroke="#6f9fd8" stroke-width="1.2"/>'
                     % (x, y, BOX_W, BOX_H * 0.7))
            self.text_block(x, y, text, width=BOX_W - 16, small=True)
            return

        if typ == "comment":
            o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="3" '
                     'fill="#fbfbf5" stroke="#b8b89a" stroke-dasharray="4 3"/>'
                     % (x, y, BOX_W, BOX_H * 0.7))
            self.text_block(x, y, text, width=BOX_W - 16, small=True)
            return

        fill = "#ffffff"
        stroke = "#4a5b6d"
        if typ in ("loopbegin", "loopend"):
            fill, stroke = "#eef7ee", "#4f8f4f"
        elif typ == "insertion":
            fill, stroke = "#f6f0fb", "#8a63b8"
        elif typ == "arrow-loop":
            fill, stroke = "#fdf3f3", "#c07a7a"
        elif typ in ("simpleinput", "simpleoutput"):
            fill, stroke = "#f0fbfb", "#3f9c9c"

        o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="4" fill="%s" '
                 'stroke="%s" stroke-width="1.5"/>' % (x, y, BOX_W, BOX_H, fill, stroke))
        self.text_block(x, y, text)

        side = item.get("side")
        if side and side in self.L.items:
            o.append('<text x="%g" y="%g" font-size="11" fill="#7a8794">[%s]</text>'
                     % (x + BOX_W + 6, y + BOX_H / 2 + 4, esc(plain(self.L.items[side]))))

    def text_block(self, x, y, text, bold=False, width=None, small=False):
        width = width or BOX_W - 16
        size = 11 if small else 12
        lines = wrap(text, int(width / (size * 0.55)))
        weight = " font-weight=\"bold\"" if bold else ""
        cy = y + BOX_H / 2 - (len(lines) - 1) * (size + 3) / 2 + 4
        for i, line in enumerate(lines):
            self.out.append('<text x="%g" y="%g" font-size="%d" fill="#22303d"%s>%s</text>'
                            % (x + 8, cy + i * (size + 3), size, weight, esc(line)))


# --------------------------------------------------------------- карта

def render_map(diagram, lay):
    items = diagram.get("items", {})
    print("ДИАГРАММА: %s" % (diagram.get("name") or "(без имени)"))
    print("СЕТКА: %d колонок x %d строк" % (lay.cols, lay.rows))
    print()
    print("%-4s %-4s %-4s %-12s %s" % ("вет", "стр", "кол", "тип", "текст / цель"))
    print("-" * 78)

    rows = sorted(lay.nodes, key=lambda n: (lay.owner.get(n[0], -1), n[2], n[1]))
    for iid, col, row, item in rows:
        typ = item.get("type")
        text = plain(item)
        extra = ""
        if typ == "branch":
            extra = "(заголовок ветки)"
        elif typ == "end":
            extra = "-> КОНЕЦ"
        print("%-4s %-4s %-4s %-12s %s" % (
            lay.owner.get(iid, "-"), row, col, typ, (text + " " + extra).strip()[:56]))

    # проверки правил DRAKON по координатам
    print()
    print("ПРОВЕРКИ:")
    occupied = {}
    clash = []
    for iid, col, row, item in lay.nodes:
        if (col, row) in occupied:
            clash.append((col, row, occupied[(col, row)], iid))
        occupied[(col, row)] = iid
    print("  пересечений клеток: %s" % ("нет" if not clash else clash[:5]))

    pos = {n[0]: (n[1], n[2]) for n in lay.nodes}
    leftward, jumps = [], []
    for src, dst, kind in lay.links:
        if src not in pos:
            continue
        if dst not in pos:
            continue                      # переход на чужую ветку - не клетка
        scol, srow = pos[src]
        dcol, drow = pos[dst]
        if items.get(dst, {}).get("type") == "branch":
            jumps.append((src, dst, dcol - scol))
            continue
        # возврат на loopend стоит в той же колонке ниже - это петля цикла, не нарушение
        if kind == "two" and dcol < scol:
            leftward.append((src, dst))
    print("  two-ветвлений влево или в свою колонку: %s"
          % ("нет" if not leftward else leftward[:5]))

    heads = [n for n in lay.nodes if n[3].get("type") == "branch"]
    print("  заголовки веток на строке 0: %s"
          % ("да" if all(n[2] == 0 for n in heads) else "НЕТ"))
    order = [n[3].get("branchId") for n in sorted(heads, key=lambda n: n[1])]
    print("  порядок веток слева направо: %s" % order)
    back = [j for j in jumps if j[2] < 0]
    print("  межветочных переходов: %d (из них назад-влево: %d)" % (len(jumps), len(back)))
    print("  стрелок: %d" % len(lay.links))


# --------------------------------------------------------------- main

def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("svg", "map"):
        print(__doc__)
        return 2
    cmd, path = sys.argv[1], sys.argv[2]
    with open(path, encoding="utf-8") as fh:
        diagram = json.load(fh)

    lay = Layout(diagram).build()

    if cmd == "map":
        render_map(diagram, lay)
        return 0

    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    svg = Svg(lay, diagram).render()
    with open(sys.argv[3], "w", encoding="utf-8") as fh:
        fh.write(svg)
    print("OK: %s -> %s (%dx%d клеток, %d иконок)"
          % (path, sys.argv[3], lay.cols, lay.rows, len(lay.nodes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
