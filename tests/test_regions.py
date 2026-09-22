# SPDX-License-Identifier: GPL-3.0-or-later
"""A stretch of the book, named by its two ends: what a recording covers.

    python3 -m unittest discover -s tests -p test_regions.py

A subparagraph's label is unique only within its chapter -- chapter 1 and
chapter 2 both have a 1.1 -- so the reader's outline writes each end with its
chapter, "2:1.1", and texparse.region_bounds reads both that and the bare
label every narration was written with before (the first subparagraph wearing
it for the start; for the end, the first at or after the start).  The aligner (timestamp.region_subs),
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

    def test_a_bare_label_is_the_narrowest_stretch(self):
        # the first 1.1 for the start, and for the end the first 1.2 AT OR
        # AFTER it: the stretch somebody picking "1.1" to "1.2" meant.  The
        # last 1.2 of the book, as it used to be, made it chapters 1 and 2.
        self.assertEqual(T.region_bounds(PAIRS, "1.1", "1.2"), (0, 1))
        self.assertEqual(T.region_bounds(PAIRS, "1.2", ""), (1, 3))
        self.assertEqual(T.region_bounds(PAIRS, "", "1.2"), (0, 1))
        with self.assertRaisesRegex(ValueError, r"ends \(1.1\) before it begins \(1.2\)"):
            T.region_bounds(PAIRS[:2], "1.2", "1.1")

    def test_recordings_of_chapter_1_stay_in_chapter_1(self):
        # the book that found it: five chapters, each numbering its
        # paragraphs from 1, and nine recordings of chapter 1 stored with bare
        # labels.  Each is read inside chapter 1; none runs on into the rest.
        chapters = {"1": 157, "2": 267, "3": 297, "4": 298, "5": 323}
        pairs = [(c, "%d.%d" % (p, s)) for c, n in chapters.items()
                 for p in range(1, n + 1) for s in (1, 2)]
        for first, last in (("1.1", "6.2"), ("7.1", "36.1"), ("139.1", "141.2"),
                            ("151.1", "157.2")):
            i, j = T.region_bounds(pairs, first, last)
            self.assertEqual((pairs[i], pairs[j]), (("1", first), ("1", last)), (first, last))

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
            # a bare label, as every narration was written before: the
            # narrowest reading, chapter 1's 1.1 to chapter 1's 2.2
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
                         [("n1", 4, 11), ("n2", 0, 3), ("n3", None, None)])
        # the fifth and sixth: the contents entry of the paragraph, its label
        self.assertEqual([s[5] for s in subs[4:12]],
                         ["1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2"])
        entries = [s[4] for s in subs]
        self.assertEqual(entries, [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7])
        toc = re.findall(r'<a class="toce" href="#([^"]+)"', html)
        self.assertEqual(len(toc), 8, "one contents entry per paragraph, the entries SUBS names")



class Status(unittest.TestCase):
    """__narration/status over real HTTP: where each recording is, and how much
    of THAT stretch is timed."""

    def test_a_recording_counts_the_times_inside_what_it_covers(self):
        import http.client
        import threading
        from unittest import mock
        import books
        import outline_harness
        import serve
        import timestamp as ts
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "books" / "english" / "outline-en"
            d.parent.mkdir(parents=True)
            outline_harness.make_book(d)
            b = books.Book(str(d))
            serve.set_narrations(b, [
                {"id": "n1", "audio": "audio/a.wav", "transcript": "", "from": "1.1", "to": "2.2"},
                {"id": "n2", "audio": "audio/b.wav", "transcript": "", "from": "2:1.1", "to": "2:2.2"}])
            subs = [x for ch in T.parse_book(str(d / "main.tex"), "en") for x in ch.subs]
            rec = lambda k, n, src="spread": {"t0": 1.0 + k, "t1": 2.0 + k, "conf": 1.0,  # noqa: E731
                                             "src": src, "label": subs[k].num, "n": n}
            times = {ts.subkey(subs[0]): rec(0, "n1"), ts.subkey(subs[1]): rec(1, "n1", "manual"),
                     # n1's id on a subparagraph of chapter 3: outside what it
                     # covers, the way the too-wide reading once spread one
                     ts.subkey(subs[8]): rec(8, "n1"),
                     # a key the book no longer has: its text changed since
                     "9.9-000000000000": {"t0": 5, "t1": 6, "label": "9.9", "n": "n1"},
                     # no id, inside n2's stretch alone: n2's
                     ts.subkey(subs[5]): rec(5, ""), ts.subkey(subs[6]): rec(6, "n2", "manual")}
            (d / "timings.json").write_text(json.dumps({"subs": times}), encoding="utf-8")
            with mock.patch.object(serve.Handler, "log_request", lambda *a, **k: None), \
                    mock.patch.object(serve, "ROOT", td), \
                    mock.patch.object(serve._AtRoot, "directory", td):
                srv = serve.Server(("127.0.0.1", 0), serve.Handler)
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                try:
                    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=60)
                    c.request("GET", "/books/english/outline-en/reader/__narration/status")
                    j = json.loads(c.getresponse().read())
                    c.close()
                finally:
                    srv.shutdown()
                    srv.server_close()
        self.assertEqual([(n["id"], n["lo"], n["hi"], n["timed"], n["subs"], n["manual"])
                          for n in j["narrations"]],
                         [("n1", 0, 3, 2, 4, 1), ("n2", 4, 7, 2, 4, 1)])


if __name__ == "__main__":
    unittest.main()
