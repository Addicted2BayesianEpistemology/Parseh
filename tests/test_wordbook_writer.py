#!/usr/bin/env python3
"""lib/texwrite.py with a word line: a chunk given words, edited, taken off
them, cut and joined, on scratch copies of the fixture editions.

Two promises are held after every operation.  Every byte outside the call or
calls it touched is the byte that was there -- a macro's name changes with
its words, and nothing else in the chapter moves.  And the chapter still
reads as the same number of chunks through texwrite's walk and through
texparse's, because a name one of them does not know makes a chunk vanish
without a word.  (The texparse half is skipped where texparse does not yet
read \\chrw: it is probed, not assumed.)

    python3 tests/test_wordbook_writer.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))
import texparse                                                 # noqa: E402
import texwrite as X                                            # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "books")
YAMA = "山(やま) へ 柴刈り(しばかり) に 、"          # mini-ja chunk 6, 山へ柴刈りに、
KAWA = "川(かわ) へ 洗濯(せんたく) に"               # mini-ja chunk 8, 川へ洗濯に


def _texparse_reads_words():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "ch1.tex")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write("\\parnum{1.1}\n\\begin{frank}\n"
                    "\\chrw{}{山}{やま}{yama}{}{mountain}{山(やま)}\n\\end{frank}\n")
        return sum(len(s.chunks) for s in texparse.parse_chapter(p, "ja").subs) == 1


READS_WORDS = _texparse_reads_words()


def read(p):
    with io.open(p, encoding="utf-8", newline="") as f:
        return f.read()


class _Copy(unittest.TestCase):
    code, folder, slug = None, None, None

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.dir = os.path.join(self.td, self.slug)
        shutil.copytree(os.path.join(FIX, self.folder, self.slug), self.dir,
                        ignore=shutil.ignore_patterns("reader", "*.pdf"))
        self.p = os.path.join(self.dir, "ch1.tex")
        self.n = len(X.read_chunks(self.p))

    def tearDown(self):
        shutil.rmtree(self.td)

    def meta(self, **kw):
        bj = os.path.join(self.dir, "book.json")
        with io.open(bj, encoding="utf-8") as f:
            d = json.load(f)
        d.update(kw)
        with io.open(bj, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

    def counts(self, want):
        """The chapter reads as `want` chunks, through both walks."""
        self.assertEqual(len(X.read_chunks(self.p)), want)
        if READS_WORDS:
            ch = texparse.parse_chapter(self.p, self.code)
            self.assertEqual(sum(len(s.chunks) for s in ch.subs), want)

    def spliced(self, before, after, start, end):
        """`after` is `before` everywhere but where [start, end) stood;
        -> what stands there now."""
        tail = len(before) - end
        self.assertEqual(after[:start], before[:start])
        self.assertEqual(after[len(after) - tail:], before[end:])
        return after[start:len(after) - tail]


class Japanese(_Copy):
    code, folder, slug = "ja", "japanese", "mini-ja"

    def test_a_chunk_is_given_words_and_they_come_off_again(self):
        before = read(self.p)
        c = X.read_chunks(self.p)[6]
        self.assertEqual((c["macro"], c["words"]), ("chr", ""))
        r = X.edit_chunk(self.p, 6, {"words": YAMA})
        self.assertEqual((r["macro"], r["changed"], r["warnings"]),
                         ("chrw", ["words"], []))
        promoted = read(self.p)
        s, e = c["span"]
        self.assertEqual(self.spliced(before, promoted, s, e),
                         "\\chrw" + before[s + len("\\chr"):e] + "{%s}" % YAMA)
        self.assertEqual(X.read_chunks(self.p)[6]["words"], YAMA)
        self.counts(self.n)
        # the chunk after it is still the chunk after it: an edit by number
        # lands where the reader's number says
        X.edit_chunk(self.p, 7, {"en": "the old woman, edited"})
        self.assertEqual(X.read_chunks(self.p)[7]["fa"], "おばあさんは")
        X.edit_chunk(self.p, 7, {"en": "the old woman"})
        self.assertEqual(read(self.p), promoted)

        # another division of the same text moves the words group and no more
        a, b = X._scan(promoted)[6].args[-1]
        r = X.edit_chunk(self.p, 6, {"words": "山(やま) へ 柴(しば) 刈り(かり) に 、"})
        self.assertEqual((r["macro"], r["changed"]), ("chrw", ["words"]))
        self.spliced(promoted, read(self.p), a, b)
        self.counts(self.n)

        r = X.edit_chunk(self.p, 6, {"words": ""})
        self.assertEqual((r["macro"], r["changed"]), ("chr", ["words"]))
        self.assertEqual(read(self.p), before)
        self.counts(self.n)

    def test_an_fa_that_leaves_its_words_behind_is_refused(self):
        X.edit_chunk(self.p, 6, {"words": YAMA})
        before = read(self.p)
        with self.assertRaises(X.Refused) as e:
            X.edit_chunk(self.p, 6, {"fa": "山へ柴刈りに行く、"})
        self.assertIn("fix the words too", str(e.exception))
        self.assertEqual(read(self.p), before)
        # where the paragraph cannot be judged against a source, the words
        # are judged against the text all the same
        shutil.rmtree(os.path.join(self.dir, "source"))
        with self.assertRaises(X.Refused):
            X.edit_chunk(self.p, 6, {"fa": "山へ柴刈りに行く、"})
        r = X.edit_chunk(self.p, 6, {"fa": "山へ柴刈りに行く、",
                                     "words": "山(やま) へ 柴刈り(しばかり) に 行く(いく) 、"})
        self.assertEqual((r["macro"], r["changed"]), ("chrw", ["fa", "words"]))
        # the chunk's kana is its own data and was not changed: warned only
        self.assertTrue(any("reading" in w for w in r["warnings"]), r["warnings"])

    def test_a_line_already_wrong_is_named_as_such(self):
        X.edit_chunk(self.p, 6, {"words": YAMA})
        t = read(self.p).replace("{%s}" % YAMA, "{山(やま) へ}")
        with io.open(self.p, "w", encoding="utf-8", newline="") as f:
            f.write(t)
        with self.assertRaises(X.Refused) as e:
            X.edit_chunk(self.p, 6, {"en": "something"})
        self.assertIn("already written here", str(e.exception))
        self.assertEqual(read(self.p), t)

    def test_words_are_judged_at_the_book_door(self):
        before = read(self.p)
        for bad in ("山(やま) へ", YAMA + " 50%", "山(やま)へ 柴刈り(しばかり) に 、",
                    "山（やま） へ 柴刈り(しばかり) に 、", 7):
            with self.assertRaises(X.Refused, msg=repr(bad)):
                X.edit_chunk(self.p, 6, {"words": bad})
        self.assertEqual(read(self.p), before)

    def test_a_warning_is_not_a_refusal(self):
        r = X.edit_chunk(self.p, 6, {"words": "山 へ 柴刈り(しばかり) に 、"})
        self.assertEqual(r["macro"], "chrw")
        self.assertTrue(any("山 has no reading" in w for w in r["warnings"]), r["warnings"])

    def test_a_book_that_reorders_is_not_warned(self):
        wrong = "山(さん) へ 柴刈り(しばかり) に 、"
        self.assertTrue(X.edit_chunk(self.p, 6, {"words": wrong})["warnings"])
        X.edit_chunk(self.p, 6, {"words": ""})
        self.meta(reorders=True)
        self.assertEqual(X.edit_chunk(self.p, 6, {"words": wrong})["warnings"], [])

    def test_the_unglossed_chunk_has_no_words(self):
        t = read(self.p)
        line = next(ln for ln in t.split("\n") if ln.startswith("\\chr{}{おじいさんは}{"))
        with io.open(self.p, "w", encoding="utf-8", newline="") as f:
            f.write(t.replace(line, "\\chp{}{おじいさんは}", 1))
        k = next(i for i, c in enumerate(X.read_chunks(self.p)) if c["macro"] == "chp")
        with self.assertRaises(X.Refused) as e:
            X.edit_chunk(self.p, k, {"words": "おじいさん は"})
        self.assertIn("\\chp", str(e.exception))

    def _cut(self, a_fa):
        pv = X.divide_preview(self.p, 6)
        return next(c for c in pv["cuts"] if c["a"] == a_fa)

    def test_split_at_a_word_boundary(self):
        X.edit_chunk(self.p, 6, {"words": YAMA})
        before, c = read(self.p), X.read_chunks(self.p)[6]
        cut = self._cut("山へ")
        self.assertEqual((cut["first"]["words"], cut["second"]["words"]),
                         ("山(やま) へ", "柴刈り(しばかり) に 、"))
        first = dict(cut["first"], kana="やまへ", tr="yama e", en="to the mountain")
        second = dict(cut["second"], kana="しばかりに", tr="shibakari ni",
                      en="to cut firewood,")
        r = X.split_chunk(self.p, 6, first, second)
        self.assertEqual((r["first"]["macro"], r["second"]["macro"], r["warnings"]),
                         ("chrw", "chrw", []))
        made = self.spliced(before, read(self.p), *c["span"])
        self.assertEqual(made.count("\n"), 1)
        self.counts(self.n + 1)

    def test_split_inside_a_word(self):
        X.edit_chunk(self.p, 6, {"words": YAMA})
        before, c = read(self.p), X.read_chunks(self.p)[6]
        cut = self._cut("山へ柴")
        self.assertEqual((cut["first"]["words"], cut["second"]["words"]),
                         ("山(やま) へ 柴(しばかり)", "刈り に 、"))
        self.assertTrue(any("柴刈り" in n for n in cut["notes"]), cut["notes"])
        first = dict(cut["first"], kana="やまへしば", tr="yama e shiba", en="to the mountain")
        second = dict(cut["second"], kana="かりに", tr="kari ni", en="to cut firewood,")
        r = X.split_chunk(self.p, 6, first, second)
        self.assertEqual((r["first"]["macro"], r["second"]["macro"]), ("chrw", "chrw"))
        self.assertTrue(any(w.startswith("second half") and "刈り has no reading" in w
                            for w in r["warnings"]), r["warnings"])
        self.spliced(before, read(self.p), *c["span"])
        self.counts(self.n + 1)

    def test_each_half_is_named_by_its_own_words(self):
        X.edit_chunk(self.p, 6, {"words": YAMA})
        cut = self._cut("山へ")
        first = dict(cut["first"], kana="やまへ", tr="yama e", en="to the mountain")
        second = dict(cut["second"], kana="しばかりに", tr="shibakari ni",
                      en="to cut firewood,", words="")
        r = X.split_chunk(self.p, 6, first, second)
        self.assertEqual((r["first"]["macro"], r["second"]["macro"]), ("chrw", "chr"))
        self.counts(self.n + 1)

    def test_two_chunks_with_words_join_and_cut_back(self):
        X.edit_chunk(self.p, 7, {"words": "おばあさん は"})
        X.edit_chunk(self.p, 8, {"words": KAWA})
        before, cs = read(self.p), X.read_chunks(self.p)
        r = X.merge_chunks(self.p, 7)
        self.assertEqual((r["macro"], r["chunks"], r["warnings"]), ("chrw", self.n - 1, []))
        self.assertEqual(r["chunk"]["words"], "おばあさん は " + KAWA)
        self.spliced(before, read(self.p), cs[7]["span"][0], cs[8]["span"][1])
        self.counts(self.n - 1)
        X.split_chunk(self.p, 7, {f: cs[7][f] for f in X.FIELDS},
                      {f: cs[8][f] for f in X.FIELDS})
        self.assertEqual(read(self.p), before)
        self.counts(self.n)

    def test_a_chunk_with_words_joins_one_without(self):
        for k in (7, 8):                        # the words on either side
            with self.subTest(words_on=k):
                self.tearDown()
                self.setUp()
                X.edit_chunk(self.p, k, {"words": KAWA if k == 8 else "おばあさん は"})
                pv = X.divide_preview(self.p, 7)
                self.assertIsNone(pv["merge_error"])
                self.assertNotIn("words", pv["merge"]["fields"])
                self.assertTrue(any("only one of the two" in n
                                    for n in pv["merge"]["notes"]))
                before, cs = read(self.p), X.read_chunks(self.p)
                r = X.merge_chunks(self.p, 7)
                self.assertEqual((r["macro"], r["chunk"]["words"]), ("chr", ""))
                self.spliced(before, read(self.p), cs[7]["span"][0], cs[8]["span"][1])
                self.counts(self.n - 1)

    def test_a_join_given_words_is_written_with_them(self):
        X.edit_chunk(self.p, 8, {"words": KAWA})
        fields = dict(X.divide_preview(self.p, 7)["merge"]["fields"],
                      words="おばあさん は " + KAWA)
        r = X.merge_chunks(self.p, 7, fields)
        self.assertEqual(r["macro"], "chrw")
        self.counts(self.n - 1)

    def test_a_caller_that_never_mentions_words_does_not_lose_them(self):
        # the reader's divide sheet sends the boxes it draws, and words is not
        # one of them: silence is refused, a blank is a decision
        X.edit_chunk(self.p, 6, {"words": YAMA})
        cut = self._cut("山へ")
        boxes = [{k: v for k, v in dict(h, kana="やまへ", tr="yama e",
                                        en="to the mountain").items() if k != "words"}
                 for h in (cut["first"], cut["second"])]
        before = read(self.p)
        with self.assertRaises(X.Refused) as e:
            X.split_chunk(self.p, 6, *boxes)
        self.assertIn("neither half", str(e.exception))
        self.assertEqual(read(self.p), before)
        r = X.split_chunk(self.p, 6, dict(boxes[0], words=""), boxes[1])
        self.assertEqual((r["first"]["macro"], r["second"]["macro"]), ("chr", "chr"))
        self.counts(self.n + 1)

        # the join: two lines, and fields that say nothing of words
        X.edit_chunk(self.p, 8, {"words": "おばあさん は"})
        X.edit_chunk(self.p, 9, {"words": KAWA})
        fields = {k: v for k, v in X.divide_preview(self.p, 8)["merge"]["fields"].items()
                  if k != "words"}
        before = read(self.p)
        with self.assertRaises(X.Refused) as e:
            X.merge_chunks(self.p, 8, fields)
        self.assertIn("says nothing of them", str(e.exception))
        self.assertEqual(read(self.p), before)
        r = X.merge_chunks(self.p, 8, dict(fields, words=""))
        self.assertEqual(r["macro"], "chr")

    def test_a_line_one_side_only_joins_through_fields_without_words(self):
        X.edit_chunk(self.p, 8, {"words": KAWA})
        fields = X.divide_preview(self.p, 7)["merge"]["fields"]
        self.assertNotIn("words", fields)
        self.assertEqual(X.merge_chunks(self.p, 7, fields)["macro"], "chr")

    def test_a_preview_of_a_line_that_does_not_read_still_offers_the_cuts(self):
        X.edit_chunk(self.p, 6, {"words": YAMA})
        t = read(self.p)
        with io.open(self.p, "w", encoding="utf-8", newline="") as f:
            f.write(t.replace("{%s}" % YAMA, "{山(やま)へ 柴刈り(しばかり) に 、}"))
        pv = X.divide_preview(self.p, 6)
        self.assertTrue(pv["cuts"])
        for c in pv["cuts"]:
            self.assertNotIn("words", c["first"])
            self.assertNotIn("words", c["second"])
            self.assertTrue(any("does not read" in n for n in c["notes"]), c["notes"])

    def test_a_blank_line_written_by_hand_is_taken_off_when_asked(self):
        c = X.read_chunks(self.p)[6]
        s, e = c["span"]
        t = read(self.p)
        with io.open(self.p, "w", encoding="utf-8", newline="") as f:
            f.write(t[:s] + "\\chrw" + t[s + len("\\chr"):e] + "{}" + t[e:])
        self.assertEqual(X.read_chunks(self.p)[6]["macro"], "chrw")
        r = X.edit_chunk(self.p, 6, {"words": ""})
        self.assertEqual((r["macro"], r["changed"]), ("chr", ["words"]))
        self.assertEqual(read(self.p), t)

    def test_words_on_new_chunks_are_refused_where_they_cannot_go(self):
        X.edit_chunk(self.p, 6, {"words": YAMA})
        cut = self._cut("山へ")
        first = dict(cut["first"], kana="やまへ", tr="yama e", en="to the mountain")
        second = dict(cut["second"], kana="しばかりに", tr="shibakari ni", en="x")
        before = read(self.p)
        with self.assertRaises(X.Refused) as e:
            X.split_chunk(self.p, 6, dict(first, words=7), second)
        self.assertIn("must be a string", str(e.exception))
        with self.assertRaises(X.Refused) as e:      # a half's words, the other text
            X.split_chunk(self.p, 6, dict(first, words=cut["second"]["words"]), second)
        self.assertIn("first half", str(e.exception))
        self.assertEqual(read(self.p), before)
        # kana on a chunk that has words and no reading names the macro with both
        t = read(self.p)
        k = X.read_chunks(self.p)[7]
        with io.open(self.p, "w", encoding="utf-8", newline="") as f:
            f.write(t[:k["span"][0]] + "\\chw{}{おばあさんは}{obāsan wa}{}{the old woman}"
                    "{おばあさん は}" + t[k["span"][1]:])
        with self.assertRaises(X.Refused) as e:
            X.edit_chunk(self.p, 7, {"kana": "おばあさんは"})
        self.assertIn("\\chrw", str(e.exception))


class Chinese(_Copy):
    code, folder, slug = "zh", "chinese", "mini-zh"
    YOU = "有(yǒu) 一(yí) 个(ge) 小(xiǎo) 村子(cūnzi) 。"

    def test_pinyin_words_come_and_go(self):
        before = read(self.p)
        c = X.read_chunks(self.p)[2]
        self.assertEqual((c["macro"], c["fa"]), ("ch", "有一个小村子。"))
        r = X.edit_chunk(self.p, 2, {"words": self.YOU})
        self.assertEqual((r["macro"], r["warnings"]), ("chw", []))
        s, e = c["span"]
        self.assertEqual(self.spliced(before, read(self.p), s, e),
                         "\\chw" + before[s + len("\\ch"):e] + "{%s}" % self.YOU)
        self.counts(self.n)
        with self.assertRaises(X.Refused):
            X.edit_chunk(self.p, 2, {"kana": "ゆう"})
        # tr is the reading a Chinese line is compared with
        r = X.edit_chunk(self.p, 2, {"words": self.YOU.replace("xiǎo", "shǎo")})
        self.assertTrue(any("reading" in w for w in r["warnings"]), r["warnings"])
        X.edit_chunk(self.p, 2, {"words": ""})
        self.assertEqual(read(self.p), before)
        self.counts(self.n)

    def test_a_join_of_two_chw(self):
        X.edit_chunk(self.p, 0, {"words": "从前(cóngqián) ，"})
        X.edit_chunk(self.p, 1, {"words": "山(shān) 下(xià)"})
        before, cs = read(self.p), X.read_chunks(self.p)
        r = X.merge_chunks(self.p, 0)
        self.assertEqual((r["macro"], r["chunk"]["words"], r["warnings"]),
                         ("chw", "从前(cóngqián) ， 山(shān) 下(xià)", []))
        self.spliced(before, read(self.p), cs[0]["span"][0], cs[1]["span"][1])
        self.counts(self.n - 1)


class Persian(_Copy):
    code, folder, slug = "fa", "persian", "mini-fa"

    def test_a_language_without_a_word_layer_refuses_words(self):
        before = read(self.p)
        with self.assertRaises(X.Refused) as e:
            X.edit_chunk(self.p, 0, {"words": "x"})
        self.assertIn("no word layer", str(e.exception))
        c = X.read_chunks(self.p)[0]
        self.assertEqual((c["macro"], c["words"]), ("ch", ""))
        pv = X.divide_preview(self.p, 0)
        if pv["cuts"]:
            cut = pv["cuts"][0]
            with self.assertRaises(X.Refused):
                X.split_chunk(self.p, 0, dict(cut["first"], words="x"), cut["second"])
        self.assertEqual(read(self.p), before)


if __name__ == "__main__":
    unittest.main()
