"""The mobile interface's books and exercises (docs/mobile.md), as the server
and the shared files write them: the mobile book shelf (lib/mobile.py,
/m/books/); the registry and the loader in lib/parseh.js that give every
book's reader its mobile layer (lib/mobilereader.js, lib/mobile.css); the
exercise decks' pages, each carrying both layouts (markdown/app/templates,
deckroutes.MODE_SCRIPT, static/mobile.css); and the mobile interface as an
app -- its manifest, icons, worker, pages, and the certificate a phone is
told to trust (serve.py's authority, over a real TLS connection).

    python3 -m unittest discover -s tests -p test_mobile_pages.py

Reads the shelf with the fixture editions of tests/fixtures/books standing on
it, and whether each reader is built stood in for, so nothing on the machine's
own shelf can move it.  What the pages DO -- on a phone, in either mode, in
the reader of each language -- is driven in a browser by
tests/mobile_pages.mjs.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "lib", "tests", "."):
    sys.path.insert(0, str(ROOT / p))
FIXTURES = ROOT / "tests" / "fixtures" / "books"

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
        'source', 'track', 'wbr'}


class Page(HTMLParser):
    """Every element of a page with the layout it sits in ('browser' or
    'mobile' under an element marked data-layout, None outside both), and
    its text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.els, self.body, self.text = [], [], {}, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'body':
            self.body = a
        where = a.get('data-layout') or next((w for w in reversed(self.stack) if w), None)
        self.els.append((where, tag, a))
        if tag not in VOID:
            self.stack.append(a.get('data-layout') or where)

    def handle_endtag(self, tag):
        if tag not in VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        self.text.append(data)

    def of(self, where):
        return [(t, a) for w, t, a in self.els if w == where]


def parse(html):
    p = Page()
    p.feed(html)
    return p


def top_level(css):
    """Every selector of a sheet, one to an item, split at top-level commas."""
    out = []
    for sel in re.findall(r'([^{}]+)\{', re.sub(r'/\*.*?\*/', '', css, flags=re.S)):
        if sel.strip().startswith('@'):           # a media query, with commas of its own
            continue
        depth, part = 0, ''
        for ch in sel:
            depth += ch == '('
            depth -= ch == ')'
            if ch == ',' and depth == 0:
                out.append(part.strip())
                part = ''
            else:
                part += ch
        out.append(part.strip())
    return [p for p in out if p and not p.startswith('@')]


# ------------------------------------------------------------ the shelf
def shelf(unbuilt=("mini-it",), found=None):
    """/m/books/ over the fixture editions, every one built but `unbuilt`."""
    import books
    import mobile
    stats = lambda b: ({"built": False} if b.slug in unbuilt  # noqa: E731
                       else {"built": True, "chapters": ["1", "2"], "subs": 12, "timed": 4})
    whole = books.all_books
    with patch.object(books, 'BOOKS_DIR', str(FIXTURES)), \
            patch.object(mobile.booklib, 'all_books',
                         found if found is not None else (lambda: whole(str(FIXTURES)))), \
            patch.object(mobile.make_index, 'stats', stats):
        return mobile.books_page()


class ShelfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import books
        cls.books = books.all_books(str(FIXTURES))
        cls.html = shelf()
        cls.page = parse(cls.html)

    def cards(self):
        return [(t, a) for w, t, a in self.page.els if 'm-book' in (a.get('class') or '').split()]

    def test_a_mobile_page_that_names_its_browser_page(self):
        self.assertIn('data-mobile-page', self.page.body)
        self.assertEqual(self.page.body.get('data-browser-page'), '/books/')
        order = [self.html.index(f) for f in ('/lib/parseh.css', '/lib/langs.css', '/lib/mobile.css',
                                               '/lib/parseh.js')]
        self.assertEqual(order, sorted(order), 'the palette, the tokens, the mobile sheet, then the script')

    def test_the_bar_is_the_hubs_mobile_bar(self):
        import mobile
        import serve
        self.assertIn('<div class="parseh-bar m-bar">', self.html)
        self.assertIn('<a class="home" href="/">', self.html)
        self.assertIn(mobile.mode_switch(), self.html)
        # one switch, written in one place for every page that carries it
        self.assertEqual(serve.mode_switch(), mobile.mode_switch())
        self.assertIn('data-parseh-theme', self.html)

    def test_a_built_book_opens_its_reader(self):
        cards = {a['data-lang']: (t, a) for t, a in self.cards()}
        self.assertEqual(sorted(cards), sorted(b.language for b in self.books))
        for b in self.books:
            t, a = cards[b.language]
            if b.slug == 'mini-it':
                continue
            self.assertEqual(t, 'a', b.slug)
            self.assertEqual(a['href'], '/books/%s/%s/reader/' % (Path(b.dir).parent.name, b.slug), b.slug)
            self.assertEqual(a['data-subs'], '12')
        # the title and the author in the book's own language and direction
        m = re.search(r'<a class="m-book" href="/books/persian/mini-fa/reader/"[^>]*>\s*'
                      r'<div class="m-btitle" lang="fa" dir="rtl">', self.html)
        self.assertIsNotNone(m)

    def test_a_book_never_built_is_no_link(self):
        cards = {a['data-lang']: (t, a) for t, a in self.cards()}
        t, a = cards['it']
        self.assertEqual((t, a['class']), ('div', 'm-book m-off'))
        self.assertNotIn('href', a)
        card = self.html[self.html.index('<div class="m-book m-off"'):]
        card = card[:card.index('</div>\n</div>') if '</div>\n</div>' in card else 800]
        self.assertIn('not built yet', card)
        self.assertIn('browser interface', card)

    def test_nothing_that_edits_or_manages_the_shelf(self):
        for t, a in [(t, a) for w, t, a in self.page.els]:
            for attr in ('data-del', 'data-build', 'data-parseh-stop'):
                self.assertNotIn(attr, a)
            self.assertNotIn(t, ('input', 'textarea', 'select', 'form'))
        for word in ('__upload', '__backup', '__restore', '__delete', '__build', '__download',
                     '/books/add', 'serve.sh', 'build.sh'):
            self.assertNotIn(word, self.html)
        hrefs = [a['href'] for w, t, a in self.page.els if t == 'a' and 'href' in a]
        self.assertEqual([h for h in hrefs if not h.endswith('/reader/')], ['/', '/books/'],
                         'besides the readers: home, and the library for the browser mode')

    def test_the_chips_filter_the_cards_by_language(self):
        import languages
        m = re.search(r'<div class="parseh-langs m-langs" role="group" aria-label="language" '
                      r'data-lang-filter="([^"]*)">', self.html)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), '.m-book[data-lang], .m-lhead')
        picks = re.findall(r'data-pick="([a-z]+)"', self.html)
        order = [L.code for L in languages.LANGS.values()]
        have = sorted({b.language for b in self.books}, key=order.index)
        self.assertEqual(picks, ['all'] + have)
        heads = re.findall(r'<h2 class="m-lhead" data-lang="([a-z]+)">', self.html)
        self.assertEqual(heads, have, 'a heading a language, in the registry\'s order')

    def test_what_a_book_says_is_escaped(self):
        import languages

        class Stub:
            slug = 'x'
            language = 'en'
            lang = languages.get('en')
            title = '<img src=x onerror=alert(1)>'
            author = 'A & B'
            title_latin = '"quoted"'
            author_latin = ''
            has_audio = False
            meta = {'blurb': '<script>alert(2)</script>'}

            def rel_from_books(self):
                return 'english/x'
        html = shelf(unbuilt=(), found=lambda: [Stub()])
        self.assertNotIn('<img src=x', html)
        self.assertNotIn('<script>alert(2)', html)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)
        self.assertIn('A &amp; B', html)
        self.assertIn('&quot;quoted&quot;', html)

    def test_an_empty_shelf_says_where_books_come_from(self):
        html = shelf(found=lambda: [])
        self.assertIn('class="m-empty"', html)
        self.assertIn('browser interface', html)
        self.assertNotIn('class="m-book', html)

    def test_the_reading_place_is_read_and_never_written(self):
        import mobile
        js = mobile.READ_ON_JS
        self.assertIn("localStorage.getItem('bk_pos:' + p)", js)
        self.assertIn("[base, base + 'index.html']", js)
        self.assertNotIn('setItem', js)
        self.assertNotIn('removeItem', js)
        # the reader keeps it so (lib/tex2html.py, save())
        tex2html = (ROOT / 'lib' / 'tex2html.py').read_text(encoding='utf-8')
        self.assertIn("const MINE = (k) => 'bk_' + k + ':' + location.pathname;", tex2html)
        self.assertIn("localStorage.setItem(MINE('pos'), JSON.stringify({i: cur}))", tex2html)


# ------------------------------------------------------------ the registry, the loader
def mobile_pages():
    """MOBILE_PAGES as parseh.js writes it: (pattern, to) pairs, the pattern
    turned into a Python one (these use nothing the two dialects differ in)."""
    js = (ROOT / 'lib' / 'parseh.js').read_text(encoding='utf-8')
    block = js[js.index('var MOBILE_PAGES = ['):js.index('];', js.index('var MOBILE_PAGES = ['))]
    return [(re.compile(m.group(1)), m.group(2))
            for m in re.finditer(r"\{ match: /(.+?)/, to: '([^']*)' \}", block)]


def route(url):
    """Parseh.mode.route in the mobile mode, for a path on this site."""
    path, _, rest = url.partition('#')
    path, _, q = path.partition('?')
    for pat, to in mobile_pages():
        if pat.search(path):
            return pat.sub(to.replace('$', '\\'), path) + ('?' + q if q else '') + ('#' + rest if rest else '')
    return url


