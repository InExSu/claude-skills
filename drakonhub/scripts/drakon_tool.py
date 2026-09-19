#!/usr/bin/env python3
"""DrakonHub helper: read and validate .drakon / .graf files.

Usage:
    python3 drakon_tool.py read  <file.drakon|.graf>
    python3 drakon_tool.py check <file.drakon|.graf>

read  - prints the diagram as indented pseudocode (branches, questions, loops, select).
check - structural validation against DrakonHub rules (import schema + DRAKON rules).
"""

import json
import sys

FLOW_TYPES = {
    "action", "question", "select", "case", "branch", "address", "loopbegin",
    "loopend", "insertion", "comment", "simpleinput", "simpleoutput", "shelf",
    "input", "output", "process", "drakon-image",
}
SERVICE_TYPES = {"header", "params", "end", "junction", "arrow-loop", "parbegin", "parend"}
TIME_TYPES = {"duration", "pause", "timer", "ctrlstart", "ctrlend"}
FREE_TYPES = {
    "callout", "conclusion", "group-duration", "rectangle", "circle", "ellipse",
    "line", "arrow", "triangle", "hexagon", "polyline", "frame", "text", "image",
}
MIND_TYPES = {"idea", "ridea"}
ALL_TYPES = FLOW_TYPES | SERVICE_TYPES | TIME_TYPES | FREE_TYPES | MIND_TYPES

NEEDS_CONTENT = {"question", "select", "loopbegin"}
INDENT = "  "


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def item_text(item):
    content = item.get("content") or item.get("text") or ""
    return " ".join(str(content).split())


def strip_html(text):
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
    return strip_html(item_text(item))


# --------------------------------------------------------------------------- read

