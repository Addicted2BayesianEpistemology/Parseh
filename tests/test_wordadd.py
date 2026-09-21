"""A text added through the doors that wrote no words now gets them proposed.

    python3 -m unittest discover -s tests -p test_wordadd.py

Two doors: lib/assemble.py, which writes a book's chapter from a model's
batch, and draft.video_from_transcript, which starts a video empty (the add
page's "Start it empty", a film on this machine).  A Japanese or Chinese
chunk that comes through either with no word line is given lib/words.py's
proposal, kept only when lib/wordline.py refuses nothing in it.  Every other
chunk -- another language's, a line the model wrote, these languages' where
the analyzers are not in the running Python -- comes out as it always did.

Runs under any Python: the analyzers are stood in for (words.line and
words.available patched), so what is written is proved everywhere.  Where
SudachiPy, spacy-pkuseg and pypinyin are installed the real proposals are made
too; where they are not, the real doors are held to what they wrote before.
"""
import contextlib
import glob
import io
import json
import os
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import books      # noqa: E402
import chunker    # noqa: E402
import draft      # noqa: E402  (puts youtube/lib on the path)
import languages  # noqa: E402
import texparse   # noqa: E402
import wordline   # noqa: E402
import words      # noqa: E402

FIX = ROOT / 'tests' / 'fixtures'
EDITIONS = sorted(glob.glob(str(FIX / 'books' / '*' / '*')))
WORDED = {'ja': str(FIX / 'books/japanese/mini-ja'), 'zh': str(FIX / 'books/chinese/mini-zh')}
VIDEOS = sorted(glob.glob(str(FIX / 'videos' / '*' / '*' / 'video.json')))
ANALYZERS = words.available('ja') or words.available('zh')
# longer names first, or \chrw is read as \chr and \chw as \ch
MACRO = re.compile(r'\\(chrw|chw|chr|chp|ch)(?![a-zA-Z])')
# a chunk of each fixture, a line a model might have written for it, and one
# the book door refuses (the 、/， is missing)
MODEL = {'ja': ('山へ柴刈りに、', '山(やま) へ 柴刈り(しばかり) に 、', '山(やま) へ 柴刈り(しばかり) に'),
         'zh': ('从前，', '从前(cóngqián) ，', '从前(cóngqián)')}
REPORT = re.compile(r'^words proposed for (\d+) of (\d+) chunks$', re.M)
# proposals the doors must drop: the words do not give the text back, or the
# line cannot be read
REFUSED = (('does not rejoin', lambda fa, code, reading="": stand_in(fa, code) + ' 余'),
           ('never closes', lambda fa, code, reading="": stand_in(fa, code) + '('))


def stand_in(fa, code, reading=""):
    """A proposal the way lib/words.py would shape one: a word per character,
    a reading over every kanji or hanzi."""
    say = 'よみ' if languages.get(code).reading else 'dú'
    return wordline.render([(ch, say if wordline.HAN.search(ch) else '')
                            for ch in fa if not ch.isspace()])


def nothing(fa, code, reading=""):
    return ''


@contextlib.contextmanager
def proposing(line=stand_in):
    """As if this Python had the analyzers, and they proposed `line`."""
    with patch.object(words, 'available', lambda code: True), \
            patch.object(words, 'line', line):
        yield


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
    return m.group(1), args


def chunk_lines(tex):
    return [ln for ln in tex.split('\n') if MACRO.match(ln)]


def unworded(tex):
    """The chapter with every \\chrw / \\chw put back as the \\chr / \\ch it
    would have been: the name without its w, the last argument dropped."""
    out = []
    for ln in tex.split('\n'):
        if re.match(r'\\ch(r?)w\{', ln):
            name, args = parts(ln)
            ln = '\\' + name[:-1] + ''.join('{%s}' % a for a in args[:-1])
        out.append(ln)
    return '\n'.join(out)


def chapter(d):
    """A word fixture's chapter as assemble.py writes it: its comments aside."""
    with open(os.path.join(d, 'ch1.tex'), encoding='utf-8') as f:
        return ''.join(ln for ln in f.read().splitlines(True) if not ln.startswith('%'))


