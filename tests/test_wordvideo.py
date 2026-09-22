#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A video divided into words: the checkers, the part tools and the writer.

    python3 -m unittest discover -s tests -p test_wordvideo.py

The fixture videos carry no words, and stay that way for tests/smoke.py's
round trips; every test here works on a temporary copy of the Japanese or
the Chinese one with each chunk given its word line (JA and ZH below, whose
readings say what the chunk's own kana or tr says).  Standard library only,
and system python3 is enough: nothing here asks an analyzer for a line.
"""
import io
import json
import os
import shutil
import subprocess
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
import wordline                  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "videos")

# every chunk's text -> its word line
JA = {
    "こんにちは、": "こんにちは 、",
    "みなさん": "みなさん",
    "今日は": "今日(きょう) は",
    "天気が": "天気(てんき) が",
    "いいですね": "いい です ね",
    "私は": "私(わたし) は",
    "毎朝": "毎朝(まいあさ)",
    "コーヒーを": "コーヒー を",
    "飲みます": "飲みます(のみます)",
    "駅まで": "駅(えき) まで",
    "歩いて": "歩いて(あるいて)",
    "十分": "十分(じゅっぷん)",
    "かかります": "かかります",
    "この本は": "この 本(ほん) は",
    "いくらですか": "いくら です か",
    "少し": "少し(すこし)",
    "高いですね": "高い(たかい) です ね",
    "ありがとうございました": "ありがとう ございました",
}
ZH = {
    "你好，": "你(nǐ) 好(hǎo) ，",
    "我想要一杯茶": "我(wǒ) 想要(xiǎng yào) 一(yì) 杯(bēi) 茶(chá)",
    "好的，": "好的(hǎo de) ，",
    "你要什么茶": "你(nǐ) 要(yào) 什么(shénme) 茶(chá)",
    "绿茶，": "绿茶(lǜ chá) ，",
    "谢谢": "谢谢(xièxie)",
    "请等一下，": "请(qǐng) 等(děng) 一下(yíxià) ，",
    "两分钟就好": "两(liǎng) 分钟(fēnzhōng) 就(jiù) 好(hǎo)",
    "多少钱": "多少(duōshao) 钱(qián)",
    "十块钱，": "十(shí) 块(kuài) 钱(qián) ，",
}

# the boxes the divide sheet shows, and so all it posts
SHEET = ("fa", "kana", "tr", "voc", "en")


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(path, obj, indent=1):
    """merge_parts.py's shape, which is the fixtures' own."""
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def raw(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def sheet(chunk, **kw):
    """What the divide sheet posts for a chunk: its boxes, blanks included,
    and never the word line."""
    out = {k: chunk.get(k, "") for k in SHEET}
    out.update(kw)
    return out


def with_words(chunk, table):
    """The chunk with its line slotted in straight after fa."""
    out = {}
    for k, v in chunk.items():
        out[k] = v
        if k == "fa" and v in table:
            out["words"] = table[v]
    return out


class Worded(unittest.TestCase):
    """A temporary copy of one fixture video, every chunk divided into words:
    annotations.json and parts/01.json alike."""
    FOLDER, ID, TABLE = "japanese", "aB3dE5fG7hI", JA

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = os.path.join(td.name, self.ID)
        shutil.copytree(os.path.join(FIX, self.FOLDER, self.ID), self.d)
        self.ap = os.path.join(self.d, "annotations.json")
        self.pp = os.path.join(self.d, "parts", "01.json")
        ann = load(self.ap)
        for sg in ann["segments"]:
            if sg.get("chunks"):
                sg["chunks"] = [with_words(c, self.TABLE) for c in sg["chunks"]]
        dump(self.ap, ann)
        batch = load(self.pp)
        for sg in batch:
            sg["chunks"] = [with_words(c, self.TABLE) for c in sg["chunks"]]
        dump(self.pp, batch)
        self.L = languages.get(ann["language"])
        self.reading = "kana" if self.L.reading else "tr"
        # the first caption of two chunks or more, which every test works on
        self.si = next(i for i, sg in enumerate(ann["segments"])
                       if len(sg.get("chunks") or []) >= 2)
        self.where = "segment %d (start %s) chunk " % (
            self.si, ann["segments"][self.si]["start"])

    def ann(self):
        return load(self.ap)

    def chunks(self, seg=None):
        return self.ann()["segments"][self.si if seg is None else seg]["chunks"]

    def change(self, k, **fields):
        """Set fields on chunk k of the caption, straight in the file."""
        ann = self.ann()
        ch = ann["segments"][self.si]["chunks"][k]
        for f, v in fields.items():
            if v is KeyError:
                ch.pop(f, None)
            else:
                ch[f] = v
        dump(self.ap, ann)

    def meta(self, **kw):
        mp = os.path.join(self.d, "video.json")
        m = load(mp)
        m.update(kw)
        dump(mp, m, indent=2)

    def check(self):
        errors, warnings, _counts = CA.check(self.d)
        return errors, warnings

    def stale(self, line):
        """A line that no longer gives its chunk's text back."""
        return line + " 了"


# --- check_annotations ------------------------------------------------------
class Checks:
    def test_the_key_stands_after_fa(self):
        self.assertEqual(CA.CHUNK_FIELDS[:2], ("fa", "words"))

    def test_a_worded_video_checks_clean(self):
        self.assertEqual(self.check(), ([], []))

    def test_words_that_do_not_give_the_text_back(self):
        self.change(0, words=self.stale(self.chunks()[0]["words"]))
        errors, _w = self.check()
        self.assertEqual(len(errors), 1, errors)
        self.assertTrue(errors[0].startswith(
            self.where + "0: the words do not reproduce the text"), errors)

    def test_a_blank_line_and_a_line_that_is_not_text(self):
        for bad, said in (("", "words is empty"), ("  ", "words is empty"),
                          (["a", "b"], "words must be text"),
                          (None, "words must be text"),
                          ("x)", "closes a parenthesis it never opened"),
                          ("x(", "opens a reading")):
            self.change(0, words=bad)
            errors, _w = self.check()
            self.assertEqual(len(errors), 1, (bad, errors))
            self.assertTrue(errors[0].startswith(self.where + "0: "), errors)
            self.assertIn(said, errors[0], bad)

    def test_a_plain_chunk_carries_no_words(self):
        self.change(0, plain=True)
        errors, _w = self.check()
        self.assertEqual(errors, [self.where + "0: a chunk marked plain carries "
                                  "no words"])
        # before the plain chunk's early return, whatever the line is
        self.change(0, words="")
        self.assertEqual(len(self.check()[0]), 1)
        self.change(0, words=KeyError)
        self.assertEqual(self.check()[0], [])

    def test_a_draft_is_held_to_its_words(self):
        self.meta(draft=True)
        self.change(0, kana="", tr="", voc="", en="")
        errors, warnings = self.check()
        self.assertEqual(errors, [], "an unwritten chunk with words is a "
                                     "draft's chunk")
        self.assertEqual(warnings, [], "a blank reading has nothing to compare")
        self.assertEqual(CA.draft_state(self.d)[1], 1,
                         "and its words do not make it a written one")
        self.change(0, words=self.stale(self.chunks()[0]["words"]))
        errors, _w = self.check()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(self.where + "0: the words do not reproduce", errors[0])

    def test_a_draft_half_written_is_said_and_not_refused(self):
        """THE ROUND TRIP HAS TO CLOSE.  The player's own editor writes a
        meaning into a blank chunk of a draft and leaves the transliteration
        for the next pass -- annwrite checks an edit without the draft flag
        on purpose, so that edit stands -- and a video refused for it here
        could never come back through the bundle door it had gone out of."""
        self.meta(draft=True)
        self.change(0, kana="", tr="", voc="", en="")
        self.assertEqual(self.check(), ([], []), "a blank chunk is asked for nothing")
        # ...now somebody types the meaning, and nothing else
        A.edit_chunk(self.d, self.si, 0, {"en": "a meaning, and nothing else"})
        errors, warnings = self.check()
        self.assertEqual(errors, [], "half written is not a refusal in a draft")
        said = [w for w in warnings if "still a draft" in w]
        self.assertTrue(said, warnings)
        self.assertTrue(all(w.startswith(self.where + "0: missing ") for w in said), said)
        # and the flag is what holds it up: without it, every one is an error
        self.meta(draft=False)
        errors, _w = self.check()
        self.assertTrue(any("missing" in e for e in errors), errors)
        self.assertTrue(all("still a draft" not in e for e in errors), errors)

    def test_a_reading_that_disagrees_warns_and_reorders_quiets_it(self):
        ch = self.chunks()[1]
        self.change(1, **{self.reading: ch[self.reading] + self.OTHER})
        errors, warnings = self.check()
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        self.assertTrue(warnings[0].startswith(self.where + "1: the words read"),
                        warnings)
        self.meta(reorders=True)
        self.assertEqual(self.check(), ([], []))
        # and a text read out of order still has to give its text back
        self.change(1, words=self.stale(ch["words"]))
        self.assertEqual(len(self.check()[0]), 1)

    def test_check_part_and_merge_parts(self):
        tool = lambda name, *a: subprocess.run(
            [sys.executable, os.path.join(YT_LIB, name), self.d] + list(a),
            capture_output=True, text=True, cwd=ROOT)
        r = tool("check_part.py", self.pp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 error(s), 0 warning(s)", r.stdout)

        batch = load(self.pp)
        good = json.dumps(batch, ensure_ascii=False)
        start = batch[0]["start"]
        where = "01.json [0] (start %s) chunk " % start

        batch[0]["chunks"][0]["words"] = self.stale(batch[0]["chunks"][0]["words"])
        dump(self.pp, batch)
        r = tool("check_part.py", self.pp)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("ERROR: %s0: the words do not reproduce the text" % where,
                      r.stdout)

        batch = json.loads(good)
        batch[0]["chunks"][0]["plain"] = True
        dump(self.pp, batch)
        r = tool("check_part.py", self.pp)
        self.assertIn("ERROR: %s0: a chunk marked plain carries no words" % where,
                      r.stdout)

        batch = json.loads(good)
        batch[0]["chunks"][1][self.reading] += self.OTHER
        dump(self.pp, batch)
        r = tool("check_part.py", self.pp)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("warning: %s1: the words read" % where, r.stdout)
        self.meta(reorders=True)
        r = tool("check_part.py", self.pp)
        self.assertIn("0 error(s), 0 warning(s)", r.stdout,
                      "check_part reads video.json's reorders")

        # merge_parts copies the chunks whole, words and all
        dump(self.pp, json.loads(good))
        os.unlink(self.ap)
        r = tool("merge_parts.py")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        got = [(c["fa"], c.get("words")) for sg in self.ann()["segments"]
               for c in sg.get("chunks") or []]
        self.assertTrue(got)
        self.assertEqual(got, [(fa, self.TABLE[fa]) for fa, _w in got])
        r = tool("check_annotations.py")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 error(s), 0 warning(s)", r.stdout)


# --- annwrite -----------------------------------------------------------------
class Writes:
    def test_words_is_editable_and_lands_after_fa(self):
        self.assertIn("words", A.EDITABLE)
        line = self.chunks()[1]["words"]
        A.edit_chunk(self.d, self.si, 1, {"words": ""})
        self.assertNotIn("words", self.chunks()[1], "an empty line removes the key")
        got = A.edit_chunk(self.d, self.si, 1, {"words": " %s " % line})
        self.assertEqual(list(got)[:3], ["fa", "words", self.reading])
        self.assertEqual(self.chunks()[1]["words"], line)

    def test_a_stale_line_is_refused_and_nothing_is_written(self):
        before = raw(self.ap)
        with self.assertRaises(ValueError) as cm:
            A.edit_chunk(self.d, self.si, 0,
                         {"words": self.stale(self.chunks()[0]["words"])})
        self.assertIn(self.where + "0: the words do not reproduce the text",
                      str(cm.exception))
        self.assertEqual(raw(self.ap), before)

    def test_an_fa_edit_that_leaves_the_words_behind_is_refused(self):
        ch = self.chunks()[0]
        before = raw(self.ap)
        with self.assertRaises(ValueError) as cm:
            A.edit_chunk(self.d, self.si, 0, {"fa": ch["fa"] + "了"})
        said = str(cm.exception)
        # check_chunk's own sentence, from the edit's own check round
        self.assertIn(self.where + "0: the words do not reproduce the text", said)
        self.assertEqual(raw(self.ap), before)
        # which is the line's doing: without one, only the caption complains
        A.edit_chunk(self.d, self.si, 0, {"words": ""})
        with self.assertRaises(ValueError) as cm:
            A.edit_chunk(self.d, self.si, 0, {"fa": ch["fa"] + "了"})
        self.assertNotIn("the words do not", str(cm.exception))
        self.assertIn("chunks do not reproduce the text", str(cm.exception))
        # and an fa edit that keeps the letters keeps the line true
        A.edit_chunk(self.d, self.si, 0, {"words": ch["words"]})
        spaced = ch["fa"][:1] + " " + ch["fa"][1:]
        A.edit_chunk(self.d, self.si, 0, {"fa": spaced})
        self.assertEqual((self.chunks()[0]["fa"], self.chunks()[0]["words"]),
                         (spaced, ch["words"]))
        self.assertEqual(self.check()[0], [])

    def test_the_preview_divides_and_joins_the_words(self):
        cs = self.chunks()
        pv = A.divide_preview(self.d, self.si, 0)
        self.assertTrue(pv["cuts"])
        for c in pv["cuts"]:
            for half, text in (("first", c["a"]), ("second", c["b"])):
                self.assertEqual(list(c[half])[:2], ["fa", "words"])
                bad, _doubt = wordline.check(text, c[half]["words"], self.L)
                self.assertEqual(bad, [], (c["at"], half, c[half]["words"]))
        self.assertEqual(pv["merge"]["fields"]["words"],
                         wordline.join_lines(cs[0]["words"], cs[1]["words"]))

    def test_joined_and_cut_back_with_the_sheet_never_sending_words(self):
        before = raw(self.ap)
        was = self.chunks()
        pv = A.divide_preview(self.d, self.si, 0)
        r = A.merge_chunks(self.d, self.si, 0, sheet(pv["merge"]["fields"]))
        self.assertEqual(r["chunks"][0]["words"],
                         wordline.join_lines(was[0]["words"], was[1]["words"]),
                         "the joined line survives a sheet that sent none")
        A.split_chunk(self.d, self.si, 0, sheet(was[0]), sheet(was[1]))
        self.assertEqual(raw(self.ap), before,
                         "and so does the divided one: the file is itself again")

    def test_a_merge_the_page_leaves_to_chunkdiv(self):
        was = self.chunks()
        r = A.merge_chunks(self.d, self.si, 0)
        self.assertEqual(self.chunks()[0]["words"],
                         wordline.join_lines(was[0]["words"], was[1]["words"]))
        self.assertEqual(self.check()[0], [], r["notes"])

    def test_merging_a_worded_chunk_with_an_unworded_one(self):
        A.edit_chunk(self.d, self.si, 1, {"words": ""})
        pv = A.divide_preview(self.d, self.si, 0)
        r = A.merge_chunks(self.d, self.si, 0, sheet(pv["merge"]["fields"]))
        self.assertNotIn("words", self.chunks()[0])
        self.assertTrue(any("only one of the two" in n for n in r["notes"]),
                        r["notes"])
        self.assertEqual(self.check()[0], [])

    def test_a_line_the_page_sends_replaces_the_proposal(self):
        was = self.chunks()
        pv = A.divide_preview(self.d, self.si, 0)
        A.merge_chunks(self.d, self.si, 0,
                       sheet(pv["merge"]["fields"], words=""))
        self.assertNotIn("words", self.chunks()[0], "an empty one removes it")
        before = raw(self.ap)
        with self.assertRaises(ValueError) as cm:
            A.split_chunk(self.d, self.si, 0, sheet(was[0]),
                          sheet(was[1], words=self.stale(was[1]["words"])))
        self.assertIn(self.where + "1: the words do not reproduce",
                      str(cm.exception))
        self.assertEqual(raw(self.ap), before)
        A.split_chunk(self.d, self.si, 0, sheet(was[0], words=was[0]["words"]),
                      sheet(was[1], words=was[1]["words"]))
        self.assertEqual([c.get("words") for c in self.chunks()[:2]],
                         [was[0]["words"], was[1]["words"]])

    def test_a_draft_divides_its_words_with_its_blank_chunks(self):
        self.meta(draft=True)
        cs = self.chunks()
        blank = {"fa": cs[1]["fa"], "words": cs[1]["words"],
                 self.reading: "", "tr": "", "voc": "", "en": ""}
        self.change(1, **{k: v for k, v in blank.items()})
        self.change(1, **{k: KeyError for k in cs[1] if k not in blank})
        pv = A.divide_preview(self.d, self.si, 1)
        if not pv["cuts"]:
            self.skipTest("chunk 1 does not divide")
        c = pv["cuts"][-1]
        A.split_chunk(self.d, self.si, 1, sheet(c["first"], fa=c["a"]),
                      sheet(c["second"], fa=c["b"]))
        got = self.chunks()[1:3]
        self.assertEqual([g["words"] for g in got],
                         [c["first"]["words"], c["second"]["words"]])
        self.assertEqual(list(got[1])[:2], ["fa", "words"])
        self.assertEqual(got[1]["en"], "", "the blank slots stay blank")
        self.assertEqual(self.check()[0], [])

    def test_a_blank_line_is_not_kept_as_a_slot(self):
        was = self.chunks()
        self.change(0, words="")
        self.assertEqual(len(self.check()[0]), 1)
        pv = A.divide_preview(self.d, self.si, 0)
        A.merge_chunks(self.d, self.si, 0, sheet(pv["merge"]["fields"]))
        A.split_chunk(self.d, self.si, 0, sheet(was[0]), sheet(was[1]))
        self.assertNotIn("words", self.chunks()[0])
        self.assertEqual(self.check()[0], [])

    def test_a_line_that_is_not_text_is_a_sentence(self):
        self.change(0, words=["a", "b"])
        with self.assertRaises(ValueError) as cm:
            A.divide_preview(self.d, self.si, 0)
        self.assertIn("words is list", str(cm.exception))

    def test_a_line_that_cannot_be_read_is_refused_by_its_chunk(self):
        # serve.py previews before it splits or merges, so this is every
        # divide the page can ask of the chunk
        was = self.chunks()
        self.change(0, words=was[0]["words"] + ")")
        before = raw(self.ap)
        c = chunkdiv.cuts(was[0]["fa"], self.L)[0]
        for fn in (lambda: A.divide_preview(self.d, self.si, 0),
                   lambda: A.split_chunk(self.d, self.si, 0, {"fa": c["a"]},
                                         {"fa": c["b"]})):
            with self.assertRaises(ValueError) as cm:
                fn()
            said = str(cm.exception)
            self.assertTrue(said.startswith("segment %d chunk 0: its words "
                                            "cannot be divided" % self.si), said)
            self.assertIn("never opened", said)
            self.assertEqual(raw(self.ap), before)
        A.edit_chunk(self.d, self.si, 0, {"words": was[0]["words"]})
        self.assertTrue(A.divide_preview(self.d, self.si, 0)["cuts"],
                        "mended, it divides again")


class Japanese(Checks, Writes, Worded):
    FOLDER, ID, TABLE = "japanese", "aB3dE5fG7hI", JA
    OTHER = "よ"

    def test_a_kanji_word_left_without_its_reading(self):
        # segment 2 is 今日は / 天気が / いいですね
        ann = self.ann()
        ann["segments"][2]["chunks"][0]["words"] = "今日 は"
        dump(self.ap, ann)
        errors, warnings = self.check()
        self.assertEqual(errors, [])
        self.assertIn("segment 2 (start 9) chunk 0: 今日 has no reading", warnings)
        self.meta(reorders=True)
        self.assertEqual(self.check(), ([], []))

    def test_a_split_at_a_word_boundary(self):
        A.split_chunk(self.d, 2, 0,
                      {"fa": "今日", "kana": "きょう", "tr": "kyō",
                       "voc": "今日 きょう kyō today", "en": "today"},
                      {"fa": "は", "kana": "は", "tr": "wa",
                       "voc": "は wa topic marker", "en": "(the topic)"})
        cs = self.chunks(2)
        self.assertEqual([c.get("words") for c in cs],
                         ["今日(きょう)", "は", "天気(てんき) が", "いい です ね"])
        self.assertEqual(list(cs[0]), ["fa", "words", "kana", "tr", "voc", "en"])
        self.assertEqual(self.check(), ([], []))

    def test_a_split_inside_a_word(self):
        A.split_chunk(self.d, 2, 0,
                      {"fa": "今", "kana": "きょう", "tr": "kyō", "en": "to-"},
                      {"fa": "日は", "kana": "は", "tr": "wa", "en": "day"})
        cs = self.chunks(2)
        self.assertEqual([cs[0]["words"], cs[1]["words"]], ["今(きょう)", "日 は"])
        errors, warnings = self.check()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["segment 2 (start 9) chunk 1: 日 has no reading"])

    def test_merging_two_worded_chunks(self):
        A.merge_chunks(self.d, 2, 0, {"fa": "今日は天気が", "kana": "きょうはてんきが",
                                      "tr": "kyō wa tenki ga", "en": "today the weather"})
        self.assertEqual(self.chunks(2)[0]["words"], "今日(きょう) は 天気(てんき) が")
        self.assertEqual(self.check(), ([], []))


class Chinese(Checks, Writes, Worded):
    FOLDER, ID, TABLE = "chinese", "zH8cN2hA6nZ", ZH
    OTHER = " le"

    def test_a_split_through_a_word_of_two_syllables(self):
        # segment 1 is 你好， / 我想要一杯茶
        A.split_chunk(self.d, 1, 1,
                      {"fa": "我想", "tr": "wǒ xiǎng", "en": "I would"},
                      {"fa": "要一杯茶", "tr": "yào yì bēi chá",
                       "en": "like a cup of tea"})
        cs = self.chunks(1)
        self.assertEqual([cs[1]["words"], cs[2]["words"]],
                         ["我(wǒ) 想(xiǎng yào)", "要 一(yì) 杯(bēi) 茶(chá)"])
        errors, warnings = self.check()
        self.assertEqual(errors, [])
        # the reading left whole on the first half says more than its text:
        # warned, never refused -- and 要 now wants one of its own
        self.assertTrue(any(w.startswith("segment 1 (start 6) chunk 1: the words read")
                            for w in warnings), warnings)
        self.assertIn("segment 1 (start 6) chunk 2: 要 has no reading", warnings)

    def test_merging_two_worded_chunks(self):
        A.merge_chunks(self.d, 1, 0, {"fa": "你好，我想要一杯茶",
                                      "tr": "nǐ hǎo wǒ xiǎng yào yì bēi chá",
                                      "en": "hello, I would like a cup of tea"})
        self.assertEqual(self.chunks(1)[0]["words"],
                         "你(nǐ) 好(hǎo) ， 我(wǒ) 想要(xiǎng yào) 一(yì) 杯(bēi) 茶(chá)")
        self.assertEqual(self.check(), ([], []))


# --- the mark that frees a caption from the transcript -----------------------
class Free(Worded):
    """The same fixture with no word lines at all (TABLE is empty), because
    this is not about words: it is about what the caption's text is held
    against.  The pasted transcript is what YouTube heard, and it is
    sometimes wrong; a chunk marked "free" says the phrase is the
    annotator's, and takes its caption out of that comparison -- the
    reading editions' "this paragraph need not reproduce source/paras/"
    (lib/reading.py), one door over."""
    TABLE = {}

    def caption(self, seg=None):
        return self.ann()["segments"][self.si if seg is None else seg]

    def reword(self, k, fa):
        """Change a chunk's text in the file, caption text and all: the
        annotations stay true to themselves and depart from the transcript
        alone, which is the one thing the mark is about."""
        ann = self.ann()
        sg = ann["segments"][self.si]
        sg["chunks"][k]["fa"] = fa
        sg["text"] = self.L.word_sep.join(c["fa"] for c in sg["chunks"])
        dump(self.ap, ann)
        return sg["text"]

    def test_a_caption_that_departs_is_reported_until_it_is_marked(self):
        was = self.chunks()[0]["fa"]
        text = self.reword(0, was + "ね")
        errors, warnings = self.check()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("segment %d: text differs from transcript.txt" % self.si,
                      errors[0])
        self.assertIn(text, errors[0])
        self.assertEqual(warnings, [])
        # marked, the caption is not compared at all, and the run says so
        self.change(0, free=True)
        errors, warnings = self.check()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["1 caption not checked against "
                                    "transcript.txt: a chunk of each is "
                                    "marked as departing from it"])
        # one mark frees the caption, not the chunk: its neighbour may move
        # too, and the annotations still have to reproduce themselves
        self.reword(1, self.chunks()[1]["fa"] + "よ")
        self.assertEqual(self.check(), ([], warnings))
        ann = self.ann()
        ann["segments"][self.si]["text"] += "!"
        dump(self.ap, ann)
        errors, _w = self.check()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("chunks do not reproduce the text", errors[0])

    def test_the_mark_is_true_or_is_not_written_at_all(self):
        for bad in (False, "yes", 1, None):
            self.change(0, free=bad)
            errors, _w = self.check()
            self.assertEqual(len(errors), 1, (bad, errors))
            self.assertEqual(errors[0], self.where + "0: 'free' is true or is "
                                                     "not written at all")
        self.change(0, free=KeyError)
        self.assertEqual(self.check(), ([], []))

    def test_the_writer_takes_the_mark_with_the_edit_it_permits(self):
        ch = self.chunks()[0]
        before = raw(self.ap)
        with self.assertRaises(ValueError) as cm:
            A.edit_chunk(self.d, self.si, 0, {"fa": ch["fa"] + "ね"})
        self.assertIn("chunks do not reproduce the text", str(cm.exception))
        self.assertEqual(raw(self.ap), before, "a refusal writes nothing")
        # with the mark the same edit stands, and the caption's text follows
        # its chunks rather than the transcript
        got = A.edit_chunk(self.d, self.si, 0,
                           {"free": True, "fa": ch["fa"] + "ね"})
        self.assertEqual(got["fa"], ch["fa"] + "ね")
        self.assertIs(got["free"], True)
        self.assertEqual(self.caption()["text"], self.L.word_sep.join(
            c["fa"] for c in self.chunks()))
        errors, warnings = self.check()
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)

    def test_unmarking_puts_the_caption_back_under_the_transcript(self):
        ch = dict(self.chunks()[0])
        A.edit_chunk(self.d, self.si, 0, {"free": True, "fa": ch["fa"] + "ね"})
        # while the text departs, taking the mark off is refused -- and by
        # the rule it broke, so the editor can say what to put back
        with self.assertRaises(ValueError) as cm:
            A.edit_chunk(self.d, self.si, 0, {"free": False})
        self.assertIn("text differs from transcript.txt", str(cm.exception))
        self.assertIs(self.chunks()[0]["free"], True)
        # the words back as they were, the mark comes off and the key with it
        got = A.edit_chunk(self.d, self.si, 0, {"free": False, "fa": ch["fa"]})
        self.assertNotIn("free", got)
        self.assertEqual(self.check(), ([], []))

    def test_the_mark_is_a_boolean_at_the_door(self):
        for bad in ("yes", 1, ["x"]):
            with self.assertRaises(ValueError) as cm:
                A.edit_chunk(self.d, self.si, 0, {"free": bad})
            self.assertIn("free is true or false, not", str(cm.exception))

    def test_the_mark_survives_a_cut_and_a_join(self):
        """A divide moves a boundary and settles nothing else: a caption the
        annotator has taken charge of must not be handed back to the
        transcript by cutting one of its phrases in two."""
        ch = self.chunks()[0]
        A.edit_chunk(self.d, self.si, 0, {"free": True, "fa": ch["fa"] + "ね"})
        pv = A.divide_preview(self.d, self.si, 0)
        cut = pv["cuts"][len(pv["cuts"]) // 2]
        self.assertEqual([cut["first"].get("free"), cut["second"].get("free")],
                         [True, True], "both halves are proposed marked")
        text = lambda c, **kw: dict(
            {k: v for k, v in c.items() if k in A.EDITABLE and isinstance(v, str)},
            **kw)
        # the sheet sends text only; the mark is carried, never typed
        A.split_chunk(self.d, self.si, 0, text(cut["first"]),
                      text(cut["second"], tr="x", en="x", kana=cut["b"]))
        self.assertEqual([c.get("free") for c in self.chunks()][:2], [True, True])
        self.assertEqual(self.check()[0], [])
        A.merge_chunks(self.d, self.si, 0, None)
        self.assertIs(self.chunks()[0]["free"], True, "and the join keeps it")
        errors, warnings = self.check()
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)

    def test_a_marked_chunk_is_written_where_the_field_order_puts_it(self):
        A.edit_chunk(self.d, self.si, 1, {"free": True})
        self.assertEqual([k for k in self.chunks()[1] if k in ("en", "free")],
                         ["en", "free"], "last of the chunk's own fields")
        self.assertIn("free", CA.CHUNK_FIELDS)


