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
        # REAL BOOKS, in the places a reference must not reach: beside the shelf, in its trash, three deep.
        # A path that names nothing is refused whatever the rules are; these are refused by them.
        into = self.shelf_with((".trash", "il-gatto-old", "it", {}))
        outside = Path(into).parent / "outside"
        outside.mkdir()
        (outside / "book.json").write_text('{"slug": "outside", "language": "it", "title": "x"}', encoding="utf-8")
        deep = Path(into, "italian", "a", "b")
        deep.mkdir(parents=True)
        (deep / "book.json").write_text('{"slug": "b", "language": "it", "title": "x"}', encoding="utf-8")
        for bad in ("../outside", "italian/../../outside", str(outside), ".trash/il-gatto-old", "italian/a/b",
                    "../etc", "/etc"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "is not a book on the shelf|no book called"):
                    making.make(FIELDS, {"name": "a.txt", "data": TEXT}, {"reference": bad}, into=into)
        for bad in ("../outside", ".trash/il-gatto-old", "italian/a/b"):
            with self.subTest(refused_as_a_path=bad):
                with self.assertRaisesRegex(ValueError, "is not a book on the shelf"):
                    making._shelf_book(bad, into)

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

    def test_the_words_step_is_told_to_the_languages_that_divide_a_chunk_into_words_and_to_no_other(self):
        # the step the page's old recipe carried in its prompt (docs/new-book-prompt.md's WORDS_STEP):
        # the machine starts the words, the annotator corrects them
        import languages
        with_words = []
        for code in languages.CODES:
            with self.subTest(code=code):
                text = making.instructions_for({"lang": code, "gloss": "en", "title": "x", "title_latin": "x"},
                                               None, into=tmpdir(self))
                if languages.get(code).words:
                    with_words.append(code)
                    self.assertIn("fill_words.py --lang %s --json" % code, text)
                    self.assertIn("`## Words`", text)
                else:
                    self.assertNotIn("fill_words", text)
        self.assertLessEqual({"ja", "zh"}, set(with_words))

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
        d = self.folder({"stage": "batch", "chapters": [{"chapter": n, "paragraphs": 4} for n in (1, 2, 3, 4, 5, 6)]})
        # ch3 and ch5 are on the disk, so that only the rule about comments and about lines keeps them out
        for name in ("ch1", "ch1b", "ch2", "ch3", "ch5", "preamble"):
            Path(d, name + ".tex").write_text("% x\n", encoding="utf-8")
        main = Path(d, "main.tex")
        main.write_text(main.read_text(encoding="utf-8").replace(
            "\\end{document}", "\\input{ch1.tex}\n\\input{ch1b}\n\\input{ch2.tex}\n% \\input{ch3.tex}\n"
                              "\\input{ch4.tex}\n   %\\input{ch5.tex}\n\\input{preamble}\n\\end{document}"),
            encoding="utf-8")
        got = making.describe(d)
        self.assertEqual(got["present"], [1, 2])          # ch3 and ch5 are comments, ch4 has no file, preamble is no chapter
        self.assertEqual(got["to_come"], [3, 4, 5, 6])
        self.assertEqual(making.chapter_inputs(d), ["ch1", "ch1b", "ch2"])

    def test_a_reader_older_than_what_the_agent_wrote_is_said_to_be_behind(self):
        # by the files' own times: the page the person looks at is the reader's, and a
        # batch that landed after it was built is not in it
        d = self.folder({"stage": "batch"})
        main = Path(d, "main.tex")
        main.write_text(main.read_text(encoding="utf-8").replace(
            "\\end{document}", "\\input{ch1.tex}\n\\end{document}"), encoding="utf-8")
        ch1 = Path(d, "ch1.tex")
        ch1.write_text("% x\n", encoding="utf-8")
        now = time.time()

        def age(path, seconds_ago):
            os.utime(path, (now - seconds_ago, now - seconds_ago))
        for p in (main, ch1):
            age(p, 100)
        self.assertTrue(making.describe(d)["stale"], "no reader at all is behind everything written")
        reader = Path(d, "reader", "index.html")
        reader.parent.mkdir()
        reader.write_text("<html></html>", encoding="utf-8")
        age(reader, 50)
        self.assertFalse(making.describe(d)["stale"], "a reader built after the last write is not behind")
        age(ch1, 10)
        self.assertTrue(making.describe(d)["stale"], "a batch written after the reader was built is")
        age(reader, 5)
        self.assertFalse(making.describe(d)["stale"])

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

    def test_the_same_road_in_every_language_of_the_registry(self):
        # the make route builds the reader the moment the folder is made: a language whose
        # skeleton had no reader with no chapter would fail there, in front of the person
        import languages
        for code in languages.CODES:
            with self.subTest(code=code):
                into = os.path.join(tmpdir(self), "books")
                os.makedirs(into)
                r = making.make({"lang": code, "gloss": "en", "title": "Book " + code, "title_latin": "Book " + code},
                                {"name": "a.txt", "data": TEXT}, into=into)
                d = r["path"]
                code_, out = self.run_tool("lib/tex2html.py", "--book", d)
                self.assertEqual(code_, 0, out)
                self.assertTrue(os.path.isfile(os.path.join(d, "reader", "index.html")))
                code_, out = self.run_tool("lib/verify_book.py", "--book", d)
                self.assertEqual(code_, 0, out)
                self.assertEqual(making.describe(d)["words"], "not started yet")
                self.assertIn(languages.get(code).name, Path(d, "AGENTS.md").read_text(encoding="utf-8"))

    def test_a_book_grows_batch_by_batch_in_every_language_of_the_registry(self):
        # the scripted stand-in (tests/making_agent.py) does what an agent is told to do, by calling
        # Parseh's own tools: at every rest point the book must read, and at the end it must verify
        import languages
        for code in languages.CODES:
            with self.subTest(code=code):
                L = languages.get(code)
                model = os.path.join(str(ROOT), "tests", "fixtures", "books", L.folder, "mini-" + code)
                original = os.path.join(tmpdir(self), "original.txt")
                self.assertEqual(self.run_tool("tests/making_agent.py", "original", model, original)[0], 0)
                into = os.path.join(tmpdir(self), "books")
                os.makedirs(into)
                r = making.make({"lang": code, "gloss": "en", "title": "Book " + code, "title_latin": "Book " + code},
                                {"name": "original.txt", "path": original}, into=into)
                d, seen = r["path"], []
                for _ in range(5):
                    got, out = self.run_tool("tests/making_agent.py", "step", d, model)
                    self.assertEqual(got, 0, out)
                    seen.append(making.describe(d)["words"])
                    got, out = self.run_tool("lib/tex2html.py", "--book", d)
                    self.assertEqual(got, 0, "the reader must build at every rest point: " + out)
                # the folder starts as "more text may come later": every part is in and the agent waits for the next
                self.assertEqual(seen, ["source recovered", "chapter table", "batch 2 of 2", "all batches in", "waiting for the next part"])
                self.assertNotIn("subparagraphs: 0", out, "the reader of the whole book has its chunks")
                self.assertEqual(making.describe(d)["to_come"], [])
                # and once the person says this is all the text, the same agent ends
                making.set_more_coming(d, False)
                got, out2 = self.run_tool("tests/making_agent.py", "step", d, model)
                self.assertEqual(got, 0, out2)
                self.assertEqual(making.describe(d)["words"], "all batches in")
                self.assertEqual(making.finish_blockers(d), [], "every part taken, the agent idle: nothing to wait for")
                got, out = self.run_tool("lib/verify_book.py", "--book", d)
                self.assertEqual(got, 0, out)
                self.assertIn("2 reproduce their source exactly", out)

    def test_the_library_lists_it_with_a_reader_and_with_none(self):
        into, r = made(self)
        import make_index
        for built in (False, True):
            if built:
                self.run_tool("lib/tex2html.py", "--book", r["path"])
            card = make_index.card(booklib.Book(r["path"]))
            self.assertIn("Il gatto", card)

    def test_the_card_of_a_book_being_made_says_where_the_making_stands_and_only_then(self):
        into, r = made(self)
        d = r["path"]
        import make_index
        patcher = patch.object(booklib, "BOOKS_DIR", into)          # the card's address is relative to the shelf
        patcher.start()
        self.addCleanup(patcher.stop)
        card = make_index.card(booklib.Book(d))
        self.assertIn('data-making="italian/il-gatto"', card)
        self.assertIn("being made &middot; not started yet", card)
        Path(d, "making.json").write_text(json.dumps({"state": "making", "stage": "batch",
                                                      "batches": {"done": 1, "of": 6}}), encoding="utf-8")
        self.assertIn("being made &middot; batch 2 of 6", make_index.card(booklib.Book(d)))
        # a half-written record is still a book being made, and the card says so
        Path(d, "making.json").write_text('{"state": "maki', encoding="utf-8")
        self.assertIn('data-making="italian/il-gatto"', make_index.card(booklib.Book(d)))
        # the making over, or a book nobody made this way: nothing on the card says it
        Path(d, "making.json").write_text(json.dumps({"state": "finished"}), encoding="utf-8")
        self.assertNotIn("data-making", make_index.card(booklib.Book(d)))
        os.unlink(os.path.join(d, "making.json"))
        self.assertNotIn("being made", make_index.card(booklib.Book(d)))

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
            self.assertIn("not available on this computer", why)
            self.assertIn("The reader is available", why)
            with self.assertRaisesRegex(ValueError, "not available on this computer"):
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


