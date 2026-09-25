# SPDX-License-Identifier: GPL-3.0-or-later
"""A document, and a deck's picked exercises, as ONE HTML page for a website
(markdown/app/webexport.py, TO-DO §8.38 and §9.7).

What these hold the export to, file by file: everything the page needs is
inside it (its faces, its pictures, its recordings -- a clip cut to its
stretch where ffmpeg is here, the whole recording once where it is not --
and the script that works its exercises); nothing of the Markdown is (not a
target-language line's source, not a line number, not an exercise's
Markdown, not a linked document's name); the page may reach nothing but a
YouTube player (its Content-Security-Policy says so to the browser); and its
script is the slice of app.js that draws and marks an exercise, with no call
in it that could save anything.  tests/html_export.mjs opens the files from
disk in a browser and answers their exercises; these read the files.

Every test works in a temporary studio library (store.use_library) and a
temporary exercises/ root (decks.set_dir), and puts both back."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "lib", ROOT / "youtube" / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import audiofile            # noqa: E402
import deckroutes           # noqa: E402
import decks                # noqa: E402
import languages            # noqa: E402
import server               # noqa: E402
import store                # noqa: E402
import webexport            # noqa: E402

STARTERS = ROOT / "markdown" / "exlex" / "starters"
ASSETS = STARTERS / "assets"


def starter_media(path):
    f = ASSETS / path
    return f if f.is_file() else None


def body_of(page):
    """The page less its <style> and its <script>s: what it SHOWS."""
    s = re.sub(r"<style>.*?</style>", "", page, flags=re.S)
    return re.sub(r"<script\b[^>]*>.*?</script>", "", s, flags=re.S)


def csp_of(page):
    m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', page)
    return m.group(1) if m else ""


def foot_of(page):
    """The page's one <footer>, after everything it shows."""
    shown = body_of(page)
    feet = re.findall(r'<footer class="xp-foot">.*?</footer>', shown, re.S)
    assert len(feet) == 1, "one foot, not %d" % len(feet)
    assert shown.index(feet[0]) > shown.index("</main>"), "the foot is below the page"
    return feet[0]


def theme_of(page):
    """-> (the theme the page's <body> names, the Aa menu's themes in order,
    the one it has selected).

    AN EXPORTED PAGE OPENS ON SEPIA (TO-DO §2.26), the paper made for
    reading, whatever the studio was showing and whatever the system
    prefers: the page names it on its own <body>, so that it is sepia before
    its script has run and where it never runs, and its script starts from
    there.  A default and not a lock, so the menu offers all three still.
    tests/html_export.mjs opens both files and sees it painted, on a dark
    system and in a browser profile made that moment."""
    body = re.search(r"<body\b[^>]*>", page).group(0)
    named = re.search(r'data-theme="([^"]*)"', body)
    menu = re.search(r'<select id="xp-theme">(.*?)</select>', page, re.S).group(1)
    return (named.group(1) if named else None,
            re.findall(r'<option value="([^"]+)"', menu),
            re.findall(r'<option value="([^"]+)" selected>', menu))


def links_of(fragment):
    """The addresses a fragment links to, each of which must open in a tab
    of its own (the page keeps nothing, so leaving it loses the answers)."""
    tags = re.findall(r"<a [^>]*>", fragment)
    for tag in tags:
        assert 'target="_blank"' in tag and 'rel="noopener noreferrer"' in tag, tag
    return [re.search(r'href="([^"]+)"', tag).group(1) for tag in tags]


class Fake:
    """What the studio's and the decks' routes use of a handler."""

    def __init__(self, raw=b"", query=""):
        self.raw = raw
        self.query = urllib.parse.parse_qs(query)
        self.sent = None

    def _body(self):
        return self.raw

    def _json_body(self):
        return json.loads(self.raw.decode("utf-8")) if self.raw else {}

    def send_json(self, obj, code=200):
        self.sent = (code, json.loads(json.dumps(obj, ensure_ascii=False)), None, {})

    def send_bytes(self, data, ctype, code=200, extra=None):
        self.sent = (code, data, ctype, dict(extra or {}))

    def send_file(self, path, download_name=None, inline_type=None):
        self.sent = (200, Path(path).read_bytes(), inline_type, {})


