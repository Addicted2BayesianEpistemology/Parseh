# SPDX-License-Identifier: GPL-3.0-or-later
"""Review later: the chunks a person flagged while reading or watching (a0.5.0).

    python3 -m unittest tests/test_later.py

The store (lib/later.py), the door (/__later in serve.py), the hub's door and
the page /later/ (lib/laterpage.py), and the files that carry them to a phone.
What the browser does with all of it -- the sidebar, the sheet, the page, two
devices, a phone with the computer away -- is driven by tests/review_later_core.mjs.

  * THE STORE: add, remove, revive, the tombstone and its 90 days, the cap of
    5000, every field clamped, every refusal in words and nothing applied,
    two devices' changes merged by the newest, a file that keeps what it does
    not know -- and, THREADED, the old fault: prefs and later writing at once
    (lib/prefs.py wrote through ONE temporary name and no lock; the same
    stress, run on that code, loses writes).
  * THE DOOR through the real server, on a temporary tree: GET ?ref=, ?counts=1,
    ?all=1 (&tomb=1), POST {by, ops}, a bad body answered 400 in words, another
    site refused, /__prefs not carrying the flags.
  * THE HUB'S DOOR in both layouts, its count and its language chips; THE PAGE in both
    layouts; the files in the phone's shell, the worker's refusal, the registry.
  * THE CLIENT's source: no HTML made from a string, no viewport units in a fixed box.

Nothing here writes the checkout's config/ (tests/configguard.py): prefs.STORE
points into a temporary folder for as long as the module runs.
"""
import http.client
import json
import os
import re
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in ("markdown/exlex", "markdown/app", "lib", "youtube/lib", "."):
    sys.path.insert(0, str(ROOT / p))
import later                                                   # noqa: E402
import prefs                                                   # noqa: E402

BOOK = "/books/english/mini-en/reader/"
OTHER = "/books/persian/mini-fa/reader/"
VIDEO = "street-market-a1b2c3"

# THE PHONE-KEEPING MEMORIES GO TO A FOLDER OF THIS FILE'S OWN, as tests/test_mobile_pages.py
# sends them: asking lib/offline.py what the app is made of (the phone's shell, below) writes
# the checksums of the files it hashed into `offline.DIGESTS` -- config/digests.json beside the
# checkout, which is the owner's.  tests/test_config_untouched.py caught this module doing it.
_scratch = None
_patches = []


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


def book_id(ref=BOOK, sub="1.1-1ac09deff425", k=0, h="abc"):
    return "later:book:%s:%s:%d:%s" % (ref, sub, k, h)


def book(n=0, at=None, ref=BOOK, text=None, lang="en", **extra):
    """A flag as lib/later.js makes one."""
    rec = {"id": book_id(ref, "1.%d-1ac09deff425" % n, n, "h%d" % n), "kind": "book", "ref": ref,
           "lang": lang, "glossLang": "fa", "title": "Mini", "at": time.time() if at is None else at,
           "by": "Linux computer · Chrome",
           "where": {"sub": "1.%d-1ac09deff425" % n, "k": n, "para": "1:%d" % n, "label": "1.%d" % n,
                     "chapter": "Chapter 1", "t": None},
           "text": text or "wound the clock %d" % n, "kana": "", "tr": "", "en": "bound the watch",
           "voc": "", "sentence": "He wound the clock."}
    rec.update(extra)
    return rec


def video(j=0, start=2.0, at=None):
    return {"id": "later:video:%s:%s:%d:h%d" % (VIDEO, start, j, j), "kind": "video", "ref": VIDEO,
            "lang": "en", "glossLang": "fa", "title": "Street market",
            "at": time.time() if at is None else at, "by": "Android phone · Chrome",
            "where": {"start": start, "j": j, "text": "The market opens early."},
            "text": "opens early", "kana": "", "tr": "", "en": "opens early", "voc": "", "sentence": ""}


