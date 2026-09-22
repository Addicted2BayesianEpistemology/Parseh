#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""What somebody has decided about a book's own text: lib/reading.py.

    python3 tests/test_reading.py

Two decisions, both about paragraphs and both kept with the book:

  * a paragraph TAKEN CHARGE OF -- one that need not reproduce
    source/paras/.  The reader's chunk sheet sets it, and both checkers have
    to honour it: what the editor allows, the checker may not then call a
    fault, or the book would be refused on upload for an edit the toolbox
    itself invited.  It is per PARAGRAPH because the check is per paragraph.
  * a run of paragraphs FOLDED AWAY.

The doors are driven through serve.Handler._route rather than by calling the
handler method directly, because the route table is a SECOND place a door has
to be named: _books_post dispatches on the path, but only after the guard in
_route lets a POST through at all.  A door written and not named in that
guard answers 405, the page says only "refused", and every other check --
the handler exists, the ids are in the built page, the build bakes the
tables -- still passes.  That is exactly how this one was found.
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
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT))
import reading                                                  # noqa: E402
import texwrite                                                 # noqa: E402
import verify_book                                              # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "books" / "english" / "mini-en"

# mini-en's ch1.tex: paragraph 1 is \parnum 1.1 and 1.2 -- chunks 0..5, held
# against source/paras/ch1_p00.txt -- and paragraph 2 is 2.1 and 2.2, chunks
# 6..12, against ch1_p01.txt.  Every chunk is a plain \ch with no word line,
# so an edit to one is judged by fidelity and not stopped earlier by the
# words check, and a refusal here therefore means what this file says it does.
PARA1_CHUNK = 0
PARA2_CHUNK = 6


