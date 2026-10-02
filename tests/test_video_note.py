#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The note a model leaves on a video's phrase is the person's to edit
(a0.4.2, W11).

    python3 -m unittest discover -s tests -p test_video_note.py

A phrase's `note` is the author's aside under the meaning -- "what the
automatic transcript really heard, a cultural point" -- and an LLM that
glosses a video leaves one when something needs saying.  It used to be the one
field of the gloss no page could change: a note about a slip in the
transcript stayed on the phrase after the transcript was mended, and the only
way to take it off was the file.  What is proved here, at the door the ✎ form
writes through (youtube/lib/annwrite.py):

  * a note is set, changed, trimmed and taken off in every fixture video's
    language, written where the field order puts it, and the file lands as the
    edit a hand would have made: what an empty box takes off leaves the file
    byte for byte as it was;
  * THE OWNER'S CASE: a note about a slip in the transcript, the phrase mended
    through the `free` tick, the note then emptied -- and the file's diff is
    the one line the note was on;
  * an edit that is refused writes nothing, and `plain` stays refused, with
    its reason;
  * THE TRAP: the divide sheet (cut, join) draws no note box, so a divide that
    sends no note must leave every note it touches where chunkdiv put it --
    the cut's on its first half, the join's both, joined with "; " -- and a
    divide that does send one is the page's say, an empty one taking it off.

