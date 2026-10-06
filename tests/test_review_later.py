#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""REVIEW LATER IN THE BOOK READER AND THE VIDEO PLAYER (a0.5.0, lane G2): what the files say.

The behaviour is tests/review_later.mjs's, driven in a browser on the real hub; here are the things a
browser would not notice breaking -- a new file in none of the lists a phone's kept page and the server
read, a loader line out of order, a string made into HTML, a rule that stopped saying which control it is
for.  The core (the store, the door, the sidebar) is tests/test_later.py's.

    python3 -m unittest tests.test_review_later   (or: python3 tests/test_review_later.py)
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in ("lib", "youtube/lib", "."):
    sys.path.insert(0, str(ROOT / folder))

import offline  # noqa: E402
import serve  # noqa: E402

READER = (ROOT / "lib" / "later-reader.js").read_text(encoding="utf-8")
CARDS = (ROOT / "lib" / "later-cards.js").read_text(encoding="utf-8")
PARSEH = (ROOT / "lib" / "parseh.js").read_text(encoding="utf-8")
TOUCH = (ROOT / "lib" / "wordtouch.js").read_text(encoding="utf-8")
MOBILE = (ROOT / "lib" / "mobile.css").read_text(encoding="utf-8")
LATERCSS = (ROOT / "lib" / "later.css").read_text(encoding="utf-8")
PLAYER = (ROOT / "youtube" / "lib" / "player.js").read_text(encoding="utf-8")
PLAYERHTML = (ROOT / "youtube" / "lib" / "player.html").read_text(encoding="utf-8")
PLAYERCSS = (ROOT / "youtube" / "lib" / "style.css").read_text(encoding="utf-8")
FILES = ("/lib/later-reader.js", "/lib/later-cards.js")
NO_HTML_FROM_STRINGS = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "createContextualFragment", "srcdoc")


class Files(unittest.TestCase):
    def test_the_two_new_scripts_are_files_the_server_hands_out_and_a_phone_keeps(self):
        for url in FILES:
            self.assertTrue((ROOT / url.lstrip("/")).is_file(), url)
            self.assertIn(url, serve.STATIC_FILES, url)
            self.assertTrue(serve.static_ok(url), url)
            self.assertIn(url, offline.SHARED, url)
            self.assertIn(url, offline.shell()["files"], url)

    def test_the_harness_is_there_and_says_what_it_builds(self):
        text = (ROOT / "tests" / "later_harness.py").read_text(encoding="utf-8")
        for word in ("multi-fa", "multi-en", "EN_VIDEO", "FA_VIDEO", "old-fa"):
            self.assertIn(word, text)


class Loading(unittest.TestCase):
    def reader_block(self):
        start = PARSEH.index("/* REVIEW LATER (a0.5.0): the chunks a person flags while reading")
        return PARSEH[start:PARSEH.index("if (window.ParsehMobileReader) return;", start)]

    def test_every_reader_loads_the_three_scripts_in_order_before_the_mobile_layer(self):
        block = self.reader_block()
        self.assertIn("[['ParsehLater', 'later.js'], ['ParsehLaterCards', 'later-cards.js'],", block)
        self.assertIn("['ParsehLaterReader', 'later-reader.js']", block)
        self.assertIn("lt.async = false;", block, "put in by hand they run in the order they were put in only if told not to be async")
        self.assertLess(block.index("later.js"), block.index("later-cards.js"))
        self.assertLess(block.index("later-cards.js"), block.index("later-reader.js"))
        # inside the reader's own block: a reader is known by its address, and a video's page loads its own
        reader = PARSEH[PARSEH.rindex("(function () {", 0, PARSEH.index("document.documentElement.classList.add('m-reader')")):]
        self.assertIn("REVIEW LATER (a0.5.0)", reader[:reader.index("if (window.ParsehMobileReader) return;")])

    def test_the_player_page_loads_the_store_and_the_cards_before_its_own_script(self):
        a, b, c = (PLAYERHTML.index(s) for s in ('<script src="/lib/later.js"></script>',
                                                   '<script src="/lib/later-cards.js"></script>',
                                                   '<script src="__BASE__/lib/player.js"></script>'))
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertNotIn("later", PARSEH[PARSEH.index("a video's page, in the mobile interface"):PARSEH.index("a book's reader, in the mobile interface")])


