# SPDX-License-Identifier: GPL-3.0-or-later
"""A draft's reading starts from its words, the checkers do not count that
reading as written while nothing else in the chunk is (a blank chunk is legal
in any book or video, and counted in one note), and every door an annotator
uses starts the words from the machine's.  Also the hub's Books and Studio
doors, which say only how many.

    python3 -m unittest discover -s tests -p test_word_seed.py

Runs under any Python: the analyzers are stood in for (words.line patched).
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
sys.path.insert(0, str(ROOT))
import draft              # noqa: E402  (puts youtube/lib on the path)
import books              # noqa: E402
import check_annotations as CA  # noqa: E402
import check_batch        # noqa: E402
import fill_words         # noqa: E402
import languages          # noqa: E402
import texparse           # noqa: E402
import wordline           # noqa: E402
import ytpages            # noqa: E402

JA, ZH, FA = languages.get('ja'), languages.get('zh'), languages.get('fa')
FIX = ROOT / 'tests' / 'fixtures'
VIDEO = {'ja': FIX / 'videos/japanese/aB3dE5fG7hI', 'zh': FIX / 'videos/chinese/zH8cN2hA6nZ'}


def stand_in(fa, code, reading=""):
    """A proposal shaped as lib/words.py shapes one: a word per character,
    a reading over every kanji or hanzi."""
    say = 'よみ' if languages.get(code).reading else 'dú'
    return wordline.render([(ch, say if wordline.HAN.search(ch) else '')
                            for ch in fa if not ch.isspace()])


def para_json(book):
    """Paragraph 0 of chapter 1, read back out of the .tex the way smoke does."""
    ch = texparse.parse_book(book.main, book.lang)[0]
    sents = []
    for s in ch.paragraphs[0].subs:
        chunks = []
        for c in s.chunks:
            d = {'fa': c.fa, 'tr': c.tr, 'voc': c.voc, 'en': c.en}
            if c.kana:
                d['kana'] = c.kana
            if c.wordline:
                d['words'] = c.wordline
            chunks.append(d)
        sents.append({'chunks': chunks})
    return {'idx': 0, 'ch': 1, 'ann': {'sentences': sents}}


def run_check_batch(para, book_dir, td):
    p = Path(td) / 'p.json'
    p.write_text(json.dumps(para, ensure_ascii=False), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'lib/check_batch.py'), str(p),
                        '--book', str(book_dir)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class ReadingFromTests(unittest.TestCase):
    def test_japanese_runs_the_kana_together_and_keeps_the_marks(self):
        self.assertEqual(wordline.reading_from('山(やま) へ 柴刈り(しばかり) に 、', JA), 'やまへしばかりに、')
        self.assertEqual(wordline.reading_from('テレビ を 見る(みる) 。', JA), 'テレビをみる。')
        self.assertEqual(wordline.reading_from('2024 年(ねん)', JA), '2024ねん')
        self.assertEqual(wordline.reading_from('「 おい 、 待て(まて) ！ 」 と 言った(いった)', JA),
                         '「おい、まて！」といった')

    def test_chinese_parts_the_pinyin_with_spaces_and_writes_the_marks_in_ascii(self):
        self.assertEqual(wordline.reading_from('我(wǒ) 想(xiǎng) 要(yào) 一(yì) 杯(bēi) 茶(chá) 。', ZH),
                         'wǒ xiǎng yào yì bēi chá.')
        self.assertEqual(wordline.reading_from('你好(nǐhǎo) ， OK', ZH), 'nǐhǎo, OK')
        self.assertEqual(wordline.reading_from('他(tā) 说(shuō) ： 「 你好(nǐhǎo) ！ 」', ZH),
                         'tā shuō: "nǐhǎo!"')
        self.assertEqual(wordline.reading_from('等等(děngděng) …… 好(hǎo) 、 行(xíng) 。', ZH),
                         'děngděng... hǎo, xíng.')

    def test_nothing_when_it_cannot_be_read(self):
        self.assertEqual(wordline.reading_from('山 へ', JA), '', 'a kanji word with no reading')
        self.assertEqual(wordline.reading_from('山(やま', JA), '', 'a line that does not parse')
        self.assertEqual(wordline.reading_from([('山', 'やま'), ('へ', '')], JA), 'やまへ')

    def test_the_reading_agrees_with_its_words(self):
        for line, L in (('山(やま) へ 柴刈り(しばかり) に 、', JA), ('我(wǒ) 想(xiǎng) 。', ZH)):
            pairs = wordline.parse(line)
            self.assertIs(wordline.agrees(pairs, wordline.reading_from(line, L), L), True)
            self.assertEqual(wordline.check(''.join(s for s, _ in pairs), line, L,
                                            reading=wordline.reading_from(line, L))[1], [])

    def test_seed_names_the_field(self):
        self.assertEqual(wordline.seed({'fa': '山へ', 'words': '山(やま) へ'}, JA), ('kana', 'やまへ'))
        self.assertEqual(wordline.seed({'fa': '我想', 'words': '我(wǒ) 想(xiǎng)'}, ZH), ('tr', 'wǒ xiǎng'))
        for chunk, L in (({'fa': '山へ'}, JA), ({'fa': '山へ', 'words': ' '}, JA),
                         ({'fa': 'دل', 'words': 'دل'}, FA), ('not a chunk', JA)):
            self.assertEqual(wordline.seed(chunk, L), (None, ''), chunk)


class DraftSeedTests(unittest.TestCase):
    def test_a_video_chunk_reads_its_words(self):
        with patch.object(draft.words, 'line', stand_in):
            c = draft._blank_chunk('山へ行く。', JA)
            self.assertEqual(list(c), ['fa', 'words', 'kana', 'tr', 'voc', 'en'])
            self.assertEqual(c['kana'], wordline.reading_from(c['words'], JA))
            self.assertEqual((c['tr'], c['voc'], c['en']), ('', '', ''))
            z = draft._blank_chunk('我想要茶。', ZH)
            self.assertEqual(list(z), ['fa', 'words', 'tr', 'voc', 'en'])
            self.assertEqual(z['tr'], 'dú dú dú dú.')

    def test_no_words_no_reading(self):
        with patch.object(draft.words, 'line', lambda fa, code, reading="": ''):
            self.assertEqual(draft._blank_chunk('山へ行く。', JA),
                             {'fa': '山へ行く。', 'kana': '', 'tr': '', 'voc': '', 'en': ''})
            self.assertEqual(draft._chunk_line('我想要茶。', ZH), r'\ch{}{我想要茶。}{}{}{}')

    def test_a_book_chunk_reads_its_words(self):
        with patch.object(draft.words, 'line', stand_in):
            line = stand_in('山へ行く。', 'ja')
            self.assertEqual(draft._chunk_line('山へ行く。', JA),
                             r'\chrw{}{山へ行く。}{%s}{}{}{}{%s}' % (wordline.reading_from(line, JA), line))
            zline = stand_in('我想要茶。', 'zh')
            self.assertEqual(draft._chunk_line('我想要茶。', ZH),
                             r'\chw{}{我想要茶。}{dú dú dú dú.}{}{}{%s}' % zline)


class CheckerTests(unittest.TestCase):
    def test_check_batch_counts_a_seeded_reading_as_unwritten(self):
        was = check_batch.LANG
        check_batch.LANG = JA
        try:
            c = {'fa': '山へ', 'words': '山(やま) へ', 'kana': 'やまへ', 'tr': '', 'voc': '', 'en': ''}
            self.assertTrue(check_batch.unwritten(c))
            self.assertFalse(check_batch.unwritten(dict(c, kana='さんへ')), 'a reading somebody changed')
            self.assertFalse(check_batch.unwritten(dict(c, en='to the mountain')))
            self.assertFalse(check_batch.unwritten({k: v for k, v in c.items() if k != 'words'}))
        finally:
            check_batch.LANG = was

    def test_check_annotations_counts_it_given_the_language(self):
        c = {'fa': '我想', 'words': '我(wǒ) 想(xiǎng)', 'tr': 'wǒ xiǎng', 'voc': '', 'en': ''}
        self.assertTrue(CA.unwritten(c, ZH))
        self.assertTrue(CA.unwritten(c, 'zh'))
        self.assertFalse(CA.unwritten(c), 'without the language the old rule counts every field')
        self.assertFalse(CA.unwritten(dict(c, tr='wǒ xiǎng yào'), ZH))

    def test_a_drafted_book_passes_its_checker_and_a_changed_reading_is_asked_for_more(self):
        texts = {'ja': 'むかしむかし、おじいさんが山へ柴刈りに行きました。',
                 'zh': '我想要一杯茶。他不去北京。'}
        for code, text in texts.items():
            with self.subTest(code), tempfile.TemporaryDirectory() as td:
                with patch.object(draft.words, 'line', stand_in):
                    r = draft.book_from_text(text, code, 'title', slug='t', into=td)
                book = books.Book(r['dir'])
                # nothing marks it as a draft: a blank chunk is legal in any book
                self.assertNotIn('draft', book.meta)
                para = para_json(book)
                chunks = [c for s in para['ann']['sentences'] for c in s['chunks']]
                self.assertTrue(all(c.get('words') for c in chunks))
                rc, out = run_check_batch(para, r['dir'], td)
                self.assertEqual(rc, 0, out)
                self.assertIn('0 errors', out)
                # every chunk counted in the one note, the seeded reading included
                self.assertEqual(re.findall(r'note\s+(\d+) of (\d+) chunks have no gloss yet', out),
                                 [(str(len(chunks)), str(len(chunks)))], out)
                self.assertNotIn('no chunk of this paragraph has words', out)
                field = 'kana' if book.lang.reading else 'tr'
                chunks[0][field] = chunks[0][field] + ('あ' if book.lang.reading else ' a')
                rc, out = run_check_batch(para, r['dir'], td)
                self.assertNotEqual(rc, 0, 'a changed reading makes the chunk somebody\'s work')

    def test_a_finished_paragraph_without_any_words_is_warned(self):
        book = books.Book(str(FIX / 'books/japanese/mini-ja'))
        with tempfile.TemporaryDirectory() as td:
            para = para_json(book)
            rc, out = run_check_batch(para, book.dir, td)
            self.assertEqual(rc, 0, out)
            self.assertEqual(out.count('no chunk of this paragraph has words'), 1, out)
            # one chunk with words is enough: a chunk the analyzer proposes
            # nothing for is legal without them
            first = para['ann']['sentences'][0]['chunks'][0]
            first['words'] = stand_in(first['fa'], 'ja')
            rc, out = run_check_batch(para, book.dir, td)
            self.assertNotIn('no chunk of this paragraph has words', out)

    def test_a_drafted_video_passes_its_checker(self):
        for code, where in VIDEO.items():
            with self.subTest(code), tempfile.TemporaryDirectory() as td:
                meta = json.loads((where / 'video.json').read_text(encoding='utf-8'))
                with patch.object(draft.words, 'line', stand_in):
                    r = draft.video_from_transcript((where / 'transcript.txt').read_text(encoding='utf-8'),
                                                    code, video_id=meta['id'], into=td)
                ann = json.loads(r['files']['annotations.json'])
                field = 'kana' if languages.get(code).reading else 'tr'
                chunks = [c for s in ann['segments'] for c in s.get('chunks', [])]
                self.assertTrue(chunks)
                for c in chunks:
                    self.assertEqual(c[field], wordline.reading_from(c['words'], languages.get(code)))
                self.assertNotIn('draft', json.loads(r['files']['video.json']),
                                 'nothing marks it as a draft: a blank chunk is legal in any video')
                p = subprocess.run([sys.executable, str(ROOT / 'youtube/lib/check_annotations.py'), r['dir']],
                                   cwd=str(ROOT / 'youtube'), capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                blank, total = CA.gloss_state(r['dir'])
                self.assertEqual(blank, total, 'every chunk still unwritten')
                self.assertGreater(total, 0)
                self.assertIn('note: %d of %d chunks have no gloss yet' % (blank, total), p.stdout)


class FillJsonTests(unittest.TestCase):
    def setUp(self):
        for target, value in (('line', stand_in), ('available', lambda code: True)):
            p = patch.object(fill_words.words, target, value)
            p.start()
            self.addCleanup(p.stop)
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.td = Path(td.name)

    def write(self, name, doc):
        p = self.td / name
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
        return p

    def quiet(self, *a, **kw):
        return fill_words.fill_json(*a, say=lambda s: None, **kw)

    def test_a_book_paragraph_gets_its_words_and_keeps_its_reading(self):
        p = self.write('p.json', {'idx': 0, 'ch': 1, 'ann': {'sentences': [{'chunks': [
            {'fa': '山へ', 'kana': 'やまへ', 'tr': 'yama e', 'voc': '', 'en': 'to the mountain'},
            {'fa': '行く。', 'words': '行く(いく) 。', 'kana': 'いく', 'tr': 'iku.', 'voc': '', 'en': 'go.'}]}]}})
        r = self.quiet([str(p)], 'ja')
        self.assertEqual((r['given'], r['had'], r['refused']), (1, 1, []))
        first, second = json.loads(p.read_text(encoding='utf-8'))['ann']['sentences'][0]['chunks']
        self.assertEqual(list(first)[:2], ['fa', 'words'])
        self.assertEqual(first['words'], stand_in('山へ', 'ja'))
        self.assertEqual(first['kana'], 'やまへ', 'a reading already written is kept')
        self.assertEqual(second['words'], '行く(いく) 。', 'a line already there is kept')

    def test_a_video_part_gets_a_blank_reading_from_its_words(self):
        p = self.write('01.json', [{'start': 3, 'chunks': [
            {'fa': '山へ', 'kana': '', 'tr': '', 'voc': '', 'en': ''}]}])
        self.quiet([str(p)], 'ja')
        c = json.loads(p.read_text(encoding='utf-8'))[0]['chunks'][0]
        self.assertEqual((c['words'], c['kana']), (stand_in('山へ', 'ja'), 'よみへ'))
        z = self.write('02.json', [{'start': 3, 'chunks': [{'fa': '我想', 'tr': '', 'voc': '', 'en': ''}]}])
        self.quiet([str(z)], 'zh')
        c = json.loads(z.read_text(encoding='utf-8'))[0]['chunks'][0]
        self.assertEqual((list(c)[:2], c['tr']), (['fa', 'words'], 'dú dú'))

    def test_a_dry_run_and_a_refused_line_write_nothing(self):
        doc = [{'start': 3, 'chunks': [{'fa': '山へ', 'kana': '', 'tr': '', 'voc': '', 'en': ''}]}]
        p = self.write('01.json', doc)
        before = p.read_bytes()
        self.assertEqual(self.quiet([str(p)], 'ja', dry_run=True)['given'], 1)
        self.assertEqual(p.read_bytes(), before)
        with patch.object(fill_words.words, 'line', lambda fa, code, reading="": stand_in(fa, code) + ' 余'):
            r = self.quiet([str(p)], 'ja')
        self.assertEqual((r['given'], len(r['refused'])), (0, 1))
        self.assertEqual(p.read_bytes(), before)

    def test_json_needs_a_language(self):
        p = self.write('01.json', [])
        with self.assertRaises(SystemExit):
            fill_words.main(['--json', str(p)])


class PromptTests(unittest.TestCase):
    CAPTIONS = [{'start': 1, 'text': '山へ行く', 'plain': False},
                {'start': 2, 'text': 'hello there', 'plain': True},
                {'start': 3, 'text': '川で遊ぶ', 'plain': False}]

    def proposing(self, yes=True):
        return [patch.object(ytpages.words, 'line', stand_in),
                patch.object(ytpages.words, 'available', lambda code: yes)]

    def test_each_caption_comes_with_the_machines_words(self):
        with self.proposing()[0], self.proposing()[1]:
            got = ytpages.caption_lines(self.CAPTIONS, JA)
            plain = ytpages.caption_lines(self.CAPTIONS)
        lines = got.split('\n')
        self.assertEqual(lines[0], '[0] 1s  山へ行く')
        self.assertEqual(lines[1], '    words: ' + stand_in('山へ行く', 'ja'))
        self.assertTrue(lines[2].startswith('(plain'))
        self.assertEqual(lines[4], '    words: ' + stand_in('川で遊ぶ', 'ja'))
        self.assertNotIn('words:', plain, 'no language, no proposal')

    def test_the_prompt_says_where_the_words_start(self):
        with self.proposing()[0], self.proposing()[1]:
            text = ytpages.chat_prompt(None, JA, None)
        self.assertIn('Start from the `words:` line', text)
        self.assertIn('comes a second line', text)
        with self.proposing(False)[0], self.proposing(False)[1]:
            without = ytpages.chat_prompt(None, JA, None)
        self.assertNotIn('Start from the `words:` line', without)
        for t in (text, without, ytpages.chat_prompt(None, FA, None)):
            self.assertNotIn('{{WORDS_RECEIVED}}', t)

    def test_the_book_prompt_has_the_words_step(self):
        import newbook
        self.assertIn('{{WORDS_STEP}}', (ROOT / 'docs/new-book-prompt.md').read_text(encoding='utf-8'))
        page = newbook.page()
        self.assertIn('WORDS_STEP: wordsStep', page)
        self.assertIn('lib/fill_words.py --lang', page)


class HubTests(unittest.TestCase):
    def test_books_and_studio_say_only_how_many(self):
        import serve
        bks = [{'slug': s, 'title': s, 'latin': s, 'lang': 'ja', 'href': '/books/japanese/%s/reader/' % s,
                'built': built, 'subs': 0, 'timed': 0, 'audio': built} for s, built in (('a', True), ('b', False))]
        with patch.object(serve, 'book_stats', lambda: bks), \
                patch.object(serve.studio.store, 'list_docs', lambda: [{'target': 'fa'}, {'target': 'ja'}]):
            html = serve.hub_page()

        def tags(href):
            door = re.search(r'<a class="door" href="%s">.*?</a>' % re.escape(href), html, re.S).group(0)
            return re.search(r'<div class="tags">(.*?)</div>', door, re.S).group(1)
        def counts(href):
            m = re.search(r'data-counts="([^"]*)"', tags(href))
            return json.loads(m.group(1).replace('&quot;', '"'))

        self.assertTrue(tags('/books/').endswith('>2 books</span>'), tags('/books/'))
        self.assertTrue(tags('/studio/').endswith('>2 documents</span>'), tags('/studio/'))
        # one count per door, which knows what each language has: the chips
        # rewrite it, so nothing lists the languages beside it
        self.assertEqual(counts('/books/')['all'], '2 books')
        self.assertEqual(counts('/books/')['ja'], '2 books')
        self.assertEqual(counts('/books/')['fa'], '0 books')
        self.assertEqual(counts('/studio/')['fa'], '1 document')
        self.assertEqual(counts('/studio/')['ja'], '1 document')
        for name in ('Japanese', 'Persian'):
            self.assertNotIn('%s:' % name, html)
        self.assertIn('channel', tags('/youtube/'), 'the videos door is as it was')
        self.assertIn(' due', tags('/exercises/'), 'the exercises door is as it was')
        self.assertNotIn('narrated', html)
        self.assertNotIn('not built', html)


if __name__ == '__main__':
    unittest.main()