class Starters(unittest.TestCase):
    """Every language's starter document -- the tour of everything a
    document can hold: target text in every form, footnotes, pictures, a
    recording and a clip of it, a formula, a video, an exercise of every
    kind -- exported and read back."""

    @classmethod
    def setUpClass(cls):
        cls.pages = {}
        for f in sorted(STARTERS.glob("*.md")):
            md = f.read_text(encoding="utf-8")
            name, data = webexport.document_html("starter-%s-0a1b2c" % f.stem,
                                                 {"title": "Starter " + f.stem}, md,
                                                 starter_media)
            cls.pages[f.stem] = (md, name, data.decode("utf-8"))

    def test_every_language_is_exported(self):
        self.assertEqual(set(self.pages), set(languages.LANGS),
                         "a starter per registry language, and each one exported")
        for code, (_md, name, page) in self.pages.items():
            with self.subTest(code):
                self.assertEqual(name, "starter-%s.html" % code)
                self.assertTrue(page.startswith("<!DOCTYPE html>"))
                self.assertIn('data-lang="%s"' % code, page)
                self.assertEqual(page.count('<article id="sheet"'), 1)

    def test_the_page_may_reach_nothing_but_a_youtube_player(self):
        for code, (_md, _name, page) in self.pages.items():
            with self.subTest(code):
                csp = csp_of(page)
                self.assertIn("default-src 'none'", csp)
                self.assertIn("connect-src 'none'", csp)
                self.assertIn("form-action 'none'", csp)
                self.assertIn("worker-src 'none'", csp)
                self.assertIn("frame-src https://www.youtube-nocookie.com", csp)
                shown = body_of(page)
                # every address the page names is its own, or YouTube's player
                for url in re.findall(r'(?:src|href)="([^"]+)"', shown):
                    self.assertTrue(url.startswith(("data:", "#", "https://www.youtube-nocookie.com/",
                                                    "http://", "https://", "mailto:")),
                                    "%s: %s" % (code, url[:60]))
                    if url.startswith(("http://", "https://")) and "youtube-nocookie" not in url:
                        # a link the author wrote: followed only if clicked
                        self.assertRegex(shown, r'<a [^>]*href="%s"' % re.escape(url))
                self.assertNotIn("/static/", shown)
                self.assertNotIn("/media/", shown)
                # the page names no referrer, its YouTube player alone the
                # site it is on: YouTube plays nothing for a player that
                # does not say where it is ("Video player configuration error")
                self.assertIn('<meta name="referrer" content="no-referrer">', page)
                players = re.findall(r"<iframe [^>]*>", shown)
                self.assertTrue(players, "the starter embeds a video")
                for tag in players:
                    self.assertIn('src="https://www.youtube-nocookie.com/embed/', tag)
                    self.assertEqual(re.findall(r'referrerpolicy="([^"]*)"', tag),
                                     ["strict-origin-when-cross-origin"])

    def test_the_foot_says_where_the_page_came_from(self):
        for code, (_md, _name, page) in self.pages.items():
            with self.subTest(code):
                foot = foot_of(page)
                self.assertIn("This page was exported from Parseh.", foot)
                self.assertEqual(links_of(foot), [webexport.GITHUB, webexport.GUIDE])

    def test_nothing_of_the_markdown_travels(self):
        # (the starters teach the notation, so it is IN their text, in code
        # spans; what must not travel is the source the studio keeps beside
        # what it renders -- a document that does not teach it is below)
        for code, (md, _name, page) in self.pages.items():
            with self.subTest(code):
                shown = body_of(page)
                for attr in webexport.SOURCE_ATTRS:
                    self.assertNotIn(attr + "=", page, attr)
                # the studio's writing pieces are not in it
                for cls in webexport.DROP_CLASSES:
                    self.assertNotIn('class="%s"' % cls, shown, cls)
                self.assertNotIn("colophon", shown, "the technical colophon is left out")

    def test_a_document_that_does_not_teach_the_notation_shows_none_of_it(self):
        md = ("---\ntitle: Secret source\nsubtitle: shown\nnote: shown too\ntarget: fa\n"
              "author-only: never shown\n---\n\n"
              "Prose with [سلام]{tl color=red} inline.\n\n"
              "[کتاب خوبی است]{tl bg=blue}\n\n"
              "![a picture](images/starter-apple.svg){width=40 align=center}\n\n"
              "![](audio/starter-chime.mp3){start=0 end=0.4}\n\n"
              ":::exercise single-choice\nprompt: Pick one\n- [x] [سلام]{tl}\n- [ ] [کتاب]{tl}\n:::\n\n"
              "A footnote[^1].\n\n[^1]: Its [خدا]{tl} body.\n")
        _n, data = webexport.document_html("secret-0a1b2c", {"title": "Secret source"}, md,
                                           starter_media)
        page = data.decode("utf-8")
        shown = body_of(page)
        # what the page shows, and the data its script reads (its code is
        # the studio's, whose comments speak of the notation in general)
        data = "".join(re.findall(r'<script id="[^"]+" type="application/json">(.*?)</script>',
                                  page, flags=re.S))
        for mark in ("{tl", "color=red", "bg=blue", ":::", "](images/", "](audio/", "{width=",
                     "start=0 end", "[^1]", "author-only", "never shown",
                     "- [x]", "prompt:"):
            self.assertNotIn(mark, shown, mark)
            self.assertNotIn(mark, data, mark)
        self.assertIn("سلام", shown)
        self.assertIn("Pick one", shown)

    def test_the_media_travel_inside_it(self):
        for code, (md, _name, page) in self.pages.items():
            with self.subTest(code):
                shown = body_of(page)
                self.assertRegex(shown, r'<img [^>]*src="data:image/svg\+xml;base64,')
                store_json = re.search(r'<script id="parseh-media" type="application/json">(.*?)</script>',
                                       page, re.S).group(1)
                media = json.loads(store_json)
                keys = set(re.findall(r'data-media="([^"]+)"', shown))
                self.assertTrue(keys, "the recordings are there")
                self.assertEqual(keys, set(media), "every recording played is carried, once")
                for data in media.values():
                    self.assertTrue(data.startswith("data:audio/"))
                # the clip of the chime (start=0 end=0.4): cut where ffmpeg is,
                # the whole chime with its window where it is not
                if audiofile.have_ffmpeg():
                    self.assertIn('data-cut="1"', shown)
                else:
                    self.assertIn('data-frag="#t=0,0.4"', shown)

    def test_the_faces_are_inside_it_and_only_the_letters_used(self):
        for code, (_md, _name, page) in self.pages.items():
            with self.subTest(code):
                css = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
                self.assertIn('font-family: "TeX Gyre Pagella"', css)
                self.assertNotRegex(css, r"url\((?!data:)", "no face is fetched")
                L = languages.get(code)
                if code == "fa":
                    self.assertIn('"Vazirmatn"', css)
                if code == "hi":
                    self.assertIn('"Noto Serif Devanagari"', css)
                if L.script == "latin":
                    self.assertNotIn('"Vazirmatn"', css, "a Latin page carries no Persian face")

    def test_the_page_opens_on_sepia_and_offers_all_three(self):
        for code, (_md, _name, page) in self.pages.items():
            with self.subTest(code):
                self.assertEqual(theme_of(page), ("sepia", ["paper", "sepia", "dark"], ["sepia"]))

    def test_the_contents_and_the_glosses_are_panels(self):
        for code, (_md, _name, page) in self.pages.items():
            with self.subTest(code):
                shown = body_of(page)
                self.assertIn('class="xp-panel xp-contents"', shown)
                self.assertIn('class="xp-panel xp-glosses"', shown)
                self.assertIn('class="gl-table', shown)
                self.assertNotIn('data-tab="cards"', shown, "the glosses' drill is not in it")
                self.assertNotIn("gl-foot", shown)

    def test_a_formula_brings_mathjax_and_a_page_without_one_does_not(self):
        md, _name, page = self.pages["it"]
        self.assertIn('class="math', page)
        self.assertIn("window.MathJax = {startup: {typeset: false}", page)
        _n, data = webexport.document_html("plain-0a1b2c", {"title": "Plain"},
                                           "---\ntitle: Plain\ntarget: it\n---\n\nNo formula.\n",
                                           starter_media)
        self.assertNotIn("window.MathJax = {startup", data.decode("utf-8"))
        self.assertLess(len(data), 1500000, "and none of its two megabytes")

    def test_the_script_is_the_exercises_and_nothing_that_saves(self):
        js = webexport._runtime()
        # the transliteration cloud travels too (the owner, 2026-09-25), with
        # appliers of the page's own that keep nothing (export.js, xpCloud)
        for needed in ("function bindExercises", "function applyTypo", "function clipWindow",
                       "function bindFootnoteClouds", "function armClipReplay",
                       "function bindColorPalette"):
            self.assertIn(needed, js)
        for never in ("function initDoc", "function initIndex", "function docColorApplier",
                      "function docMarkApplier", "function bindImageLayout", "function api(", "fetch(", "XMLHttpRequest",
                      "sendBeacon", "document.cookie", "indexedDB", "serviceWorker",
                      "window.localStorage", "window.sessionStorage", "__FOLD__"):
            self.assertNotIn(never, js, never)
        script = webexport._script(False)
        self.assertIn("(function (localStorage, sessionStorage) {", script)
        self.assertIn("})(parsehMemory(), parsehMemory());", script)
        self.assertNotIn("</script", script)
        deno = shutil.which("deno")
        if deno:
            with tempfile.TemporaryDirectory() as td:
                f = Path(td) / "script.js"
                f.write_text(script, encoding="utf-8")
                run = subprocess.run([deno, "eval", "new Function(Deno.readTextFileSync(%r))" % str(f)],
                                     capture_output=True, text=True, timeout=120)
                self.assertEqual(run.returncode, 0, run.stderr[-800:])


