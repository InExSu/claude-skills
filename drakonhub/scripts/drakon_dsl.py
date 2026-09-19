#!/usr/bin/env python3
"""DrakonHub DSL - компактный текст вместо ручной сборки JSON.

Зачем: LLM плохо пишет .drakon вручную (надо самому придумывать id и
проставлять связи one/two). DSL описывает алгоритм текстом с отступами,
конвертер сам раздаёт id, строит связи и силуэт.

Usage:
    python3 drakon_dsl.py to-drakon <in.dsl>  <out.drakon>
    python3 drakon_dsl.py to-dsl    <in.drakon> [out.dsl]
    python3 drakon_dsl.py roundtrip <in.drakon>     # .drakon -> DSL -> .drakon, сверка графов

Синтаксис DSL (отступ = 2 пробела):

    # Название диаграммы                заголовок
    > Условие старта: ...               params (строку можно повторить)
    % Описание                          description

    @ Имя ветки                         ветка силуэта, порядок = branchId слева направо
      Действие                          action (команда в императиве)
      Другое действие [20 мин]          action с длительностью (side -> duration)
      // пояснение                      comment
      >> Подпроцесс                     insertion (вызов другой диаграммы)
      << Событие                        simpleinput (ждать события)
      >! Сигнал                         simpleoutput
      ? Вопрос?                         question, флаг1=1
        да:                             ветка one (вниз)
          ...
        нет:                            ветка two (вправо)
          ...
      * Что выбираем?                   select
        - Вариант 1:                    case (последний с пустым текстом = остальные)
          ...
        - (остальные):
          ...
      ~ цикл: Повторить 10 раз          loopbegin
        тело цикла
      ~ /цикл -> Имя ветки              loopend, one = куда после цикла
      -> Имя ветки                      переход на ветку
      -> КОНЕЦ                          переход на end
      -> повтор                         внутри цикла: конец итерации (на loopend)
      -> петля                          возврат к метке 'петля' (arrow-loop) в ветке

Каждый путь обязан заканчиваться `-> Ветка`, `-> КОНЕЦ`, `-> повтор` или
`-> петля`. Внутри цикла пустой блок `да:` / `нет:` означает «конец итерации»
(== `-> повтор`) - DrakonHub не умеет тянуть цикл через two-ветку вопроса.
"""

import json
import re
import sys

DURATION_RE = re.compile(r"\s*\[([^\]]+)\]\s*$")


class DslError(Exception):
    pass


# --------------------------------------------------------------- утилиты

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


# --------------------------------------------------------------- DSL -> .drakon

