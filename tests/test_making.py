# SPDX-License-Identifier: GPL-3.0-or-later
"""A book made by an agent, in place (a0.4.2, TO-DO §8.40): the folder, the
record, the asks, the draft and Finish.

    python3 -m unittest tests/test_making.py

Held here, all of it on real files in a temporary tree and never in the
checkout's books/:

  * making.make writes the whole folder or nothing -- book.json, the main.tex
    skeleton, the original inside the book's own folder, the journal, an EMPTY
    ASKS.md, making.json and the instructions -- puts the book on the shelf at
    once, and leaves no staging directory behind whatever it refuses;
  * the record: what an agent's half-written or wrong making.json still reads
    as, the words for every stage, and that a file that will not parse is a
    book still being made (the lock on editing must not lift for it);
  * an ask is one dated entry, appended whole, and refused for a finished book;
  * the tools that read a book take one with no chapter yet, and one whose
    main.tex grows a batch at a time, with a frankdraft.* beside it, an annot/
    and an original/ in the folder;
  * Finish: check, then the full build, both clean before the making ends, and
    what it says in words when either is not.
"""
import calendar
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "lib", "youtube/lib", "."):
    sys.path.insert(0, str(ROOT / p))
import books as booklib                                        # noqa: E402
import bookbuild                                               # noqa: E402
import bundle                                                  # noqa: E402
import making                                                  # noqa: E402

PY = os.environ.get("PARSEH_PYTHON") or sys.executable
PDF = b"%PDF-1.4\n% a tiny stand-in, enough to look like one\n1 0 obj<<>>endobj\n%%EOF\n"
FIELDS = {"lang": "it", "gloss": "en", "title": "Il gatto", "title_latin": "Il gatto",
          "author": "Anonimo", "author_latin": "Anonimo", "year": "1900", "blurb": "A cat.",
          "pages": "1-3"}
TEXT = b"Il gatto dorme.\n\nIl cane corre.\n"


def tmpdir(test):
    d = tempfile.mkdtemp(prefix="test-making-", dir=os.environ.get("TMPDIR") or None)
    test.addCleanup(shutil.rmtree, d, ignore_errors=True)
    return d


def made(test, fields=None, original=None, options=None):
    into = os.path.join(tmpdir(test), "books")
    os.makedirs(into)
    r = making.make(dict(FIELDS, **(fields or {})),
                    original or {"name": "Il Gatto.txt", "data": TEXT}, options, into=into)
    return into, r


