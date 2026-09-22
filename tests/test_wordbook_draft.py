# SPDX-License-Identifier: GPL-3.0-or-later
"""A book drafted from its text gets its words at birth (lib/draft.py).

    python3 -m unittest discover -s tests -p test_wordbook_draft.py

Runs under any Python.  The analyzers are stood in for -- words.line patched
-- so the shape of what is written is proved everywhere; where SudachiPy and
spacy-pkuseg really are installed, the real proposals are drafted as well and
every line is held to lib/wordline.py's book door.
"""
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import chunker    # noqa: E402
import draft      # noqa: E402
import languages  # noqa: E402
import wordline   # noqa: E402
import words      # noqa: E402

TEXT = {
    'ja': 'むかしむかし、おじいさんが山へ柴刈りに行きました。\n\n私は（注）東京に住んでいます。',
    'zh': '我想要一杯茶。他不去北京。\n\n今天天气很好。',
}
FIXTURE = {'ja': ROOT / 'tests/fixtures/books/japanese/mini-ja',
           'zh': ROOT / 'tests/fixtures/books/chinese/mini-zh'}
# longer names first, or \chrw is read as \chr and \chw as \ch
MACRO = re.compile(r'\\(chrw|chw|chr|chp|ch)(?![a-zA-Z])')
ARITY = {'chrw': 7, 'chw': 6, 'chr': 6, 'ch': 5, 'chp': 2}


def parts(line):
    """The name and the {...} arguments of one chunk line, braces counted."""
    m = MACRO.match(line)
    args, i = [], m.end()
    while i < len(line) and line[i] == '{':
        depth, j = 0, i
        while True:
            depth += {'{': 1, '}': -1}.get(line[j], 0)
            j += 1
            if depth == 0:
                break
        args.append(line[i + 1:j - 1])
        i = j
    return m.group(1), args, line[i:]


def chunk_lines(tex):
    return [parts(ln) for ln in tex.split('\n') if MACRO.match(ln)]


def stand_in(fa, code):
    """A proposal the way lib/words.py would shape one: a word per character,
    a reading over every kanji or hanzi."""
    L = languages.get(code)
    say = 'よみ' if L.reading else 'dú'
    return wordline.render([(ch, say if wordline.HAN.search(ch) else '')
                            for ch in fa if not ch.isspace()])


