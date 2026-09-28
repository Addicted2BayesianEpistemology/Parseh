#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""THE TAB'S SOUND, RECORDED IN ONE PLACE (youtube/lib/tabcapture.js), as the files around it name it.

    python3 -m unittest discover -s tests -p test_tabcapture.py

What the recording DOES -- one share, the waveform's numbers, the sound in
chunks, the cancel, the words -- is driven in a real Chrome by
tests/youtube_capture.mjs.  What is checked here is what only the files can
say, and what no browser test would ever notice missing:

* the player's page links exactly the files a kept video carries offline
  (lib/offline.py PLAYER_FILES).  Nothing held the two together: the day
  tabcapture.js was added to the page and not to the list, a video kept for
  the phone would have opened offline and stopped at "loading the
  annotations…", which is what happened to the stylesheet and the script
  before that list existed;
* the server sends the new file at the address the page asks for;
* the sentences that say why a tab cannot be recorded are the card kit's,
  word for word (the add page never loads the card kit, so the module carries
  its own copy, and two copies of a sentence drift);
* nothing in it asks for the microphone.
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

PLAYER_HTML = ROOT / "youtube" / "lib" / "player.html"
TABCAPTURE = ROOT / "youtube" / "lib" / "tabcapture.js"
CARDKIT = ROOT / "lib" / "cardkit.js"

_scratch = None
_patches = []


# THE PHONE-KEEPING MEMORIES GO TO A FOLDER OF THIS FILE'S OWN, as
# tests/test_mobile_pages.py does: lib/offline.py remembers every file it
# hashes in config/digests.json, which is the owner's.
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
    for p in reversed(_patches):
        p.stop()
    _scratch.cleanup()


def page_links():
    """Every script and stylesheet the player's page asks the parser to fetch,
    split into the video mount's own (`__BASE__/...`, as the server writes the
    mount in) and the toolbox's (`/lib/...`)."""
    html = PLAYER_HTML.read_text(encoding="utf-8")
    own, shared = [], []
    for tag, rest in re.findall(r"<(script|link)\b([^>]*)>", html, re.I):
        if tag.lower() == "link" and "stylesheet" not in rest:
            continue
        m = re.search(r"\b(?:src|href)=\"([^\"]+)\"", rest, re.I)
        if not m or "://" in m.group(1):
            continue
        url = m.group(1)
        if url.startswith("__BASE__"):
            own.append(url[len("__BASE__"):])
        else:
            shared.append(url)
    return own, shared


def sentences(source, names):
    """The string constants `var NAME = '...'` of a script, by name."""
    out = {}
    for name in names:
        m = re.search(r"var %s = ((?:'[^']*'(?:\s*\+\s*)?\s*)+);" % name, source)
        assert m, "%s is not a string constant in the script" % name
        out[name] = "".join(re.findall(r"'([^']*)'", m.group(1)))
    return out


class WhatAKeptVideoCarriesTests(unittest.TestCase):

    def test_the_player_links_exactly_the_files_the_offline_list_names(self):
        import offline
        own, _shared = page_links()
        self.assertEqual(sorted(own), sorted(offline.PLAYER_FILES),
                         "what player.html links from the video mount is what a kept video carries")
        self.assertIn("/lib/tabcapture.js", own, "the tab capture is one of them")

    def test_the_toolbox_files_it_links_are_in_the_shared_list(self):
        import offline
        _own, shared = page_links()
        self.assertTrue(shared)
        missing = [u for u in shared if u not in offline.SHARED]
        self.assertEqual(missing, [], "the toolbox's files the player links, and no phone was given")

    def test_the_guard_would_catch_a_file_left_out(self):
        import offline
        without = tuple(f for f in offline.PLAYER_FILES if f != "/lib/tabcapture.js")
        own, _shared = page_links()
        with patch.object(offline, "PLAYER_FILES", without):
            self.assertNotEqual(sorted(own), sorted(offline.PLAYER_FILES))

    def test_a_kept_video_lists_the_file_with_its_digest(self):
        import offline
        video = ROOT / "tests" / "fixtures" / "videos" / "italian" / "kL9mN1oP3qR"
        rec = offline.video(str(video), "kL9mN1oP3qR", "/youtube")
        by_url = {e["url"]: e for e in rec["small"]}
        entry = by_url.get("/youtube/lib/tabcapture.js")
        self.assertIsNotNone(entry, "the record of a kept video names the file")
        self.assertEqual(entry["bytes"], TABCAPTURE.stat().st_size)
        self.assertTrue(entry.get("digest"), "and weighs it, so a phone can tell a broken copy")

    def test_the_server_sends_it(self):
        import serve
        self.assertIn("/youtube/lib/tabcapture.js", serve.STATIC_FILES)
        self.assertTrue(TABCAPTURE.is_file())


class WhatTheModuleSaysTests(unittest.TestCase):

    def test_the_sentences_are_the_card_kits(self):
        # the card kit's are inside a function, on one line each; read them by
        # what they say and match the module's constants to them
        kit = CARDKIT.read_text(encoding="utf-8")
        body = re.search(r"function tabProblem\(\) \{(.*?)\n  \}\n", kit, re.S).group(1)
        said = re.findall(r"return '([^']+)';", body)
        self.assertEqual(len(said), 3, "the card kit's tabProblem says three things: " + repr(said))
        mine = sentences(TABCAPTURE.read_text(encoding="utf-8"),
                         ["SAY_SECURE", "SAY_BROWSER", "SAY_READER"])
        self.assertEqual(said, [mine["SAY_SECURE"], mine["SAY_BROWSER"], mine["SAY_READER"]],
                         "the same three sentences, in the same order")

    def test_the_microphone_is_never_asked_for(self):
        source = TABCAPTURE.read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
        code = re.sub(r"(?m)//.*$", "", code)
        self.assertNotIn("getUserMedia", code)
        self.assertNotIn("audioinput", code)

    def test_nothing_is_ever_connected_to_the_speakers(self):
        code = re.sub(r"/\*.*?\*/", "", TABCAPTURE.read_text(encoding="utf-8"), flags=re.S)
        code = re.sub(r"(?m)//.*$", "", code)
        self.assertNotIn(".destination", code)

    def test_the_worklet_is_a_string_made_into_a_blob_and_not_a_file(self):
        # so that a kept video needs nothing but tabcapture.js for the sound
        # (lib/offline.py PLAYER_FILES has no second file), and no policy the
        # pages do not set could refuse it
        import offline
        source = TABCAPTURE.read_text(encoding="utf-8")
        self.assertIn("registerProcessor(", source)
        self.assertIn("URL.createObjectURL(new Blob([WORKLET]", source)
        self.assertIn("audioWorklet.addModule(url)", source)
        self.assertEqual([f for f in offline.PLAYER_FILES if "worklet" in f.lower()], [])

    def test_it_is_a_classic_script(self):
        # the phone's copy of the player loads it with a plain <script src>
        source = TABCAPTURE.read_text(encoding="utf-8")
        self.assertFalse(re.search(r"(?m)^\s*(import|export)\b", source))
        self.assertIn("window.ParsehTabCapture", source)


if __name__ == "__main__":
    unittest.main()
