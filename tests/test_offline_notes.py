#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""THE NOTES TRAVEL WITH THEIR BOOK OR THEIR VIDEO, as addresses.

    python3 -m unittest discover -s tests -p test_offline_notes.py

The owner, 2026-09-23: *"the keep button in books and videos should also keep
the notes rendered in bare page way"*.  Until that day `lib/offline.py` never
walked a `markdown/` folder, so a kept book kept its text and its recordings
and left every note he had written on the computer: every seam on a train
opened on nothing.  What was decided then is in `TO-DO.md` §0, second block,
and this file is that list of decisions read back to the code, one test to a
decision:

1. one tick, beside the recordings;
2. the marks travel, and they are a DOOR;
3. a note that holds an exercise keeps its full studio page, and the studio's
   scripts are paid once for the phone;
4. all thirteen of the studio's faces travel, once, in the shared list;
5. MathJax only where a note has a formula;
6. a note's pictures come with the notes, its recordings are one row of their
   own beside the narrations;
7. a note written, edited or deleted moves the thing's version;
8. what the computer no longer has can be found and given back;
9. books and videos together.

And one from the block after it (2026-09-23, his 3): a tick must be testable.
A note's page is RENDERED as it is sent, so its size in this record is an
honest guess at what it will cost and never the answer's own byte count -- it
must therefore promise nothing but its own presence, or the check that now
ticks the boxes would call every kept note broken.  Its pictures and its
recordings are files, and carry real digests.  That is the last class here.

DRIVEN, NEVER RESTATED.  Every test here builds a real book or a real video
with real notes written through the studio's own store, asks the door what it
is made of (`serve.notes_to_keep`, which is what the two `__offline` routes
call) and reads the record `lib/offline.py` answers with.  Where a number is
claimed -- what a picture adds, what a note weighs -- it is measured by
building the same thing twice and subtracting, rather than by working the
answer out the way the code does and agreeing with itself.

WHY A BOOK IS BUILT BY HAND HERE rather than copied out of `tests/fixtures`.
The record is made of addresses and file sizes, and a fixture edition brings
a hundred files that have nothing to do with the question; four files and a
directory are the whole of what `offline.book` looks at, and a test that says
so is a test somebody can read.
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "lib", ROOT / "youtube" / "lib",
               ROOT / "markdown" / "app", ROOT / "markdown" / "exlex"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import offline                                      # noqa: E402
import serve                                        # noqa: E402

store = serve.studio.store
STUDIO = serve.STUDIO_BASE


# THE PHONE-KEEPING MEMORIES GO TO A FOLDER OF THIS FILE'S OWN (TO-DO §2.25).
# Every test here asks lib/offline.py what a thing is made of, and the answer
# is remembered in `offline.DIGESTS` and `offline.WHERES`: config/digests.json
# and config/wheres.json beside the checkout, which are the owner's.  Left
# there, this file wrote about a hundred entries a run into his digests, each
# named by the path of one of its own temporary books.  Patched for as long as
# the module runs, as tests/test_wave_estimate.py patches them -- and the
# memories themselves with them, which lib/offline.py keeps between calls: a
# memory read in here, or learnt and not yet written, would otherwise go on
# into the next module and be written wherever the stores point by then.
_scratch = None
_patches = []


def setUpModule():
    global _scratch
    _scratch = tempfile.TemporaryDirectory()
    config = Path(_scratch.name) / "config"
    _patches[:] = [mock.patch.object(offline, "DIGESTS", str(config / "digests.json")),
                   mock.patch.object(offline, "WHERES", str(config / "wheres.json")),
                   mock.patch.object(offline, "_digests", None),
                   mock.patch.object(offline, "_digests_new", False),
                   mock.patch.object(offline, "_wheres_store", None),
                   mock.patch.object(offline, "_wheres_store_new", False)]
    for p in _patches:
        p.start()


def tearDownModule():
    for p in reversed(_patches):
        p.stop()
    _scratch.cleanup()


# Five notes, because the owner named five kinds of them and each one is a
# different sentence in his decision: a plain one, one with a picture, one
# with a recording, one that holds an exercise, one with a formula.
PLAIN = """---
title: On the fable
lang: en
target: fa
anchor: after sub 1.1-aaaa
---

The idiom in this line is the one from chapter two.
"""

WITH_PICTURE = """---
title: With a plate
lang: en
target: fa
anchor: after sub 1.2-bbbb
---

The plate the edition prints here:

![the plate](images/plate.jpg)
"""

WITH_RECORDING = """---
title: Said aloud
lang: en
target: fa
anchor: after sub 1.3-cccc
---

How the line sounds when it is read out.
"""

