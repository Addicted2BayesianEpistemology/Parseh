# SPDX-License-Identifier: GPL-3.0-or-later
"""LaTeX drawings (TO-DO §8.39): the ::::latex fence, theme names, a rename's
rewrite of the text, and the key a drawing is kept under.  No TeX is run:
what a compile makes is checked by hand (docs/releasing.md).  The themes'
store is redirected to a temporary folder, so config/ is never written."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
for folder in (ROOT / "lib", ROOT / "markdown" / "exlex", ROOT / "markdown" / "app"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import latexdraw    # noqa: E402
import latexthemes  # noqa: E402
import mdparser     # noqa: E402
import texgen       # noqa: E402
import htmlgen      # noqa: E402


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


def _drawn(calls=None, w=99.0):
    def draw(tex, theme, **kw):
        if calls is not None:
            calls.append((tex, theme, sorted(kw)))
        return {"ok": True, "key": "c" * 64, "url": "/latex/%s.svg" % ("c" * 64), "w": w, "h": 20,
                "pdf": "/nowhere/%s.pdf" % ("c" * 64)}
    return draw


def _figure(md, **kw):
    with mock.patch.dict(htmlgen.LATEX, {"draw": _drawn(), "draw_all": None}):
        return htmlgen.render_document(md, **kw)["html"]


class Caption(unittest.TestCase):
    """A latex BLOCK (never the inline mark) may take `caption="…"` in its braces:
    inline markup in double quotes, set under the drawing as a figure's caption is."""

    def blocks(self, md):
        return [b for b in mdparser.parse(md)[1] if b["type"] == "latex"]

    def test_the_braces_take_a_quoted_caption(self):
        b, = self.blocks('::::latex chemistry {width=45 align=left caption="Water forms from hydrogen"}\nx\n::::\n')
        self.assertEqual((b["caption"], b["width"], b["align"], b["theme"]),
                         ("Water forms from hydrogen", 45, "left", "chemistry"))
        self.assertFalse(b["errors"])

    def test_no_caption_is_none_and_the_theme_is_optional(self):
        b, = self.blocks("::::latex {width=45}\nx\n::::\n")
        self.assertEqual(b["caption"], "")
        b, = self.blocks('::::latex {caption="A"}\nx\n::::\n')
        self.assertEqual((b["caption"], b["theme"], b["width"]), ("A", "", None))

    def test_a_caption_may_hold_braces_brackets_and_the_layout_words(self):
        b, = self.blocks('::::latex chem {caption="[x^2]{math} and width=9, a } too" width=30}\nx\n::::\n')
        self.assertEqual(b["caption"], "[x^2]{math} and width=9, a } too")
        self.assertEqual(b["width"], 30, "the words outside the quotes still read")
        self.assertFalse(b["errors"])

    def test_whitespace_is_one_space(self):
        b, = self.blocks('::::latex {caption="  two   words "}\nx\n::::\n')
        self.assertEqual(b["caption"], "two words")

    def test_a_caption_without_quotes_or_with_an_open_one_is_said_not_dropped(self):
        b, = self.blocks("::::latex chem {caption=Water}\nx\n::::\n")
        self.assertTrue(any("double quotes" in e for e in b["errors"]), b["errors"])
        b, = self.blocks('::::latex chem {caption="Water}\nx\n::::\n')
        self.assertTrue(b["errors"], "an open quote is a bad opening line")

    def test_a_caption_on_a_card(self):
        md = (":::exercise flashcard\ntype: jolly\nfront: |\n  ::::latex {caption=\"Water\"}\n  \\ce{H2O}\n  ::::\n"
              "back: water\n:::\n")
        self.assertEqual(latexthemes.blocks_in(md)[0]["attrs"], 'caption="Water"')

    def test_a_caption_never_changes_the_drawing_asked_for(self):
        calls = []
        plain = '::::latex chemistry {width=45}\n\\ce{H2O}\n::::\n'
        said = '::::latex chemistry {width=45 caption="Water"}\n\\ce{H2O}\n::::\n'
        with mock.patch.dict(htmlgen.LATEX, {"draw": _drawn(calls), "draw_all": None}):
            htmlgen.render_document(plain)
            htmlgen.render_document(said)
        self.assertEqual(calls[0], calls[1], "the same (tex, theme) is asked of the drawer, nothing more")
        self.assertEqual(calls[0][:2], ("\\ce{H2O}", "chemistry"))
        # and the key is made of what latexdraw.key_of is given, which has no room for one
        import inspect
        self.assertEqual(list(inspect.signature(latexdraw.key_of).parameters),
                         ["tex", "resolved", "state", "inline"])

    def test_the_html_is_a_figures_caption_below_a_natural_size_drawing(self):
        html = _figure('::::latex chemistry {caption="Water with *care* and [x^2]{math}"}\nx\n::::\n')
        self.assertIn('<figure class="latex has-caption align-center"', html)
        self.assertRegex(html, r"<figcaption[^>]*><span>Water with <em>care</em> and .*</span></figcaption>")
        self.assertIn('data-latex-caption="Water with *care* and [x^2]{math}"', html,
                      "the source, for the editor's pencil")
        self.assertLess(html.index("<img"), html.index("<figcaption"))
        # the drawing keeps its natural width (9.9 ems); the caption's box is never narrower than 20em
        self.assertIn("width:9.90em", html)
        self.assertIn("min(100%,20em)", html)

    def test_the_html_of_a_drawing_with_a_width(self):
        html = _figure('::::latex chemistry {width=45 align=right caption="Water"}\nx\n::::\n')
        self.assertIn("width:45%", html)
        self.assertIn("margin-left:55.00%", html, "where an uncaptioned drawing of that width would stand")
        self.assertIn("<figcaption", html)
        self.assertIn('data-width="45" data-align="right"', html)

    def test_a_drawing_without_a_caption_is_the_figure_it_always_was(self):
        html = _figure("::::latex chemistry {width=45}\nx\n::::\n")
        self.assertNotIn("figcaption", html)
        self.assertNotIn("has-caption", html)
        self.assertIn('style="width:45%;margin-left:27.50%"', html)
        self.assertIn('data-latex-caption=""', html)

    def test_a_drawing_that_could_not_be_made_shows_no_caption_but_keeps_it_for_the_pencil(self):
        def broken(tex, theme, **kw):
            return {"ok": False, "kind": "latex", "said": "LaTeX stopped."}
        with mock.patch.dict(htmlgen.LATEX, {"draw": broken, "draw_all": None}):
            html = htmlgen.render_document('::::latex {caption="Kept"}\nx\n::::\n')["html"]
        self.assertIn("latex-fail", html)
        self.assertNotIn("<figcaption", html)
        self.assertIn('data-latex-caption="Kept"', html)

    def test_a_card_shows_it_and_has_no_pencil(self):
        md = ("---\ntarget: it\n---\n\n:::exercise flashcard\ncard-type: jolly\nfront-primary: |\n"
              "  ::::latex {caption=\"On a card\"}\n  x\n  ::::\nback-primary: y\n:::\n")
        html = _figure(md)
        self.assertRegex(html, r"<figcaption[^>]*><span>On a card</span></figcaption>")
        self.assertNotIn("data-latex-caption", html)

    def test_the_paper_sets_it_under_the_drawing_in_small_grey_type(self):
        block = self.blocks('::::latex chemistry {caption="Water & *care*"}\nx\n::::\n')[0]
        with mock.patch.dict(texgen.LATEX, {"draw": _drawn()}):
            tex = texgen._render_latex(block)
        self.assertIn(r"{\footnotesize\color{graytx} Water \& \emph{care}\par}", tex)
        self.assertIn(r"\includegraphics[scale=", tex, "the drawing at its natural size")
        self.assertIn(r"\dimen1=20em", tex, "and the caption's box no narrower than 20em or the line")
        sized = self.blocks('::::latex chemistry {width=45 align=left caption="W"}\nx\n::::\n')[0]
        with mock.patch.dict(texgen.LATEX, {"draw": _drawn()}):
            tex = texgen._render_latex(sized)
        self.assertIn(r"\includegraphics[width=0.450\linewidth]", tex)
        self.assertIn(r"\raggedright", tex)
        plain = self.blocks("::::latex chemistry {width=45}\nx\n::::\n")[0]
        with mock.patch.dict(texgen.LATEX, {"draw": _drawn()}):
            self.assertNotIn(r"\footnotesize", texgen._render_latex(plain))


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
    def test_base_packages_have_a_public_name_and_explanation(self):
        base, = [g for g in latexthemes.GROUPS if g[0] == "base"]
        self.assertEqual(base[1], "Base packages")
        self.assertTrue(base[2])
        self.assertNotIn("formulae", " ".join(base).lower())

    def test_the_language_groups_added_for_l10_are_real_rows(self):
        # TO-DO §8.39's L10, researched and each one really compiled, 2026-09-27:
        # every group id a package below names must have a heading, and every
        # package must give tlmgr a real name, a licence, and a file that
        # proves it once it is here.
        group_ids = {g[0] for g in latexthemes.GROUPS}
        for group in ("linguistics", "phonetics", "scripts"):
            self.assertIn(group, group_ids)
        expect = {"forest": "linguistics", "tikz-dependency": "linguistics",
                  "tipa": "phonetics", "xpinyin": "scripts"}
        for pid, group in expect.items():
            row = latexthemes.PACKAGES[pid]
            self.assertEqual(row["group"], group)
            self.assertTrue(row["tl"] and all(row["tl"]))
            self.assertTrue(row["licence"])
            self.assertTrue(row["file"] and row["file"].endswith(".sty"))
            self.assertIn(pid, row["code"])

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