def record(d):
    return json.loads(Path(d, "making.json").read_text(encoding="utf-8"))


def agent_writes(d, **fields):
    """What an agent does to making.json: reads it, changes its own fields, writes it whole."""
    doc = record(d)
    doc.update(fields)
    Path(d, "making.json").write_text(json.dumps(doc), encoding="utf-8")


class TheTextInParts(unittest.TestCase):
    """The text a bit at a time (brief 5.10): the original is part 1, every later part is sent or pasted,
    written whole and listed, and the list is Parseh's to write -- the agent's own record is `sources`."""

    def folder(self, **fields):
        _into, r = made(self, fields)
        return r["path"]

    def test_the_original_is_part_one_and_more_text_is_expected_unless_the_page_says_it_is_all(self):
        d = self.folder()
        doc = record(d)
        self.assertEqual(doc["more_coming"], True)
        self.assertEqual(len(doc["parts"]), 1)
        first = doc["parts"][0]
        self.assertEqual((first["n"], first["file"], first["chapter"], first["join"], first["bytes"]),
                         (1, "original/Il-Gatto.txt", "new", "", len(TEXT)))
        self.assertTrue(making._epoch(first["added"]))
        # Parseh's own copy, in original/ where the agent is not told to write
        self.assertEqual(json.loads(Path(d, "original", "parts.json").read_text(encoding="utf-8"))["parts"], doc["parts"])
        _into, r = made(self, options={"more_coming": False})
        self.assertEqual(record(r["path"])["more_coming"], False)

    def test_a_part_from_a_file_is_written_whole_numbered_and_listed(self):
        d = self.folder()
        got = making.add_part(d, {"name": "Chapter Two!.txt", "data": TEXT}, {"label": "the second book", "chapter": "last"})
        self.assertEqual((got["n"], got["file"], got["chapter"], got["label"]), (2, "original/part-002-Chapter-Two.txt", "last", "the second book"))
        self.assertEqual(Path(d, got["file"]).read_bytes(), TEXT)
        # a spooled upload is copied, not read into memory, and what the caller spooled is left to it
        spool = os.path.join(tmpdir(self), "spool")
        Path(spool).write_bytes(PDF)
        third = making.add_part(d, {"name": "big.pdf", "path": spool}, {"pages": "2-5"})
        self.assertEqual((third["n"], third["pages"], third["chapter"], third["bytes"]), (3, [2, 5], "auto", len(PDF)))
        self.assertTrue(os.path.exists(spool))
        doc = record(d)
        self.assertEqual([p["n"] for p in doc["parts"]], [1, 2, 3], "the list is complete, from the first original on")
        self.assertEqual(sorted(os.listdir(os.path.join(d, "original"))),
                         ["Il-Gatto.txt", "part-002-Chapter-Two.txt", "part-003-big.pdf", "parts.json"], "no .part left behind")
        # the file that is read before every batch says so, whatever the agent does with making.json
        asks = Path(d, "ASKS.md").read_text(encoding="utf-8")
        self.assertIn("a part was added", asks)
        self.assertIn("original/part-002-Chapter-Two.txt", asks)
        self.assertEqual(making.describe(d)["asks"], {"count": 0, "last": ""}, "what Parseh writes there is no ask of the person's")
        making.ask(d, "shorter glosses")
        self.assertEqual(making.describe(d)["asks"]["count"], 1)

    def test_pasted_text_is_a_part_named_from_its_label(self):
        d = self.folder()
        got = making.add_part(d, {"text": "  Il gatto torna.\r\n\r\nE dorme.\x00 "}, {"label": "last page"})
        self.assertEqual((got["file"], got["pages"]), ("original/part-002-last-page.txt", None))
        self.assertEqual(Path(d, got["file"]).read_text(encoding="utf-8"), "Il gatto torna.\n\nE dorme.")
        self.assertEqual(making.add_part(d, {"text": "Ancora."})["file"], "original/part-003-pasted.txt")

    def test_a_part_that_is_refused_is_refused_in_the_words_of_the_first_original_and_writes_nothing(self):
        d = self.folder()
        before = (sorted(os.listdir(os.path.join(d, "original"))), record(d)["parts"], (Path(d) / "ASKS.md").read_bytes())
        for source, options, said in (
                ({"name": "a.txt", "data": b""}, None, "the original is empty"),
                ({"name": "a.pdf", "data": TEXT}, None, "does not look like a PDF"),
                ({"name": "a.epub", "data": TEXT[:0] + b"not a zip"}, None, "does not look like an epub"),
                ({"name": "a.docx", "data": TEXT}, None, "has to be a PDF with a text layer"),
                ({"name": "a.txt", "data": b"x\x00y"}, None, "does not look like a text file"),
                ({"name": "a.pdf", "data": PDF}, {"pages": "9-2"}, "the first not after the last"),
                ({"text": "   "}, None, "the text is empty"),
                ({"text": "x"}, {"chapter": "middle"}, "no such place for a part"),
                ({"text": "x"}, {"join": "line"}, "joined to the paragraph before"),
                ({"text": "x"}, {"chapter": "new", "join": "paragraph"}, "cannot start a new chapter")):
            with self.assertRaisesRegex(ValueError, said):
                making.add_part(d, source, options)
        after = (sorted(os.listdir(os.path.join(d, "original"))), record(d)["parts"], (Path(d) / "ASKS.md").read_bytes())
        self.assertEqual(after, before)

    def test_a_disk_that_fills_leaves_the_folder_as_it_was(self):
        d = self.folder()
        before = sorted(os.listdir(os.path.join(d, "original")))
        with patch.object(making.os, "replace", side_effect=OSError(28, "No space left on device")):
            with self.assertRaisesRegex(ValueError, "nothing was changed"):
                making.add_part(d, {"name": "a.txt", "data": TEXT})
        self.assertEqual(sorted(os.listdir(os.path.join(d, "original"))), before)
        self.assertEqual(len(record(d)["parts"]), 1)

    def test_a_finished_book_or_one_nobody_made_this_way_takes_no_part_and_a_reopened_one_does(self):
        d = self.folder()
        making._end_making(d)
        with self.assertRaisesRegex(ValueError, "reopen the making"):
            making.add_part(d, {"text": "x"})
        with self.assertRaisesRegex(ValueError, "reopen the making first"):
            making.set_more_coming(d, False)
        making.reopen(d)
        self.assertEqual(making.add_part(d, {"text": "x"})["n"], 2)
        os.unlink(os.path.join(d, "making.json"))
        with self.assertRaisesRegex(ValueError, "not made by an agent"):
            making.add_part(d, {"text": "x"})

    def test_numbering_goes_past_a_file_the_list_lost_and_two_devices_get_two_numbers(self):
        d = self.folder()
        Path(d, "original", "part-004-lost.txt").write_bytes(b"x")
        self.assertEqual(making.add_part(d, {"text": "x"})["n"], 5)
        got = []

        def add():
            got.append(making.add_part(d, {"text": "again"})["n"])
        threads = [threading.Thread(target=add) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(got), list(range(6, 14)))
        self.assertEqual([p["n"] for p in record(d)["parts"]], [1, 5] + list(range(6, 14)))

    def test_an_agent_that_writes_making_json_whole_from_what_it_read_cannot_lose_a_part(self):
        d = self.folder()
        stale = record(d)
        making.add_part(d, {"text": "Ancora."}, {"chapter": "new"})
        making.set_more_coming(d, False)
        # the agent writes its own fields from the file as it read it a while ago
        Path(d, "making.json").write_text(json.dumps(dict(stale, stage="batch", on="batch 3")), encoding="utf-8")
        self.assertEqual([p["n"] for p in record(d)["parts"]], [1], "what the agent wrote is what is there ...")
        got = making.describe(d)                       # ... until Parseh looks, which puts its own list back
        self.assertEqual([p["n"] for p in got["parts"]], [1, 2])
        doc = record(d)
        self.assertEqual(([p["n"] for p in doc["parts"]], doc["more_coming"], doc["stage"]), ([1, 2], False, "batch"),
                         "the agent's fields are the agent's, and Parseh's are put back")
        # a file the agent is half way through writing is left alone, to be put right at the next look
        Path(d, "making.json").write_text('{"stage": "ba', encoding="utf-8")
        making.describe(d)
        self.assertEqual(Path(d, "making.json").read_text(encoding="utf-8"), '{"stage": "ba')

    def test_where_each_part_stands_is_the_agents_word_and_its_chapter_table(self):
        d = self.folder()
        making.add_part(d, {"text": "due"}, {"label": "two"})
        making.add_part(d, {"text": "tre"}, {"chapter": "last", "join": "paragraph"})
        for name in ("ch1", "ch2"):
            Path(d, name + ".tex").write_text("% x\n", encoding="utf-8")
        main = Path(d, "main.tex")
        main.write_text(main.read_text(encoding="utf-8").replace("\\end{document}", "\\input{ch1.tex}\n\\input{ch2.tex}\n\\end{document}"),
                        encoding="utf-8")
        agent_writes(d, sources={"done": [1, 2], "of": 3, "decided": {"2": "a new chapter: it opens with a heading"}},
                     chapters=[{"chapter": 1, "paragraphs": 3, "part": 1}, {"chapter": 2, "paragraphs": 2, "part": 2},
                               {"chapter": 3, "paragraphs": 1, "part": 3}])
        parts = making.describe(d)["parts"]
        self.assertEqual([(p["n"], p["state"]) for p in parts], [(1, "worked"), (2, "worked"), (3, "added")])
        self.assertEqual(parts[1]["decided"], "a new chapter: it opens with a heading")
        self.assertEqual((parts[1]["label"], parts[2]["chapter"], parts[2]["join"]), ("two", "last", "paragraph"))
        agent_writes(d, sources={"done": [1, 2, 3]}, chapters=[])
        self.assertEqual([p["state"] for p in making.describe(d)["parts"]], ["recovered"] * 3,
                         "taken by the agent, and no chapter of its table says which part it came from")
        agent_writes(d, sources="every part", chapters=None)          # an agent's wrong shape reads as nothing taken
        self.assertEqual([p["state"] for p in making.describe(d)["parts"]], ["added"] * 3)

    def test_a_book_made_before_parts_gets_its_list_when_the_first_part_is_added(self):
        d = self.folder()
        doc = record(d)
        doc.pop("parts"), doc.pop("more_coming")
        Path(d, "making.json").write_text(json.dumps(doc), encoding="utf-8")
        os.unlink(os.path.join(d, "original", "parts.json"))
        self.assertEqual(making.describe(d)["parts"], [], "nothing to list, and nothing to wait for")
        self.assertEqual(making.finish_blockers(d), ["the agent has not said it is done: its record says "
                                                     "\"not started yet\", and what it writes next is lost once the book is finished"])
        self.assertEqual(making.add_part(d, {"text": "x"})["n"], 2)
        self.assertEqual([p["n"] for p in record(d)["parts"]], [1, 2], "the original it was made from is part 1")
        self.assertEqual(record(d)["parts"][0]["file"], "original/Il-Gatto.txt")

    def test_this_is_all_the_text_and_more_is_coming_are_the_persons_to_say_and_to_take_back(self):
        d = self.folder()
        self.assertEqual(making.set_more_coming(d, False), False)
        self.assertEqual((record(d)["more_coming"], making.describe(d)["more_coming"]), (False, False))
        self.assertIn("this is all the text", Path(d, "ASKS.md").read_text(encoding="utf-8"))
        self.assertEqual(making.set_more_coming(d, True), True)
        self.assertEqual(record(d)["more_coming"], True)
        asks = Path(d, "ASKS.md").read_text(encoding="utf-8")
        self.assertIn("more text is coming", asks)
        making.set_more_coming(d, True)
        self.assertEqual(Path(d, "ASKS.md").read_text(encoding="utf-8"), asks, "no entry for what did not change")

    def test_the_stage_words_know_the_agent_is_waiting_for_the_next_part(self):
        self.assertEqual(making.stage_words({"stage": "waiting"}), "waiting for the next part")

    def test_a_sent_file_is_recovered_as_blank_line_paragraphs_for_the_add_page(self):
        got = making.recovered_text({"name": "a.txt", "data": b"Il gatto\ndorme.\n\nIl cane corre.\n"}, "it")
        self.assertEqual(got, "Il gatto dorme.\n\nIl cane corre.")
        spool = os.path.join(tmpdir(self), "parseh-upload-xyz.zip")          # what a server spools a big body as
        Path(spool).write_bytes(b"Uno.\nDue.\n")
        self.assertEqual(making.recovered_text({"name": "b.txt", "path": spool}, "it"), "Uno.\n\nDue.")
        with self.assertRaisesRegex(ValueError, "the original is empty"):
            making.recovered_text({"name": "a.txt", "data": b""}, "it")
        with self.assertRaisesRegex(ValueError, "PDF could not be read"):
            making.recovered_text({"name": "a.pdf", "data": b"%PDF-1.4\nno\n"}, "it")