class RegistryTests(unittest.TestCase):
    def test_where_a_link_goes_in_the_mobile_mode(self):
        cases = {
            '/': '/', '/index.html': '/',
            '/books/': '/m/books/', '/books/index.html': '/m/books/', '/books/?x=1#y': '/m/books/?x=1#y',
            # a reader is its own mobile version, by either of its addresses
            '/books/persian/mini-fa/reader/': '/books/persian/mini-fa/reader/',
            '/books/persian/mini-fa/reader/index.html#par-2': '/books/persian/mini-fa/reader/#par-2',
            '/books/old-book/reader/index.html': '/books/old-book/reader/',
            # and so is every page of the decks
            '/exercises/': '/exercises/', '/exercises/deck/persian/words/study': '/exercises/deck/persian/words/study',
            # a page with no mobile version keeps its address
            '/youtube/': '/youtube/', '/studio/': '/studio/', '/books/add/': '/books/add/',
            '/books/persian/mini-fa/': '/books/persian/mini-fa/',
        }
        for url, want in cases.items():
            self.assertEqual(route(url), want, url)

    def test_every_reader_is_given_the_mobile_layer(self):
        js = (ROOT / 'lib' / 'parseh.js').read_text(encoding='utf-8')
        loader = js[js.index("/* ---- a book's reader, in the mobile interface"):]
        m = re.search(r"!/(.+?)/\.test\(location\.pathname\)", loader)
        self.assertIsNotNone(m)
        reader = re.compile(m.group(1))
        for path in ('/books/persian/mini-fa/reader/', '/books/japanese/mini-ja/reader/index.html',
                     '/books/old-book/reader/'):
            self.assertTrue(reader.search(path), path)
        for path in ('/books/', '/books/add/', '/m/books/', '/books/persian/mini-fa/',
                     '/books/persian/mini-fa/reader/ch-2.html', '/youtube/v/abc/'):
            self.assertFalse(reader.search(path), path)
        # loaded from beside parseh.js, as activity.js is: a built reader links
        # lib/ relatively, and needs no rebuild to gain the layer
        self.assertIn("replace(/parseh\\.js(?=[?#]|$).*$/, '')", loader)
        self.assertIn("base + 'mobile.css'", loader)
        self.assertIn("base + 'mobilereader.js'", loader)
        self.assertIn("classList.add('m-reader')", loader)
        self.assertIn("setAttribute('blocking', 'render')", loader)

    def test_the_layer_is_on_the_web(self):
        import serve
        for f in ('/lib/mobile.css', '/lib/mobilereader.js'):
            self.assertIn(f, serve.STATIC_FILES)
            self.assertTrue(serve.static_ok(f))
            self.assertTrue((ROOT / f.lstrip('/')).is_file(), f)

    def test_a_mobile_only_page_goes_back_to_its_browser_page_on_a_switch_only(self):
        js = (ROOT / 'lib' / 'parseh.js').read_text(encoding='utf-8')
        apply = js[js.index('function modeApply()'):js.index('function modeSet(m)')]
        self.assertIn("getAttribute('data-browser-page')", apply)
        # inside the "the mode changed" branch, and only towards the browser
        changed = apply[apply.index('if (was !== null && was !== m) {'):]
        self.assertIn("m === 'browser'", changed)
        self.assertIn('location.replace(back)', changed)

    def test_the_readers_writing_gestures_are_refused_in_the_mobile_mode(self):
        js = (ROOT / 'lib' / 'mobilereader.js').read_text(encoding='utf-8')
        self.assertIn("window.addEventListener('click'", js)
        self.assertIn("window.addEventListener('keydown'", js)
        self.assertIn("e.key === 'e' || e.key === 'E'", js)
        self.assertEqual(js.count('if (!mobile()'), 2, 'each refusal asks the mode first')
        # nothing of the reader's own is moved or rewritten: the layer only
        # adds, into the header's first row, elements it made itself (the
        # switch, and the field that says how far ↺ and ↻ move)
        receivers = re.findall(r'(\w+)\.(?:appendChild|insertBefore|replaceWith|replaceChildren|remove)\(', js)
        self.assertEqual(set(receivers), {'row', 'sw', 'set'})
        self.assertIn("var sw = el('span', 'parseh-mode');", js)
        self.assertIn("var set = el('label', 'm-rskip');", js)
        self.assertNotIn('innerHTML', js)

    def test_the_recording_moves_by_the_seconds_asked_and_takes_the_reading_place_along(self):
        js = (ROOT / 'lib' / 'mobilereader.js').read_text(encoding='utf-8')
        # one number for every book, kept beside the reader's own habits
        self.assertIn("var SKIP_KEY = 'bk_skip', SKIP_DEF = 10, SKIP_MAX = 600;", js)
        self.assertIn("if (!(v >= 1)) v = skipSecs();", js)
        self.assertIn("v = Math.min(SKIP_MAX, v);", js)
        skip = js[js.index('function skipBy(secs)'):]
        skip = skip[:skip.index('\n  }\n') + 4]
        # listening has no reading place: only the fold ahead is worked out again
        self.assertIn('if (listening) {', skip)
        self.assertIn('if (!a.paused) armListen();', skip)
        # reading: the subparagraph the recording lands in is the place, and
        # where the playing stops
        self.assertIn('var i = subAtTime(to);', skip)
        self.assertIn('cur = i; hl(i, true); save();', skip)
        self.assertIn('stopAt = SUBS[i][1];', skip)
        # every binding of the reader's read before any is written
        self.assertLess(skip.index('void [waiting, atBound, previewing, cur, stopAt, hl, save, SUBS, seekTo];'),
                        skip.index('waiting = null;'))
        # the reader has each of them, at the top level of its script
        tex2html = (ROOT / 'lib' / 'tex2html.py').read_text(encoding='utf-8')
        for decl in ('let cur = -1, loop = false, cont = true, stopAt = null, gap = 0, waiting = null;',
                     'let listening = false, afterFold = null, seeking = false;', 'let previewing = false;',
                     'function subAtTime(t) {', 'function seekTo(t, done) {', 'function armListen() {',
                     'function hl(i, mayScroll) {', 'function save() {'):
            self.assertIn('\n' + decl, tex2html)
        # a book with no narration has no ↺ and ↻, nor the field
        css = (ROOT / 'lib' / 'mobile.css').read_text(encoding='utf-8')
        self.assertIn('html.m-reader[data-mode=mobile] body.noaudio :is(.m-skip,.m-rskip,.m-rbreak)'
                      '{display:none!important}', css)

    def test_the_header_stays_while_it_is_being_used(self):
        # the bars follow the scroll at every width in the mobile mode, and
        # stand down while a page holds them (⋯ open, a skip's own scroll)
        js = (ROOT / 'lib' / 'parseh.js').read_text(encoding='utf-8')
        bars = js[js.index('  function bars() {'):js.index('  function wire() {')]
        self.assertIn('var want = mq.matches || isMobile();', bars)
        self.assertIn('modeOnChange(follow);', bars)
        self.assertIn("document.body.hasAttribute('data-bars-held')", bars)
        # where the page is, kept even while held, before the hold is asked
        self.assertLess(bars.index('lastY = y;'), bars.index("hasAttribute('data-bars-held')"))
        layer = (ROOT / 'lib' / 'mobilereader.js').read_text(encoding='utf-8')
        self.assertIn("hold('more', on);", layer)
        self.assertIn("holdForSkip(); skipBy(", layer)

    def test_the_reader_sheet_hides_every_writing_door(self):
        css = (ROOT / 'lib' / 'mobile.css').read_text(encoding='utf-8')
        m = re.search(r"html\.m-reader\[data-mode=mobile\] :is\(([^)]*)\)\{display:none!important\}", css)
        self.assertIsNotNone(m)
        shut = {s.strip() for s in m.group(1).split(',')}
        for door in ('#chpen', '#anki', '#bmbox', '#chbox', '#dvbox', '#fdbox', '#narrbox', '#naskbox',
                     '#secbox', '.dlsheet', '#ntedit', '.gap .plus', '.tocedit', '#tocsecs',
                     '#cloud .mkcard', '#cloud .mkedit'):
            self.assertIn(door, shut)
        # the header keeps what it names and nothing else
        keep = re.search(r"html\.m-reader\[data-mode=mobile\] header > \.hrow > :not\(([^)]*)\)", css)
        self.assertIsNotNone(keep)
        kept = {s.strip() for s in keep.group(1).split(',')}
        for gone in ('#bookinfo', '#buildbook', '#buildhtml', '#narr', '#fold', '#editmode', '#stopsrv',
                     '.dl', '#lookupset', '#build'):
            self.assertNotIn(gone, kept)
        for there in ('#play', '#toc', '#typo', '#theme', '.pgrp', '[data-toggle=nogloss]'):
            self.assertIn(there, kept)


