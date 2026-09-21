"""The mobile mode's groundwork (docs/mobile.md): the hub carries both of its
layouts and the switch between them, the browser layout keeps every door it
had, and the mobile one has nothing on it that edits or administers.

    python3 -m unittest discover -s tests -p test_mobile_mode.py

Reads the hub as serve.hub_page() writes it, with every shelf it counts -- the
books, the studio's notes, the videos and the exercise decks -- stood in for,
so the counts are known and nothing in the tree the test runs in (whatever
books, videos or decks it holds) can move them; and the shared script and
sheets as files.  What the page DOES with all this -- the switch, the cookie,
the routing, what is on the screen in each mode -- is driven in a browser by
tests/mobile_mode.mjs.
"""
import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
sys.path.insert(0, str(ROOT))

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
        'source', 'track', 'wbr'}


class Layouts(HTMLParser):
    """Every element of the page with the layout it sits in: 'browser' or
    'mobile' under an element marked data-layout, None outside both."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.els, self.body = [], [], {}

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

    def of(self, where):
        return [(t, a) for w, t, a in self.els if w == where]


def hub():
    import serve
    bks = [{'slug': 'a', 'title': 'a', 'latin': 'a', 'lang': 'ja', 'href': '/books/japanese/a/reader/',
            'built': True, 'subs': 0, 'timed': 0, 'audio': False}]
    docs = [{'target': 'fa'}, {'target': 'ar'}, {'target': 'hi'}]
    yt = {'channels': 1, 'videos': 2, 'decks': 0, 'cards': 0, 'by_lang': {'it': {'videos': 2, 'channels': 1}}}
    dk = {'decks': 1, 'due': 3, 'by_lang': {'tr': {'decks': 1, 'due': 3}}}
    with patch.object(serve, 'book_stats', lambda: bks), \
            patch.object(serve.studio.store, 'list_docs', lambda: docs), \
            patch.object(serve.ytpages, 'stats', lambda: yt), \
            patch.object(serve.studio.decks, 'hub_stats', lambda *a, **k: dk):
        html = serve.hub_page()
    p = Layouts()
    p.feed(html)
    return html, p


class HubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html, cls.page = hub()

    def hrefs(self, where):
        return [a['href'] for t, a in self.page.of(where) if t == 'a' and 'href' in a]

    def test_the_page_carries_both_layouts_and_says_it_is_a_mobile_page(self):
        marked = [(w, t, a.get('class')) for w, t, a in self.page.els if 'data-layout' in a]
        self.assertEqual(marked, [('browser', 'div', 'parseh-bar'), ('mobile', 'div', 'parseh-bar m-bar'),
                                  ('browser', 'div', 'hub-browser'), ('mobile', 'div', 'hub-mobile')])
        self.assertIn('data-mobile-page', self.page.body)
        # the mobile sheet comes after the palette it draws with
        self.assertLess(self.html.index('/lib/parseh.css'), self.html.index('/lib/mobile.css'))
        self.assertLess(self.html.index('/lib/mobile.css'), self.html.index('/lib/parseh.js'))

    def test_the_switch_is_in_both_bars(self):
        for where in ('browser', 'mobile'):
            modes = [(a['data-parseh-mode'], a.get('aria-pressed'), a.get('type'))
                     for t, a in self.page.of(where) if 'data-parseh-mode' in a]
            self.assertEqual(modes, [('browser', 'true', 'button'), ('mobile', 'false', 'button')], where)
            groups = [a for t, a in self.page.of(where) if 'parseh-mode' in (a.get('class') or '').split()]
            self.assertEqual([(g.get('role'), g.get('aria-label')) for g in groups], [('group', 'interface')])
        self.assertIn('>Browser</button>', self.html)
        self.assertIn('>Mobile</button>', self.html)

    def test_the_browser_layout_keeps_every_door(self):
        got = self.hrefs('browser')
        for href in ('/books/', '/youtube/', '/studio/', '/exercises/', '/anki/sync/', '/clips/',
                     '/lookup/', '/guide/', '/'):
            self.assertIn(href, got)
        self.assertTrue(any('data-parseh-stop' in a for t, a in self.page.of('browser')))
        self.assertTrue(any(a.get('class') == 'addr' for t, a in self.page.of('browser')))
        # the doors are still written as the other tests read them, and the
        # first of each is the browser layout's
        for href in ('/books/', '/studio/', '/exercises/', '/lookup/'):
            m = re.search(r'<a class="door(?: wide)?" href="%s">' % re.escape(href), self.html)
            self.assertIsNotNone(m, href)
            self.assertLess(self.html.index('class="hub-browser"'), m.start())
            self.assertLess(m.start(), self.html.index('class="hub-mobile"'))

    def test_the_mobile_layout_has_nothing_that_edits_or_administers(self):
        self.assertEqual(self.hrefs('mobile'), ['/', '/books/', '/youtube/', '/studio/', '/exercises/', '/guide/'])
        els = self.page.of('mobile')
        buttons = [a.get('data-parseh-mode') or ('theme' if 'data-parseh-theme' in a else a.get('data-pick'))
                   for t, a in els if t == 'button']
        self.assertEqual(buttons[:3], ['browser', 'mobile', 'theme'])
        self.assertEqual(buttons[3], 'all')
        self.assertEqual(sorted(buttons[4:]), ['ar', 'fa', 'hi', 'it', 'ja', 'tr'])
        for t, a in els:
            self.assertNotIn('data-parseh-stop', a)
            self.assertNotIn('data-del', a)
            self.assertNotIn('data-build', a)
            self.assertNotIn(t, ('input', 'textarea', 'select', 'form'))
            self.assertNotIn(a.get('class'), ('addr', 'foot'))
        mobile = self.html[self.html.index('class="hub-mobile"'):]
        for word in ('/anki/', '/clips/', '/lookup/', '/add/', 'stop', 'Anki', 'dictionar'):
            self.assertNotIn(word, mobile)

    def test_a_mobile_door_counts_what_the_browser_door_counts(self):
        def counts(cls, href):
            m = re.search(r'<a class="%s" href="%s">(.*?)</a>' % (cls, re.escape(href)), self.html, re.S)
            return [json.loads(c.replace('&quot;', '"')) for c in re.findall(r'data-counts="([^"]*)"', m.group(1))]
        for href in ('/books/', '/youtube/', '/studio/', '/exercises/'):
            got, want = counts('m-door', href), counts('door', href)
            self.assertTrue(want, href)
            self.assertEqual(got, want, href)
        self.assertEqual(counts('m-door', '/books/')[0]['ja'], '1 book')
        self.assertEqual(counts('m-door', '/studio/')[0]['hi'], '1 document')
        self.assertEqual(counts('m-door', '/youtube/')[0]['it'], '2 videos')
        self.assertEqual(counts('m-door', '/exercises/')[1]['tr'], '3 due')
        # the chip row is there twice, the same chips; the mobile one says so
        rows = re.findall(r'<div class="(parseh-langs[^"]*)" role="group" aria-label="language">(.*?)</div>',
                          self.html, re.S)
        self.assertEqual([c for c, _ in rows], ['parseh-langs', 'parseh-langs m-langs'])
        self.assertEqual(rows[0][1], rows[1][1])

    def test_the_guide_is_the_html_one_and_no_terminal_is_asked_for(self):
        import serve
        self.assertNotIn('/guide.pdf', self.html)
        self.assertIn('/guide/', self.hrefs('browser'))
        self.assertIn('/guide/', self.hrefs('mobile'))
        self.assertNotIn('serve.sh', self.html)
        # the clip tray's bar has the same guide button
        with patch.object(serve.clips, 'listing', lambda: []):
            tray = serve.clips_page()
        self.assertIn('href="/guide/"', tray)
        self.assertNotIn('/guide.pdf', tray)
        # ... and says what it opens in the hub's words: the guide, not "the
        # manual", the name of the PDF it used to open
        said = lambda html: re.search(r'<a class="parseh-btn" href="/guide/"[^>]*title="([^"]*)"', html).group(1)  # noqa: E731
        self.assertEqual(said(tray), said(self.html))
        self.assertEqual(said(tray), "the guide: how to use Parseh")

    def test_one_activity_container_shown_in_both_layouts(self):
        found = [(w, t) for w, t, a in self.page.els if a.get('id') == 'hub-activity']
        self.assertEqual(found, [(None, 'div')])
        self.assertLess(self.html.index('<main class="hub">'), self.html.index('id="hub-activity"'))
        self.assertLess(self.html.index('id="hub-activity"'), self.html.index('class="hub-browser"'))


class SharedFilesTests(unittest.TestCase):
    def test_the_mobile_sheet_is_on_the_web(self):
        import serve
        self.assertIn('/lib/mobile.css', serve.STATIC_FILES)
        self.assertTrue(serve.static_ok('/lib/mobile.css'))
        self.assertTrue((ROOT / 'lib' / 'mobile.css').is_file())

    def test_the_layouts_switch_on_html_data_mode(self):
        css = (ROOT / 'lib' / 'mobile.css').read_text(encoding='utf-8')
        self.assertIn('html[data-mode=mobile] [data-layout=browser],\n'
                      'html:not([data-mode=mobile]) [data-layout=mobile]{display:none!important}', css)
        # everything else in it is the mobile layout's own: nothing that a
        # browser page (the reader, the player, the studio) could pick up
        rules = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
        for sel in re.findall(r'([^{}]+)\{', rules):
            for part in sel.split(','):
                part = part.strip()
                if not part or part.startswith('@') or part == ':root':
                    continue
                self.assertTrue(re.search(r'\bm-|\[data-layout=|main\.hub', part), part)

    def test_parseh_js_offers_the_mode(self):
        js = (ROOT / 'lib' / 'parseh.js').read_text(encoding='utf-8')
        self.assertIn("var MODE_KEY = 'parseh_mode';", js)
        self.assertIn("'; Path=/; SameSite=Lax; Max-Age=31536000'", js)
        m = re.search(r'mode: \{([^}]*)\}', js)
        self.assertIsNotNone(m)
        for name in ('get: modeGet', 'set: modeSet', 'isMobile: isMobile', 'route: modeRoute',
                     'onChange: modeOnChange', 'pages: MOBILE_PAGES'):
            self.assertIn(name, m.group(1))
        # applied while <head> is parsed, as the theme is: after the export,
        # before the wait for the DOM
        tail = js[js.index('window.Parseh = '):]
        self.assertLess(tail.index('modeApply();'), tail.index("document.readyState === 'loading'"))


if __name__ == '__main__':
    unittest.main()
