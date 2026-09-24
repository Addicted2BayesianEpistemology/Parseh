#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Glossing a region with an LLM (lib/glossregion.py), on every fixture
edition and every fixture video.

    python3 -m unittest discover -s tests -p test_glossregion.py

The round trip is the proof worth having: a glossed chunk has its gloss
deleted through the door the reader and the player use, the region around it
is asked for in a prompt, the prompt's own JSON is answered with the gloss
that was deleted -- and the file is then the file it was, BYTE FOR BYTE.  A
prompt that sent the wrong text, an apply that wrote a field it should not,
a writer that normalised something on the way past would all show up here.

Then everything an answer must NOT do, and the page cannot stop because the
page decides nothing: rewrite a gloss already written (kept, listed, the file
untouched), answer another region or another video (dropped), divide a
sentence differently (dropped), put another text -- or the same texts in
another order -- where a chunk is (dropped: the text is what says which chunk
a gloss is for), leave a chunk half glossed (dropped, nothing written), fill a
box that is not blank in per-field mode, replace glosses in re-gloss without
the second click, give a caption a start that is no time at all (dropped, no
crash), carry a broken character or nest deeper than it can be read (refused
whole, before anything is written).  And the text the prompt sends is the
chunks as they stand -- a paragraph or a caption freed from its source is
sent as the page shows it, never as source/paras/ or transcript.txt has it --
with a paragraph folded away in the reader left out and counted.

Every fixture is copied to a temporary directory first: nothing under
tests/fixtures/ is ever written.  Standard library only.
"""
import glob
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "lib")
YT_LIB = os.path.join(ROOT, "youtube", "lib")
for _p in (LIB, YT_LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import annwrite as A              # noqa: E402
import books                      # noqa: E402
import check_annotations as CA    # noqa: E402
import glossregion as GR          # noqa: E402
import languages                  # noqa: E402
import reading                    # noqa: E402
import texwrite as X              # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")
BOOKS = sorted(glob.glob(os.path.join(FIX, "books", "*", "*", "book.json")))
VIDEOS = sorted(glob.glob(os.path.join(FIX, "videos", "*", "*", "video.json")))
GLOSS = ("kana", "tr", "voc", "en")
# json_blocks' own words for an answer it cannot read at all
BROKEN = ("the answer carries a broken character (an unpaired surrogate) -- "
          "copy it again from the chat")
DEEP = "the answer nests too deep to be read"


def fence(doc):
    return "```json\n" + json.dumps(doc, ensure_ascii=False, indent=1) + "\n```"


def data_of(prompt):
    """The JSON the prompt ends with: the last ```json fence in it."""
    a = prompt.rindex("```json") + len("```json")
    return json.loads(prompt[a:prompt.rindex("```")])


def snap(d):
    """Every file under d -> its bytes."""
    out = {}
    for base, _dirs, files in os.walk(d):
        for f in files:
            p = os.path.join(base, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, d)] = fh.read()
    return out


def required(L):
    return (["kana"] if L.reading else []) + (["tr"] if L.require_tr else []) + ["en"]


def said(fields):
    """The fields as the prompt lists them: `kana`, `tr` and `en`."""
    f = ["`%s`" % x for x in fields]
    return f[0] if len(f) == 1 else "%s and %s" % (", ".join(f[:-1]), f[-1])


def todos(doc, key):
    """[(unit, j, chunk)] for every chunk the prompt marks as to do."""
    return [(u, j, c) for u in doc[key] for j, c in enumerate(u.get("chunks") or [])
            if c.get("todo")]


class JsonBlocks(unittest.TestCase):
    A = {"sentences": [{"at": "ch1:1.1", "chunks": []}]}
    B = {"sentences": [{"at": "ch1:1.2", "chunks": []}]}

    def dump(self, d):
        return json.dumps(d, ensure_ascii=False)

    def test_blocks_glued_to_the_fence_before_them_are_blocks(self):
        a, b = self.dump(self.A), self.dump(self.B)
        for glue in ("", " ", "\t "):
            text = "```json\n%s\n```%s```json\n%s\n```" % (a, glue, b)
            self.assertEqual(GR.json_blocks(text), [self.A, self.B], repr(glue))
        self.assertEqual(GR.json_blocks("```json\r\n%s\r\n``````json\r\n%s\r\n```" % (a, b)),
                         [self.A, self.B], "pasted from Windows")

    def test_a_fence_of_prose_is_ignored(self):
        text = ("Here is what I did:\n```\nI kept every chunk as divided.\n```\n"
                "```json\n%s\n```\n```text\n42\n```" % self.dump(self.A))
        self.assertEqual(GR.json_blocks(text), [self.A])
        # ...while a fence without a label that does hold JSON still counts
        self.assertEqual(GR.json_blocks("```\n%s\n```" % self.dump(self.A)), [self.A])

    def test_a_broken_json_fence_is_refused(self):
        with self.assertRaises(ValueError) as cm:
            GR.json_blocks('```json\n{"sentences": [\n```')
        self.assertIn("not valid JSON", str(cm.exception))
        with self.assertRaises(ValueError):
            GR.json_blocks("```json\n%s\n```\n```json\n{broken\n```" % self.dump(self.A))

    def test_several_documents_without_fences(self):
        a, b = self.dump(self.A), self.dump(self.B)
        self.assertEqual(GR.json_blocks(a + "\n" + b), [self.A, self.B])
        self.assertEqual(GR.json_blocks(a + "\n\n" + b + "\n"), [self.A, self.B])
        self.assertEqual(GR.json_blocks(a), [self.A])
        self.assertEqual(GR.json_blocks("Sure! " + a + " Done."), [self.A],
                         "the outermost {...} of a text that is not JSON")

    def test_a_broken_character_is_refused_wherever_it_is(self):
        # half of a surrogate pair -- what a chat window leaves of an emoji
        # cut in two -- cannot be written in UTF-8: the report that quotes
        # it could not be sent, after the good chunks were written.  Refused
        # before anything is read: as pasted, as the escape a model wrote in
        # its JSON, in the prose round the JSON, unfenced
        good = self.dump(self.A)
        for text in ('```json\n{"sentences": [{"at": "ch1:1.1\ud83d", "chunks": []}]}\n```',
                     '```json\n{"sentences": [{"at": "ch1:1.1\\ud83d", "chunks": []}]}\n```',
                     "Here it is \udc00\n```json\n%s\n```" % good,
                     '{"sentences": [], "x": {"\\ud800": 1}}'):
            with self.assertRaises(ValueError) as cm:
                GR.json_blocks(text)
            self.assertEqual(str(cm.exception), BROKEN, repr(text))
        # ...while a whole pair, escaped or not, is the character it is
        self.assertEqual(GR.json_blocks('{"a": "\\ud83d\\ude00 \U0001F600"}'),
                         [{"a": "\U0001F600 \U0001F600"}])

    def test_an_answer_nested_too_deep_is_refused(self):
        # json.loads gives up past some ten thousand levels with a
        # RecursionError, which is no ValueError: it went past every handler
        # to a 500.  Said in words, wherever the nesting is
        deep = "[" * 100000 + "]" * 100000
        for text in ("```json\n%s\n```" % deep, "```\n%s\n```" % deep, deep,
                     'Sure! ' + '{"a": ' * 100000 + "1" + "}" * 100000 + " Done."):
            with self.assertRaises(ValueError) as cm:
                GR.json_blocks(text)
            self.assertEqual(str(cm.exception), DEEP)
        # ...while a depth the decoder does follow is read
        doc = []
        for _ in range(499):
            doc = [doc]
        self.assertEqual(GR.json_blocks("[" * 500 + "]" * 500), [doc])

    def test_an_answer_that_is_not_text(self):
        for answer in (None, 5, ["x"], {"sentences": []}, "", "   "):
            with self.assertRaises(ValueError) as cm:
                GR.json_blocks(answer)
            self.assertIn("empty", str(cm.exception), repr(answer))
        with self.assertRaises(ValueError):
            GR.json_blocks("no json here at all")


