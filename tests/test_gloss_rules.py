#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The rules a gloss is held to, on both surfaces, in Persian, Italian,
Japanese and Chinese -- and in every fixture language where a rule is asked
of every book or video.

    python3 -m unittest discover -s tests -p test_gloss_rules.py

A chunk nobody has glossed yet is legal everywhere: in every book and every
video, with nothing -- no flag -- to say so.  What that one rule asks of the
rest is proved here, a surface at a time, through the doors a hand uses (the
reader's chunk sheet is lib/texwrite.py, the player's ✎ form
youtube/lib/annwrite.py) and the checkers:

  * by hand a gloss is FILLED a box at a time (half a gloss is saved), and
    EMPTIED whole: emptying one box a finished gloss needs is refused, and
    says that emptying every box ("delete gloss") takes the gloss off; a
    delete keeps the text, the colour, the word line and a video's note;
    sending blank over blank changes nothing; voc may always be emptied;
  * the reading a draft proposes from a chunk's word line leaves the chunk
    blank while nothing else is written, and counts as the reading it is
    once something is; the line corrected on a blank chunk proposes its
    reading again, and the chunk stays blank;
  * a stray "kana" where the language has no reading is no gloss: the
    checker warns of it, and "delete gloss" takes the gloss off beside it;
  * a cut or a join is not refused for the gloss it leaves (blank, half
    glossed or complete), and a blank Japanese or Chinese chunk divides into
    two blank halves, each proposed the reading of its own words;
  * the checkers count blank chunks in one note and call a half-glossed
    chunk an error; a "draft": true an older version left in book.json or
    video.json is never read; the bundle door notes a half-glossed chunk
    instead of refusing the video;
  * the warnings a blank chunk would make certain in advance stay silent,
    each pinned to its count: every fixture transcript drafted into a video,
    a book drafted without word lines, a blank chapter added to every
    fixture edition (and its finished chapter warned exactly as before);
  * lib/draft.py writes no flag, and will not file a video under an id
    another language's folder already holds; verify_book reads an indented
    chunk as the reader does.