# ------------------------------------------------------------ the decks
TEMPLATES = ('decks.html', 'deck.html', 'study.html', 'cram.html')


def rendered(name):
    import deckroutes
    import languages
    deck = {'folder': 'persian', 'slug': 'words', 'name': 'Words', 'lang': 'fa', 'path': 'persian/words',
            'counts': {'total': 0}, 'study': {}, 'settings': {}}
    mapping = deckroutes._deck_mapping('Words', deck)
    mapping['LANG_CHIPS'] = languages.chips_html({})
    return deckroutes.render_template(name, mapping)


class DeckTests(unittest.TestCase):
    def test_the_switch_is_the_hubs(self):
        import deckroutes
        import mobile
        self.assertEqual(deckroutes.MODE_SWITCH, mobile.mode_switch())

    def test_the_mode_is_read_as_parseh_js_reads_it(self):
        import deckroutes
        js = (ROOT / 'lib' / 'parseh.js').read_text(encoding='utf-8')
        s = deckroutes.MODE_SCRIPT
        self.assertIn("localStorage.getItem('parseh_mode')", s)
        # the same cookie pattern, character for character
        cookie = re.search(r"m = /(.+?)/\.exec\(document\.cookie", js).group(1)
        self.assertIn('/' + cookie.replace('\\s', '\\s') + '/.exec(document.cookie', s)
        self.assertIn("m=c?c[1]:'browser'", s)
        self.assertIn("setAttribute('data-mode',m)", s)

    def test_every_page_carries_both_layouts(self):
        import deckroutes
        for name in TEMPLATES:
            html = rendered(name)
            self.assertNotIn('{{', html, name)
            head = html[:html.index('</head>')]
            # the mode is on <html> before the first sheet is asked for
            self.assertLess(head.index(deckroutes.MODE_SCRIPT), head.index('<link rel="stylesheet"'), name)
            self.assertLess(head.index('/static/app.css'), head.index('/static/mobile.css'), name)
            p = parse(html)
            bars = [(w, a.get('class')) for w, t, a in p.els if t == 'header']
            self.assertEqual(bars, [('browser', 'topbar'), ('mobile', 'm-topbar')], name)
            modes = [a['data-parseh-mode'] for t, a in p.of('mobile') if 'data-parseh-mode' in a]
            self.assertEqual(modes, ['browser', 'mobile'], name)
            self.assertTrue(any('data-parseh-theme' in a for t, a in p.of('mobile')), name)
            self.assertTrue(any(t == 'a' and a.get('href') == '/' for t, a in p.of('mobile')), name)

    def test_the_mobile_layouts_have_nothing_that_edits(self):
        for name in TEMPLATES:
            p = parse(rendered(name))
            for t, a in p.of('mobile'):
                self.assertNotIn(a.get('id'), ('btn-stop', 'btn-import', 'btn-restore', 'btn-new-deck',
                                               'btn-rename', 'btn-add-exercise', 'btn-options',
                                               'btn-delete-deck', 'btn-edit-card'), name)
                self.assertNotIn(t, ('input', 'textarea', 'select', 'form'), name)
        # and the sheet takes the browser layout's editing controls away:
        # the deck's own, and the list's -- which the mobile layout shows,
        # to pick exercises to cram, with nothing in it that changes one
        css = (ROOT / 'markdown' / 'app' / 'static' / 'mobile.css').read_text(encoding='utf-8')
        hidden = set()
        for m in re.finditer(r'html\[data-mode=mobile\] body\[data-page=(?:deck|study)\] :is\(([^{]*)\)'
                             r'\{display:none!important\}', css):
            hidden |= {s.strip() for s in m.group(1).split(',')}
        for sel in ('#btn-rename', '#btn-add-exercise', '#btn-options', '#btn-delete-deck', '#btn-edit-card',
                    '#btn-bulk-copy', '#btn-bulk-move', '#btn-bulk-add-tag', '#btn-bulk-remove-tag',
                    '#btn-bulk-new', '#btn-bulk-delete', '.dk-row-actions', '.dk-selection-hint'):
            self.assertIn(sel, hidden)
        for kept in ('.dk-browse', '#btn-select-all', '#btn-select-shown', '#btn-select-tag',
                     '#btn-deselect-all', '#browse-list'):
            self.assertNotIn(kept, hidden)
        self.assertIn('html[data-mode=mobile] .card.dk-card .dropdown{display:none!important}', css)

    def test_studying_answers_in_one_place(self):
        p = parse(rendered('study.html'))
        ids = [a.get('id') for w, t, a in p.els if a.get('id')]
        box = rendered('study.html')
        box = box[box.index('<div class="dk-answerbar">'):box.index('<div id="study-done"')]
        for inside in ('id="study-actions"', 'id="rating-bar"', 'id="btn-next"'):
            self.assertIn(inside, box)
        self.assertIn('btn-next', ids)
        nxt = [a for w, t, a in p.els if a.get('id') == 'btn-next'][0]
        self.assertEqual(nxt.get('data-layout'), 'mobile')
        # no bar over the exercise in the mobile layout: the way back is by the
        # deck's name, on both pages
        for name in ('study.html', 'cram.html'):
            back = [a for w, t, a in parse(rendered(name)).els if 'm-back' in (a.get('class') or '').split()]
            self.assertEqual(len(back), 1, name)
            self.assertEqual(back[0].get('data-layout'), 'mobile', name)
            self.assertIn('dk-back', back[0]['class'].split(), name)
        css = (ROOT / 'markdown' / 'app' / 'static' / 'mobile.css').read_text(encoding='utf-8')
        self.assertIn('html[data-mode=mobile] body:is([data-page=study],[data-page=cram]) .m-topbar{display:none}', css)
        # Next rates as the answer says: the rating the bar was shown for
        js = (ROOT / 'markdown' / 'app' / 'static' / 'decks.js').read_text(encoding='utf-8')
        self.assertIn('btnNext.dataset.rating = focus;', js)
        self.assertIn('if (btnNext.dataset.rating) rate(btnNext.dataset.rating);', js)
        self.assertIn('showBar(good ? "good" : "again");', js)
        self.assertIn('showBar("good");', js)

    def test_a_deck_crams_what_is_picked(self):
        p = parse(rendered('deck.html'))
        go = [a for w, t, a in p.els if a.get('id') == 'm-cram'][0]
        self.assertEqual(go.get('data-layout'), 'mobile')
        js = (ROOT / 'markdown' / 'app' / 'static' / 'decks.js').read_text(encoding='utf-8')
        self.assertIn('$("#btn-cram").addEventListener("click", cramSelected);', js)
        self.assertIn('$("#m-cram").addEventListener("click", cramSelected);', js)
        self.assertIn('go.hidden = n === 0;', js)

    def test_the_sheet_reaches_nothing_of_the_browser_layout(self):
        css = (ROOT / 'markdown' / 'app' / 'static' / 'mobile.css').read_text(encoding='utf-8')
        self.assertIn('html[data-mode=mobile] [data-layout=browser],\n'
                      'html:not([data-mode=mobile]) [data-layout=mobile]{display:none!important}', css)
        for part in top_level(css):
            self.assertTrue(re.search(r'html\[data-mode=mobile\]|\.m-|\[data-layout=', part), part)

    def test_the_pages_are_wired(self):
        js = (ROOT / 'markdown' / 'app' / 'static' / 'decks.js').read_text(encoding='utf-8')
        boot = js[js.index('/* ---------------- boot ---------------- */'):]
        self.assertIn('bindMode();', boot)
        self.assertIn('$("#btn-practise").addEventListener("click"', js)
        self.assertIn('sessionStorage.setItem(`parseh-cram:${deck.path}`', js)


