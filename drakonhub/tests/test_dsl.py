#!/usr/bin/env python3
"""Регресс-тесты DSL-слоя drakonhub. Только стандартная библиотека.

Запуск из папки скилла:
  python3 tests/test_dsl.py

Контракт, который держат тесты:

* фикстуры tests/fixtures/*.dsl каноничны: build -> check без ошибок, а
  diagram_to_dsl возвращает ровно тот же текст (fidelity, не только roundtrip);
* канон устойчив: DSL -> .drakon -> DSL -> .drakon -> DSL совпадает;
* выноска `*` — плашка в ряду над диаграммой: без наложений, размер
  посчитан под перенос текста движком (14px Arial, maxWidth 400);
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
    CALLOUT_ROW_BOTTOM,
    CALLOUT_ROW_LEFT,
    CALLOUT_TAIL,
    CALLOUT_WIDTH_MAX,
    build_diagram,
    callout_box,
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


class CalloutPlacementTest(unittest.TestCase):
    """Выноски: ряд над диаграммой, без наложений, плашка по размеру текста."""

    SOURCE = (
        "# Проба\n"
        "* Короткая выноска\n"
        "Собрать данные\n"
        "* Длинная выноска про раскладку в редакторе: текст переносится "
        "по словам и занимает несколько строк подряд\n"
        "Отправить отчёт\n"
    )

    @staticmethod
    def callouts(doc):
        return [n for n in doc["items"].values() if n.get("type") == "callout"]

    def test_callouts_do_not_overlap_and_sit_above(self):
        """Раньше все выноски получали одну точку и ложились друг на друга."""
        callouts = self.callouts(build_diagram(parse_dsl(self.SOURCE)))
        self.assertEqual(2, len(callouts), "потеряли выноски")
        boxes = [(c["left"], c["top"], c["left"] + c["width"], c["top"] + c["py"])
                 for c in callouts]
        (left1, top1, right1, bottom1), (left2, top2, right2, bottom2) = boxes
        no_x = right1 <= left2 or right2 <= left1
        no_y = bottom1 <= top2 or bottom2 <= top1
        self.assertTrue(no_x or no_y, "выноски наложились: %s и %s" % (boxes[0], boxes[1]))
        for callout in callouts:
            self.assertLessEqual(callout["top"] + callout["py"], -40,
                                 "хвост выноски заходит на поток")
            self.assertEqual(CALLOUT_ROW_BOTTOM + CALLOUT_TAIL,
                             callout["top"] + callout["py"],
                             "конец хвоста не на общей линии ряда")
            self.assertEqual(callout["width"] // 2, callout["px"],
                             "хвост не по центру плашки")

    def test_plate_grows_with_text_and_fits_engine_measure(self):
        """Плашка не меньше замера движка, иначе текст вылезает из неё."""
        short, long = self.callouts(build_diagram(parse_dsl(self.SOURCE)))
        self.assertLess(short["height"], long["height"])
        self.assertLessEqual(long["width"], CALLOUT_WIDTH_MAX)
        for text, measured in (
            ("Заметка средней длины: проверка переноса по словам и оценки строк",
             56.375),
            ("Очень длинная заметка про поведение выносок в редакторе. " * 8,
             201.875),
        ):
            with self.subTest(text=text[:30]):
                _, height = callout_box(text)
                self.assertGreaterEqual(height, measured)

    def test_callout_inside_block_shares_row(self):
        """Выноска внутри ветки попадает в тот же ряд (не в иконки)."""
        doc = build_diagram(parse_dsl(
            "# Проба\n? Устал?\n  да:\n    * Отдохнуть подольше\n    Стоп\n"
            "  нет:\n    Продолжить\n"))
        callouts = self.callouts(doc)
        self.assertEqual(1, len(callouts))
        self.assertEqual(CALLOUT_ROW_LEFT, callouts[0]["left"])

    def test_many_callouts_keep_canon_order(self):
        """С 8+ выносками id ≥ 10: лексикографическая сортировка рвала канон."""
        source = ("# Проба\n"
                  + "".join("* Заметка номер %d\n" % i for i in range(1, 9))
                  + "Собрать данные\nОтправить отчёт\n")
        canon = diagram_to_dsl(build_diagram(parse_dsl(source)))
        order = [line for line in canon.split("\n") if line.startswith("*")]
        self.assertEqual(["* Заметка номер %d" % i for i in range(1, 9)], order)


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
