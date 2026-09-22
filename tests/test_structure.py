#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
r"""A chapter's name and the sections inside it: lib/structure.py and its door.

The promise being tested is narrow and load-bearing: a structural mark is a
PLACE and changes nothing else.  Every write here is followed by the question
"did any number move?", because the whole design rests on the answer being no
-- paragraph numbers come from \parnum and from nothing else, and verify_book
holds every paragraph against source/paras/ch<N>_p<NN>.txt by that number.

The doors are driven through serve.Handler._route, not by calling the handler
straight: a door can be perfectly right and still be unreachable because the
POST guard in _route does not name its prefix, and that is a mistake only the
route table can show (tests/test_reading.py:472 exists for the same reason).
"""
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, ROOT)          # serve.py is at the root, beside build.sh

import structure  # noqa: E402
import texparse as T  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "books", "english", "mini-en")


def text_of(path):
    """The file, with the handle closed behind it: a test that leaks one
    fills the verbose output with ResourceWarnings and buries its own result."""
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def shape(path):
    """What a chapter is, in the terms that must never move."""
    ch = T.parse_chapter(path)
    return {"paras": [p.no for p in ch.paragraphs],
            "subs": [s.label for s in ch.subs],
            "chunks": [c.fa for c in T.all_chunks([ch])]}


