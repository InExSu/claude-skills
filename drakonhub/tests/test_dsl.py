#!/usr/bin/env python3
"""Регресс-тесты DSL-слоя drakonhub. Только стандартная библиотека.

Запуск из папки скилла:
  python3 tests/test_dsl.py

Контракт, который держат тесты:

* фикстуры tests/fixtures/*.dsl каноничны: build -> check без ошибок, а
  diagram_to_dsl возвращает ровно тот же текст (fidelity, не только roundtrip);
* канон устойчив: DSL -> .drakon -> DSL -> .drakon -> DSL совпадает;
* регрессии: комментарий перед первой иконкой ветки не уводит соседа из
  ветки; выбор не втягивает продолжение в первый case; параллельный блок не
  теряет хвост после parend; verify отклоняет неканонический источник.
"""

import contextlib
import glob
import io
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from drakon_dsl import cmd_verify  # noqa: E402
from drakon_format import (  # noqa: E402
    build_diagram,
    check_drakon,
    diagram_to_dsl,
    load_doc,
    parse_dsl,
)

FIXTURES_DIR = os.path.join(ROOT, "tests", "fixtures")
TEMPLATES_DIR = os.path.join(ROOT, "templates")


def load_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def fixture_names():
    names = sorted(os.path.basename(p)
                   for p in glob.glob(os.path.join(FIXTURES_DIR, "*.dsl")))
    return names


class DslFidelityTest(unittest.TestCase):
    def test_fixtures_canonical_fidelity(self):
        """Источник = канон своего же графа: иконки и ветки не съезжают."""
        self.assertTrue(fixture_names(), "нет фикстур в tests/fixtures")
        for name in fixture_names():
            with self.subTest(fixture=name):
                source = load_text(os.path.join(FIXTURES_DIR, name))
                doc = build_diagram(parse_dsl(source))
                errors, _ = check_drakon(doc, name)
                self.assertEqual([], errors, name)
                canon = diagram_to_dsl(doc)
                self.assertEqual(source.rstrip("\n"), canon.rstrip("\n"),
                                 "%s: канон разошёлся с источником" % name)

    def test_fixtures_canon_is_stable(self):
        """Канон идемпотентен: DSL -> .drakon -> DSL не плывёт при повторе."""
        for name in fixture_names():
            with self.subTest(fixture=name):
                source = load_text(os.path.join(FIXTURES_DIR, name))
                first = diagram_to_dsl(build_diagram(parse_dsl(source)))
                second = diagram_to_dsl(build_diagram(parse_dsl(first)))
                self.assertEqual(first, second, name)

    def test_templates_dsl_canonical(self):
        """Коммитнутые .dsl-шаблоны обязаны быть каноническими."""
        paths = sorted(glob.glob(os.path.join(TEMPLATES_DIR, "*.dsl")))
        self.assertTrue(paths, "нет .dsl-шаблонов")
        for path in paths:
            with self.subTest(template=os.path.basename(path)):
                source = load_text(path)
                canon = diagram_to_dsl(build_diagram(parse_dsl(source)))
                self.assertEqual(source.rstrip("\n"), canon.rstrip("\n"),
                                 path)


class CommentPlacementTest(unittest.TestCase):
    def test_comment_first_branch_keeps_wiring(self):
        """Комментарий первым ребёнком ветки не выкидывает ветку из вопроса.

        Раньше здесь ломался разбор пост-доминаторов: комментарий выпадал из
        графа, вопрос «схлопывался» на соседа, и верная ветка уезжала за вопрос.
        """
        doc = build_diagram(parse_dsl(
            load_text(os.path.join(FIXTURES_DIR, "comment-first-no.dsl"))))
        items = doc["items"]
        question = next(n for n in items.values() if n.get("type") == "question")
        yes = items[question["one"]]
        no = items[question["two"]]
        self.assertEqual("action", yes.get("type"), "ветка «да» потерялась")
        self.assertEqual("Отправить отчёт", yes.get("content"))
        self.assertEqual("comment", no.get("type"))
        self.assertEqual("Запросить уточнение", items[no["one"]].get("content"))

    def test_comment_before_action_attached_to_next_icon(self):
        doc = build_diagram(parse_dsl(
            load_text(os.path.join(FIXTURES_DIR, "comment-before-action.dsl"))))
        items = doc["items"]
        comments = [n for n in items.values() if n.get("type") == "comment"]
        self.assertEqual(1, len(comments))
        self.assertEqual("Отправить отчёт",
                         items[comments[0]["one"]].get("content"))


class TailKeptTest(unittest.TestCase):
    def test_select_continuation_stays_after_select(self):
        """Продолжение после выбора не втягивается в первый case."""
        doc = build_diagram(parse_dsl(
            load_text(os.path.join(FIXTURES_DIR, "select-comment-first.dsl"))))
        canon = diagram_to_dsl(doc)
        self.assertEqual("  Сохранить результат", canon.split("\n")[-1])

    def test_parallel_block_tail_survives_drakon_to_dsl(self):
        """to-dsl не теряет иконки после parend (хвост был потерян молча)."""
        doc = load_doc(os.path.join(TEMPLATES_DIR, "parallel-and-timer.drakon"))
        canon = diagram_to_dsl(doc)
        self.assertIn("Собрать итог", canon)
        self.assertTrue(canon.rstrip().endswith("!pause Пауза перед завершением"),
                        canon)


class VerifyCommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.join(ROOT, ".cache", "test_verify")
        os.makedirs(self.tmp, exist_ok=True)

    def run_verify(self, text):
        path = os.path.join(self.tmp, "src.dsl")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cmd_verify(path)
        return code, out.getvalue()

    def test_canonical_source_passes(self):
        code, message = self.run_verify(
            load_text(os.path.join(FIXTURES_DIR, "comment-first-no.dsl")))
        self.assertEqual(0, code, message)

    def test_noncanonical_source_reports_diff(self):
        # Читаемый, но неканонический источник (без отступов): verify обязан
        # вернуть 1 и показать diff, а не промолчать.
        code, message = self.run_verify(
            "# Проба\nПроверить данные\n> Сверка с первоисточником\nОтправить отчёт\n")
        self.assertEqual(1, code, message)
        self.assertIn("канон разошёлся", message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
