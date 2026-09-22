# SPDX-License-Identifier: GPL-3.0-or-later
"""A stretch of the book, named by its two ends: what a recording covers.

    python3 -m unittest discover -s tests -p test_regions.py

A subparagraph's label is unique only within its chapter -- chapter 1 and
chapter 2 both have a 1.1 -- so the reader's outline writes each end with its
chapter, "2:1.1", and texparse.region_bounds reads both that and the bare
label every narration was written with before (the first subparagraph wearing
it for the start, the last for the end).  The aligner (timestamp.region_subs),
the server (its status and its two doors) and the build (NARR's lo/hi, which
the player goes by) all read a stretch through it.  The book is
tests/outline_harness.py's: three chapters, all with the labels 1.1 1.2 2.1
2.2.  The browser half -- picking, and a recording of chapter 2 played from
the right file -- is tests/outline.mjs.
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "youtube/lib", "lib", "tests", "."):
    sys.path.insert(0, str(ROOT / p))
import texparse as T  # noqa: E402

PAIRS = [("1", "1.1"), ("1", "1.2"), ("2", "1.1"), ("2", "1.2")]


class Bounds(unittest.TestCase):
    def test_nothing_named_is_the_whole_book(self):
        self.assertEqual(T.region_bounds(PAIRS, "", ""), (0, 3))
        self.assertEqual(T.region_bounds(PAIRS, None, None), (0, 3))

    def test_an_end_with_its_chapter_is_exactly_one_subparagraph(self):
        self.assertEqual(T.region_bounds(PAIRS, "2:1.1", "2:1.2"), (2, 3))
        self.assertEqual(T.region_bounds(PAIRS, "1:1.1", "1:1.2"), (0, 1))
        self.assertEqual(T.region_bounds(PAIRS, "2:1.1", ""), (2, 3))
        self.assertEqual(T.region_bounds(PAIRS, "", "1:1.2"), (0, 1))

    def test_a_bare_label_is_read_as_it_always_was(self):
        # the first 1.1 for the start and the last 1.2 for the end: the widest
        # reading, which is what every narration written before meant
        self.assertEqual(T.region_bounds(PAIRS, "1.1", "1.2"), (0, 3))
        self.assertEqual(T.region_bounds(PAIRS, "1.2", ""), (1, 3))

    def test_what_is_not_there_is_said(self):
        with self.assertRaisesRegex(ValueError, "no subparagraph 1.1 in chapter 3"):
            T.region_bounds(PAIRS, "3:1.1", "")
        with self.assertRaisesRegex(ValueError, "no subparagraph 9.9 in this book"):
            T.region_bounds(PAIRS, "", "9.9")
        with self.assertRaisesRegex(ValueError, r"ends \(1:1.1\) before it begins \(2:1.2\)"):
            T.region_bounds(PAIRS, "2:1.2", "1:1.1")
        with self.assertRaisesRegex(ValueError, "no subparagraphs"):
            T.region_bounds([], "", "")

    def test_a_chapter_named_with_a_colon_of_its_own(self):
        # the label never holds a colon, so the last one is where it starts
        self.assertEqual(T.region_bounds([("A:B", "1.1"), ("C", "1.1")], "A:B:1.1", "A:B:1.1"),
                         (0, 0))


class Book(unittest.TestCase):
    """The three-chapter book, parsed, aligned and built."""

    @classmethod
    def setUpClass(cls):
        import outline_harness
        cls.td = tempfile.mkdtemp(prefix="parseh-regions-")
        cls.d = Path(cls.td) / "books" / "english" / "outline-en"
        cls.d.parent.mkdir(parents=True)
        outline_harness.make_book(cls.d)
        # a chapter written across two files: ch2b.tex continues chapter 2
        # with paragraph 3 and says no \chapopen of its own
        src = (cls.d / "ch2.tex").read_text(encoding="utf-8")
        cont = re.sub(r"\\chapopen\{2\}", "", src)
        cont = re.sub(r"\\chapname\{[^}]*\}", "", cont)
        cont = re.sub(r"\\secmark\{[^}]*\}", "", cont)
        cont = cont.replace("\\parnum{1.", "\\parnum{3.").replace("\\parnum{2.", "\\parnum{4.")
        cont = cont.replace("\\ch{}{Then ", "\\ch{}{Later ")
        (cls.d / "ch2b.tex").write_text(cont, encoding="utf-8")
        main = (cls.d / "main.tex").read_text(encoding="utf-8")
        (cls.d / "main.tex").write_text(
            main.replace("\\input{ch2.tex}", "\\input{ch2.tex}\n\\input{ch2b.tex}"), encoding="utf-8")
        cls.chapters = T.parse_book(str(cls.d / "main.tex"), "en")
        cls.subs = [x for ch in cls.chapters for pp in ch.paragraphs for x in pp.subs]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.td, ignore_errors=True)

    def test_every_subparagraph_has_a_name_no_other_answers_to(self):
        names = [T.qualified(x) for x in self.subs]
        self.assertEqual(names[:4], ["1:1.1", "1:1.2", "1:2.1", "1:2.2"])
        self.assertEqual(len(set(names)), len(names))
        # a file that only continues a chapter is that chapter's
        self.assertEqual([T.qualified(x) for x in self.subs[8:12]],
                         ["2:3.1", "2:3.2", "2:4.1", "2:4.2"])
        self.assertEqual(sorted({x.num for x in self.subs}),
                         ["1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2"],
                         "while the labels alone repeat")

    def test_the_aligner_reads_a_stretch_the_same_way(self):
        import timestamp as ts
        got = ts.region_subs(self.subs, "2:1.1", "2:4.2")
        self.assertEqual([T.qualified(x) for x in got],
                         ["2:1.1", "2:1.2", "2:2.1", "2:2.2", "2:3.1", "2:3.2", "2:4.1", "2:4.2"])
        with self.assertRaises(SystemExit) as said:
            ts.region_subs(self.subs, "5:1.1", "")
        self.assertIn("no subparagraph 1.1 in chapter 5", str(said.exception))

    def test_the_server_refuses_a_stretch_the_book_does_not_have(self):
        import books
        import serve
        h = object.__new__(serve.Handler)
        b = books.Book(str(self.d))
        self.assertIsNone(h._region_error(b, "2:1.1", "2:2.2"))
        self.assertIsNone(h._region_error(b, "1.1", ""))
        self.assertEqual(h._region_error(b, "4:1.1", ""), "there is no subparagraph 1.1 in chapter 4")
        labels = h._sub_labels(b)
        self.assertEqual(labels[4], {"label": "1.1", "chapter": "2", "key": "2:1.1"})
        self.assertNotIn("subkey", labels[0], "the key timings.json files under is asked for")
        self.assertIn("subkey", h._sub_labels(b, subkeys=True)[0])

    def test_the_build_places_each_recording_and_labels_each_subparagraph(self):
        import serve
        import books
        audio = self.d / "audio"
        audio.mkdir(exist_ok=True)
        for name in ("a.wav", "b.wav", "c.wav"):
            (audio / name).write_bytes(b"RIFF")
        b = books.Book(str(self.d))
        serve.set_narrations(b, [
            {"id": "n1", "audio": "audio/a.wav", "transcript": "", "from": "2:1.1", "to": "2:4.2"},
            # a bare label, as every narration was written before: the widest
            # reading, from the book's first 1.1 to its last 2.2
            {"id": "n2", "audio": "audio/b.wav", "transcript": "", "from": "1.1", "to": "2.2"},
            {"id": "n3", "audio": "audio/c.wav", "transcript": "", "from": "7:1.1", "to": ""}])
        r = subprocess.run([sys.executable, str(ROOT / "lib" / "tex2html.py"), "--book", str(self.d)],
                           capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        self.assertIn("recording n3 covers nothing in this book", r.stderr)
        html = (self.d / "reader" / "index.html").read_text(encoding="utf-8")
        narr = json.loads(re.search(r"const NARR=(\[.*?\]);", html, re.S).group(1))
        subs = json.loads(re.search(r"const SUBS=(\[.*?\]);", html, re.S).group(1))
        self.assertEqual([(n["id"], n["lo"], n["hi"]) for n in narr],
                         [("n1", 4, 11), ("n2", 0, 15), ("n3", None, None)])
        # the fifth and sixth: the contents entry of the paragraph, its label
        self.assertEqual([s[5] for s in subs[4:12]],
                         ["1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2"])
        entries = [s[4] for s in subs]
        self.assertEqual(entries, [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7])
        toc = re.findall(r'<a class="toce" href="#([^"]+)"', html)
        self.assertEqual(len(toc), 8, "one contents entry per paragraph, the entries SUBS names")


if __name__ == "__main__":
    unittest.main()