def slurp(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def add(rec):
    return {"op": "add", "record": rec}


def remove(rec, at=None):
    return {"op": "remove", "id": rec["id"], "at": time.time() if at is None else at}


class Scratch(unittest.TestCase):
    """prefs.STORE in a folder of this test's own."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.store = os.path.join(self._td.name, "config", "prefs.json")
        p = patch.object(prefs, "STORE", self.store)
        p.start()
        self.addCleanup(p.stop)

    def file(self):
        with open(self.store, encoding="utf-8") as fh:
            return json.load(fh)

    def live(self, ref=None):
        return later.all_of(ref)


# ------------------------------------------------------------------ the store
class Store(Scratch):
    def test_a_flag_is_added_and_listed(self):
        r = book(1)
        said = later.apply_ops([add(r)], "Linux computer · Chrome")
        self.assertEqual((said["added"], said["removed"], said["live"]), (1, 0, 1))
        got = self.live()
        self.assertEqual([x["id"] for x in got], [r["id"]])
        self.assertEqual(got[0]["text"], "wound the clock 1")
        self.assertEqual(got[0]["where"]["label"], "1.1")
        # under the third top-level key, beside the other two
        doc = self.file()
        self.assertIn("items", doc["later"])
        self.assertEqual(sorted(doc["later"]["items"]), [r["id"]])

    # THE MOMENTS BELOW ARE AN HOUR OR TWO AGO, never 1970: a tombstone older
    # than 90 days is dropped by the very write that makes it (the next test
    # but one), which is the rule and not what these tests are about
    T = time.time() - 7200

    def test_a_removal_leaves_a_tombstone_and_the_flag_is_gone(self):
        T = self.T
        r = book(1, at=T + 100)
        later.apply_ops([add(r)])
        said = later.apply_ops([remove(r, at=T + 110)])
        self.assertEqual(said["removed"], 1)
        self.assertEqual(self.live(), [])
        self.assertEqual(later.counts()["total"], 0)
        tomb = self.file()["later"]["items"][r["id"]]
        self.assertEqual(tomb, {"gone": T + 110, "kind": "book", "ref": BOOK})
        # a device that syncs asks for the removals too
        got = later.all_of(tombstones=True)
        self.assertEqual(got, [{"id": r["id"], "gone": T + 110, "kind": "book", "ref": BOOK}])
        self.assertEqual(later.all_of(OTHER, tombstones=True), [])

    def test_an_add_newer_than_the_tombstone_revives_and_an_older_one_does_not(self):
        T = self.T
        r = book(1, at=T + 100)
        later.apply_ops([add(r)])
        later.apply_ops([remove(r, at=T + 110)])
        # a device that was away and still holds the flag sends it again, as old as it was
        said = later.apply_ops([add(dict(r, at=T + 105))])
        self.assertEqual((said["added"], said["ignored"]), (0, 1))
        self.assertEqual(self.live(), [])
        # as old as the removal itself: the removal wins
        said = later.apply_ops([add(dict(r, at=T + 110))])
        self.assertEqual(said["added"], 0)
        self.assertEqual(self.live(), [])
        # flagged again, after: the flag is back
        said = later.apply_ops([add(dict(r, at=T + 120))])
        self.assertEqual(said["added"], 1)
        self.assertEqual([x["at"] for x in self.live()], [T + 120])

    def test_the_last_change_to_one_flag_wins_in_either_order(self):
        T = self.T
        r = book(1)
        a, b = dict(r, at=T + 200, by="A", en="newer"), dict(r, at=T + 100, by="B", en="older")
        later.apply_ops([add(a)])
        later.apply_ops([add(b)])
        self.assertEqual((self.live()[0]["by"], self.live()[0]["en"]), ("A", "newer"))
        # a removal older than the flag is not a removal of it
        said = later.apply_ops([remove(r, at=T + 150)])
        self.assertEqual(said["removed"], 0)
        self.assertEqual(len(self.live()), 1)
        # the same add sent twice changes nothing, and does not write
        was = os.stat(self.store).st_mtime_ns
        said = later.apply_ops([add(a)])
        self.assertEqual((said["added"], said["ignored"]), (0, 1))
        self.assertEqual(os.stat(self.store).st_mtime_ns, was)

    def test_two_devices_merge_by_the_newest_change_per_flag(self):
        T = self.T
        shared, only_phone, only_computer = book(1, at=T + 100), book(2, at=T + 100), book(3, at=T + 100)
        # the phone and the computer both flagged the same chunk, away from each other
        later.apply_ops([add(dict(shared, by="phone", at=T + 101)), add(only_phone)], "phone")
        later.apply_ops([add(dict(shared, by="computer", at=T + 102)), add(only_computer)], "computer")
        got = {x["id"]: x for x in self.live()}
        self.assertEqual(len(got), 3, "one chunk flagged on two devices is ONE flag")
        self.assertEqual(got[shared["id"]]["by"], "computer")
        # the computer removes the shared one; the phone, which has not heard, flagged it earlier still
        later.apply_ops([remove(shared, at=T + 130)], "computer")
        later.apply_ops([add(dict(shared, by="phone", at=T + 101))], "phone")
        self.assertEqual(sorted(x["id"] for x in self.live()), sorted([only_phone["id"], only_computer["id"]]))
        # ... and flags it again, after
        later.apply_ops([add(dict(shared, by="phone", at=T + 140))], "phone")
        self.assertIn(shared["id"], [x["id"] for x in self.live()])

    def test_a_removal_of_a_flag_never_heard_of_is_kept_so_that_a_late_add_cannot_come_in(self):
        T = self.T
        r = book(1, at=T + 100)
        later.apply_ops([remove(r, at=T + 110)])
        self.assertEqual(self.file()["later"]["items"][r["id"]], {"gone": T + 110, "kind": "book", "ref": BOOK})
        later.apply_ops([add(r)])
        self.assertEqual(self.live(), [])

    def test_a_tombstone_is_dropped_after_90_days_by_the_next_write(self):
        old, young, kept = book(1, at=1.0), book(2, at=1.0), book(3)
        later.apply_ops([add(old), add(young), add(kept)])
        now = time.time()
        later.apply_ops([remove(old, at=now - 91 * 86400), remove(young, at=now - 89 * 86400)])
        # (the 91-day-old removal is old the moment it is written: it goes with that very write)
        items = self.file()["later"]["items"]
        self.assertNotIn(old["id"], items)
        self.assertIn(young["id"], items)
        # and the one that was young is dropped by a write after its 90th day
        doc = prefs._read()
        doc["later"]["items"][young["id"]]["gone"] = now - 91 * 86400
        prefs._write(doc)
        later.apply_ops([add(book(4))])
        self.assertNotIn(young["id"], self.file()["later"]["items"])
        self.assertEqual(later.TOMB_SECONDS, 90 * 86400)

    def test_the_live_flags_are_capped_and_the_oldest_go(self):
        self.assertEqual(later.MAX_LIVE, 5000)
        with patch.object(later, "MAX_LIVE", 12):
            for start in (0, 10):
                later.apply_ops([add(book(n, at=1000.0 + n)) for n in range(start, start + 10)])
            got = sorted(x["at"] for x in self.live())
            self.assertEqual(len(got), 12)
            self.assertEqual(got, [1000.0 + n for n in range(8, 20)])
            # an old one sent now is the oldest, and is the one to go
            later.apply_ops([add(book(99, at=1.0))])
            self.assertEqual(len(self.live()), 12)
            self.assertNotIn(book_id(h="h99", sub="1.99-1ac09deff425", k=99), [x["id"] for x in self.live()])

    def test_the_tombstones_are_capped_too(self):
        base = time.time() - 100
        with patch.object(later, "MAX_TOMBS", 5):
            later.apply_ops([remove(book(n), at=base + n) for n in range(9)])
            tombs = later.all_of(tombstones=True)
            self.assertEqual(sorted(x["gone"] for x in tombs), [base + 4 + n for n in range(5)])

    def test_every_text_is_clamped_and_every_number_is_finite(self):
        now = time.time()
        r = book(1, text="x" * 900, kana="k" * 900, tr="t" * 900, en="e" * 900, voc="v" * 1500,
                 sentence="s" * 1200, title="T" * 900, by="b" * 200, at=now + 10 ** 9)
        r["where"].update({"label": "L" * 200, "chapter": "C" * 500, "k": 10 ** 9, "t": float("inf")})
        later.apply_ops([add(r)])
        got = self.live()[0]
        for field, limit in (("text", 600), ("kana", 600), ("tr", 600), ("en", 600), ("voc", 1200),
                             ("sentence", 800), ("title", 600), ("by", 60)):
            self.assertEqual(len(got[field]), limit, field)
        self.assertEqual((len(got["where"]["label"]), len(got["where"]["chapter"])), (80, 300))
        # a clock set wrong, or a value from the future: taken as at most a minute ahead
        self.assertLessEqual(got["at"], time.time() + 61)
        self.assertEqual(got["where"]["k"], 100000)
        self.assertIsNone(got["where"]["t"], "an infinite time is no time")
        # the file is JSON a browser can read: nothing infinite in it
        json.loads(slurp(self.store), parse_constant=lambda c: self.fail(c))

    def test_text_is_squeezed_and_control_characters_go(self):
        r = book(1, text="  the \t clock\n\x00 wound  ", voc="one  line\r\n\r\ntwo\x07 lines", tr="a\nb")
        later.apply_ops([add(r)])
        got = self.live()[0]
        self.assertEqual(got["text"], "the clock wound")
        self.assertEqual(got["voc"], "one line\ntwo lines")
        self.assertEqual(got["tr"], "a b")

    def test_a_video_flag_keeps_its_caption_and_a_bad_language_is_nothing(self):
        r = video(1, start=12.5)
        r["lang"] = "not a language!"
        later.apply_ops([add(r)])
        got = self.live(VIDEO)[0]
        self.assertEqual(got["where"], {"start": 12.5, "j": 1, "text": "The market opens early."})
        self.assertEqual(got["lang"], "")

    def test_counts_say_what_there_is_per_book_and_video_and_in_each_language(self):
        later.apply_ops([add(book(1, at=100.0, title="Mini")), add(book(2, at=300.0, title="Mini")),
                         add(book(1, at=200.0, ref=OTHER, lang="fa", title="Persian one")),
                         add(video(0, at=250.0))])
        got = later.counts()
        self.assertEqual(got["total"], 4)
        self.assertEqual([(c["ref"], c["n"], c["kind"]) for c in got["counts"]],
                         [(BOOK, 2, "book"), (VIDEO, 1, "video"), (OTHER, 1, "book")])
        self.assertEqual(got["counts"][0]["at"], 300.0)
        self.assertEqual(got["counts"][2]["title"], "Persian one")
        self.assertEqual(got["counts"][2]["lang"], "fa")
        per, total = later.by_language()
        self.assertEqual((per, total), ({"en": 3, "fa": 1}, 4))
        self.assertEqual(sorted(x["ref"] for x in later.all_of(BOOK)), [BOOK, BOOK])
        # newest first
        self.assertEqual([x["at"] for x in later.all_of()], [300.0, 250.0, 200.0, 100.0])

    def test_the_file_keeps_what_it_does_not_know_and_the_flags_survive_the_other_writers(self):
        # a key an older or a newer Parseh wrote, beside the three of this one
        prefs._write({"settings": {}, "places": {}, "something_new": {"a": 1}})
        later.apply_ops([add(book(1))])
        prefs.set_settings({"bk_rate": {"v": "1.5", "at": time.time()}}, "x")
        prefs.set_place("/books/english/mini-en/reader/", 3, "1.3", 10, "x")
        doc = self.file()
        self.assertEqual(doc["something_new"], {"a": 1})
        self.assertEqual(len(doc["later"]["items"]), 1)
        self.assertEqual(doc["settings"]["bk_rate"]["v"], "1.5")
        # and the flags are not on /__prefs: they have a door of their own
        self.assertEqual(sorted(prefs.all_of()), ["places", "settings"])
        self.assertEqual(len(self.live()), 1)

    def test_what_this_parseh_cannot_read_is_left_alone_and_never_shown(self):
        prefs._write({"settings": {}, "places": {}, "later": {"items": {
            "later:book:x": {"future": "shape"}, "junk": 5,
            book_id(): dict(book(0), at="soon")}}})
        later.apply_ops([add(book(1))])
        items = self.file()["later"]["items"]
        self.assertEqual(sorted(items), sorted(["later:book:x", "junk", book_id(), book(1)["id"]]))
        self.assertEqual([x["id"] for x in self.live()], [book(1)["id"]])
        self.assertEqual(later.counts()["total"], 1)

    def test_no_format_number_is_needed_and_none_was_raised(self):
        # lib/version.py: a field added that an older reader simply ignores is not a change of format
        self.assertEqual(prefs.STORE_FORMAT, 1)
        import version
        self.assertNotIn("later", json.dumps(version.FORMATS))
        text = (ROOT / "lib" / "later.py").read_text(encoding="utf-8")
        self.assertIn("NO FORMAT NUMBER", text)


class Refusals(Scratch):
    """The whole of a request is checked before any of it is applied, and a
    refusal says, in words, which change and why."""

    def refused(self, ops, fragment, by=""):
        later.apply_ops([add(book(7))])
        before = slurp(self.store)
        with self.assertRaises(ValueError) as caught:
            later.apply_ops(ops, by)
        self.assertIn(fragment, str(caught.exception))
        self.assertEqual(slurp(self.store), before, "nothing was applied")
        return str(caught.exception)

    def test_the_body(self):
        self.refused({"op": "add"}, "list of changes")
        self.refused("add", "list of changes")
        self.refused(None, "list of changes")
        self.refused([5], "change 1: a change is an object")
        self.refused([{"op": "frobnicate"}], "'add' or 'remove'")
        self.refused([{}], "'add' or 'remove'")

    def test_too_many_changes_at_once(self):
        self.refused([remove(book(n)) for n in range(later.MAX_OPS + 1)], "1001 changes at once")

    def test_a_flag_that_cannot_be_one(self):
        good = book(1)
        self.refused([add(good), add(dict(book(2), kind="movie"))], "change 2: a flag's kind")
        self.refused([add(dict(good, ref="/etc/passwd"))], "a book's reader path")
        self.refused([add(dict(good, ref="/books/english/mini-en/reader/../../x/reader/"))], "a book's reader path")
        self.refused([add(dict(good, ref="/books/english/mini-en/"))], "a book's reader path")
        self.refused([add(dict(good, kind="video"))], "a book's reader path")
        self.refused([add(dict(good, text=""))], "chunk's text")
        self.refused([add(dict(good, text="   \n"))], "chunk's text")
        self.refused([add(dict(good, text=None))], "chunk's text")
        self.refused([add(dict(good, id="x" * 301))], "not a flag's id")
        self.refused([add(dict(good, id="book:1"))], "not a flag's id")
        self.refused([add(dict(good, id=book_id() + " space"))], "not a flag's id")
        self.refused([add(dict(good, id=book_id(ref=OTHER)))], "another place")
        self.refused([add(dict(good, id=5))], "not a flag's id")
        self.refused([add("a flag")], "a flag is an object")
        self.refused([{"op": "add"}], "a flag is an object")
        v = video(1)
        self.refused([add(dict(v, ref="../x"))], "a video's id")
        self.refused([add(dict(v, ref=BOOK))], "neither")

    def test_a_removal_that_cannot_be_one(self):
        self.refused([{"op": "remove"}], "not a flag's id")
        self.refused([{"op": "remove", "id": "later:book:nowhere:1:0:h"}], "not a flag's id")
        self.refused([{"op": "remove", "id": ["a"]}], "not a flag's id")

    def test_a_clock_that_is_not_a_number_is_now(self):
        r = book(1)
        later.apply_ops([add(dict(r, at="yesterday")), {"op": "remove", "id": book(2)["id"], "at": float("nan")}])
        self.assertLessEqual(abs(self.live()[0]["at"] - time.time()), 5)
        self.assertLessEqual(abs(self.file()["later"]["items"][book(2)["id"]]["gone"] - time.time()), 5)

    def test_the_ref_the_door_is_asked_for_is_checked_too(self):
        self.assertEqual(later.check_ref(BOOK), BOOK)
        self.assertEqual(later.check_ref(VIDEO), VIDEO)
        for bad in ("", None, 5, "/books/x", "a b", "../x", "/books/english/mini-en/reader"):
            with self.assertRaises(ValueError):
                later.check_ref(bad)


# ----------------------------------------------------------------- the threads
class Threaded(Scratch):
    """The server answers each request on a thread of its own, and a person's
    pages write together: a reader's place, a speed, a flag.  lib/prefs.py
    used to write through ONE temporary name and hold no lock, so the second
    `open` truncated what the first was about to move into place and the
    first `os.replace` failed with FileNotFoundError -- answered as a 400, and
    (tests/making.mjs measured it) 379 writes in 3000 -- and two writers that
    read the same file each wrote back without the other's change."""

    THREADS, EACH = 8, 30

    def run_threads(self, work):
        errors, gate = [], threading.Barrier(self.THREADS)

        def target(t):
            gate.wait()
            try:
                work(t)
            except Exception as e:                       # noqa: BLE001 -- what the test counts
                errors.append("%s: %s" % (type(e).__name__, e))
        threads = [threading.Thread(target=target, args=(t,)) for t in range(self.THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return errors

    def test_prefs_and_later_writing_at_once_fail_nowhere_and_lose_nothing(self):
        def work(t):
            for i in range(self.EACH):
                kind = i % 3
                if kind == 0:
                    prefs.set_settings({"bk_rate": {"v": str(i), "at": time.time()}}, "dev%d" % t)
                elif kind == 1:
                    prefs.set_place("/books/english/b%d/reader/" % t, i, "label %d" % i, 10, "dev%d" % t, time.time())
                else:
                    later.apply_ops([add(book(i + 100 * t, at=time.time() + i))], "dev%d" % t)
        self.assertEqual(self.run_threads(work), [])
        wrote = len([i for i in range(self.EACH) if i % 3 == 2])
        self.assertEqual(len(self.live()), self.THREADS * wrote, "no flag was lost to another writer")
        self.assertEqual(sorted(prefs.places()), ["/books/english/b%d/reader/" % t for t in range(self.THREADS)])
        self.assertIn("bk_rate", prefs.settings())
        # and nothing was left behind beside the file
        self.assertEqual(sorted(os.listdir(os.path.dirname(self.store))), ["prefs.json"])

    def test_writes_of_the_whole_file_alone_do_not_collide(self):
        def work(t):
            for i in range(60):
                prefs._write({"settings": {"k%d" % t: {"v": str(i), "at": 1.0, "by": ""}}, "places": {}})
        self.assertEqual(self.run_threads(work), [])
        self.assertEqual(sorted(os.listdir(os.path.dirname(self.store))), ["prefs.json"])
        json.loads(slurp(self.store))

    def test_the_lock_is_one_and_shared(self):
        self.assertIs(later.prefs.LOCK, prefs.LOCK)
        with prefs.LOCK:
            with prefs.LOCK:                            # an RLock: a function holding it may call another
                pass


# ----------------------------------------------------------------- the server
class Served(unittest.TestCase):
    """serve.py's own Handler on a free port, its stores in a temporary tree."""

    @classmethod
    def setUpClass(cls):
        import serve
        import network
        import offline
        cls.serve, cls.network = serve, network
        cls._td = tempfile.TemporaryDirectory()
        tmp = Path(cls._td.name)
        cls.tmp = tmp
        cls.patches = [
            patch.object(serve.Handler, "log_request", lambda *a, **k: None),
            patch.object(network, "STORE", str(tmp / "config" / "network.json")),
            patch.object(prefs, "STORE", str(tmp / "config" / "prefs.json")),
            patch.object(offline, "DIGESTS", str(tmp / "config" / "digests.json")),
            patch.object(offline, "WHERES", str(tmp / "config" / "wheres.json")),
        ]
        for p in cls.patches:
            p.start()
        network._CACHE.update({"key": None, "doc": None})
        cls.srv = serve.Server(("127.0.0.1", 0), serve.Handler, None)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in reversed(cls.patches):
            p.stop()
        cls.network._CACHE.update({"key": None, "doc": None})
        cls._td.cleanup()

    def setUp(self):
        # every test begins with no flags
        if os.path.exists(prefs.STORE):
            os.unlink(prefs.STORE)

    def ask(self, method, path, body=None, headers=None, raw=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        h = {"Content-Type": "application/json"}
        h.update(headers or {})
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode("utf-8"))
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        text = r.read().decode("utf-8", "replace")
        c.close()
        try:
            return r.status, json.loads(text)
        except ValueError:
            return r.status, text

    def post(self, ops, by="Linux computer · Chrome", **kw):
        return self.ask("POST", "/__later", {"by": by, "ops": ops}, **kw)

    def test_a_flag_goes_in_by_the_door_and_comes_out_by_every_way_of_asking(self):
        a, b, v = book(1), book(2), video(0)
        status, got = self.post([add(a), add(b), add(v)])
        self.assertEqual((status, got["ok"], got["added"], got["live"]), (200, True, 3, 3))
        status, got = self.ask("GET", "/__later?ref=" + BOOK.replace("/", "%2F"))
        self.assertEqual(status, 200)
        self.assertTrue(got["ok"])
        self.assertEqual(got["ref"], BOOK)
        self.assertEqual(sorted(x["id"] for x in got["items"]), sorted([a["id"], b["id"]]))
        self.assertAlmostEqual(got["now"], time.time(), delta=5)
        status, got = self.ask("GET", "/__later?ref=" + VIDEO)
        self.assertEqual([x["id"] for x in got["items"]], [v["id"]])
        status, got = self.ask("GET", "/__later?counts=1")
        self.assertEqual(got["total"], 3)
        self.assertEqual({c["ref"]: c["n"] for c in got["counts"]}, {BOOK: 2, VIDEO: 1})
        status, got = self.ask("GET", "/__later?all=1")
        self.assertEqual(len(got["items"]), 3)

    def test_a_removal_is_told_only_to_the_one_who_asks_for_it(self):
        t = time.time() - 600
        a = book(1, at=t)
        self.post([add(a)])
        self.post([remove(a, at=t + 10)])
        _s, got = self.ask("GET", "/__later?all=1")
        self.assertEqual(got["items"], [])
        _s, got = self.ask("GET", "/__later?all=1&tomb=1")
        self.assertEqual(got["items"], [{"id": a["id"], "gone": t + 10, "kind": "book", "ref": BOOK}])
        _s, got = self.ask("GET", "/__later?ref=%s&tomb=1" % BOOK.replace("/", "%2F"))
        self.assertEqual([x["id"] for x in got["items"]], [a["id"]])
        _s, got = self.ask("GET", "/__later?ref=%s&tomb=1" % OTHER.replace("/", "%2F"))
        self.assertEqual(got["items"], [])
        # a stale device sends the flag again, as old as it was: it does not come back
        _s, got = self.post([add(a)])
        self.assertEqual((got["added"], got["live"]), (0, 0))

    def test_the_flags_are_not_on_prefs(self):
        self.post([add(book(1))])
        _s, got = self.ask("GET", "/__prefs")
        self.assertEqual(sorted(got), ["ok", "places", "settings"])

    def test_a_bad_request_is_a_400_in_words_and_changes_nothing(self):
        self.post([add(book(1))])
        before = slurp(prefs.STORE)
        for ops, words in (("add", "list of changes"), ([{"op": "x"}], "'add' or 'remove'"),
                           ([add(dict(book(1), ref="/etc/passwd"))], "a book's reader path"),
                           ([add(dict(book(1), text=""))], "chunk's text")):
            status, got = self.post(ops)
            self.assertEqual(status, 400, ops)
            self.assertFalse(got["ok"])
            self.assertIn(words, got["error"])
        status, got = self.ask("POST", "/__later", {"by": "x"})
        self.assertEqual((status, got["ok"]), (400, False))
        self.assertIn("list of changes", got["error"])
        # a body that is not an object, and one that is not JSON at all
        status, got = self.ask("POST", "/__later", raw=b"[1, 2]")
        self.assertEqual((status, got["ok"]), (400, False))
        status, got = self.ask("POST", "/__later", raw=b"not json")
        self.assertEqual((status, got["ok"]), (400, False))
        self.assertIn("JSON", got["error"])
        self.assertEqual(slurp(prefs.STORE), before)

    def test_a_question_that_names_nothing_is_a_400_too(self):
        status, got = self.ask("GET", "/__later")
        self.assertEqual((status, got["ok"]), (400, False))
        self.assertIn("?ref=", got["error"])
        self.assertIn("?counts=1", got["error"])
        for q in ("?ref=../x", "?ref=%2Fetc%2Fpasswd", "?ref=a%20b"):
            status, got = self.ask("GET", "/__later" + q)
            self.assertEqual(status, 400, q)
            self.assertIn("book's reader path", got["error"])

    def test_the_door_answers_get_and_post_only(self):
        for verb in ("PUT", "PATCH", "DELETE"):
            status, _got = self.ask(verb, "/__later", {})
            self.assertEqual(status, 405, verb)

    def test_a_disk_that_will_not_write_is_a_500_not_a_400(self):
        # a page that took a full disk for a bad body would throw away what it holds
        with patch.object(later, "apply_ops", side_effect=OSError("no space left")):
            status, got = self.post([add(book(1))])
        self.assertEqual(status, 500)
        self.assertIn("no space left", got["error"])

    def test_another_site_cannot_flag_anything(self):
        for h in ({"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.example"},
                  {"Origin": "https://evil.example"}):
            status, got = self.post([add(book(1))], headers=h)
            self.assertEqual(status, 403)
            self.assertIn("only Parseh's own pages may change anything", got["error"])
        status, got = self.post([add(book(1))], headers={"Sec-Fetch-Site": "same-origin",
                                                         "Origin": "http://127.0.0.1:%d" % self.port})
        self.assertEqual(status, 200)

    def test_a_device_not_let_in_is_refused_like_any_other_door(self):
        # the gate is the toolbox's one gate (lib/network.py): /__later is no exception
        with patch.object(self.network, "needs_code", lambda *a, **k: True), \
                patch.object(self.network, "let_in", lambda *a, **k: False):
            status, got = self.post([add(book(1))])
            self.assertEqual(status, 403)
            self.assertIn("has not been let in", got["error"])
            status, _got = self.ask("GET", "/__later?counts=1")
            self.assertEqual(status, 403)
        self.assertEqual(later.counts()["total"], 0)

    # ---- the hub's door
    def hub(self):
        status, html = self.ask("GET", "/")
        self.assertEqual(status, 200)
        return html

    def test_the_hub_has_the_door_in_both_layouts_and_says_nothing_marked_yet(self):
        html = self.hub()
        browser = html[html.index('class="hub-browser"'):html.index('class="hub-mobile"')]
        mobile = html[html.index('class="hub-mobile"'):]
        self.assertEqual(browser.count('href="/later/"'), 1)
        self.assertEqual(mobile.count('href="/later/"'), 1)
        self.assertIn('<a class="door wide" href="/later/">', browser)
        self.assertIn('<a class="m-door" href="/later/">', mobile)
        self.assertIn("Review later", browser)
        self.assertIn("Review later", mobile)
        for part in (browser, mobile):
            m = re.search(r'<span class="tag[^"]*" data-count-kind="later" data-counts="([^"]*)">([^<]*)</span>', part)
            self.assertIsNotNone(m)
            self.assertEqual(m.group(2), "nothing marked yet")
            self.assertEqual(json.loads(m.group(1).replace("&quot;", '"'))["all"], "nothing marked yet")
        # after the first mobile door and before the guide, so the doors of the browser's four keep their grid
        self.assertLess(mobile.index('href="/exercises/"'), mobile.index('href="/later/"'))
        self.assertLess(mobile.index('href="/later/"'), mobile.index('href="/guide/"'))

    def test_the_door_counts_the_flags_and_each_language_chip_counts_its_own(self):
        self.post([add(book(1)), add(book(2)), add(book(1, ref=OTHER, lang="fa")), add(video(0))])
        html = self.hub()
        tags = re.findall(r'<span class="(tag[^"]*)" data-count-kind="later" data-counts="([^"]*)">([^<]*)</span>', html)
        self.assertEqual(len(tags), 2, "one in each layout")
        for cls, counts, said in tags:
            self.assertIn("on", cls.split())
            self.assertEqual(said, "4 chunks")
            per = json.loads(counts.replace("&quot;", '"'))
            self.assertEqual((per["all"], per["en"], per["fa"], per["it"]), ("4 chunks", "3 chunks", "1 chunk", "nothing marked yet"))
        self.post([remove(book(1)), remove(book(2)), remove(book(1, ref=OTHER, lang="fa"))])
        self.assertIn(">1 chunk</span>", self.hub())

    # ---- the page
    def test_the_page_carries_both_layouts_and_loads_what_draws_it(self):
        status, html = self.ask("GET", "/later/")
        self.assertEqual(status, 200)
        self.assertIn("<title>Review later", html)
        self.assertIn('data-layout="browser"', html)
        self.assertIn('data-layout="mobile"', html)
        self.assertEqual(html.count('data-parseh-mode="browser"'), 2, "the switch is in both bars")
        self.assertEqual(html.count('data-parseh-mode="mobile"'), 2)
        self.assertEqual(html.count("data-parseh-theme"), 2)
        self.assertIn("data-mobile-page", html)
        self.assertIn('<div class="parseh-bar" data-layout="browser">', html)
        self.assertIn('<div class="parseh-bar m-bar" data-layout="mobile">', html)
        self.assertIn('<span class="m-where">Review later</span>', html)
        self.assertLess(html.index("/lib/parseh.css"), html.index("/lib/mobile.css"))
        self.assertLess(html.index("/lib/mobile.css"), html.index("/lib/later.css"))
        self.assertLess(html.index("/lib/later.css"), html.index("/lib/parseh.js"))
        self.assertIn('<script src="/lib/later.js" defer></script>', html)
        self.assertIn('id="lp-root"', html)
        self.assertIn("data-later-page", html)
        # the registry's names and directions, for the heads of the groups
        langs = json.loads(re.search(r'data-langs="([^"]*)"', html).group(1).replace("&quot;", '"'))
        self.assertEqual((langs["fa"]["name"], langs["fa"]["dir"]), ("Persian", "rtl"))
        self.assertEqual(langs["en"]["dir"], "ltr")
        self.assertEqual(langs["ar"]["dir"], "rtl")
        # nothing in it edits anything
        for word in ("<input", "<textarea", "<form", "data-del", "stop the server"):
            self.assertNotIn(word, html)

    def test_the_page_has_one_address(self):
        for path in ("/later", "/later/index.html"):
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
            c.request("GET", path)
            r = c.getresponse()
            r.read()
            c.close()
            self.assertEqual((r.status, r.getheader("Location")), (302, "/later/"), path)
        status, _got = self.ask("POST", "/later/", {})
        self.assertEqual(status, 405)

    def test_the_script_and_the_sheet_are_served(self):
        for path, kind in (("/lib/later.js", "javascript"), ("/lib/later.css", "css")):
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
            c.request("GET", path)
            r = c.getresponse()
            body = r.read()
            c.close()
            self.assertEqual(r.status, 200, path)
            self.assertIn(kind, r.getheader("Content-Type"), path)
            self.assertEqual(body, (ROOT / path.lstrip("/")).read_bytes())


# ------------------------------------------------------- the phone and its files
class Phone(unittest.TestCase):
    def test_the_worker_refuses_the_door_at_once_when_the_computer_is_away(self):
        sw = (ROOT / "lib" / "sw.js").read_text(encoding="utf-8")
        block = sw[sw.index("const NEEDS_COMPUTER = ["):]
        block = block[:block.index("];")]
        self.assertIn(r"/\/__later$/", block)
        self.assertIn(r"/\/__prefs$/", block)

    def test_the_files_and_the_page_are_in_the_phones_shell(self):
        import offline
        for url in ("/lib/later.js", "/lib/later.css"):
            self.assertIn(url, offline.SHARED)
            self.assertTrue((ROOT / url.lstrip("/")).is_file(), url)
        self.assertIn("/later/", offline.SHELL_PAGES)
        rec = offline.shell()
        self.assertIn("/later/", rec["pages"])
        self.assertIn("/lib/later.js", rec["files"])
        self.assertIn("/lib/later.css", rec["files"])

    def test_the_page_is_a_page_with_a_mobile_version(self):
        js = (ROOT / "lib" / "parseh.js").read_text(encoding="utf-8")
        block = js[js.index("var MOBILE_PAGES = ["):]
        block = block[:block.index("];")]
        self.assertIn("{ match: /^\\/later\\/$/, to: '/later/' }", block)

    def test_both_files_are_static_files_the_server_hands_out(self):
        serve_text = (ROOT / "serve.py").read_text(encoding="utf-8")
        self.assertIn('"/lib/later.js", "/lib/later.css"', serve_text)


# --------------------------------------------------------------- the client's source
class Source(unittest.TestCase):
    JS = (ROOT / "lib" / "later.js").read_text(encoding="utf-8")
    CSS = (ROOT / "lib" / "later.css").read_text(encoding="utf-8")

    def test_no_html_is_made_from_a_string(self):
        for word in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "createContextualFragment", "srcdoc"):
            self.assertNotIn(word, self.JS, word)

    def test_a_box_fixed_to_the_screen_is_not_sized_in_the_screens_units(self):
        # lib/pagezoom.js scales the page: percentages and a variable, never vw, vh or dvh
        for text, name in ((self.JS, "later.js"), (self.CSS, "later.css")):
            body = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            self.assertIsNone(re.search(r"\d\s*(vw|vh|dvh|svh|lvh|vmin|vmax)\b", body), name)
        self.assertIn("top:var(--later-top,var(--headh,0px))", self.CSS)
        self.assertIn("width:min(420px,100%)", self.CSS)
        self.assertIn("max-height:86%", self.CSS)

    def test_the_flags_are_in_no_book_and_no_bundle(self):
        # the person's own: a book handed on carries the edition, not somebody's flags
        for name in ("lib/bundle.py", "lib/shelf.py"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for word in ("prefs", "later.py", "/__later"):
                self.assertNotIn(word, text, (name, word))
        py = (ROOT / "lib" / "later.py").read_text(encoding="utf-8")
        self.assertNotIn("books", re.sub(r'""".*?"""', "", py, flags=re.S).replace("/books/", "").replace("BOOK_REF", ""),
                         "the store never opens a book's folder")

    def test_the_api_is_all_there(self):
        tail = self.JS[self.JS.index("window.ParsehLater = {"):]
        for name in ("ready", "sync", "has", "get", "list", "count", "add", "remove", "toggle", "undo", "on",
                     "pending", "idFor", "record", "href", "fromHash", "refOf", "panel", "page", "device"):
            self.assertRegex(tail, r"\b%s:" % name)
        head = self.JS[:self.JS.index("(function () {")]
        for name in ("canCard()", "locate(record)", "goTo(record)", "makeCard?(record)", "queue?(records)", "label?(record)"):
            self.assertIn(name, head)

    def test_the_shapes_are_the_ones_the_computer_checks(self):
        # the same segment pattern, and the same limits, on both sides
        py = (ROOT / "lib" / "later.py").read_text(encoding="utf-8")
        for shape in ("[A-Za-z0-9][A-Za-z0-9._-]{0,80}", "[A-Za-z0-9][A-Za-z0-9._-]{0,120}",
                      "[A-Za-z0-9_.:/@%+=~-]*"):
            self.assertIn(shape, self.JS)
        self.assertIn("[A-Za-z0-9][A-Za-z0-9._-]{0,80}", py)
        self.assertIn("[A-Za-z0-9][A-Za-z0-9._-]{0,120}", py)
        self.assertIn("[A-Za-z0-9_.:/@%%+=~-]*", py)
        self.assertIn("{id: 300, text: 600, other: 600, voc: 1200, sentence: 800, by: 60, label: 80,", self.JS)
        self.assertEqual(later.LIMIT, {"id": 300, "text": 600, "other": 600, "voc": 1200, "sentence": 800,
                                       "by": 60, "label": 80, "chapter": 300, "sub": 200, "para": 40})


if __name__ == "__main__":
    unittest.main()