class SheetThemes(Store):
    """What the drawing sheet's Theme list is told: a theme's missing packages, and where Settings is."""

    class Reply:
        def send_json(self, obj, status=200):
            self.obj = obj

    def ask(self, gone, settings):
        import server
        import texpackages
        h = self.Reply()
        with mock.patch.object(texpackages, "installed", lambda f: (False if f in gone else True)), \
                mock.patch.dict(htmlgen.LATEX, {"settings": settings}):
            server.api_latex_themes(h)
        return h.obj

    def test_a_theme_says_which_of_its_packages_this_computer_lacks(self):
        got = self.ask({"mhchem.sty"}, "/settings/latex/")
        self.assertEqual(got["themes"], ["default", "chemistry", "drawing"])
        self.assertEqual(got["missing"], {"chemistry": [{"id": "mhchem", "install": "mhchem"}]},
                         "only the theme that loads it, by the TeX Live package to install")
        self.assertEqual(got["settings"], "/settings/latex/")

    def test_nothing_missing_and_no_settings_page(self):
        got = self.ask(set(), None)
        self.assertEqual(got["missing"], {})
        self.assertIsNone(got["settings"], "the studio alone has no Settings to send anyone to")

    def test_a_compiler_this_computer_lacks_is_missing_too(self):
        import server
        h = self.Reply()
        with mock.patch.object(latexdraw, "compiler", lambda name, fresh=False: None):
            server.api_latex_themes(h)
        self.assertTrue(h.obj["missing"]["default"][0]["install"] is None
                        and h.obj["missing"]["default"][0]["id"] == latexthemes.find("default")["compiler"])


