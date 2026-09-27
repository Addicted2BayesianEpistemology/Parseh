# SPDX-License-Identifier: GPL-3.0-or-later
"""LaTeX drawings (TO-DO §8.39): the ::::latex fence, theme names, a rename's
rewrite of the text, and the key a drawing is kept under.  No TeX is run:
what a compile makes is checked by hand (docs/releasing.md).  The themes'
store is redirected to a temporary folder, so config/ is never written."""
import json
import os
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


if __name__ == "__main__":
    unittest.main()