class TheFile(unittest.TestCase):
    """lib/structure.py, writing into a real chapter."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.book = Path(td.name) / "books" / "english" / "mini-en"
        self.book.parent.mkdir(parents=True)
        shutil.copytree(FIXTURE, self.book, ignore=shutil.ignore_patterns("reader"))
        self.ch1 = str(self.book / "ch1.tex")
        self.was = text_of(self.ch1)
        self.shape = shape(self.ch1)

    def test_a_book_with_no_marks_reads_as_a_book_with_no_marks(self):
        got = structure.read(str(self.book))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["name"], "")
        self.assertEqual(got[0]["sections"], [])
        self.assertEqual(got[0]["paragraphs"], [1, 2])

    def test_naming_a_chapter_moves_no_number(self):
        structure.set_chapter_name(str(self.book), 1, "The Dam")
        self.assertEqual(shape(self.ch1), self.shape)
        self.assertEqual(structure.read(str(self.book))[0]["name"], "The Dam")

    def test_a_section_opens_at_the_paragraph_it_names(self):
        structure.set_section(str(self.book), 1, 2, "The Spillway")
        self.assertEqual(shape(self.ch1), self.shape,
                         "a section is a place; it moves nothing")
        ch = T.parse_chapter(self.ch1)
        got = {p.no: p.section for p in ch.paragraphs if p.section}
        self.assertEqual(sorted(got), [2],
                         "on the paragraph asked for, not the one before it")

    def test_a_section_stands_above_parstart_and_never_among_the_timings(self):
        r"""The one placement that is safe.

        tex2html.load_times gathers the `% @par` comments and flushes them at
        the first line that is not one, keying them by THAT line.  A mark
        between a `% @par` and its \begin{frank} would take the flush, and the
        subparagraph would silently lose its times and play as unnarrated.
        """
        structure.set_section(str(self.book), 1, 2, "The Spillway")
        lines = text_of(self.ch1).split("\n")
        mark = [i for i, l in enumerate(lines) if l.startswith("\\secmark")]
        self.assertEqual(len(mark), 1)
        after = [l for l in lines[mark[0] + 1:] if l.strip()][0]
        self.assertTrue(after.startswith("\\parstart") or after.startswith("\\parnum"),
                        "the next thing after the mark is the paragraph it opens: %r"
                        % after)
        # and nothing was dropped into the middle of a timing block
        for i, l in enumerate(lines):
            if re.match(r"^%\s*@par\b", l):
                nxt = [x for x in lines[i + 1:] if x.strip()][0]
                self.assertFalse(nxt.startswith("\\secmark"),
                                 "a mark between a %% @par and its \\begin{frank} "
                                 "loses that subparagraph's times")

    def test_taking_them_away_restores_the_file_byte_for_byte(self):
        b = str(self.book)
        structure.set_chapter_name(b, 1, "The Dam")
        structure.set_section(b, 1, 2, "The Spillway")
        structure.set_section(b, 1, 2, "", on=False)
        structure.set_chapter_name(b, 1, "")
        self.assertEqual(text_of(self.ch1), self.was,
                         "a book that has had its marks taken away is the book "
                         "it was, to the byte")

    def test_renaming_replaces_rather_than_stacking(self):
        b = str(self.book)
        structure.set_section(b, 1, 2, "First")
        structure.set_section(b, 1, 2, "Second")
        text = text_of(self.ch1)
        self.assertEqual(text.count("\\secmark"), 1)
        self.assertEqual(structure.read(b)[0]["sections"],
                         [{"para": 2, "title": "Second"}])

    def test_a_typed_title_is_text_and_not_latex(self):
        b = str(self.book)
        structure.set_section(b, 1, 2, "Water & Waste, 100% of it")
        self.assertEqual(structure.read(b)[0]["sections"][0]["title"],
                         "Water & Waste, 100% of it")
        raw = text_of(self.ch1)
        self.assertIn(r"\&", raw, "the & is escaped on the way into the .tex")
        self.assertIn(r"\%", raw, "and so is the %, which would comment the "
                                  "rest of the line out")
        self.assertEqual(shape(self.ch1), self.shape)

    def test_a_name_that_would_break_the_build_is_refused(self):
        b = str(self.book)
        for bad in ("", "   ", "two\nlines"):
            with self.assertRaises(structure.Refused):
                structure.set_section(b, 1, 2, bad)
        self.assertEqual(text_of(self.ch1), self.was,
                         "and nothing was written")

    def test_a_paragraph_that_is_not_there_is_refused(self):
        with self.assertRaises(structure.Refused):
            structure.set_section(str(self.book), 1, 99, "Nowhere")
        with self.assertRaises(structure.Refused):
            structure.set_chapter_name(str(self.book), 9, "No chapter")


class TheDoors(unittest.TestCase):
    """__struct/section and __struct/chapter, through the route table."""

    def setUp(self):
        from unittest import mock
        import serve
        self.serve, self.mock = serve, mock
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.book = self.root / "books" / "english" / "mini-en"
        self.book.parent.mkdir(parents=True)
        shutil.copytree(FIXTURE, self.book, ignore=shutil.ignore_patterns("reader"))
        # _book_dir walks up from the resolved path but only while it is still
        # under ROOT, so a scratch shelf needs both of these to be reachable
        for target, value in ((serve._AtRoot, "directory"), (serve, "ROOT")):
            p = mock.patch.object(target, value, str(self.root))
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(serve.Handler, "_rebuild_reader",
                              lambda self_, b: {"ok": True, "error": ""})
        p.start()
        self.addCleanup(p.stop)

    def post(self, door, body):
        h = object.__new__(self.serve.Handler)
        h.path = "/books/english/mini-en/reader/"
        h.directory = str(self.root)
        h._json_body = lambda: body
        h.sent = []
        h.send_json = lambda payload, status=200: h.sent.append((status, payload))
        h._route("POST", "/books/english/mini-en/reader/__struct/" + door)
        return h.sent[-1]

    def test_the_route_reaches_the_door_at_all(self):
        status, payload = self.post("section", {"para": "1:2", "title": "The Spillway"})
        self.assertNotEqual(status, 405, "_route's POST guard has to name "
                            "/__struct/ beside /__reading/ and /__edit/, or the "
                            "door is unreachable however right it is")
        self.assertEqual(status, 200, payload)

    def test_a_chapter_is_named_and_unnamed_through_the_door(self):
        status, payload = self.post("chapter", {"chapter": 1, "title": "The Dam"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["structure"][0]["name"], "The Dam")
        self.assertEqual(T.parse_chapter(str(self.book / "ch1.tex")).name, "The Dam",
                         "and it is in the .tex, not only in the answer")
        status, payload = self.post("chapter", {"chapter": 1, "title": ""})
        self.assertEqual(payload["structure"][0]["name"], "")

    def test_a_section_is_opened_renamed_and_removed_through_the_door(self):
        status, payload = self.post("section", {"para": "1:2", "title": "The Spillway"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["structure"][0]["sections"],
                         [{"para": 2, "title": "The Spillway"}])
        status, payload = self.post("section", {"para": "1:2", "title": "Rebuilt"})
        self.assertEqual(payload["structure"][0]["sections"],
                         [{"para": 2, "title": "Rebuilt"}])
        status, payload = self.post("section", {"para": "1:2", "on": False})
        self.assertEqual(payload["structure"][0]["sections"], [])

    def test_a_refusal_is_a_sentence_and_a_400(self):
        status, payload = self.post("section", {"para": "nonsense", "title": "x"})
        self.assertEqual(status, 400)
        self.assertIn("paragraph", payload["error"])
        status, payload = self.post("chapter", {"title": "x"})
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])

    def test_the_door_changes_no_number(self):
        was = shape(str(self.book / "ch1.tex"))
        self.post("chapter", {"chapter": 1, "title": "The Dam"})
        self.post("section", {"para": "1:2", "title": "The Spillway"})
        self.assertEqual(shape(str(self.book / "ch1.tex")), was)


if __name__ == "__main__":
    unittest.main(verbosity=2)
