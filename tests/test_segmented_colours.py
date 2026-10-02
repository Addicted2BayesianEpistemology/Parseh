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

    def test_nested_target_mark_keeps_the_run_and_no_placeholder(self):
        source = "[[[ک[ت]{crimson}[ا]{indigo}ب]]]{tl}"
        tex = texgen.inline(source)
        self.assertIn(r"\segword{کتاب}", tex)
        self.assertNotIn("[[", tex)
        self.assertNotIn("{tl}", tex)
        self.assertNotIn("\x05", tex)
        shown = htmlgen.inline(source)
        self.assertEqual("کتاب", _text(shown))
        self.assertEqual(1, shown.count("segmented-colour-run"))

    def test_exercise_prompt_keeps_segmented_run_whole(self):
        md = ("---\ntitle: T\ntarget: fa\n---\n\n"
              ":::exercise single-choice\n"
              "prompt: Pick [[ک[ت]{crimson}[ا]{indigo}ب]] now.\n"
              "- [x] yes\n- [ ] no\n:::\n")
        tex = texgen.generate(*mdparser.parse(md), colophon=False)
        self.assertEqual(1, tex.count(r"\segword{کتاب}"))
        self.assertNotIn("Pick [[", tex)
        page = htmlgen.render_document(md)["html"]
        self.assertEqual(1, page.count("segmented-colour-run"))

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

    @unittest.skipUnless(shutil.which("xelatex") and shutil.which("pdftoppm"),
                         "needs xelatex and pdftoppm")
    def test_real_pdf_engine_renders_colours_in_every_container(self):
        word = "[[ک[ت]{teal}[ا]{indigo}ب]]"
        cases = {
            "paragraph": word + "\n",
            "heading": "## A %s title\n" % word,
            "target_mark": "[%s]{tl}\n" % word,
            "prompt": (":::exercise single-choice\n"
                       "prompt: Pick %s now.\n"
                       "- [x] yes\n- [ ] no\n:::\n" % word),
        }
        with tempfile.TemporaryDirectory(prefix="parseh-segcolour-") as td:
            fonts = Path(td) / "fonts"
            fonts.mkdir()
            for name in ("Vazirmatn-Regular.ttf", "Vazirmatn-Bold.ttf"):
                shutil.copy2(ROOT / "markdown" / "exlex" / "assets" / "fonts" / name,
                             fonts / name)
            for name, body in cases.items():
                with self.subTest(container=name):
                    md = "---\ntitle: T\nlang: en\ntarget: fa\n---\n\n" + body
                    tex = texgen.generate(*mdparser.parse(md), colophon=False)
                    self.assertEqual(1, tex.count(r"\segword{کتاب}"))
                    self.assertNotIn("[[", tex)
                    self.assertNotIn("\x05", tex)
                    main = Path(td) / (name + ".tex")
                    main.write_text(tex, encoding="utf-8")
                    done = subprocess.run(
                        [shutil.which("xelatex"), "-interaction=nonstopmode",
                         "-halt-on-error", main.name], cwd=td, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True, timeout=90)
                    self.assertEqual(0, done.returncode, done.stdout[-4000:])
                    pdf = Path(td) / (name + ".pdf")
                    self.assertTrue(pdf.exists())
                    raster = subprocess.run(
                        [shutil.which("pdftoppm"), "-r", "220", "-f", "1",
                         "-singlefile", str(pdf), str(Path(td) / name)], cwd=td,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=90)
                    self.assertEqual(0, raster.returncode, raster.stdout[-2000:])
                    colours = list(_ppm_pixels(Path(td) / (name + ".ppm")))
                    teal = sum(g > 55 and b > 50 and r < g * .65
                               and abs(g - b) < 35 for r, g, b in colours)
                    indigo = sum(b > 70 and b > r * 1.45 and b > g * 1.35
                                 for r, g, b in colours)
                    self.assertGreater(teal, 20, "teal piece did not reach the PDF")
                    self.assertGreater(indigo, 8, "indigo piece did not reach the PDF")


def _text(html):
    import re
    return re.sub(r"<[^>]+>", "", html)


def _ppm_pixels(path):
    """Read the P6 file emitted by pdftoppm without an optional image API."""
    raw = path.read_bytes()
    tokens, at = [], 0
    while len(tokens) < 4:
        while at < len(raw) and chr(raw[at]).isspace():
            at += 1
        if raw[at:at + 1] == b"#":
            at = raw.find(b"\n", at) + 1
            continue
        end = at
        while end < len(raw) and not chr(raw[end]).isspace():
            end += 1
        tokens.append(raw[at:end])
        at = end
    while at < len(raw) and chr(raw[at]).isspace():
        at += 1
    magic, width, height, maximum = tokens
    if magic != b"P6" or maximum != b"255":
        raise AssertionError("unexpected PPM header: %r" % (tokens,))
    pixels = raw[at:]
    expected = int(width) * int(height) * 3
    if len(pixels) != expected:
        raise AssertionError("PPM has %d bytes, expected %d" % (len(pixels), expected))
    return zip(pixels[0::3], pixels[1::3], pixels[2::3])


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
