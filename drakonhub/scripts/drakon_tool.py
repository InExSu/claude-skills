#!/usr/bin/env python3
"""drakon_tool: проверка и чтение диаграмм.

Использование (из папки скилла):
  python3 scripts/drakon_tool.py check diagram.drakon    # схема + правила ДРАКОН
  python3 scripts/drakon_tool.py read  diagram.drakon    # псевдокод по веткам
  python3 scripts/drakon_tool.py read  map.graf          # план ментальной карты
  python3 scripts/drakon_tool.py check flow.seq          # диаграмма последовательности
  python3 scripts/drakon_tool.py check order.sm          # машина состояний

ДРАКОН — основной формат. .seq и .sm — вспомогательные (Mermaid-цели).

Только стандартная библиотека.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drakon_format import (  # noqa: E402
    DslError,
    check_drakon,
    check_graf,
    diagram_to_dsl,
    graf_to_outline,
    load_doc,
)
from sequence_format import (  # noqa: E402
    SeqError,
    check_sequence,
    sequence_to_dsl,
)
from state_format import (  # noqa: E402
    StateError,
    check_state,
    state_to_dsl,
)


def read_text(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        raise ValueError("файл не найден: %s" % path)


def text_kind(path):
    """Определить вспомогательный текстовый формат по расширению."""
    lowered = path.lower()
    if lowered.endswith(".seq"):
        return "seq"
    if lowered.endswith(".sm"):
        return "sm"
    return None


def cmd_check(path):
    kind = text_kind(path)
    if kind is not None:
        try:
            text = read_text(path)
        except ValueError as exc:
            print("ошибка: %s" % exc)
            return 1
        errors, remarks = (check_sequence(text, path) if kind == "seq"
                           else check_state(text, path))
    else:
        try:
            doc = load_doc(path)
        except ValueError as exc:
            print("ошибка: %s" % exc)
            return 1
        doc_type = doc.get("type")
        if doc_type == "drakon":
            errors, remarks = check_drakon(doc, path)
        elif doc_type == "graf":
            errors, remarks = check_graf(doc, path), []
        else:
            print("ошибка: %s: неизвестный type %r (нужен drakon, graf, .seq или .sm)"
                  % (path, doc_type))
            return 1
    for message in remarks:
        print("замечание: %s" % message)
    for message in errors:
        print("ошибка: %s" % message)
    if errors:
        print("%s: ошибок: %d, замечаний: %d" % (path, len(errors), len(remarks)))
        return 1
    if remarks:
        print("%s: ошибок нет, замечаний: %d" % (path, len(remarks)))
        return 0
    print("OK: ошибок и замечаний нет")
    return 0


def cmd_read(path):
    kind = text_kind(path)
    try:
        if kind == "seq":
            print(sequence_to_dsl(read_text(path)))
        elif kind == "sm":
            print(state_to_dsl(read_text(path)))
        else:
            doc = load_doc(path)
            doc_type = doc.get("type")
            if doc_type == "drakon":
                print(diagram_to_dsl(doc))
            elif doc_type == "graf":
                print(graf_to_outline(doc))
            else:
                print("ошибка: %s: неизвестный type %r" % (path, doc_type))
                return 1
    except (DslError, SeqError, StateError) as exc:
        print("ошибка: %s: %s" % (path, exc))
        return 1
    except ValueError as exc:
        print("ошибка: %s" % exc)
        return 1
    return 0


def main(argv):
    if len(argv) != 3 or argv[1] not in ("check", "read"):
        print("использование:")
        print("  drakon_tool.py check <файл.drakon|.graf|.seq|.sm>")
        print("  drakon_tool.py read  <файл.drakon|.graf|.seq|.sm>")
        return 2
    if argv[1] == "check":
        return cmd_check(argv[2])
    return cmd_read(argv[2])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