class Builder:
    def __init__(self):
        self.items = {}
        self.n = 0
        self.branches = {}      # имя ветки -> id
        self.branch_order = []
        self.end_id = None
        self.loop_stack = []
        self.arrows = []        # arrow-loop текущей ветки (цель для '-> петля')

    # -- примитивы ----------------------------------------------------

    def new(self, typ, **fields):
        self.n += 1
        iid = str(self.n)
        item = {"type": typ}
        item.update({k: v for k, v in fields.items() if v not in (None, "")})
        self.items[iid] = item
        return iid

    def end(self):
        if self.end_id is None:
            self.end_id = self.new("end")
        return self.end_id

    def resolve(self, name):
        name = name.strip()
        if name in ("КОНЕЦ", "END", "конец", "end"):
            return self.end()
        if name == "повтор":
            if not self.loop_stack:
                raise DslError("'-> повтор' вне цикла")
            return self.loop_stack[-1]
        if name == "петля":
            if not self.arrows:
                raise DslError("'-> петля' без иконки 'петля' в этой ветке")
            return self.arrows[-1]
        if name.startswith("@"):
            name = name[1:].strip()
        if name in self.branches:
            return self.branches[name]
        raise DslError("неизвестный переход: %r (нет ветки с таким именем)" % name)

    # -- разбор -------------------------------------------------------

    @staticmethod
    def tree(lines):
        """Список (indent, text) -> лес узлов {text, children}."""
        root = {"text": None, "children": []}
        stack = [(-1, root)]
        for indent, text in lines:
            node = {"text": text, "children": []}
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack[-1][1]["children"].append(node)
            stack.append((indent, node))
        return root["children"]

    def build(self, top):
        header = {"name": "", "params": [], "description": []}
        branch_nodes = []
        for node in top:
            text = node["text"]
            if text.startswith("#"):
                header["name"] = text[1:].strip()
            elif text.startswith(">"):
                header["params"].append(text[1:].strip())
            elif text.startswith("%"):
                header["description"].append(text[1:].strip())
            elif text.startswith("@"):
                branch_nodes.append(node)
            else:
                raise DslError("строка верхнего уровня вне ветки: %r" % text)

        if not branch_nodes:
            raise DslError("нет ни одной ветки '@'")

        # ветки регистрируем заранее, чтобы переходы могли ссылаться вперёд
        for node in branch_nodes:
            name = node["text"][1:].strip()
            if name and name in self.branches:
                raise DslError("ветка %r повторяется" % name)
            bid = self.new("branch", branchId=len(self.branch_order), content=name)
            if name:
                self.branches[name] = bid
            self.branch_order.append((bid, name))

        for index, node in enumerate(branch_nodes):
            self.build_branch(node, self.branch_order[index][0])

        self.items["header"] = {"type": "header", "style": ""}

        diagram = {
            "name": header["name"],
            "type": "drakon",
            "items": self.items,
        }
        if header["params"]:
            diagram["params"] = "".join("<p>%s</p>" % p for p in header["params"])
        if header["description"]:
            diagram["description"] = " ".join(header["description"])
        diagram["style"] = ""
        return diagram

    def build_branch(self, node, bid):
        self.arrows = []
        ids = []
        for kid in self.attach_loop_closers(node["children"]):
            self.build_node(kid, ids)
        if not ids:
            raise DslError("пустая ветка: %s" % node["text"])
        self.link_chain(ids)
        self.items[bid]["one"] = ids[0]

    def link_chain(self, ids):
        for a, b in zip(ids, ids[1:]):
            # вопрос/выбор/цикл сами назначают свой one - не перетираем
            if "one" not in self.items[a]:
                self.items[a]["one"] = b

    def build_block(self, kids, parent_id, link):
        ids = []
        for kid in self.attach_loop_closers(kids):
            self.build_node(kid, ids)
        if not ids:
            # пустой блок внутри цикла - это "конец итерации":
            # в DRAKON цикл строится по вертелу, и указывать явно
            # -> повтор на two-ветке вопроса нельзя (редактор падает).
            if self.loop_stack:
                self.items[parent_id][link] = self.loop_stack[-1]
                return
            raise DslError("пустой блок у %s (%s)" % (parent_id, link))
        self.link_chain(ids)
        self.items[parent_id][link] = ids[0]

    def close_loop_tails(self, body_ids, le):
        """Замкнуть на loopend все висячие концы тела цикла.

        Обходим тело цикла (one и two), не выходя за его пределы, и у
        каждого узла без `one` ставим `one = loopend` - это "конец
        итерации". Узлы, которые сами уводят наружу (branch, end), не
        трогаем: там выход из цикла задан явно.
        """
        seen = set()
        stack = list(body_ids)
        while stack:
            cur = stack.pop()
            if cur is None or cur in seen:
                continue
            seen.add(cur)
            item = self.items.get(cur)
            if not isinstance(item, dict):
                continue
            typ = item.get("type")
            if typ in ("loopend",):
                continue
            target = item.get("one")
            if not target:
                if typ not in ("branch", "end"):
                    item["one"] = le
                continue
            if self.items.get(target, {}).get("type") in ("branch", "end"):
                continue
            stack.append(target)
            if item.get("two"):
                stack.append(item["two"])

    @staticmethod
    def pick_loop_closer(kids):
        """Найти '~ /цикл' среди детей цикла (или глубже - в последнем
        потомке, куда его могла приклеить attach_loop_closers)."""
        for kid in kids:
            if kid["text"].startswith("~ /"):
                return kid
        return None

    @staticmethod
    def attach_loop_closers(kids):
        """'~ /цикл -> ...' пишется на том же отступе, что и '~ цикл:' - это
        не ребёнок цикла, а его закрытие. Приклеиваем к узлу цикла.

        Важно: приклеивать надо к последнему узлу '~ цикл', а не к последнему
        узлу вообще. Иначе '~ /цикл' станет ребёнком узла, идущего ПОСЛЕ
        цикла (например 'Действие 3' из правой ветви вопроса), и цикл
        останется без закрытия - "цикл без закрытия '~ /цикл -> ...'"."""
        out = []
        for kid in kids:
            if kid["text"].startswith("~ /") and out:
                loop = None
                for node in reversed(out):
                    if node["text"].startswith("~ "):
                        loop = node
                        break
                if loop is None:
                    raise DslError("'~ /цикл' без открытия цикла: %s" % kid["text"])
                loop["children"].append(kid)
            else:
                out.append(kid)
        return out

    @staticmethod
    def pick(kids, label):
        """Найти дочерний блок 'да:' / 'нет:' и вернуть его строки."""
        for kid in kids:
            if kid["text"].rstrip(":").strip().lower() == label:
                return kid["children"]
        return None

    def build_node(self, node, out_ids):
        text = node["text"]
        kids = node["children"]

        # переход
        if text.startswith("->"):
            out_ids.append(self.resolve(text[2:]))
            return

        # вопрос
        if text.startswith("? "):
            q = self.new("question", flag1=1, content=text[2:].strip())
            out_ids.append(q)
            yes = self.pick(kids, "да")
            no = self.pick(kids, "нет")
            if yes is None:
                raise DslError("вопрос без блока 'да:': %s" % text)
            if no is None:
                raise DslError("вопрос без блока 'нет:': %s" % text)
            self.build_block(yes, q, "one")
            self.build_block(no, q, "two")
            return q

        # выбор
        if text.startswith("* "):
            sel = self.new("select", content=text[2:].strip())
            out_ids.append(sel)
            cases = [k for k in kids if k["text"].startswith("-")]
            if len(cases) < 2:
                raise DslError("select требует минимум 2 варианта: %s" % text)
            prev = None
            for case in cases:
                label = case["text"][1:].strip().rstrip(":")
                if label in ("(остальные)", "остальные"):
                    label = ""
                cid = self.new("case", content=label)
                if prev is None:
                    self.items[sel]["one"] = cid
                else:
                    self.items[prev]["two"] = cid
                self.build_block(case["children"], cid, "one")
                prev = cid
            return sel

        # цикл
        if text.startswith("~ "):
            closer = self.pick_loop_closer(kids)
            if closer is None:
                raise DslError("цикл без закрытия '~ /цикл -> ...': %s" % text)
            # убрать closer из тела, иначе рекурсивный build_node
            # (ветви вопроса) снова наткнётся на него
            body = [k for k in kids if k is not closer]
            body_text = text[2:].strip()
            if body_text.lower().startswith("цикл:"):
                body_text = body_text[len("цикл:"):].strip()
            lb = self.new("loopbegin", content=body_text)
            out_ids.append(lb)
            le = self.new("loopend")
            self.loop_stack.append(le)

            b_ids = []
            try:
                for kid in body:
                    self.build_node(kid, b_ids)
            finally:
                self.loop_stack.pop()

            if not b_ids:
                b_ids = [le]
            self.link_chain(b_ids)
            self.items[lb]["one"] = b_ids[0]
            # замкнуть на loopend ВСЕ тупики тела цикла, а не только
            # последний узел главной цепочки. Иначе ветви two вопросов
            # остаются без one, и генератор кода не находит loopend:
            # "цикл без закрытия '~ /цикл -> ...'".
            self.close_loop_tails(b_ids, le)

            rest = closer["text"][2:].strip()          # "/цикл[: текст][-> Цель]"
            if not rest.startswith("/цикл"):
                raise DslError("ожидалось '~ /цикл [-> Цель]', получено: %s" % closer["text"])
            rest = rest[len("/цикл"):].strip()
            if rest.startswith(":"):
                rest = rest[1:].strip()
            if "->" in rest:
                text_part, target = rest.split("->", 1)
            else:
                text_part, target = rest, ""
            text_part = text_part.strip()
            if text_part:
                self.items[le]["content"] = text_part
            target = target.strip()
            if target:
                self.items[le]["one"] = self.resolve(target)
            else:
                # цикл закрывается, а вертел ветки продолжается ниже
                out_ids.append(le)
            return lb

        # комментарий
        if text.startswith("//"):
            out_ids.append(self.new("comment", content=text[2:].strip()))
            return

        # вызов другой диаграммы
        if text.startswith(">>"):
            out_ids.append(self.new("insertion", content=text[2:].strip()))
            return

        # петля-стрелка (точка возврата)
        if text == "петля" or text.startswith("петля "):
            aid = self.new("arrow-loop", content=text[len("петля"):].strip())
            self.arrows.append(aid)
            out_ids.append(aid)
            return aid

        # ожидание события
        if text.startswith("<<"):
            out_ids.append(self.new("simpleinput", content=text[2:].strip()))
            return

        # выдача сигнала
        if text.startswith(">!"):
            out_ids.append(self.new("simpleoutput", content=text[2:].strip()))
            return

        # действие (с возможной длительностью в [])
        m = DURATION_RE.search(text)
        duration = None
        if m:
            duration = m.group(1).strip()
            text = text[:m.start()].strip()
        if not text:
            raise DslError("пустое действие")
        aid = self.new("action", content=text)
        if duration:
            did = self.new("duration", content=duration)
            self.items[aid]["side"] = did
        out_ids.append(aid)
        return aid