WITH_EXERCISE = """---
title: Drill on the idiom
lang: en
target: fa
anchor: after sub 1.4-dddd
---

:::exercise fill-blanks
prompt: Complete it.
content-direction: target
text: The cat is [[one]].
- [one] [گربه]{tl}
- [ ] [سگ]{tl}
:::
"""

WITH_MATHS = """---
title: The counting of it
lang: en
target: fa
anchor: after sub 1.5-eeee
---

The metre comes to [a^2+b^2]{math} feet.
"""

ALL_FIVE = {"plain": PLAIN, "picture": WITH_PICTURE, "sound": WITH_RECORDING,
            "exercise": WITH_EXERCISE, "maths": WITH_MATHS}

PICTURE_BYTES = 4321
SOUND_BYTES = 2000002

BOOK_BASE = "/books/persian/kelile/"
VIDEO_ID = "abc123XYZ"


class Made:
    """A book or a video on a temporary disk, with notes written beside it.

    It holds the ids the store gave each note back, because a test that wants
    to edit "the note with the exercise in it" has no other way to name it:
    the id is made from the title and a hash, and it is the store's to give.
    """

    def __init__(self, root, content_dir, ids):
        self.root, self.dir, self.ids = root, content_dir, ids

    def notes(self):
        """What the door hands lib/offline.py -- the real one, not a fake."""
        return serve.notes_to_keep(self.dir)

    def book(self):
        rec = offline.book(self.dir, BOOK_BASE, self.notes(), STUDIO)
        rec["shared"] = offline.shared() + (rec.get("shared") or [])
        rec.update(offline.totals(rec))
        return rec

    def video(self):
        rec = offline.video(self.dir, VIDEO_ID, "/youtube", self.notes(), STUDIO)
        rec["shared"] = offline.shared() + (rec.get("shared") or [])
        rec.update(offline.totals(rec))
        return rec

    def write(self, key, markdown):
        """A note saved as the editor's Save saves it.

        The clock is moved on for the length of the save because the store
        stamps a document to the SECOND (`store._now`) and the record stamps
        a note by that stamp alone: two things done inside one second are one
        moment as far as `updated` can tell, and a test that raced the clock
        would be green or red by luck.  A person editing a note an hour after
        keeping the book is what this stands for.
        """
        was = store.use_library(serve.studio.notes.dir_for(self.dir))
        try:
            with mock.patch.object(store, "_now", lambda: "2026-09-23T23:59:59"):
                store.save(self.ids[key], markdown)
        finally:
            store.use_library(was)

    def add(self, markdown):
        was = store.use_library(serve.studio.notes.dir_for(self.dir))
        try:
            return store.create(markdown, tags=["note"])["id"]
        finally:
            store.use_library(was)

    def delete(self, key):
        was = store.use_library(serve.studio.notes.dir_for(self.dir))
        try:
            store.delete(self.ids[key])
        finally:
            store.use_library(was)