class TheFolder(unittest.TestCase):
    def test_it_is_written_whole(self):
        into, r = made(self)
        d = Path(r["path"])
        self.assertEqual(d, Path(into, "italian", "il-gatto"))
        for name in ("book.json", "main.tex", "NOTES.md", "ASKS.md", "making.json", "AGENTS.md",
                     "CLAUDE.md", "original/Il-Gatto.txt"):
            self.assertTrue((d / name).is_file(), name)
        for sub in ("source/paras", "annot"):
            self.assertTrue((d / sub).is_dir(), sub)
        self.assertEqual((d / "original" / "Il-Gatto.txt").read_bytes(), TEXT)
        meta = json.loads((d / "book.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["slug"], meta["language"], meta["gloss"], meta["main"]),
                         ("il-gatto", "it", "en", "main.tex"))
        # the original is where the book's own folder says it is: not others/, which no update keeps
        self.assertEqual(meta["source_pdf"], "original/Il-Gatto.txt")
        self.assertNotIn("source_pages", meta, "a page range is a PDF's")
        self.assertEqual(sorted(r["files"]), sorted(
            ["AGENTS.md", "ASKS.md", "CLAUDE.md", "NOTES.md", "book.json", "main.tex",
             "making.json", "original/Il-Gatto.txt"]))

    def test_the_asks_file_is_empty_and_the_record_starts_as_a_folder_made(self):
        _into, r = made(self)
        d = Path(r["path"])
        self.assertEqual((d / "ASKS.md").read_bytes(), b"")
        doc = json.loads((d / "making.json").read_text(encoding="utf-8"))
        self.assertEqual((doc["state"], doc["stage"], doc["parseh"]), ("making", "folder",
                                                                       making.version.VERSION))
        self.assertTrue(making._epoch(doc["started"]) and making._epoch(doc["updated"]))
        self.assertEqual(making.state(str(d)), "making")
        self.assertTrue(making.is_making(str(d)))

    def test_the_skeleton_is_the_one_newbook_has_with_nothing_left_unfilled(self):
        _into, r = made(self, {"title_latin_upper": "IL GATTO"})
        tex = (Path(r["path"]) / "main.tex").read_text(encoding="utf-8")
        self.assertNotIn("{{", tex)
        for line in (r"\newcommand{\BookLang}{it}", r"\newcommand{\BookGloss}{en}",
                     r"\newcommand{\BookTitleLatin}{IL GATTO}", r"\newcommand{\FrankLib}{../../../lib}"):
            self.assertIn(line, tex)
        # not one \input of a chapter: the agent adds one per batch
        self.assertFalse([l for l in tex.split("\n") if l.startswith("\\input{ch")])

    def test_the_book_is_on_the_shelf_at_once_and_no_staging_is_left(self):
        into, r = made(self)
        shelf = booklib.all_books(into)
        self.assertEqual([b.dir for b in shelf], [os.path.realpath(r["path"])])
        b = shelf[0]
        self.assertEqual((b.language, b.gloss, b.title_latin), ("it", "en", "Il gatto"))
        self.assertEqual(os.listdir(os.path.join(into, "italian")), ["il-gatto"])

    def test_a_pdf_keeps_its_page_range(self):
        _into, r = made(self, original={"name": "book.pdf", "data": PDF})
        meta = json.loads((Path(r["path"]) / "book.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["source_pdf"], meta["source_pages"]), ("original/book.pdf", [1, 3]))
        self.assertIn("pages 1-3", (Path(r["path"]) / "NOTES.md").read_text(encoding="utf-8"))

    def test_an_upload_spooled_to_disk_is_copied_not_read_into_memory(self):
        spool = os.path.join(tmpdir(self), "spool")
        Path(spool).write_bytes(PDF)
        _into, r = made(self, original={"name": "big.pdf", "path": spool})
        self.assertEqual((Path(r["path"]) / "original" / "big.pdf").read_bytes(), PDF)
        self.assertTrue(os.path.exists(spool), "the caller deletes what it spooled")

    def test_what_is_refused_is_refused_in_words_and_writes_nothing(self):
        into = os.path.join(tmpdir(self), "books")
        os.makedirs(into)
        cases = (
            ({"lang": "klingon"}, None, "klingon"),
            ({"gloss": "klingon"}, None, "klingon"),
            ({"title": ""}, None, "needs a title"),
            ({"title": "50% off"}, None, "the title cannot hold the character %"),
            ({"author_latin": "A\\B"}, None, "the transliterated author cannot hold a backslash"),
            ({"title": "کتاب", "title_latin": "", "slug": ""}, None, "no directory name"),
            ({}, {"name": "book.docx", "data": b"PK\x03\x04 x"}, "PDF with a text layer"),
            ({}, {"name": "book.pdf", "data": b"not a pdf at all"}, "does not look like a PDF"),
            ({}, {"name": "book.epub", "data": b"not a zip"}, "does not look like an epub"),
            ({}, {"name": "book.txt", "data": b"binary\x00\x01"}, "does not look like a text file"),
            ({}, {"name": "book.txt", "data": b""}, "is empty"),
            ({"pages": "9-2"}, {"name": "b.pdf", "data": PDF}, "first not after the last"),
            ({"pages": "nine"}, {"name": "b.pdf", "data": PDF}, "13-21"),
        )
        for fields, original, said in cases:
            with self.subTest(said=said):
                with self.assertRaisesRegex(ValueError, said):
                    making.make(dict(FIELDS, **fields), original or {"name": "a.txt", "data": TEXT},
                                into=into)
                self.assertEqual(os.listdir(into), [], "no folder, no staging")
        with self.assertRaisesRegex(ValueError, "there is no book called"):
            making.make(FIELDS, {"name": "a.txt", "data": TEXT}, {"reference": "italian/nothing"},
                        into=into)
        self.assertEqual(os.listdir(into), [])

    def test_a_name_is_taken_in_any_state_and_the_book_there_is_untouched(self):
        into, r = made(self)
        marker = Path(r["path"], "NOTES.md")
        marker.write_text("mine", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "a book is already at books/italian/il-gatto/"):
            making.make(FIELDS, {"name": "a.txt", "data": TEXT}, into=into)
        self.assertEqual(marker.read_text(encoding="utf-8"), "mine")
        self.assertEqual(os.listdir(os.path.join(into, "italian")), ["il-gatto"])

    def test_the_originals_name_cannot_climb_or_hide(self):
        for given, want in (("../../etc/passwd.txt", "passwd.txt"), ("C:\\Users\\me\\Il Gatto.PDF", "Il-Gatto.pdf"),
                            ("کتاب.txt", "original.txt"), (".hidden.txt", "hidden.txt")):
            self.assertEqual(making._original_name(given), want, given)

    def test_every_language_of_the_registry_and_a_right_to_left_title(self):
        import languages
        for code in languages.CODES:
            with self.subTest(code=code):
                into = os.path.join(tmpdir(self), "books")
                os.makedirs(into)
                r = making.make({"lang": code, "gloss": "en", "title": "کتاب", "title_latin": "Ketab",
                                 "author": "نویسنده", "author_latin": "Nevisande"},
                                {"name": "a.txt", "data": TEXT}, into=into)
                L = languages.get(code)
                self.assertEqual(r["dir"], "%s/ketab" % L.folder)
                self.assertEqual(booklib.all_books(into)[0].language, code)


class ReferenceAndExamples(unittest.TestCase):
    """Learn from is optional and none by default; the box that lets the agent
    look at the person's finished books in this language is off by default, and
    when it is ticked names those books and no others."""

    def shelf_with(self, *books):
        into = os.path.join(tmpdir(self), "books")
        for folder, slug, lang, extra in books:
            d = Path(into, folder, slug)
            d.mkdir(parents=True)
            (d / "book.json").write_text(json.dumps({"slug": slug, "language": lang, "title": slug,
                                                     "title_latin": slug}), encoding="utf-8")
            (d / "main.tex").write_text("\\end{document}\n", encoding="utf-8")
            for name, text in extra.items():
                (d / name).write_text(text, encoding="utf-8")
        return into

    def agents(self, into, options):
        r = making.make(FIELDS, {"name": "a.txt", "data": TEXT}, options, into=into)
        return (Path(r["path"]) / "AGENTS.md").read_text(encoding="utf-8")

    def test_by_default_the_agent_is_shown_nothing_of_the_shelf(self):
        into = self.shelf_with(("italian", "finished-one", "it", {}), ("persian", "farsi", "fa", {}))
        text = self.agents(into, None)
        for name in ("finished-one", "farsi", "learn the method from"):
            self.assertNotIn(name, text)

    def test_a_reference_is_named_where_it_lies_and_never_copied(self):
        into = self.shelf_with(("persian", "farsi", "fa", {"NOTES.md": "notes"}))
        text = self.agents(into, {"reference": "persian/farsi"})
        self.assertIn(os.path.join(into, "persian", "farsi"), text)
        self.assertIn("read it, change nothing", text)
        self.assertFalse(os.path.exists(os.path.join(into, "italian", "il-gatto", "farsi")))

    def test_a_reference_cannot_climb_out_of_the_shelf(self):
        into = self.shelf_with()
        for bad in ("../etc", "italian/../../x", "/etc", ".trash/x", "a/b/c"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    making.make(FIELDS, {"name": "a.txt", "data": TEXT}, {"reference": bad}, into=into)

    def test_the_box_names_this_languages_finished_books_and_no_other_language_and_no_book_still_being_made(self):
        into = self.shelf_with(("italian", "done-it", "it", {}), ("italian", "half-it", "it",
                                                                  {"making.json": '{"state": "making"}'}),
                               ("italian", "closed-it", "it", {"making.json": '{"state": "finished"}'}),
                               ("persian", "farsi", "fa", {}))
        text = self.agents(into, {"examples": True})
        self.assertIn("done-it", text)
        self.assertIn("closed-it", text)
        self.assertNotIn("half-it", text)
        self.assertNotIn("farsi", text)
        self.assertIn("as examples only", text)


class TheInstructionsSeam(unittest.TestCase):
    def test_write_instructions_writes_two_files_and_replaces_only_them(self):
        into, r = made(self)
        d = r["path"]
        Path(d, "NOTES.md").write_text("journal", encoding="utf-8")
        facts = making.facts_for(making._identity(FIELDS), "Il-Gatto.txt", None, {}, d, into)
        for name in ("AGENTS.md", "CLAUDE.md"):
            os.unlink(os.path.join(d, name))
        self.assertEqual(making.write_instructions(d, facts, {}), ["AGENTS.md", "CLAUDE.md"])
        self.assertEqual(Path(d, "NOTES.md").read_text(encoding="utf-8"), "journal")

    def test_claude_md_is_one_line_pointing_at_agents_md(self):
        _into, r = made(self)
        one = (Path(r["path"]) / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertEqual(len(one.strip().splitlines()), 1)
        self.assertIn("AGENTS.md", one)

    def test_the_stub_says_what_a_working_agent_needs(self):
        _into, r = made(self)
        text = (Path(r["path"]) / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("{{", text)
        import runtime
        python = runtime.find_env()[1] or sys.executable
        for must in (making.LIB, python, r["path"], "original/Il-Gatto.txt", "ASKS.md", "NOTES.md",
                     "making.json", "Write only inside this folder", "Never run the full build",
                     "frankdraft.pdf", "docs/lang/it.md"):
            self.assertIn(must, text)
        # no terminal step for the person, no copy of the tools, nothing to bring back
        for gone in ("conda env create", "conda activate", "others/", "PROMPT.md", "cp -r"):
            self.assertNotIn(gone, text)

    def test_the_page_shows_the_same_text_the_folder_gets(self):
        into, r = made(self, {"title_latin_upper": ""})
        asked = making.instructions_for(dict(FIELDS, original="Il Gatto.txt"), None, into=into)
        # the folder is made where the page says it will be, so the words agree to the letter
        # but for the folder itself, which did not exist while the page asked
        written = (Path(r["path"]) / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(asked, written)

    def test_the_preview_is_asked_while_the_form_is_half_filled(self):
        text = making.instructions_for({"lang": "fa", "gloss": "en"})
        self.assertIn("Persian", text)
        self.assertNotIn("{{", text)


class TheRecord(unittest.TestCase):
    def folder(self, doc=None, raw=None):
        _into, r = made(self)
        if doc is not None:
            Path(r["path"], "making.json").write_text(json.dumps(doc), encoding="utf-8")
        if raw is not None:
            Path(r["path"], "making.json").write_text(raw, encoding="utf-8")
        return r["path"]

    def test_the_words_for_every_stage(self):
        w = making.stage_words
        self.assertEqual(w({}), "not started yet")
        self.assertEqual(w({"stage": "source"}), "source recovered")
        self.assertEqual(w({"stage": "chapters"}), "chapter table")
        self.assertEqual(w({"stage": "batch", "batches": {"done": 1, "of": 6}}), "batch 2 of 6")
        self.assertEqual(w({"stage": "batch", "batches": {"done": 0, "of": 0}}), "batch 1")
        self.assertEqual(w({"stage": "batch", "batches": {"done": 6, "of": 6}}), "all batches in")
        self.assertEqual(w({"stage": "done"}), "all batches in")
        self.assertEqual(w({"state": "finished", "stage": "batch"}), "finished")
        self.assertEqual(w({"stage": "something the agent made up"}), "something the agent made up")

    def test_a_wrong_or_half_written_file_still_reads(self):
        for doc in ({"stage": None, "batches": "many", "chapters": "one", "checks": [1, 2], "on": 7},
                    {"batches": {"done": "x", "of": -3}, "chapters": [None, "a", {"chapter": "x"}, 3]},
                    {"updated": "yesterday", "started": [1], "parseh": {"a": 1}}):
            d = self.folder(doc)
            got = making.describe(d)
            self.assertTrue(got["ok"] and got["making"], doc)
            json.dumps(got)                 # and it goes out as JSON

    def test_a_file_that_will_not_parse_is_a_book_still_being_made(self):
        for raw in ("{\"state\": \"maki", "", "[1, 2]", "null", "not json"):
            d = self.folder(raw=raw)
            self.assertEqual(making.state(d), "making", raw)
            got = making.describe(d)
            self.assertTrue(got["making"] and got["broken"], raw)

    def test_a_book_with_no_record_is_an_ordinary_book(self):
        d = self.folder()
        os.unlink(os.path.join(d, "making.json"))
        self.assertEqual(making.state(d), "none")
        self.assertFalse(making.is_making(d))
        got = making.describe(d)
        self.assertEqual({k: v for k, v in got.items() if k != "now"},
                         {"ok": True, "making": False, "state": "none"})

    def test_finished_is_only_what_parseh_wrote(self):
        d = self.folder({"state": "finished", "finished": "2026-09-29T14:20:01Z"})
        self.assertEqual(making.state(d), "finished")
        self.assertFalse(making.describe(d)["making"])
        # an agent's file with no state at all is not a finished book
        self.assertEqual(making.state(self.folder({"stage": "done"})), "making")

    def test_chapters_still_to_come_are_the_table_less_the_chapters_main_tex_inputs(self):
        d = self.folder({"stage": "batch", "chapters": [{"chapter": n, "paragraphs": 4} for n in (1, 2, 3, 4)]})
        for name in ("ch1", "ch1b", "ch2"):
            Path(d, name + ".tex").write_text("% x\n", encoding="utf-8")
        main = Path(d, "main.tex")
        main.write_text(main.read_text(encoding="utf-8").replace(
            "\\end{document}", "\\input{ch1.tex}\n\\input{ch1b}\n\\input{ch2.tex}\n% \\input{ch3.tex}\n"
                              "\\input{ch4.tex}\n\\end{document}"), encoding="utf-8")
        got = making.describe(d)
        self.assertEqual(got["present"], [1, 2])          # ch3 is a comment, ch4 has no file
        self.assertEqual(got["to_come"], [3, 4])
        self.assertEqual(making.chapter_inputs(d), ["ch1", "ch1b", "ch2"])

    def test_parseh_updated_during_the_making_is_said_when_the_versions_differ(self):
        self.assertFalse(making.describe(self.folder())["updated_by_parseh"])
        d = self.folder({"state": "making", "parseh": "a0.1.0"})
        got = making.describe(d)
        self.assertTrue(got["updated_by_parseh"])
        self.assertEqual((got["parseh"], got["parseh_now"]), ("a0.1.0", making.version.VERSION))

    def test_the_time_is_the_agents_and_falls_back_to_the_file(self):
        at = float(calendar.timegm((2026, 9, 29, 14, 20, 1)))
        d = self.folder({"state": "making", "updated": "2026-09-29T14:20:01Z"})
        self.assertEqual(making.describe(d)["updated"], at)
        d = self.folder({"state": "making"})
        self.assertAlmostEqual(making.describe(d)["updated"], time.time(), delta=60)
        self.assertEqual(making._epoch("2026-09-29T16:20:01+02:00"), at)
        self.assertEqual(making._epoch("2026-09-29 12:20"), at - 7201)          # no zone: UTC
        self.assertEqual(making._epoch(int(at)), at)
        self.assertIsNone(making._epoch("yesterday"))
        self.assertIsNone(making._epoch(True))

    def test_the_notes_tail_starts_at_the_start_of_a_line(self):
        d = self.folder()
        Path(d, "NOTES.md").write_text("".join("line %04d of the journal\n" % n for n in range(400)),
                                       encoding="utf-8")
        tail = making.describe(d)["notes"]
        self.assertLessEqual(len(tail), making.NOTES_TAIL)
        self.assertTrue(tail.startswith("line "), tail[:20])
        self.assertTrue(tail.endswith("line 0399 of the journal"))


class Asks(unittest.TestCase):
    def folder(self):
        _into, r = made(self)
        return r["path"]

    def test_a_general_ask_is_one_dated_entry(self):
        d = self.folder()
        got = making.ask(d, "Keep the vocabulary lines short.", when=1790605201)
        self.assertEqual(got["count"], 1)
        text = Path(d, "ASKS.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"^## \d{4}-\d\d-\d\d \d\d:\d\d \u2014 what to change from now on\n\n"
                               r"Keep the vocabulary lines short\.\n$")

    def test_an_ask_about_a_chunk_carries_its_address_and_text(self):
        d = self.folder()
        making.ask(d, "This meaning is too free.\nMake it literal.",
                   {"address": "chapter 1, paragraph 2, subparagraph 2.1, chunk 4",
                    "text": "il gatto\ndorme"})
        text = Path(d, "ASKS.md").read_text(encoding="utf-8")
        self.assertIn("\u2014 about a chunk\n\nchapter 1, paragraph 2, subparagraph 2.1, chunk 4:\n"
                      "> il gatto dorme\n\nThis meaning is too free.\nMake it literal.\n", text)

    def test_entries_are_kept_apart_and_counted(self):
        d = self.folder()
        for n in range(3):
            making.ask(d, "ask number %d" % n)
        text = Path(d, "ASKS.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("\n## "), 2)
        self.assertEqual(making.describe(d)["asks"]["count"], 3)
        self.assertIn("ask number 2", making.describe(d)["asks"]["last"])

    def test_two_devices_asking_together_never_interleave_their_entries(self):
        d = self.folder()
        threads = [threading.Thread(target=making.ask, args=(d, "line %02d" % n + "x" * 500))
                   for n in range(24)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        text = Path(d, "ASKS.md").read_text(encoding="utf-8")
        parts = [p for p in text.split("## ") if p.strip()]
        self.assertEqual(len(parts), 24)
        for part in parts:
            self.assertRegex(part, r"^\d{4}-\d\d-\d\d \d\d:\d\d \u2014 what to change from now on\n\n"
                                   r"line \d\dx{500}\n+$")

    def test_what_cannot_be_written_is_refused_in_words(self):
        d = self.folder()
        with self.assertRaisesRegex(ValueError, "nothing in the box"):
            making.ask(d, "  \n ")
        self.assertEqual(Path(d, "ASKS.md").read_bytes(), b"")
        making._end_making(d)
        with self.assertRaisesRegex(ValueError, "this book is finished"):
            making.ask(d, "too late")
        os.unlink(os.path.join(d, "making.json"))
        with self.assertRaisesRegex(ValueError, "not made by an agent"):
            making.ask(d, "nobody is there")

    def test_control_characters_never_reach_the_file(self):
        d = self.folder()
        making.ask(d, "ok\x00\x07\x1b[31m red\r\nnext")
        text = Path(d, "ASKS.md").read_text(encoding="utf-8")
        self.assertNotRegex(text, "[\x00-\x08\x0b-\x1f]")
        self.assertIn("ok[31m red\nnext", text)


class TheToolsTakeAGrowingBook(unittest.TestCase):
    """lib/books.py, the library, the reader and verify_book take a book with no
    chapter yet, and one whose main.tex grows batch by batch -- with a draft's
    frankdraft.*, an annot/ and an original/ in the folder."""

    def run_tool(self, *args):
        r = subprocess.run([PY] + list(args), capture_output=True, text=True, cwd=str(ROOT))
        return r.returncode, r.stdout + r.stderr

    def test_a_skeleton_with_no_chapter_reads_builds_and_verifies(self):
        into, r = made(self)
        d = r["path"]
        b = booklib.Book(d)
        from texparse import parse_book
        self.assertEqual(parse_book(b.main, b.lang), [])
        code, out = self.run_tool("lib/tex2html.py", "--book", d)
        self.assertEqual(code, 0, out)
        self.assertIn("subparagraphs: 0", out)
        self.assertTrue(os.path.isfile(os.path.join(d, "reader", "index.html")))
        code, out = self.run_tool("lib/verify_book.py", "--book", d)
        self.assertEqual(code, 0, out)
        self.assertIn("0 paragraphs built", out)

    def test_the_library_lists_it_with_a_reader_and_with_none(self):
        into, r = made(self)
        import make_index
        for built in (False, True):
            if built:
                self.run_tool("lib/tex2html.py", "--book", r["path"])
            card = make_index.card(booklib.Book(r["path"]))
            self.assertIn("Il gatto", card)

    def test_the_files_an_agent_leaves_beside_the_book_break_nothing(self):
        into, r = made(self)
        d = r["path"]
        for name, text in (("frankdraft.tex", "% a draft\n"), ("frankdraft.pdf", "%PDF-1.4\n"),
                           ("frankdraft.log", "x"), ("annot/ch1_p00.json", "{}"),
                           ("NOTES.md", "journal"), ("ASKS.md", "## an ask\n")):
            Path(d, name).write_text(text, encoding="utf-8")
        self.assertEqual(self.run_tool("lib/tex2html.py", "--book", d)[0], 0)
        self.assertEqual(self.run_tool("lib/verify_book.py", "--book", d)[0], 0)
        self.assertEqual(self.run_tool("lib/books.py")[0], 0)

    def test_the_draft_is_a_way_of_the_build_job_and_names_the_chapters_it_has(self):
        into, r = made(self)
        d = r["path"]
        for name in ("ch1", "ch1b"):
            Path(d, name + ".tex").write_text("% x\n", encoding="utf-8")
        main = Path(d, "main.tex")
        main.write_text(main.read_text(encoding="utf-8").replace(
            "\\end{document}", "\\input{ch1.tex}\n\\input{ch1b.tex}\n\\end{document}"), encoding="utf-8")
        self.assertEqual(making.chapter_inputs(d), ["ch1", "ch1b"])
        self.assertIn("draft", bookbuild.WAYS)
        with patch.object(bookbuild.shutil, "which", lambda name: "/bin/sh"), \
                patch.object(bookbuild.runtime, "WIN", False), \
                patch.object(bookbuild, "ROOT", os.path.dirname(into)):
            cmd = bookbuild.command(d, "draft", ["ch1", "ch1b"])
            self.assertEqual(cmd[0], "sh")
            self.assertEqual(cmd[2:], ["italian/il-gatto", "--draft", "ch1", "ch1b"])
            got = making.draft_state(d)
        self.assertTrue(got["can"])
        self.assertEqual(got["chapters"], ["ch1", "ch1b"])
        self.assertEqual(got["pdf"], "")

    def test_where_there_is_no_sh_the_draft_says_it_is_not_available_and_the_reader_is(self):
        _into, r = made(self)
        d = r["path"]
        with patch.object(bookbuild.shutil, "which", lambda name: None):
            ok, why = bookbuild.available("draft")
            self.assertFalse(ok)
            self.assertIn("not available here", why)
            self.assertIn("The reader is", why)
            with self.assertRaisesRegex(ValueError, "not available here"):
                bookbuild.start(d, "draft", chapters=["ch1"])
            self.assertFalse(making.draft_state(d)["can"])
        with patch.object(bookbuild.runtime, "WIN", True):
            self.assertFalse(bookbuild.available("draft")[0])
        # the reader and the PDF are not the draft's business
        self.assertEqual(bookbuild.available("html"), (True, ""))

    def test_a_draft_with_no_chapter_is_refused(self):
        _into, r = made(self)
        with patch.object(bookbuild.shutil, "which", lambda name: "/bin/sh"), \
                patch.object(bookbuild.runtime, "WIN", False):
            with self.assertRaisesRegex(ValueError, "no chapter in the book yet"):
                bookbuild.start(r["path"], "draft", chapters=[])
            self.assertIn("no chapter", making.draft_state(r["path"])["why"])

    def test_the_draft_is_older_than_the_batch_after_it(self):
        _into, r = made(self)
        d = r["path"]
        Path(d, "ch1.tex").write_text("% x\n", encoding="utf-8")
        main = Path(d, "main.tex")
        main.write_text(main.read_text(encoding="utf-8").replace(
            "\\end{document}", "\\input{ch1.tex}\n\\end{document}"), encoding="utf-8")
        pdf = Path(d, "frankdraft.pdf")
        pdf.write_bytes(b"%PDF")
        os.utime(pdf, (1000, 1000))
        with patch.object(bookbuild.shutil, "which", lambda name: "/bin/sh"), \
                patch.object(bookbuild.runtime, "WIN", False):
            self.assertTrue(making.draft_state(d)["pdf_old"])
            os.utime(pdf, None)
            self.assertFalse(making.draft_state(d)["pdf_old"])


class Finish(unittest.TestCase):
    """The check and the full build, then the end of the making -- with the two
    subprocesses stood in for by a runner that says what each would say."""

    OK_VERIFY = "\nitalian/il-gatto [Italian]: 2 paragraphs built, 2 reproduce their source exactly, 0 mismatched, 0 without a source\n"

    def folder(self):
        _into, r = made(self)
        return r["path"]

    def run_finish(self, d, verify, build, no_tex=False):
        """-> the finished job's view.  `verify` = (exit code, output); `build` = (exit code, lines)."""
        seen = []

        def runner(cmd, say):
            seen.append(cmd)
            name = os.path.basename(cmd[1]) if len(cmd) > 1 else ""
            if name == "verify_book.py":
                for line in verify[1].splitlines():
                    say(line)
                return verify[0]
            for line in build[1]:
                say(line)
            return build[0]
        with patch.object(making.shutil, "which", lambda name: None if no_tex else "/usr/bin/" + name):
            with patch.object(making.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0)):
                view, started = making.finish_start(d, runner=runner, wait=0.01)
                self.assertTrue(started)
                for _ in range(500):
                    job = making.finish_status(d)
                    if job["state"] != "running":
                        break
                    time.sleep(0.02)
        return job, seen

    def test_both_clean_ends_the_making(self):
        d = self.folder()
        job, seen = self.run_finish(d, (0, self.OK_VERIFY), (0, ["   pdf: 0 overfull boxes, 3 pages"]))
        self.assertEqual((job["state"], job["ok"]), ("done", True))
        self.assertEqual([s["state"] for s in job["steps"]], ["done", "done"])
        self.assertIn("every paragraph reproduces its source (2 paragraphs)", job["steps"][0]["said"])
        self.assertEqual(job["steps"][1]["said"], "the PDF and the reader were built")
        self.assertEqual(making.state(d), "finished")
        doc = json.loads(Path(d, "making.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["finished"] and doc["stage"] == "folder")
        # the running agent is told, in the file it reads before every batch
        self.assertIn("\u2014 finished\n\nThe person finished this book from Parseh. Stop:",
                      Path(d, "ASKS.md").read_text(encoding="utf-8"))
        # the check ran first, on this book, with the environment's Python
        self.assertEqual(os.path.basename(seen[0][1]), "verify_book.py")
        self.assertEqual(seen[0][2:], ["--book", d])

    def test_a_paragraph_that_no_longer_reproduces_its_source_stops_it_and_says_which(self):
        d = self.folder()
        out = ("  MISMATCH chapter 2 paragraph 3 at char 41 of 120\n     built : ...x...\n     source: ...y...\n"
               "  NO SOURCE for chapter 2 paragraph 4 (ch2_p03.txt)\n\n"
               "italian/il-gatto [Italian]: 5 paragraphs built, 3 reproduce their source exactly, 1 mismatched, 1 without a source\n")
        job, _seen = self.run_finish(d, (1, out), (0, []))
        self.assertEqual((job["state"], job["ok"]), ("failed", False))
        first = job["steps"][0]
        self.assertEqual(first["state"], "failed")
        self.assertEqual(first["said"], "2 paragraphs do not reproduce their source")
        self.assertEqual(first["lines"], [
            "chapter 2 paragraph 3 does not reproduce its source (it differs at character 41)",
            "chapter 2 paragraph 4 has no source file in source/paras/"])
        self.assertEqual(job["steps"][1]["state"], "skipped")
        self.assertEqual(making.state(d), "making")
        self.assertIn("still being made", job["said"])

    def test_a_book_with_no_chapter_is_not_finished(self):
        d = self.folder()
        out = "\nitalian/il-gatto [Italian]: 0 paragraphs built, 0 reproduce their source exactly, 0 mismatched, 0 without a source\n"
        job, _seen = self.run_finish(d, (0, out), (0, []))
        self.assertEqual(job["state"], "failed")
        self.assertIn("no chapter in the book yet", job["steps"][0]["said"])
        self.assertEqual(making.state(d), "making")

    def test_a_build_that_fails_says_texs_first_error_and_leaves_the_making_on(self):
        d = self.folder()
        job, _seen = self.run_finish(d, (0, self.OK_VERIFY), (1, [
            "== il-gatto", "   PDF FAILED -- first error from main.log:", "! Undefined control sequence.",
            "at least one PDF did not build; its reader was written, see above"]))
        self.assertEqual((job["state"], job["steps"][1]["state"]), ("failed", "failed"))
        self.assertEqual(job["steps"][1]["said"],
                         "the build failed: PDF FAILED: ! Undefined control sequence.")
        self.assertEqual(making.state(d), "making")

    def test_with_no_tex_the_reader_alone_is_built_and_the_pdf_is_said_to_be_left(self):
        d = self.folder()
        job, seen = self.run_finish(d, (0, self.OK_VERIFY), (0, ["the reader"]), no_tex=True)
        self.assertEqual(job["state"], "done")
        self.assertIn("the PDF was left, because TeX is not installed", job["steps"][1]["said"])
        self.assertTrue(any("--html" in c or "html" in c for c in [" ".join(map(str, s)) for s in seen[1:]]),
                        seen)
        self.assertEqual(making.state(d), "finished")

    def test_a_second_press_while_it_runs_follows_the_same_job(self):
        d = self.folder()
        gate = threading.Event()

        def runner(cmd, say):
            gate.wait(5)
            for line in self.OK_VERIFY.splitlines():
                say(line)
            return 0
        with patch.object(making.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0)):
            first, started = making.finish_start(d, runner=runner, wait=0.01)
            again, started2 = making.finish_start(d, runner=runner, wait=0.01)
            self.assertEqual((started, started2), (True, False))
            gate.set()
            for _ in range(500):
                if making.finish_status(d)["state"] != "running":
                    break
                time.sleep(0.02)

    def test_a_book_that_is_not_being_made_cannot_be_finished(self):
        d = self.folder()
        os.unlink(os.path.join(d, "making.json"))
        with self.assertRaisesRegex(ValueError, "not being made"):
            making.finish_start(d)
        Path(d, "making.json").write_text('{"state": "finished"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "finished already"):
            making.finish_start(d)

    def test_verify_words_reads_the_tools_own_lines(self):
        ok, said, lines = making.verify_words(0, self.OK_VERIFY)
        self.assertEqual((ok, said, lines), (True, "every paragraph reproduces its source (2 paragraphs)", []))
        ok, said, _ = making.verify_words(2, "Traceback: nothing")
        self.assertFalse(ok)
        self.assertIn("could not run", said)


class TheBundle(unittest.TestCase):
    """What a finished book carries in its download and its backup (brief 5.9): its
    original and annot/ beside what it carried before, and never the agent's own files."""

    AGENTS_OWN = ("AGENTS.md", "CLAUDE.md", "ASKS.md", "making.json", ".claude/settings.json",
                  ".claude/skills/parseh-book/SKILL.md", "frankdraft.tex", "frankdraft.pdf",
                  "frankdraft.log", "main.pdf", "main.aux")

    def book(self, original=None):
        _into, r = made(self, original=original)
        d = Path(r["path"])
        (d / "annot").mkdir(exist_ok=True)
        (d / "annot" / "ch1_p00.json").write_text('{"idx": 0, "ch": 1, "ann": {"sentences": []}}',
                                                  encoding="utf-8")
        for name in self.AGENTS_OWN[4:]:
            (d / name).parent.mkdir(parents=True, exist_ok=True)
            (d / name).write_text("x", encoding="utf-8")
        return d

    def names(self, data):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return {n.split("/", 1)[1] for n in z.namelist() if "/" in n and not n.endswith("/")}, \
                json.loads(z.read("parseh-bundle.json"))

    def test_the_download_carries_the_original_and_annot_and_none_of_the_agents_files(self):
        d = self.book()
        data, _name = bundle.pack_book(str(d))
        got, man = self.names(data)
        for want in ("book.json", "main.tex", "NOTES.md", "original/Il-Gatto.txt", "annot/ch1_p00.json"):
            self.assertIn(want, got)
        for never in self.AGENTS_OWN:
            self.assertNotIn(never, got, never)
        self.assertEqual(man["format"], "parseh-bundle/3", "raised: going back past a0.4.2 says so first")
        # and every shape carries them, because they are the book's own record
        for mode in bundle.MODES:
            self.assertIn("annot/ch1_p00.json", self.names(bundle.pack_book(str(d), audio=mode)[0])[0], mode)

    def test_the_backup_of_the_shelf_carries_them_too(self):
        d = self.book()
        import shelf
        path, _name = shelf.pack("book", root=str(d.parents[2]))
        self.addCleanup(os.unlink, path)
        with zipfile.ZipFile(path) as z:
            inner = [n for n in z.namelist() if n.endswith(".zip")]
            self.assertEqual(len(inner), 1)
            got, man = self.names(z.read(inner[0]))
        self.assertIn("original/Il-Gatto.txt", got)
        self.assertIn("annot/ch1_p00.json", got)
        self.assertNotIn("making.json", got)

    def test_it_comes_back_as_an_ordinary_book_with_its_record_and_its_source(self):
        d = self.book()
        data, _ = bundle.pack_book(str(d))
        root = tmpdir(self)
        done = bundle.install(data, root=root)
        got = Path(root, done["dir"])
        self.assertEqual((got / "original" / "Il-Gatto.txt").read_bytes(), TEXT)
        self.assertTrue((got / "annot" / "ch1_p00.json").is_file())
        for never in ("AGENTS.md", "CLAUDE.md", "ASKS.md", "making.json", ".claude"):
            self.assertFalse((got / never).exists(), never)
        # an ordinary book: nothing says it is being made, so the reader's doors edit it
        self.assertEqual(making.state(str(got)), "none")

    def test_an_older_or_hand_made_bundle_over_a_book_does_not_take_its_record_away(self):
        d = self.book()
        data, _ = bundle.pack_book(str(d))
        root = tmpdir(self)
        first = bundle.install(data, root=root)
        dest = Path(root, first["dir"])
        # the bundle a0.4.1 would have made: the same book without annot/ and original/
        with zipfile.ZipFile(io.BytesIO(data)) as z, io.BytesIO() as out:
            with zipfile.ZipFile(out, "w") as w:
                for n in z.namelist():
                    if "/annot/" not in n and "/original/" not in n:
                        w.writestr(n, z.read(n))
            older = out.getvalue()
        self.assertNotIn("annot", self.names(older)[0])
        done = bundle.install(older, replace=True, root=root)
        self.assertTrue((dest / "annot" / "ch1_p00.json").is_file(), "the record was kept")
        self.assertTrue((dest / "original" / "Il-Gatto.txt").is_file(), "and so was the source")
        self.assertIn("annot", done["kept"])
        # a bundle that carries its own replaces them
        (dest / "annot" / "ch1_p00.json").write_text("{}", encoding="utf-8")
        bundle.install(data, replace=True, root=root)
        self.assertIn("ann", (dest / "annot" / "ch1_p00.json").read_text(encoding="utf-8"))

    def test_the_original_is_stored_counted_as_no_recording_and_has_no_text_budget(self):
        d = self.book(original={"name": "big.pdf", "data": PDF + os.urandom(20000)})
        data, _ = bundle.pack_book(str(d))
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            info = z.getinfo("%s/original/big.pdf" % d.name)
            self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
        said = bundle.payload("book", str(d), "linked")
        self.assertEqual((said["media"], said["media_bytes"]), (0, 0), "an original is no recording")
        self.assertLess(abs(len(data) - said["bytes"]), 0.01 * len(data) + 64)
        # a text budget of 5 kB refuses 5 kB of source/ text and takes a 20 kB original whole
        with mock.patch.object(bundle, "MAX_UNPACKED", 5000):
            root = tmpdir(self)
            self.assertEqual(bundle.install(data, root=root)["ok"], True)
            bad = io.BytesIO()
            with zipfile.ZipFile(bad, "w") as z:
                z.writestr("parseh-bundle.json", json.dumps({
                    "format": bundle.FORMAT, "kind": "book", "language": "it", "gloss": "en", "slug": "x"}))
                z.writestr("x/book.json", json.dumps({"slug": "x", "language": "it", "main": "main.tex"}))
                z.writestr("x/main.tex", "\\end{document}\n")
                z.writestr("x/source/paras/ch1_p00.txt", "a" * 6000)
            with self.assertRaisesRegex(bundle.BundleError, "of text"):
                bundle.install(bad.getvalue(), root=tmpdir(self))

    def test_a_hand_made_bundle_cannot_put_a_page_or_a_script_in_either(self):
        d = self.book()
        data, _ = bundle.pack_book(str(d))
        out = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(data)) as z, zipfile.ZipFile(out, "w") as w:
            for n in z.namelist():
                w.writestr(n, z.read(n))
            for extra in ("original/page.html", "annot/page.html", "original/evil.svg", "annot/x.js",
                          "original/.hidden.txt/x", "AGENTS.md", ".claude/skills/x/SKILL.md"):
                w.writestr("%s/%s" % (d.name, extra), "<script>alert(1)</script>")
        root = tmpdir(self)
        what = bundle.inspect(out.getvalue(), root=root)
        for extra in ("original/page.html", "annot/page.html", "original/evil.svg", "annot/x.js",
                      "AGENTS.md", ".claude/skills/x/SKILL.md"):
            self.assertIn(extra, what["dropped"], extra)
        self.assertNotIn("original/page.html", what["files"])
        done = bundle.install(out.getvalue(), root=root)
        got = Path(root, done["dir"])
        for extra in ("original/page.html", "annot/page.html", "original/evil.svg", "annot/x.js",
                      "AGENTS.md", ".claude"):
            self.assertFalse((got / extra).exists(), extra)

    def test_the_originals_kinds_are_the_tools_own_in_both_places(self):
        self.assertEqual(bundle.ORIGINAL_EXTS, making.ORIGINAL_EXTS)
        self.assertEqual(bundle.SHAPE["book"]["dirs"]["original"], making.ORIGINAL_EXTS)
        self.assertEqual(bundle.SHAPE["book"]["dirs"]["annot"], (".json",))

    def test_a_book_from_before_a0_4_2_packs_to_the_same_files_as_it_did(self):
        # a fixture book has no annot/ and no original/: nothing is added, nothing goes missing
        book = tmpdir(self) + "/books/english/mini-en"
        shutil.copytree(ROOT / "tests" / "fixtures" / "books" / "english" / "mini-en", book,
                        ignore=shutil.ignore_patterns("reader"))
        got, man = self.names(bundle.pack_book(book)[0])
        self.assertFalse([n for n in got if n.startswith(("annot/", "original/"))])
        self.assertIn("ch1.tex", got)
        self.assertEqual(man["format"], bundle.FORMAT)


class OpeningTheFolder(unittest.TestCase):
    def test_the_program_is_the_systems_and_never_waited_for(self):
        d = tmpdir(self)
        calls = []
        with patch.object(making.subprocess, "Popen", lambda cmd, **kw: calls.append((cmd, kw))):
            self.assertIsNone(making.open_folder(d))
        cmd, kw = calls[0]
        self.assertEqual(cmd[-1], d)
        self.assertIn(os.path.basename(cmd[0]), ("xdg-open", "open", "explorer"))
        self.assertEqual(kw["stdout"], subprocess.DEVNULL)

    def test_a_missing_file_manager_or_folder_is_said_in_words(self):
        d = tmpdir(self)

        def gone(*a, **k):
            raise FileNotFoundError(2, "No such file or directory")
        with patch.object(making.subprocess, "Popen", gone):
            self.assertIn("open the folder from the path above", making.open_folder(d))
        self.assertEqual(making.open_folder(os.path.join(d, "nowhere")), "the folder is not there any more")

    def test_each_platform_has_its_own_program(self):
        with patch.object(making.os, "name", "nt"):
            self.assertEqual(making.open_program("C:\\b")[0], "explorer")
        with patch.object(making.os, "name", "posix"), patch.object(making.sys, "platform", "darwin"):
            self.assertEqual(making.open_program("/b")[0], "open")
        with patch.object(making.os, "name", "posix"), patch.object(making.sys, "platform", "linux"):
            self.assertTrue(making.open_program("/b")[0].endswith("xdg-open"))


if __name__ == "__main__":
    unittest.main()