class Cleaning(unittest.TestCase):
    def test_a_link_to_another_document_keeps_its_words_and_nothing_else(self):
        md = ("---\ntitle: Links\ntarget: it\n---\n\nSee [the other page](doc:Secret Other Doc) "
              "and [a site](https://example.org).\n")
        _n, data = webexport.document_html("links-0a1b2c", {"title": "Links"}, md, lambda p: None)
        shown = body_of(data.decode("utf-8"))
        self.assertIn('<span class="doclink-plain">the other page</span>', shown)
        self.assertNotIn("Secret Other Doc", data.decode("utf-8"))
        self.assertRegex(shown, r'<a class="lnk" href="https://example.org"')

    def test_a_missing_file_is_a_placeholder_not_a_request(self):
        md = "---\ntitle: Gone\ntarget: it\n---\n\n![a cat](images/cat.png)\n"
        _n, data = webexport.document_html("gone-0a1b2c", {"title": "Gone"}, md, lambda p: None)
        shown = body_of(data.decode("utf-8"))
        self.assertIn("img-placeholder", shown)
        self.assertNotIn('src="images/', shown)

    def test_a_recording_played_twenty_times_is_carried_once(self):
        def page_of(n):
            lines = ["---", "title: Many", "target: it", "---", ""]
            lines += ["![](audio/starter-chime.mp3)" for _ in range(n)]
            _n, data = webexport.document_html("many-0a1b2c", {"title": "Many"},
                                               "\n\n".join(lines), starter_media)
            return data.decode("utf-8")
        was = audiofile.have_ffmpeg
        audiofile.have_ffmpeg = lambda: False          # the whole recording, as without ffmpeg
        try:
            one, twenty = page_of(1), page_of(20)
        finally:
            audiofile.have_ffmpeg = was
        media = json.loads(re.search(r'<script id="parseh-media" type="application/json">(.*?)</script>',
                                     twenty, re.S).group(1))
        self.assertEqual(len(media), 1)
        self.assertEqual(twenty.count('data-media="a0"'), 20)
        chime = (ASSETS / "audio" / "starter-chime.mp3").read_bytes()
        self.assertLess(len(twenty) - len(one), len(chime), "one copy of the chime, not twenty")

    @unittest.skipUnless(audiofile.have_ffmpeg(), "ffmpeg is not installed")
    def test_a_clip_is_cut_to_its_stretch(self):
        md = ("---\ntitle: Clip\ntarget: it\n---\n\n"
              "![](audio/starter-chime.mp3){start=0 end=0.4}\n\n"
              "![](audio/starter-chime.mp3){start=0 end=0.4}\n")
        _n, data = webexport.document_html("clip-0a1b2c", {"title": "Clip"}, md, starter_media)
        page = data.decode("utf-8")
        media = json.loads(re.search(r'<script id="parseh-media" type="application/json">(.*?)</script>',
                                     page, re.S).group(1))
        self.assertEqual(len(media), 1, "the same stretch twice is cut once")
        self.assertEqual(page.count('data-cut="1"'), 2)
        import base64
        cut = base64.b64decode(list(media.values())[0].split(",", 1)[1])
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / ("clip" + audiofile.best_output()[0])
            f.write_bytes(cut)
            got = audiofile.duration(str(f))
        if got is not None:
            self.assertAlmostEqual(got, 0.4, delta=0.15, msg="the clip is its stretch")

    def test_a_disposition_names_the_file_in_any_script(self):
        d = webexport.disposition("تمرین-ها.html")
        self.assertTrue(d.startswith('attachment; filename="'))
        self.assertIn("filename*=UTF-8''" + urllib.parse.quote("تمرین-ها.html", safe=""), d)
        self.assertIn('filename="', d)
        self.assertRegex(d, r'filename="[\x20-\x7e]+"')


