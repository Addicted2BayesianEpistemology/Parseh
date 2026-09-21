#!/usr/bin/env python3
"""lib/words.py gives each proposed word its stretch of the chunk's own reading.

    python3 -m unittest discover -s tests -p test_wordalign.py

The laying over is tested on words given by hand, so Japanese runs under any
Python and Chinese under one with pypinyin (its syllables come from there);
the cases end to end need the analyzers and are skipped without them.
"""
import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "lib") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "lib"))
import words                                                    # noqa: E402

HAVE_PINYIN = importlib.util.find_spec("pypinyin") is not None


class Japanese(unittest.TestCase):
    def test_the_chunks_kana_reads_a_word_the_dictionary_misreads(self):
        pairs = [("私", "わたくし"), ("は", ""), ("毎朝", "まいあさ"),
                 ("コーヒー", ""), ("を", ""), ("飲みます", "のみます")]
        self.assertEqual(words._given_japanese(pairs, "わたしはまいあさコーヒーをのみます"),
                         [("私", "わたし"), ("は", ""), ("毎朝", "まいあさ"),
                          ("コーヒー", ""), ("を", ""), ("飲みます", "のみます")])

    def test_a_reading_the_dictionary_does_not_have(self):
        pairs = [("今日", "きょう"), ("は", ""), ("十分", "じゅうぶん"), ("です", "")]
        self.assertEqual(words._given_japanese(pairs, "こんにちはじゅっぷんです"),
                         [("今日", "こんにち"), ("は", ""), ("十分", "じゅっぷん"), ("です", "")])

    def test_a_word_the_machine_gave_no_reading(self):
        self.assertEqual(words._given_japanese([("十", ""), ("分", "ふん")], "じゅっぷん"),
                         [("十", "じゅっ"), ("分", "ぷん")])

    def test_katakana_and_punctuation_in_the_reading(self):
        self.assertEqual(words._given_japanese([("山", "やま"), ("へ", ""), ("、", "")], "ヤマヘ、"),
                         [("山", "やま"), ("へ", ""), ("、", "")])

    def test_two_kanji_words_side_by_side_are_parted_by_the_dictionary(self):
        self.assertEqual(words._given_japanese([("山", "やま"), ("川", "かわ")], "やまがわ"),
                         [("山", "やま"), ("川", "がわ")])

    def test_a_small_ke_is_read_not_spelled(self):
        self.assertEqual(words._given_japanese([("三ヶ月", "さんかげつ")], "さんかげつ"),
                         [("三ヶ月", "さんかげつ")])

    def test_a_reading_of_some_other_text_leaves_the_machines(self):
        pairs = [("私", "わたくし"), ("は", "")]
        self.assertEqual(words._given_japanese(pairs, "さようなら"), pairs)


@unittest.skipUnless(HAVE_PINYIN, "pypinyin is not installed in this Python")
class Chinese(unittest.TestCase):
    def test_the_tones_are_the_ones_tr_writes(self):
        pairs = [("每天", "měitiān"), ("早上", "zǎoshàng"), ("，", ""), ("老人", "lǎorén")]
        self.assertEqual(words._given_chinese(pairs, "měitiān zǎoshang, lǎorén"),
                         [("每天", "měitiān"), ("早上", "zǎoshang"), ("，", ""), ("老人", "lǎorén")])

    def test_a_character_read_two_ways(self):
        self.assertEqual(words._given_chinese([("很", "hěn"), ("长", "zhǎng")], "hěn cháng"),
                         [("很", "hěn"), ("长", "cháng")])

    def test_the_changed_tone_of_yi(self):
        self.assertEqual(words._given_chinese([("一", "yī"), ("个", "gè")], "yí ge"),
                         [("一", "yí"), ("个", "ge")])

    def test_a_capital_and_an_apostrophe(self):
        self.assertEqual(words._given_chinese([("天安门", "tiān'ānmén")], "Tiān'ānmén"),
                         [("天安门", "Tiān'ānmén")])

    def test_a_word_tr_writes_as_two(self):
        self.assertEqual(words._given_chinese([("打水", "dǎshuǐ")], "dǎ shuǐ"),
                         [("打水", "dǎshuǐ")])

    def test_erhua(self):
        self.assertEqual(words._given_chinese([("一点儿", "yìdiǎn'ér")], "yìdiǎnr"),
                         [("一点儿", "yìdiǎnr")])

    def test_a_latin_word_is_spelled_as_it_stands(self):
        pairs = [("我", "wǒ"), ("用", "yòng"), ("iPhone", ""), ("。", "")]
        self.assertEqual(words._given_chinese(pairs, "Wǒ yòng iPhone."),
                         [("我", "Wǒ"), ("用", "yòng"), ("iPhone", ""), ("。", "")])

    def test_a_reading_of_some_other_text_leaves_the_machines(self):
        pairs = [("我", "wǒ")]
        self.assertEqual(words._given_chinese(pairs, "nǐ hǎo"), pairs)


class EndToEnd(unittest.TestCase):
    @unittest.skipUnless(words.available("ja"), "no Japanese analyzer in this Python")
    def test_japanese(self):
        text = "私は毎朝コーヒーを飲みます"
        self.assertIn("私(わたくし)", words.line(text, "ja"))
        self.assertIn("私(わたし)", words.line(text, "ja", "わたしはまいあさコーヒーをのみます"))

    @unittest.skipUnless(words.available("zh"), "no Chinese analyzer in this Python")
    def test_chinese(self):
        got = words.line("早上很冷", "zh", "zǎoshang hěn lěng")
        self.assertIn("zǎoshang", got)
        self.assertNotIn("zǎoshàng", got)

    @unittest.skipUnless(words.available("ja"), "no Japanese analyzer in this Python")
    def test_a_reading_never_moves_a_cut(self):
        text = "山へ柴刈りに、"
        cut = [s for s, _ in words.propose(text, "ja")]
        self.assertEqual([s for s, _ in words.propose(text, "ja", "ぜんぜんちがう")], cut)
        self.assertEqual([s for s, _ in words.propose(text, "ja", "やまへしばかりに")], cut)


if __name__ == "__main__":
    unittest.main()
