# SPDX-License-Identifier: GPL-3.0-or-later
"""The friendly numbers of Settings -> About (lib/aboutstats.py), and the page that shows them.

    python3 -m unittest tests/test_about_stats.py

They are read off what is already kept -- a deck's answers, a video's length and
day, a book's book.json -- so each test builds a small tree in a temporary folder
and counts it.  A dot folder (.trash) is never counted.
"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "lib", "youtube/lib", "."):
    sys.path.insert(0, str(ROOT / p))
import aboutstats                                              # noqa: E402


def put(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")


def shelf(root):
    """Three books (one of the old layout; a fourth in the trash), two videos (a third broken; one in the
    trash), two decks (a third in the trash) with three answers between them."""
    for where in ("books/persian/one", "books/persian/two", "books/oldbook", "books/.trash/persian/gone"):
        put(root / where / "book.json", {"title": where})
    put(root / "youtube/videos/persian/v1/video.json", {"duration": "0:35", "added": "2026-09-05"})
    put(root / "youtube/videos/italian/v2/video.json", {"duration": "75:20", "added": "2026-08-30"})
    put(root / "youtube/videos/italian/v3/video.json", "{ not json")
    put(root / "youtube/videos/.trash/italian/v4/video.json", {"duration": "9:00", "added": "2020-01-01"})
    put(root / "exercises/persian/d1/deck.json", {"created": "2026-09-01T10:00:00+02:00"})
    put(root / "exercises/persian/d1/items/aaaaaaaaaaaa.json", {})
    put(root / "exercises/persian/d1/items/bbbbbbbbbbbb.json", {})
    put(root / "exercises/persian/d1/schedule/aaaaaaaaaaaa.json",
        {"state": {}, "history": [{"at": "2026-09-02T08:00:00+02:00"}, {"at": "2026-09-03T08:00:00+02:00"}]})
    put(root / "exercises/persian/d1/schedule/bbbbbbbbbbbb.json", {"state": {}, "history": [{"at": "2026-09-04T08:00:00+02:00"}]})
    put(root / "exercises/italian/d2/deck.json", {"created": "2026-09-10T10:00:00+02:00"})   # no items, no schedule
    put(root / "exercises/.trash/persian--old--1/deck.json", {"created": "2019-01-01"})


class Counting(unittest.TestCase):
    def test_a_shelf_is_counted_and_a_trash_is_not(self):
        with tempfile.TemporaryDirectory() as td:
            shelf(Path(td))
            got = aboutstats.collect(td)
        self.assertEqual((got["books"], got["videos"], got["decks"], got["exercises"], got["answers"]), (3, 2, 2, 2, 3), got)
        self.assertEqual(got["video_seconds"], 35 + 75 * 60 + 20)
        self.assertEqual(got["folders"], ["italian", "persian"])
        self.assertEqual(got["since"], "2026-08-30", "the earliest day anything says (the broken and trashed ones say none)")
        self.assertTrue(got["complete"])

    def test_nothing_on_the_shelf(self):
        with tempfile.TemporaryDirectory() as td:
            got = aboutstats.collect(td)
        self.assertEqual((got["books"], got["videos"], got["decks"], got["answers"], got["since"]), (0, 0, 0, 0, None))

    def test_a_shelf_too_big_to_read_in_time_says_so(self):
        with tempfile.TemporaryDirectory() as td:
            shelf(Path(td))
            ticks = iter([0.0])
            got = aboutstats.collect(td, budget=0.5, clock=lambda: next(ticks, 10.0))
        self.assertFalse(got["complete"])
        self.assertTrue(aboutstats.tiles(got)[0][0].startswith("at least "), "and the numbers that may be short say 'at least'")

    def test_lengths(self):
        for text, want in (("0:35", 35), ("75:20", 4520), ("1:02:03", 3723), ("42", 42), ("", 0), ("x", 0),
                           ("1:2:3:4", 0), ("-1:00", 0), (None, 0)):
            self.assertEqual(aboutstats.seconds(text), want, text)


class Words(unittest.TestCase):
    def test_spans_are_about_not_exact(self):
        self.assertEqual(aboutstats.span(0.005), "less than a minute")
        self.assertEqual(aboutstats.span(0.5), "about 30 minutes")
        self.assertEqual(aboutstats.span(1), "about 1 hour")
        self.assertEqual(aboutstats.span(2.26), "about 2.5 hours")
        self.assertEqual(aboutstats.span(26.4), "about 26 hours")

    def test_the_tiles(self):
        s = {"answers": 1240, "videos": 37, "video_seconds": 9 * 3600 + 1800, "books": 5, "decks": 12, "exercises": 340,
             "folders": ["italian", "persian"], "since": "2026-09-03", "complete": True}
        t = aboutstats.tiles(s, {"italian": "Italian", "persian": "Persian"})
        self.assertEqual([x[0] for x in t], ["1,240", "37", "5", "12"])
        self.assertEqual([x[1] for x in t], ["cards answered", "videos on the shelf", "books on the shelf", "decks of exercises"])
        self.assertIn("23 packs of playing cards", t[0][2])
        self.assertIn("About 9.5 hours", t[1][2])
        self.assertIn("roughly 6 films", t[1][2])
        self.assertEqual(t[2][2], "In 2 languages.")
        self.assertEqual(t[3][2], "Holding 340 exercises.")

    def test_one_of_each_and_none_at_all(self):
        s = {"answers": 1, "videos": 1, "video_seconds": 0, "books": 1, "decks": 1, "exercises": 1,
             "folders": ["persian"], "since": None, "complete": True}
        t = aboutstats.tiles(s)
        self.assertEqual([x[1] for x in t], ["card answered", "video on the shelf", "book on the shelf", "deck of exercises"])
        self.assertEqual(t[0][2], "A good start.")
        zero = aboutstats.tiles({"answers": 0, "videos": 0, "video_seconds": 0, "books": 0, "decks": 0, "exercises": 0,
                                 "folders": [], "since": None, "complete": True})
        self.assertEqual([x[2] for x in zero], ["None yet: the first is waiting in a deck.", "Add one from Videos.",
                                                "Make one from Books.", "Make one in the studio."])

    def test_the_day_it_began(self):
        s = {"since": "2026-09-03"}
        self.assertEqual(aboutstats.since_line(s, date(2026, 10, 5)), "Parseh has been with you since 3 September 2026 (32 days).")
        self.assertEqual(aboutstats.since_line(s, date(2026, 9, 4)), "Parseh has been with you since 3 September 2026 (1 day).")
        self.assertEqual(aboutstats.since_line(s, date(2026, 9, 3)), "Your first day with Parseh is today.")
        self.assertEqual(aboutstats.since_line(s, date(2026, 9, 1)), "", "a day in the future is not said")
        self.assertEqual(aboutstats.since_line({"since": None}), "")


class ThePage(unittest.TestCase):
    def test_it_shows_them_and_ends_in_a_foot_like_every_other_door(self):
        import aboutpage
        import settingspage
        with tempfile.TemporaryDirectory() as td:
            shelf(Path(td))
            aboutpage._KEPT.clear()
            with patch.object(settingspage, "ROOT", td):
                html = aboutpage.page("")
            aboutpage._KEPT.clear()
        self.assertIn("Your time with Parseh", html)
        self.assertIn("<b>3</b><span>cards answered</span>", html)
        self.assertIn("<b>2</b><span>videos on the shelf</span>", html)
        self.assertIn("Parseh has been with you since 30 August 2026", html)
        self.assertIn("not the time spent watching them", html, "the hours are said to be the videos' lengths")
        self.assertIn('class="foot"', html)
        self.assertNotIn("footer-links", html, "the foot is the one the other doors have, with its links spaced")
        self.assertIn('<a href="/guide/">User guide</a> &middot; <a href="/licences/">Licences</a>', html)
        self.assertIn('settings</a> &middot; about', html)

    def test_it_keeps_the_count_for_a_minute(self):
        import aboutpage
        with tempfile.TemporaryDirectory() as td:
            shelf(Path(td))
            aboutpage._KEPT.clear()
            first = aboutpage.stats(td)
            put(Path(td) / "books/persian/three/book.json", {})
            self.assertIs(aboutpage.stats(td), first, "counting reads every deck: not on every look")
            aboutpage._KEPT.clear()
            self.assertEqual(aboutpage.stats(td)["books"], first["books"] + 1)
            aboutpage._KEPT.clear()


if __name__ == "__main__":
    unittest.main()
