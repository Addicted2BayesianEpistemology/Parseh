# SPDX-License-Identifier: GPL-3.0-or-later
"""Partial-word foreground colours: grammar, renderers and source edits."""
import sys
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app", ROOT / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import htmlgen  # noqa: E402
import mdparser  # noqa: E402
import segcolour  # noqa: E402
import store  # noqa: E402
import texgen  # noqa: E402


class ScannerTests(unittest.TestCase):
    CASES = (
        ("[[a[b]{crimson}c]]", "abc"),
        ("[[[a]{crimson}bc]]", "abc"),
        ("[[ab[c]{crimson}]]", "abc"),
        ("[[a[b]{crimson}[c]{indigo}d]]", "abcd"),
        ("[[[ab]{crimson}[cd]{indigo}]]", "abcd"),
        ("[[a[bc]{#C2185B}d]]", "abcd"),
        ("[[ک[ت]{crimson}[ا]{indigo}ب]]{translit:ketāb}", "کتاب"),
        ("[[日[本]{indigo}語]]{kana:にほんご translit:nihongo}", "日本語"),
    )

    def test_recognises_and_flattens_valid_runs(self):
        for source, plain in self.CASES:
            with self.subTest(source=source):
                nodes = list(segcolour.find_runs(source))
                self.assertEqual(1, len(nodes))
                self.assertEqual(plain, nodes[0].plain_text)
                self.assertEqual(plain, segcolour.flatten(source))

    def test_plain_double_brackets_and_malformed_runs_stay_literal(self):
        for source in ("[[ordinary brackets]]", "[[slot]]", "[[کتاب",
                       "[[ک[ت]{crimson}", "[[ک[ت]{red}اب]]",
                       "[[x[[a]{teal}b]]"):
            self.assertEqual([], list(segcolour.find_runs(source)), source)
            self.assertEqual(source, segcolour.flatten(source), source)

    def test_literal_invalid_piece_inside_valid_run_keeps_source_mapping(self):
        source = "[[x[y]{red}z[q]{teal}]]"
        node = next(segcolour.find_runs(source))
        self.assertEqual("x[y]{red}zq", node.plain_text)
        self.assertEqual(len(node.plain_text), len(node.positions))

    def test_outer_marks_belong_to_the_whole_run(self):
        node = next(segcolour.find_runs(
            "[[日[本]{indigo}語]]{kana:にほんご translit:nihongo}"))
        self.assertEqual("にほんご", node.mark("kana"))
        self.assertEqual("nihongo", node.mark("translit"))


