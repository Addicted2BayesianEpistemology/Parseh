#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""THE BARE NOTE PAGE: the note, the studio's sheet, and nothing else.

    python3 -m unittest discover -s tests -p test_note_page.py

A note used to open the studio's whole document page inside the reader --
app.css, app.js, the exercise forms, the mode switch, the keeping and
explaining scripts, MathJax, about 1.3 MB of it, on every open and once per
book, because the assets hang off each book's own notes mount.  The owner
asked (2026-09-23) for a note to open at once; the answer is a page of its
own (`markdown/app/server.py` `page_note`, `templates/note.html`) that
carries the rendered note on the studio's reading sheet and loads no studio
script at all, with *open in the studio* in its header for the whole of it.

Two things this holds, because both are promises to a reader:

* a note that HOLDS AN EXERCISE is sent to the full page instead -- without
  the studio's script an exercise is a box that cannot be answered, and
  nothing inert is ever shown;
* the sheet is linked at the STUDIO's own address, not at this mount's, so
  two books share one copy instead of fetching one each.

Driven through the route itself over a temporary library, with the answer
read raw.
"""
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "markdown" / "exlex", ROOT / "markdown" / "app",
               ROOT / "lib", ROOT / "youtube" / "lib"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import server   # noqa: E402
import store    # noqa: E402

PLAIN = """---
title: About this bit
lang: en
target: fa
---

A plain note, with [گربه]{tl} in it.
"""

WITH_EXERCISE = """---
title: A note that asks something
lang: en
target: fa
---

Before.

:::exercise fill-blanks
prompt: Complete it.
content-direction: target
text: The cat is [[one]].
- [one] [گربه]{tl}
- [ ] [سگ]{tl}
:::
"""


class Fake:
    """What the studio's routes use of a handler, recording the answer."""

    def __init__(self):
        self.sent = None
        self.query = {}

    def send_bytes(self, data, ctype, status=200, headers=None):
        self.sent = (status, data, ctype, headers or {})

    def send_html(self, text, code=200):
        self.sent = (code, text.encode("utf-8"), "text/html; charset=utf-8", {})