class TheFile(unittest.TestCase):
    """reading.json itself: what it holds, and what it does not keep."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = td.name

    def test_a_book_nobody_has_decided_anything_about_reads_as_empty(self):
        self.assertEqual(reading.load(self.d), {"free": [], "collapsed": []})
        self.assertFalse(os.path.exists(reading.path_for(self.d)),
                         "and has no file, which is what it looked like before")

    def test_a_paragraph_is_taken_charge_of_and_given_back(self):
        reading.set_free(self.d, 1, 13, True)
        self.assertTrue(reading.is_free(self.d, 1, 13))
        self.assertFalse(reading.is_free(self.d, 1, 12), "its neighbour is not")
        self.assertFalse(reading.is_free(self.d, 2, 13), "nor the same number "
                         "in another chapter")
        reading.set_free(self.d, 1, 13, False)
        self.assertFalse(reading.is_free(self.d, 1, 13))
        self.assertFalse(os.path.exists(reading.path_for(self.d)),
                         "and with nothing left to say the file goes away again")

    def test_two_runs_that_meet_are_one_run(self):
        reading.collapse(self.d, "1:5", "1:9")
        doc = reading.collapse(self.d, "1:10", "1:12")
        self.assertEqual(doc["collapsed"], [["1:5", "1:12"]],
                         "touching runs join -- two bars with nothing between "
                         "them is not what folding looks like")

    def test_a_run_in_another_chapter_stays_its_own(self):
        reading.collapse(self.d, "1:5", "1:9")
        doc = reading.collapse(self.d, "2:3", "2:4")
        self.assertEqual(doc["collapsed"], [["1:5", "1:9"], ["2:3", "2:4"]])

    def test_the_ends_may_arrive_either_way_round(self):
        doc = reading.collapse(self.d, "1:9", "1:5")
        self.assertEqual(doc["collapsed"], [["1:5", "1:9"]])

    def test_a_run_nested_in_another_is_absorbed_by_it(self):
        reading.collapse(self.d, "1:5", "2:3")
        doc = reading.collapse(self.d, "1:7", "1:8")
        self.assertEqual(doc["collapsed"], [["1:5", "2:3"]],
                         "kept beside it, nothing would ever draw the inner "
                         "run's bar -- foldedRun answers with the first run "
                         "that contains a paragraph -- while the sheet went on "
                         "offering to unfold it, which left the text folded")

    def test_runs_that_overlap_across_a_chapter_boundary_join(self):
        reading.collapse(self.d, "2:1", "2:4")
        doc = reading.collapse(self.d, "1:8", "2:2")
        self.assertEqual(doc["collapsed"], [["1:8", "2:4"]],
                         "overlapping is not a question about chapters, and "
                         "the sheet offers every paragraph in the book")

    def test_unfolding_from_inside_an_absorbed_run_leaves_nothing_folded(self):
        reading.collapse(self.d, "1:5", "2:3")
        reading.collapse(self.d, "1:7", "1:8")
        doc = reading.collapse(self.d, "1:7", "1:7", on=False)
        self.assertEqual(doc["collapsed"], [],
                         "one run went in and one comes out: a fold must never "
                         "survive its own unfold")

    def test_the_ends_of_two_chapters_are_not_assumed_to_touch(self):
        reading.collapse(self.d, "1:5", "1:9")
        doc = reading.collapse(self.d, "2:1", "2:2")
        self.assertEqual(doc["collapsed"], [["1:5", "1:9"], ["2:1", "2:2"]],
                         "nothing in this file knows how many paragraphs "
                         "chapter 1 has, so 1:9 and 2:1 are not adjacent")

    def test_a_run_brought_within_reach_by_the_first_join_joins_too(self):
        reading.collapse(self.d, "1:1", "1:2")
        reading.collapse(self.d, "1:4", "1:5")
        doc = reading.collapse(self.d, "1:3", "1:3")
        self.assertEqual(doc["collapsed"], [["1:1", "1:5"]],
                         "one paragraph closes the gap between two runs, and "
                         "swallowing the first brings the second within reach")

    def test_a_run_is_unfolded_by_any_paragraph_in_it(self):
        reading.collapse(self.d, "1:5", "1:9")
        doc = reading.collapse(self.d, "1:7", "1:7", on=False)
        self.assertEqual(doc["collapsed"], [], "the whole run goes, not a hole "
                         "cut in the middle of it")

    def test_a_paragraph_knows_which_run_holds_it(self):
        doc = reading.collapse(self.d, "1:5", "1:9")
        self.assertEqual(reading.in_collapsed(doc, 1, 7), ["1:5", "1:9"])
        self.assertIsNone(reading.in_collapsed(doc, 1, 4))
        self.assertIsNone(reading.in_collapsed(doc, 2, 7))

    def test_a_name_that_is_not_a_paragraph_is_refused(self):
        with self.assertRaises(ValueError):
            reading.collapse(self.d, "nonsense", "1:4")

    def test_junk_in_the_file_is_ignored_rather_than_believed(self):
        with io.open(reading.path_for(self.d), "w", encoding="utf-8") as f:
            json.dump({"free": ["1:4", "rubbish", 7],
                       "collapsed": [["1:2", "1:3"], "no", ["1:9"]]}, f)
        self.assertEqual(reading.load(self.d),
                         {"free": ["1:4"], "collapsed": [["1:2", "1:3"]]})


class TheCheckers(unittest.TestCase):
    """The promise: what the editor allows, the checkers do not call a fault."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.book = Path(td.name) / "mini-en"
        shutil.copytree(FIXTURE, self.book, ignore=shutil.ignore_patterns("reader"))
        self.ch1 = str(self.book / "ch1.tex")

    def edit(self, index, fa):
        return texwrite.edit_chunk(self.ch1, index, {"fa": fa})

    def test_without_the_mark_the_edit_is_refused(self):
        with self.assertRaises(texwrite.Refused) as e:
            self.edit(PARA1_CHUNK, "The young man")
        self.assertIn("source/paras/ch1_p00.txt", str(e.exception))

    def test_with_the_mark_the_same_edit_is_written(self):
        reading.set_free(str(self.book), 1, 1, True)
        r = self.edit(PARA1_CHUNK, "The young man")
        self.assertTrue(r["changed"], r)
        self.assertIn("reading.json", r["fidelity"])
        self.assertTrue(r["fidelity"].startswith("not checked:"),
                        "a note in the vocabulary the sheet already uses, not "
                        "an 'ok' that would claim the source was reproduced: "
                        "%s" % r["fidelity"])
        with io.open(self.ch1, encoding="utf-8") as f:
            self.assertIn("The young man", f.read())

    def test_the_mark_frees_that_paragraph_and_no_other(self):
        reading.set_free(str(self.book), 1, 1, True)
        with self.assertRaises(texwrite.Refused) as e:
            self.edit(PARA2_CHUNK, "A woman came in")
        self.assertIn("source/paras/ch1_p01.txt", str(e.exception),
                      "paragraph 2 is checked exactly as it was -- the mark is "
                      "a door held open for one paragraph, not the check off")

    def test_verify_book_names_it_and_still_passes_the_book(self):
        reading.set_free(str(self.book), 1, 1, True)
        self.edit(PARA1_CHUNK, "The young man")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = verify_book.main(str(self.book))
        said = out.getvalue()
        self.assertEqual(rc, 0, said)
        self.assertIn("NOT CHECKED chapter 1 paragraph 1", said)
        self.assertIn("1 marked as departing from it", said)
        self.assertIn("0 mismatched", said,
                      "and it is not counted as a mismatch, which is what "
                      "would refuse the book on upload")

    def test_a_book_with_no_marks_is_checked_exactly_as_before(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = verify_book.main(str(self.book))
        said = out.getvalue()
        self.assertEqual(rc, 0, said)
        self.assertNotIn("NOT CHECKED", said)
        self.assertNotIn("departing", said,
                         "a book nobody has decided anything about says nothing "
                         "about reading.json at all")


class TheKeys(unittest.TestCase):
    """What the build may call a paragraph, in books it did not write.

    Folding has to work on any book, including editions made long before any
    of this existed, and a paragraph is named "<chapter>:<paragraph>" where
    the chapter is the number in the FILE'S NAME.  Two old shapes say whether
    that holds, and neither is in the plain fixture:

      * a .tex whose name carries no number -- a characters.tex beside the
        chapters, which build.sh takes and verify_book.py names and skips,
        because source/paras/ch<N>_p<NN>.txt is made of the number.  Two of
        them would both be "0:1", and folding one would fold the other, so
        they are given no key at all: shown, never folded;
      * a paragraph CONTINUED IN A SECOND FILE -- ch1.tex and ch1b.tex are
        both chapter 1 -- written as one .para per piece, each carrying the
        same key.  The pieces must fold as one paragraph; the page merges
        them into one stretch (PARAT), which tests/folding.mjs holds.
    """

    def build(self, name, text):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        d = Path(td.name) / "book"
        shutil.copytree(FIXTURE, d, ignore=shutil.ignore_patterns("reader"))
        (d / name).write_text(text, encoding="utf-8")
        mp = d / "main.tex"
        s = mp.read_text(encoding="utf-8")
        # chapter order is main.tex's \input lines and nowhere else
        # (texparse.parse_book), so a file not named there is not in the book
        self.assertIn("\\input{ch1.tex}", s)
        mp.write_text(s.replace("\\input{ch1.tex}",
                                "\\input{ch1.tex}\n\\input{%s}" % name),
                      encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "lib" / "tex2html.py"),
                            "--book", str(d)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr or r.stdout)
        # a book of several chapters keeps all but the first in a fragment
        # beside the reader, so the whole of it is every .html there
        out = d / "reader"
        return "".join((out / f).read_text(encoding="utf-8")
                       for f in sorted(os.listdir(out)) if f.endswith(".html"))

    def paras(self, html):
        return json.loads(re.search(r"const PARAS=(\[.*?\]);", html, re.S).group(1))

    def test_a_tex_with_no_chapter_number_names_no_paragraph(self):
        html = self.build("characters.tex",
                          "\\parstart{9.1}{The names in this book}\n"
                          "\\parnum{9.1}\n\\begin{frank}\n"
                          "\\ch{}{The names in this book}{\u00f0\u0259 ne\u026amz}"
                          "{}{the names in this book}\n"
                          "\\end{frank}\n\\parend\n")
        self.assertEqual(self.paras(html), [["1:1", 0, 1], ["1:2", 2, 3]],
                         "the chapters are named; the file that is not a "
                         "chapter is not")
        self.assertNotIn('data-p="0:', html,
                         "and nothing is called chapter 0, which two such "
                         "files would both answer to")
        self.assertIn("The names in this book", html,
                      "it is still in the book -- not foldable is not hidden")

    def test_a_paragraph_continued_in_a_second_file_keeps_one_name(self):
        html = self.build("ch1b.tex",
                          "\\parnum{2.3}\n\\begin{frank}\n"
                          "\\ch{}{and went home.}{\u0259n w\u025bnt ho\u028am}"
                          "{}{and went home.}\n"
                          "\\end{frank}\n\\parend\n")
        paras = self.paras(html)
        self.assertEqual(paras, [["1:1", 0, 1], ["1:2", 2, 3], ["1:2", 4, 4]],
                         "one paragraph, two pieces, one name")
        self.assertEqual([p[0] for p in paras].count("1:2"), 2,
                         "and the build says so rather than hiding it, so the "
                         "page can put the pieces back together")


