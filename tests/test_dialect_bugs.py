# SPDX-License-Identifier: GPL-3.0-or-later
"""Three places where the studio's Markdown dialect did not do what its
README says (markdown/README.md), each pinned by what the page and the
paper are given.

    python3 -m unittest discover -s tests -p test_dialect_bugs.py

- `->` is an arrow on paper as `→` is; it wrote a carriage return into the
  .tex (texgen.inline).
- `[…]{math}` starts at its own `[`; it started at the first `[` of the
  paragraph and swallowed the marks, links and blanks before it
  (texgen.MATH_RE).
- A table's separator cell needs one dash, as in GFM (`|-|-|`, `:-:`); it
  needed two, and a table written with one was a paragraph of pipes
  (mdparser._TABLE_SEP).
"""
import re
import sys
import unittest
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app", ROOT / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import htmlgen    # noqa: E402
import mdparser   # noqa: E402
import store      # noqa: E402
import texgen     # noqa: E402


def doc(body, target="fa"):
    return "---\ntitle: T\nlang: en\ntarget: %s\n---\n\n%s\n" % (target, body)


def paper(md):
    return texgen.generate(*mdparser.parse(md), colophon=False)


def page(md, preview=False):
    return htmlgen.render_document(md, editor_preview=preview)["html"]


class ArrowTests(unittest.TestCase):
    """`→` and `->` are one arrow: `<span class="arrow">→</span>` on the
    page, `$\\rightarrow$` on paper."""

    def test_the_ascii_arrow_is_the_arrow_on_paper(self):
        for target in ("fa", "it", "ja"):
            texgen.set_target(target)
            ascii_, glyph = texgen.inline("a -> b"), texgen.inline("a → b")
            self.assertEqual("a $\\rightarrow$ b", ascii_, target)
            self.assertEqual(glyph.split(), ascii_.split(), target)

    def test_no_carriage_return_reaches_the_tex(self):
        # every place a line of prose is set: a paragraph, a list, a table,
        # a box, a heading's gloss, an exercise's prompt and its rows
        md = doc("From A -> B.\n\n- one -> two\n\n| x | y |\n|---|---|\n| a -> b | c |\n\n"
                 "> in a box -> here\n\n## [کتاب]{tl} | ketâb | Arabic -> Persian | = *book*\n\n"
                 ":::exercise true-false\nprompt: Read -> decide.\n- up -> down => true\n:::")
        tex = paper(md)
        self.assertEqual(0, tex.count("\r"), "carriage returns in the .tex")
        self.assertEqual(0, tex.replace("\\rightarrow$", "").count("ightarrow$"))
        self.assertEqual(7, tex.count("$\\rightarrow$"))

    def test_the_page_draws_both_arrows_alike(self):
        texgen.set_target("fa")
        self.assertEqual(htmlgen.inline("a → b"), htmlgen.inline("a -> b"))
        self.assertEqual('a <span class="arrow">→</span> b', htmlgen.inline("a -> b"))


_PAGE_MATH = re.compile(r'<span class="math" data-tex="([^"]*)"')
_PAPER_MATH = re.compile(r"\\\(((?:[^\\]|\\(?!\)))*)\\\)")
MARK = "#ABCDEF"          # a colour no starter uses


def page_formulas(html):
    return [unescape(t) for t in _PAGE_MATH.findall(html)]


def paper_formulas(tex):
    return _PAPER_MATH.findall(tex)


