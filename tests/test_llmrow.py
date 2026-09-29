#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""THE LLM ROW (lib/llmrow.js), as the files around it name it.

    python3 -m unittest discover -s tests -p test_llmrow.py

What the row DOES -- the size said before the copy, the held text copied inside
the click, the box for a copy by hand, the two slots, the last-used button --
is driven in a real Chromium by tests/llmrow.mjs.  What is checked here is what
only the files can say, and what no browser test would notice missing until a
phone was offline:

* the toolbox serves the script, the phone keeps it (a reader and a player load
  it in their heads, and a page whose tag is in no offline list opens away from
  the computer and stops there), and the studio run on its own answers for it;
* every script the reader's template loads from lib/ is one a phone keeps -- not
  only this one: the list was held to the BUILT readers by another test, which
  passes over a reader built before the script was added;
* every page that mounts the row loads the script, under the surface's own name;
* the number of the Parseh that wrote a prompt is asked of the server and is
  written into no script (brief §3.4).
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "youtube/lib", "lib", "tests", "."):
    sys.path.insert(0, str(ROOT / p))

ROW = ROOT / "lib" / "llmrow.js"
_scratch = None
_patches = []


# THE PHONE-KEEPING MEMORIES GO TO A FOLDER OF THIS FILE'S OWN, as
# tests/test_tabcapture.py does: lib/offline.py remembers every file it hashes in
# config/digests.json, which is the owner's.
def setUpModule():
    global _scratch
    import offline
    _scratch = tempfile.TemporaryDirectory()
    config = Path(_scratch.name) / "config"
    _patches[:] = [patch.object(offline, "DIGESTS", str(config / "digests.json")),
                   patch.object(offline, "WHERES", str(config / "wheres.json")),
                   patch.object(offline, "_digests", None),
                   patch.object(offline, "_digests_new", False),
                   patch.object(offline, "_wheres_store", None),
                   patch.object(offline, "_wheres_store_new", False)]
    for p in _patches:
        p.start()


def tearDownModule():
    for p in _patches:
        p.stop()
    _scratch.cleanup()


class ServedAndKeptTests(unittest.TestCase):

    def test_the_toolbox_serves_it(self):
        import serve
        self.assertTrue(ROW.is_file())
        self.assertIn("/lib/llmrow.js", serve.STATIC_FILES)

    def test_a_phone_keeps_it(self):
        import offline
        self.assertIn("/lib/llmrow.js", offline.SHARED)

    def test_every_script_the_readers_template_loads_from_lib_is_kept(self):
        import offline
        source = (ROOT / "lib" / "tex2html.py").read_text(encoding="utf-8")
        linked = re.findall(r'<script src="__LIB__/([\w.\-]+\.js)"', source)
        self.assertIn("llmrow.js", linked, "the reader loads the row's script")
        missing = ["/lib/" + f for f in linked if "/lib/" + f not in offline.SHARED]
        self.assertEqual([], missing, "a reader loads these in its head, and no phone was given them")

    def test_the_player_loads_it_and_its_tag_is_in_that_list_too(self):
        page = (ROOT / "youtube" / "lib" / "player.html").read_text(encoding="utf-8")
        self.assertIn('<script src="/lib/llmrow.js"></script>', page)

    def test_the_studio_run_on_its_own_answers_for_it(self):
        import server as studio_server
        routes = [(m, rx, fn) for m, rx, fn in studio_server.ROUTES if fn is studio_server.serve_llmrow_js]
        self.assertEqual(1, len(routes), "one route answers /lib/llmrow.js")
        self.assertTrue(re.match(routes[0][1], "/lib/llmrow.js"))
        sent = {}

        class Handler:
            def send_bytes(self, data, ctype, code=200, headers=None):
                sent.update(data=data, ctype=ctype, code=code)

            def send_json(self, body, code=200):
                sent.update(json=body, code=code)

        studio_server.serve_llmrow_js(Handler())
        self.assertEqual(200, sent["code"])
        self.assertEqual(ROW.read_bytes(), sent["data"], "the toolbox's own bytes, not a copy")
        self.assertTrue(sent["ctype"].startswith("text/javascript"))


class MountedWhereItIsUsedTests(unittest.TestCase):
    """The eight surfaces are named as lib/promptkit.py will name them; each page that mounts
    the row says which it is, and loads the script that draws it."""

    def sources(self):
        import ytpages
        read = lambda *p: (ROOT.joinpath(*p)).read_text(encoding="utf-8")
        return {
            "studio prompt page": (read("markdown", "app", "templates", "prompt.html"),
                                   read("markdown", "app", "static", "app.js"), "studio-doc"),
            "editor's dialog": (read("markdown", "app", "templates", "edit.html"),
                                read("markdown", "app", "static", "editor.js"), "studio-exercises"),
            "video add page": (ytpages.add_page(), ytpages.ADD_PAGE_JS, "video-new"),
            "transcript tidy": (ytpages.add_page(), read("youtube", "lib", "subedit.js"), "transcript-tidy"),
            "player's panel": (read("youtube", "lib", "player.html"), read("youtube", "lib", "player.js"), "video-region"),
            "player's Ask LLM": (read("youtube", "lib", "player.html"), read("youtube", "lib", "player.js"), "ask"),
            "reader's sheet": (read("lib", "tex2html.py"), read("lib", "tex2html.py"), "book-region"),
            "reader's Ask LLM": (read("lib", "tex2html.py"), read("lib", "tex2html.py"), "ask"),
        }

    def test_each_page_loads_the_script_and_names_its_surface(self):
        for name, (page, script, surface) in self.sources().items():
            self.assertIn("/llmrow.js", page, "%s loads the row's script" % name)
            self.assertRegex(script, r"surface: ['\"]%s['\"]" % re.escape(surface),
                             "%s mounts the row as %s" % (name, surface))

    def test_the_two_buttons_it_replaces_are_gone_from_the_prompt_page(self):
        page = (ROOT / "markdown" / "app" / "templates" / "prompt.html").read_text(encoding="utf-8")
        self.assertNotIn('id="btn-copy-prompt"', page)
        self.assertIn('id="llm-row"', page)


class TheNumberIsAskedNotWrittenTests(unittest.TestCase):

    def test_no_script_carries_the_version(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        for name in ("llmrow.js", "llm.js"):
            src = (ROOT / "lib" / name).read_text(encoding="utf-8")
            self.assertNotIn(version, src, name)
            self.assertIsNone(re.search(r"\ba\d+\.\d+\.\d+\b", src),
                              "%s writes a release number into itself" % name)

    def test_asks_the_server_for_it(self):
        src = (ROOT / "lib" / "llm.js").read_text(encoding="utf-8")
        self.assertIn("/__version", src)
        import serve
        text = (ROOT / "serve.py").read_text(encoding="utf-8")
        self.assertIn('if path == "/__version":', text)
        self.assertIn("version.VERSION", text)
        self.assertTrue(hasattr(serve, "version"))


if __name__ == "__main__":
    unittest.main()
