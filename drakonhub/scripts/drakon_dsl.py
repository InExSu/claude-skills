#!/usr/bin/env python3
"""drakon_dsl: компактный DSL вместо ручной сборки JSON.

Использование (из папки скилла):
  python3 scripts/drakon_dsl.py to-drakon workout.dsl out.drakon
  python3 scripts/drakon_dsl.py to-dsl    out.drakon out.dsl
  python3 scripts/drakon_dsl.py roundtrip minimal.drakon

roundtrip проверяет каноническую форму: .drakon -> DSL -> .drakon -> DSL,
оба DSL-текста должны совпасть.

Только стандартная библиотека.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drakon_format import (  # noqa: E402
    DslError,
    build_diagram,
    check_drakon,
    diagram_to_dsl,
    load_doc,
    parse_dsl,
    save_doc,
)


def read_text(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        raise DslError("файл не найден: %s" % path)


def cmd_to_drakon(src, dst):
    try:
        roots = parse_dsl(read_text(src))
        doc = build_diagram(roots)
    except DslError as exc:
        print("ошибка: %s: %s" % (src, exc))
        return 1
    errors, remarks = check_drakon(doc, dst)
    if errors:
        for message in errors:
            print("ошибка: %s" % message)
        return 1
    save_doc(doc, dst)
    print("OK: %s -> %s (%d иконок)" % (src, dst, len(doc["items"])))
    return 0


def cmd_to_dsl(src, dst):
    try:
        doc = load_doc(src)
    except ValueError as exc:
        print("ошибка: %s" % exc)
        return 1
    if doc.get("type") != "drakon":
        print("ошибка: %s: to-dsl работает только с .drakon" % src)
        return 1
    try:
        text = diagram_to_dsl(doc)
    except DslError as exc:
        print("ошибка: %s: %s" % (src, exc))
        return 1
    with open(dst, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    print("OK: %s -> %s" % (src, dst))
    return 0


def cmd_roundtrip(src):
    try:
        doc = load_doc(src)
    except ValueError as exc:
        print("ошибка: %s" % exc)
        return 1
    if doc.get("type") != "drakon":
        print("ошибка: %s: roundtrip работает только с .drakon" % src)
        return 1
    try:
        first = diagram_to_dsl(doc)
        rebuilt = build_diagram(parse_dsl(first))
        errors, _ = check_drakon(rebuilt, src)
        if errors:
            for message in errors:
                print("ошибка: %s" % message)
            return 1
        second = diagram_to_dsl(rebuilt)
    except DslError as exc:
        print("ошибка: %s: %s" % (src, exc))
        return 1
    if first != second:
        print("ошибка: %s: канонические графы разошлись" % src)
        old, new = first.split("\n"), second.split("\n")
        for index, (left, right) in enumerate(zip(old, new), 1):
            if left != right:
                print("  строка %d:\n    было:  %s\n    стало: %s" % (index, left, right))
                break
        if len(old) != len(new):
            print("  разная длина: %d против %d строк" % (len(old), len(new)))
        return 1
    print("OK: графы совпали (%d узлов)" % len(doc["items"]))
    return 0


def main(argv):
    if len(argv) == 4 and argv[1] == "to-drakon":
        return cmd_to_drakon(argv[2], argv[3])
    if len(argv) == 4 and argv[1] == "to-dsl":
        return cmd_to_dsl(argv[2], argv[3])
    if len(argv) == 3 and argv[1] == "roundtrip":
        return cmd_roundtrip(argv[2])
    print("использование:")
    print("  drakon_dsl.py to-drakon <вход.dsl> <выход.drakon>")
    print("  drakon_dsl.py to-dsl    <вход.drakon> <выход.dsl>")
    print("  drakon_dsl.py roundtrip <файл.drakon>")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
