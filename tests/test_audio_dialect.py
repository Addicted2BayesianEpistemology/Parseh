# SPDX-License-Identifier: GPL-3.0-or-later
"""Recordings in the studio dialect, and flashcards made of blocks
(markdown/exlex/mdparser.py, markdown/app/htmlgen.py, markdown/exlex/texgen.py).

    python3 -m unittest discover -s tests -p test_audio_dialect.py

A recording is written like a picture, `![caption](audio/word.mp3){...}`,
and is laid out and numbered like one.  A jolly flashcard's field may hold
any block content through `key: |`; a field that is one plain paragraph
renders exactly as every card did before, which COMPAT_* below pin byte for
byte against the renderer as it was (commit 95048d0), apart from the card's
wrapper, which stopped being a <button>.

The PDF of tests/fixtures/studio/audio/audio.md is built by
`tests/smoke.py --pdf`; here only the .tex is read."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "lib", ROOT / "youtube" / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import audiofile  # noqa: E402
import htmlgen    # noqa: E402
import mdparser   # noqa: E402
import store      # noqa: E402
import texgen     # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "studio" / "audio" / "audio.md"


def doc(body, target="fa"):
    return "---\ntitle: T\nlang: en\ntarget: %s\n---\n\n%s\n" % (target, body)


def blocks_of(md):
    return mdparser.parse(md)[1]


def tex_body(md):
    fm, blocks = mdparser.parse(md)
    tex = texgen.generate(fm, blocks, colophon=False)
    return tex[tex.index("\\begin{document}"):]


def exercise(md):
    return next(b for b in blocks_of(md) if b["type"] == "exercise")


# three jolly cards of one-line (and one `|` paragraph) fields, a vocab and an
# opposites card, one in a box
COMPAT_MD = (
    '---\n'
    'title: Cards as they were\n'
    'target: fa\n'
    '---\n'
    '\n'
    'A note before the cards[^n].\n'
    '\n'
    '[^n]: A document note that a card cites too.\n'
    '\n'
    ':::exercise flashcard\n'
    'prompt: Test **prompt**.\n'
    'card-type: jolly\n'
    'front-primary: [سلام]{tl}\n'
    'front-secondary: salâm\n'
    'back-primary: hello\n'
    'back-secondary: greeting, see[^n]\n'
    'explanation-correct: Because [this]{tl}.\n'
    ':::\n'
    '\n'
    ':::exercise flashcard\n'
    'card-type: jolly\n'
    'front-primary: سؤال\n'
    'front-secondary: |\n'
    '  first line\n'
    '  second line\n'
    'back-primary: question\n'
    'back-secondary: a **request** for information\n'
    'front-primary-size: 140\n'
    'front-secondary-shade: subdued\n'
    'back-primary-shade: #aa3300\n'
    ':::\n'
    '\n'
    ':::exercise flashcard\n'
    'card-type: vocab\n'
    'target: [کتاب]{tl}\n'
    'reading: ketâb\n'
    'transliteration: ketāb\n'
    'meaning: book\n'
    'context: یک کتاب = *a book*\n'
    'notes: plural کتاب\u200cها\n'
    'source: [Dehkhoda](https://example.org/d)\n'
    'front-image: images/cat.png\n'
    'back-image: images/fig.pdf\n'
    'direction: reverse\n'
    ':::\n'
    '\n'
    ':::exercise flashcard\n'
    'card-type: opposites\n'
    'target: گرم\n'
    'opposite: سرد\n'
    'reading: garm\n'
    'opposite-transliteration: sard\n'
    'notes: hot and cold\n'
    'front-image: images/hot.png\n'
    ':::\n'
    '\n'
    '> :::exercise flashcard\n'
    '> card-type: vocab\n'
    '> front: A boxed card\n'
    '> back: its back\n'
    '> :::\n'
)

# htmlgen.render_document(COMPAT_MD, colophon=False) at 95048d0,
# before cards could hold blocks: one tuple entry per line
COMPAT_READER = (
    '<header class="titleblock">',
    '<h1>Cards as they were</h1>',
    '<div class="titlerule"></div>',
    '</header>',
    '<p data-src-line="5">A note before the cards<span class="fn"><sup class="fnref" tabindex="0" role="button" aria-describedby="fn-1">1</sup><span class="fncloud" role="tooltip" id="fn-1">A document note that a card cites too.</span></span>.</p>',
    '<section class="exercise" data-exercise="1" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="17" data-src-line="9"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button></div><div class="ex-prompt">Test <strong>prompt</strong>.</div><div class="ex-body"><button type="button" class="ex-flashcard" data-card-type="jolly" aria-label="Flip flashcard"><span class="ex-card-front"><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)"><span class="fa fa-l fa-rich" dir="rtl" lang="fa" data-tl-kind="mark" data-tl-src="سلام" data-rtl-kind="mark" data-rtl-src="سلام" data-tl-font="" data-tl-bg="" data-tl-vertical="" data-tl-height="22" data-rtl-font="" data-rtl-bg="">سلام</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">salâm</div></span><span class="ex-card-back" hidden><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">hello</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">greeting, see<span class="fn"><sup class="fnref" tabindex="0" role="button" aria-describedby="fn-2">2</sup><span class="fncloud" role="tooltip" id="fn-2">A document note that a card cites too.</span></span></div></span><small>tap to reveal</small></button></div><div class="ex-explanation ex-explanation-neutral" hidden>Because <span class="fa fa-l fa-rich" dir="rtl" lang="fa" data-tl-kind="mark" data-tl-src="this" data-rtl-kind="mark" data-rtl-src="this" data-tl-font="" data-tl-bg="" data-tl-vertical="" data-tl-height="22" data-rtl-font="" data-rtl-bg="">this</span>.</div></section>',
    '<section class="exercise" data-exercise="2" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="30" data-src-line="19"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button></div><div class="ex-body"><button type="button" class="ex-flashcard" data-card-type="jolly" aria-label="Flip flashcard"><span class="ex-card-front"><div class="ex-card-field primary" style="font-size:140%;color:var(--ink)"><span class="fa fa-l" dir="rtl" lang="fa" data-fa="سؤال" data-occ="0">سؤال</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">first line<br>second line</div></span><span class="ex-card-back" hidden><div class="ex-card-field primary" style="font-size:120%;color:#aa3300">question</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">a <strong>request</strong> for information</div></span><small>tap to reveal</small></button></div></section>',
    '<section class="exercise" data-exercise="3" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="44" data-src-line="32"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button></div><div class="ex-body"><button type="button" class="ex-flashcard" data-card-type="vocab" aria-label="Flip flashcard"><span class="ex-card-front"><span class="ex-card-image-placeholder">images/fig.pdf</span><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">book</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)"><span class="fa fa-l" dir="rtl" lang="fa" data-fa="یک کتاب" data-occ="0">یک کتاب</span> <span class="eq">=</span> <em>a book</em></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">plural <span class="fa fa-l" dir="rtl" lang="fa" data-fa="کتاب\u200cها" data-occ="0">کتاب\u200cها</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)"><a class="lnk" href="https://example.org/d" target="_blank" rel="noopener noreferrer">Dehkhoda</a></div></span><span class="ex-card-back" hidden><span class="ex-card-image-placeholder">images/cat.png</span><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)"><span class="fa fa-l fa-rich" dir="rtl" lang="fa" data-tl-kind="mark" data-tl-src="کتاب" data-rtl-kind="mark" data-rtl-src="کتاب" data-tl-font="" data-tl-bg="" data-tl-vertical="" data-tl-height="22" data-rtl-font="" data-rtl-bg="">کتاب</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">ketâb</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">ketāb</div></span><small>tap to reveal</small></button></div></section>',
    '<section class="exercise" data-exercise="4" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="54" data-src-line="46"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button></div><div class="ex-body"><button type="button" class="ex-flashcard" data-card-type="opposites" aria-label="Flip flashcard"><span class="ex-card-front"><span class="ex-card-image-placeholder">images/hot.png</span><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)"><span class="fa fa-l" dir="rtl" lang="fa" data-fa="گرم" data-occ="0">گرم</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">garm</div></span><span class="ex-card-back" hidden><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)"><span class="fa fa-l" dir="rtl" lang="fa" data-fa="سرد" data-occ="0">سرد</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">sard</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">hot and cold</div></span><small>tap to reveal</small></button></div></section>',
    '<div class="box" data-src-line="56"><section class="exercise" data-exercise="5" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="4"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button></div><div class="ex-body"><button type="button" class="ex-flashcard" data-card-type="vocab" aria-label="Flip flashcard"><span class="ex-card-front"><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">A boxed card</div></span><span class="ex-card-back" hidden><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">its back</div></span><small>tap to reveal</small></button></div></section></div>',
    '<section class="footnotes"><h4>Note</h4><ol><li id="fnlist-1" value="1">A document note that a card cites too.</li><li id="fnlist-2" value="2">A document note that a card cites too.</li></ol></section>',
)

# htmlgen.render_document(COMPAT_MD, colophon=False, editor_preview=True) at 95048d0,
# before cards could hold blocks: one tuple entry per line
COMPAT_PREVIEW = (
    '<header class="titleblock">',
    '<h1>Cards as they were</h1>',
    '<div class="titlerule"></div>',
    '</header>',
    '<p data-src-line="5">A note before the cards<span class="fn"><sup class="fnref" tabindex="0" role="button" aria-describedby="fn-1">1</sup><span class="fncloud" role="tooltip" id="fn-1">A document note that a card cites too.</span></span>.</p>',
    '<section class="exercise" data-exercise="1" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="17" data-editor-preview="1" data-src-line="9"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button><button type="button" class="ex-edit" title="Edit this exercise">✎ Edit</button></div><div class="ex-prompt">Test <strong>prompt</strong>.</div><div class="ex-body"><button type="button" class="ex-flashcard flipped" data-card-type="jolly" aria-label="Flip flashcard"><span class="ex-card-front"><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)"><span class="fa fa-l fa-rich" dir="rtl" lang="fa" data-tl-kind="mark" data-tl-src="سلام" data-rtl-kind="mark" data-rtl-src="سلام" data-tl-font="" data-tl-bg="" data-tl-vertical="" data-tl-height="22" data-rtl-font="" data-rtl-bg="">سلام</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">salâm</div></span><span class="ex-card-back"><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">hello</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">greeting, see<span class="fn"><sup class="fnref" tabindex="0" role="button" aria-describedby="fn-2">2</sup><span class="fncloud" role="tooltip" id="fn-2">A document note that a card cites too.</span></span></div></span><small>front and back shown in preview</small></button></div><div class="ex-explanation ex-explanation-neutral">Because <span class="fa fa-l fa-rich" dir="rtl" lang="fa" data-tl-kind="mark" data-tl-src="this" data-rtl-kind="mark" data-rtl-src="this" data-tl-font="" data-tl-bg="" data-tl-vertical="" data-tl-height="22" data-rtl-font="" data-rtl-bg="">this</span>.</div></section>',
    '<section class="exercise" data-exercise="2" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="30" data-editor-preview="1" data-src-line="19"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button><button type="button" class="ex-edit" title="Edit this exercise">✎ Edit</button></div><div class="ex-body"><button type="button" class="ex-flashcard flipped" data-card-type="jolly" aria-label="Flip flashcard"><span class="ex-card-front"><div class="ex-card-field primary" style="font-size:140%;color:var(--ink)"><span class="fa fa-l" dir="rtl" lang="fa" data-fa="سؤال" data-occ="0">سؤال</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">first line<br>second line</div></span><span class="ex-card-back"><div class="ex-card-field primary" style="font-size:120%;color:#aa3300">question</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">a <strong>request</strong> for information</div></span><small>front and back shown in preview</small></button></div></section>',
    '<section class="exercise" data-exercise="3" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="44" data-editor-preview="1" data-src-line="32"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button><button type="button" class="ex-edit" title="Edit this exercise">✎ Edit</button></div><div class="ex-body"><button type="button" class="ex-flashcard flipped" data-card-type="vocab" aria-label="Flip flashcard"><span class="ex-card-front"><span class="ex-card-image-placeholder">images/fig.pdf</span><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">book</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)"><span class="fa fa-l" dir="rtl" lang="fa" data-fa="یک کتاب" data-occ="0">یک کتاب</span> <span class="eq">=</span> <em>a book</em></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">plural <span class="fa fa-l" dir="rtl" lang="fa" data-fa="کتاب\u200cها" data-occ="0">کتاب\u200cها</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)"><a class="lnk" href="https://example.org/d" target="_blank" rel="noopener noreferrer">Dehkhoda</a></div></span><span class="ex-card-back"><span class="ex-card-image-placeholder">images/cat.png</span><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)"><span class="fa fa-l fa-rich" dir="rtl" lang="fa" data-tl-kind="mark" data-tl-src="کتاب" data-rtl-kind="mark" data-rtl-src="کتاب" data-tl-font="" data-tl-bg="" data-tl-vertical="" data-tl-height="22" data-rtl-font="" data-rtl-bg="">کتاب</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">ketâb</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">ketāb</div></span><small>front and back shown in preview</small></button></div></section>',
    '<section class="exercise" data-exercise="4" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="54" data-editor-preview="1" data-src-line="46"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button><button type="button" class="ex-edit" title="Edit this exercise">✎ Edit</button></div><div class="ex-body"><button type="button" class="ex-flashcard flipped" data-card-type="opposites" aria-label="Flip flashcard"><span class="ex-card-front"><span class="ex-card-image-placeholder">images/hot.png</span><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)"><span class="fa fa-l" dir="rtl" lang="fa" data-fa="گرم" data-occ="0">گرم</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">garm</div></span><span class="ex-card-back"><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)"><span class="fa fa-l" dir="rtl" lang="fa" data-fa="سرد" data-occ="0">سرد</span></div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">sard</div><div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">hot and cold</div></span><small>front and back shown in preview</small></button></div></section>',
    '<div class="box" data-src-line="56"><section class="exercise" data-exercise="5" data-subtype="flashcard" data-primitive="flashcard" data-scored="0" data-src-end="4" data-editor-preview="1"><div class="ex-head"><span class="ex-kicker">Flashcard</span><button type="button" class="ex-card-zoom" title="Open this card large, over the page">⤢ Enlarge</button></div><div class="ex-body"><button type="button" class="ex-flashcard flipped" data-card-type="vocab" aria-label="Flip flashcard"><span class="ex-card-front"><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">A boxed card</div></span><span class="ex-card-back"><div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">its back</div></span><small>front and back shown in preview</small></button></div></section></div>',
    '<section class="footnotes"><h4>Note</h4><ol><li id="fnlist-1" value="1">A document note that a card cites too.</li><li id="fnlist-2" value="2">A document note that a card cites too.</li></ol></section>',
)


class ParseTests(unittest.TestCase):
    def test_an_audio_line_is_a_block_of_its_own(self):
        b = blocks_of(doc("![Lesson](audio/lesson.m4a){width=40 align=right offset=-5 "
                          "start=1:05.2 end=1:09}"))[0]
        self.assertEqual({"type": "audio", "_line": 6, "caption": "Lesson",
                          "path": "audio/lesson.m4a", "valid": True, "width": 40,
                          "align": "right", "offset": -5, "start": 65.2, "end": 69}, b)
        plain = blocks_of(doc("![](audio/word.mp3)"))[0]
        self.assertEqual(("audio", True, 60, "left", 0, None, None),
                         (plain["type"], plain["valid"], plain["width"], plain["align"],
                          plain["offset"], plain["start"], plain["end"]))
        # a picture is still a picture
        self.assertEqual("image", blocks_of(doc("![](images/word.mp3)"))[0]["type"])

    def test_which_paths_are_recordings(self):
        good = ["audio/word.mp3", "audio/Word-2.MP3", "audio/a.m4a", "audio/a.aac",
                "audio/a.ogg", "audio/a.oga", "audio/a.opus", "audio/a.wav",
                "audio/a.flac", "audio/a.webm", "audio/x.y_z.mp3"]
        bad = ["audio/word.txt", "audio/word", "audio/.mp3", "audio/-x.mp3",
               "audio/sub/word.mp3", "audio/wörd.mp3", "audio/word.mp4"]
        for path in good + bad:
            b = blocks_of(doc("![c](%s)" % path))[0]
            self.assertEqual(("audio", path in good), (b["type"], b["valid"]), path)
            # the parser's copy says what lib/audiofile.py says
            self.assertEqual(bool(audiofile.PATH_RE.match(path)),
                             bool(mdparser.AUDIO_PATH_RE.match(path)), path)
        self.assertEqual(tuple(audiofile.EXTS), mdparser.AUDIO_EXTS)
        # not under audio/: an (invalid) picture, as before
        b = blocks_of(doc("![c](word.mp3)"))[0]
        self.assertEqual(("image", False), (b["type"], b["valid"]))

    def test_times_take_a_fraction_on_the_seconds(self):
        cases = {"90": 90, "1:30": 90, "1:02:03": 3723, "65.5": 65.5,
                 "1:05.25": 65.25, "1:05.2": 65.2, "0:00.25": 0.25, "1:05.0": 65,
                 "5.": 5, ".5": 0.5, "0.333": 0.33, "-5": 0, "-1.5": 0,
                 "abc": None, "1.5:30": None, "": None, ".": None, "1:": None}
        for raw, want in cases.items():
            got = mdparser.parse_time(raw)
            self.assertEqual(want, got, raw)
            self.assertIs(type(want), type(got), raw)

    def test_a_clip_time_is_written_by_one_formatter(self):
        # the studio's layout editor writes `start=`/`end=` with it, the page's
        # media fragment and data-start/data-end with it: parse_time reads back
        # exactly what it wrote
        cases = {65: "65", 65.0: "65", 65.5: "65.5", 65.25: "65.25", 1.25: "1.25",
                 0: "0", 0.1: "0.1", 69.254: "69.25", 0.999: "1", 2.005: "2"}
        for v, want in cases.items():
            self.assertEqual(want, mdparser.clip_seconds(v), v)
            self.assertEqual(round(v, 2), mdparser.parse_time(mdparser.clip_seconds(v)), v)
        self.assertFalse(hasattr(store, "_seconds") or hasattr(htmlgen, "_time_attr"),
                         "no second copy of the formatter")
        src = "![w](audio/w.mp3)\n"
        self.assertIn("start=1.25 end=69.25}",
                      store.image_layout_markdown(src, 0, 60, "left", 0, start=1.25, end=69.254))
        html = htmlgen.render_document(doc("![w](audio/w.mp3){start=1.25 end=69.25}"),
                                       asset_base="/m/")["html"]
        self.assertIn('src="/m/audio/w.mp3#t=1.25,69.25"', html)
        self.assertIn('data-start="1.25" data-end="69.25"', html)

    def test_a_clip_window_is_cut_by_one_rule(self):
        self.assertIs(store.clip_window, texgen.clip_window, "the studio's editor uses the renderers' rule")
        for start, end, want in ((None, 0, (None, None)), (0, 0, (0, None)), (2, 1.5, (2, None)),
                                 (None, 3, (None, 3)), (1.5, 3, (1.5, 3)), (5, 5, (5, None))):
            self.assertEqual(want, texgen.clip_window(start, end), (start, end))
            self.assertEqual(want, texgen.audio_window({"start": start, "end": end}), (start, end))
            self.assertEqual(want, store._clip_window(start, end, whole=False), (start, end))

    def test_a_time_too_long_to_be_one_is_no_time(self):
        # a float of 309 digits is infinite, and one minute of 400 digits
        # overflows a float: unreadable, not a crash of every page render
        for raw in ("9" * 400 + ".5", "9" * 400 + ":5.5", "1:" + "9" * 400 + ".5"):
            self.assertIsNone(mdparser.parse_time(raw), raw[:12])
        # a whole number stays whole, however long, as it always did
        self.assertEqual(10 ** 400, mdparser.parse_time("1" + "0" * 400))
        big = "9" * 400 + ".5"
        md = doc("![c](audio/a.mp3){start=%s end=%s}\n\n@[v](https://youtu.be/nFoM8JraEek){start=%s}\n\n"
                 "![c](images/a.png){end=%s}" % (big, big, big, big))
        html = htmlgen.render_document(md, asset_base="/m/")["html"]
        self.assertIn('src="/m/audio/a.mp3"', html)
        self.assertIn("embed/nFoM8JraEek?rel=0\"", html)
        self.assertIn("audio · a.mp3}", tex_body(md))

    def test_a_block_field_keeps_its_text_as_written(self):
        body = [":::exercise flashcard", "card-type: jolly",
                "front-primary: one line", "front-secondary: |", "",
                "    - item", "      - nested", "    ", "    | a | b |",
                "    |---|---|", "    | 1 | 2 |", "", "back-primary: |",
                "\ttabbed", "back-secondary: x", ":::"]
        b = exercise(doc("\n".join(body)))
        self.assertEqual([], b["errors"])
        self.assertEqual({"front-secondary": "- item\n  - nested\n\n| a | b |\n|---|---|\n| 1 | 2 |",
                          "back-primary": "tabbed"}, b["raw_fields"])
        # the inline value is what it always was
        old = lambda lines: " ⏎ ".join(x.lstrip() for x in lines).strip()
        self.assertEqual(old(body[4:12]), b["fields"]["front-secondary"])
        self.assertEqual("⏎ - item ⏎ - nested ⏎  ⏎ | a | b | ⏎ |---|---| ⏎ | 1 | 2 | ⏎",
                         b["fields"]["front-secondary"])
        self.assertEqual("one line", b["fields"]["front-primary"])
        self.assertNotIn("front-primary", b["raw_fields"])
        self.assertEqual({}, exercise(doc(":::exercise yes-no\n- Is it? => yes\n:::"))["raw_fields"])
        # and parses into the blocks it spells
        fields = mdparser.card_field(b, "front-secondary", "fa")
        self.assertEqual("blocks", fields[0])
        self.assertEqual(["list", "table"], [x["type"] for x in fields[1]])
        self.assertEqual([[0, "item"], [2, "nested"]], fields[1][0]["items"])

    def test_a_note_excerpt_leaves_a_recording_out(self):
        import notes
        self.assertEqual("Before.\nAfter.",
                         notes.excerpt(doc("Before.\n\n![Said](audio/word.mp3){start=1.5}\n\nAfter.")))

    def test_stats_count_recordings_apart(self):
        md = doc("![a](audio/a.mp3)\n\n![p](images/p.png)\n\n"
                 "@[v](https://youtu.be/nFoM8JraEek)\n\n> ![b](audio/b.mp3)\n\n"
                 ":::exercise flashcard\ncard-type: jolly\nfront-primary: ![c](audio/c.mp3)\n"
                 "back-primary: x\n:::")
        stats = htmlgen.render_document(md)["stats"]
        self.assertEqual((2, 2), (stats["images"], stats["audio"]))
        self.assertEqual(stats, htmlgen.stats(md, blocks_of(md), target="fa"))


class FlashcardValidationTests(unittest.TestCase):
    def errors(self, body):
        return exercise(doc(":::exercise flashcard\n%s\n:::" % body))["errors"]

    def test_recording_fields_name_a_file_under_audio(self):
        self.assertEqual([], self.errors("target: x\nfront-audio: audio/x.mp3\nback-audio: audio/y.WAV"))
        self.assertEqual(["front-audio must name a file under audio/ (e.g. audio/word.mp3)"],
                         self.errors("target: x\nfront-audio: x.mp3"))
        self.assertEqual(["back-audio must name a file under audio/ (e.g. audio/word.mp3)"],
                         self.errors("card-type: opposites\ntarget: a\nopposite: b\n"
                                     "back-audio: audio/y.txt"))
        self.assertEqual(["front-audio must name a file under audio/ (e.g. audio/word.mp3)",
                          "back-audio must name a file under audio/ (e.g. audio/word.mp3)"],
                         self.errors("target: x\nfront-audio: images/x.png\nback-audio: audio/"))

    def test_a_jolly_card_needs_one_field_a_side(self):
        self.assertEqual([], self.errors("card-type: jolly\nfront-secondary: a\nback-primary: b"))
        self.assertEqual([], self.errors("card-type: jolly\nfront-primary: |\n  - a\nback-secondary: b"))
        need = ["a Jolly flashcard needs a front field and a back field"]
        self.assertEqual(need, self.errors("card-type: jolly\nfront-primary: a\nfront-secondary: b"))
        self.assertEqual(need, self.errors("card-type: jolly\nback-primary: a"))

    def test_a_card_cannot_hold_an_exercise(self):
        md = doc(":::exercise flashcard\ncard-type: jolly\nfront-primary: |\n"
                 "  :::exercise yes-no\n  - Is it? => yes\nback-primary: b\n:::\n\n"
                 ":::exercise yes-no\n- After? => yes\n:::")
        b = exercise(md)
        self.assertEqual(["front-primary cannot hold an exercise"], b["errors"])
        html = htmlgen.render_document(md)["html"]
        self.assertEqual(["1", "2"], re.findall(r'data-exercise="(\d+)"', html))

    def test_not_even_in_a_box_on_the_card(self):
        for field in ("front-primary: |\n  > :::exercise yes-no\n  > - Is it? => yes\n  > :::\n  > after",
                      "front-primary: > :::exercise yes-no",
                      "front-primary: |\n  > A box\n  >\n  > > :::exercise yes-no\n  > > - Is it? => yes\n  > > :::"):
            md = doc(":::exercise flashcard\ncard-type: jolly\n%s\nback-primary: hello\n:::" % field)
            self.assertEqual(["front-primary cannot hold an exercise"], exercise(md)["errors"], field)
            html = htmlgen.render_document(md)["html"]
            self.assertIn('<div class="ex-invalid">', html)
            self.assertNotIn("ex-flashcard", html)
        # the words `:::exercise` in a sentence are only words
        self.assertEqual([], self.errors("card-type: jolly\nfront-primary: |\n  write :::exercise yes-no\n"
                                         "back-primary: hello"))


class AudioHtmlTests(unittest.TestCase):
    def test_a_clipped_recording(self):
        html = htmlgen.render_document(
            doc("![Lesson [سلام]{tl}](audio/lesson.m4a){width=60 align=center offset=0 "
                "start=1:05.2 end=1:09}\n\n![Lesson](audio/lesson.m4a){width=60 align=center "
                "offset=0 start=1:05.2 end=1:09}"),
            asset_base="/media/doc-1/")["html"]
        # the first line's caption holds brackets: not a figure at all
        self.assertIn("<p data-src-line=\"6\">", html)
        self.assertIn(
            '<figure class="img audio align-center" data-idx="0" data-width="60" '
            'data-align="center" data-offset="0" data-start="65.2" data-end="69" '
            'style="width:60%;margin-left:20.00%" data-src-line="8">'
            '<audio controls preload="metadata" src="/media/doc-1/audio/lesson.m4a#t=65.2,69">'
            '</audio><button class="audio-edit" type="button" title="Layout &amp; clip">'
            '⚙ layout</button><figcaption>Lesson</figcaption></figure>', html)

    def test_the_fragment_and_the_window(self):
        def figure(attrs):
            html = htmlgen.render_document(doc("![](audio/a.mp3){%s}" % attrs),
                                           asset_base="/m/")["html"]
            return re.search(r"<figure[^>]*>.*?</figure>", html).group(0)
        f = figure("start=0.25")
        self.assertIn('src="/m/audio/a.mp3#t=0.25"', f)
        self.assertIn('data-start="0.25" style=', f)
        self.assertNotIn("data-end", f)
        f = figure("end=9")
        self.assertIn('src="/m/audio/a.mp3#t=0,9"', f)
        self.assertNotIn("data-start", f)
        f = figure("start=12 end=12")          # no window's end
        self.assertIn('src="/m/audio/a.mp3#t=12"', f)
        self.assertNotIn("data-end", f)
        # with no start the window starts at 0, so an end at 0 (or what
        # rounds to it) ends nothing either: `#t=0,0` would never play
        for attrs in ("end=0", "end=0.001", "start=0 end=0"):
            f = figure(attrs)
            self.assertNotIn("data-end", f, attrs)
            self.assertNotIn(",0", f, attrs)
        self.assertIn('src="/m/audio/a.mp3"', figure("end=0"))
        self.assertIn('src="/m/audio/a.mp3#t=0"', figure("start=0 end=0"))
        f = figure("width=30")
        self.assertIn('src="/m/audio/a.mp3"', f)
        self.assertNotIn("#t=", f)
        self.assertNotIn("data-start", f)
        # no caption, no figcaption
        self.assertNotIn("figcaption", f)

    def test_without_a_file_store_and_with_a_bad_path(self):
        html = htmlgen.render_document(doc("![Word](audio/word.mp3)\n\n![Bad](audio/word.txt)\n\n"
                                           "![Pic](images/p.png)"))["html"]
        self.assertIn('<figure class="img audio align-left" data-idx="0" data-width="60" '
                      'data-align="left" data-offset="0" style="width:60%;margin-left:0.00%" '
                      'data-src-line="6"><div class="img-placeholder">🔊 <code>audio/word.mp3'
                      '</code></div><button class="audio-edit" type="button" title="Layout &amp; '
                      'clip">⚙ layout</button><figcaption>Word</figcaption></figure>', html)
        self.assertIn('<div class="img-missing" data-src-line="8">not an audio file: '
                      '<code>audio/word.txt</code></div>', html)
        # the bad line still takes its number, as store's line scan counts it
        self.assertIn('data-idx="2"', html)
        self.assertNotIn("<audio", html)

    def test_one_counter_for_pictures_videos_and_recordings_boxed_or_not(self):
        html = htmlgen.render_document(doc(
            "![p](images/p.png)\n\n![a](audio/a.mp3)\n\n@[v](https://youtu.be/nFoM8JraEek)\n\n"
            "> In a box:\n>\n> ![b](audio/b.ogg)\n\n![c](audio/c.flac)"), asset_base="/m/")["html"]
        order = re.findall(r'<figure class="img( [a-z]+)? align-left" data-idx="(\d+)"', html)
        self.assertEqual([("", "0"), (" audio", "1"), (" video", "2"), (" audio", "3"),
                          (" audio", "4")], order)
        boxed = html[html.index('<div class="box"'):]
        boxed = boxed[:boxed.index("</div>")]
        self.assertIn('data-idx="3"', boxed)
        self.assertNotIn("data-src-line", boxed[boxed.index("<figure"):])

    def test_a_video_time_stays_whole_seconds(self):
        md = doc("@[v](https://youtu.be/nFoM8JraEek){start=116.6 end=140.25}")
        html = htmlgen.render_document(md)["html"]
        self.assertIn("embed/nFoM8JraEek?rel=0&amp;start=116&amp;end=140&amp;enablejsapi=1", html)
        self.assertIn('data-start="116" data-end="140"', html)
        tex = tex_body(md)
        self.assertIn("https://youtu.be/nFoM8JraEek?t=116}", tex)
        self.assertIn("video YouTube · 1:56–2:20}", tex)


# The renderer before cards held blocks, on cards that hold none: the output
# must be the same bytes apart from the wrapper -- <div role="button"> for
# <button>, <div> sides for <span> ones, the hint's class, aria-pressed --
# and apart from the two fields that are one target-language paragraph,
# which the page draws as a block and the card now draws as the page does
# (the card keeps giving them its size and its place: app.css).
def rewrapped(old_lines, preview):
    html = "\n".join(old_lines)
    html = re.sub(
        r'<button type="button" class="ex-flashcard( flipped)?" data-card-type="([a-z]+)" '
        r'aria-label="Flip flashcard"><span class="ex-card-front">',
        lambda m: ('<div class="ex-flashcard%s" role="button" tabindex="0" data-card-type="%s" '
                   'aria-label="Flip flashcard" aria-pressed="%s"><div class="ex-card-front">'
                   % (m.group(1) or "", m.group(2), "true" if preview else "false")), html)
    html = html.replace('</span><span class="ex-card-back"', '</div><div class="ex-card-back"')
    html = html.replace("</span><small>", '</div><small class="ex-card-hint">')
    html = html.replace("</small></button>", "</small></div>")
    # `front-primary: [سلام]{tl}` -- a marked target run, now the target
    # block it is on the page (and, being a block, offered to no editor)
    html = re.sub(r'<span class="fa fa-l fa-rich" dir="rtl" lang="fa" data-tl-kind="mark" '
                  r'data-tl-src="سلام" data-rtl-kind="mark" data-rtl-src="سلام" ([^>]*)>سلام</span>',
                  r'<p class="fa-par" dir="rtl" lang="fa" \1>سلام</p>', html)
    # A vocabulary card's marked target is also a standalone exercise cell.
    html = re.sub(r'(<div class="ex-card-field primary"[^>]*>)(<span class="fa fa-l fa-rich" '
                  r'dir="rtl" lang="fa" data-tl-kind="mark" data-tl-src="کتاب"[^>]*>کتاب</span>)(</div>)',
                  r'\1<span class="ex-target-block" dir="rtl" lang="fa">\2</span>\3', html)
    # a target block the overlay can open says which of the blocks with its
    # text it is, counted in the order of the source (data-tl-occ): each of
    # these is the only one
    html = re.sub(r'( data-tl-src="[^"]*")( data-rtl-kind=)', r'\1 data-tl-occ="0"\2', html)
    # `front-primary: سؤال` -- a line of nothing but the target script, now
    # the display line it is on the page
    return html.replace('<span class="fa fa-l" dir="rtl" lang="fa" data-fa="سؤال" data-occ="0">سؤال</span>',
                        '<p class="fa-display"><span class="fa fa-l" dir="rtl" lang="fa">سؤال</span></p>')


class FlashcardHtmlTests(unittest.TestCase):
    def test_cards_without_blocks_render_as_they_always_did(self):
        for lines, preview in ((COMPAT_READER, False), (COMPAT_PREVIEW, True)):
            want = rewrapped(lines, preview)
            self.assertEqual(5, want.count('role="button" tabindex="0" data-card-type='))
            self.assertNotIn("<button type=\"button\" class=\"ex-flashcard", want)
            got = htmlgen.render_document(COMPAT_MD, colophon=False, editor_preview=preview)["html"]
            self.assertEqual(2, got.count('class="ex-translit-switch"'))
            self.assertEqual(2, got.count('ex-card-transliteration'))
            without_toggle = got.replace('<button type="button" class="ex-translit-switch" '
                                         'aria-pressed="false"></button>', '')
            without_toggle = without_toggle.replace(' secondary ex-card-transliteration', ' secondary')
            self.assertEqual(want, without_toggle)

    RICH = (":::exercise flashcard\ncard-type: jolly\nfront-primary: |\n"
            "  ## A heading on the card\n  ### [سلام]{tl}\n  ## کتاب | ketâb\n"
            "  ![Said](audio/salam.mp3){width=80 align=center offset=0 start=0.5}\n"
            "front-secondary: salâm\nback-primary: |\n"
            "  **hello**, a note[^card].\n\n"
            "  | Persian | English |\n  |---|---|\n  | سلام | hello |\n\n"
            "  - on arriving\n    - and leaving\n\n"
            "  ![Picture](images/p.png){width=40}\n\n"
            "  @[Clip](https://youtu.be/nFoM8JraEek){start=3}\n\n"
            "  > A box on the card.\n\n"
            "  [^card]: Written inside the card.\n"
            "back-secondary: see[^doc]\n:::")

    def rich(self, **kw):
        md = doc("![Before](audio/before.mp3)\n\n" + self.RICH +
                 "\n\n## After the card\n\n![After](images/after.png)\n\n[^doc]: The document's note.")
        return htmlgen.render_document(md, asset_base="/m/", **kw)

    def card(self, html):
        start = html.index('<div class="ex-flashcard')
        return html[start:html.index('<small class="ex-card-hint">', start)]

    def test_a_card_made_of_blocks(self):
        out = self.rich()
        card = self.card(out["html"])
        self.assertEqual(4, card.count('<div class="ex-card-field ex-card-blocks primary"')
                         + card.count('<div class="ex-card-field secondary"')
                         + card.count('<div class="ex-card-field ex-card-blocks secondary"'))
        for piece in ('<table class="bt">', "<ul><li>on arriving<ul><li>and leaving</li></ul></li></ul>",
                      '<img src="/m/images/p.png" alt="Picture">',
                      '<audio controls preload="metadata" src="/m/audio/salam.mp3#t=0.5"></audio>',
                      '<div class="video-box"><iframe src="https://www.youtube-nocookie.com/embed/nFoM8JraEek?rel=0&amp;start=3',
                      '<div class="box"><p>A box on the card.</p></div>',
                      "<strong>hello</strong>, a note"):
            self.assertIn(piece, card)
        # a figure on a card is no layout target, and moves no number
        self.assertNotIn("data-idx", card)
        self.assertNotIn("audio-edit", card)
        self.assertNotIn("video-edit", card)
        self.assertNotIn("data-src-line", card)
        self.assertEqual(["0", "1"], re.findall(r'data-idx="(\d+)"', out["html"]))
        self.assertIn('<figcaption>After</figcaption>', out["html"][out["html"].index('data-idx="1"'):])
        # the text fields keep their inline form beside the block ones
        self.assertIn('<div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">salâm</div>', card)
        self.assertIn('<div class="ex-card-field ex-card-blocks primary" style="font-size:120%;color:var(--ink)"><h2 class="section">', card)

    def test_headings_on_a_card_are_labels(self):
        out = self.rich()
        card = self.card(out["html"])
        self.assertIn('<h2 class="section">A heading on the card</h2>', card)
        self.assertIn('<h3 class="subsection"><span class="fa fa-l fa-rich"', card)
        self.assertIn('<section class="voce"><div class="voce-head">', card)
        self.assertIsNone(re.search(r' id="(sec|sub|voce)-', card))
        self.assertNotIn("secnum", card)
        self.assertEqual(['<a class="toc-sec" href="#sec-1"><span class="secnum">1.</span> After the card</a>'],
                         re.findall(r"<a [^>]*>.*?</a>", out["toc"]))
        self.assertIn('<h2 class="section" id="sec-1"', out["html"])

    def test_a_footnote_written_inside_a_card(self):
        html = self.rich()["html"]
        card = self.card(html)
        self.assertIn('<span class="fncloud" role="tooltip" id="fn-1">Written inside the card.</span>', card)
        self.assertIn('<span class="fncloud" role="tooltip" id="fn-2">The document&#x27;s note.</span>', card)
        self.assertIn('<li id="fnlist-1" value="1">Written inside the card.</li>', html)

    def test_a_note_cited_before_the_field_that_defines_it(self):
        # the natural place for a card's notes is its end: a front field
        # citing one written in a back field gets its text
        md = doc(":::exercise flashcard\ncard-type: jolly\nprompt: A prompt[^p].\n"
                 "front-primary: the word[^w]\nfront-secondary: |\n  - one[^x]\n  - two\n"
                 "back-primary: |\n  the meaning\n\n  [^w]: Defined at the end of the card.\n"
                 "back-secondary: |\n  **x**\n\n  [^x]: Defined after its list.\n\n  [^p]: The prompt's.\n:::")
        html = htmlgen.render_document(md)["html"]
        for n, text in ((1, "The prompt&#x27;s."), (2, "Defined at the end of the card."),
                        (3, "Defined after its list.")):
            self.assertIn('<span class="fncloud" role="tooltip" id="fn-%d">%s</span>' % (n, text), html)
            self.assertIn('<li id="fnlist-%d" value="%d">%s</li>' % (n, n, text), html)
        body = tex_body(md)
        self.assertIn("\\footnotetext[1]{The prompt's.}\\stepcounter{footnote}\n"
                      "\\footnotetext[2]{Defined at the end of the card.}\\stepcounter{footnote}\n"
                      "\\footnotetext[3]{Defined after its list.}\\stepcounter{footnote}", body)
        self.assertNotIn("\\footnotetext[2]{}", body)

    def test_a_field_is_never_left_empty(self):
        # what parses to no block at all (a rule, a lone definition) shows
        # its text as every card did; a `#` heading is a heading on the card,
        # where a document would have taken it for its title
        md = doc(":::exercise flashcard\ncard-type: jolly\nfront-primary: # 1 rule of the club\n"
                 "front-secondary: ---\nback-primary: |\n  # Big word\n\n  the rest\n"
                 "back-secondary: [^n]: only a note\n:::\n\n***\n\n:::exercise flashcard\n"
                 "card-type: jolly\nfront-primary: ***\nback-primary: |\n  ___\n:::")
        self.assertEqual([[], []], [b["errors"] for b in blocks_of(md) if b["type"] == "exercise"])
        out = htmlgen.render_document(md)
        html = out["html"]
        front, back = self.sides(html)
        self.assertIn('<h2 class="section">1 rule of the club</h2>', front)
        self.assertIn('<div class="ex-card-field secondary" style="font-size:88%;color:var(--graytx)">---</div>', front)
        self.assertIn('<h2 class="section">Big word</h2>\n<p>the rest</p>', back)
        self.assertIn(': only a note</div>', back)
        self.assertEqual("T", out["title"])
        second = html[html.index('data-exercise="2"'):]
        front, back = self.sides(second)
        self.assertIn('style="font-size:120%;color:var(--ink)">***</div>', front)
        self.assertIn('style="font-size:120%;color:var(--ink)">___</div>', back)
        self.assertNotRegex(html, r'<div class="ex-card-(front|back)"( hidden)?></div>')
        body = tex_body(md)
        self.assertIn("\\textbf{Front:}\\par\n{\\sffamily\\bfseries\\large\\color{accent} 1 rule of the club\\par}"
                      "\\smallskip\\par\n---\\par\\medskip\\textbf{Back:}\\par\n{\\sffamily\\bfseries\\large"
                      "\\color{accent} Big word\\par}\\smallskip", body)
        self.assertIn("\\textbf{Front:} ***\\par\\medskip\\textbf{Back:} \\_\\_\\_}\\medskip", body)

    def test_the_preview_shows_both_sides_turned(self):
        html = self.rich(editor_preview=True)["html"]
        self.assertIn('<div class="ex-flashcard flipped" role="button" tabindex="0" '
                      'data-card-type="jolly" aria-label="Flip flashcard" aria-pressed="true">', html)
        self.assertIn('<div class="ex-card-back">', html)
        self.assertIn('<small class="ex-card-hint">front and back shown in preview</small></div>', html)
        html = self.rich()["html"]
        self.assertIn('aria-pressed="false"><div class="ex-card-front">', html)
        self.assertIn('<div class="ex-card-back" hidden>', html)
        self.assertIn('<small class="ex-card-hint">tap to reveal</small></div>', html)
        self.assertNotIn("<button type=\"button\" class=\"ex-flashcard", html)

    VOCAB = (":::exercise flashcard\ncard-type: %s\ntarget: [کتاب]{tl}\nopposite: دفتر\nmeaning: book\n"
             "front-image: images/cat.png\nfront-audio: audio/ketab.mp3\nback-audio: audio/book.m4a\n%s:::")
    PLAY = ('<span class="ex-card-audio" data-side="%s"><audio preload="metadata" src="/m/audio/%s">'
            '</audio><button type="button" class="ex-card-play" aria-label="Play the recording" '
            'title="Play">🔊</button></span>')

    def sides(self, html):
        front = html[html.index('<div class="ex-card-front">'):html.index('<div class="ex-card-back"')]
        back = html[html.index('<div class="ex-card-back"'):html.index('<small class="ex-card-hint">')]
        return front, back

    def test_vocabulary_and_opposites_play_a_recording(self):
        for kind, text in (("vocab", "book"), ("opposites", "دفتر")):
            html = htmlgen.render_document(doc(self.VOCAB % (kind, "")), asset_base="/m/")["html"]
            front, back = self.sides(html)
            picture = front.index('<img class="ex-card-image" src="/m/images/cat.png" alt="">')
            play = front.index(self.PLAY % ("front", "ketab.mp3"))
            words = front.index('<div class="ex-card-field primary"')
            self.assertLess(picture, play, kind)
            self.assertLess(play, words, kind)
            self.assertTrue(back.startswith('<div class="ex-card-back" hidden>' + self.PLAY % ("back", "book.m4a")), kind)
            self.assertIn(text, back)
            # turned round, each recording stays with its words
            front, back = self.sides(htmlgen.render_document(
                doc(self.VOCAB % (kind, "direction: reverse\n")), asset_base="/m/")["html"])
            self.assertIn(self.PLAY % ("back", "book.m4a"), front)
            self.assertIn(self.PLAY % ("front", "ketab.mp3"), back)
            # no file store yet
            front, back = self.sides(htmlgen.render_document(doc(self.VOCAB % (kind, "")))["html"])
            self.assertIn('<span class="ex-card-audio-placeholder">🔊 <code>audio/ketab.mp3</code></span>', front)
            self.assertIn('<span class="ex-card-audio-placeholder">🔊 <code>audio/book.m4a</code></span>', back)

    def test_a_single_field_can_be_just_a_recording(self):
        html = htmlgen.render_document(doc(
            ":::exercise flashcard\ncard-type: jolly\nfront-primary: ![](audio/a.mp3)\n"
            "back-primary: plain\n:::"), asset_base="/m/")["html"]
        front, back = self.sides(html)
        self.assertIn('<div class="ex-card-field ex-card-blocks primary" style="font-size:120%;color:var(--ink)">'
                      '<figure class="img audio align-left" data-width="60" data-align="left" data-offset="0" '
                      'style="width:60%;margin-left:0.00%"><audio controls preload="metadata" src="/m/audio/a.mp3">'
                      '</audio></figure></div>', front)
        self.assertIn('<div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">plain</div>', back)


class PageEditorsTests(unittest.TestCase):
    """The page's hover editors address what they edit by position: a word
    by (text, occurrence) (colour, reading), a target-text block and a Latin
    block by (content, occurrence).  store finds the n-th one in the source,
    so both must count the same things.  A field a card draws as blocks is
    part of the card, like the pictures on it: it offers none of them, and
    the store's searches do not see its text.  A card of plain fields is
    offered and counted as it always was (FlashcardHtmlTests pins its bytes)."""

    CARD = (":::exercise flashcard\ncard-type: jolly\nfront-primary: سلام\n"
            "front-secondary: > سلام 2 بار\nback-primary: |\n  سلام 2 بار\n\n"
            "  **a greeting**[^c], سلام\n\n  ## سلام | salâm\n\n  [سلام ۲ بار]{tl}\n\n"
            "  [A Latin block]{la}\n\n  [^c]: the word سلام is said on arriving\n"
            "back-secondary: word\n:::")
    AFTER = ("After the card: سلام is said on arriving.\n\nسلام 2 بار\n\n[سلام ۲ بار]{tl}\n\n"
             "[A Latin block]{la}")

    def runs(self, html):
        return [(t, int(n)) for t, n in re.findall(r'data-fa="([^"]*)" data-occ="(\d+)"', html)]

    def drift(self, md, html):
        # tests/smoke.py occurrence_drift, the check every example document gets
        store._target_of(md)
        page = {}
        for text, occ in self.runs(html):
            page.setdefault(text, []).append(occ)
        return ["%s: page %s, source %d" % (t, occs, len(store._run_matches(md, t)))
                for t, occs in page.items()
                if sorted(occs) != list(range(len(store._run_matches(md, t))))]

    def changed(self, before, after):
        return [b for a, b in zip(before.split("\n"), after.split("\n")) if a != b]

    def test_a_card_of_blocks_offers_no_editor(self):
        html = htmlgen.render_document(doc(self.CARD))["html"]
        front = html[html.index('<div class="ex-card-front">'):html.index('<div class="ex-card-back"')]
        back = html[html.index('<div class="ex-card-back"'):html.index('<small class="ex-card-hint">')]
        # a field of one target-language line is the display line the page
        # draws, and offers no word to colour, as no target block does
        self.assertIn('<div class="ex-card-field primary" style="font-size:120%;color:var(--ink)">'
                      '<p class="fa-display"><span class="fa fa-l" dir="rtl" lang="fa">سلام</span></p></div>', front)
        blocks = front + back
        for attr in ("data-fa=", "data-occ=", "data-tl-src=", "data-tl-kind=", "data-la-src="):
            self.assertNotIn(attr, blocks)
        # and what it draws is all there
        for piece in ('<p class="fa-par"', '<section class="voce">', '<div class="la-par align-left"',
                      "<strong>a greeting</strong>", 'id="fn-1">the word <span class="fa'):
            self.assertIn(piece, back)

    def test_a_word_after_the_card_is_the_word_coloured(self):
        for target, card, after, word in (
                ("fa", self.CARD, self.AFTER, "سلام"),
                ("it", ":::exercise flashcard\ncard-type: jolly\nfront-primary: [casa]{tl}\n"
                       "back-primary: |\n  [casa bella]{tl}\n\n  **a house**\n:::",
                 "After the card: [casa]{tl} and [casa bella]{tl} again.", "casa bella")):
            md = doc(card + "\n\n" + after, target=target)
            html = htmlgen.render_document(md)["html"]
            self.assertEqual([], self.drift(md, html), target)
            last = [occ for text, occ in self.runs(html) if text == word][-1]
            new = store.recolor_markdown(md, word, last, "teal")
            self.assertEqual(1, len(self.changed(md, new)), target)
            self.assertTrue(self.changed(md, new)[0].startswith("After the card: "), target)
            self.assertIn("[%s]{teal}" % word, self.changed(md, new)[0], target)

    def test_a_block_after_the_card_is_the_block_edited(self):
        md = doc(self.CARD + "\n\n" + self.AFTER)
        html = htmlgen.render_document(md)["html"]

        def occurrence(kind, content):
            same = [src for k, src in re.findall(r'data-tl-kind="([a-z]+)" data-tl-src="([^"]*)"', html)
                    if k == kind and src == content]
            return len(same) - 1
        for kind, content, want in (("auto", "سلام 2 بار", "سلام 3 بار"),
                                    ("mark", "سلام ۲ بار", "[سلام ۳ بار]{tl}")):
            new = store.tl_edit_markdown(md, kind, content, occurrence(kind, content),
                                         [want.strip("[]{tl}")])
            self.assertEqual([want], self.changed(md, new), kind)
        las = [src for src in re.findall(r'<div class="la-par[^"]*"(?: data-la-src="([^"]*)")?', html)]
        self.assertEqual(["", "A Latin block"], las)
        new = store.la_layout_markdown(md, "A Latin block", las.count("A Latin block") - 1,
                                       50, 0, "center", None)
        self.assertEqual(["[A Latin block]{la align=center width=50}"], self.changed(md, new))

    def test_the_fixture_holds_together(self):
        md = FIXTURE.read_text(encoding="utf-8")
        self.assertEqual([], self.drift(md, htmlgen.render_document(md, asset_base="/m/")["html"]))


class LayoutIndexTests(unittest.TestCase):
    """data-idx n is what store.image_layout_markdown rewrites as index n:
    both count every picture, video and recording line in document order,
    boxes included, and neither counts one written on a flashcard."""

    MD = doc("![fig-a](audio/a.mp3)\n\n![fig-b](images/b.png)\n\n"
             "@[fig-c](https://youtu.be/nFoM8JraEek)\n\n"
             "> A box:\n>\n> ![fig-d](audio/d.ogg){start=1.5}\n\n"
             ":::exercise flashcard\ncard-type: jolly\nfront-primary: |\n"
             "  ![card-1](audio/card.mp3)\n  ![card-2](images/card.png)\n"
             "back-primary: ![card-3](audio/card3.mp3)\n:::\n\n"
             "![fig-e](audio/e.mp3)\n\n"
             "> :::exercise flashcard\n> card-type: jolly\n> front-primary: |\n"
             ">   ![card-4](audio/card4.mp3)\n> back-primary: x\n> :::\n>\n"
             "> ![fig-f](audio/f.wav)\n\n"
             "![fig-g](images/g.png)")

    def check(self, md):
        html = htmlgen.render_document(md, asset_base="/m/")["html"]
        figures = [(i, re.sub(r"<[^>]*>", "", cap)) for i, cap in re.findall(
            r'<figure class="img[^"]*"(?: data-idx="(\d+)")?[^>]*>(?:(?!</figure>).)*?'
            r'<figcaption>(.*?)</figcaption></figure>', html)]
        numbered = [(int(i), cap) for i, cap in figures if i]
        self.assertEqual(list(range(len(numbered))), [i for i, _ in numbered])
        lines = md.split("\n")
        for i, cap in numbered:
            out = store.image_layout_markdown(md, i, 33, "right", 4).split("\n")
            changed = [n for n, (a, b) in enumerate(zip(lines, out)) if a != b]
            self.assertEqual(1, len(changed), (i, cap))
            self.assertIn("[%s](" % cap, lines[changed[0]], (i, cap))
            self.assertIn("{width=33 align=right offset=4", out[changed[0]])
        return numbered

    def test_the_renderer_and_the_store_count_alike(self):
        self.assertEqual(["fig-a", "fig-b", "fig-c", "fig-d", "fig-e", "fig-f", "fig-g"],
                         [cap for _, cap in self.check(self.MD)])
        html = htmlgen.render_document(self.MD, asset_base="/m/")["html"]
        self.assertEqual(4, len(re.findall(r'<figure class="img[^"]*" data-width=[^>]*>'
                                           r'(?:(?!</figure>).)*<figcaption>card-', html)))

    def test_the_fixture(self):
        numbered = self.check(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(5, len(numbered))


class TexTests(unittest.TestCase):
    def test_a_recording_on_paper(self):
        body = tex_body(doc("![Lesson سلام](audio/lesson_1.m4a){width=50 align=center offset=0 "
                            "start=1:05.2 end=1:09}\n\n![](audio/a.mp3){start=0.25}\n\n"
                            "![](audio/b.mp3){end=90}\n\n![](audio/bad.txt)"))
        self.assertIn(
            "\\par\\medskip\\noindent\\hspace*{0.250\\linewidth}\\begin{minipage}{0.500\\linewidth}"
            "\\colorbox{boxbg}{\\parbox{\\dimexpr\\linewidth-1.2em\\relax}{\\centering\\vspace{0.7ex}"
            "{\\Large\\color{accent}\\audioX}\\\\[0.4ex]{\\normalsize\\textbf{Lesson \\pe{سلام}}}\\\\[0.3ex]"
            "{\\footnotesize\\color{graytx}audio · lesson\\_1.m4a · 1:05.2–1:09}\\vspace{0.7ex}}}"
            "\\end{minipage}\\par\\medskip", body)
        self.assertIn("{\\footnotesize\\color{graytx}audio · a.mp3 · dal 0:00.25}", body)
        self.assertIn("{\\footnotesize\\color{graytx}audio · b.mp3 · fino a 1:30}", body)
        self.assertNotIn("bad.txt", body)
        for attrs in ("end=0", "end=0.001", "start=0 end=0"):
            one = tex_body(doc("![](audio/c.mp3){%s}" % attrs))
            self.assertNotIn("fino a", one, attrs)
            self.assertNotIn("–0:00", one, attrs)
        self.assertIn("audio · c.mp3}", tex_body(doc("![](audio/c.mp3){end=0}")))
        # the file is never staged or referenced
        self.assertNotIn("audio/", body)
        self.assertNotIn("\\href", body)
        self.assertEqual(3, body.count("\\audioX"))

    def test_the_template_draws_the_note_with_or_without_dejavu(self):
        tex = texgen.generate(*mdparser.parse(doc("x")))
        self.assertIn("\\newcommand{\\audioX}{{\\symfont ♪}}%", tex)
        self.assertIn("\\newcommand{\\audioX}{\\ensuremath{\\sharp}}%", tex)

    def test_a_jolly_card_made_of_blocks(self):
        body = tex_body(doc("Before[^a].\n\n[^a]: Note A.\n\n" + FlashcardHtmlTests.RICH +
                            "\n\n[^doc]: The document's note."))
        # the exercise's box (\expaperexercise) closes on its \medskip
        end = body.index("}\\medskip\n", body.index("Flashcard}"))
        card, after = body[body.index("Flashcard}"):end], body[end:]
        self.assertIn("\\textbf{Front:}\\par\n{\\sffamily\\bfseries\\large\\color{accent} A heading on the card\\par}\\smallskip", card)
        self.assertIn("{\\sffamily\\bfseries\\normalsize\\color{accentlt} {\\tlfont\\beginR سلام\\endR}\\par}\\smallskip", card)
        self.assertIn("\\voce{کتاب}{}{ketâb}{}", card)
        self.assertNotIn("\\section", card)
        self.assertNotIn("\\subsection", card)
        for piece in ("{\\Large\\color{accent}\\audioX}", "\\begin{tabular}", "\\begin{itemize}",
                      "\\includegraphics[width=\\linewidth]{images/p.png}", "\\href{https://youtu.be/nFoM8JraEek?t=3}",
                      "\\colorbox{boxbg}{\\begin{minipage}{0.93\\linewidth}", "\\par\nsalâm\\par\\medskip\\textbf{Back:}\\par\n"):
            self.assertIn(piece, card)
        # every note is set after the exercise's box, never inside it
        self.assertIn("\\textbf{hello}, a note\\protect\\footnotemark[2]", card)
        self.assertIn("see\\protect\\footnotemark[3]", card)
        self.assertNotIn("\\footnotetext", card)
        self.assertNotIn("\\footnote{", card)
        self.assertIn("\\footnotetext[2]{Written inside the card.}\\stepcounter{footnote}\n"
                      "\\footnotetext[3]{The document's note.}\\stepcounter{footnote}", after)

    def test_a_jolly_card_prints_its_fields_as_the_page_draws_them(self):
        body = tex_body(COMPAT_MD)
        # a field of one target-language line is the display line and the
        # target block the page draws, on paper as on the screen; the prose
        # fields are the inline text they always were
        self.assertIn("\\textbf{Front:}\\par\n\\par\\medskip\\noindent\\hspace*{1.5em}"
                      "{\\large\\pel{سؤال}}\\par\\medskip\\par\nfirst line\\newline second line"
                      "\\par\\medskip\\textbf{Back:} question / a \\textbf{request} for information"
                      "}\\medskip", body)
        self.assertIn("\\textbf{Front:}\\par\n\\begin{fapar}سلام\\end{fapar}\\par\nsalâm"
                      "\\par\\medskip\\textbf{Back:} hello / greeting, see"
                      "\\protect\\footnotemark[2]}"
                      "\\medskip\n\\footnotetext[2]{A document note that a card cites too.}", body)

    def test_vocabulary_names_its_recordings(self):
        body = tex_body(doc(FlashcardHtmlTests.VOCAB % ("vocab", "")))
        self.assertIn("\\textbf{Front:} {\\color{accent}\\audioX}~{\\footnotesize\\color{graytx}ketab.mp3}\\quad "
                      "{\\tlfont\\beginR کتاب\\endR}\\par\\medskip\\textbf{Back:} {\\color{accent}\\audioX}~"
                      "{\\footnotesize\\color{graytx}book.m4a}\\quad book", body)
        body = tex_body(doc((FlashcardHtmlTests.VOCAB % ("opposites", "")).replace("front-audio: audio/ketab.mp3\n", "")))
        self.assertIn("\\textbf{Front:} {\\tlfont\\beginR کتاب\\endR}\\par\\medskip\\textbf{Back:} "
                      "{\\color{accent}\\audioX}~{\\footnotesize\\color{graytx}book.m4a}\\quad \\pe{دفتر}", body)

    def test_a_note_in_a_table_in_a_box_reaches_the_page(self):
        body = tex_body(doc("> A box:\n>\n> | a | b |\n> |---|---|\n> | x | cell[^t] |\n>\n> after[^b]\n\n"
                            "[^t]: In the table.\n[^b]: In the box."))
        box = body[body.index("\\begin{center}\n\\colorbox{boxbg}"):body.index("\\vspace{0.8ex}\\end{minipage}}")]
        self.assertNotIn("\\footnotetext", box)
        self.assertIn("\\end{center}\n\\footnotetext[1]{In the table.}\\stepcounter{footnote}\n"
                      "\\footnotetext[2]{In the box.}\\stepcounter{footnote}", body)


class FixtureTests(unittest.TestCase):
    def test_the_fixture_renders_every_kind(self):
        md = FIXTURE.read_text(encoding="utf-8")
        blocks = blocks_of(md)
        self.assertEqual([], [b["errors"] for b in blocks if b["type"] == "exercise" and b["errors"]])
        out = htmlgen.render_document(md, asset_base="/m/")
        self.assertEqual({"images": 1, "audio": 4},
                         {k: out["stats"][k] for k in ("images", "audio")})
        self.assertIn("#t=0.5,1.25", out["html"])
        self.assertIn("ex-card-blocks", out["html"])
        self.assertIn('class="ex-card-audio" data-side="back"', out["html"])
        for asset in ("audio/greeting.mp3", "images/swatch.png"):
            self.assertTrue((FIXTURE.parent / asset).is_file(), asset)
        self.assertTrue(audiofile.kind((FIXTURE.parent / "audio/greeting.mp3").read_bytes()))


if __name__ == "__main__":
    unittest.main()