# ------------------------------------------------------------ the app
def png_size(path):
    data = Path(path).read_bytes()[:24]
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path
    return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')


class AppTests(unittest.TestCase):
    """The mobile interface installed as an app: what the server says about
    it.  That Chromium finds the pages installable, that the worker takes
    them over and answers for a server that has gone, is driven by
    tests/mobile_pages.mjs (its part "app")."""

    def test_the_manifest_describes_the_mobile_interface(self):
        import mobile
        m = mobile.manifest()
        self.assertEqual((m['name'], m['short_name']), ('Parseh', 'Parseh'))
        # it opens on the mobile hub, in the mobile mode, and the whole toolbox is the app
        self.assertEqual((m['start_url'], m['scope'], m['id']), ('/?mode=mobile', '/', '/'))
        self.assertEqual(m['display'], 'fullscreen')
        self.assertIn('standalone', m['display_override'])
        self.assertEqual(m['orientation'], 'any')
        got = {(i['sizes'], i['purpose']) for i in m['icons']}
        self.assertEqual(got, {('192x192', 'any'), ('512x512', 'any'), ('512x512', 'maskable')})

    def test_the_icons_are_there_at_the_sizes_named(self):
        import mobile
        import serve
        for i in mobile.manifest()['icons'] + [{'src': '/lib/icons/apple-touch-icon.png', 'sizes': '180x180'}]:
            self.assertIn(i['src'], serve.STATIC_FILES)
            self.assertTrue(serve.static_ok(i['src']))
            w, h = png_size(ROOT / i['src'].lstrip('/'))
            self.assertEqual('%dx%d' % (w, h), i['sizes'], i['src'])
        # the script that drew them is not on the web
        self.assertFalse(serve.static_ok('/lib/icons/make.mjs'))

    def test_every_page_of_the_mobile_interface_carries_the_app_tags(self):
        import deckroutes
        import mobile
        head = mobile.app_head()
        self.assertIn('<link rel="manifest" href="/manifest.webmanifest">', head)
        self.assertEqual(deckroutes.APP_HEAD, head, 'the same tags, in the one place each side keeps them')
        self.assertIn(head, shelf())
        self.assertIn(head, mobile.install_page('authority'))
        for name in TEMPLATES:
            self.assertIn(head, rendered(name), name)
        import test_mobile_mode
        self.assertIn(head, test_mobile_mode.hub()[0])
        # and a page built without them -- a book's reader -- is given them
        js = (ROOT / 'lib' / 'parseh.js').read_text(encoding='utf-8')
        self.assertIn("if (location.protocol === 'file:' || document.querySelector('link[rel=manifest]')) return;", js)
        self.assertIn("['link', {rel: 'manifest', href: '/manifest.webmanifest'}]", js)

    def test_the_hub_has_the_door_and_the_app_not(self):
        import test_mobile_mode
        html = test_mobile_mode.hub()[0]
        self.assertIn('<a class="m-door m-guide m-appdoor" href="/m/install/">', html)
        css = (ROOT / 'lib' / 'mobile.css').read_text(encoding='utf-8')
        self.assertIn('@media (display-mode:standalone),(display-mode:fullscreen),(display-mode:minimal-ui){\n'
                      '  .m-appdoor{display:none!important}', css)

    def test_the_worker_answers_pages_only_and_only_when_the_server_is_away(self):
        sw = (ROOT / 'lib' / 'sw.js').read_text(encoding='utf-8')
        self.assertIn("if (r.mode !== 'navigate' || r.method !== 'GET') return;", sw)
        self.assertIn('e.respondWith(fetch(r).catch(() =>', sw)
        self.assertIn("const OFFLINE = '/m/offline/';", sw)
        self.assertEqual(sw.count('caches.open('), 1, 'the offline page is the one thing kept')
        # served from the top of the site, so that its scope is all of it
        serve_py = (ROOT / 'serve.py').read_text(encoding='utf-8')
        self.assertIn('if path == "/sw.js":', serve_py)
        self.assertIn('"text/javascript; charset=utf-8"', serve_py)

    def test_the_offline_page_stands_alone(self):
        import mobile
        html = mobile.offline_page()
        self.assertNotIn('<link', html)
        self.assertNotIn('<script', html)
        self.assertIn('prefers-color-scheme:dark', html)
        self.assertIn('location.reload()', html)

    def test_the_install_page_says_what_the_server_speaks(self):
        import mobile
        own = mobile.install_page('authority')
        self.assertIn('href="/m/install/parseh-ca.crt"', own)
        self.assertIn('data-parseh-install hidden', own)
        self.assertIn('data-browser-page="/"', own)
        for other in ('own', 'http'):
            self.assertNotIn('parseh-ca.crt', mobile.install_page(other), other)
        # nothing on it asks for a terminal
        for page in (own, mobile.install_page('own'), mobile.install_page('http')):
            for word in ('serve.sh', 'serve.bat', 'terminal', 'openssl', '--http'):
                self.assertNotIn(word, page)

    def test_the_mode_comes_from_the_apps_address(self):
        js = (ROOT / 'lib' / 'parseh.js').read_text(encoding='utf-8')
        at = js.index('var m = /(?:^\\?|&)mode=(browser|mobile)(?=&|$)/.exec(location.search);')
        # read before the mode is first put on the page
        self.assertLess(at, js.rindex('  apply();\n  modeApply();'))
        self.assertIn('history.replaceState(history.state', js)
        # the worker registered in the mobile mode, on every page and at the switch
        self.assertIn("if (isMobile()) appRegister();", js)
        self.assertIn("modeOnChange(function (m) { if (m === 'mobile') appRegister(); });", js)
        decks = (ROOT / 'markdown' / 'app' / 'static' / 'decks.js').read_text(encoding='utf-8')
        self.assertIn('if (m === "mobile") appRegister();', decks)