class Reader:
    def __init__(self, diagram):
        self.items = diagram.get("items", {})
        self.lines = []

    def emit(self, depth, text):
        self.lines.append(INDENT * depth + text)

    def get(self, item_id):
        return self.items.get(item_id)

    def branches(self):
        pairs = []
        for item_id, item in self.items.items():
            if item.get("type") == "branch":
                pairs.append((item.get("branchId", 0), item_id))
        return [i for _, i in sorted(pairs, key=lambda p: p[0])]

    def walk(self, item_id, depth, on_path, stop_after_loop=None):
        """Follow `one` chain. Returns when the chain ends."""
        seen = set()
        while item_id:
            if item_id in on_path:
                self.emit(depth, "(цикл -> %s)" % item_id)
                return
            if item_id in seen:
                self.emit(depth, "(петля на %s)" % item_id)
                return
            seen.add(item_id)
            item = self.get(item_id)
            if not item:
                self.emit(depth, "!! нет иконки %s" % item_id)
                return
            typ = item.get("type")
            on_path = on_path | {item_id}

            if typ == "end":
                self.emit(depth, "КОНЕЦ")
                return
            if typ == "branch":
                self.emit(depth, "-> ветка «%s» (%s)" % (plain(item), item_id))
                return
            if typ == "loopend":
                self.emit(depth, "конец цикла" + (" — %s" % plain(item) if plain(item) else ""))
                item_id = item.get("one")
                continue
            if typ == "arrow-loop":
                self.emit(depth, "↺ возврат" + (" — %s" % plain(item) if plain(item) else ""))
                item_id = item.get("one")
                continue
            if typ == "loopbegin":
                self.render_loop(item_id, item, depth, on_path)
                nxt = self.loop_exit(item_id)
                if not nxt:
                    return
                item_id = nxt
                continue
            if typ == "question":
                return self.render_question(item_id, item, depth, on_path)
            if typ == "select":
                return self.render_select(item, depth, on_path)
            if typ in ("case",):
                self.emit(depth, "ВАРИАНТ «%s»:" % plain(item))
                self.walk(item.get("one"), depth + 1, on_path)
                item_id = item.get("two")
                continue
            if typ == "insertion":
                self.emit(depth, "ВЫЗОВ: %s" % plain(item))
                item_id = item.get("one")
                continue
            if typ == "comment":
                self.emit(depth, "// %s" % plain(item))
                item_id = item.get("one")
                continue
            prefix = {
                "simpleinput": "ЖДАТЬ: %s",
                "simpleoutput": "ВЫДАТЬ: %s",
                "process": "ПАРАЛЛЕЛЬНЫЙ ПРОЦЕСС: %s",
                "shelf": "ПОЛКА: %s",
                "input": "ВВОД: %s",
                "output": "ВЫВОД: %s",
                "address": "ПЕРЕЙТИ: %s",
            }.get(typ, "%s")
            self.emit(depth, prefix % plain(item) if "%s" in prefix else plain(item))
            side = self.get(item.get("side")) if item.get("side") else None
            if side:
                self.emit(depth + 1, "(длительность: %s)" % plain(side))
            item_id = item.get("one")

    def render_question(self, qid, item, depth, on_path):
        flag1 = item.get("flag1", 1)
        yes_id = item.get("one") if flag1 == 1 else item.get("two")
        no_id = item.get("two") if flag1 == 1 else item.get("one")
        self.emit(depth, "? %s" % plain(item))
        self.emit(depth + 1, "ДА:")
        self.walk(yes_id, depth + 2, on_path)
        self.emit(depth + 1, "НЕТ:")
        self.walk(no_id, depth + 2, on_path)
        return None  # обе ветки отрисованы

    def render_select(self, item, depth, on_path):
        self.emit(depth, "ВЫБОР: %s" % plain(item))
        case_id = item.get("one")
        idx = 0
        while case_id:
            case = self.get(case_id)
            if not case:
                self.emit(depth + 1, "!! нет case %s" % case_id)
                return None
            idx += 1
            label = plain(case) or "остальные случаи"
            self.emit(depth + 1, "ВАРИАНТ %d «%s»:" % (idx, label))
            self.walk(case.get("one"), depth + 2, on_path)
            case_id = case.get("two")
        return None

    def loop_body_end(self, begin_id):
        """Walk `one` from loopbegin until its loopend (nested loops aware)."""
        depth = 0
        cur = self.get(begin_id).get("one")
        visited = set()
        while cur and cur not in visited:
            visited.add(cur)
            item = self.get(cur)
            if not item:
                return None
            typ = item.get("type")
            if typ == "loopbegin":
                depth += 1
            elif typ == "loopend":
                if depth == 0:
                    return cur
                depth -= 1
            cur = item.get("one")
        return None

    def render_loop(self, begin_id, item, depth, on_path):
        self.emit(depth, "ЦИКЛ (%s):" % (plain(item) or "пока условие"))
        end_id = self.loop_body_end(begin_id)
        cur = item.get("one")
        visited = set()
        while cur and cur != end_id and cur not in visited:
            visited.add(cur)
            node = self.get(cur)
            if not node:
                break
            typ = node.get("type")
            if typ == "loopend":
                break
            if typ == "loopbegin":
                self.render_loop(cur, node, depth + 1, on_path)
                cur = self.loop_exit(cur)
                continue
            if typ == "question":
                flag1 = node.get("flag1", 1)
                yes_id = node.get("one") if flag1 == 1 else node.get("two")
                no_id = node.get("two") if flag1 == 1 else node.get("one")
                self.emit(depth + 1, "? %s" % plain(node))
                if yes_id == end_id or yes_id is None:
                    self.emit(depth + 2, "ДА: повторить цикл")
                else:
                    self.emit(depth + 2, "ДА:")
                    self.walk(yes_id, depth + 3, on_path)
                if no_id == end_id or no_id is None:
                    self.emit(depth + 2, "НЕТ: выйти из цикла")
                else:
                    self.emit(depth + 2, "НЕТ:")
                    self.walk(no_id, depth + 3, on_path)
                return
            self.walk(cur, depth + 1, on_path, stop_after_loop=True)
            return
        if not end_id:
            self.emit(depth + 1, "!! цикл без loopend")

    def loop_exit(self, begin_id):
        end_id = self.loop_body_end(begin_id)
        if not end_id:
            return None
        return self.get(end_id).get("one")

    def read_drakon(self, diagram):
        name = diagram.get("name") or "(без имени)"
        self.emit(0, "ДИАГРАММА: %s" % name)
        if diagram.get("params"):
            self.emit(0, "ПАРАМЕТРЫ: %s" % strip_html(str(diagram["params"])))
        branches = self.branches()
        if not branches:
            self.emit(0, "!! нет ни одной ветки силуэта — диаграмма не стартует")
            return
        for bid in branches:
            item = self.items[bid]
            self.emit(0, "")
            self.emit(0, "ВЕТКА %s «%s»:" % (item.get("branchId", 0), plain(item)))
            self.walk(item.get("one"), 1, {bid})
        return

    def read_graf(self, diagram):
        items = diagram.get("items", {})
        roots = [i for i, it in items.items() if it.get("type") in ("ridea", "header")]
        if not roots:
            roots = [i for i, it in items.items() if not it.get("parent")]
        children = {}
        for i, it in items.items():
            if it.get("type") in ("idea", "ridea"):
                children.setdefault(it.get("parent"), []).append(i)
        for group in children.values():
            group.sort(key=lambda i: items[i].get("ordinal", 0))

        def node(item_id, depth):
            it = items.get(item_id, {})
            self.emit(depth, "- %s" % (plain(it) or "(пусто)"))
            for child in children.get(item_id, []):
                node(child, depth + 1)

        self.emit(0, "КАРТА: %s" % (diagram.get("name") or "(без имени)"))
        for root in roots:
            node(root, 0)

    def run(self, diagram):
        if diagram.get("type") == "graf" or any(
            it.get("type") in MIND_TYPES for it in diagram.get("items", {}).values()
        ):
            self.read_graf(diagram)
        else:
            self.read_drakon(diagram)
        return "\n".join(self.lines)