class TheThirdChecker(unittest.TestCase):
    """check_batch.py honours the mark too.

    THREE files implement the source-fidelity rule -- texwrite._fidelity,
    verify_book.py and lib/check_batch.py -- and a paragraph the reader's own
    editor was allowed to change must not then be refused by the checker
    somebody runs next.  Only verify_book.py is on the upload path, so this one
    cannot refuse a book coming back; it can, though, tell an author their
    edition is broken when it is not.

    Held here because nothing else in the suite runs check_batch against a
    paragraph that MISMATCHES: the first version of this very fix crashed on
    that one path -- main() binds a local named `reading` (a chunk's reading
    line), which shadows the module for the whole function -- and every other
    suite stayed green while the door was dead.
    """

    def para_json(self, book_dir):
        """The annotator's JSON for paragraph 1, built from the .tex itself,
        the way tests/test_wordbook_parsers.py's para0 builds it."""
        import books as booklib
        import texparse
        b = booklib.Book(str(book_dir))
        para = texparse.parse_book(b.main, b.lang)[0].paragraphs[0]
        sents = []
        for s in para.subs:
            out = []
            for c in s.chunks:
                d = {"fa": c.fa, "tr": c.tr, "voc": c.voc, "en": c.en}
                if getattr(c, "kana", ""):
                    d["kana"] = c.kana
                if getattr(c, "wordline", ""):
                    d["words"] = c.wordline
                out.append(d)
            sents.append({"chunks": out})
        # idx is the 0-based number in source/paras/ch1_p00.txt, so this is
        # paragraph 1 -- the one reading.json calls "1:1"
        return {"idx": 0, "ch": 1, "ann": {"sentences": sents}}

    def check(self, book_dir, para_path):
        r = subprocess.run([sys.executable, str(ROOT / "lib" / "check_batch.py"),
                            str(para_path), "--book", str(book_dir)],
                           capture_output=True, text=True, cwd=str(book_dir))
        return r.stdout + r.stderr

    def test_a_paragraph_taken_charge_of_is_not_called_a_mismatch(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        book = Path(td.name) / "mini-en"
        shutil.copytree(FIXTURE, book, ignore=shutil.ignore_patterns("reader"))
        blob = self.para_json(book)
        # mini-en's chunks carry no word line, so this breaks the source
        # comparison and nothing else: what is left is the one rule under test
        blob["ann"]["sentences"][0]["chunks"][0]["fa"] = "The young man"
        para = book / "para0.json"
        para.write_text(json.dumps(blob, ensure_ascii=False), encoding="utf-8")

        said = self.check(book, para)
        self.assertIn("TEXT MISMATCH", said, said)

        reading.set_free(str(book), 1, 1, True)
        said = self.check(book, para)
        self.assertNotIn("Traceback", said,
                         "the module must not be shadowed by main()'s own "
                         "`reading`: %s" % said)
        self.assertNotIn("TEXT MISMATCH", said, said)
        self.assertIn("FIDELITY NOT CHECKED", said, said)


class TheRoundTrip(unittest.TestCase):
    """Download a book that departs from its source, and upload it again.

    The thing that must never happen: a paragraph taken charge of in the
    reader, edited so that it really does depart from its source, packed by
    the download, and then REFUSED on the way back in for the very mismatch
    the mark permits.  The upload's check is bundle._fidelity, which runs
    verify_book.main on the unpacked tree -- so reading.json has to be
    unpacked before that check is made, and the checker has to honour it.
    Neither is obvious from either file alone, which is why it is held here.
    """

    def test_an_exempt_paragraph_that_departs_survives_the_round_trip(self):
        import bundle
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        book = root / "books" / "english" / "mini-en"
        book.parent.mkdir(parents=True)
        shutil.copytree(FIXTURE, book, ignore=shutil.ignore_patterns("reader"))

        reading.set_free(str(book), 1, 1, True)
        texwrite.edit_chunk(str(book / "ch1.tex"), PARA1_CHUNK,
                            {"fa": "The young man"})
        # the book now genuinely fails the rule, and says so itself
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            verify_book.main(str(book))
        self.assertIn("NOT CHECKED", out.getvalue())

        data, _ = bundle.pack_book(str(book))
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        self.assertTrue([n for n in names if n.endswith("reading.json")],
                        "the mark is in the zip: %s" % names)

        far = root / "far"
        (far / "books").mkdir(parents=True)
        res = bundle.install(data, root=str(far))
        self.assertTrue(res.get("ok"), res)
        there = far / "books" / "english" / "mini-en"
        self.assertTrue(reading.is_free(str(there), 1, 1),
                        "and the same paragraph is still taken charge of, so it "
                        "can be edited on the far side exactly as it was here")

    def test_without_the_mark_the_same_book_is_refused(self):
        """The other half: the check is still a check."""
        import bundle
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        book = root / "books" / "english" / "mini-en"
        book.parent.mkdir(parents=True)
        shutil.copytree(FIXTURE, book, ignore=shutil.ignore_patterns("reader"))

        # depart from the source with the mark, then take the mark away again:
        # the text is what it is, and nothing now excuses it
        reading.set_free(str(book), 1, 1, True)
        texwrite.edit_chunk(str(book / "ch1.tex"), PARA1_CHUNK,
                            {"fa": "The young man"})
        reading.set_free(str(book), 1, 1, False)

        data, _ = bundle.pack_book(str(book))
        far = root / "far"
        (far / "books").mkdir(parents=True)
        with self.assertRaises(Exception) as e:
            bundle.install(data, root=str(far))
        self.assertIn("source", str(e.exception).lower(),
                      "refused for the text, and it says so: %s" % e.exception)


class TheDoors(unittest.TestCase):
    """__reading/free and __reading/fold, through the route table."""

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
        # under ROOT -- the guard that stops a request naming a book outside
        # the toolbox -- so a scratch shelf needs both of these to be reachable
        for target, value in ((serve._AtRoot, "directory"), (serve, "ROOT")):
            p = mock.patch.object(target, value, str(self.root))
            p.start()
            self.addCleanup(p.stop)
        # the reader is rebuilt after every decision; that it is rebuilt is
        # tex2html's affair and is covered where the build is
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
        h._route("POST", "/books/english/mini-en/reader/__reading/" + door)
        return h.sent[-1]

    def test_the_route_reaches_the_door_at_all(self):
        status, payload = self.post("free", {"para": "1:1", "on": True})
        self.assertNotEqual(status, 405, "_route's POST guard has to name "
                            "/__reading/ beside /__edit/ and /__narration/, or "
                            "the door is unreachable however right it is")
        self.assertEqual(status, 200, payload)

    def test_a_paragraph_is_taken_charge_of_through_the_door(self):
        status, payload = self.post("free", {"para": "1:2", "on": True})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["reading"]["free"], ["1:2"])
        self.assertTrue(reading.is_free(str(self.book), 1, 2),
                        "and it is on disk, not only in the answer")
        status, payload = self.post("free", {"para": "1:2", "on": False})
        self.assertEqual(payload["reading"]["free"], [])

    def test_a_run_is_folded_and_unfolded_through_the_door(self):
        status, payload = self.post("fold", {"from": "1:1", "to": "1:2",
                                             "on": True})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["reading"]["collapsed"], [["1:1", "1:2"]])
        status, payload = self.post("fold", {"from": "1:2", "on": False})
        self.assertEqual(payload["reading"]["collapsed"], [],
                         "named by a paragraph inside it, as the bar's own "
                         "unfold button names it")

    def test_one_paragraph_folds_on_its_own(self):
        status, payload = self.post("fold", {"from": "1:2", "on": True})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["reading"]["collapsed"], [["1:2", "1:2"]],
                         "no `to` means the run is that one paragraph")

    def test_a_name_that_is_not_a_paragraph_is_refused(self):
        status, payload = self.post("free", {"para": "nonsense", "on": True})
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        status, payload = self.post("fold", {"from": "nonsense", "on": True})
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])


if __name__ == "__main__":
    unittest.main()