@unittest.skipUnless(shutil.which('openssl'), 'openssl makes the certificate')
class CertificateTests(unittest.TestCase):
    """serve.py's certificate: an authority of the machine's own, which a
    phone is told to trust once, and the server's, signed by it."""

    def setUp(self):
        import serve
        self.serve = serve
        self.td = tempfile.TemporaryDirectory()
        self.dir = self.td.name
        self.patch = patch.object(serve, 'TLS_DIR', self.dir)
        self.patch.start()
        self.quiet = patch('builtins.print')
        self.quiet.start()

    def tearDown(self):
        self.quiet.stop()
        self.patch.stop()
        self.td.cleanup()

    def f(self, name):
        return os.path.join(self.dir, name)

    def text(self, name):
        return subprocess.run(['openssl', 'x509', '-in', self.f(name), '-noout', '-text'],
                              capture_output=True, text=True, check=True).stdout

    def test_an_authority_and_a_certificate_it_signed(self):
        cert, key = self.serve.make_cert()
        self.assertEqual((cert, key), (self.f('cert.pem'), self.f('key.pem')))
        for name in ('ca.pem', 'ca-key.pem', 'cert.pem', 'key.pem'):
            self.assertTrue(os.path.isfile(self.f(name)), name)
        for private in ('ca-key.pem', 'key.pem'):
            self.assertEqual(os.stat(self.f(private)).st_mode & 0o777, 0o600, private)
        # nothing of the making is left behind
        self.assertEqual(sorted(os.listdir(self.dir)), ['ca-key.pem', 'ca.pem', 'cert.pem', 'key.pem', 'names.txt'])
        # the chain the server sends: its own, then the authority
        pems = Path(cert).read_text().count('-----BEGIN CERTIFICATE-----')
        self.assertEqual(pems, 2)
        r = subprocess.run(['openssl', 'verify', '-CAfile', self.f('ca.pem'), cert],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        leaf = self.text('cert.pem')
        self.assertIn('CA:FALSE', leaf)
        self.assertIn('TLS Web Server Authentication', leaf)
        self.assertIn('DNS:localhost', leaf)
        self.assertIn('IP Address:127.0.0.1', leaf)
        # no longer than an iPhone accepts
        r = subprocess.run(['openssl', 'x509', '-in', cert, '-noout', '-checkend', str(826 * 86400)],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0, 'it ends within 826 days')

    def test_the_authority_can_vouch_for_this_machine_only(self):
        self.serve.make_cert()
        ca = self.text('ca.pem')
        self.assertIn('CA:TRUE, pathlen:0', ca)
        self.assertIn('X509v3 Name Constraints: critical', ca)
        for permitted in ('DNS:localhost', 'DNS:local', 'DNS:ts.net', 'IP:192.168.0.0/255.255.0.0',
                          'IP:10.0.0.0/255.0.0.0', 'IP:172.16.0.0/255.240.0.0', 'IP:100.64.0.0/255.192.0.0',
                          'IP:127.0.0.0/255.0.0.0'):
            self.assertIn(permitted, ca)
        # and the server's certificate names nothing outside them
        self.assertFalse(self.serve._ip_permitted('8.8.8.8'))
        self.assertTrue(self.serve._ip_permitted('100.86.243.109'))
        self.assertTrue(self.serve._ip_permitted('192.168.1.20'))
        with patch.object(self.serve, 'cert_names', lambda: (['localhost', 'box', 'box.example.com'],
                                                             ['127.0.0.1', '192.168.1.20', '8.8.8.8'])):
            self.serve.make_cert(force=True)
        leaf = self.text('cert.pem')
        self.assertIn('IP Address:192.168.1.20', leaf)
        self.assertNotIn('8.8.8.8', leaf)
        self.assertNotIn('box.example.com', leaf)

    def test_kept_renewed_near_its_end_and_made_again_when_asked(self):
        self.serve.make_cert()
        ca, first = Path(self.f('ca.pem')).read_text(), Path(self.f('cert.pem')).read_text()
        self.serve.make_cert()
        self.assertEqual(Path(self.f('cert.pem')).read_text(), first, 'kept')
        with patch.object(self.serve, 'TLS_RENEW', 900 * 86400):
            self.serve.make_cert()
        second = Path(self.f('cert.pem')).read_text()
        self.assertNotEqual(second, first, 'near its end: made again')
        self.serve.make_cert(force=True)
        self.assertNotEqual(Path(self.f('cert.pem')).read_text(), second, 'asked: made again')
        self.assertEqual(Path(self.f('ca.pem')).read_text(), ca, 'the authority a phone trusts, never')

    def test_an_old_certificate_of_parsehs_own_is_replaced_once(self):
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-days', '3650', '-nodes',
                        '-keyout', self.f('key.pem'), '-out', self.f('cert.pem'),
                        '-subj', '/CN=box/O=Parseh'], capture_output=True, check=True)
        self.assertTrue(self.serve._made_here(self.f('cert.pem')))
        self.serve.make_cert()
        self.assertTrue(os.path.isfile(self.f('ca.pem')))
        r = subprocess.run(['openssl', 'verify', '-CAfile', self.f('ca.pem'), self.f('cert.pem')],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_certificate_put_there_by_hand_is_left_alone(self):
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-days', '90', '-nodes',
                        '-keyout', self.f('key.pem'), '-out', self.f('cert.pem'),
                        '-subj', '/CN=box.tail1234.ts.net'], capture_output=True, check=True)
        own = Path(self.f('cert.pem')).read_bytes()
        self.assertFalse(self.serve._made_here(self.f('cert.pem')))
        self.serve.make_cert()
        self.assertEqual(Path(self.f('cert.pem')).read_bytes(), own)
        self.assertEqual(sorted(os.listdir(self.dir)), ['cert.pem', 'key.pem'])
        self.assertIsNone(self.serve.authority_der())

    def test_the_server_speaks_it_and_hands_over_the_authority_alone(self):
        import http.client
        import ssl
        import threading
        serve = self.serve
        cert, key = serve.make_cert()
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        with patch.object(serve.Handler, 'log_request', lambda *a, **k: None):
            srv = serve.Server(('127.0.0.1', 0), serve.Handler, ctx)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                # a client that trusts the authority and nothing else
                trust = ssl.create_default_context(cafile=self.f('ca.pem'))
                c = http.client.HTTPSConnection('localhost', srv.server_address[1], context=trust, timeout=30)
                c.request('GET', '/m/install/parseh-ca.crt')
                r = c.getresponse()
                body = r.read()
                self.assertEqual(r.status, 200)
                self.assertEqual(r.getheader('Content-Type'), 'application/x-x509-ca-cert')
                self.assertEqual(body, serve.authority_der())
                self.assertEqual(body, ssl.PEM_cert_to_DER_cert(Path(self.f('ca.pem')).read_text()))
                self.assertNotIn(b'PRIVATE KEY', body)
                c.request('GET', '/m/install/')
                r = c.getresponse()
                page = r.read().decode('utf-8')
                self.assertIn('href="/m/install/parseh-ca.crt"', page)
                c.close()
            finally:
                srv.shutdown()
                srv.server_close()


if __name__ == '__main__':
    unittest.main()