class NotePage(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        was = store.use_library(Path(td.name))
        self.addCleanup(store.use_library, was)

    def page(self, markdown):
        meta = store.create(markdown)
        h = Fake()
        server.page_note(h, meta["id"])
        self.assertIsNotNone(h.sent, "the route answered")
        return meta, h.sent

    def html(self, markdown):
        meta, sent = self.page(markdown)
        self.assertEqual(sent[0], 200, sent)
        return meta, sent[1].decode("utf-8")

    def test_the_note_is_there_on_the_studios_own_sheet(self):
        meta, html = self.html(PLAIN)
        self.assertIn("About this bit", html)
        self.assertIn("گربه", html)
        # the reading sheet, and the language sheet beside it
        self.assertIn("/static/sheet.css", html)
        self.assertIn("/static/langs.css", html)

    def loads(self, html):
        """What the page really FETCHES: the src and href of its own tags.
        Read off the tags and not off the text, because the page explains in
        a comment which scripts it is not loading, and naming them there is
        the point of the comment."""
        return (re.findall(r'<script[^>]*\ssrc="([^"]+)"', html)
                + re.findall(r'<link[^>]*\shref="([^"]+)"', html))

    def test_it_loads_none_of_the_studios_machinery(self):
        """The whole point: what made a note slow was everything a document
        page carries for WRITING one."""
        _meta, html = self.html(PLAIN)
        got = self.loads(html)
        for name in ("app.js", "exform.js", "mode.js", "editor.js",
                     "keep.js", "explain.js", "activity.js", "app.css"):
            self.assertFalse([u for u in got if u.endswith("/" + name)],
                             "%s must not be loaded by a note: %s" % (name, got))
        # and no script of its own either: what it runs is inline
        self.assertEqual([u for u in got if u.endswith(".js")], [], got)

    def test_the_sheet_is_the_studios_one_copy_not_this_mounts(self):
        """Canonical assets (the owner's ask): the notes of two books point
        at the same file, so the phone and the browser cache it once."""
        _meta, html = self.html(PLAIN)
        for href in self.loads(html):
            if href.endswith(("sheet.css", "langs.css")):
                self.assertTrue(href.startswith(server.BASE + "/static/"),
                                "%s is not at the studio's own address" % href)

    def test_open_in_the_studio_is_in_the_header(self):
        meta, html = self.html(PLAIN)
        self.assertIn("open in the studio", html)
        self.assertIn("/doc/%s" % meta["id"], html)

    def test_a_note_holding_an_exercise_opens_the_full_page(self):
        """Nothing inert is ever shown: an exercise without the studio's
        script cannot be answered, so the bare page refuses itself."""
        meta, sent = self.page(WITH_EXERCISE)
        self.assertEqual(sent[0], 302, sent)
        self.assertEqual(sent[3].get("Location"), "%s/doc/%s" % (server.base(), meta["id"]))

    def test_the_render_says_how_many_exercises_it_drew(self):
        """The question is asked of the RENDER and not of the markdown: only
        the render knows what a block became."""
        import htmlgen
        self.assertEqual(htmlgen.render_document(PLAIN)["exercises"], 0)
        self.assertGreater(htmlgen.render_document(WITH_EXERCISE)["exercises"], 0)


class TheDocumentPageUnderANotesMount(unittest.TestCase):
    """THE OTHER HALF OF "ONE COPY FOR THE SHELF" (the owner, 2026-09-23,
    second block).

    A note that holds an exercise is sent to the document page, and from
    2026-09-23 that page is also what is KEPT for such a note when the book it
    sits in is kept on a phone.  `lib/offline.py` names the studio's files at
    the studio's own address, once for the whole phone; so the page has to ask
    for them there as well, or a phone that kept `/studio/static/app.js` would
    be asked for `/books/<slug>/notes/static/app.js`, hold nothing for it, and
    open the one note that was kept whole as an unanswerable box.

    Driven through the route under a mount, exactly as `serve.py`'s `_notes`
    runs it, with the answer read raw.
    """

    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        was = store.use_library(Path(td.name))
        self.addCleanup(store.use_library, was)
        self.mount = "/books/persian/kelile/notes"
        mounted = server.use_mount(self.mount, html_only=True)
        self.addCleanup(server.restore_mount, mounted)

    def page(self, markdown):
        meta = store.create(markdown)
        h = Fake()
        server.page_doc(h, meta["id"])
        self.assertIsNotNone(h.sent, "the route answered")
        self.assertEqual(h.sent[0], 200, h.sent)
        return meta, h.sent[1].decode("utf-8")

    def loads(self, html):
        return (re.findall(r'<script[^>]*\ssrc="([^"]+)"', html)
                + re.findall(r'<link[^>]*\shref="([^"]+)"', html))

    def test_the_studios_files_are_asked_for_at_the_studios_own_address(self):
        _meta, html = self.page(WITH_EXERCISE)
        files = [u for u in self.loads(html) if "/static/" in u]
        self.assertTrue(files, "the document page loads the studio's files")
        for url in files:
            self.assertTrue(url.startswith(server.BASE + "/static/"),
                            "%s is under this book's mount, so a second book "
                            "would keep a second copy of it" % url)
        self.assertTrue([u for u in files if u.endswith("/app.js")],
                        "the script that answers an exercise among them: %r" % files)

    def test_what_belongs_to_the_mount_still_names_the_mount(self):
        """Only the FILES move: the library link, the editor, the downloads
        and the media of this note are this book's and nowhere else's."""
        meta, html = self.page(WITH_EXERCISE)
        self.assertIn('href="%s/doc/%s/edit"' % (self.mount, meta["id"]), html)
        self.assertIn('data-base="%s"' % self.mount, html)

    def test_the_page_says_what_it_is_so_a_kept_copy_can_be_told_apart(self):
        """Away from the computer there is no redirect to see: the reader asks
        for the bare address and has to know whether what came back is the
        bare page or the whole studio (`lib/tex2html.py`, NOTE_FULL_MARK)."""
        _meta, html = self.page(WITH_EXERCISE)
        self.assertIn('<body data-page="doc"', html)


class TheSheetIsShared(unittest.TestCase):
    """app.css was split in two (2026-09-23): sheet.css is the reading sheet
    both pages link, app.css what is left.  /static/app.css still answers
    with both, so nothing that asked for it before lost anything."""

    def test_the_two_files_exist_and_the_sheet_holds_the_sheet(self):
        static = ROOT / "markdown" / "app" / "static"
        sheet = (static / "sheet.css").read_text(encoding="utf-8")
        app = (static / "app.css").read_text(encoding="utf-8")
        self.assertIn("@font-face", sheet)
        self.assertIn(".sheet", sheet)
        self.assertNotIn("@font-face", app.split("/*", 1)[0])

    def test_the_served_app_css_is_still_both(self):
        src = (ROOT / "markdown" / "app" / "server.py").read_text(encoding="utf-8")
        self.assertIn("def serve_app_css", src)
        self.assertIn("sheet.css", src)


if __name__ == "__main__":
    unittest.main()