class InlineMark(unittest.TestCase):
    """`[…]{latex}` / `[…]{latex theme}` (TO-DO §8.39's L8): no TeX run here
    either, same rule as this whole file -- LATEX_INLINE_RE and
    inline_latex_pairs are pure regex, imported (not copied) from
    lib/latexthemes.py by markdown/exlex/texgen.py and lib/offline.py alike."""
    def test_a_mark_names_its_body_and_an_optional_theme(self):
        m = latexthemes.LATEX_INLINE_RE.search(r"[\ce{H2O}]{latex}")
        self.assertEqual((m.group(1), m.group(3)), (r"\ce{H2O}", None))
        m = latexthemes.LATEX_INLINE_RE.search(r"[\ce{H2O}]{latex chemistry}")
        self.assertEqual((m.group(1), m.group(3)), (r"\ce{H2O}", "chemistry"))

    def test_a_bracket_the_body_opens_and_closes_itself_is_kept(self):
        # the same reason MATH_RE reads `[0,1)` and `\sqrt[3]{x}` correctly
        m = latexthemes.LATEX_INLINE_RE.search(r"[x \in [0,1)]{latex}")
        self.assertEqual(m.group(1), r"x \in [0,1)")

    def test_two_marks_on_one_line_are_both_found_apart(self):
        found = [m.groups() for m in
                 latexthemes.LATEX_INLINE_RE.finditer(r"a [x]{latex} b [y]{latex drawing} c")]
        self.assertEqual([(g[0], g[2]) for g in found], [("x", None), ("y", "drawing")])

    def test_not_a_run_of_the_target_language(self):
        self.assertIn("latex", texgen.NOT_A_RUN)

    def test_pairs_are_deduplicated_in_first_seen_order(self):
        pairs = latexthemes.inline_latex_pairs(
            "[x]{latex} and [y]{latex chemistry} and [x]{latex} again")
        self.assertEqual(pairs, [("x", None), ("y", "chemistry")])

    def test_a_mark_is_found_in_every_text_field_because_the_sweep_is_of_the_raw_source(self):
        # no block tree, no exercise type list to keep in step: an inline
        # mark in a prompt, an option, a note or a document paragraph is the
        # same three characters to a regex over the whole markdown
        source = ("prompt: [p]{latex}\n\nOne option: [a]{latex}, another: "
                  "[b]{latex chemistry}\n\nA note: [c]{latex}.\n")
        self.assertEqual(
            {t for t, _ in latexthemes.inline_latex_pairs(source)}, {"p", "a", "b", "c"})

    def test_a_mark_right_after_an_exercise_s_own_checkbox_is_a_known_limit(self):
        # inherited from MATH_RE, which this mirrors exactly (both are a raw
        # sweep of UNPARSED source, before the parser strips "- [x] "): the
        # mark's own body is swallowed with the checkbox before it, when
        # nothing separates the two.  Harmless where it is used -- a page's
        # pre-warm only wastes one compile of nonsense text, and the block
        # tree the real render reads from is never touched by this sweep --
        # but real, and worth a name rather than a silent surprise.
        source = "- [x] [a]{latex}\n"
        got = [t for t, _ in latexthemes.inline_latex_pairs(source)]
        self.assertEqual(got, ["x] [a"])