def batch(d):
    """Every paragraph of chapter 1 in the annotator's JSON, read back out of
    the .tex -- with no "words", as a model's batch arrives."""
    b = books.Book(d)
    paras = []
    for n, para in enumerate(texparse.parse_book(b.main, b.lang)[0].paragraphs):
        sents = []
        for s in para.subs:
            cs = []
            for c in s.chunks:
                x = {'fa': c.fa, 'tr': c.tr, 'voc': c.voc, 'en': c.en}
                if c.kana:
                    x['kana'] = c.kana
                cs.append(x)
            sents.append({'chunks': cs})
        paras.append({'idx': n, 'ch': 1, 'ann': {'sentences': sents}})
    return {'paragraphs': paras}


def each_chunk(bj):
    return [c for p in bj['paragraphs'] for s in p['ann']['sentences'] for c in s['chunks']]


def given(bj, fa, line):
    for c in each_chunk(bj):
        if c['fa'] == fa:
            c['words'] = line
    return bj


def assemble(d, bj):
    """assemble.py's command line, run in this process so that what a test
    patches is what it imports -> (status, report, the .tex)."""
    with tempfile.TemporaryDirectory() as td:
        bp, out = os.path.join(td, 'batch.json'), os.path.join(td, 'out.tex')
        with open(bp, 'w', encoding='utf-8') as f:
            json.dump(bj, f, ensure_ascii=False)
        argv = ['assemble.py', bp, os.path.join(d, 'source', 'src_ch1.json'), '1', out,
                '--book', d]
        err, rc = io.StringIO(), 0
        with patch.object(sys, 'argv', argv), contextlib.redirect_stderr(err):
            try:
                runpy.run_path(str(ROOT / 'lib' / 'assemble.py'), run_name='__main__')
            except SystemExit as e:
                rc = e.code
        with open(out, encoding='utf-8') as f:
            return rc, err.getvalue(), f.read()


class Assemble(unittest.TestCase):
    def the_chapter_it_always_wrote(self, d, rc, report, tex):
        self.assertEqual(rc, 0, report)
        self.assertIn('ALL PARAGRAPHS CLEAN', report)
        self.assertNotIn('words proposed', report)
        with open(os.path.join(d, 'ch1.tex'), encoding='utf-8') as f:
            self.assertEqual(chunk_lines(tex), chunk_lines(f.read()))
        if d in WORDED.values():
            self.assertEqual(tex, chapter(d))

    def test_nothing_proposable_writes_the_chapter_it_always_wrote(self):
        asked = []

        def refuse(fa, code, reading=""):
            raise AssertionError('asked for the words of %r' % fa)
        with patch.object(words, 'available', lambda code: asked.append(code) or False), \
                patch.object(words, 'line', refuse):
            for d in EDITIONS:
                with self.subTest(d):
                    self.the_chapter_it_always_wrote(d, *assemble(d, batch(d)))
        self.assertEqual(set(asked), set(WORDED), 'only a language with words asks')

    @unittest.skipIf(ANALYZERS, 'the analyzers are in %s' % sys.executable)
    def test_without_the_analyzers_every_edition_is_unchanged(self):
        for d in EDITIONS:
            with self.subTest(d):
                self.the_chapter_it_always_wrote(d, *assemble(d, batch(d)))

    def test_a_chunk_without_words_is_given_the_proposal(self):
        for code, d in WORDED.items():
            with self.subTest(code), proposing():
                bj = batch(d)
                rc, report, tex = assemble(d, bj)
                self.assertEqual(rc, 0, report)
                self.assertIn('ALL PARAGRAPHS CLEAN', report)
                n = str(len(each_chunk(bj)))
                self.assertEqual(REPORT.findall(report), [(n, n)])
                name = 'chrw' if languages.get(code).reading else 'chw'
                for ln in chunk_lines(tex):
                    macro, args = parts(ln)
                    self.assertEqual(macro, name)
                    self.assertEqual(args[-1], stand_in(args[1], code))
                self.assertEqual(unworded(tex), chapter(d), 'and nothing else is changed')

    def test_a_line_the_model_wrote_is_kept_and_judged(self):
        for code, d in WORDED.items():
            fa, good, bad = MODEL[code]
            for line, status in ((good, 0), (bad, 1)):
                with self.subTest((code, line)), proposing():
                    bj = given(batch(d), fa, line)
                    rc, report, tex = assemble(d, bj)
                    self.assertEqual(rc, status, report)
                    n = len(each_chunk(bj))
                    self.assertEqual(REPORT.findall(report), [(str(n - 1), str(n))])
                    lines = {parts(ln)[1][1]: parts(ln)[1][-1] for ln in chunk_lines(tex)}
                    self.assertEqual(lines[fa], line, 'never replaced by the proposal')
                    if status:
                        self.assertIn('words of %r: the words do not reproduce' % fa, report)

    def test_a_blank_line_stays_the_error_it_is(self):
        for code, d in WORDED.items():
            fa = MODEL[code][0]
            with self.subTest(code), proposing():
                rc, report, tex = assemble(d, given(batch(d), fa, '  '))
                self.assertEqual(rc, 1, report)
                self.assertIn('blank words for %r' % fa, report)
                line = next(ln for ln in chunk_lines(tex) if parts(ln)[1][1] == fa)
                self.assertTrue(line.startswith('\\chr{' if code == 'ja' else '\\ch{'), line)

    def test_a_proposal_the_book_door_refuses_is_dropped(self):
        tex_special = ('a LaTeX special', lambda fa, code, reading="": stand_in(fa, code) + ' %')
        for why, line in REFUSED + (tex_special,):
            for code, d in WORDED.items():
                with self.subTest((why, code)), proposing(line):
                    bj = batch(d)
                    rc, report, tex = assemble(d, bj)
                    self.assertEqual(rc, 0, report)
                    self.assertIn('ALL PARAGRAPHS CLEAN', report)
                    self.assertEqual(REPORT.findall(report), [('0', str(len(each_chunk(bj))))])
                    self.assertEqual(tex, chapter(d))

    def test_a_doubted_proposal_is_kept_and_its_doubts_printed(self):
        def bare(fa, code, reading=""):
            return wordline.render([(ch, '') for ch in fa if not ch.isspace()])
        for code, d in WORDED.items():
            with self.subTest(code), proposing(bare):
                rc, report, tex = assemble(d, batch(d))
                self.assertEqual(rc, 0, report)
                self.assertIn('has no reading', report)
                self.assertEqual({parts(ln)[0] for ln in chunk_lines(tex)},
                                 {'chrw' if code == 'ja' else 'chw'})