class FormulaStartsAtItsOwnBracketTests(unittest.TestCase):
    """`[…]{math}` is read from its own `[`: a mark, a link or a blank
    written before it in the same paragraph stays out of it.  texgen.MATH_RE
    is the one pattern the page, the paper, the store's count of the runs
    (store._blank_maths) and the HTML guide (html-guide/engine/inline.py)
    read a formula with."""

    CASES = (
        # (target, text, the formulas, what else must come out whole)
        ("fa", "[تند]{teal} then [x^2]{math}", ["x^2"],
         ('<span class="fac fac-teal" data-color="teal"><span class="fa"', r"\textcolor{fateal}{\pe{تند}}")),
        ("fa", "see [the site](https://x.org) and [x^2]{math}", ["x^2"],
         ('<a class="lnk" href="https://x.org" target="_blank" rel="noopener noreferrer">the site</a>',
          r"\href{https://x.org}{the site}")),
        ("it", "[b]{teal} [c]{math}", ["c"],
         ('<span class="fac fac-teal" data-color="teal"><span class="fa" dir="ltr" lang="it" data-fa="b"',
          r"\textcolor{fateal}{\pe{b}}")),
        ("it", "[a]{teal translit:x} and [bello]{crimson}, then [y]{math} and [z]{math}", ["y", "z"],
         ('data-translit="x"', r"\textcolor{facrimson}{\pe{bello}}")),
        ("fa", "![a picture](images/a.png) inline, [l](doc:Other) and [q]{math}", ["q"],
         ("", "")),
    )

    def test_a_mark_or_a_link_before_a_formula_stays_out_of_it(self):
        for target, text, formulas, (html_part, tex_part) in self.CASES:
            md = doc(text, target)
            html, tex = page(md), paper(md)
            self.assertEqual(formulas, page_formulas(html), text)
            self.assertEqual(formulas, paper_formulas(tex), text)
            self.assertIn(html_part, html, text)
            self.assertIn(tex_part, tex, text)
            self.assertNotIn("]{", "".join(page_formulas(html)), text)

    def test_the_body_still_holds_brackets(self):
        # an interval either way round, the French one, a root's index, a
        # bracket inside a subscript, a commutator that is nothing but a
        # bracket, \left[ ... \right], nested roots, a formula over two
        # lines of its paragraph (which the parser joins with a space)
        bodies = (r"x \in [0,1]", r"x^2 + [0,1)", r"x \in (0,1]", r"x \in ]0,1[",
                  r"\sqrt[3]{x}", r"a_{[i]}", r"[A,B]", r"[[A,B],C]",
                  r"\left[ \frac{a}{b} \right]", r"\left[ x \right)",
                  r"\sqrt[\sqrt[3]{x}]{y}", r"f_{[a,b]}(x)", r"(0,1] \cup (2,3]", "a +\nb")
        for body in bodies:
            md = doc("A formula [%s]{math} here, and [تند]{teal} too." % body)
            drawn = body.replace("\n", " ")
            self.assertEqual([drawn], page_formulas(page(md)), body)
            self.assertEqual([drawn], paper_formulas(paper(md)), body)

    def test_a_blank_before_a_formula_on_paper(self):
        # the page cuts the sentence at its blanks before it reads a
        # formula; paper reads the whole sentence, and the formula used to
        # start at the blank's `[[` (the owner's own hydrology exercises)
        md = doc(":::exercise fill-blanks\nprompt: Fill.\n"
                 "text: Calcium hardness is [[hardness]] mg/L as [CaCO_3]{math}, and [[d]].\n"
                 "- [hardness] [150]{math}\n- [d] done\n:::", "en")
        tex = paper(md)
        self.assertEqual(["CaCO_3", "150"], paper_formulas(tex))
        self.assertIn(r"Calcium hardness is \rule{5em}{", tex)
        self.assertNotIn("hardness]]", tex)
        for preview in (False, True):     # (the preview draws the answer in its blank)
            self.assertEqual(["150", "CaCO_3"], sorted(page_formulas(page(md, preview))))

    def test_the_store_blanks_the_formula_the_page_draws(self):
        # a run before a formula is a run the page offers, and the store
        # finds it: it is not counted as part of the formula
        md = doc("[تند]{teal} کتاب then [x^2]{math} and کتاب.")
        runs = re.findall(r'data-fa="کتاب" data-occ="(\d)"', page(md))
        self.assertEqual(["0", "1"], runs)
        self.assertEqual(2, len(store._run_matches(md, "کتاب")))

    def test_the_hover_palette_before_a_formula_on_the_starters(self):
        # the word right before the first formula of the Japanese, Chinese
        # and Hindi starters: coloured through the store as the palette
        # does, at each place the page offers it, the paragraph must still
        # draw its formula -- on the page and on paper -- and the new colour
        # round that word alone
        for code, word, formula in (("ja", "五十音", r"5 \times 10 = 50"),
                                    ("zh", "三七二十一", r"3 \times 7 = 21"),
                                    ("hi", "है", r"f = \frac{60}{2000} \times 1000 = 30")):
            md = (ROOT / "markdown" / "exlex" / "starters" / (code + ".md")).read_text(encoding="utf-8")
            html = page(md)
            self.assertIn(formula, page_formulas(html), code)
            occs = [int(n) for n in re.findall(r'data-fa="%s" data-occ="(\d+)"' % word, html)]
            self.assertTrue(occs, code)
            before_formula = False
            for occ in occs:
                new = store.recolor_markdown(md, word, occ, MARK)
                at = new.index("[%s]{%s}" % (word, MARK))
                end = new.find("\n\n", at)
                here = ("[%s]{math}" % formula) in new[at:end]
                before_formula |= here
                new_html = page(new)
                self.assertEqual(page_formulas(html), page_formulas(new_html), (code, occ))
                self.assertEqual(paper_formulas(paper(md)), paper_formulas(paper(new)), (code, occ))
                coloured = re.findall(r'<span class="fac" data-color="%s" style="color:%s">'
                                      r'<span class="fa[^"]*"[^>]* data-fa="([^"]*)" data-occ="(\d+)"'
                                      % (MARK, MARK), new_html)
                self.assertEqual([(word, str(occ))], coloured, (code, occ))
                if here:
                    # (paper prints no explanation, where some of them are)
                    self.assertIn(r"\textcolor[HTML]{ABCDEF}{\pe{%s}}" % word, paper(new), code)
            self.assertTrue(before_formula, "%s: no %s stands before its formula" % (code, word))