class KeptDrawings(Store):
    """L9: a live editor's cache is not the saved-library cache."""

    def _put(self, key, preview=False):
        p = latexdraw.paths(key, preview)
        os.makedirs(os.path.dirname(p["meta"]), exist_ok=True)
        for kind, data in (("svg", b"<svg/>"), ("pdf", b"%PDF-"),
                           ("meta", json.dumps({"w": 10, "h": 10}).encode("utf-8"))):
            with open(p[kind], "wb") as fh:
                fh.write(data)

    def test_a_preview_is_not_counted_or_kept_until_promoted(self):
        key = "a" * 64
        self._put(key, preview=True)
        self.assertEqual(latexdraw.size()["drawings"], 0)
        self.assertEqual(latexdraw.file_of(key + ".svg"), latexdraw.paths(key, True)["svg"])
        self.assertTrue(latexdraw._promote(key))
        self.assertEqual(latexdraw.size()["drawings"], 1)
        self.assertEqual(latexdraw.file_of(key + ".svg"), latexdraw.paths(key)["svg"])

    def test_an_owner_keeps_its_key_and_an_orphan_waits_for_the_grace(self):
        key = "b" * 64
        self._put(key)
        doc = {"format": 1, "owners": {"document:test": [key]}, "unowned": {}, "repaired": 0}
        latexdraw._reconcile_owners(doc, [key], now=100)
        self.assertNotIn(key, doc["unowned"])
        doc["owners"].clear()
        latexdraw._reconcile_owners(doc, [key], now=100)
        self.assertEqual(doc["unowned"][key], 100)
        self.assertTrue(os.path.exists(latexdraw.paths(key)["svg"]))
        latexdraw._reconcile_owners(doc, [key], now=100 + latexdraw.OWNER_GRACE_SECONDS + 1)
        self.assertFalse(os.path.exists(latexdraw.paths(key)["svg"]))

    def test_a_delete_starts_the_grace_clock_even_after_a_repair(self):
        # found by the owner, rc3: repair_owners keeps the whole live set as one
        # owner, so a deleted document's keys still counted as owned and the
        # day of grace began at the next repair, not at the delete
        key = "e" * 64
        self._put(key)
        with open(latexdraw._owners_path(), "w", encoding="utf-8") as fh:
            json.dump({"format": 1, "owners": {"document:a": [key]}, "unowned": {}, "repaired": 0}, fh)
        latexdraw.repair_owners({key}, force=True)
        self.assertIn(key, latexdraw._owner_doc()["owners"][latexdraw.REPAIR_OWNER])
        latexdraw.forget_owner("document:a")
        doc = latexdraw._owner_doc()
        self.assertIn(key, doc["unowned"], "the day starts at the delete")
        self.assertNotIn(key, latexdraw._owned(doc))

    def test_a_delete_of_a_source_no_owner_recorded_starts_it_too(self):
        key = "f" * 64
        self._put(key)
        latexdraw.repair_owners({key}, force=True)
        latexdraw.forget_owner("document:never-recorded", also={key})
        self.assertIn(key, latexdraw._owner_doc()["unowned"])

    def test_forgetting_leaves_no_empty_owner_and_no_empty_folder(self):
        gone, kept = "1" * 64, "2" * 64
        self._put(gone)
        self._put(kept)
        with open(latexdraw._owners_path(), "w", encoding="utf-8") as fh:
            json.dump({"format": 1, "owners": {"document:a": [gone], "document:b": [kept]},
                       "unowned": {gone: 5}, "repaired": 0}, fh)
        out = latexdraw.forget_unused({kept})
        self.assertEqual(out["drawings"], 1)
        doc = latexdraw._owner_doc()
        self.assertEqual(doc["owners"], {"document:b": [kept]}, "an owner of nothing is dropped")
        self.assertEqual(doc["unowned"], {})
        self.assertFalse(os.path.exists(os.path.dirname(latexdraw.paths(gone)["svg"])),
                         "the emptied folder goes with its last drawing")
        self.assertTrue(os.path.isfile(latexdraw.paths(kept)["svg"]))

    def test_saving_promotes_the_matching_preview_and_records_its_owner(self):
        key = "c" * 64
        self._put(key, preview=True)
        with mock.patch.object(latexdraw, "plan", return_value={"ok": True, "key": key}):
            keys = latexdraw.own_source("document:test", "::::latex\nx\n::::\n")
        self.assertEqual(keys, {key})
        self.assertTrue(os.path.isfile(latexdraw.paths(key)["svg"]))
        with open(latexdraw._owners_path(), encoding="utf-8") as fh:
            owners = json.load(fh)["owners"]
        self.assertEqual(owners["document:test"], [key])

    def test_showing_a_solved_exercise_is_not_the_same_question_as_caching_a_preview(self):
        # found reviewing this: the two were briefly one flag
        # (editor_preview alone), and a deck's solved study/cram view
        # (editor_preview=True, its own drawings meant to be KEPT) silently
        # stopped showing solved at all, because htmlgen read that one flag
        # for both "show the answer" and "cache this as an unsaved preview".
        calls = []

        def drawn(tex, theme, **kw):
            calls.append(kw.get("preview", False))
            return {"ok": True, "key": "d" * 64, "url": "/latex/d.svg", "w": 10, "h": 10}
        md = ("---\ntarget: it\n---\n\n:::exercise flashcard\ncard-type: jolly\n"
             "front-primary: |\n  ::::latex\n  x\n  ::::\nback-primary: y\n:::\n")
        with mock.patch.dict(htmlgen.LATEX, {"draw": drawn, "draw_all": None}):
            solved = htmlgen.render_document(md, editor_preview=True, latex_preview=False)
            self.assertIn('data-editor-preview="1"', solved["html"], "shown solved")
            self.assertEqual(calls, [False], "kept, not cached as an unsaved preview")
            calls.clear()
            live = htmlgen.render_document(md, editor_preview=True, latex_preview=True)
            self.assertIn('data-editor-preview="1"', live["html"])
            self.assertEqual(calls, [True], "the studio's own unsaved typing IS both at once")