# --- a book ----------------------------------------------------------------
class Book(object):
    """A scratch copy of one fixture edition, a glossed chunk picked in it,
    and the region round it."""

    def __init__(self, test, bj):
        src = os.path.dirname(bj)
        self.d = os.path.join(test.td, "%d" % len(os.listdir(test.td)),
                              os.path.basename(src))
        shutil.copytree(src, self.d, ignore=shutil.ignore_patterns(
            "reader", "*.pdf", "*.aux", "*.log", "*.toc", "*.out"))
        with io.open(bj, encoding="utf-8") as f:
            self.name = "%s [%s]" % (os.path.basename(src), json.load(f)["language"])
        b = books.Book(self.d)
        self.L, self.G = b.lang, b.gloss_lang
        ch = next(c for c in X.book_chapters(self.d) if c["file"] == "ch1.tex")
        self.p, self.base, self.chapter = ch["path"], ch["first"], ch["chapter"]
        recs = self.recs()
        glossed = [r for r in recs if r["macro"] != "chp"
                   and all(r[f].strip() for f in required(self.L))]
        test.assertTrue(glossed, self.name)
        # a glossed chunk that is not the first, in a sentence of more than
        # one chunk, so that there is something round it on every side
        size = lambda r: sum(1 for x in recs if x["label"] == r["label"])
        self.k = next((r["index"] for r in glossed if r["index"] and size(r) > 1),
                      glossed[0]["index"])
        self.old = {f: recs[self.k][f] for f in GLOSS if recs[self.k][f].strip()}
        self.n = self.base + self.k
        self.first = self.base + max(0, self.k - 1)
        self.last = self.base + min(len(recs) - 1, self.k + 1)
        self.before = snap(self.d)

    def recs(self):
        return X.read_chunks(self.p)

    def delete(self, k=None):
        k = self.k if k is None else k
        r = self.recs()[k]
        X.edit_chunk(self.p, k, {f: "" for f in GLOSS if f in r["fields"]
                                 and (f != "kana" or self.L.reading)})

    def prompt(self, first=None, last=None, **mode):
        return GR.book_prompt(self.d, self.first if first is None else first,
                              self.last if last is None else last, **mode)

    def apply(self, doc, first=None, last=None, **mode):
        return GR.book_apply(self.d, self.first if first is None else first,
                             self.last if last is None else last,
                             doc if isinstance(doc, str) else fence(doc), **mode)

    def shown(self, r):
        """The file's records for the chunks a prompt answer covers."""
        return self.recs()[r["first"] - self.base:r["last"] - self.base + 1]