class VideoDoor:
    """What the video tests share: a fixture's transcript drafted empty, and
    a draft held to the one drafted with no words."""

    def draft(self, vj, how=chunker.DEFAULT_WAY, into=None):
        with open(vj, encoding='utf-8') as f:
            meta = json.load(f)
        with open(os.path.join(os.path.dirname(vj), 'transcript.txt'), encoding='utf-8') as f:
            text = f.read()
        return draft.video_from_transcript(text, meta['language'], video_id=meta['id'],
                                           how=how, into=into)

    @staticmethod
    def language(vj):
        with open(vj, encoding='utf-8') as f:
            return languages.get(json.load(f)['language'])

    def worded(self):
        return [vj for vj in VIDEOS if self.language(vj).words]

    def held(self, r, blank):
        """r's files are `blank`'s but for "words" after "fa" in its chunks,
        every one a line the video door takes -> how many chunks have one."""
        L = languages.get(r['language'])
        ann, n = json.loads(r['files']['annotations.json']), 0
        for sg in ann['segments']:
            if sg.get('plain'):
                self.assertNotIn('chunks', sg)
            for ch in sg.get('chunks', []):
                if 'words' in ch:
                    n += 1
                    self.assertEqual(list(ch)[:2], ['fa', 'words'])
                    self.assertEqual(wordline.check(ch['fa'], ch['words'], L,
                                                    door=wordline.VIDEO)[0], [])
                    # the chunk's reading starts as the words' readings run
                    # together; without words it is the blank it always was
                    field = 'kana' if L.reading else 'tr'
                    self.assertEqual(ch[field], wordline.reading_from(ch['words'], L))
                    ch[field] = ''
                    del ch['words']
        self.assertEqual(json.dumps(ann, ensure_ascii=False, indent=1) + '\n',
                         blank['files']['annotations.json'])
        for name in ('video.json', 'transcript.txt'):
            self.assertEqual(r['files'][name], blank['files'][name])
        return n

    def checks(self, vj):
        """check_annotations passes the draft as written."""
        with tempfile.TemporaryDirectory() as td:
            r = self.draft(vj, into=td)
            p = subprocess.run([sys.executable, str(ROOT / 'youtube/lib/check_annotations.py'),
                                r['dir']], cwd=str(ROOT / 'youtube'),
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn('0 error(s)', p.stdout + p.stderr)


class Video(VideoDoor, unittest.TestCase):
    def test_nothing_proposable_drafts_what_it_always_drafted(self):
        asked = []
        with patch.object(words, 'line', lambda fa, code, reading="": asked.append(code) or ''):
            for vj in VIDEOS:
                with self.subTest(vj):
                    L = self.language(vj)
                    shape = ['fa'] + (['kana'] if L.reading else []) + ['tr', 'voc', 'en']
                    for sg in json.loads(self.draft(vj)['files']['annotations.json'])['segments']:
                        for ch in sg.get('chunks', []):
                            self.assertEqual(list(ch), shape)
        self.assertEqual(set(asked), {'ja', 'zh'}, 'only a language with words asks')

    @unittest.skipIf(ANALYZERS, 'the analyzers are in %s' % sys.executable)
    def test_without_the_analyzers_every_video_is_unchanged(self):
        for vj in VIDEOS:
            for how in chunker.WAYS:
                with self.subTest((vj, how)):
                    real = self.draft(vj, how)
                    with patch.object(words, 'line', nothing):
                        self.assertEqual(self.draft(vj, how), real)

    def test_a_proposal_is_the_key_after_fa(self):
        for vj in self.worded():
            with self.subTest(vj):
                with patch.object(words, 'line', nothing):
                    blank = self.draft(vj)
                with patch.object(words, 'line', stand_in):
                    r = self.draft(vj)
                    self.assertEqual(self.held(r, blank), r['chunks'], 'every chunk')
                    for sg in json.loads(r['files']['annotations.json'])['segments']:
                        for ch in sg.get('chunks', []):
                            self.assertEqual(ch['words'], stand_in(ch['fa'], r['language']))
                    self.checks(vj)

    def test_a_proposal_the_video_door_refuses_is_dropped(self):
        for why, line in REFUSED:
            for vj in self.worded():
                with self.subTest((why, vj)):
                    with patch.object(words, 'line', nothing):
                        blank = self.draft(vj)
                    with patch.object(words, 'line', line):
                        self.assertEqual(self.draft(vj)['files'], blank['files'])

    def test_it_is_the_video_door_that_judges(self):
        # a caption may carry what LaTeX may not: the book door refuses this
        # line, and a video keeps it
        ja, fa, line = languages.get('ja'), '50%の人', '50% の 人(ひと)'
        self.assertTrue(wordline.check(fa, line, ja, door=wordline.BOOK)[0])
        with patch.object(words, 'line', lambda fa, code, reading="": line):
            # and the reading starts as the words', the % kept as the text has it
            self.assertEqual(wordline.reading_from(line, ja), '50%のひと')
            self.assertEqual(draft._blank_chunk(fa, ja),
                             {'fa': fa, 'words': line, 'kana': '50%のひと', 'tr': '', 'voc': '', 'en': ''})


@unittest.skipUnless(ANALYZERS, 'no analyzer in %s: the real proposals are not made' % sys.executable)
class RealProposals(VideoDoor, unittest.TestCase):
    def test_assemble_proposes_what_the_book_door_takes(self):
        for code, d in WORDED.items():
            if not words.available(code):
                continue
            with self.subTest(code):
                L = languages.get(code)
                fa, good, _bad = MODEL[code]
                rc, report, tex = assemble(d, given(batch(d), fa, good))
                self.assertEqual(rc, 0, report)
                self.assertIn('ALL PARAGRAPHS CLEAN', report)
                (proposed, n), = REPORT.findall(report)
                self.assertGreater(int(proposed), 0)
                with tempfile.TemporaryDirectory() as td:
                    path = os.path.join(td, 'ch1.tex')
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(tex)
                    back = texparse.all_chunks([texparse.parse_chapter(path, L)])
                self.assertEqual(len(back), int(n))
                self.assertEqual(sum(1 for c in back if c.wordline), int(proposed) + 1)
                for c in back:
                    if c.fa == fa:
                        self.assertEqual(c.wordline, good, 'the model line is kept')
                    if c.wordline:
                        errors, _doubts = wordline.check(
                            c.fa, c.wordline, L, reading=c.kana if L.reading else c.tr,
                            door=wordline.BOOK)
                        self.assertEqual(errors, [], c.wordline)
                self.assertEqual(unworded(tex), chapter(d), 'and nothing else is changed')

    def test_a_video_drafted_empty_gets_what_the_video_door_takes(self):
        for vj in self.worded():
            if not words.available(self.language(vj).code):
                continue
            for how in chunker.WAYS:
                with self.subTest((vj, how)):
                    with patch.object(words, 'line', nothing):
                        blank = self.draft(vj, how)
                    self.assertGreater(self.held(self.draft(vj, how), blank), 0)
            self.checks(vj)


if __name__ == '__main__':
    unittest.main()