class RenderTests(unittest.TestCase):
    def setUp(self):
        texgen.set_target("fa")
        htmlgen.set_target("fa")
        htmlgen.reset_state()

    def test_html_is_one_semantic_word_with_inline_visual_children(self):
        out = htmlgen.inline("[[ک[ت]{crimson}[ا]{indigo}ب]]{translit:ketāb}")
        self.assertEqual(1, out.count('class="fa segmented-colour-run"'))
        self.assertEqual(1, out.count('data-fa="کتاب"'))
        self.assertEqual(1, out.count('data-translit="ketāb"'))
        self.assertEqual(2, out.count('class="seg-colour fac'))
        self.assertEqual("کتاب", _text(out))

    def test_pdf_keeps_one_target_run_and_mono_drops_colours(self):
        source = "[[ک[ت]{crimson}[ا]{indigo}ب]]"
        colour = texgen.inline(source)
        self.assertTrue(colour.startswith(r"\pe{"), colour)
        self.assertIn(r"\segword{کتاب}", colour)
        self.assertEqual(4, colour.count(r"\segpiece"))
        self.assertEqual(2, colour.count(r"\color"))
        texgen.set_print(mono=True)
        try:
            self.assertEqual(r"\pe{کتاب}", texgen.inline(source))
        finally:
            texgen.set_print()

    def test_glossary_uses_flattened_word_and_outer_transliteration(self):
        md = ("---\ntitle: T\ntarget: fa\n---\n\n"
              "[[ک[ت]{crimson}[ا]{indigo}ب]]{translit:ketāb} = *book*\n")
        gloss = htmlgen.glosses(md)
        self.assertEqual(("کتاب", "ketāb", "book"),
                         (gloss[0]["fa"], gloss[0]["translit"], gloss[0]["tr"]))

    def test_vocabulary_heading_keeps_one_flattened_headword(self):
        md = ("---\ntitle: T\ntarget: fa\n---\n\n"
              "## [[ک[ت]{crimson}[ا]{indigo}ب]] | ketāb | origin\n")
        fm, blocks = mdparser.parse(md)
        voce = next(b for b in blocks if b["type"] == "voce")
        self.assertEqual("کتاب", voce["fa"])
        self.assertEqual([("ک", None), ("ت", "crimson"),
                          ("ا", "indigo"), ("ب", None)], voce["fa_segments"])
        page = htmlgen.render_document(md)["html"]
        self.assertIn('class="voce-fa segmented-colour-run"', page)
        self.assertIn('data-fa="کتاب"', page)

    def test_segmented_run_counts_as_one_run_in_script_and_latin_targets(self):
        htmlgen.set_target("fa")
        self.assertEqual(["کتاب"], htmlgen.target_runs("[[ک[ت]{crimson}اب]]"))
        htmlgen.set_target("en")
        self.assertEqual(["unbreakable"],
                         htmlgen.target_runs("[[un[break]{crimson}able]]"))

    def test_full_text_search_indexes_the_flattened_word(self):
        with tempfile.TemporaryDirectory() as td:
            old = store.use_library(td)
            try:
                store.create("---\ntitle: Segmented search\ntarget: fa\n---\n\n"
                             "[[ک[ت]{crimson}[ا]{indigo}ب]]\n")
                found = store.list_docs(q="کتاب", intext=True)
                self.assertEqual(["Segmented search"], [d["title"] for d in found])
            finally:
                store.use_library(old)

    @unittest.skipUnless(shutil.which("xelatex"), "needs xelatex")
    def test_real_pdf_engine_accepts_segmented_persian(self):
        md = ("---\ntitle: T\nlang: en\ntarget: fa\n---\n\n"
              "کتاب ⏎ [[ک[ت]{crimson}[ا]{indigo}ب]]\n")
        tex = texgen.generate(*mdparser.parse(md), colophon=False)
        with tempfile.TemporaryDirectory(prefix="parseh-segcolour-") as td:
            main = Path(td) / "main.tex"
            main.write_text(tex, encoding="utf-8")
            done = subprocess.run([shutil.which("xelatex"),
                                   "-interaction=nonstopmode", "-halt-on-error",
                                   "main.tex"], cwd=td, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, timeout=90)
            self.assertEqual(0, done.returncode, done.stdout[-4000:])
            pdf = Path(td) / "main.pdf"
            self.assertTrue(pdf.exists())
            try:
                import fitz
            except ImportError:
                return
            page = fitz.open(pdf)[0]
            lines, seen_lines = [], []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    shown = "".join(span["text"] for span in line["spans"])
                    seen_lines.append(shown)
                    if "کتاب" in shown or "باتک" in shown or shown == "\uffff" * 4:
                        lines.append(fitz.Rect(line["bbox"]))
            self.assertEqual(2, len(lines), seen_lines)

            def ink(rect):
                pix = page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=rect + (-2, -2, 2, 2),
                                      alpha=False)
                raw, n = pix.samples, pix.n
                pts = {(x, y) for y in range(pix.height) for x in range(pix.width)
                       if min(raw[(y * pix.width + x) * n:(y * pix.width + x) * n + 3]) < 245}
                x0, x1 = min(x for x, _ in pts), max(x for x, _ in pts)
                y0, y1 = min(y for _, y in pts), max(y for _, y in pts)
                return {(x - x0, y - y0) for x, y in pts}, (x1 - x0 + 1, y1 - y0 + 1)

            plain, psize = ink(lines[0])
            coloured, csize = ink(lines[1])
            self.assertLessEqual(abs(psize[0] - csize[0]), 2,
                                 (psize, csize, "colour changed the shaped word's width"))
            best = 0.0
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    shifted = {(x + dx, y + dy) for x, y in coloured}
                    best = max(best, len(plain & shifted) / len(plain | shifted))
            self.assertGreater(best, .78,
                               "colour boundaries changed Persian contextual glyph forms: %.3f" % best)
            cpix = page.get_pixmap(matrix=fitz.Matrix(4, 4),
                                   clip=lines[1] + (-2, -2, 2, 2), alpha=False)
            rgb = [cpix.samples[i:i + 3] for i in range(0, len(cpix.samples), cpix.n)]
            self.assertTrue(any(r > 90 and r > g * 1.45 and r > b * 1.25
                                for r, g, b in rgb), "crimson piece did not reach the PDF")
            self.assertTrue(any(b > 90 and b > r * 1.45 and b > g * 1.35
                                for r, g, b in rgb), "indigo piece did not reach the PDF")