class OneChunk(unittest.TestCase):
    def run_chunk(self, ch, code, **kw):
        errors, warnings = [], []
        CA.check_chunk(ch, "x", errors.append, warnings.append,
                       languages.get(code), **kw)
        return errors, warnings

    def test_a_language_without_a_word_layer(self):
        errors, _w = self.run_chunk({"fa": "سلام", "words": "سلام",
                                     "tr": "salām", "en": "hello"}, "fa")
        self.assertEqual(len(errors), 1)
        self.assertIn("no word layer", errors[0])

    def test_a_reading_that_is_not_text_is_reported_not_tripped_on(self):
        errors, _w = self.run_chunk({"fa": "山", "words": "山(やま)", "kana": 7,
                                     "tr": "yama", "en": "mountain"}, "ja")
        self.assertEqual(errors, ["x: missing 'kana'"])

    def test_chinese_tr_writes_the_changed_tone_and_the_word_its_own(self):
        ch = {"fa": "一个", "words": "一(yī) 个(gè)", "tr": "yí gè", "en": "one"}
        self.assertEqual(self.run_chunk(ch, "zh"), ([], []))
        ch["tr"] = "liǎng gè"
        errors, warnings = self.run_chunk(ch, "zh")
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(self.run_chunk(ch, "zh", reorders=True), ([], []))


if __name__ == "__main__":
    unittest.main()