def dsl_to_drakon(text):
    lines = []
    for raw in text.split("\n"):
        if not raw.strip() or raw.lstrip().startswith(";"):
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))
    if not lines:
        raise DslError("пустой файл")
    return Builder().build(Builder.tree(lines))


# --------------------------------------------------------------- .drakon -> DSL

class Renderer:
    def __init__(self, diagram):
        self.items = diagram.get("items", {})
        self.lines = []

    def emit(self, indent, text):
        self.lines.append(" " * indent + text)

    def branches(self):
        pairs = [(it.get("branchId", 0), iid)
                 for iid, it in self.items.items()
                 if isinstance(it, dict) and it.get("type") == "branch"]
        return [iid for _, iid in sorted(pairs, key=lambda p: p[0])]

    def label(self, iid):
        """Имя цели перехода: имя ветки, КОНЕЦ или повтор."""
        if iid is None:
            return "КОНЕЦ"
        item = self.items.get(iid)
        if not isinstance(item, dict):
            return "КОНЕЦ"
        if item.get("type") == "branch":
            return plain(item) or iid
        if item.get("type") == "loopend":
            return "повтор"
        if item.get("type") == "arrow-loop":
            return "петля"
        return "КОНЕЦ"

    def duration_suffix(self, item):
        side = item.get("side")
        if side and side in self.items:
            return " [%s]" % plain(self.items[side])
        return ""

    def walk(self, iid, indent, path, stop=None):
        """Печатает цепочку от iid. Возвращает, дойдя до ветки/конца/стопа."""
        while iid:
            item = self.items.get(iid)
            if not isinstance(item, dict):
                self.emit(indent, "!! нет иконки %s" % iid)
                return
            typ = item.get("type")

            # ветка, конец и конец итерации - легальные цели перехода,
            # даже если уже встречались на этом пути (возврат на ветку = цикл)
            if typ == "branch":
                self.emit(indent, "-> %s" % (plain(item) or iid))
                return
            if typ == "end":
                self.emit(indent, "-> КОНЕЦ")
                return
            if typ == "loopend":
                self.emit(indent, "-> повтор")
                return
            if stop and iid == stop:
                self.emit(indent, "-> повтор")
                return
            # повторный заход на петлю-стрелку - это и есть возврат цикла
            if typ == "arrow-loop" and iid in path:
                self.emit(indent, "-> петля")
                return

            if iid in path:
                self.emit(indent, "!! зацикливание на %s" % iid)
                return
            path = path + [iid]
            if typ == "action":
                self.emit(indent, plain(item) + self.duration_suffix(item))
            elif typ == "comment":
                self.emit(indent, "// %s" % plain(item))
            elif typ == "insertion":
                self.emit(indent, ">> %s" % plain(item))
            elif typ == "simpleinput":
                self.emit(indent, "<< %s" % plain(item))
            elif typ == "simpleoutput":
                self.emit(indent, ">! %s" % plain(item))
            elif typ == "arrow-loop":
                self.emit(indent, "петля" + (" " + plain(item) if plain(item) else ""))
            elif typ == "question":
                flag1 = item.get("flag1", 1)
                yes_id = item.get("one") if flag1 == 1 else item.get("two")
                no_id = item.get("two") if flag1 == 1 else item.get("one")
                self.emit(indent, "? %s" % plain(item))
                self.emit(indent + 2, "да:")
                self.walk(yes_id, indent + 4, path, stop)
                self.emit(indent + 2, "нет:")
                self.walk(no_id, indent + 4, path, stop)
                return
            elif typ == "select":
                self.emit(indent, "* %s" % plain(item))
                case_id = item.get("one")
                idx = 0
                while case_id and case_id not in path:
                    case = self.items.get(case_id)
                    if not isinstance(case, dict) or case.get("type") != "case":
                        break
                    idx += 1
                    label = plain(case) or "(остальные)"
                    self.emit(indent + 2, "- %s:" % label)
                    path = path + [case_id]
                    self.walk(case.get("one"), indent + 4, path, stop)
                    case_id = case.get("two")
                return
            elif typ == "loopbegin":
                end_id = self.find_loopend(iid)
                self.emit(indent, "~ цикл: %s" % (plain(item) or "пока условие"))
                self.walk(item.get("one"), indent + 2, path, stop=end_id)
                if end_id:
                    after = self.items[end_id].get("one")
                    nxt = self.items.get(after)
                    kind = nxt.get("type") if isinstance(nxt, dict) else None
                    closer = "~ /цикл"
                    if plain(self.items[end_id]):
                        closer += ": " + plain(self.items[end_id])
                    if kind in ("branch", "end", "loopend", "arrow-loop"):
                        closer += " -> %s" % self.label(after)
                        self.emit(indent, closer)
                    else:
                        # после цикла вертел ветки продолжается - пишем его ниже
                        self.emit(indent, closer)
                        self.walk(after, indent, path, stop)
                return
            else:
                self.emit(indent, "%s: %s" % (typ, plain(item)))

            iid = item.get("one")

    def find_loopend(self, begin_id):
        """Ищет свой loopend по всему телу цикла (и one, и two),
        не заходя в чужие ветки и учитывая вложенные циклы."""
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
            if typ in ("branch", "end"):
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

    def render(self, diagram):
        name = diagram.get("name")
        if name:
            self.emit(0, "# %s" % name)
        params = diagram.get("params")
        if params:
            for chunk in re.split(r"</?p>", params):
                chunk = " ".join(strip_tags(chunk).split())
                if chunk:
                    self.emit(0, "> %s" % chunk)
        descr = diagram.get("description")
        if descr:
            self.emit(0, "%% %s" % " ".join(strip_tags(descr).split()))

        for bid in self.branches():
            item = self.items[bid]
            self.emit(0, "")
            bname = plain(item)
            self.emit(0, ("@ %s" % bname) if bname else "@")
            self.walk(item.get("one"), 2, [bid])
        return "\n".join(self.lines) + "\n"