def _text(html):
    import re
    return re.sub(r"<[^>]+>", "", html)


def select(source, visible, occurrence=0):
    at = -1
    for _ in range(occurrence + 1):
        at = source.index(visible, at + 1)
    return at, at + len(visible)


class EditorRewriteTests(unittest.TestCase):
    def paint(self, source, visible, colour, occurrence=0):
        a, b = select(source, visible, occurrence)
        return store.colour_selection_markdown(source, a, b, colour)[0]

    def test_partial_word(self):
        self.assertEqual("[[ک[تا]{crimson}ب]]", self.paint("کتاب", "تا", "crimson"))

    def test_second_colour_and_recolour_subsection(self):
        self.assertEqual("[[ک[ت]{crimson}[ا]{indigo}ب]]",
                         self.paint("[[ک[تا]{crimson}ب]]", "ا", "indigo"))
        self.assertEqual("[[ک[ت]{teal}[ا]{crimson}[ب]{teal}]]",
                         self.paint("[[ک[تاب]{teal}]]", "ا", "crimson"))

    def test_marks_and_base_colour_survive_splitting(self):
        self.assertEqual("[[ک[تا]{crimson}ب]]{translit:ketāb}",
                         self.paint("[کتاب]{translit:ketāb}", "تا", "crimson"))
        self.assertEqual("[[[ک]{teal}[تا]{crimson}[ب]{teal}]]{translit:ketāb}",
                         self.paint("[کتاب]{teal translit:ketāb}", "تا", "crimson"))

    def test_no_colour_and_uniform_colour_canonicalise(self):
        mixed = "[[[ک]{teal}[تا]{crimson}[ب]{teal}]]"
        self.assertEqual("[[[ک]{teal}[ت]{crimson}ا[ب]{teal}]]",
                         self.paint(mixed, "ا", None))
        self.assertEqual("کتاب", self.paint("[[ک[تاب]{teal}]]", "تاب", None))
        self.assertEqual("[کتاب]{teal}",
                         self.paint("[[[ک]{teal}[تاب]{crimson}]]", "تاب", "teal"))

    def test_complete_phrase_uses_ordinary_mark(self):
        self.assertEqual("[کتاب خوب]{teal}", self.paint("کتاب خوب", "کتاب خوب", "teal"))

    def test_crossing_words_colours_exact_intersections(self):
        source = "کتاب خوب"
        a, b = source.index("ت"), source.index("و", source.index(" ")) + 1
        out = store.colour_selection_markdown(source, a, b, "teal")[0]
        self.assertEqual("[[ک[تاب]{teal}]] [[[خو]{teal}ب]]", out)

    def test_crossing_existing_annotations_preserves_their_semantics(self):
        source = "[[ک[تا]{crimson}ب]]{translit:ketāb} خوب"
        a, b = source.index("ا"), source.rindex("و") + 1
        out = store.colour_selection_markdown(source, a, b, "indigo")[0]
        self.assertEqual(
            "[[ک[ت]{crimson}[اب]{indigo}]]{translit:ketāb} [[[خو]{indigo}ب]]",
            out)

        source = "[کتاب]{teal translit:ketāb} خوب"
        a, b = source.index("ت"), source.rindex("و") + 1
        out = store.colour_selection_markdown(source, a, b, "crimson")[0]
        self.assertEqual(
            "[[[ک]{teal}[تاب]{crimson}]]{translit:ketāb} [[[خو]{crimson}ب]]",
            out)

    def test_linguistic_cloud_edit_preserves_segments(self):
        source = "[[ک[ت]{crimson}[ا]{indigo}ب]]{translit:ketāb}"
        self.assertEqual("[[ک[ت]{crimson}[ا]{indigo}ب]]{translit:ketâb}",
                         store.retranslit_markdown(source, "کتاب", 0, "ketâb"))


if __name__ == "__main__":
    unittest.main()