class OneDashSeparatorTests(unittest.TestCase):
    """The line under a table's header needs one dash a cell, as in GFM;
    in the body a cell of `-` or `--` is still an empty one."""

    def table(self, md):
        blocks = [b for b in mdparser.parse(md)[1] if b["type"] != "para"]
        self.assertEqual(["table"], [b["type"] for b in blocks], md)
        return blocks[0]

    def test_one_dash_makes_a_table(self):
        for sep, align in (("|-|-|-|", ["l", "l", "l"]), ("|:-:|-:|:-|", ["c", "r", "l"]),
                           ("-|-|-", ["l", "l", "l"]), (":-: | -: | -", ["c", "r", "l"]),
                           ("| :- | --: | :---: |", ["l", "r", "c"]),
                           ("|---|---|---|", ["l", "l", "l"])):     # (as before)
            for target in ("fa", "it", "ja"):
                md = doc("Before.\n\n| a | b | c |\n%s\n| x | y | z |\n\nAfter." % sep, target)
                t = self.table(md)
                self.assertEqual((["a", "b", "c"], align, [["x", "y", "z"]]),
                                 (t["header"], t["align"], t["rows"]), (sep, target))
                html, tex = page(md), paper(md)
                self.assertIn('<table class="bt"><thead><tr><th class="a-%s">a</th>' % align[0], html)
                self.assertNotIn("| a |", html, sep)
                self.assertIn("\\begin{tabular}{@{}%s@{}}" % " ".join(align), tex, sep)
                self.assertNotIn("| a |", tex, sep)

    def test_a_body_row_of_dashes_is_a_row_of_empty_cells(self):
        # right under a one-dash separator, a row that looks like one is
        # the table's first row, and its cells are the empty cell
        md = doc("| a | b |\n|-|-|\n| - | -- |\n| — | x |\n| - | - |")
        t = self.table(md)
        self.assertEqual([["-", "--"], ["—", "x"], ["-", "-"]], t["rows"])
        html = page(md)
        self.assertEqual(5, html.count('<td class="a-l">—</td>'))
        self.assertIn('<td class="a-l">x</td>', html)
        self.assertIn("--- & ---\\\\\n--- & x\\\\\n--- & ---\\\\", paper(md))

    def test_what_is_not_a_separator_stays_prose(self):
        # one column, a horizontal rule, a cell with text in it, colons
        # with no dash
        for second in ("| --- |", "---", "| - | x |", "|:|:|"):
            md = doc("| a | b |\n%s\n| c | d |" % second)
            self.assertNotIn("table", [b["type"] for b in mdparser.parse(md)[1][:1]], second)


if __name__ == "__main__":
    unittest.main()