class DraftedWords(unittest.TestCase):
    def draft(self, code, how='sentence'):
        return draft.book_from_text(TEXT[code], code, 'title', slug='t', how=how)

    def test_no_proposal_writes_the_draft_it_always_wrote(self):
        with patch.object(draft.words, 'line', lambda fa, code: ''):
            for code, name in (('ja', 'chr'), ('zh', 'ch')):
                tex = self.draft(code)['files']['ch1.tex']
                got = chunk_lines(tex)
                self.assertTrue(got)
                for macro, args, rest in got:
                    self.assertEqual((macro, len(args), rest), (name, ARITY[name], ''))
                    self.assertFalse(any(args[2:]), 'every gloss blank')
                self.assertIn('The last field is the meaning,', tex)
                self.assertNotIn('WORDS', tex)

    def test_a_proposal_is_the_last_argument_and_nothing_else_is_filled(self):
        with patch.object(draft.words, 'line', stand_in):
            for code, name in (('ja', 'chrw'), ('zh', 'chw')):
                L = languages.get(code)
                r = self.draft(code)
                tex = r['files']['ch1.tex']
                got = chunk_lines(tex)
                self.assertEqual(len(got), r['chunks'])
                for macro, args, rest in got:
                    self.assertEqual((macro, len(args), rest), (name, ARITY[name], ''))
                    fa, line = args[1], args[-1]
                    self.assertEqual(line, stand_in(fa, code))
                    # the chunk's reading (kana, or tr without one) starts as
                    # the words' readings run together; the rest stays blank
                    self.assertEqual(args[2], wordline.reading_from(line, L))
                    self.assertTrue(args[2], 'a reading was given')
                    self.assertFalse(any(args[3:-1]), 'everything after the reading stays blank')
                    self.assertEqual(wordline.check(fa, line, L, door=wordline.BOOK)[0], [])
                self.assertIn('The meaning is next to last,', tex)
                self.assertIn("The last field is the chunk's WORDS", tex)
                # the header is TeX comments and nothing else
                head = tex.split('\\chapopen{', 1)[0]
                self.assertTrue(all(ln.startswith('%') for ln in head.split('\n') if ln))

    def test_a_language_without_words_never_asks_for_them(self):
        def refuse(fa, code):
            raise AssertionError('asked for the words of %s' % code)
        with patch.object(draft.words, 'line', refuse):
            tex = draft.book_from_text('مرد پیر در تاریکی نشسته بود.', 'fa', 't',
                                       slug='t')['files']['ch1.tex']
        self.assertEqual([m for m, _a, _r in chunk_lines(tex)], ['ch'])

    def test_a_line_the_book_door_would_refuse_is_not_written(self):
        for bad in ('山(やま)',              # does not rejoin the text
                    '山(やま',               # never closes its reading
                    '山(やま)へ 柴刈り'):      # a reading that does not end its word
            with patch.object(draft.words, 'line', lambda fa, code, bad=bad: bad):
                tex = self.draft('ja')['files']['ch1.tex']
            self.assertEqual({m for m, _a, _r in chunk_lines(tex)}, {'chr'}, bad)
            self.assertNotIn('WORDS', tex)

    def test_a_chapter_with_words_in_some_chunks_says_so(self):
        seen = []

        def some(fa, code):
            seen.append(fa)
            return stand_in(fa, code) if len(seen) % 2 else ''
        with patch.object(draft.words, 'line', some):
            tex = self.draft('zh')['files']['ch1.tex']
        self.assertEqual({m for m, _a, _r in chunk_lines(tex)}, {'chw', 'ch'})
        for macro, args, _rest in chunk_lines(tex):
            self.assertEqual(len(args), ARITY[macro])
        self.assertIn('The meaning is next to last,', tex)
        self.assertIn("The last field is the chunk's WORDS", tex)

    def test_the_chapter_is_still_cut_in_one_call(self):
        calls = []
        real = chunker.chunk_all

        def counted(texts, lang, how=chunker.DEFAULT_WAY):
            calls.append(len(texts))
            return real(texts, lang, how)
        with patch.object(draft.words, 'line', stand_in), \
                patch.object(draft.chunker, 'chunk_all', counted):
            self.draft('zh')
        self.assertEqual(len(calls), 1)

    def test_adding_to_a_book_goes_through_the_same_door(self):
        for code, name in (('ja', 'chrw'), ('zh', 'chw')):
            for where in ('new', 'last'):
                with tempfile.TemporaryDirectory() as td:
                    b = os.path.join(td, 'b')
                    shutil.copytree(FIXTURE[code], b)
                    last = max(draft.chapters_of(b))
                    path = os.path.join(b, 'ch%d.tex' % last)
                    with open(path, encoding='utf-8') as f:
                        was = f.read()
                    calls = []
                    with patch.object(draft.words, 'line', stand_in), \
                            patch.object(draft.chunker, 'chunk_all',
                                         lambda t, l, h, real=chunker.chunk_all:
                                         calls.append(1) or real(t, l, h)):
                        r = draft.add_to_book(b, TEXT[code], how='sentence', chapter=where)
                    self.assertEqual(len(calls), 1, 'one cut for the text added')
                    with open(os.path.join(b, 'ch%d.tex' % r['chapter']), encoding='utf-8') as f:
                        now = f.read()
                    if where == 'last':
                        # what was there is left alone, and the draft header of
                        # the added part is not pasted into the middle of it
                        self.assertTrue(now.startswith(was.split('\\chapend')[0].rstrip('\n')))
                        now = now[len(was.split('\\chapend')[0]):]
                        self.assertNotIn('of a DRAFT', now)
                    self.assertEqual([m for m, _a, _r in chunk_lines(now)],
                                     [name] * r['chunks'], '%s %s' % (code, where))


@unittest.skipUnless(words.available('ja') or words.available('zh'),
                     'no analyzer in %s: the real proposals are not drafted' % sys.executable)
class RealProposals(unittest.TestCase):
    def test_every_line_drafted_passes_the_book_door(self):
        import glob
        for code in ('ja', 'zh'):
            if not words.available(code):
                continue
            L = languages.get(code)
            name = 'chrw' if L.reading else 'chw'
            paras = sorted(glob.glob(str(FIXTURE[code] / 'source/paras/*.txt')))
            fixture = '\n\n'.join(Path(p).read_text(encoding='utf-8').strip() for p in paras)
            for text in (TEXT[code], fixture):
                for how in chunker.WAYS:
                    got = chunk_lines(draft.book_from_text(text, code, 't', slug='t',
                                                           how=how)['files']['ch1.tex'])
                    self.assertTrue(got)
                    for macro, args, rest in got:
                        self.assertEqual((macro, len(args), rest), (name, ARITY[name], ''))
                        errors, _warnings = wordline.check(
                            args[1], args[-1], L, reading='', door=wordline.BOOK)
                        self.assertEqual(errors, [], args[-1])

    def test_drafts_made_at_once_each_get_their_words(self):
        # serve.py drafts in a thread per request, over one analyzer a language
        import threading
        for code, fa in (('ja', '山へ柴刈りに行きました。'), ('zh', '我想要一杯茶。')):
            if not words.available(code):
                continue
            L = languages.get(code)
            alone = draft._chunk_line(fa, L)
            got = []

            def go():
                mine = [draft._chunk_line(fa, L) for _ in range(40)]
                got.extend(mine)
            ts = [threading.Thread(target=go) for _ in range(8)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            self.assertEqual(len(got), 320)
            self.assertEqual(set(got), {alone}, code)


if __name__ == '__main__':
    unittest.main()