def drakon_to_dsl(diagram):
    return Renderer(diagram).render(diagram)


# --------------------------------------------------------------- round-trip

def nlabel(items, iid):
    """Устойчивая метка узла: не зависит от конкретного id."""
    item = items.get(iid)
    if not isinstance(item, dict):
        return "?%s" % iid
    typ = item.get("type")
    text = plain(item)
    if typ == "branch":
        return "branch#%s:%s" % (item.get("branchId"), text)
    if typ == "end":
        return "END"
    return "%s:%s" % (typ, text)


def canonical(diagram):
    """Каноническое описание графа: обход детерминирован (соседей берём в
    порядке их меток, а не в порядке one/two), а у question сравниваем
    семантические Да/Нет, а не сырые one/two."""
    items = diagram.get("items", {})
    pairs = [(it.get("branchId", 0), iid)
             for iid, it in items.items()
             if isinstance(it, dict) and it.get("type") == "branch"]
    if not pairs:
        return "[]"
    queue = [sorted(pairs)[0][1]]
    order, i = {}, 0
    while i < len(queue):
        cur = queue[i]
        i += 1
        if cur in order:
            continue
        order[cur] = len(order)
        item = items.get(cur)
        if not isinstance(item, dict):
            continue
        targets = [item.get(f) for f in ("one", "two", "side")]
        targets = sorted({t for t in targets if t and t in items and t not in order},
                         key=lambda t: nlabel(items, t))
        for t in targets:
            if t not in queue:
                queue.append(t)

    def ref_of(tgt):
        if tgt is None:
            return "-"
        return str(order[tgt]) if tgt in order else "?%s" % tgt

    def ref(item, field):
        return ref_of(item.get(field))

    out = []
    for iid in queue:
        if iid not in order:
            continue
        item = items[iid]
        typ = item.get("type")
        if typ == "question":
            flag1 = item.get("flag1", 1)
            yes = item.get("one") if flag1 == 1 else item.get("two")
            no = item.get("two") if flag1 == 1 else item.get("one")
            out.append("question|%s|yes=%s|no=%s" % (plain(item), ref_of(yes), ref_of(no)))
        else:
            out.append("%s|%s|%s|%s" % (typ, plain(item), ref(item, "one"), ref(item, "two")))
    return "\n".join(out)