The fixtures are copied into a temporary directory and never written.
Standard library only.
"""
import difflib
import glob
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YT_LIB = os.path.join(ROOT, "youtube", "lib")
for _p in (os.path.join(ROOT, "lib"), YT_LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import annwrite as A             # noqa: E402
import check_annotations as CA   # noqa: E402
import chunkdiv                  # noqa: E402
import languages                 # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "videos")
EVERY = sorted(glob.glob(os.path.join(FIX, "*", "*", "video.json")))
# the boxes the divide sheet draws, and so all it posts (the colour it posts
# too, when the phrase has one: tests/test_wordvideo.py says the same)
SHEET = ("fa", "kana", "tr", "voc", "en")


def raw(path):
    with open(path, "rb") as f:
        return f.read()


def text_of(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def language_of(vj):
    return json.loads(text_of(vj))["language"]


def lines_changed(before, after):
    """The lines a diff of the two files has, as git shows them: ['-<line>',
    '+<line>', ...] and nothing around them."""
    return [x for x in difflib.unified_diff(
        before.decode("utf-8").splitlines(), after.decode("utf-8").splitlines(),
        lineterm="", n=0) if x[:1] in "+-" and x[:3] not in ("+++", "---")]


class Scratch(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = td.name
        self.n = 0

    def copy(self, vj):
        """A copy of the fixture video whose video.json is `vj` -> its folder"""
        self.n += 1
        d = os.path.join(self.td, "%d" % self.n, os.path.basename(os.path.dirname(vj)))
        os.makedirs(os.path.dirname(d))
        shutil.copytree(os.path.dirname(vj), d)
        return d

    def persian(self):
        return self.copy(os.path.join(FIX, "persian", "fA6bK2mQ8sT", "video.json"))

    def where(self, v, divisible=False):
        """(segment, chunk) of the first phrase of the language -- an aside
        marked plain is none -- or the first one that divides, and has a phrase
        after it"""
        L = A.video_language(v, A._meta(v), A.read(v))
        for i, sg in enumerate(A.read(v)["segments"]):
            chunks = sg.get("chunks") or []
            for k, c in enumerate(chunks):
                if sg.get("plain") or c.get("plain"):
                    continue
                if not divisible:
                    return i, k
                if chunkdiv.cuts(c["fa"], L) and k + 1 < len(chunks):
                    return i, k
        self.fail("no such phrase in %s" % v)

    def chunk(self, v, i, k):
        return A.read(v)["segments"][i]["chunks"][k]

    def path(self, v):
        return os.path.join(v, "annotations.json")


class TheNoteIsThePersons(Scratch):
    def test_a_note_is_set_trimmed_changed_and_taken_off_in_every_language(self):
        for vj in EVERY:
            code = language_of(vj)
            with self.subTest(code):
                v = self.copy(vj)
                i, k = self.where(v)
                if self.chunk(v, i, k).get("note"):
                    self.skipTest("this fixture's first phrase has a note already")
                before, errors = raw(self.path(v)), CA.check(v)[0]
                # set, and trimmed: a text box hands back the spaces it was left with
                got = A.edit_chunk(v, i, k, {"note": "  heard one word, said another  "})
                self.assertEqual(got["note"], "heard one word, said another")
                self.assertEqual(self.chunk(v, i, k)["note"], "heard one word, said another")
                self.assertEqual(CA.check(v)[0], errors, "the checker has nothing against it")
                # written where the field order puts it, after the meaning: every
                # key a phrase has stays in the order CHUNK_FIELDS gives them
                keys = [x for x in self.chunk(v, i, k) if x in CA.CHUNK_FIELDS]
                self.assertEqual(keys, sorted(keys, key=CA.CHUNK_FIELDS.index), keys)
                # the note's own line, and at most the comma JSON asks of the line
                # above it when the note is the last thing the phrase says
                added = lines_changed(before, raw(self.path(v)))
                self.assertLessEqual(len(added), 3, added)
                self.assertTrue([x for x in added if x[0] == "+" and
                                 '"note": "heard one word, said another"' in x], added)
                self.assertFalse([x for x in added if x[0] == "-" and '"note"' in x], added)
                # changed, in place
                at = list(self.chunk(v, i, k)).index("note")
                A.edit_chunk(v, i, k, {"note": "something else"})
                self.assertEqual(self.chunk(v, i, k)["note"], "something else")
                self.assertEqual(list(self.chunk(v, i, k)).index("note"), at)
                # the same words again: the file is the file it was
                kept = raw(self.path(v))
                A.edit_chunk(v, i, k, {"note": "something else"})
                self.assertEqual(raw(self.path(v)), kept)
                # taken off, by an empty box (and by null, which is the page's
                # other way of saying it): the key goes and the file is the
                # one the phrase started with -- indent, escapes, last newline
                for empty in ("", "   ", None):
                    A.edit_chunk(v, i, k, {"note": "again"})
                    got = A.edit_chunk(v, i, k, {"note": empty})
                    self.assertNotIn("note", got)
                    self.assertNotIn("note", self.chunk(v, i, k))
                    self.assertEqual(raw(self.path(v)), before, repr(empty))
                self.assertEqual(CA.check(v)[0], errors)

    def test_a_note_lands_before_the_colour_and_the_mark_it_has_not_got_yet(self):
        v = self.persian()
        i, k = self.where(v)
        A.edit_chunk(v, i, k, {"col": "blue"})
        A.edit_chunk(v, i, k, {"note": "a word the transcript lost"})
        keys = [x for x in self.chunk(v, i, k)]
        self.assertEqual(keys[-2:], ["note", "col"], keys)

    def test_the_owners_case_the_note_mended_away_is_one_line_of_the_diff(self):
        """A video whose transcript has a slip in it, and a note an LLM left to
        say so.  The phrase is mended through the `free` tick -- the transcript
        is what YouTube heard, and stays so -- and now the note is stale.  It is
        emptied in the form, and the file is the file it was but for that line."""
        v = self.persian()
        i, k = 1, 2
        t = os.path.join(v, "transcript.txt")
        was = text_of(t)
        self.assertIn("سلام، ببخشید سیب چند است", was)
        # what YouTube heard: سیر (garlic) for سیب (apple); the LLM's gloss followed the
        # transcript, and its note says what the speaker really said
        with io.open(t, "w", encoding="utf-8") as f:
            f.write(was.replace("ببخشید سیب", "ببخشید سیر"))
        ann = A.read(v)
        ann["segments"][i]["text"] = "سلام، ببخشید سیر چند است"
        ann["segments"][i]["chunks"][k]["fa"] = "سیر چند است"
        ann["segments"][i]["chunks"][k]["note"] = "the transcript heard سیر (garlic); the speaker says سیب (apple)"
        A.write(v, ann)
        self.assertEqual(CA.check(v)[0], [])
        # mended through the form's `free` tick: refused without it, written with it
        with self.assertRaises(ValueError) as cm:
            A.edit_chunk(v, i, k, {"fa": "سیب چند است"})
        self.assertIn("reproduce", str(cm.exception))
        A.edit_chunk(v, i, k, {"fa": "سیب چند است", "free": True})
        self.assertEqual(self.chunk(v, i, k)["fa"], "سیب چند است")
        self.assertIn("note", self.chunk(v, i, k), "the note is stale, and still there")
        before = raw(self.path(v))
        # ...and the note emptied in the form
        A.edit_chunk(v, i, k, {"note": ""})
        after = raw(self.path(v))
        gone = lines_changed(before, after)
        self.assertEqual(len(gone), 1, gone)
        self.assertTrue(gone[0].startswith('-') and '"note": "the transcript heard' in gone[0], gone)
        self.assertNotIn("note", self.chunk(v, i, k))
        self.assertEqual(CA.check(v)[0], [])
        # the transcript was never touched by any of it
        self.assertIn("سیر چند است", text_of(t))

    def test_a_refused_edit_writes_nothing(self):
        v = self.persian()
        i, k = self.where(v)
        before = raw(self.path(v))
        for fields, why in (({"note": 7}, "note must be text, not int"),
                            ({"note": ["a"]}, "note must be text, not list"),
                            ({"note": {"a": 1}}, "note must be text, not dict"),
                            ({"note": "kept?", "col": "purple"}, "purple")):
            with self.subTest(fields):
                with self.assertRaises(ValueError) as cm:
                    A.edit_chunk(v, i, k, fields)
                self.assertIn(why, str(cm.exception))
                self.assertEqual(raw(self.path(v)), before, "a refusal writes nothing")

    def test_plain_stays_refused_with_its_reason_and_a_mistyped_key_is_answered(self):
        v = self.persian()
        i, k = self.where(v)
        before = raw(self.path(v))
        with self.assertRaises(ValueError) as cm:
            A.edit_chunk(v, i, k, {"plain": True})
        said = str(cm.exception)
        self.assertIn("cannot set 'plain' on a chunk", said)
        self.assertIn("note", said, "the fields a page may set name it")
        self.assertIn("decides whether a phrase is asked for a gloss at all", said)
        with self.assertRaises(ValueError) as cm:
            A.edit_chunk(v, i, k, {"nope": "x"})
        self.assertIn("cannot set 'nope' on a chunk", str(cm.exception))
        self.assertNotIn("gloss at all", str(cm.exception), "plain's reason is plain's")
        self.assertEqual(raw(self.path(v)), before)

    def test_a_phrase_nobody_has_glossed_can_carry_a_note_and_stays_unglossed(self):
        """The note is no gloss: a phrase with only a note says nothing is
        written (check_annotations.unwritten), exactly as `delete gloss` leaves
        it -- and the checker has nothing against it."""
        v = self.copy(os.path.join(FIX, "italian", "kL9mN1oP3qR", "video.json"))
        i, k = self.where(v)
        L = A.video_language(v, A._meta(v), A.read(v))
        A.edit_chunk(v, i, k, {f: "" for f in ("tr", "voc", "en", "kana")})
        self.assertTrue(CA.unwritten(self.chunk(v, i, k), L))
        A.edit_chunk(v, i, k, {"note": "no gloss yet, and a word to say about it"})
        self.assertTrue(CA.unwritten(self.chunk(v, i, k), L))
        self.assertEqual(CA.check(v)[0], [])


class CutAndJoinCarryTheNote(Scratch):
    """What the divide sheet posts is SHEET, never a note: the sheet has no box
    for it.  So the note a cut or a join touches has to come through unasked
    (annwrite._CARRIED) -- and a page that does name one is heard."""

    def posted(self, ch, **more):
        return dict({f: ch.get(f, "") for f in SHEET}, **more)

    def divisible(self, code):
        vj = next(x for x in EVERY if language_of(x) == code)
        v = self.copy(vj)
        return v, self.where(v, divisible=True)

    def test_a_cut_leaves_the_note_on_its_first_half_in_every_language(self):
        for vj in EVERY:
            code = language_of(vj)
            with self.subTest(code):
                v = self.copy(vj)
                try:
                    i, k = self.where(v, divisible=True)
                except AssertionError:
                    self.skipTest("nothing in this fixture divides")
                A.edit_chunk(v, i, k, {"note": "said in the middle"})
                pv = A.divide_preview(v, i, k)
                self.assertEqual(pv["cuts"][0]["first"]["note"], "said in the middle")
                self.assertNotIn("note", pv["cuts"][0]["second"])
                cut = pv["cuts"][0]
                A.split_chunk(v, i, k, self.posted(cut["first"]), self.posted(cut["second"]))
                a, b = self.chunk(v, i, k), self.chunk(v, i, k + 1)
                self.assertEqual(a.get("note"), "said in the middle")
                self.assertNotIn("note", b)
                # a cut hands the second half a meaning nobody has typed yet --
                # the middle of the work, and the only thing the checker may say
                self.assertEqual([e for e in CA.check(v)[0] if "missing" not in e], [])

    def test_a_join_joins_the_notes_with_a_semicolon_in_every_language(self):
        for vj in EVERY:
            code = language_of(vj)
            with self.subTest(code):
                v = self.copy(vj)
                try:
                    i, k = self.where(v, divisible=True)
                except AssertionError:
                    self.skipTest("nothing in this fixture divides")
                A.edit_chunk(v, i, k, {"note": "first"})
                A.edit_chunk(v, i, k + 1, {"note": "second"})
                pv = A.divide_preview(v, i, k)
                self.assertEqual(pv["merge"]["fields"]["note"], "first; second")
                # the sheet posts the joined chunk's boxes and no note
                A.merge_chunks(v, i, k, self.posted(pv["merge"]["fields"]))
                self.assertEqual(self.chunk(v, i, k)["note"], "first; second")
                self.assertEqual(CA.check(v)[0], [])
                # and a join the sheet does not post at all (the command line's
                # and the tests' way) is the proposal whole
                w = self.copy(vj)
                A.edit_chunk(w, i, k, {"note": "first"})
                A.merge_chunks(w, i, k)
                self.assertEqual(self.chunk(w, i, k)["note"], "first")

    def test_a_page_that_names_the_note_is_heard(self):
        v, (i, k) = self.divisible("it")
        A.edit_chunk(v, i, k, {"note": "to be moved"})
        cut = A.divide_preview(v, i, k)["cuts"][0]
        # taken off the first half by the page, and written on the second
        A.split_chunk(v, i, k, self.posted(cut["first"], note=""),
                      self.posted(cut["second"], note="  now on the second  "))
        self.assertNotIn("note", self.chunk(v, i, k))
        self.assertEqual(self.chunk(v, i, k + 1)["note"], "now on the second")
        # a join whose joined note the page has emptied
        A.edit_chunk(v, i, k, {"note": "x"})
        pv = A.divide_preview(v, i, k)
        A.merge_chunks(v, i, k, self.posted(pv["merge"]["fields"], note=""))
        self.assertNotIn("note", self.chunk(v, i, k))
        self.assertEqual(CA.check(v)[0], [])

    def test_a_divide_still_refuses_plain_and_the_flag_is_still_carried(self):
        v, (i, k) = self.divisible("it")
        cut = A.divide_preview(v, i, k)["cuts"][0]
        before = raw(self.path(v))
        with self.assertRaises(ValueError) as cm:
            A.split_chunk(v, i, k, self.posted(cut["first"], plain=True),
                          self.posted(cut["second"]))
        self.assertIn("cannot set 'plain' on a chunk", str(cm.exception))
        self.assertIn("gloss at all", str(cm.exception))
        self.assertEqual(raw(self.path(v)), before)


if __name__ == "__main__":
    unittest.main()