Everything works on copies in a temporary directory: the fixture editions
and videos under tests/fixtures/ are never written.  The Japanese and Chinese
analyzers are used where this Python has them, and lib/words.py's shape is
stood in for where it has not (words.line patched, as test_word_seed does),
so the seeded readings are proved under any Python.
"""
import contextlib
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "lib")
YT_LIB = os.path.join(ROOT, "youtube", "lib")
for _p in (LIB, YT_LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import annwrite as A              # noqa: E402
import books                      # noqa: E402
import bundle                     # noqa: E402
import check_annotations as CA    # noqa: E402
import chunkdiv                   # noqa: E402
import chunker                    # noqa: E402
import draft                      # noqa: E402
import languages                  # noqa: E402
import texparse                   # noqa: E402
import texwrite as X              # noqa: E402
import wordline                   # noqa: E402
import words                      # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")
CODES = ("fa", "it", "ja", "zh")
GLOSS = ("kana", "tr", "voc", "en")
BOOK_FIX = {"fa": "persian/mini-fa", "it": "italian/mini-it",
            "ja": "japanese/mini-ja", "zh": "chinese/mini-zh"}
VIDEO_FIX = {"fa": "persian/fA6bK2mQ8sT", "it": "italian/kL9mN1oP3qR",
             "ja": "japanese/aB3dE5fG7hI", "zh": "chinese/zH8cN2hA6nZ"}
# two sentences each: one paragraph of a drafted book, two captions of a
# drafted video -- and every sentence long enough to divide
TEXT = {"fa": ["مرد پیر در تاریکی نشسته بود.", "او هیچ چیز نگفت."],
        "it": ["Il vecchio sedeva nel buio.", "Non disse niente a nessuno."],
        "ja": ["むかしむかし、おじいさんが山へ柴刈りに行きました。", "私は東京に住んでいます。"],
        "zh": ["我想要一杯茶。", "他不去北京。"]}
NOTE = re.compile(r"note\s+(\d+) of (\d+) chunks have no gloss yet")
VNOTE = re.compile(r"^note: (\d+) of (\d+) chunks have no gloss yet$", re.M)


def stand_in(fa, code, reading=""):
    """A proposal shaped as lib/words.py shapes one: a word per character,
    a reading over every kanji or hanzi (test_word_seed's)."""
    say = "よみ" if languages.get(code).reading else "dú"
    return wordline.render([(ch, say if wordline.HAN.search(ch) else "")
                            for ch in fa if not ch.isspace()])


def proposing(code):
    """The analyzer where this Python has one, the stand-in where not."""
    if words.available(code):
        return contextlib.nullcontext()
    return patch.object(draft.words, "line", stand_in)


def required(L):
    """What a written chunk of this language must carry."""
    return (["kana"] if L.reading else []) + (["tr"] if L.require_tr else []) + ["en"]


def raw(path):
    with open(path, "rb") as f:
        return f.read()


def para_json(book, chapter=1):
    """Paragraph 0 of chapter 1 (or `chapter`), read back out of the .tex the
    way smoke does."""
    ch = texparse.parse_book(book.main, book.lang)[chapter - 1]
    sents = []
    for s in ch.paragraphs[0].subs:
        chunks = []
        for c in s.chunks:
            d = {"fa": c.fa, "tr": c.tr, "voc": c.voc, "en": c.en}
            if c.kana:
                d["kana"] = c.kana
            if c.wordline:
                d["words"] = c.wordline
            chunks.append(d)
        sents.append({"chunks": chunks})
    return {"idx": 0, "ch": chapter, "ann": {"sentences": sents}}


class Scratch(unittest.TestCase):
    """Copies and drafts in a temporary directory, and the questions both
    surfaces are asked."""

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = td.name
        self.n = 0

    def fresh(self, name):
        self.n += 1
        d = os.path.join(self.td, "%d" % self.n, name)
        os.makedirs(os.path.dirname(d))
        return d

    # --- books -------------------------------------------------------------
    def fixture_book(self, code):
        """A copy of the fixture edition -> its ch1.tex"""
        d = self.fresh(os.path.basename(BOOK_FIX[code]))
        shutil.copytree(os.path.join(FIX, "books", BOOK_FIX[code]), d,
                        ignore=shutil.ignore_patterns("reader", "*.pdf", "*.aux",
                                                      "*.log", "*.toc", "*.out"))
        return os.path.join(d, "ch1.tex")

    def drafted_book(self, code):
        """A book drafted from TEXT: one paragraph, a blank chunk a sentence,
        every chunk of a words language carrying its line and the reading
        proposed from it.  -> its ch1.tex"""
        with proposing(code):
            r = draft.book_from_text(" ".join(TEXT[code]), code, "t", slug="t-" + code,
                                     into=self.fresh("books"))
        return os.path.join(r["dir"], "ch1.tex")

    def chunk(self, p, k):
        return X.read_chunks(p)[k]

    def complete_book_chunk(self, p, L):
        """The first chunk of the chapter glossed in full, voc included, that
        has somewhere to divide."""
        return next(k for k, c in enumerate(X.read_chunks(p))
                    if c["macro"] != "chp" and c["voc"].strip()
                    and all(c[f].strip() for f in required(L))
                    and chunkdiv.cuts(c["fa"], L))

    def check_batch(self, p, para=None):
        """check_batch.py on paragraph 0 (or `para`) -> (rc, output)"""
        d = os.path.dirname(p)
        pp = os.path.join(self.td, "p%d.json" % self.n)
        with io.open(pp, "w", encoding="utf-8") as f:
            json.dump(para or para_json(books.Book(d)), f, ensure_ascii=False)
        r = subprocess.run([sys.executable, os.path.join(LIB, "check_batch.py"), pp,
                            "--book", d], cwd=d, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    # --- videos ------------------------------------------------------------
    def fixture_video(self, code):
        d = self.fresh(os.path.basename(VIDEO_FIX[code]))
        shutil.copytree(os.path.join(FIX, "videos", VIDEO_FIX[code]), d)
        return d

    def drafted_video(self, code, vid=None):
        """A video drafted from TEXT, a caption a sentence.  -> its directory"""
        transcript = "".join("0:%02d\n%s\n" % (5 * n, s) for n, s in enumerate(TEXT[code]))
        with proposing(code):
            r = draft.video_from_transcript(transcript, code,
                                            video_id=vid or "tstRuleVd" + code,
                                            into=self.fresh("videos"))
        return r["dir"]

    def seg_chunk(self, v, i, k):
        return A.read(v)["segments"][i]["chunks"][k]

    def complete_video_chunk(self, v, L):
        """(segment, chunk) of the first chunk glossed in full, voc included."""
        return next((i, k) for i, sg in enumerate(A.read(v)["segments"])
                    if not sg.get("plain")
                    for k, c in enumerate(sg.get("chunks") or [])
                    if CA.required(c, L) and CA.complete(c, L)
                    and (c.get("voc") or "").strip() and chunkdiv.cuts(c["fa"], L))

    def first_glossable(self, v, L):
        return next((i, k) for i, sg in enumerate(A.read(v)["segments"])
                    if not sg.get("plain")
                    for k, c in enumerate(sg.get("chunks") or [])
                    if CA.required(c, L))

    def ann_path(self, v):
        return os.path.join(v, "annotations.json")

    def cli(self, v):
        r = subprocess.run([sys.executable, os.path.join(YT_LIB, "check_annotations.py"), v],
                           cwd=os.path.join(ROOT, "youtube"), capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr


def same(a, b):
    """Two video chunks that say the same: a key written empty and a key not
    written are one thing to every reader of the format (annwrite._set)."""
    return all((a.get(f) or "") == (b.get(f) or "") for f in set(a) | set(b))


def deleted(fields, L):
    """The fields "delete gloss" sends: every box of the gloss, empty."""
    return {f: "" for f in GLOSS if f in fields and (f != "kana" or L.reading)}


def read_otherwise(line, L):
    """The same word line with its first reading corrected, as a person
    corrects what the analyzer proposed: it still gives the chunk's text
    back, and the reading proposed from it (wordline.seed) is another."""
    pairs = wordline.parse(line)
    k = next(n for n, (_w, r) in enumerate(pairs) if r)
    w, r = pairs[k]
    pairs[k] = (w, r + "あ" if L.reading else "mǎ" if r != "mǎ" else "niú")
    return wordline.render(pairs)


# --- the reader's chunk sheet ------------------------------------------------
class BookHandEdits(Scratch):
    def test_one_box_filled_on_a_blank_chunk_is_saved(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                p = self.drafted_book(code)
                self.assertTrue(CA.unwritten(self.chunk(p, 0), L))
                r = X.edit_chunk(p, 0, {"en": "a meaning, and nothing else"})
                self.assertEqual(r["changed"], ["en"])
                self.assertEqual(self.chunk(p, 0)["en"], "a meaning, and nothing else")
                # ...and one more box, whatever the chunk still lacks
                r = X.edit_chunk(p, 0, {"voc": "a word, a meaning"})
                self.assertEqual(r["changed"], ["voc"])

    def test_emptying_one_box_a_finished_gloss_needs_is_refused(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                p = self.fixture_book(code)
                k = self.complete_book_chunk(p, L)
                before = raw(p)
                for f in required(L):
                    with self.assertRaises(X.Refused) as cm:
                        X.edit_chunk(p, k, {f: ""})
                    self.assertIn('"delete gloss"', str(cm.exception), f)
                    self.assertEqual(raw(p), before, "a refusal writes nothing")
                # every required box emptied but the vocabulary kept is not
                # a delete either
                with self.assertRaises(X.Refused):
                    X.edit_chunk(p, k, {f: "" for f in required(L)})
                self.assertEqual(raw(p), before)

    def test_a_delete_empties_every_box_and_keeps_the_rest(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                p = self.fixture_book(code)
                k = self.complete_book_chunk(p, L)
                X.edit_chunk(p, k, {"col": "red"})
                was, others, before = self.chunk(p, k), X.read_chunks(p), raw(p)
                r = X.edit_chunk(p, k, deleted(was["fields"], L))
                now = self.chunk(p, k)
                self.assertEqual(sorted(r["changed"]),
                                 sorted(f for f in GLOSS if was.get(f)))
                self.assertEqual([now[f] for f in GLOSS], ["", "", "", ""])
                self.assertEqual((now["macro"], now["fa"], now["col"]),
                                 (was["macro"], was["fa"], "red"),
                                 "the same kind of chunk, its text and its colour")
                self.assertTrue(CA.unwritten(now, L))
                keep = lambda c: {f: v for f, v in c.items() if f not in ("span", "line")}
                self.assertEqual([keep(c) for j, c in enumerate(X.read_chunks(p)) if j != k],
                                 [keep(c) for j, c in enumerate(others) if j != k])
                # undo: the old fields written back through the same door
                X.edit_chunk(p, k, {f: was[f] for f in GLOSS if was[f]})
                self.assertEqual(raw(p), before, "undone byte for byte")

    def test_a_delete_keeps_the_word_line(self):
        for code in ("ja", "zh"):
            with self.subTest(code):
                L = languages.get(code)
                p = self.drafted_book(code)
                X.edit_chunk(p, 0, {"en": "a meaning", "voc": "a word"})
                was = self.chunk(p, 0)
                self.assertIn(was["macro"], ("chw", "chrw"))
                self.assertFalse(CA.unwritten(was, L))
                X.edit_chunk(p, 0, deleted(was["fields"], L))
                now = self.chunk(p, 0)
                self.assertEqual((now["macro"], now["words"]), (was["macro"], was["words"]))
                self.assertEqual([now[f] for f in GLOSS], ["", "", "", ""])

    def test_blank_over_blank_changes_nothing(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                p = self.drafted_book(code)
                c, before = self.chunk(p, 0), raw(p)
                blank = {f: "" for f in GLOSS if f in c["fields"] and not c[f]}
                self.assertIn("en", blank)
                r = X.edit_chunk(p, 0, blank)
                self.assertEqual(r["changed"], [])
                self.assertEqual(raw(p), before)
                # ...in a half-glossed chunk as well: a required box sent
                # blank that WAS blank is no emptying, and never refused
                X.edit_chunk(p, 0, {"voc": "a word"})
                before = raw(p)
                r = X.edit_chunk(p, 0, {f: "" for f in required(L)
                                        if not self.chunk(p, 0)[f]})
                self.assertEqual((r["changed"], raw(p)), ([], before))

    def test_the_vocabulary_may_always_be_emptied(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                p = self.fixture_book(code)
                k = self.complete_book_chunk(p, L)
                was = self.chunk(p, k)
                r = X.edit_chunk(p, k, {"voc": ""})
                now = self.chunk(p, k)
                self.assertEqual((r["changed"], now["voc"]), (["voc"], ""))
                self.assertEqual([now[f] for f in required(L)], [was[f] for f in required(L)])

    def test_a_seeded_reading_is_blank_only_until_something_is_written(self):
        for code in ("ja", "zh"):
            with self.subTest(code):
                L = languages.get(code)
                p = self.drafted_book(code)
                c = self.chunk(p, 0)
                field, proposal = wordline.seed(c, L)
                self.assertEqual((field, c[field]), ("kana" if L.reading else "tr", proposal))
                self.assertTrue(proposal and CA.unwritten(c, L), "the proposal is nobody's")
                # while the chunk is blank the proposal may go, and come back
                self.assertEqual(X.edit_chunk(p, 0, {field: ""})["changed"], [field])
                self.assertEqual(X.edit_chunk(p, 0, {field: proposal})["changed"], [field])
                # written, the proposal is the chunk's reading and is guarded
                fill = dict({"en": "a meaning"}, **({"tr": "a reading"} if L.reading else {}))
                X.edit_chunk(p, 0, fill)
                c = self.chunk(p, 0)
                self.assertFalse(CA.unwritten(c, L))
                self.assertTrue(CA.complete(c, L), "the seeded reading counts as there")
                before = raw(p)
                with self.assertRaises(X.Refused) as cm:
                    X.edit_chunk(p, 0, {field: ""})
                self.assertIn('"delete gloss"', str(cm.exception))
                self.assertEqual(raw(p), before)
                # everything but the proposal emptied: blank again, a delete
                X.edit_chunk(p, 0, {f: "" for f in fill})
                self.assertTrue(CA.unwritten(self.chunk(p, 0), L))
                # a reading somebody CHANGED is a gloss: the same emptying
                # then leaves a written chunk without its meaning, refused
                X.edit_chunk(p, 0, dict(fill, **{field: proposal + ("あ" if L.reading else " a")}))
                before = raw(p)
                with self.assertRaises(X.Refused):
                    X.edit_chunk(p, 0, {f: "" for f in fill})
                self.assertEqual(raw(p), before)

    def test_a_word_line_corrected_on_a_blank_chunk_proposes_its_reading_again(self):
        """The word line is the text divided, not a gloss.  Corrected on a
        chunk nobody has glossed -- a reading the analyzer got wrong, two
        words run together -- it proposes the chunk's reading again, as a cut
        and a join do: kept, the old proposal would no longer be the one the
        line makes, and would read as somebody's writing -- a chunk nobody
        glossed listed as half glossed, its "delete gloss" lit, and the
        region fill sending it as context instead of asking for it.  The
        reader's sheet sends the line alone for exactly this edit."""
        for code in ("ja", "zh"):
            with self.subTest(code):
                L = languages.get(code)
                p = self.drafted_book(code)
                c = self.chunk(p, 0)
                field, was = wordline.seed(c, L)
                self.assertTrue(was and c[field] == was and CA.unwritten(c, L))
                line = read_otherwise(c["words"], L)
                X.edit_chunk(p, 0, {"words": line})
                now = self.chunk(p, 0)
                proposal = wordline.seed(now, L)[1]
                self.assertNotEqual(proposal, was)
                self.assertEqual((now["words"], now[field]), (line, proposal))
                self.assertTrue(CA.unwritten(now, L), now)
                rc, out = self.check_batch(p)
                self.assertEqual(rc, 0, out)
                self.assertIn("\n0 errors, 0 warnings, 1 note", out)
                # the line taken off: there is nothing left to propose from,
                # and the proposal goes with it
                X.edit_chunk(p, 0, {"words": ""})
                now = self.chunk(p, 0)
                self.assertEqual((now["words"], now[field]), ("", ""))
                self.assertTrue(CA.unwritten(now, L))
                # a reading TYPED in the same save as the corrected line is
                # the person's, and is kept -- the proposal is made again only
                # when the reading was not sent (on a fresh draft, whose chunk
                # still holds the line's proposal)
                typed = {"ja": "てすとです", "zh": "ceshi"}[code]
                q = self.drafted_book(code)
                fresh = self.chunk(q, 0)
                self.assertEqual(fresh[field], wordline.seed(fresh, L)[1])
                X.edit_chunk(q, 0, {"words": read_otherwise(fresh["words"], L),
                                    field: typed})
                now = self.chunk(q, 0)
                self.assertEqual(now[field], typed)
                self.assertFalse(CA.unwritten(now, L), now)
                # a WRITTEN chunk's reading is its own, whatever its line
                # proposes: correcting the line under it changes nothing else
                X.edit_chunk(p, 1, {"en": "a meaning"})
                c = self.chunk(p, 1)
                X.edit_chunk(p, 1, {"words": read_otherwise(c["words"], L)})
                self.assertEqual(self.chunk(p, 1)[field], c[field])
                self.assertNotEqual(wordline.seed(self.chunk(p, 1), L)[1], c[field])


# --- the player's ✎ form -----------------------------------------------------
class VideoHandEdits(Scratch):
    def test_one_box_filled_on_a_blank_chunk_is_saved(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                v = self.drafted_video(code)
                i, k = self.first_glossable(v, L)
                self.assertTrue(CA.unwritten(self.seg_chunk(v, i, k), L))
                got = A.edit_chunk(v, i, k, {"en": "a meaning, and nothing else"})
                self.assertEqual(got["en"], "a meaning, and nothing else")
                self.assertEqual(self.seg_chunk(v, i, k)["en"], "a meaning, and nothing else")
                A.edit_chunk(v, i, k, {"voc": "a word · a meaning"})
                self.assertEqual(self.seg_chunk(v, i, k)["voc"], "a word · a meaning")

    def test_emptying_one_box_a_finished_gloss_needs_is_refused(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                v = self.fixture_video(code)
                i, k = self.complete_video_chunk(v, L)
                before = raw(self.ann_path(v))
                for f in required(L):
                    with self.assertRaises(ValueError) as cm:
                        A.edit_chunk(v, i, k, {f: ""})
                    self.assertIn('"delete gloss"', str(cm.exception), f)
                    self.assertEqual(raw(self.ann_path(v)), before, "a refusal writes nothing")
                with self.assertRaises(ValueError):
                    A.edit_chunk(v, i, k, {f: "" for f in required(L)})
                self.assertEqual(raw(self.ann_path(v)), before)

    def test_a_delete_empties_every_box_and_keeps_the_rest(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                v = self.fixture_video(code)
                i, k = self.complete_video_chunk(v, L)
                A.edit_chunk(v, i, k, {"col": "blue"})
                ann = A.read(v)
                ann["segments"][i]["chunks"][k]["note"] = "a note of mine"
                A.write(v, ann)
                was, before = dict(self.seg_chunk(v, i, k)), raw(self.ann_path(v))
                A.edit_chunk(v, i, k, deleted(GLOSS, L))
                now = self.seg_chunk(v, i, k)
                self.assertFalse(any(f in now for f in GLOSS), now)
                self.assertEqual({f: now.get(f) for f in ("fa", "col", "note")},
                                 {"fa": was["fa"], "col": "blue", "note": "a note of mine"})
                self.assertTrue(CA.unwritten(now, L))
                self.assertEqual(CA.check(v)[0], [], "a blank chunk is legal")
                # undo, through the same door
                A.edit_chunk(v, i, k, {f: was[f] for f in GLOSS if was.get(f)})
                self.assertEqual(raw(self.ann_path(v)), before, "undone byte for byte")

    def test_a_delete_keeps_the_word_line(self):
        for code in ("ja", "zh"):
            with self.subTest(code):
                L = languages.get(code)
                v = self.drafted_video(code)
                i, k = self.first_glossable(v, L)
                A.edit_chunk(v, i, k, {"en": "a meaning", "voc": "a word"})
                was = dict(self.seg_chunk(v, i, k))
                self.assertTrue(was.get("words"))
                A.edit_chunk(v, i, k, deleted(GLOSS, L))
                now = self.seg_chunk(v, i, k)
                self.assertEqual((now["fa"], now["words"]), (was["fa"], was["words"]))
                self.assertFalse(any(now.get(f) for f in GLOSS), now)

    def test_blank_over_blank_changes_nothing(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                v = self.drafted_video(code)
                i, k = self.first_glossable(v, L)
                c = self.seg_chunk(v, i, k)
                blank = {f: "" for f in GLOSS if f in c and not c[f]}
                self.assertIn("en", blank)
                A.edit_chunk(v, i, k, blank)
                self.assertTrue(same(self.seg_chunk(v, i, k), c))
                # ...in a half-glossed chunk as well: a required box sent
                # blank that WAS blank is no emptying, and never refused
                A.edit_chunk(v, i, k, {"voc": "a word"})
                was = self.seg_chunk(v, i, k)
                A.edit_chunk(v, i, k, {f: "" for f in required(L) if not was.get(f)})
                self.assertTrue(same(self.seg_chunk(v, i, k), was))

    def test_the_vocabulary_may_always_be_emptied(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                v = self.fixture_video(code)
                i, k = self.complete_video_chunk(v, L)
                was = self.seg_chunk(v, i, k)
                A.edit_chunk(v, i, k, {"voc": ""})
                now = self.seg_chunk(v, i, k)
                self.assertNotIn("voc", now)
                self.assertEqual([now[f] for f in required(L)], [was[f] for f in required(L)])

    def test_a_seeded_reading_is_blank_only_until_something_is_written(self):
        for code in ("ja", "zh"):
            with self.subTest(code):
                L = languages.get(code)
                v = self.drafted_video(code)
                i, k = self.first_glossable(v, L)
                c = self.seg_chunk(v, i, k)
                field, proposal = wordline.seed(c, L)
                self.assertEqual((field, c[field]), ("kana" if L.reading else "tr", proposal))
                self.assertTrue(proposal and CA.unwritten(c, L), "the proposal is nobody's")
                self.assertEqual(CA.gloss_state(v)[0], CA.gloss_state(v)[1])
                A.edit_chunk(v, i, k, {field: ""})
                A.edit_chunk(v, i, k, {field: proposal})
                self.assertTrue(CA.unwritten(self.seg_chunk(v, i, k), L))
                fill = dict({"en": "a meaning"}, **({"tr": "a reading"} if L.reading else {}))
                A.edit_chunk(v, i, k, fill)
                c = self.seg_chunk(v, i, k)
                self.assertTrue(CA.complete(c, L), "the seeded reading counts as there")
                self.assertEqual(CA.check(v)[0], [])
                before = raw(self.ann_path(v))
                with self.assertRaises(ValueError) as cm:
                    A.edit_chunk(v, i, k, {field: ""})
                self.assertIn('"delete gloss"', str(cm.exception))
                self.assertEqual(raw(self.ann_path(v)), before)
                A.edit_chunk(v, i, k, {f: "" for f in fill})
                self.assertTrue(CA.unwritten(self.seg_chunk(v, i, k), L))
                A.edit_chunk(v, i, k, dict(fill, **{field: proposal + ("あ" if L.reading else " a")}))
                before = raw(self.ann_path(v))
                with self.assertRaises(ValueError):
                    A.edit_chunk(v, i, k, {f: "" for f in fill})
                self.assertEqual(raw(self.ann_path(v)), before)

    def test_a_word_line_corrected_on_a_blank_chunk_proposes_its_reading_again(self):
        """As a book's (BookHandEdits, above): the player's ✎ form sends the
        line alone when only the line was corrected."""
        for code in ("ja", "zh"):
            with self.subTest(code):
                L = languages.get(code)
                v = self.drafted_video(code)
                i, k = self.first_glossable(v, L)
                c = self.seg_chunk(v, i, k)
                field, was = wordline.seed(c, L)
                self.assertTrue(was and c[field] == was and CA.unwritten(c, L))
                line = read_otherwise(c["words"], L)
                A.edit_chunk(v, i, k, {"words": line})
                now = self.seg_chunk(v, i, k)
                proposal = wordline.seed(now, L)[1]
                self.assertNotEqual(proposal, was)
                self.assertEqual((now["words"], now[field]), (line, proposal))
                self.assertTrue(CA.unwritten(now, L), now)
                blank, total = CA.gloss_state(v)
                self.assertEqual(blank, total)
                self.assertEqual(CA.check(v)[:2], ([], []))
                A.edit_chunk(v, i, k, {"words": ""})
                now = self.seg_chunk(v, i, k)
                self.assertEqual((now.get("words"), now.get(field) or ""), (None, ""))
                self.assertTrue(CA.unwritten(now, L))
                # a reading typed in the same save as the corrected line is
                # kept (on a fresh draft, whose chunk still holds the proposal)
                typed = {"ja": "てすとです", "zh": "ceshi"}[code]
                w = self.drafted_video(code, vid="tstRuleVx" + code)
                fi, fk = self.first_glossable(w, L)
                fresh = self.seg_chunk(w, fi, fk)
                self.assertEqual(fresh[field], wordline.seed(fresh, L)[1])
                A.edit_chunk(w, fi, fk, {"words": read_otherwise(fresh["words"], L),
                                         field: typed})
                now = self.seg_chunk(w, fi, fk)
                self.assertEqual(now.get(field), typed)
                self.assertFalse(CA.unwritten(now, L), now)
                # a written chunk's reading is its own
                i2, k2 = next((n, j) for n, sg in enumerate(A.read(v)["segments"])
                              if not sg.get("plain")
                              for j, x in enumerate(sg.get("chunks") or [])
                              if (n, j) != (i, k) and x.get("words"))
                A.edit_chunk(v, i2, k2, {"en": "a meaning"})
                c = self.seg_chunk(v, i2, k2)
                A.edit_chunk(v, i2, k2, {"words": read_otherwise(c["words"], L)})
                self.assertEqual(self.seg_chunk(v, i2, k2)[field], c[field])
                self.assertNotEqual(wordline.seed(self.seg_chunk(v, i2, k2), L)[1], c[field])

    def test_a_stray_kana_is_no_gloss_where_the_language_has_no_reading(self):
        """A "kana" on a chunk of a language with no reading -- the chat
        prompt's example shows one for every language, so a model may send
        it, and the add page takes it in.  Nothing shows it (the player's
        cloud and ✎ form have no reading line there), so it is no gloss:
        the chunk it is left alone on is blank, "delete gloss" takes the
        gloss off whether or not the page sends the kana with it, and the
        checker says it is there -- a warning, since files that have one
        exist and must go on loading."""
        for vj in sorted(glob.glob(os.path.join(FIX, "videos", "*", "*", "video.json"))):
            with io.open(vj, encoding="utf-8") as f:
                L = languages.get(json.load(f)["language"])
            if L.reading:
                continue
            with self.subTest(L.code):
                v = self.fresh(os.path.basename(os.path.dirname(vj)))
                shutil.copytree(os.path.dirname(vj), v)
                i, k = self.first_glossable(v, L)
                ann = A.read(v)
                was = dict(ann["segments"][i]["chunks"][k])
                self.assertTrue(CA.complete(was, L))
                ann["segments"][i]["chunks"][k]["kana"] = "a reading a model added"
                A.write(v, ann)
                errors, warnings, _n = CA.check(v)
                self.assertEqual(errors, [])
                self.assertIn("segment %d (start %s) chunk %d: kana on a chunk of a "
                              "language with no reading -- ignored"
                              % (i, ann["segments"][i]["start"], k), warnings)
                # the delete a page sends that knows the key is there
                A.edit_chunk(v, i, k, {f: "" for f in GLOSS})
                now = self.seg_chunk(v, i, k)
                self.assertFalse([f for f in GLOSS if f in now], now)
                self.assertEqual(CA.check(v)[0], [])
                # ...and the one a page sends that does not (the player's
                # before, which sent kana only where there is a reading): the
                # stray kana is left, and is no gloss
                A.write(v, ann)
                A.edit_chunk(v, i, k, deleted(GLOSS, L))
                now = self.seg_chunk(v, i, k)
                self.assertEqual({f: now[f] for f in GLOSS if f in now},
                                 {"kana": "a reading a model added"})
                self.assertTrue(CA.unwritten(now, L))
                self.assertEqual(CA.gloss_state(v)[0], 1)
                self.assertEqual(CA.check(v)[0], [], "not half glossed: nothing is missing")
                # where the language HAS a reading, a kana is a gloss
                self.assertFalse(CA.unwritten({"fa": "山", "kana": "やま"}, languages.get("ja")))


# --- where a chunk ends ------------------------------------------------------
class CutAndJoin(Scratch):
    """A cut or a join moves a boundary, and the gloss comes along as it was:
    blank, half glossed or complete, it is not the divide's to refuse."""

    def book_cut(self, p, k, pick=None):
        pv = X.divide_preview(p, k)
        self.assertTrue(pv["cuts"])
        cut = pv["cuts"][len(pv["cuts"]) // 2] if pick is None else pick(pv["cuts"])
        keep = lambda h: {f: x for f, x in cut[h].items() if f in X.FIELDS}
        return cut, keep("first"), keep("second")

    def video_cut(self, v, i, k):
        pv = A.divide_preview(v, i, k)
        self.assertTrue(pv["cuts"])
        cut = pv["cuts"][len(pv["cuts"]) // 2]
        keep = lambda h: {f: x for f, x in cut[h].items() if f in A.EDITABLE}
        return cut, keep("first"), keep("second")

    def own_reading(self, halves, L):
        """Every half blank, and in a words language carrying the reading of
        its own words -- or none, where its words have none to give."""
        for h in halves:
            self.assertTrue(CA.unwritten(h, L), h)
            field, proposal = wordline.seed(h, L)
            if field:
                self.assertEqual(h.get(field) or "", proposal, h)

    def test_a_blank_book_chunk_divides_into_two_blank_halves(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                p = self.drafted_book(code)
                pv = X.divide_preview(p, 0)
                for c in pv["cuts"]:
                    self.own_reading([c["first"], c["second"]], L)
                cut, a, b = self.book_cut(p, 0)
                X.split_chunk(p, 0, a, b)
                halves = X.read_chunks(p)[:2]
                self.assertEqual([h["fa"] for h in halves], [cut["a"], cut["b"]])
                self.own_reading(halves, L)
                # and joined, they are the blank chunk they came from
                X.merge_chunks(p, 0)
                one = self.chunk(p, 0)
                self.assertEqual(one["fa"], cut["a"] + L.word_sep + cut["b"])
                self.own_reading([one], L)

    def test_a_half_glossed_book_chunk_cuts_and_joins(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                p = self.drafted_book(code)
                X.edit_chunk(p, 0, {"voc": "a word"})
                cut, a, b = self.book_cut(p, 0)
                X.split_chunk(p, 0, dict(a, en="a meaning"), b)
                first, second = X.read_chunks(p)[:2]
                self.assertEqual((first["en"], second["en"]), ("a meaning", ""))
                # a half glossed and a blank one join into one half glossed
                X.edit_chunk(p, 1, deleted(second["fields"], L))
                X.merge_chunks(p, 0)
                one = self.chunk(p, 0)
                self.assertEqual(one["fa"], cut["a"] + L.word_sep + cut["b"])
                self.assertFalse(CA.unwritten(one, L))
                # and a complete chunk may be cut into a complete half and a
                # half left with no meaning
                q = self.fixture_book(code)
                k = self.complete_book_chunk(q, L)
                cut, a, b = self.book_cut(q, k)
                X.split_chunk(q, k, a, dict(b, en=""))
                self.assertEqual(self.chunk(q, k + 1)["en"], "")

    def test_a_blank_video_chunk_divides_into_two_blank_halves(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                v = self.drafted_video(code)
                i, k = self.first_glossable(v, L)
                pv = A.divide_preview(v, i, k)
                for c in pv["cuts"]:
                    self.own_reading([c["first"], c["second"]], L)
                cut, a, b = self.video_cut(v, i, k)
                A.split_chunk(v, i, k, a, b)
                halves = A.read(v)["segments"][i]["chunks"][k:k + 2]
                self.assertEqual([h["fa"] for h in halves], [cut["a"], cut["b"]])
                self.own_reading(halves, L)
                self.assertEqual(CA.check(v)[0], [])
                A.merge_chunks(v, i, k)
                self.own_reading([self.seg_chunk(v, i, k)], L)
                self.assertEqual(CA.check(v)[0], [])

    def test_a_half_glossed_video_chunk_cuts_and_joins(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                v = self.drafted_video(code)
                i, k = self.first_glossable(v, L)
                A.edit_chunk(v, i, k, {"voc": "a word"})
                cut, a, b = self.video_cut(v, i, k)
                A.split_chunk(v, i, k, dict(a, en="a meaning"), b)
                first, second = A.read(v)["segments"][i]["chunks"][k:k + 2]
                self.assertEqual((first.get("en"), second.get("en") or ""), ("a meaning", ""))
                A.edit_chunk(v, i, k + 1, deleted(GLOSS, L))
                A.merge_chunks(v, i, k)
                one = self.seg_chunk(v, i, k)
                self.assertFalse(CA.unwritten(one, L))
                # a complete chunk cut into a complete half and a meaningless one
                w = self.fixture_video(code)
                i, k = self.complete_video_chunk(w, L)
                cut, a, b = self.video_cut(w, i, k)
                A.split_chunk(w, i, k, a, dict(b, en=""))
                self.assertFalse(self.seg_chunk(w, i, k + 1).get("en"))


# --- the checkers, and the doors that ask them -------------------------------
class Checkers(Scratch):
    def test_check_batch_counts_the_blank_and_refuses_the_half_glossed(self):
        for code in CODES:
            with self.subTest(code):
                p = self.drafted_book(code)
                d = os.path.dirname(p)
                para = para_json(books.Book(d))
                n = sum(len(s["chunks"]) for s in para["ann"]["sentences"])
                rc, blank = self.check_batch(p, para)
                self.assertEqual(rc, 0, blank)
                self.assertIn("\n0 errors, 0 warnings, 1 note", blank)
                self.assertEqual(NOTE.findall(blank), [(str(n), str(n))])
                # half glossed: a vocabulary line and nothing else -- written,
                # and without the meaning every language requires
                half = json.loads(json.dumps(para))
                half["ann"]["sentences"][0]["chunks"][0]["voc"] = "a word"
                rc, out = self.check_batch(p, half)
                self.assertEqual(rc, 1 + sum(1 for f in required(books.Book(d).lang)
                                             if f != "en"
                                             and not half["ann"]["sentences"][0]["chunks"][0].get(f)),
                                 out)
                self.assertIn("ERROR empty en for ", out)
                self.assertEqual(NOTE.findall(out), [(str(n - 1), str(n))])
                # a leftover "draft": true is never read
                mp = os.path.join(d, "book.json")
                with io.open(mp, encoding="utf-8") as f:
                    meta = json.load(f)
                with io.open(mp, "w", encoding="utf-8") as f:
                    json.dump(dict(meta, draft=True), f, ensure_ascii=False)
                self.assertEqual(self.check_batch(p, para), (0, blank))
                self.assertEqual(self.check_batch(p, half), (rc, out))

    def test_check_annotations_counts_the_blank_and_refuses_the_half_glossed(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                v = self.drafted_video(code)
                blank_n, total = CA.gloss_state(v)
                self.assertTrue(0 < blank_n == total)
                self.assertEqual(CA.check(v)[:2], ([], []))
                rc, blank = self.cli(v)
                self.assertEqual(rc, 0, blank)
                self.assertEqual(VNOTE.findall(blank), [(str(total), str(total))])
                i, k = self.first_glossable(v, L)
                A.edit_chunk(v, i, k, {"voc": "a word"})
                errors = CA.check(v)[0]
                missing = [f for f in CA.required(self.seg_chunk(v, i, k), L)
                           if not (self.seg_chunk(v, i, k).get(f) or "").strip()]
                self.assertIn("en", missing)
                self.assertEqual(errors, ["segment %d (start %s) chunk %d: missing %r"
                                          % (i, A.read(v)["segments"][i]["start"], k, f)
                                          for f in missing])
                rc, half = self.cli(v)
                self.assertEqual(rc, 1, half)
                self.assertEqual(VNOTE.findall(half), [(str(total - 1), str(total))])
                # a leftover "draft": true is never read
                mp = os.path.join(v, "video.json")
                with io.open(mp, encoding="utf-8") as f:
                    meta = json.load(f)
                with io.open(mp, "w", encoding="utf-8") as f:
                    json.dump(dict(meta, draft=True), f, ensure_ascii=False, indent=2)
                self.assertEqual(self.cli(v), (1, half))
                self.assertEqual(CA.check(v)[0], errors)

    def test_the_bundle_door_notes_a_half_glossed_chunk_and_refuses_the_rest(self):
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                v = self.fixture_video(code)
                vid = os.path.basename(v)
                i, k = self.complete_video_chunk(v, L)
                notes = bundle._check_video(v, vid, code, "en")
                self.assertFalse(any("half glossed" in n for n in notes), notes)
                # a gloss deleted is a blank chunk, which is no note at all
                A.edit_chunk(v, i, k, deleted(GLOSS, L))
                notes = bundle._check_video(v, vid, code, "en")
                self.assertFalse(any("half glossed" in n for n in notes), notes)
                # half glossed: kept, and said
                A.edit_chunk(v, i, k, {"voc": "a word"})
                self.assertTrue(CA.check(v)[0], "an error to the checker")
                notes = bundle._check_video(v, vid, code, "en")
                self.assertEqual([n for n in notes if "half glossed" in n],
                                 ["1 chunk half glossed -- kept, not refused: finish it "
                                  "in the player"])
                # ...while any other error still refuses the video
                ann = A.read(v)
                ann["segments"][i]["chunks"][k]["col"] = "purple"
                A.write(v, ann)
                with self.assertRaises(bundle.BundleError) as cm:
                    bundle._check_video(v, vid, code, "en")
                self.assertIn("purple", str(cm.exception))
                self.assertNotIn("missing", str(cm.exception))

    # --- the warnings a blank chunk would make certain in advance -----------
    # A warning that cannot fail teaches its reader to skip warnings, so the
    # checkers keep quiet about what a chunk nobody has glossed is bound to
    # be: a whole sentence in one chunk, a paragraph with no word lines, a
    # text still unpointed.  Each silence is pinned here to its count of
    # warnings -- zero -- since "0 errors" alone would pass with every one of
    # them back.
    def test_every_fixture_transcript_drafts_into_a_video_that_checks_clean(self):
        """"Start it empty" over each fixture video's own transcript: every
        caption one blank chunk a sentence, often more than seven words --
        and check_annotations says nothing but the count note."""
        for vj in sorted(glob.glob(os.path.join(FIX, "videos", "*", "*", "video.json"))):
            src = os.path.dirname(vj)
            with io.open(vj, encoding="utf-8") as f:
                code = json.load(f)["language"]
            with self.subTest(code):
                with io.open(os.path.join(src, "transcript.txt"), encoding="utf-8") as f:
                    transcript = f.read()
                with proposing(code):
                    v = draft.video_from_transcript(transcript, code,
                                                    video_id=os.path.basename(src),
                                                    into=self.fresh("videos"))["dir"]
                blank, total = CA.gloss_state(v)
                self.assertTrue(0 < blank == total, (blank, total))
                rc, out = self.cli(v)
                self.assertEqual(rc, 0, out)
                self.assertIn("0 error(s), 0 warning(s)", out)
                self.assertEqual(VNOTE.findall(out), [(str(total), str(total))])

    def test_a_book_drafted_without_word_lines_is_not_warned_for_them(self):
        """A Japanese or Chinese draft made where no analyzer proposes a word
        line: a paragraph nobody has started glossing is not told it has no
        words -- only one somebody has."""
        for code in ("ja", "zh"):
            with self.subTest(code):
                L = languages.get(code)
                with patch.object(draft.words, "line", lambda fa, code, reading="": ""):
                    r = draft.book_from_text(" ".join(TEXT[code]), code, "t",
                                             slug="t-" + code, into=self.fresh("books"))
                p = os.path.join(r["dir"], "ch1.tex")
                self.assertFalse([c for c in X.read_chunks(p) if c["words"]])
                rc, out = self.check_batch(p)
                self.assertEqual(rc, 0, out)
                self.assertIn("\n0 errors, 0 warnings, 1 note", out)
                self.assertNotIn("has words", out)
                # started, the paragraph is told
                X.edit_chunk(p, 0, {f: "a gloss" for f in required(L)})
                rc, out = self.check_batch(p)
                self.assertEqual(rc, 0, out)
                self.assertIn("no chunk of this paragraph has words", out)
                self.assertIn("\n0 errors, 1 warnings, 1 note", out)

    def test_a_blank_chapter_leaves_the_glossed_ones_as_they_were(self):
        """A chapter added to a finished edition (/books/add/, "Add to a book
        already here") is its text as it stands, every chunk blank.  Its
        paragraph is not warned about the pointing and the seams a gloss has
        still to settle, and the finished chapter's paragraph is warned about
        exactly what it was before -- the blank chunks are not counted into
        the book's own pointing either (check_batch's corpus).  Persian is
        where those warnings are; every edition is asked.  Added twice, cut
        both ways the add page offers: one chunk a sentence, and by phrase --
        where a chunk ends inside its sentence, at a seam an ezafe could be
        missing from once it is glossed."""
        for bj in sorted(glob.glob(os.path.join(FIX, "books", "*", "*", "book.json"))):
            rel = os.path.relpath(os.path.dirname(bj), os.path.join(FIX, "books"))
            with io.open(bj, encoding="utf-8") as f:
                code = json.load(f)["language"]
            with self.subTest(rel):
                d = self.fresh(os.path.basename(rel))
                shutil.copytree(os.path.dirname(bj), d, ignore=shutil.ignore_patterns(
                    "reader", "*.pdf", "*.aux", "*.log", "*.toc", "*.out"))
                p = os.path.join(d, "ch1.tex")
                glossed = self.check_batch(p)
                with io.open(os.path.join(d, "source", "paras", "ch1_p00.txt"),
                             encoding="utf-8") as f:
                    text = f.read()
                for chapter, how in enumerate(chunker.WAYS, 2):
                    with proposing(code):
                        draft.add_to_book(d, text, how=how)
                    book = books.Book(d)
                    para = para_json(book, chapter=chapter)
                    n = sum(len(s["chunks"]) for s in para["ann"]["sentences"])
                    self.assertTrue(n and all(CA.unwritten(c, book.lang)
                                              for s in para["ann"]["sentences"]
                                              for c in s["chunks"]), how)
                    rc, out = self.check_batch(p, para)
                    self.assertEqual(rc, 0, out)
                    self.assertIn("\n0 errors, 0 warnings, 1 note", out, how)
                    self.assertEqual(NOTE.findall(out), [(str(n), str(n))])
                    self.assertEqual(self.check_batch(p), glossed,
                                     "the finished chapter's paragraph, word for word")
                if book.lang.code == "fa":
                    self.assertIn("POINTING", glossed[1], "the warnings are there to keep")


# --- lib/draft.py and verify_book --------------------------------------------
class Drafting(Scratch):
    def test_a_draft_writes_no_flag(self):
        for code in CODES:
            with self.subTest(code), proposing(code):
                r = draft.book_from_text(" ".join(TEXT[code]), code, "t", slug="t")
                self.assertNotIn("draft", r)
                self.assertNotIn("draft", json.loads(r["files"]["book.json"]))
                v = draft.video_from_transcript("0:00\n%s\n" % TEXT[code][0], code,
                                                video_id="tstRuleVd" + code)
                self.assertNotIn("draft", v)
                self.assertNotIn("draft", json.loads(v["files"]["video.json"]))
                for text in list(r["files"].values()) + list(v["files"].values()):
                    self.assertNotIn('"draft"', text)

    def test_a_video_id_is_one_video_in_every_language(self):
        into = self.fresh("videos")
        vid = "tstRuleVdAB"
        transcript = {c: "0:00\n%s\n" % TEXT[c][0] for c in CODES}
        with proposing("fa"):
            first = draft.video_from_transcript(transcript["fa"], "fa", video_id=vid, into=into)
        self.assertTrue(os.path.isfile(os.path.join(first["dir"], "annotations.json")))
        for code in CODES:
            with self.subTest(code):
                L = languages.get(code)
                with self.assertRaises(ValueError) as cm, proposing(code):
                    draft.video_from_transcript(transcript[code], code, video_id=vid, into=into)
                said = str(cm.exception)
                self.assertIn("already exists", said)
                self.assertEqual("one id cannot be two videos" in said, code != "fa", said)
                if code != "fa":
                    self.assertFalse(os.path.exists(os.path.join(into, L.folder, vid)),
                                     "and nothing is written")
        self.assertEqual(sorted(os.listdir(into)), [languages.get("fa").folder])

    def test_verify_book_reads_an_indented_chunk(self):
        for code in CODES:
            with self.subTest(code):
                p = self.fixture_book(code)
                d = os.path.dirname(p)
                verify = lambda: subprocess.run(
                    [sys.executable, os.path.join(LIB, "verify_book.py"), "--book", d],
                    cwd=d, capture_output=True, text=True).stdout
                flat = verify()
                built = re.search(r"(\d+) paragraphs built, \1 reproduce", flat)
                self.assertTrue(built, flat)
                with io.open(p, encoding="utf-8") as f:
                    tex = f.read()
                indented = re.sub(r"^(\\(?:parnum|ch[a-z]*)\{)", r"  \1", tex, flags=re.M)
                self.assertNotEqual(indented, tex)
                with io.open(p, "w", encoding="utf-8") as f:
                    f.write(indented)
                self.assertEqual(verify().splitlines()[-1], flat.splitlines()[-1])
                # ...and still sees a letter changed on an indented line
                c = X.read_chunks(p)[1]
                a, b = c["span"]
                call = indented[a:b].replace("{%s}" % c["fa"], "{%s}" % (c["fa"] + c["fa"][-1]), 1)
                self.assertNotEqual(call, indented[a:b])
                with io.open(p, "w", encoding="utf-8") as f:
                    f.write(indented[:a] + call + indented[b:])
                self.assertIn(" 1 mismatched", verify())


if __name__ == "__main__":
    unittest.main()