class Ground(unittest.TestCase):
    """What every test here stands on: a thing on the disk, and its notes."""

    def make(self, kind="book", which=ALL_FIVE, picture=True, sound=True):
        """`picture` and `sound` are knobs and not decoration: a size is
        claimed here only by building the same thing twice and subtracting,
        and that needs two trees whose only difference is the one file."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        if kind == "book":
            d = root / "books" / "persian" / "kelile"
            (d / "reader").mkdir(parents=True)
            (d / "reader" / "index.html").write_text("<html>the book</html>",
                                                     encoding="utf-8")
            (d / "book.json").write_text(json.dumps({"title": "Kelile",
                                                     "narrations": []}),
                                         encoding="utf-8")
        else:
            d = root / "youtube" / "videos" / "persian" / VIDEO_ID
            d.mkdir(parents=True)
            (d / "video.json").write_text(json.dumps({"title": "A talk"}),
                                          encoding="utf-8")
            (d / "annotations.json").write_text("{}", encoding="utf-8")
            (d / "transcript.txt").write_text("0.0 the first line\n",
                                              encoding="utf-8")
        ids = {}
        notes_dir = serve.studio.notes.dir_for(str(d))
        notes_dir.mkdir(parents=True, exist_ok=True)
        was = store.use_library(notes_dir)
        try:
            for key, markdown in which.items():
                meta = store.create(markdown, tags=["note"])
                ids[key] = meta["id"]
                doc = Path(str(store.doc_dir(meta["id"])))
                if key == "picture" and picture:
                    (doc / "images").mkdir(exist_ok=True)
                    (doc / "images" / "plate.jpg").write_bytes(b"x" * PICTURE_BYTES)
                if key == "sound" and sound:
                    (doc / "audio").mkdir(exist_ok=True)
                    (doc / "audio" / "said.mp3").write_bytes(b"y" * SOUND_BYTES)
        finally:
            store.use_library(was)
        return Made(root, str(d), ids)

    def group(self, rec):
        """The notes' half of the record, with the addresses behind the one
        tick laid out as `urls` -- which is what the sheet fetches when the
        row is ticked, and what these tests are about.  Every entry in the
        record itself stands for ONE address (lib/offline.py's header): the
        grouping is the sheet's, where the owner sees it."""
        g = rec.get("notes")
        self.assertTrue(g, "the notes are their own half of the record: %r"
                        % (sorted(rec),))
        g = dict(g)
        g["urls"] = [x["url"] for x in (g.get("small") or [])]
        return g

    def shared_urls(self, rec):
        """What the STUDIO lends the phone for the notes' sake, which lives
        inside the notes' own half of the record.  It is not in the record's
        `shared` -- that is what every page of the app needs, fetched on any
        first keep -- because these four megabytes must be fetched only when
        the notes row is ticked: a person who keeps the text of a book and is
        told it costs a few hundred kilobytes may not be handed four."""
        return [x["url"] for x in ((rec.get("notes") or {}).get("shared") or [])]

    def notes_row(self, rec):
        """The notes' recordings: one row on the sheet, one entry each in the
        record, so that ticking the row fetches the sounds themselves."""
        rows = (rec.get("notes") or {}).get("media") or []
        if not rows:
            return None
        return {"url": rows[0]["url"], "kind": rows[0].get("kind"),
                "covers": rows[0].get("covers"), "count": len(rows),
                "bytes": sum(r.get("bytes") or 0 for r in rows), "rows": rows}


class OneTickBesideTheRecordings(Ground):
    """His first decision: *its notes · 34 · about 280 kB*, which can be
    unticked -- not folded into the text, where they would be kept whether he
    asked for them or not, and not thirty-four rows burying the two narrations
    he came to the sheet for."""

    def test_the_notes_are_one_row_that_says_how_many_and_about_how_much(self):
        rec = self.make().book()
        g = self.group(rec)
        self.assertEqual([g["kind"], g["title"], g["count"], g["about"]],
                         ["notes", "its notes", 5, True])
        self.assertEqual(g["url"], BOOK_BASE + "notes",
                         "the row is named by the notes' own mount")
        self.assertGreater(len(g["urls"]), g["count"],
                           "one row, many addresses behind it: %r" % (g["urls"],))

    def test_the_size_is_the_owners_arithmetic_and_not_the_source_alone(self):
        """He said *a note's bare page is about 8 kB rendered; forty of them
        are a third of a megabyte*.  A sheet that measured `source.md` alone
        would have told him five notes cost half a kilobyte, which is the one
        number on that sheet nobody could act on."""
        made = self.make()
        g = self.group(made.book())
        sources = 0
        for d, _dirs, files in os.walk(serve.studio.notes.dir_for(made.dir)):
            if "source.md" in files:
                sources += os.path.getsize(os.path.join(d, "source.md"))
        per_note = (g["bytes"] - PICTURE_BYTES) / g["count"]
        self.assertGreater(g["bytes"], sources * 10,
                           "the page's wrapper is most of what a note costs "
                           "(%d bytes of source in all)" % sources)
        self.assertTrue(5000 <= per_note <= 20000,
                        "a note is about eight kilobytes rendered: %d" % per_note)

    def test_a_book_with_no_notes_is_exactly_what_it_was(self):
        """Nothing above may cost a book nobody has written a note beside: no
        group, no studio files, and the two halves still adding up."""
        made = self.make(which={})
        rec = offline.book(made.dir, BOOK_BASE, made.notes(), STUDIO)
        rec.update(offline.totals(rec))
        self.assertNotIn("notes", rec)
        self.assertNotIn("shared", rec)
        self.assertEqual(rec["media"], [])
        self.assertEqual(rec["bytes"], rec["small_bytes"] + rec["media_bytes"])
        self.assertEqual(rec["groups_bytes"], 0)

    def test_what_it_costs_is_said_in_three_parts(self):
        rec = self.make().book()
        self.assertEqual(rec["bytes"],
                         rec["small_bytes"] + rec["groups_bytes"] + rec["media_bytes"])
        self.assertGreater(rec["groups_bytes"], 0)
        self.assertEqual(rec["groups_bytes"], self.group(rec)["bytes"],
                         "a group is counted apart from the text, because it "
                         "is the one part of the answer that can be unticked")


class EveryNoteHasItsPage(Ground):
    """His third decision, and the whole point of the second: a kept note the
    reader cannot open, or cannot find, is not a kept note."""

    def test_each_note_is_there_at_the_address_the_reader_asks_for(self):
        made = self.make()
        urls = self.group(made.book())["urls"]
        for key, doc_id in made.ids.items():
            if key == "exercise":
                continue
            self.assertIn("%snotes/note/%s" % (BOOK_BASE, doc_id), urls,
                          "%s is kept at its bare page" % key)

    def test_the_bare_address_is_the_one_the_two_readers_really_ask_for(self):
        """Read off the readers themselves, because an address that is kept
        and an address that is asked for are two different facts and only
        their agreement is worth anything (`lib/tex2html.py` `noteUrl`,
        `youtube/lib/player.js` `holdNote`)."""
        for path in (ROOT / "lib" / "tex2html.py",
                     ROOT / "youtube" / "lib" / "player.js"):
            src = path.read_text(encoding="utf-8")
            self.assertIn("'/note/' + encodeURIComponent(id)", src,
                          "%s asks for a note at the bare address" % path.name)

    def test_a_note_holding_an_exercise_keeps_its_full_studio_page(self):
        """Without the studio's scripts an exercise is a box that cannot be
        answered, which is why `page_note` sends such a note to the document
        page at the desk; away from the desk it must open exactly as it does
        there."""
        made = self.make()
        urls = self.group(made.book())["urls"]
        doc_id = made.ids["exercise"]
        self.assertIn("%snotes/doc/%s" % (BOOK_BASE, doc_id), urls)

    def test_the_exercise_note_is_reachable_from_the_mark_as_well(self):
        """THE ADDRESS A MARK GOES TO IS THE BARE ONE, whatever the note holds.

        At the desk the bare address answers such a note with a redirect to
        the document page and the reader remembers the id; away from the desk
        there is no redirect to see, and the reader's own comment says what it
        expects instead -- the kept page handed back *at the bare address*,
        recognised by the `data-page="doc"` the studio writes on it.  With
        only the document address kept, the mark's fetch finds nothing, the
        frame navigates to an address no cache holds, and the one note that
        was kept whole is the one note that cannot be opened.
        """
        made = self.make()
        urls = self.group(made.book())["urls"]
        self.assertIn("%snotes/note/%s" % (BOOK_BASE, made.ids["exercise"]), urls,
                      "the bare address is what the mark opens; the document "
                      "page is what the frame is then sent to, so BOTH belong "
                      "in the group (lib/tex2html.py, holdNote and ntShow)")

    def test_the_marks_travel_with_them(self):
        """The reader draws a mark from `<mount>/api/marks` and from nothing
        else, so a kept note whose list stayed behind is a page nothing on the
        phone can reach."""
        rec = self.make().book()
        self.assertIn(BOOK_BASE + "notes/api/marks", self.group(rec)["urls"])

    def test_the_marks_list_is_a_door_by_the_workers_own_test(self):
        """A door is asked of the computer first and answered from the phone
        only when it cannot be reached -- which is what makes a note written
        at the desk this morning show its mark the moment the phone is home
        (his seventh decision).  Asked of `lib/sw.js`'s own `isDoor` rather
        than of a copy of it written out here."""
        import re
        sw = (ROOT / "lib" / "sw.js").read_text(encoding="utf-8")
        body = sw.split("function isDoor(url) {", 1)[1].split("}", 1)[0]
        patterns = [re.compile(p.replace("\\/", "/").replace("/", r"\/"))
                    for p in re.findall(r"/(\S+?)/\.test", body)]
        self.assertTrue(patterns, "isDoor's own tests were found: %r" % body)
        marks = BOOK_BASE + "notes/api/marks"
        self.assertTrue(any(p.search(marks) for p in patterns),
                        "%s is a door to the worker" % marks)
        page = BOOK_BASE + "notes/note/on-the-fable-abc123"
        self.assertFalse(any(p.search(page) for p in patterns),
                         "a note's own page is a file and not a door")


class ThePicturesComeTheRecordingsAreARow(Ground):
    """His sixth decision, which is one sentence with two halves: a picture is
    part of reading the note, a recording is megabytes nobody asked for."""

    def test_a_notes_picture_is_in_the_group_and_costs_exactly_what_it_is(self):
        """Measured by subtraction -- the same five notes, one tree with the
        plate beside its note and one without -- so the number is the file's
        own size and not this file's opinion of how sizes are added up.  The
        pages weigh ABOUT what they weigh; a picture is a file, and a file is
        weighed exactly."""
        made = self.make()
        with_it = self.group(made.book())
        without = self.group(self.make(picture=False).book())
        self.assertEqual([with_it["pictures"], without["pictures"]], [1, 0])
        self.assertEqual([u for u in with_it["urls"] if u.endswith("plate.jpg")],
                         [BOOK_BASE + "notes/media/%s/images/plate.jpg"
                          % made.ids["picture"]],
                         "kept under its own note, where the render asks for it")
        self.assertEqual(with_it["bytes"] - without["bytes"], PICTURE_BYTES)

    def test_the_notes_recordings_are_one_row_beside_the_narrations(self):
        rec = self.make().book()
        row = self.notes_row(rec)
        self.assertIsNotNone(row, "a row for them: %r" % ((rec.get("notes") or {}).get("media"),))
        self.assertEqual([row["kind"], row["count"], row["bytes"]],
                         ["recording", 1, SOUND_BYTES])
        self.assertEqual(len(row["rows"]), 1,
                         "one entry per file, drawn as one row: the sheet counts them")
        self.assertIn("the notes", row.get("covers") or "",
                      "the row says whose recordings they are")
        self.assertNotIn(row["url"], self.group(rec)["urls"],
                         "and they are NOT in the tick that keeps the notes: "
                         "twelve megabytes are never kept by surprise")

    def test_a_recording_is_not_folded_into_the_notes_size(self):
        made = self.make()
        self.assertLess(self.group(made.book())["bytes"], SOUND_BYTES,
                        "the notes' own row must not carry the weight of "
                        "their recordings, or the tick would lie")


class WhatANoteOpensOn(Ground):
    """His third, fourth and fifth decisions, which are one thing said three
    ways: the studio's own files are paid ONCE FOR THE PHONE."""

    def test_the_studios_files_are_named_at_the_studios_own_address(self):
        """Under this book's notes mount they would be a second copy for every
        book on the shelf, and the phone would hold ten of each."""
        rec = self.make().book()
        studio = [u for u in self.shared_urls(rec) if "/static/" in u]
        self.assertTrue(studio, "the studio lends the phone something")
        for url in studio:
            self.assertTrue(url.startswith(STUDIO + "/static/"),
                            "%s is not at the studio's own address" % url)
        self.assertFalse([u for u in self.shared_urls(rec)
                          if u.startswith(BOOK_BASE)],
                         "nothing shared is under this one book")

    def test_the_sheet_a_bare_note_is_set_on_is_named(self):
        """It was named nowhere until this was built, and `note.html` links it
        and nothing else: a kept note whose sheet stayed behind opens as
        unstyled markup."""
        rec = self.make().book()
        self.assertIn(STUDIO + "/static/sheet.css", self.shared_urls(rec))
        self.assertIn(STUDIO + "/static/langs.css", self.shared_urls(rec))

    def test_the_studios_scripts_come_where_a_note_holds_an_exercise(self):
        with_it = self.shared_urls(self.make().book())
        without = self.shared_urls(self.make(which={"plain": PLAIN}).book())
        self.assertIn(STUDIO + "/static/app.js", with_it)
        self.assertIn(STUDIO + "/static/exform.js", with_it)
        self.assertNotIn(STUDIO + "/static/exform.js", without,
                         "a shelf of plain notes does not pay for the form "
                         "that answers an exercise")

    def test_all_thirteen_faces_travel_once(self):
        """Nothing kept them before -- they are named only inside `url()` calls
        in the sheet, which nothing but a browser reads -- so a kept document
        rendered in whatever face the phone happened to have."""
        rec = self.make().book()
        faces = [x for x in ((rec.get("notes") or {}).get("shared") or [])
                 if "/static/fonts/" in x["url"]]
        on_disk = [n for n in os.listdir(ROOT / "markdown" / "app" / "static" / "fonts")
                   if n.lower().endswith(offline.FACES)]
        self.assertEqual(sorted(f["url"].rsplit("/", 1)[-1] for f in faces),
                         sorted(on_disk),
                         "every face the sheet is set in, read off the "
                         "directory rather than off a list nobody updates")
        self.assertGreater(sum(f["bytes"] for f in faces), 1_000_000,
                           "weighed, because 1.83 MB is worth saying")
        self.assertEqual(len(faces), len(set(f["url"] for f in faces)),
                         "once, not once per note")

    def test_mathjax_comes_only_where_a_note_has_a_formula(self):
        heavy = STUDIO + "/static/mathjax/tex-svg.js"
        with_it = self.shared_urls(self.make().book())
        without = self.shared_urls(self.make(which={"plain": PLAIN,
                                                    "picture": WITH_PICTURE}).book())
        self.assertIn(heavy, with_it, "the two megabytes where there is maths")
        self.assertNotIn(heavy, without, "and not a byte of them where there is none")
        weight = [x["bytes"] for x in self.make().book()["notes"]["shared"]
                  if x["url"] == heavy]
        self.assertGreater(weight[0], 1_000_000,
                           "at the address the loader really goes on to ask "
                           "for, which is where the weight is")

    def test_the_maths_is_asked_of_the_render_and_not_of_a_dollar_sign(self):
        """`$` and `\\(` are ordinary characters in this toolbox's dialect: a
        note about a price must not fetch two megabytes, and one written in
        the dialect must."""
        price = PLAIN.replace("The idiom in this line is the one from chapter two.",
                              "It cost $5, and \\(nothing\\) more.")
        got = self.make(which={"plain": price}).notes()
        self.assertEqual([n["maths"] for n in got], [False], got)
        self.assertEqual([n["maths"] for n in
                          self.make(which={"maths": WITH_MATHS}).notes()], [True])

    def test_whether_a_note_holds_an_exercise_is_asked_of_the_render(self):
        """Only the render knows what a block became -- a malformed exercise
        block is still an exercise box on the page -- and getting it wrong
        keeps a bare page for a note the server will not serve bare."""
        made = self.make()
        asked = {n["id"]: n["exercises"] for n in made.notes()}
        self.assertEqual({key: asked[doc_id] for key, doc_id in made.ids.items()},
                         {"plain": False, "picture": False, "sound": False,
                          "exercise": True, "maths": False})


class TheVersionMoves(Ground):
    """His seventh decision.  The marks list is re-read whenever the computer
    is there, so a new note's mark appears at once; and the version moves, so
    the out-of-date bar offers to keep it again in one tap.

    THE NOTES CARRY A VERSION OF THEIR OWN, beside the thing's.  Folded into
    one, a note written at the desk would tell somebody who deliberately kept
    a book WITHOUT its notes that what he has is out of date -- and the press
    he was offered would fetch him nothing he had asked for.  So lib/keep.js
    compares the two apart: the thing's version speaks to everybody, the
    notes' only to whoever kept the notes."""

    def test_a_note_edited_moves_the_notes_version(self):
        made = self.make()
        was = made.book()
        made.write("plain", PLAIN.replace("chapter two", "chapter nine"))
        now = made.book()
        self.assertNotEqual(now["notes"]["version"], was["notes"]["version"])
        self.assertEqual(now["version"], was["version"],
                         "and leaves the book's own alone: nothing of the "
                         "text, the pictures or the recordings changed")

    def test_a_note_written_moves_it(self):
        made = self.make()
        was = made.book()["notes"]["version"]
        made.add(PLAIN.replace("On the fable", "A sixth note"))
        now = made.book()
        self.assertNotEqual(now["notes"]["version"], was)
        self.assertEqual(self.group(now)["count"], 6)

    def test_a_note_deleted_moves_it_and_takes_its_addresses_away(self):
        """Which is how the phone can find what the computer no longer has
        (his eighth decision): what is in the thing's cache and in no list any
        more is what the next Save gives back."""
        made = self.make()
        before = self.group(made.book())["urls"]
        made.delete("picture")
        after = self.group(made.book())
        gone = [u for u in before if u not in after["urls"]]
        self.assertEqual(after["count"], 4)
        self.assertTrue(any(u.endswith("/images/plate.jpg") for u in gone),
                        "the picture goes with the note it was in: %r" % gone)
        self.assertTrue(any("/note/" in u for u in gone), gone)

    def test_the_book_itself_changing_still_moves_it(self):
        """The book's own version is untouched by any of this: a rebuilt
        reader moves it, and the bar says so to everybody, whether or not
        they kept the notes."""
        made = self.make()
        was = made.book()["version"]
        (Path(made.dir) / "reader" / "index.html").write_text(
            "<html>the book, rebuilt</html>", encoding="utf-8")
        self.assertNotEqual(made.book()["version"], was)


class TheVideoIsTheMirror(Ground):
    """His ninth decision: he asked for both, and the two readers' note code
    is a mirror, so the two records are one shape."""

    def test_a_videos_notes_are_the_same_row_under_the_videos_own_mount(self):
        made = self.make("video")
        rec = made.video()
        g = self.group(rec)
        mount = "/youtube/v/%s/notes" % VIDEO_ID
        self.assertEqual([g["kind"], g["title"], g["count"]], ["notes", "its notes", 5])
        self.assertEqual(g["url"], mount)
        self.assertIn(mount + "/api/marks", g["urls"])
        self.assertIn(mount + "/note/" + made.ids["plain"], g["urls"])
        self.assertIn(mount + "/doc/" + made.ids["exercise"], g["urls"])

    def test_a_videos_notes_recordings_are_one_row_too(self):
        rec = self.make("video").video()
        row = self.notes_row(rec)
        self.assertIsNotNone(row, (rec.get("notes") or {}).get("media"))
        self.assertEqual([row["count"], row["bytes"]], [1, SOUND_BYTES])

    def test_a_videos_notes_lean_on_the_same_one_copy_of_the_studio(self):
        rec = self.make("video").video()
        urls = self.shared_urls(rec)
        self.assertIn(STUDIO + "/static/sheet.css", urls)
        self.assertFalse([u for u in urls if u.startswith("/youtube/v/")],
                         "nothing the studio lends belongs to one video")

    def test_a_video_with_no_notes_is_exactly_what_it_was(self):
        made = self.make("video", which={})
        rec = offline.video(made.dir, VIDEO_ID, "/youtube", made.notes(), STUDIO)
        rec.update(offline.totals(rec))
        self.assertNotIn("notes", rec)
        self.assertEqual(rec["bytes"], rec["small_bytes"] + rec["media_bytes"])


class TheDoorGathersAndNothingBreaks(Ground):
    """`lib/` must not import the studio -- a reader, a bundle and the launcher
    all lean on it and none of them has a studio -- so `serve.py` looks and
    `lib/offline.py` is handed the answer.  These are the two ways that hand
    can come back empty, and neither may cost somebody a kept book."""

    def test_a_thing_with_no_markdown_folder_is_kept_without_notes(self):
        made = self.make(which={})
        self.assertEqual(made.notes(), [])
        self.assertIsNotNone(made.book())

    def test_a_note_that_will_not_render_is_still_kept(self):
        """Keeping it is never worse than leaving it behind: its page renders
        there or says why."""
        broken = "---\ntitle: A broken one\nlang: en\ntarget: fa\n---\n\n:::exercise\n"
        made = self.make(which={"plain": PLAIN, "broken": broken})
        self.assertEqual(self.group(made.book())["count"], 2)

    def test_the_library_is_put_back_after_the_door_has_looked(self):
        """Both are thread-local: a request that left this thread pointing at
        somebody's book would serve the wrong library to whoever asked next."""
        made = self.make()
        was = str(store.lib())
        made.notes()
        self.assertEqual(str(store.lib()), was)


class TheSheetReadsWhatTheDoorAnswers(Ground):
    """A RECORD NOBODY DRAWS KEEPS NOTHING.

    The door's answer and the keep sheet are two files written apart, and
    everything above is true of the answer alone: the notes are gathered,
    weighed, addressed -- and if `lib/keep.js` looks for them under another
    name it draws no row, the owner is never asked, and not one note reaches
    the phone.  `tests/mobile_pages.mjs` proves the whole of it by driving a
    phone; this is the cheap half of the same question, asked of the sheet's
    own line so that the unit suite says it too.
    """

    def test_the_sheet_looks_for_the_notes_where_the_door_puts_them(self):
        keep = (ROOT / "lib" / "keep.js").read_text(encoding="utf-8")
        lines = [ln.strip() for ln in keep.splitlines()
                 if "kind: 'notes'" in ln or "rec.notes" in ln or "rec.groups" in ln]
        self.assertTrue(lines, "lib/keep.js says nowhere where it looks for the "
                               "notes: this test has gone stale, or the row has")
        rec = self.make().book()
        wanted = "rec.groups" if "groups" in rec else "rec.notes"
        self.assertTrue(any(wanted in ln for ln in lines),
                        "the door answers with %s and the sheet reads %r: the notes "
                        "are gathered and never drawn, so the row cannot be ticked "
                        "and nothing of them is kept"
                        % (wanted, "; ".join(lines)))


class ANotesRowCanBeChecked(Ground):
    """A TICK THE PHONE CAN TEST, AND A PROMISE IT MUST NOT BE GIVEN.

    The owner's 3 of 2026-09-23 -- *"the boxes should by default show the
    things that are actually kept in memory, and there should be a check of
    this, it should actually look for the file and check that the download was
    complete and correct"* -- changed what an entry in this record MEANS.  A
    box is no longer ticked because the address is a key in a cache; the
    worker opens the body and tests it against what the record promised.

    Which is why the notes are the delicate case, and why these tests are
    here rather than with the other record tests.  A note's page does not
    exist as a file: the computer RENDERS it as it sends it, and what
    lib/offline.py weighs for it is the source on the disk plus the measured
    template wrapper -- an honest guess at what it will cost the owner and
    never the answer's own byte count.  Measured against that guess, every
    note page on the phone would be judged broken, every Save would fetch
    them all again, and the row would never tick: a worse fault than the one
    being mended, and one the owner would see as "it keeps re-downloading my
    notes".  So those entries say `check: "here"` -- test that you HAVE this
    answer, and test nothing else about it -- and a note's PICTURES and
    RECORDINGS, which are files streamed verbatim, carry real digests.
    """

    def small(self, rec):
        return {x["url"]: x for x in ((rec.get("notes") or {}).get("small") or [])}

    def test_a_notes_page_promises_only_that_it_is_here(self):
        made = self.make(which={"plain": PLAIN})
        rec = made.book()
        pages = [x for u, x in self.small(rec).items() if "/note/" in u or "/doc/" in u]
        self.assertTrue(pages, "the note's own page is what the reader opens")
        for x in pages:
            self.assertEqual(x.get("check"), "here", x["url"])
            self.assertNotIn("digest", x, x["url"])
            self.assertGreater(x.get("bytes") or 0, 0,
                               "it still says what it will cost him: %s" % x["url"])

    def test_the_seams_list_promises_only_that_it_is_here(self):
        """It is a door -- the computer first, this copy behind it -- and its
        answer is composed from the book's marks every time it is asked."""
        made = self.make(which={"plain": PLAIN})
        marks = [x for u, x in self.small(made.book()).items() if u.endswith("/api/marks")]
        self.assertEqual(len(marks), 1, "the marks travel, once")
        self.assertEqual(marks[0].get("check"), "here")

    def test_a_notes_picture_carries_a_real_digest(self):
        """A file the server streams byte for byte is a file the phone can be
        asked to hash, and a picture is exactly where the old lie bit: an
        HTML page answered where a picture was asked for left a key in the
        cache and ticked a box."""
        made = self.make(which={"picture": WITH_PICTURE})
        pics = [x for u, x in self.small(made.book()).items() if u.endswith(".jpg")]
        self.assertEqual(len(pics), 1, "the picture comes with the notes")
        self.assertRegex(pics[0]["digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(pics[0]["digest"],
                         hashlib.sha256(b"x" * PICTURE_BYTES).hexdigest(),
                         "and it is the digest of the bytes that will be sent")
        self.assertEqual(pics[0]["bytes"], PICTURE_BYTES)

    def test_a_notes_recording_is_checked_like_anything_else_its_size(self):
        """Decision A reads as if a recording were checked by length alone;
        a SMALL recording is hashed like any other small file, and a large
        one is weighed.  The owner's decision is the size -- "digest the small
        files, length for the big ones" -- and a note's recording is kilobytes.
        Exempting recordings by kind lost the half of his decision that
        matters most here: a length catches a download cut short and nothing
        else, while the suite's own damage is one byte flipped in the middle
        of a kept recording, which only a digest can see."""
        import offline
        made = self.make(which={"sound": WITH_RECORDING})
        row = self.notes_row(made.book())
        self.assertIsNotNone(row, "the notes' recordings are their own row")
        entry = row["rows"][0]
        self.assertLess(entry["bytes"], offline.DIGEST_MAX_MEDIA)
        self.assertEqual(entry["digest"], hashlib.sha256(b"y" * SOUND_BYTES).hexdigest())
        # and the ceiling a recording is measured against is its own, far
        # lower than a page's: one book's fifty narrations had 128.9 MB hashed
        # at every press of the door under a single eight-megabyte ceiling
        self.assertLess(offline.DIGEST_MAX_MEDIA, offline.DIGEST_MAX)

    def test_what_the_studio_lends_is_a_file_or_says_it_is_not(self):
        """The thirteen faces and MathJax are files on the disk and carry
        digests; the studio's three MADE-UP ones -- langs.css written out of
        the language registry, app.css and app.js joined as they go out --
        have no length this file can predict and say so."""
        made = self.make()
        lent = {x["url"]: x for x in ((made.book().get("notes") or {}).get("shared") or [])}
        self.assertTrue(lent, "a note opens on the studio's own sheet")
        for url, x in lent.items():
            if x.get("check") == "here":
                self.assertNotIn("digest", x, url)
                continue
            self.assertRegex(x.get("digest", ""), r"^[0-9a-f]{64}$", url)
            self.assertGreater(x["bytes"], 0, url)

    def test_the_sheet_passes_the_promise_on_and_the_worker_reads_it(self):
        """The record saying it is not enough: lib/keep.js gathers the notes'
        entries into the `want` list it sends, and lib/sw.js must answer
        `here` for them.  Dropped by either, every note row goes untickable."""
        keep = (ROOT / "lib" / "keep.js").read_text(encoding="utf-8")
        self.assertIn("check: x.check || ''", keep, "the sheet passes it on")
        self.assertIn("noteSmall, noteShared, nmedia", keep,
                      "and the notes' own three lists are in what it asks about")
        sw = (ROOT / "lib" / "sw.js").read_text(encoding="utf-8")
        self.assertIn("if (want.check === 'here') return true;", sw)


if __name__ == "__main__":
    unittest.main()