class Reopen(unittest.TestCase):
    def test_a_finished_book_is_making_again_with_its_record_kept_and_the_agent_told(self):
        _into, r = made(self)
        d = r["path"]
        Path(d, "annot").joinpath("ch1_p00.json").write_text("{}", encoding="utf-8")
        Path(d, "NOTES.md").write_text("# notes\n", encoding="utf-8")
        agent_writes(d, stage="done", checks={"verify_book": "clean"}, sources={"done": [1], "of": 1})
        making._end_making(d)
        self.assertEqual((making.state(d), making.is_making(d)), ("finished", False))
        self.assertTrue(record(d)["finished"])
        # the Finish that ended it is a job the server still holds, and the panel reads it every few seconds
        making.FINISH[os.path.realpath(d)] = {"state": "done", "steps": [], "said": "", "started": 0, "finished": 0, "ok": True}
        self.addCleanup(making.FINISH.pop, os.path.realpath(d), None)
        making.reopen(d)
        self.assertEqual(making.finish_status(d)["state"], "idle",
                         "or the reopened panel would take the making for ended and reload itself for ever")
        doc = record(d)
        self.assertEqual((making.state(d), making.is_making(d)), ("making", True), "the lock on editing is back")
        self.assertEqual(("finished" in doc, doc["stage"], doc["checks"], doc["sources"], len(doc["parts"])),
                         (False, "done", {"verify_book": "clean"}, {"done": [1], "of": 1}, 1))
        self.assertEqual(Path(d, "annot", "ch1_p00.json").read_text(encoding="utf-8"), "{}")
        self.assertEqual(Path(d, "NOTES.md").read_text(encoding="utf-8"), "# notes\n")
        asks = Path(d, "ASKS.md").read_text(encoding="utf-8")
        self.assertLess(asks.index("\u2014 finished"), asks.index("\u2014 reopened"))
        self.assertIn("is taken back", asks)

    def test_only_a_finished_book_is_reopened(self):
        _into, r = made(self)
        with self.assertRaisesRegex(ValueError, "not finished"):
            making.reopen(r["path"])
        os.unlink(os.path.join(r["path"], "making.json"))
        with self.assertRaisesRegex(ValueError, "not made by an agent"):
            making.reopen(r["path"])


