#!/usr/bin/env python3
"""drakon_tool: проверка и чтение диаграмм ДРАКОН.

Использование (из папки скилла):
  python3 scripts/drakon_tool.py check diagram.drakon   # схема + правила ДРАКОН
  python3 scripts/drakon_tool.py read diagram.drakon    # псевдокод по веткам
  python3 scripts/drakon_tool.py read map.graf          # план ментальной карты

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


def cmd_check(path):
    try:
        doc = load_doc(path)
    except ValueError as exc:
        print("ошибка: %s" % exc)
        return 1
    kind = doc.get("type")
    if kind == "drakon":
        errors, remarks = check_drakon(doc, path)
    elif kind == "graf":
        errors, remarks = check_graf(doc, path), []
    else:
        print("ошибка: %s: неизвестный type %r (нужен drakon или graf)" % (path, kind))
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
    try:
        doc = load_doc(path)
    except ValueError as exc:
        print("ошибка: %s" % exc)
        return 1
    kind = doc.get("type")
    try:
        if kind == "drakon":
            print(diagram_to_dsl(doc))
        elif kind == "graf":
            print(graf_to_outline(doc))
        else:
            print("ошибка: %s: неизвестный type %r" % (path, kind))
            return 1
    except DslError as exc:
        print("ошибка: %s: %s" % (path, exc))
        return 1
    return 0


def main(argv):
    if len(argv) != 3 or argv[1] not in ("check", "read"):
        print("использование:")
        print("  drakon_tool.py check <файл.drakon|файл.graf>")
        print("  drakon_tool.py read  <файл.drakon|файл.graf>")
        return 2
    if argv[1] == "check":
        return cmd_check(argv[2])
    return cmd_read(argv[2])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