def paths(diagram, cap=3000):
    """Множество путей от стартовой ветки до терминатора.

    В отличие от canonical(), нечувствительно к дублированию узлов: если
    в исходнике две ветки сходятся на одну иконку (слияние), DSL развернёт
    её в две копии - графы разные, а набор путей одинаковый.
    """
    items = diagram.get("items", {})
    pairs = [(it.get("branchId", 0), iid)
             for iid, it in items.items()
             if isinstance(it, dict) and it.get("type") == "branch"]
    if not pairs:
        return []
    start = sorted(pairs)[0][1]
    out = []

    def walk(iid, acc, seen, depth):
        if len(out) >= cap or depth > 80:
            out.append(acc + ["<срез>"])
            return
        item = items.get(iid)
        if not isinstance(item, dict):
            out.append(acc + ["?%s" % iid])
            return
        typ = item.get("type")
        if typ == "branch":
            # ветка - не тупик: фиксируем имя и идём дальше по её вертелу
            acc = acc + ["@" + (plain(item) or "ветка#%s" % item.get("branchId"))]
            if iid in seen:
                out.append(acc + ["<цикл>"])
                return
            walk(item.get("one"), acc, seen | {iid}, depth + 1)
            return
        if typ == "end":
            out.append(acc + ["КОНЕЦ"])
            return
        if iid in seen:
            out.append(acc + ["<цикл:%s>" % nlabel(items, iid)])
            return
        acc = acc + ["%s:%s" % (typ, plain(item))]
        seen = seen | {iid}
        if typ == "question":
            flag1 = item.get("flag1", 1)
            yes = item.get("one") if flag1 == 1 else item.get("two")
            no = item.get("two") if flag1 == 1 else item.get("one")
            walk(yes, acc + ["да"], seen, depth + 1)
            walk(no, acc + ["нет"], seen, depth + 1)
            return
        if typ == "select":
            case = item.get("one")
            while case and case not in seen:
                node = items.get(case, {})
                walk(node.get("one"), acc + ["вариант:%s" % (plain(node) or "остальные")],
                     seen | {case}, depth + 1)
                case = node.get("two")
            return
        walk(item.get("one"), acc, seen, depth + 1)

    walk(start, [], frozenset(), 0)
    return sorted(out)


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("to-drakon", "to-dsl", "roundtrip"):
        print(__doc__)
        return 2
    cmd = sys.argv[1]

    def load_json(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    if cmd == "to-drakon":
        with open(sys.argv[2], encoding="utf-8") as fh:
            text = fh.read()
        diagram = dsl_to_drakon(text)
        with open(sys.argv[3], "w", encoding="utf-8") as fh:
            json.dump(diagram, fh, ensure_ascii=False, indent=2)
        print("OK: %s -> %s (%d items)" % (sys.argv[2], sys.argv[3], len(diagram["items"])))
        return 0

    if cmd == "to-dsl":
        diagram = load_json(sys.argv[2])
        text = drakon_to_dsl(diagram)
        if len(sys.argv) > 3:
            with open(sys.argv[3], "w", encoding="utf-8") as fh:
                fh.write(text)
            print("OK: %s -> %s" % (sys.argv[2], sys.argv[3]))
        else:
            sys.stdout.write(text)
        return 0

    # roundtrip
    diagram = load_json(sys.argv[2])
    text = drakon_to_dsl(diagram)
    again = dsl_to_drakon(text)
    a, b = canonical(diagram), canonical(again)
    if len(sys.argv) > 3:
        with open(sys.argv[3], "w", encoding="utf-8") as fh:
            fh.write(text)
    if a == b:
        print("OK: графы совпали (%d узлов)" % len(a.split("\n")))
        return 0
    pa, pb = paths(diagram), paths(again)
    if pa and pa == pb:
        print("OK: потоки совпали (%d пути); граф развёрнут - общие иконки "
              "продублированы, как это делает DSL" % len(pa))
        return 0
    print("РАСХОЖДЕНИЕ:")
    for x, y in zip(a.split("\n"), b.split("\n")):
        if x != y:
            print("  было: %s" % x)
            print("  стало: %s" % y)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DslError as exc:
        print("ОШИБКА DSL: %s" % exc)
        sys.exit(1)