class BookRegion(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = td.name

    def every(self, check):
        """check(book) on a fresh copy of every fixture edition, each a
        subtest of its own."""
        for bj in BOOKS:
            with self.subTest(os.path.relpath(os.path.dirname(bj), FIX)):
                check(Book(self, bj))

    def test_the_deleted_gloss_is_asked_for_and_comes_back_byte_for_byte(self):
        self.every(self.the_deleted_gloss_is_asked_for_and_comes_back_byte_for_byte)

    def the_deleted_gloss_is_asked_for_and_comes_back_byte_for_byte(self, b):
        b.delete()
        self.assertEqual(b.recs()[b.k]["en"], "")
        r = b.prompt()
        t = r["prompt"]
        self.assertIn("- language: %s (`%s`)" % (b.L.name, b.L.code), t)
        self.assertIn("## The conventions of %s — binding" % b.L.name, t)
        self.assertIn("Write every meaning in %s." % b.G.name, t)
        self.assertIn("- gloss language: **%s** (`%s`)" % (b.G.name, b.G.code), t)
        self.assertIn("**A chunk you gloss is glossed completely:** %s on every one"
                      % said(required(b.L)), t)
        self.assertIn("`voc` is **LaTeX**", t)
        self.assertNotIn("`voc` is **plain text**", t)
        self.assertNotIn("{{", t.split("## The conventions of")[0])
        doc = data_of(t)
        got = [c for u in doc["sentences"] for c in u["chunks"]]
        recs = b.shown(r)
        self.assertEqual([c["fa"] for c in got], [x["fa"] for x in recs])
        self.assertLessEqual(r["first"], b.n)
        self.assertGreaterEqual(r["last"], b.n)
        for c, x in zip(got, recs):
            if x["index"] == b.k or (x["macro"] != "chp" and CA.unwritten(x, b.L)):
                self.assertIs(c.get("todo"), True, c)
                self.assertFalse(any(f in c for f in GLOSS), c)
            elif x["macro"] == "chp":
                self.assertEqual(c.get("plain"), True)
            else:
                self.assertNotIn("todo", c)
                self.assertEqual({f: c[f] for f in GLOSS if f in c},
                                 {f: x[f] for f in GLOSS if x[f].strip()},
                                 "a glossed chunk is sent with its gloss")
        self.assertEqual(r["fill"], sum(1 for c in got if c.get("todo")))
        self.assertEqual(r["glossed"], sum(1 for c in got
                                           if not c.get("todo") and not c.get("plain")))
        # answered with what was deleted
        (u, j, c), = [x for x in todos(doc, "sentences")
                      if x[2]["fa"] == b.recs()[b.k]["fa"]]
        c.pop("todo")
        c.update(b.old)
        a = b.apply(doc)
        self.assertEqual((a["written"], a["filled"], a["dropped"], a["kept"]),
                         ([b.n], 1, [], []), a)
        self.assertEqual(a["chunks"][str(b.n)]["en"], b.old["en"])
        self.assertEqual(snap(b.d), b.before, "the book is itself byte for byte")

    def test_a_correction_pasted_after_the_answer_wins(self):
        self.every(self.a_correction_pasted_after_the_answer_wins)

    def a_correction_pasted_after_the_answer_wins(self, b):
        b.delete()
        doc = data_of(b.prompt()["prompt"])
        (u, j, c), = todos(doc, "sentences")[:1]
        c.update(b.old, en="WRONG FIRST TRY")
        fix = json.loads(json.dumps({"sentences": [u]}))
        fix["sentences"][0]["chunks"][j]["en"] = b.old["en"]
        a = b.apply(fence(doc) + fence(fix))        # glued, as a paste lands
        self.assertEqual(a["written"], [b.n], a)
        self.assertEqual(snap(b.d), b.before)

    def test_a_hostile_answer_changes_nothing_and_says_what_it_kept(self):
        self.every(self.a_hostile_answer_changes_nothing_and_says_what_it_kept)

    def a_hostile_answer_changes_nothing_and_says_what_it_kept(self, b):
        b.delete()
        before = snap(b.d)
        doc = data_of(b.prompt()["prompt"])
        hostile = 0
        for u in doc["sentences"]:
            for c in u["chunks"]:
                if c.get("en"):
                    c["en"] = "HOSTILE " + c["en"]
                    c["col"] = "red"
                    hostile += 1
        self.assertTrue(hostile)
        a = b.apply(doc)
        self.assertEqual(snap(b.d), before, "not one byte")
        self.assertEqual((a["written"], a["filled"], a["wrote"]), ([], 0, False))
        self.assertEqual(len(a["kept"]), hostile, a["kept"])
        self.assertTrue(all("already glossed" in k["why"] for k in a["kept"]), a["kept"])
        self.assertEqual([x["index"] for x in a["unanswered"]], [b.n])

    def test_an_answer_for_another_region_is_dropped(self):
        self.every(self.an_answer_for_another_region_is_dropped)

    def an_answer_for_another_region_is_dropped(self, b):
        b.delete()
        before = snap(b.d)
        doc = data_of(b.prompt()["prompt"])
        (u, j, c), = todos(doc, "sentences")
        c.pop("todo")
        c.update(b.old)
        # the region the page has now: another sentence of the book
        elsewhere = next(x for x in b.recs() if x["label"] != b.recs()[b.k]["label"])
        n = b.base + elsewhere["index"]
        a = b.apply(doc, first=n, last=n)
        self.assertEqual(snap(b.d), before)
        self.assertEqual(a["written"], [])
        self.assertIn("outside the region you selected",
                      [d["why"] for d in a["dropped"]])
        # ...and a sentence the book does not have at all
        u["at"] = "ch1:99.99"
        a = b.apply(doc)
        self.assertEqual(snap(b.d), before)
        self.assertIn("no such sentence in this book", [d["why"] for d in a["dropped"]])

    def test_a_sentence_divided_again_is_dropped(self):
        self.every(self.a_sentence_divided_again_is_dropped)

    def a_sentence_divided_again_is_dropped(self, b):
        b.delete()
        before = snap(b.d)
        doc = data_of(b.prompt()["prompt"])
        (u, j, c), = todos(doc, "sentences")
        if len(u["chunks"]) < 2:
            self.skipTest("%s: the chunk is its sentence's only one" % b.name)
        c.pop("todo")
        c.update(b.old)
        i = j if j + 1 < len(u["chunks"]) else j - 1
        one, two = u["chunks"][i], u["chunks"][i + 1]
        u["chunks"][i:i + 2] = [dict(one, fa=one["fa"] + b.L.word_sep + two["fa"])]
        a = b.apply(doc)
        self.assertEqual(snap(b.d), before)
        self.assertEqual(a["written"], [])
        self.assertTrue(any("differently" in d["why"] and "nothing is written" in d["why"]
                            for d in a["dropped"]), a["dropped"])

    def test_an_answer_that_cannot_be_read_writes_nothing(self):
        self.every(self.an_answer_that_cannot_be_read_writes_nothing)

    def an_answer_that_cannot_be_read_writes_nothing(self, b):
        # a good answer for the deleted chunk, and beside it a sentence whose
        # "at" holds a broken character: the good chunk used to be written,
        # and then the report quoting that "at" could not be sent (a 500,
        # and no report of what landed).  Refused whole, before anything
        # is written
        b.delete()
        before = snap(b.d)
        doc = data_of(b.prompt()["prompt"])
        (u, j, c), = todos(doc, "sentences")
        c.pop("todo")
        c.update(b.old)
        doc["sentences"].append({"at": "ch1:\ud800", "chunks": []})
        for answer, said in ((fence(doc), BROKEN),
                             ("```json\n%s\n```" % json.dumps(doc), BROKEN),
                             ("```json\n%s\n```" % ("[" * 100000 + "]" * 100000), DEEP)):
            with self.assertRaises(GR.Refused) as cm:
                b.apply(answer)
            self.assertEqual(str(cm.exception), said)
            self.assertEqual(snap(b.d), before, "not one byte")
        # the same answer without that sentence is the good one it was
        doc["sentences"].pop()
        self.assertEqual(b.apply(doc)["written"], [b.n])

    def test_a_chunk_whose_text_is_another_is_dropped(self):
        self.every(self.a_chunk_whose_text_is_another_is_dropped)

    def a_chunk_whose_text_is_another_is_dropped(self, b):
        # THE SAME NUMBER OF CHUNKS, one of them with another text in it: a
        # model that lost its place, or glossed a sentence it was not sent.
        # Matched by position alone the gloss of that other text would land
        # on the chunk the page has there; its text is what says it is not
        # this chunk's (D13, D15)
        b.delete()
        before = snap(b.d)
        doc = data_of(b.prompt()["prompt"])
        (u, j, c), = todos(doc, "sentences")
        c.pop("todo")
        c.update(b.old)
        c["fa"] = next(x["fa"] for x in b.recs()
                       if x["macro"] != "chp" and CA.norm(x["fa"], b.L) != CA.norm(c["fa"], b.L))
        a = b.apply(doc)
        self.assertEqual(snap(b.d), before, "not one byte")
        self.assertEqual((a["written"], a["filled"]), ([], 0), a)
        (d,), = [[d for d in a["dropped"] if d.get("index") == b.n]]
        self.assertTrue(d["why"].startswith("text does not match: the answer has «"), d)

    def test_two_chunks_swapped_are_both_dropped(self):
        self.every(self.two_chunks_swapped_are_both_dropped)

    def two_chunks_swapped_are_both_dropped(self, b):
        # the same chunks and the same texts, in another order: neither is
        # where its text is, so neither takes the gloss the answer put there
        # -- the blank one would otherwise take its neighbour's gloss
        b.delete()
        before = snap(b.d)
        doc = data_of(b.prompt()["prompt"])
        (u, j, c), = todos(doc, "sentences")
        if len(u["chunks"]) < 2:
            self.skipTest("%s: the chunk is its sentence's only one" % b.name)
        c.pop("todo")
        c.update(b.old)
        o = j + 1 if j + 1 < len(u["chunks"]) else j - 1
        self.assertNotEqual(CA.norm(u["chunks"][o]["fa"], b.L), CA.norm(c["fa"], b.L))
        u["chunks"][j], u["chunks"][o] = u["chunks"][o], u["chunks"][j]
        a = b.apply(doc)
        self.assertEqual(snap(b.d), before, "not one byte")
        self.assertEqual((a["written"], a["filled"]), ([], 0), a)
        self.assertEqual(sorted(d["index"] for d in a["dropped"]
                                if d["why"].startswith("text does not match")),
                         sorted([b.n, b.n + o - j]), a["dropped"])

    def test_an_incomplete_gloss_is_dropped_and_nothing_written(self):
        self.every(self.an_incomplete_gloss_is_dropped_and_nothing_written)

    def an_incomplete_gloss_is_dropped_and_nothing_written(self, b):
        b.delete()
        before = snap(b.d)
        doc = data_of(b.prompt()["prompt"])
        (u, j, c), = todos(doc, "sentences")
        c.pop("todo")
        short = required(b.L)[0]
        c.update({f: v for f, v in b.old.items() if f != short} or {"voc": "a word"})
        if short != "en":
            c.setdefault("en", "a meaning")
        else:
            c.setdefault("voc", "a word")
        a = b.apply(doc)
        self.assertEqual(snap(b.d), before, "never half a gloss")
        self.assertEqual(a["written"], [])
        (d,), = [[d for d in a["dropped"] if d.get("index") == b.n]]
        self.assertIn("would leave it half glossed: missing `%s`" % short, d["why"])

    def test_per_field_fills_only_the_blank_boxes(self):
        self.every(self.per_field_fills_only_the_blank_boxes)

    def per_field_fills_only_the_blank_boxes(self, b):
        b.delete()
        X.edit_chunk(b.p, b.k, {"en": b.old["en"]})       # one box, by hand
        written = snap(b.d)
        slots = [f for f in GLOSS if f in b.recs()[b.k]["fields"]
                 and (f != "kana" or b.L.reading)]
        r = b.prompt(perfield=True)
        doc = data_of(r["prompt"])
        (u, j, c), = [x for x in todos(doc, "sentences")
                      if x[2]["fa"] == b.recs()[b.k]["fa"]]
        self.assertEqual(c["todo"], [f for f in slots if f != "en"])
        self.assertEqual(c["en"], b.old["en"], "what is written is sent")
        c.update({f: b.old[f] for f in c["todo"] if f in b.old}, en="CHANGED")
        # not per field: the chunk is written, so it is kept whole
        a = b.apply(doc)
        self.assertEqual(snap(b.d), written)
        self.assertTrue(any(k["index"] == b.n for k in a["kept"]), a["kept"])
        # per field: the blank boxes filled, the written one kept
        a = b.apply(doc, perfield=True)
        self.assertEqual((a["written"], a["completed"]), ([b.n], 1), a)
        k, = [k for k in a["kept"] if k["index"] == b.n]
        self.assertIn("`en`", k["why"])
        self.assertEqual(snap(b.d), b.before)

    def test_regloss_writes_nothing_until_it_is_confirmed(self):
        self.every(self.regloss_writes_nothing_until_it_is_confirmed)

    def regloss_writes_nothing_until_it_is_confirmed(self, b):
        r = b.prompt(regloss=True)
        doc = data_of(r["prompt"])
        chunks = [c for u in doc["sentences"] for c in u["chunks"] if not c.get("plain")]
        self.assertTrue(all(c.get("todo") is True for c in chunks))
        self.assertFalse(any(f in c for c in chunks for f in GLOSS),
                         "no gloss already written is sent")
        self.assertEqual((r["glossed"], r["fill"]), (0, len(chunks)))
        recs = {x["fa"]: x for x in b.shown(r)}
        for c in chunks:
            x = recs[c["fa"]]
            c.update({f: x[f] for f in GLOSS if x[f].strip()}, en="NEW " + x["en"])
        a = b.apply(doc, regloss=True)
        self.assertEqual((a["confirm_needed"], a["replace"], a["written"]),
                         (True, len(chunks), []), a)
        self.assertEqual(snap(b.d), b.before)
        a = b.apply(doc, regloss=True, confirm=True)
        self.assertEqual((a["confirm_needed"], a["replaced"], a["filled"]),
                         (False, len(chunks), 0), a)
        now = {x["fa"]: x for x in b.shown(r)}
        for fa, x in recs.items():
            if x["macro"] != "chp":
                self.assertEqual(now[fa]["en"], "NEW " + x["en"])
                self.assertEqual([now[fa][f] for f in ("kana", "tr", "voc")],
                                 [x[f] for f in ("kana", "tr", "voc")])

    def test_a_free_paragraph_is_sent_as_the_page_shows_it(self):
        self.every(self.a_free_paragraph_is_sent_as_the_page_shows_it)

    def a_free_paragraph_is_sent_as_the_page_shows_it(self, b):
        x = b.recs()[b.k]
        reading.set_free(b.d, b.chapter, x["para"], True)
        departed = x["fa"] + b.L.word_sep + x["fa"]
        X.edit_chunk(b.p, b.k, {"fa": departed})
        b.delete()
        src = os.path.join(b.d, "source", "paras", "ch%d_p%02d.txt"
                           % (b.chapter, x["para"] - 1))
        with io.open(src, encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn(CA.norm(departed, b.L), CA.norm(source, b.L))
        doc = data_of(b.prompt()["prompt"])
        (u, j, c), = todos(doc, "sentences")
        self.assertEqual(c["fa"], departed, "the text as it stands, not the source's")
        c.pop("todo")
        c.update(b.old)
        a = b.apply(doc)
        self.assertEqual(a["written"], [b.n], a)
        self.assertEqual((b.recs()[b.k]["fa"], b.recs()[b.k]["en"]), (departed, b.old["en"]))

    def test_a_folded_paragraph_is_left_out_and_counted(self):
        self.every(self.a_folded_paragraph_is_left_out_and_counted)

    def a_folded_paragraph_is_left_out_and_counted(self, b):
        recs = b.recs()
        first, last = b.base, b.base + len(recs) - 1
        full = data_of(b.prompt(first, last)["prompt"])
        para2 = {x["label"] for x in recs if x["para"] == 2}
        self.assertTrue(para2)
        folded_at = [u["at"] for u in full["sentences"]
                     if u["at"].split(":", 1)[1] in para2]
        self.assertEqual(len(folded_at), len(para2))
        k2 = next(x["index"] for x in recs if x["para"] == 2 and x["macro"] != "chp")
        old2 = {f: recs[k2][f] for f in GLOSS if recs[k2][f].strip()}
        b.delete(k2)
        reading.collapse(b.d, reading.key(b.chapter, 2), reading.key(b.chapter, 2))
        r = b.prompt(first, last)
        self.assertEqual(r["folded"], 1)
        self.assertIn("(1 folded paragraph left out)", r["region"])
        doc = data_of(r["prompt"])
        self.assertEqual([u["at"] for u in doc["sentences"]],
                         [u["at"] for u in full["sentences"] if u["at"] not in folded_at])
        self.assertEqual(todos(doc, "sentences"), [], "a folded chunk is not asked for")
        # an answer that fills it anyway is dropped, and says why
        before = snap(b.d)
        label = recs[k2]["label"]
        unit = next(u for u in full["sentences"] if u["at"].split(":", 1)[1] == label)
        j2 = [x["index"] for x in recs if x["label"] == label].index(k2)
        unit["chunks"][j2].update(old2)
        a = b.apply({"sentences": [unit]}, first, last)
        self.assertEqual(snap(b.d), before)
        self.assertEqual(a["written"], [])
        self.assertTrue(any("folded" in d["why"] for d in a["dropped"]), a["dropped"])


# --- a video -----------------------------------------------------------------
class Video(object):
    def __init__(self, test, vj):
        src = os.path.dirname(vj)
        self.d = os.path.join(test.td, "%d" % len(os.listdir(test.td)),
                              os.path.basename(src))
        shutil.copytree(src, self.d)
        with io.open(vj, encoding="utf-8") as f:
            meta = json.load(f)
        self.meta = meta
        self.name = "%s [%s]" % (os.path.basename(src), meta["language"])
        self.L = CA.video_language(self.d, meta)
        self.G = CA.video_gloss(meta)
        segs = self.segs()
        cands = [(i, k) for i, sg in enumerate(segs) if i and not sg.get("plain")
                 for k, c in enumerate(sg.get("chunks") or [])
                 if CA.required(c, self.L) and CA.complete(c, self.L)]
        test.assertTrue(cands, self.name)
        self.i, self.k = next(((i, k) for i, k in cands if len(segs[i]["chunks"]) > 1), cands[0])
        c = segs[self.i]["chunks"][self.k]
        self.old = {f: c[f] for f in GLOSS if (c.get(f) or "").strip()}
        self.frm, self.to = max(0, self.i - 1), min(len(segs) - 1, self.i + 1)
        self.before = snap(self.d)

    def segs(self):
        return A.read(self.d)["segments"]

    def chunk(self):
        return self.segs()[self.i]["chunks"][self.k]

    def delete(self):
        A.edit_chunk(self.d, self.i, self.k,
                     {f: "" for f in GLOSS if f != "kana" or self.L.reading})

    def fraction(self):
        """Caption i made to begin half a second later, in annotations.json
        and transcript.txt alike -- the checker holds the one to the other --
        as a transcript with fractions has it.  -> its start now."""
        ann = A.read(self.d)
        was = ann["segments"][self.i]["start"]
        path = os.path.join(self.d, "transcript.txt")
        caps = CA.parse_transcript(path, self.L)
        (c,), = [[c for c in caps if c["start"] == was]]
        c["start"] = ann["segments"][self.i]["start"] = was + 0.5
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(CA.transcript_text(caps))
        A.write(self.d, ann)
        return was + 0.5

    def prompt(self, frm=None, to=None, **mode):
        return GR.video_prompt(self.d, self.frm if frm is None else frm,
                               self.to if to is None else to, **mode)

    def apply(self, doc, frm=None, to=None, **mode):
        return GR.video_apply(self.d, self.frm if frm is None else frm,
                              self.to if to is None else to,
                              doc if isinstance(doc, str) else fence(doc), **mode)

    def todo(self, doc):
        (u, j, c), = [x for x in todos(doc, "captions")
                      if x[0]["i"] == self.i and x[1] == self.k]
        return u, j, c


class VideoRegion(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = td.name

    def every(self, check):
        """check(video) on a fresh copy of every fixture video, each a
        subtest of its own."""
        for vj in VIDEOS:
            with self.subTest(os.path.relpath(os.path.dirname(vj), FIX)):
                check(Video(self, vj))

    def test_the_deleted_gloss_is_asked_for_and_comes_back_byte_for_byte(self):
        self.every(self.the_deleted_gloss_is_asked_for_and_comes_back_byte_for_byte)

    def the_deleted_gloss_is_asked_for_and_comes_back_byte_for_byte(self, v):
        v.delete()
        self.assertTrue(CA.unwritten(v.chunk(), v.L))
        r = v.prompt()
        t = r["prompt"]
        self.assertIn("- language: %s (`%s`)" % (v.L.name, v.L.code), t)
        self.assertIn("## The conventions of %s — binding" % v.L.name, t)
        self.assertIn("Write every meaning in %s." % v.G.name, t)
        self.assertIn("- gloss language: **%s** (`%s`)" % (v.G.name, v.G.code), t)
        self.assertIn("**A chunk you gloss is glossed completely:** %s on every one"
                      % said(required(v.L)), t)
        self.assertIn("`voc` is **plain text**", t)
        self.assertNotIn("`voc` is **LaTeX**", t)
        doc = data_of(t)
        segs = v.segs()
        self.assertEqual([u["i"] for u in doc["captions"]], list(range(v.frm, v.to + 1)))
        for u in doc["captions"]:
            sg = segs[u["i"]]
            self.assertEqual(u["start"], sg["start"])
            if sg.get("plain"):
                self.assertEqual((u.get("plain"), u.get("text")), (True, sg["text"]))
                continue
            self.assertEqual([c["fa"] for c in u["chunks"]], [c["fa"] for c in sg["chunks"]])
            for c, x in zip(u["chunks"], sg["chunks"]):
                if not CA.required(x, v.L):
                    self.assertEqual(c.get("plain"), True)
                elif CA.unwritten(x, v.L):
                    self.assertIs(c.get("todo"), True, c)
                    self.assertFalse(any(f in c for f in GLOSS), c)
                else:
                    self.assertNotIn("todo", c)
                    self.assertEqual({f: c[f] for f in GLOSS if f in c},
                                     {f: x[f] for f in GLOSS if (x.get(f) or "").strip()})
        u, j, c = v.todo(doc)
        self.assertEqual(r["fill"], len(todos(doc, "captions")))
        c.pop("todo")
        c.update(v.old)
        a = v.apply(doc)
        self.assertEqual((a["written"], a["filled"], a["dropped"], a["kept"]),
                         ([[v.i, v.k]], 1, [], []), a)
        self.assertEqual(a["segments"][str(v.i)]["chunks"][v.k]["en"], v.old["en"])
        self.assertEqual(snap(v.d), v.before, "the video is itself byte for byte")

    def test_a_correction_pasted_after_the_answer_wins(self):
        self.every(self.a_correction_pasted_after_the_answer_wins)

    def a_correction_pasted_after_the_answer_wins(self, v):
        v.delete()
        doc = data_of(v.prompt()["prompt"])
        u, j, c = v.todo(doc)
        c.update(v.old, en="WRONG FIRST TRY")
        fix = json.loads(json.dumps({"captions": [u]}))
        fix["captions"][0]["chunks"][j]["en"] = v.old["en"]
        a = v.apply(fence(doc) + fence(fix))
        self.assertEqual(a["written"], [[v.i, v.k]], a)
        self.assertEqual(snap(v.d), v.before)

    def test_a_hostile_answer_changes_nothing_and_says_what_it_kept(self):
        self.every(self.a_hostile_answer_changes_nothing_and_says_what_it_kept)

    def a_hostile_answer_changes_nothing_and_says_what_it_kept(self, v):
        v.delete()
        before = snap(v.d)
        doc = data_of(v.prompt()["prompt"])
        hostile = 0
        for u in doc["captions"]:
            for c in u.get("chunks") or []:
                if c.get("en"):
                    c["en"] = "HOSTILE " + c["en"]
                    c["note"] = "an LLM's note"
                    hostile += 1
        self.assertTrue(hostile)
        a = v.apply(doc)
        self.assertEqual(snap(v.d), before, "not one byte")
        self.assertEqual((a["written"], a["filled"], a["wrote"]), ([], 0, False))
        self.assertEqual(len(a["kept"]), hostile, a["kept"])
        self.assertTrue(all("already glossed" in k["why"] and "`note`" in k["why"]
                            for k in a["kept"]), a["kept"])
        self.assertEqual([(x["i"], x["chunk"]) for x in a["unanswered"]], [(v.i, v.k)])

    def test_an_answer_for_another_video_or_region_is_dropped(self):
        self.every(self.an_answer_for_another_video_or_region_is_dropped)

    def an_answer_for_another_video_or_region_is_dropped(self, v):
        v.delete()
        before = snap(v.d)
        doc = data_of(v.prompt()["prompt"])
        u, j, c = v.todo(doc)
        c.pop("todo")
        c.update(v.old)
        # another video: the same numbers, other times
        other = json.loads(json.dumps(doc))
        for x in other["captions"]:
            x["start"] = x["start"] + 7.5
        a = v.apply(other)
        self.assertEqual(snap(v.d), before)
        self.assertEqual(a["written"], [])
        self.assertTrue(any("start does not match" in d["why"] for d in a["dropped"]),
                        a["dropped"])
        # another region: the caption lies outside the one picked now
        j2 = next(i for i, sg in enumerate(v.segs()) if i != v.i and not sg.get("plain"))
        a = v.apply(doc, frm=j2, to=j2)
        self.assertEqual(snap(v.d), before)
        self.assertIn("caption %d is outside the region you selected" % v.i,
                      [d["why"] for d in a["dropped"]])
        # and a caption the video has not got
        u["i"] = len(v.segs()) + 4
        u.pop("start")
        a = v.apply(doc)
        self.assertEqual(snap(v.d), before)
        self.assertTrue(any(d["why"].startswith("no caption %d" % u["i"])
                            for d in a["dropped"]), a["dropped"])

    def test_a_caption_divided_again_is_dropped(self):
        self.every(self.a_caption_divided_again_is_dropped)

    def a_caption_divided_again_is_dropped(self, v):
        v.delete()
        before = snap(v.d)
        doc = data_of(v.prompt()["prompt"])
        u, j, c = v.todo(doc)
        if len(u["chunks"]) < 2:
            self.skipTest("%s: the chunk is its caption's only one" % v.name)
        c.pop("todo")
        c.update(v.old)
        i = j if j + 1 < len(u["chunks"]) else j - 1
        one, two = u["chunks"][i], u["chunks"][i + 1]
        u["chunks"][i:i + 2] = [dict(one, fa=one["fa"] + v.L.word_sep + two["fa"])]
        a = v.apply(doc)
        self.assertEqual(snap(v.d), before)
        self.assertEqual(a["written"], [])
        self.assertTrue(any("differently" in d["why"] for d in a["dropped"]), a["dropped"])

    def test_an_answer_that_cannot_be_read_writes_nothing(self):
        self.every(self.an_answer_that_cannot_be_read_writes_nothing)

    def an_answer_that_cannot_be_read_writes_nothing(self, v):
        # as a book's: here the broken character is in another chunk's text,
        # which the report quotes when it does not match
        v.delete()
        before = snap(v.d)
        doc = data_of(v.prompt()["prompt"])
        u, j, c = v.todo(doc)
        c.pop("todo")
        c.update(v.old)
        other = next(x for x in doc["captions"] if x is not u and x.get("chunks"))
        other["chunks"][0]["fa"] = "x\ud800"
        for answer, said in ((fence(doc), BROKEN),
                             ("```json\n%s\n```" % json.dumps(doc), BROKEN),
                             ("[" * 100000 + "]" * 100000, DEEP)):
            with self.assertRaises(GR.Refused) as cm:
                v.apply(answer)
            self.assertEqual(str(cm.exception), said)
            self.assertEqual(snap(v.d), before, "not one byte")

    def test_a_chunk_whose_text_is_another_is_dropped(self):
        self.every(self.a_chunk_whose_text_is_another_is_dropped)

    def a_chunk_whose_text_is_another_is_dropped(self, v):
        # as a book's (BookRegion's, above): the same number of chunks, one
        # of them another caption's text
        v.delete()
        before = snap(v.d)
        doc = data_of(v.prompt()["prompt"])
        u, j, c = v.todo(doc)
        c.pop("todo")
        c.update(v.old)
        c["fa"] = next(x["fa"] for sg in v.segs() if not sg.get("plain")
                       for x in sg.get("chunks") or []
                       if CA.required(x, v.L) and CA.norm(x["fa"], v.L) != CA.norm(c["fa"], v.L))
        a = v.apply(doc)
        self.assertEqual(snap(v.d), before, "not one byte")
        self.assertEqual((a["written"], a["filled"]), ([], 0), a)
        (d,), = [[d for d in a["dropped"] if (d.get("i"), d.get("chunk")) == (v.i, v.k)]]
        self.assertTrue(d["why"].startswith("text does not match: the answer has «"), d)

    def test_two_chunks_swapped_are_both_dropped(self):
        self.every(self.two_chunks_swapped_are_both_dropped)

    def two_chunks_swapped_are_both_dropped(self, v):
        v.delete()
        before = snap(v.d)
        doc = data_of(v.prompt()["prompt"])
        u, j, c = v.todo(doc)
        if len(u["chunks"]) < 2:
            self.skipTest("%s: the chunk is its caption's only one" % v.name)
        c.pop("todo")
        c.update(v.old)
        o = j + 1 if j + 1 < len(u["chunks"]) else j - 1
        self.assertNotEqual(CA.norm(u["chunks"][o]["fa"], v.L), CA.norm(c["fa"], v.L))
        u["chunks"][j], u["chunks"][o] = u["chunks"][o], u["chunks"][j]
        a = v.apply(doc)
        self.assertEqual(snap(v.d), before, "not one byte")
        self.assertEqual((a["written"], a["filled"]), ([], 0), a)
        self.assertEqual(sorted((d["i"], d["chunk"]) for d in a["dropped"]
                                if d["why"].startswith("text does not match")),
                         sorted([(v.i, j), (v.i, o)]), a["dropped"])

    def test_a_start_that_is_no_time_is_dropped(self):
        self.every(self.a_start_that_is_no_time_is_dropped)

    def a_start_that_is_no_time_is_dropped(self, v):
        # The answer's `start` is the model's to write, and JSON lets it
        # write a number no float holds (a 1 and four hundred zeros), or
        # Python's reader lets it write NaN and Infinity.  Set against a
        # caption that begins on a fraction -- a transcript with fractions,
        # a caption's time moved in the player -- the first could not even
        # be subtracted (an OverflowError, a 500), and NaN matched every
        # caption, since no comparison with it is ever true.  A start that
        # is no time at all matches no caption: dropped, in words.
        at = v.fraction()
        self.assertEqual(CA.check(v.d)[0], [], "the video checks as it did")
        v.delete()
        before = snap(v.d)
        doc = data_of(v.prompt()["prompt"])
        u, j, c = v.todo(doc)
        self.assertEqual(u["start"], at)
        c.pop("todo")
        c.update(v.old)
        for start in (10 ** 400, -10 ** 400, float("nan"), float("inf"), float("-inf")):
            u["start"] = start
            a = v.apply(doc)
            self.assertEqual(snap(v.d), before, "not one byte: start %r" % start)
            self.assertEqual(a["written"], [], start)
            (d,), = [[d for d in a["dropped"] if d.get("i") == v.i]]
            self.assertTrue(d["why"].startswith("start does not match (the answer says "), d)
            self.assertIn("which is no number of seconds", d["why"])
            # and without the caption's number, looked for by its start alone
            one = {"captions": [{k: x for k, x in u.items() if k != "i"}]}
            a = v.apply(one)
            self.assertEqual(snap(v.d), before, "not one byte: start %r alone" % start)
            self.assertEqual(a["written"], [], start)
            d, = a["dropped"]
            self.assertTrue(d["why"].startswith('it has no "i" naming its caption, and its '
                                                "start ("), d)
            self.assertTrue(d["why"].endswith(") is no number of seconds"), d)
        # the control: the caption's own start, fraction and all, lands
        u["start"] = at
        a = v.apply(doc)
        self.assertEqual(a["written"], [[v.i, v.k]], a)

    def test_an_incomplete_gloss_is_dropped_and_nothing_written(self):
        self.every(self.an_incomplete_gloss_is_dropped_and_nothing_written)

    def an_incomplete_gloss_is_dropped_and_nothing_written(self, v):
        v.delete()
        before = snap(v.d)
        doc = data_of(v.prompt()["prompt"])
        u, j, c = v.todo(doc)
        c.pop("todo")
        short = required(v.L)[0]
        c.update({f: x for f, x in v.old.items() if f != short})
        if short != "en":
            c.setdefault("en", "a meaning")
        else:
            c.setdefault("voc", "a word")
        a = v.apply(doc)
        self.assertEqual(snap(v.d), before, "never half a gloss")
        self.assertEqual(a["written"], [])
        (d,), = [[d for d in a["dropped"] if (d.get("i"), d.get("chunk")) == (v.i, v.k)]]
        self.assertIn("would leave it half glossed: missing `%s`" % short, d["why"])

    def test_per_field_fills_only_the_blank_boxes(self):
        self.every(self.per_field_fills_only_the_blank_boxes)

    def per_field_fills_only_the_blank_boxes(self, v):
        v.delete()
        A.edit_chunk(v.d, v.i, v.k, {"en": v.old["en"]})
        written = snap(v.d)
        slots = [f for f in GLOSS if f != "kana" or v.L.reading]
        doc = data_of(v.prompt(perfield=True)["prompt"])
        u, j, c = v.todo(doc)
        self.assertEqual(c["todo"], [f for f in slots if f != "en"])
        self.assertEqual(c["en"], v.old["en"])
        c.update({f: v.old[f] for f in c["todo"] if f in v.old}, en="CHANGED")
        a = v.apply(doc)
        self.assertEqual(snap(v.d), written)
        self.assertTrue(any((k["i"], k["chunk"]) == (v.i, v.k) for k in a["kept"]))
        a = v.apply(doc, perfield=True)
        self.assertEqual((a["written"], a["completed"]), ([[v.i, v.k]], 1), a)
        k, = [k for k in a["kept"] if (k["i"], k["chunk"]) == (v.i, v.k)]
        self.assertIn("`en`", k["why"])
        self.assertEqual(snap(v.d), v.before)

    def test_regloss_writes_nothing_until_it_is_confirmed(self):
        self.every(self.regloss_writes_nothing_until_it_is_confirmed)

    def regloss_writes_nothing_until_it_is_confirmed(self, v):
        r = v.prompt(regloss=True)
        doc = data_of(r["prompt"])
        segs = v.segs()
        chunks = [(u["i"], j, c) for u in doc["captions"]
                  for j, c in enumerate(u.get("chunks") or []) if not c.get("plain")]
        self.assertTrue(chunks)
        self.assertTrue(all(c.get("todo") is True for _i, _j, c in chunks))
        self.assertFalse(any(f in c for _i, _j, c in chunks for f in GLOSS))
        self.assertEqual((r["glossed"], r["fill"]), (0, len(chunks)))
        for i, j, c in chunks:
            x = segs[i]["chunks"][j]
            c.update({f: x[f] for f in GLOSS if (x.get(f) or "").strip()},
                     en="NEW " + x["en"])
        a = v.apply(doc, regloss=True)
        self.assertEqual((a["confirm_needed"], a["replace"], a["written"]),
                         (True, len(chunks), []), a)
        self.assertEqual(snap(v.d), v.before)
        a = v.apply(doc, regloss=True, confirm=True)
        self.assertEqual((a["confirm_needed"], a["replaced"]), (False, len(chunks)), a)
        now = v.segs()
        for i, j, _c in chunks:
            x, y = segs[i]["chunks"][j], now[i]["chunks"][j]
            self.assertEqual(y["en"], "NEW " + x["en"])
            self.assertEqual([y.get(f) for f in ("kana", "tr", "voc")],
                             [x.get(f) for f in ("kana", "tr", "voc")])

    def test_a_free_caption_is_sent_as_the_page_shows_it(self):
        self.every(self.a_free_caption_is_sent_as_the_page_shows_it)

    def a_free_caption_is_sent_as_the_page_shows_it(self, v):
        departed = v.chunk()["fa"] + v.L.word_sep + v.chunk()["fa"]
        A.edit_chunk(v.d, v.i, v.k, {"free": True, "fa": departed})
        v.delete()
        with io.open(os.path.join(v.d, "transcript.txt"), encoding="utf-8") as f:
            transcript = f.read()
        self.assertNotIn(CA.norm(departed, v.L), CA.norm(transcript, v.L))
        doc = data_of(v.prompt()["prompt"])
        u, j, c = v.todo(doc)
        self.assertEqual(c["fa"], departed, "the text as it stands, not the transcript's")
        c.pop("todo")
        c.update(v.old)
        a = v.apply(doc)
        self.assertEqual(a["written"], [[v.i, v.k]], a)
        self.assertEqual((v.chunk()["fa"], v.chunk()["en"], v.chunk()["free"]),
                         (departed, v.old["en"], True))


if __name__ == "__main__":
    unittest.main()