class WhatFinishWaitsFor(unittest.TestCase):
    """The owner has not decided it (brief 5.10): ONE function says what stands in the way, and each option
    he is offered is a change of a setting beside it -- shown here, so that none of them is more than that."""

    def folder(self, **fields):
        _into, r = made(self)
        d = r["path"]
        agent_writes(d, **fields)
        return d

    def test_recommended_the_agent_has_taken_every_part_and_said_it_is_idle_and_more_text_does_not_stop_it(self):
        d = self.folder(stage="batch", on="batch 4 of 12", batches={"done": 3, "of": 12})
        making.add_part(d, {"text": "x"}, {"label": "the last chapters"})
        self.assertEqual(making.finish_blockers(d), [
            "part 1 has not been taken by the agent yet", "part 2 (the last chapters) has not been taken by the agent yet",
            "the agent has not said it is done: its record says \"batch 4 of 12\", and what it writes next is lost "
            "once the book is finished"])
        agent_writes(d, sources={"done": [1, 2]}, stage="waiting")
        self.assertEqual(making.finish_blockers(d), [], "waiting for the next part is idle, and more_coming is true")
        self.assertTrue(making.describe(d)["more_coming"])
        agent_writes(d, stage="done")
        self.assertEqual(making.finish_blockers(d), [])
        self.assertEqual(making.describe(d)["blockers"], [])

    def test_a_second_press_goes_through_where_the_agent_has_not_said_it_is_idle(self):
        d = self.folder(stage="batch")
        self.assertEqual(making.finish_gate(d)[0], False)
        allowed, blockers = making.finish_gate(d, confirmed=True)
        self.assertEqual((allowed, len(blockers)), (True, 2))
        with patch.object(making, "FINISH_CONFIRMABLE", False):
            self.assertEqual(making.finish_gate(d, confirmed=True)[0], False)

    def test_option_a_nothing_but_the_second_press(self):
        d = self.folder(stage="batch")
        with patch.object(making, "FINISH_WAITS_FOR", ()):
            self.assertEqual((making.finish_blockers(d), making.finish_gate(d)[0]), ([], True))

    def test_option_b_the_persons_this_is_all_the_text_and_every_part_taken(self):
        d = self.folder(stage="done", sources={"done": [1]})
        with patch.object(making, "FINISH_WAITS_FOR", ("text", "parts", "agent")), patch.object(making, "FINISH_CONFIRMABLE", False):
            self.assertEqual(making.finish_blockers(d), ["you have not said that this is all the text: more may be coming"])
            self.assertEqual(making.finish_gate(d, confirmed=True)[0], False, "no second press passes it")
            making.set_more_coming(d, False)
            self.assertEqual(making.finish_blockers(d), [])
            making.add_part(d, {"text": "x"})
            self.assertEqual(making.finish_blockers(d), ["part 2 has not been taken by the agent yet"])

    def test_a_book_that_is_finished_or_has_no_record_waits_for_nothing(self):
        d = self.folder()
        making._end_making(d)
        self.assertEqual(making.finish_blockers(d), [])
        os.unlink(os.path.join(d, "making.json"))
        self.assertEqual(making.finish_blockers(d), [])

    def test_a_record_the_agent_is_writing_just_now_is_said_and_not_guessed_at(self):
        d = self.folder()
        Path(d, "making.json").write_text('{"stage": "ba', encoding="utf-8")
        self.assertEqual(len(making.finish_blockers(d)), 1)
        self.assertIn("cannot be read just now", making.finish_blockers(d)[0])


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

    def test_every_part_of_the_text_travels_with_the_book_and_parseh_s_copy_of_the_list_does_not(self):
        d = self.book()
        making.add_part(str(d), {"name": "Chapter Two.txt", "data": TEXT}, {"label": "two"})
        making.add_part(str(d), {"name": "x.pdf", "data": PDF}, {"pages": "0-1"})
        making.add_part(str(d), {"text": "Pasted."})
        data, _name = bundle.pack_book(str(d))
        got, _man = self.names(data)
        for want in ("original/Il-Gatto.txt", "original/part-002-Chapter-Two.txt", "original/part-003-x.pdf",
                     "original/part-004-pasted.txt"):
            self.assertIn(want, got)
        self.assertNotIn("original/parts.json", got, "the list is about one making on one computer, like making.json")
        self.assertFalse([n for n in got if n.endswith(".part")])

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