class Handler:
    """The parts of a request the routes below read and answer with."""

    def __init__(self, body=None):
        self.body, self.sent, self.query = body, None, {}

    def _json_body(self):
        return self.body

    def _body(self):
        return json.dumps(self.body).encode("utf-8")

    def send_json(self, obj, code=200):
        self.sent = (code, obj)


NOTE = "---\ntarget: it\n---\n\n# %s\n\n::::latex\n\\ce{%s}\n::::\n\nA mark, [\\ce{%s2}]{latex}, in a line.\n"
EXERCISE = (":::exercise single-choice\nprompt: |\n  Pick.\n  ::::latex\n  \\ce{NaCl}\n  ::::\n"
            "- [x] [\\ce{Na}]{latex}\n- [ ] [\\ce{Cl}]{latex}\n:::\n")


class ForgetWhatWasDeleted(Store):
    """L26, the owner's report after rc3: every document, deck and note that
    held a drawing deleted, the button freed only some.  Driven through the
    routes the pages use -- the studio's, the decks', Settings' -- with the keys
    the real plan() makes; only the TeX run is left out, a drawing being a file
    put where its key says."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT))
        import serve                                          # noqa: E402
        import deckroutes                                     # noqa: E402
        import decks                                          # noqa: E402
        import latexpage                                      # noqa: E402
        import network                                        # noqa: E402
        import store                                          # noqa: E402
        cls.serve, cls.studio, cls.deckroutes, cls.decks = serve, serve.studio, deckroutes, decks
        cls.latexpage, cls.network, cls.store = latexpage, network, store

    def setUp(self):
        super().setUp()
        base = Path(self.tmp.name)
        self.library, self.exercises = base / "library", base / "exercises"
        self.library.mkdir()
        self.books = [base / "book-a" / "markdown", base / "book-b" / "markdown"]
        for one in self.books:
            one.mkdir(parents=True)
        was_lib, self.store.LIB = self.store.LIB, self.library
        was_decks = self.decks.set_dir(self.exercises)
        self.addCleanup(lambda: setattr(self.store, "LIB", was_lib))
        self.addCleanup(lambda: self.decks.set_dir(was_decks))
        for patch in (mock.patch.object(latexdraw, "compiler", lambda name, fresh=False:
                                        {"path": "xelatex", "version": "test", "miktex": False}),
                      mock.patch.object(self.serve, "notes_libraries",
                                        lambda: [(str(one), "the notes of " + one.parent.name)
                                                 for one in self.books])):
            patch.start()
            self.addCleanup(patch.stop)

    def put(self, keys):
        for key in keys:
            for kind, path in latexdraw.paths(key).items():
                if kind != "fail":
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "wb") as fh:
                        fh.write(b"x")
        return set(keys)

    def make_document(self, title, formula):
        h = Handler({"markdown": NOTE % (title, formula, formula)})
        self.studio.api_create(h)
        doc_id = h.sent[1]["meta"]["id"]
        markdown = self.store.get(doc_id)[1]
        return doc_id, self.put(latexdraw._source_keys(markdown))

    def make_note(self, book, title, formula):
        was = self.store.use_library(self.books[book])
        try:
            meta = self.store.create(NOTE % (title, formula, formula))
            markdown = self.store.get(meta["id"])[1]
            keys = self.put(latexdraw._source_keys(markdown))
            latexdraw.own_source(self.studio._latex_owner(meta["id"]), markdown)
        finally:
            self.store.use_library(was)
        return meta["id"], keys

    def make_deck(self):
        h = Handler({"name": "Geometry", "lang": "it"})
        self.deckroutes.api_decks_create(h)
        deck = h.sent[1]["deck"]
        h = Handler({"markdown": EXERCISE})
        self.deckroutes.api_item_add(h, deck["folder"], deck["slug"])
        item = self.decks.get_item(deck["folder"], deck["slug"], h.sent[1]["item"]["id"])
        keys = self.put(latexdraw._source_keys(item["markdown"] + "\n" + (item.get("footnotes") or "")))
        return deck, keys

    def forget(self):
        code, out = self.latexpage.api("forget", {}, self.network.SELF, self.serve.notes_libraries(),
                                       rename=self.studio.latexrename, used=self.serve.latex_used)
        self.assertEqual(code, 200, out)
        return out

    def on_disk(self):
        return sorted(os.path.join(here, f) for here, _d, files in os.walk(latexdraw.DRAWN)
                      for f in files if f != latexdraw.OWNERS_FILE)

    def test_every_deleted_document_deck_and_note_frees_its_drawings(self):
        doc_id, doc = self.make_document("Uno", "H2O")
        deck, exercise = self.make_deck()
        note_id, note = self.make_note(0, "Nota", "NaOH")
        self.assertEqual((len(doc), len(exercise), len(note)), (2, 3, 2))
        self.assertEqual(latexdraw.size()["drawings"], 7)
        self.assertEqual(self.forget()["drawings"], 0, "everything is still named by a source")
        self.assertEqual(latexdraw.size()["drawings"], 7)

        self.studio.api_delete(Handler(), doc_id)
        self.assertEqual(self.forget()["drawings"], 2)
        h = Handler()
        self.deckroutes.api_deck_delete(h, deck["folder"], deck["slug"])
        self.assertEqual(h.sent, (200, {"ok": True}))
        self.assertTrue((self.exercises / ".trash").is_dir(), "a deck is only moved to its trash")
        out = self.forget()
        self.assertEqual(out["drawings"], 3, "the trashed deck's drawings go, as rc3 left 3 behind")
        was = self.store.use_library(self.books[0])
        try:
            self.studio.api_delete(Handler(), note_id)
        finally:
            self.store.use_library(was)
        out = self.forget()
        self.assertEqual((out["drawings"], out["forgotten"]), (2, 2))
        self.assertEqual(out["kept"], {"drawings": 0, "bytes": 0})
        self.assertEqual(self.on_disk(), [], "not one file of a drawing is left")
        doc = latexdraw._owner_doc()
        self.assertEqual(doc["owners"], {}, "no owner of nothing")
        self.assertEqual(self.forget()["drawings"], 0, "and a second press finds nothing")

    def test_the_explicit_button_ignores_a_trash_and_the_startup_repair_keeps_it(self):
        deck, exercise = self.make_deck()
        self.deckroutes.api_deck_delete(Handler(), deck["folder"], deck["slug"])
        self.assertEqual(self.serve.latex_used(), exercise, "the repair keeps what a restore would need")
        self.assertEqual(self.serve.latex_used(include_trash=False), set())
        # a book in its trash is a trash too
        trashed = self.books[0].parent.parent / "trash-book" / ".trash" / "old" / "markdown"
        trashed.mkdir(parents=True)
        self.books.append(trashed)
        was = self.store.use_library(trashed)
        try:
            meta = self.store.create(NOTE % ("Vecchia", "KCl", "KCl"))
            note = latexdraw._source_keys(self.store.get(meta["id"])[1])
        finally:
            self.store.use_library(was)
        self.assertEqual(self.serve.latex_used(), exercise | note)
        self.assertEqual(self.serve.latex_used(include_trash=False), set())

    def test_a_deck_taken_back_from_its_trash_is_simply_drawn_again(self):
        deck, exercise = self.make_deck()
        self.deckroutes.api_deck_delete(Handler(), deck["folder"], deck["slug"])
        self.assertEqual(self.forget()["drawings"], 3)
        self.assertEqual(self.on_disk(), [])
        trashed, = list((self.exercises / ".trash").iterdir())
        target = self.exercises / deck["folder"] / deck["slug"]
        target.parent.mkdir(parents=True, exist_ok=True)
        trashed.rename(target)
        self.assertEqual(self.serve.latex_used(include_trash=False), exercise,
                         "back in its place, its drawings are named again")
        made = []

        def compiled(tex, resolved, info, key, limit, inline=False, preview=False):
            made.append(key)
            self.put([key])
            return latexdraw._ok(key, {"w": 10, "h": 10})

        item = self.decks.get_item(deck["folder"], deck["slug"], self.decks._item_ids(target)[0])
        block = [b for b in latexthemes.blocks_in(item["markdown"]) if b["closed"]][0]
        with mock.patch.object(latexdraw, "_compile", compiled):
            out = latexdraw.draw(block["tex"], block["theme"] or None)
        self.assertTrue(out["ok"])
        self.assertEqual(made, [out["key"]], "it was compiled again, the way a first sight is")
        self.assertIn(out["key"], exercise)
        self.assertTrue(os.path.isfile(latexdraw.paths(out["key"])["svg"]))

    def test_the_same_note_in_two_books_is_two_owners(self):
        # found reading, then driven: the owner was built from store.LIB and not
        # from the library the request is in, so one note id in two libraries (a
        # book brought back beside its trashed copy) shared an owner and each
        # save overwrote the other's keys
        a, keys_a = self.make_note(0, "Same", "AlCl3")
        shutil.copytree(self.books[0], self.books[1], dirs_exist_ok=True)
        for source in self.books[1].rglob("source.md"):
            source.write_text(source.read_text(encoding="utf-8").replace("AlCl3", "FeCl3"), encoding="utf-8")
        was = self.store.use_library(self.books[1])
        try:
            markdown = self.store.get(a)[1]
            keys_b = self.put(latexdraw._source_keys(markdown))
            self.assertNotEqual(self.studio._latex_owner(a), "document:%s:%s" % (os.path.realpath(str(self.library)), a))
            latexdraw.own_source(self.studio._latex_owner(a), markdown)
        finally:
            self.store.use_library(was)
        self.assertTrue(keys_a and keys_b and not (keys_a & keys_b))
        owners = latexdraw._owner_doc()["owners"]
        self.assertEqual(len(owners), 2)
        self.assertEqual(sorted(k for keys in owners.values() for k in keys), sorted(keys_a | keys_b))
        was = self.store.use_library(self.books[0])
        try:
            self.studio.api_delete(Handler(), a)
        finally:
            self.store.use_library(was)
        owners = latexdraw._owner_doc()["owners"]
        self.assertEqual(sorted(k for keys in owners.values() for k in keys), sorted(keys_b),
                         "deleting one book's note leaves the other's drawings owned")
        self.assertEqual(self.forget()["drawings"], len(keys_a))
        self.assertEqual(latexdraw.size()["drawings"], len(keys_b))


if __name__ == "__main__":
    unittest.main()