class Routes(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        was = store.use_library(root / "library")
        self.addCleanup(store.use_library, was)
        was_dir = decks.set_dir(root / "exercises")
        self.addCleanup(decks.set_dir, was_dir)

    def test_the_document_downloads_as_one_page(self):
        md = (STARTERS / "fa.md").read_text(encoding="utf-8")
        meta = store.create(md)
        for sub in ("images", "audio"):
            for f in (ASSETS / sub).iterdir():
                if sub == "images":
                    store.save_image(meta["id"], f.name, f.read_bytes())
                else:
                    store.save_audio(meta["id"], f.name, f.read_bytes())
        route = [p for m, p, fn in server.ROUTES if fn is server.serve_download][0]
        self.assertTrue(re.match(route, "/download/%s/html" % meta["id"]))
        h = Fake()
        server.serve_download(h, meta["id"], "html")
        status, data, ctype, headers = h.sent
        self.assertEqual((status, ctype), (200, "text/html; charset=utf-8"))
        self.assertRegex(headers["Content-Disposition"], r'^attachment; filename="[^"]+\.html"')
        page = data.decode("utf-8")
        self.assertRegex(page, r'<img [^>]*src="data:image/')
        self.assertIn("data:audio/", page)
        self.assertEqual(store.get(meta["id"])[1], md, "the document is not touched")

    def test_the_download_menu_offers_it_under_the_pdf(self):
        tpl = (ROOT / "markdown" / "app" / "templates" / "doc.html").read_text(encoding="utf-8")
        pdf = tpl.index('id="dl-pdf"')
        html_at = tpl.index('id="dl-html"')
        self.assertLess(pdf, html_at)
        self.assertIn("/download/{{DOC_ID}}/html", tpl)
        self.assertIn("HTML page, for a website (.html)", tpl)

    def test_the_picked_exercises_download_as_one_page_that_crams_them(self):
        d = decks.create_deck("Italiano: esercizi", "it")
        F, S = d["folder"], d["slug"]
        for f in (ASSETS / "images").iterdir():
            decks.add_image(F, S, f.name, f.read_bytes())
        for f in (ASSETS / "audio").iterdir():
            decks.add_audio(F, S, f.name, f.read_bytes())
        md = (STARTERS / "it.md").read_text(encoding="utf-8")
        blocks = re.findall(r"^:::exercise[^\n]*\n.*?^:::\s*$", md, re.S | re.M)
        ids = [decks.add_item(F, S, b)["id"] for b in blocks]
        picked = ids[::2]
        before = [decks.get_item(F, S, i) for i in ids]
        files = sorted(p.name for p in decks.deck_dir(F, S).rglob("*"))
        h = Fake(json.dumps({"ids": picked}).encode("utf-8"))
        deckroutes.dispatch(h, "POST", "/api/decks/%s/%s/export-html" % (F, S))
        status, data, ctype, headers = h.sent
        self.assertEqual((status, ctype), (200, "text/html; charset=utf-8"))
        self.assertIn('filename="%s.html"' % S, headers["Content-Disposition"])
        page = data.decode("utf-8")
        cards = json.loads(re.search(r'<script id="parseh-cards" type="application/json">(.*?)</script>',
                                     page, re.S).group(1))
        self.assertEqual(len(cards), len(picked), "the picked ones, and only those")
        for c in cards:
            self.assertEqual(set(c), {"item", "html", "solution"})
            self.assertEqual(set(c["item"]), {"id", "label", "subtype", "excerpt"},
                             "no Markdown, footnotes, tags or schedule")
            self.assertNotIn(c["item"]["id"], ids, "an exercise's id stays in the deck")
            self.assertIn('class="exercise', c["html"])
        for item_id in ids:
            item = decks.get_item(F, S, item_id)
            self.assertNotIn(item["markdown"], page)
        self.assertNotIn(":::exercise", body_of(page))
        self.assertIn("connect-src 'none'", csp_of(page))
        self.assertEqual(theme_of(page), ("sepia", ["paper", "sepia", "dark"], ["sepia"]),
                         "it opens on Sepia too, and Aa offers all three")
        foot = foot_of(page)
        self.assertIn("This page was exported from Parseh.", foot)
        self.assertEqual(links_of(foot), [webexport.GITHUB, webexport.GUIDE])
        # nothing about the deck changed: no item touched, nothing scheduled
        self.assertEqual([decks.get_item(F, S, i) for i in ids], before)
        self.assertEqual(sorted(p.name for p in decks.deck_dir(F, S).rglob("*")), files)

    def test_nothing_picked_is_refused(self):
        d = decks.create_deck("Empty", "it")
        h = Fake(json.dumps({"ids": []}).encode("utf-8"))
        deckroutes.dispatch(h, "POST", "/api/decks/%s/%s/export-html" % (d["folder"], d["slug"]))
        self.assertGreaterEqual(h.sent[0], 400)

    def test_the_deck_page_offers_it_beside_cram_in_the_browser_layout_alone(self):
        tpl = (ROOT / "markdown" / "app" / "templates" / "deck.html").read_text(encoding="utf-8")
        cram = tpl.index('id="btn-cram"')
        xp = tpl.index('id="btn-export-html"')
        self.assertLess(cram, xp)
        tag = tpl[tpl.rindex("<button", 0, xp):tpl.index(">", xp)]
        self.assertIn('data-layout="browser"', tag)
        self.assertIn("disabled", tag)
        self.assertIn("Export selected to HTML", tpl)


if __name__ == "__main__":
    unittest.main()
