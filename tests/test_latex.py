# SPDX-License-Identifier: GPL-3.0-or-later
"""LaTeX drawings (TO-DO §8.39): the ::::latex fence, theme names, a rename's
rewrite of the text, and the key a drawing is kept under.  No TeX is run:
what a compile makes is checked by hand (docs/releasing.md).  The themes'
store is redirected to a temporary folder, so config/ is never written."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for folder in (ROOT / "lib", ROOT / "markdown" / "exlex", ROOT / "markdown" / "app"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import latexdraw    # noqa: E402
import latexthemes  # noqa: E402
import mdparser     # noqa: E402


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.was = latexthemes.STORE, latexdraw.DRAWN
        latexthemes.STORE = os.path.join(self.tmp.name, "config", "latex.json")
        latexdraw.DRAWN = os.path.join(self.tmp.name, "latex")

    def tearDown(self):
        latexthemes.STORE, latexdraw.DRAWN = self.was
        self.tmp.cleanup()


class TheFence(unittest.TestCase):
    def blocks(self, md):
        return [b for b in mdparser.parse(md)[1] if b["type"] == "latex"]

    def test_a_block_with_its_theme_and_layout(self):
        b, = self.blocks("::::latex chemistry {width=45 align=left}\n\\ce{H2O}\n::::\n")
        self.assertEqual((b["theme"], b["tex"], b["align"]), ("chemistry", "\\ce{H2O}", "left"))
        self.assertEqual(b["width"], 45)
        self.assertFalse(b["errors"])

    def test_no_theme_no_width(self):
        b, = self.blocks("::::latex\nx\n::::\n")
        self.assertIsNone(b["theme"] or None)
        self.assertIsNone(b["width"])
        self.assertEqual(b["align"], "center")

    def test_three_colons_inside_do_not_close_it(self):
        b, = self.blocks("::::latex drawing\n\\node {:::};\n:::\n::::\nafter\n")
        self.assertIn(":::", b["tex"])
        self.assertTrue(any(x["type"] == "para" for x in mdparser.parse(
            "::::latex drawing\n:::\n::::\nafter\n")[1]))

    def test_an_unclosed_block_says_so(self):
        b, = self.blocks("::::latex\nx\n")
        self.assertTrue(b["errors"])

    def test_math_is_untouched(self):
        kinds = [b["type"] for b in mdparser.parse(":::math\nx^2\n:::\n")[1]]
        self.assertNotIn("latex", kinds)

    def test_a_card_field_keeps_it_and_the_exercise_goes_on(self):
        md = (":::exercise flashcard\ntype: jolly\nfront: |\n  ::::latex\n  \\ce{H2O}\n  ::::\n"
              "back: water\n:::\n\nafter\n")
        blocks = mdparser.parse(md)[1]
        self.assertTrue(any(b["type"] == "exercise" for b in blocks))
        self.assertEqual([b for b in latexthemes.blocks_in(md)][0]["tex"], "\\ce{H2O}")

    def test_the_light_scanner_finds_a_block_in_a_box(self):
        b, = latexthemes.blocks_in("> ::::latex drawing\n> x\n> ::::\n")
        self.assertEqual((b["theme"], b["tex"], b["closed"]), ("drawing", "x", True))


class Names(unittest.TestCase):
    def test_one_word_any_script(self):
        for good in ("chemistry", "شیمی", "化学", "my-theme_2"):
            self.assertTrue(latexthemes.name_ok(good), good)
        for bad in ("", "two words", "a/b", "x" * 41):
            self.assertFalse(latexthemes.name_ok(bad), bad)

    def test_case_does_not_matter(self):
        self.assertEqual(latexthemes.name_key("Chemistry"), latexthemes.name_key("chemistry"))


class Rename(unittest.TestCase):
    def test_only_the_name_on_the_opening_line(self):
        md = ("::::latex Chemistry {width=40}\n\\ce{chemistry}\n::::\n"
              "> ::::latex chemistry\n> x\n> ::::\n::::latex drawing\ny\n::::\n")
        out, n = latexthemes.rename_in_text(md, "chemistry", "chem")
        self.assertEqual(n, 2)
        self.assertIn("::::latex chem {width=40}", out)
        self.assertIn("> ::::latex chem\n", out)
        self.assertIn("\\ce{chemistry}", out)
        self.assertIn("::::latex drawing", out)

    def test_an_editor_catches_up(self):
        mark = latexthemes.rename_mark()
        latexthemes.log_rename("zzold", "zznew")
        self.assertIn("::::latex zznew", latexthemes.catch_up("::::latex zzold\nx\n::::\n", mark))
        self.assertIn("::::latex zzold",
                      latexthemes.catch_up("::::latex zzold\nx\n::::\n", latexthemes.rename_mark()))


class Themes(Store):
    def test_starters_and_the_default(self):
        names = [t["name"] for t in latexthemes.themes()]
        self.assertEqual(names[:3], ["default", "chemistry", "drawing"])
        self.assertEqual(latexthemes.default_name(), "default")
        self.assertFalse(os.path.exists(os.path.join(ROOT, "config", "latex.json.tmp")))

    def test_a_missing_theme_is_said(self):
        p = latexdraw.plan("x", "nosuch")
        self.assertFalse(p["ok"])
        self.assertEqual(p["fix"], {"kind": "theme-missing", "theme": "nosuch"})

    def test_the_key_follows_the_drawing_not_the_name(self):
        a = latexthemes.resolve("chemistry")
        b = dict(a, name="renamed")
        self.assertEqual(latexdraw.key_of("x", a, "s"), latexdraw.key_of("x", b, "s"))
        self.assertNotEqual(latexdraw.key_of("x", a, "s"),
                            latexdraw.key_of("x", latexthemes.resolve("drawing"), "s"))
        self.assertNotEqual(latexdraw.key_of("x", a, "s"), latexdraw.key_of("x", a, "t"))

    def test_mhchem_only_where_ticked(self):
        self.assertIn("mhchem", latexthemes.resolve("chemistry")["preamble"])
        self.assertNotIn("mhchem", latexthemes.resolve("default")["preamble"])

    def test_export_and_import_under_a_free_name(self):
        data = latexthemes.export_bytes("chemistry")
        theme = latexthemes.read_export(data)
        with self.assertRaises(latexthemes.ThemeError):
            latexthemes.import_theme(theme, "drawing")
        latexthemes.import_theme(theme, "chem2")
        self.assertIsNotNone(latexthemes.find("CHEM2"))


if __name__ == "__main__":
    unittest.main()