class Source(unittest.TestCase):
    def test_no_html_is_made_from_a_string_in_the_new_scripts(self):
        for name, text in (("later-reader.js", READER), ("later-cards.js", CARDS)):
            for word in NO_HTML_FROM_STRINGS:
                self.assertNotIn(word, text, (name, word))

    def test_the_readers_globals_are_asked_for_the_way_the_mobile_layer_asks(self):
        # a reader built before a0.5.0 may not have one of them: each is looked for with typeof, never assumed
        for name in ("openAnki", "needChapters", "chunkData", "textOf", "SUBS", "SRC", "press", "refitCloud",
                     "closeAnki", "sheetSeq", "cardTo", "cloudC", "penFor", "tocOpen", "autoscroll"):
            self.assertRegex(READER, r"typeof %s\b" % name, name)
        self.assertIn("'use strict'", READER)
        self.assertIn("if (window.ParsehLaterReader) return;", READER)

    def test_the_four_ways_to_flag_say_what_they_say(self):
        for words in ("review later", "✓ marked", "point at a chunk first, then press L", "marked to review later"):
            self.assertIn(words, READER)
        for words in ("point at a phrase first, then press L", "✓ marked", "review later"):
            self.assertIn(words, PLAYER)
        self.assertIn("'Review later: “'", TOUCH)
        self.assertIn("” off review later'", TOUCH)

    def test_the_held_fingers_line_is_the_last_and_asks_the_page(self):
        copy = TOUCH.index("'Copy the caption' : 'Copy the sentence'")
        later = TOUCH.index("var later = window.ParsehLaterMark;")
        self.assertLess(copy, later, "after the two copies, so that their places do not move")
        self.assertIn("later.can(at.unit)", TOUCH)
        for page, text in (("reader", READER), ("player", PLAYER)):
            self.assertIn("window.ParsehLaterMark = {", text, page)

    def test_the_l_key_is_heard_first_and_not_in_a_field_with_a_sheet_open_or_with_a_modifier(self):
        for text in (READER, PLAYER):
            self.assertRegex(text, r"e\.altKey \|\| e\.ctrlKey \|\| e\.metaKey")
            self.assertIn("defaultPrevented", text)
            self.assertIn("input, textarea, select, [contenteditable]", text)
        self.assertIn("window.addEventListener('keydown', onKey, true);", READER)
        self.assertIn("}, true);", PLAYER[PLAYER.index("var at = null;"):PLAYER.index("window.ParsehLaterMark = {")])
        for flag in ("ankiOpen", "chOpen", "fdShown", "secShown", "rgShown", "narrOpen"):
            self.assertIn("typeof %s !== 'undefined' && %s" % (flag, flag), READER)
        self.assertIn("if (ankiOpen || editing || dvOn || vmOpen || ntOn || dsheet) return;", PLAYER)

    def test_a_card_saved_is_told_by_the_sheets_own_doors(self):
        # the reader: press() and the clipboard's copy are wrapped, once; the sheet's hidden is watched
        self.assertIn("window.press = wrapped;", READER)
        self.assertIn("K.copy = copied;", READER)
        self.assertIn("attributeFilter: ['hidden']", READER)
        self.assertIn("target !== 'md' || lastCopy === true", READER)
        # the player: its own press, copyMarkdown and closeAnki say so
        self.assertIn("laterPressDone(seq, target, ok);", PLAYER)
        self.assertIn("laterCopied = ok === true;", PLAYER)
        self.assertEqual(PLAYER.count("laterSheetShut();"), 1)
        self.assertIn("target !== 'md' || laterCopied", PLAYER)

    def test_the_player_draws_its_marks_after_every_way_the_transcript_is_drawn(self):
        self.assertEqual(PLAYER.count("    pnPaint();\n    laterPaint();\n  }"), 2, "render() and redrawSeg(), both ending the same way")
        self.assertEqual(PLAYER.count("laterButton(ch) + '</div>'"), 1, "the cloud's row, once")
        self.assertIn("class=\"mklater", PLAYER)
        self.assertIn("if (t.classList.contains('mklater')) { laterToggle(cloudCtx.sg, cloudCtx.ch); return; }", PLAYER)

    def test_the_queue_takes_a_flag_off_without_the_removed_line(self):
        self.assertIn("ParsehLater.remove(rec.id, {toast: false});", CARDS)
        self.assertIn("window.ParsehLaterCards = {one: one, queue: queue", CARDS)
        for words in ("item ", " of ", "'Skip'", "'Stop'"):
            self.assertIn(words, CARDS)


class Styles(unittest.TestCase):
    def test_the_dotted_line_is_a_thick_dotted_accent_line_that_the_pages_other_underlines_do_not_beat(self):
        rule = LATERCSS[LATERCSS.index(".later-mark{"):]
        rule = rule[:rule.index("}")]
        self.assertIn("underline dotted var(--accent,#be3455) 2px!important", rule)
        self.assertIn("text-decoration-skip-ink:none!important", rule)

    def test_the_door_is_not_beaten_by_hidden_and_the_phones_line_names_it(self):
        self.assertIn(".later-btn[hidden]{display:none!important}", LATERCSS)
        # the reader's and the player's first lines on a phone: let through, ordered, and told how to fit
        self.assertIn(".px-ask,\n  .later-btn,.kp-off", MOBILE)
        self.assertIn("#theme,#typo,.px-ask,.later-btn,.kp-btn", MOBILE)
        self.assertIn("html.m-reader[data-mode=mobile] header button.later-btn{order:8;", MOBILE)
        self.assertIn("html.m-player[data-mode=mobile] header button.later-btn{order:5;", MOBILE)
        self.assertIn("@media (min-width:360px) and (max-width:399px){", MOBILE)
        self.assertIn("header button.later-btn{order:12;flex:1 1 100%}", MOBILE)

    def test_the_players_door_is_compact_where_its_header_has_no_room(self):
        # at 1280px the full «⚑ later» sent the gear to a second row (measured: 45px -> 80px); the word comes back from 1480px
        self.assertIn("@media (max-width:1479px){\n  header .later-btn .lb-word{display:none}\n}", PLAYERCSS)

    def test_no_text_of_the_new_controls_is_drawn_in_the_accent(self):
        # the accent is 4.4:1 on the sepia paper: it colours a line and a border, never a word
        body = LATERCSS[LATERCSS.index("ON THE PAGE ITSELF"):]
        for rule in re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", body, flags=re.S)):
            self.assertNotRegex(rule[1], r"(^|;)\s*color:\s*var\(--accent", rule[0].strip())
        self.assertIn("#cloud .mkrow .mklater.on{color:var(--ink);", PLAYERCSS)

    def test_the_fixed_boxes_use_no_viewport_units(self):
        body = re.sub(r"/\*.*?\*/", "", LATERCSS[LATERCSS.index("ON THE PAGE ITSELF"):], flags=re.S)
        self.assertIsNone(re.search(r"\d\s*(vw|vh|dvh|svh|lvh|vmin|vmax)\b", body))


if __name__ == "__main__":
    unittest.main()