# -------------------------------------------------------------------------- check

class Checker:
    def __init__(self, diagram):
        self.d = diagram
        self.items = diagram.get("items", {})
        self.errors = []
        self.warnings = []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def check(self):
        self.check_header()
        self.check_items()
        self.check_links()
        self.check_branches()
        self.check_reachability()
        self.check_end()
        self.check_loops()
        self.check_questions()
        self.check_back_edges()
        return self.errors, self.warnings

    def check_back_edges(self):
        """Ловит конструкции, из-за которых DrakonHub уходит в бесконечный обход.

        1. one/two/side назад на уже пройденную иконку той же ветки
           (кроме branch / arrow-loop / junction) -> layoutSilhouette
           зацикливается, редактор виснет.
        2. несколько возвратов на одну ветку -> тот же риск.

        Разрешённые цели возврата: branch (паттерн «Lunch break»),
        arrow-loop и junction (паттерн «Work out - question-action»).
        loopend -> branch тоже допустим: так сделано в официальном
        примере «A-star algorithm».
        """
        allowed_back = {"branch", "arrow-loop", "junction"}

        for branch_id, branch in self.items.items():
            if not (isinstance(branch, dict) and branch.get("type") == "branch"):
                continue
            start = branch.get("one")
            if not start:
                continue
            returns = set()
            if not hasattr(self, "seen_back_edges"):
                self.seen_back_edges = set()
            seen_edges = self.seen_back_edges

            def walk(node_id, path):
                if node_id is None or node_id in path:
                    return
                node = self.items.get(node_id)
                if not isinstance(node, dict):
                    return
                path = path + [node_id]
                for field in ("one", "two", "side"):
                    target = node.get(field)
                    if not target or target not in self.items:
                        continue
                    ttype = self.get_type(target)
                    if target in path and ttype not in allowed_back:
                        key = (node_id, field, target)
                        if key not in seen_edges:
                            seen_edges.add(key)
                            self.err("%s.%s -> %s: возврат назад по ветке «%s». "
                                     "Цикл замыкайте парой loopbegin/loopend или "
                                     "переходом на id ветки" %
                                     (node_id, field, target, plain(branch)))
                        continue
                    if target == branch_id:
                        returns.add(node_id)
                        continue
                    walk(target, path)

            walk(start, [])
            members = self.branch_members(branch_id)
            # важно: возврат именно ИЗНУТРИ этой же ветки. Переход на ветку
            # из другой ветки (как 121 -> 43 в A-star) — нормален.
            own_returns = returns & members
            if len(own_returns) > 1:
                self.warn('ветка «%s» (%s): несколько возвратов на неё изнутри '
                          '(%s) — риск зацикливания. Оставьте один' %
                          (plain(branch), branch_id, ", ".join(sorted(own_returns))))

            # возврат на свою же ветку + цикл внутри неё = findLeftLinks вешается
            has_loop = any(self.get_type(m) in ("loopbegin", "loopend") for m in members)
            if has_loop and own_returns:
                self.err('ветка «%s» (%s): внутри есть цикл loopbegin/loopend '
                         'и одновременно возврат на эту же ветку (%s). '
                         'Такого нет ни в одном официальном примере — редактор '
                         'зациклится в findLeftLinks. Уберите возврат на ветку' %
                         (plain(branch), branch_id, ", ".join(sorted(own_returns))))

    def branch_members(self, branch_id):
        """Узлы ветки: обход от branch.one, не заходя внутрь других веток."""
        members, stack = set(), [self.items[branch_id].get("one")]
        while stack:
            node_id = stack.pop()
            if not node_id or node_id in members or node_id not in self.items:
                continue
            item = self.items[node_id]
            if not isinstance(item, dict) or item.get("type") == "branch":
                continue
            members.add(node_id)
            for field in ("one", "two", "side"):
                target = item.get(field)
                if target:
                    stack.append(target)
        return members

    def get_type(self, item_id):
        item = self.items.get(item_id)
        return item.get("type") if isinstance(item, dict) else None

    def check_header(self):
        if not isinstance(self.items, dict):
            self.err("items должен быть объектом")
            return
        if self.d.get("type") not in (None, "drakon", "graf", "free", "basic"):
            self.err('неизвестный type: %r' % self.d.get("type"))
        if self.d.get("type") in (None, "drakon") and "header" not in self.items:
            self.warn('нет item с id "header" — заголовок будет создан из name')
        if self.d.get("style") and not isinstance(self.d.get("style"), str):
            self.err("style верхнего уровня должен быть JSON-строкой")
        if self.d.get("params") and not isinstance(self.d.get("params"), str):
            self.err("params должен быть строкой")
        if not self.d.get("name"):
            self.warn("нет name — заголовок диаграммы пустой")

    def check_items(self):
        for item_id, item in self.items.items():
            if not isinstance(item_id, str):
                self.err("ключ items должен быть строкой: %r" % item_id)
            if not isinstance(item, dict):
                self.err("item %s не объект" % item_id)
                continue
            typ = item.get("type")
            if typ not in ALL_TYPES:
                self.err("item %s: неизвестный type %r" % (item_id, typ))
            if "style" in item and not isinstance(item["style"], str):
                self.err("item %s: style должен быть JSON-строкой" % item_id)
            else:
                try:
                    if item.get("style"):
                        json.loads(item["style"])
                except ValueError:
                    self.err("item %s: style не парсится как JSON" % item_id)
            if typ in NEEDS_CONTENT and not plain(item):
                self.err("item %s (%s): пустой content — сломает генерацию кода" % (item_id, typ))
            if typ == "action" and not plain(item):
                self.warn("item %s: пустое действие" % item_id)
            if typ == "end" and item.get("one"):
                self.warn("item %s: у end есть связь one — конец должен быть терминальным" % item_id)

    def check_links(self):
        for item_id, item in self.items.items():
            if not isinstance(item, dict):
                continue
            for field in ("one", "two", "side"):
                target = item.get(field)
                if target is None:
                    continue
                if not isinstance(target, str):
                    self.err("item %s: поле %s должно быть строкой-id" % (item_id, field))
                elif target not in self.items:
                    self.err("item %s: %s указывает на несуществующий id %s" % (item_id, field, target))

    def check_branches(self):
        ids = []
        for item_id, item in self.items.items():
            if isinstance(item, dict) and item.get("type") == "branch":
                bid = item.get("branchId")
                if bid is None:
                    self.err("ветка %s: нет branchId" % item_id)
                else:
                    ids.append(bid)
                if not item.get("one"):
                    self.err("ветка %s: нет one (пустая ветка)" % item_id)
        if not ids:
            self.err("нет ни одной ветки (branch) — не с чего начинать диаграмму")
            return
        if len(set(ids)) != len(ids):
            self.err("branchId не уникальны: %s" % sorted(ids))

    def check_reachability(self):
        branches = [(i.get("branchId", 0), iid)
                    for iid, i in self.items.items()
                    if isinstance(i, dict) and i.get("type") == "branch"]
        if not branches:
            return
        start = sorted(branches)[0][1]
        seen, stack = set(), [start]
        while stack:
            cur = stack.pop()
            if cur in seen or cur not in self.items:
                continue
            seen.add(cur)
            item = self.items[cur]
            if not isinstance(item, dict):
                continue
            for field in ("one", "two", "side"):
                if item.get(field):
                    stack.append(item[field])
        for item_id, item in self.items.items():
            if not isinstance(item, dict):
                continue
            typ = item.get("type")
            if typ in FREE_TYPES or typ in ("header", "params", "duration"):
                continue
            if item_id not in seen:
                self.warn("item %s (%s) недостижим от стартовой ветки" % (item_id, typ))

    def check_end(self):
        ends = [i for i, it in self.items.items()
                if isinstance(it, dict) and it.get("type") == "end"]
        if not ends:
            self.err("нет иконки end — у диаграммы должен быть один конец")
        elif len(ends) > 1:
            self.warn("несколько end (%s) — по правилам DRAKON конец один" % ", ".join(ends))

    def check_loops(self):
        depth = 0
        for item_id, item in self.items.items():
            if not isinstance(item, dict):
                continue
            typ = item.get("type")
            if typ == "loopbegin" and not item.get("one"):
                self.err("loopbegin %s: нет тела цикла (one)" % item_id)
            if typ == "loopend":
                depth += 1
        begins = sum(1 for it in self.items.values()
                     if isinstance(it, dict) and it.get("type") == "loopbegin")
        if begins != depth:
            self.warn("loopbegin: %d, loopend: %d — циклы должны быть парными" % (begins, depth))

    def check_questions(self):
        for item_id, item in self.items.items():
            if not isinstance(item, dict) or item.get("type") != "question":
                continue
            if "flag1" not in item:
                self.warn("question %s: нет flag1 (по умолчанию 1 — one=Да)" % item_id)
            if not item.get("one"):
                self.err("question %s: нет one (путь Да/Нет вниз)" % item_id)
            if not item.get("two"):
                self.err("question %s: нет two (правая ветка)" % item_id)
            if item.get("one") and item.get("one") == item.get("two"):
                self.warn("question %s: one == two — обе ветки ведут в одну точку" % item_id)
            text = plain(item).lower()
            for bad in (" не ", " и ", " или "):
                if bad in " %s " % text:
                    self.warn('question %s: в тексте есть "%s" — разбей на отдельные вопросы '
                              'или поменяй Да/Нет через flag1' % (item_id, bad.strip()))
        for item_id, item in self.items.items():
            if isinstance(item, dict) and item.get("type") == "select":
                case_id = item.get("one")
                count = 0
                while case_id:
                    case = self.items.get(case_id)
                    if not isinstance(case, dict) or case.get("type") != "case":
                        self.err("select %s: one ведёт не на case (%s)" % (item_id, case_id))
                        break
                    count += 1
                    if not case.get("one"):
                        self.err("case %s: нет one (тело варианта)" % case_id)
                    case_id = case.get("two")
                if count < 2:
                    self.warn("select %s: меньше двух case" % item_id)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("read", "check"):
        print(__doc__)
        return 2
    cmd, path = sys.argv[1], sys.argv[2]
    try:
        diagram = load(path)
    except (OSError, ValueError) as exc:
        print("Не удалось прочитать файл: %s" % exc)
        return 1
    if cmd == "read":
        print(Reader(diagram).run(diagram))
        return 0
    errors, warnings = Checker(diagram).check()
    if not errors and not warnings:
        print("OK: ошибок и замечаний нет")
        return 0
    for msg in errors:
        print("ОШИБКА: %s" % msg)
    for msg in warnings:
        print("ЗАМЕЧАНИЕ: %s" % msg)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
