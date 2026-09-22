# SPDX-License-Identifier: GPL-3.0-or-later
"""Where a sentence is cut into chunks: at its punctuation first, in every
language, then at the edges of its phrases -- and never inside a word.

    python3 -m unittest discover -s tests -p test_phrase_cut.py

Runs under any Python.  A Japanese sentence is cut between SudachiPy's words,
and a Chinese one between pkuseg's tagged words, where those are installed,
and those cuts are proved there; everywhere the characters are read instead,
and that cut is proved with the analyzer stood down.  A spaced language is cut
by its own list of function words and by a dictionary built here for the test.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import chunker    # noqa: E402
import draft      # noqa: E402
import lookup     # noqa: E402
import segmenter  # noqa: E402
import wordline   # noqa: E402
import words      # noqa: E402

# Momotarō as tests/fixtures/books/japanese/mini-ja cuts it by hand.
MOMOTARO = [
    ('むかしむかし、あるところに、おじいさんとおばあさんが住んでいました。',
     ['むかしむかし、', 'あるところに、', 'おじいさんと', 'おばあさんが', '住んでいました。']),
    ('おばあさんは桃を拾って、家に持って帰りました。',
     ['おばあさんは', '桃を拾って、', '家に', '持って帰りました。']),
    ('二人はその子を桃太郎と名づけて、大切に育てました。',
     ['二人は', 'その子を', '桃太郎と名づけて、', '大切に育てました。']),
]


def cut(text, code='ja'):
    got = chunker.chunk(text, code, 'phrase')
    assert chunker.reproduces(got, text, code), got
    return got


def no_tagger():
    return patch.object(chunker.words, 'parsed', lambda text, lang: [])


class Characters(unittest.TestCase):
    """Japanese read off its characters, as a Python without SudachiPy reads it."""

    def setUp(self):
        p = no_tagger()
        p.start()
        self.addCleanup(p.stop)

    def test_a_comma_closes_the_chunk_before_it(self):
        self.assertEqual(cut('寒い朝に、窓を開ける。'), ['寒い朝に、', '窓を開ける。'])
        self.assertEqual(cut('暗い部屋で、ろうそくを灯す。'), ['暗い部屋で、', 'ろうそくを灯す。'])
        self.assertEqual(cut('おじいさんは山へ柴刈りに、おばあさんは川へ洗濯に行きました。'),
                         ['おじいさんは', '山へ柴刈りに、', 'おばあさんは', '川へ洗濯に', '行きました。'])

    def test_the_run_after_a_comma_is_not_cut_inside_a_word(self):
        got = cut('冷たい雨が、窓の外にながれ落ちる。')
        self.assertEqual(got[0], '冷たい雨が、')
        self.assertTrue(got[-1].endswith('ながれ落ちる。'), got)

    def test_a_quote_keeps_the_particle_it_closes_into(self):
        self.assertEqual(cut('「おい、待ってくれ！」と彼は叫んだ。'),
                         ['「おい、', '待ってくれ！」と', '彼は叫んだ。'])

    def test_the_pieces_grow_into_phrases_but_not_past_a_topic(self):
        self.assertEqual(cut('本を読んで映画を見ました'), ['本を読んで', '映画を見ました'])
        self.assertEqual(cut('私は毎日日本語を勉強しています'), ['私は', '毎日日本語を', '勉強しています'])
        self.assertEqual(cut('雨が降る。'), ['雨が降る。'], 'a last short verb joins its subject')

    def test_a_draft_cut_into_phrases_keeps_the_marks_in_its_readings(self):
        def stand_in(fa, code, reading=''):
            return wordline.render([(ch, 'よみ' if wordline.HAN.search(ch) else '')
                                    for ch in fa if not ch.isspace()])
        with patch.object(draft.words, 'line', stand_in):
            tex = draft.book_from_text('寒い朝に、窓を開ける。', 'ja', 't', slug='t',
                                       how='phrase')['files']['ch1.tex']
        lines = [ln for ln in tex.split('\n') if ln.startswith('\\chrw{')]
        self.assertEqual(len(lines), 2, tex)
        self.assertTrue(lines[0].startswith('\\chrw{}{寒い朝に、}{よみいよみに、}'), lines[0])
        self.assertTrue(lines[1].startswith('\\chrw{}{窓を開ける。}{よみをよみける。}'), lines[1])


class Words(unittest.TestCase):
    """Japanese cut between the words SudachiPy divides it into."""

    @classmethod
    def setUpClass(cls):
        if not words.available('ja'):
            raise unittest.SkipTest('no SudachiPy in %s' % sys.executable)

    def test_parsed_is_the_word_strip_with_its_parts_of_speech(self):
        text = '寒い朝に、窓を開ける。'
        got = words.parsed(text, 'ja')
        self.assertEqual([s for s, _ in got], [s for s, _ in wordline.parse(words.line(text, 'ja'))])
        self.assertEqual(got[2][1][0][1][0], '助詞', got[2])

    def test_a_tale_cut_by_hand_is_cut_the_same_way(self):
        for text, want in MOMOTARO:
            self.assertEqual(cut(text), want)

    def test_a_comma_a_modifier_and_a_verb_with_its_object(self):
        self.assertEqual(cut('寒い朝に、窓を開ける。'), ['寒い朝に、', '窓を開ける。'])
        self.assertEqual(cut('もし明日雨が降ったら、私たちは家で映画を見るつもりです。'),
                         ['もし明日雨が', '降ったら、', '私たちは', '家で映画を', '見るつもりです。'])
        self.assertEqual(cut('ありがとうございました'), ['ありがとうございました'])

    def test_no_chunk_ends_inside_a_word(self):
        for text in ['冷たい雨が、窓の外にながれ落ちる。',
                     'えーと、あのね、きのうね、ともだちとね、こうえんにいったんだよ。',
                     '昨日駅前の本屋で買ったばかりの本をなくしてしまった。'] + [t for t, _ in MOMOTARO]:
            ends, at = set(), 0
            for surface, _pieces in words.parsed(text, 'ja'):
                at = text.index(surface, at) + len(surface)
                ends.add(at)
            at = 0
            for c in cut(text)[:-1]:
                at = text.index(c, at) + len(c)
                self.assertIn(at, ends, (text, c))


class Chinese(unittest.TestCase):
    def test_without_the_tagger_it_is_cut_at_its_own_punctuation(self):
        with no_tagger():
            self.assertEqual(cut('从前，山下有一个小村子。', 'zh'), ['从前，', '山下有一个小村子。'])
            self.assertEqual(cut('他一边喝着茶，一边看着报纸；外面下着雨。', 'zh'),
                             ['他一边喝着茶，', '一边看着报纸；', '外面下着雨。'])
            self.assertEqual(cut('「你好。」他说。', 'zh'), ['「你好。」', '他说。'])
            self.assertEqual(cut('你去过北京吗我没去过', 'zh'), ['你去过北京吗', '我没去过'])

    def test_with_the_tagger_a_clause_is_cut_into_its_phrases(self):
        if not words.tagger_available('zh'):
            self.skipTest('no pkuseg part-of-speech model for %s' % sys.executable)
        # the hand-made chunks of tests/fixtures/books/chinese/mini-zh and its video
        for text, want in (('每天早上，老人去河边打水。', ['每天早上，', '老人去河边', '打水。']),
                           ('你好，我想要一杯茶', ['你好，', '我想要一杯茶']),
                           ('从前，山下有一个小村子。', ['从前，', '山下', '有一个小村子。']),
                           ('晚上，他在灯下看书，猫在他的脚边睡觉。',
                            ['晚上，', '他在灯下', '看书，', '猫在他的脚边', '睡觉。'])):
            self.assertEqual(cut(text, 'zh'), want)
        # and a clause nobody punctuated, which is what an auto-caption is
        self.assertEqual(cut('我昨天在北京的一家小书店里买了一本很有意思的书。', 'zh'),
                         ['我昨天', '在北京的一家小书店里', '买了', '一本很有意思的书。'])
        got = words.parsed('我想要一杯茶。', 'zh')
        self.assertEqual([(w, p[0][1][0]) for w, p in got][:3], [('我', 'r'), ('想', 'v'), ('要', 'v')])

    def test_the_tagger_is_asked_only_where_its_model_is_on_disk(self):
        if not words.available('zh'):
            self.skipTest('no pkuseg in %s' % sys.executable)
        with patch.object(words.segmenter, 'model_ready', lambda code, name: False):
            self.assertFalse(words.tagger_available('zh'))
            self.assertEqual(words.parsed('我想要一杯茶。', 'zh'), [], 'nothing is downloaded by a cut')

    def test_the_models_are_found_file_by_file(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'PKUSEG_HOME': td}):
            self.assertEqual([m['have'] for m in segmenter.models('zh')], [False, False])
            for name, files in (('spacy_ontonotes', ('features.msgpack', 'weights.npz')),
                                ('postag', ('features.pkl', 'weights.npz'))):
                os.makedirs(os.path.join(td, name))
                for f in files:
                    Path(td, name, f).write_bytes(b'x')
            self.assertEqual([m['have'] for m in segmenter.models('zh')], [False, False],
                             'the zip too, or pkuseg fetches the model again')
            for name in ('spacy_ontonotes', 'postag'):
                Path(td, name + '.zip').write_bytes(b'x')
            self.assertTrue(segmenter.model_ready('zh', 'postag'))
            self.assertEqual(segmenter.about('zh')['models'][1]['name'], 'postag')
        self.assertEqual(segmenter.models('ja'), [], 'SudachiPy downloads nothing')


class Spaced(unittest.TestCase):
    @staticmethod
    def forget():
        have = getattr(lookup._CONNS, 'map', None) or {}
        for conn, _stamp in have.values():
            try:
                conn and conn.close()
            except Exception:
                pass
        lookup._CONNS.map = {}

    def test_with_no_dictionary_the_function_words_and_the_punctuation_cut(self):
        with patch.object(chunker.lookup, 'available', lambda code: False):
            self.assertEqual(cut('When I got home, my mother was already asleep.', 'en'),
                             ['When I got home,', 'my mother was already asleep.'])
            self.assertEqual(cut('He said, "Wait!" and she stopped — then she turned.', 'en'),
                             ['He said, "Wait!"', 'and she stopped —', 'then she turned.'])
            self.assertEqual(cut('Yes, I know.', 'en'), ['Yes,', 'I know.'], 'an interjection is its own chunk')
            self.assertEqual(cut('the old man sat in the darkness', 'en'),
                             ['the old man sat', 'in the darkness'], 'a preposition opens a phrase')
            self.assertEqual(cut("C'era una volta un pezzo di legno.", 'it'),
                             ["C'era una volta", 'un pezzo di legno.'], 'di ties its noun to the one before')
            self.assertEqual(cut('Buongiorno, vorrei un chilo di pomodori', 'it'),
                             ['Buongiorno,', 'vorrei un chilo di pomodori'])
            # a language with no list either: its punctuation is all there is
            self.assertEqual(cut('Oui , monsieur ; je sais.', 'fr'), ['Oui , monsieur ;', 'je sais.'])
            line = 'eins zwei drei vier fünf sechs sieben'
            self.assertEqual(cut(line, 'de'), [line], 'and no cut is made at random')

    def test_with_a_dictionary_each_word_is_read_in_its_place(self):
        rows = [('when', 'conj'), ('i', 'pron'), ('get', 'verb', 'a sense', ['got']), ('home', 'noun'),
                ('my', 'det'), ('mother', 'noun'), ('be', 'verb', 'a sense', ['was']), ('already', 'adv'),
                ('asleep', 'adj'), ('the', 'article'), ('old', 'adj'), ('man', 'intj'),
                ('man', 'noun', 'an adult male\na person\na piece in a game'),
                ('tired', 'adj'), ('and', 'conj'), ('hungry', 'adj'), ('sit', 'verb', 'a sense', ['sat']),
                ('in', 'prep'), ('darkness', 'noun'), ('wind', 'verb', 'a sense', ['wound']), ('clock', 'noun'),
                ('put', 'verb'), ('it', 'pron'), ('down', 'adv'), ('not', 'conj')]
        with tempfile.TemporaryDirectory() as td:
            c = lookup.create(str(Path(td) / 'en.db'))
            for row in rows:
                head, pos = row[0], row[1]
                sense = row[2] if len(row) > 2 else 'a sense'
                forms = row[3] if len(row) > 3 else []
                eid = c.execute('INSERT INTO entry (headword, translit, pos, sense) VALUES (?,?,?,?)',
                                (head, '', pos, sense)).lastrowid
                for form in [head] + forms:
                    c.execute('INSERT INTO form (form, entry_id, note) VALUES (?,?,?)', (form, eid, ''))
            c.executemany('INSERT INTO meta (key, value) VALUES (?,?)',
                          [('lang', 'en'), ('source', 'a fixture'), ('licence', 'none')])
            c.commit()
            c.close()
            self.forget()
            try:
                with patch.object(lookup, 'DICT_DIR', td):
                    self.assertTrue(lookup.available('en'))
                    self.assertEqual(lookup.pos_weights('en', 'man')[0][0], 'noun',
                                     'the reading with the most senses first')
                    self.assertEqual(chunker._class('man', 'en'), 'NOUN')
                    self.assertEqual(chunker._class('not', 'en'), 'NEG',
                                     "the language's own list, not the dictionary's conjunction")
                    self.assertEqual(cut('The old man wound the clock and put it down.', 'en'),
                                     ['The old man', 'wound the clock', 'and put it down.'])
                    self.assertEqual(cut('The old man, tired and hungry, sat in the darkness.', 'en'),
                                     ['The old man,', 'tired and hungry,', 'sat in the darkness.'])
                    self.assertEqual(cut('When I got home, my mother was already asleep.', 'en')[0],
                                     'When I got home,')
            finally:
                self.forget()


if __name__ == '__main__':
    unittest.main()
