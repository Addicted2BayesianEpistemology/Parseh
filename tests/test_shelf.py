#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A whole shelf of books, or of videos, backed up and put back.

    python3 -m unittest discover -s tests -p test_shelf.py

WHAT HAS TO HOLD.  The studio has had a Backup button and a Load from
backup button for its library since the library existed; lib/shelf.py is
the same pair for the three other shelves.  What it must be is:

  a) A ZIP OF BUNDLES, not a zip of the tree.  Every book and every video
     already has a door -- lib/bundle.py -- whose allowlist is read in both
     directions, and whose budgets (MAX_ENTRIES, MAX_UNPACKED) are per
     bundle.  A flat zip of books/ would walk past the first and blow the
     second.  So what comes out holds one bundle per item, and can be taken
     apart and fed to the "bring a book back" panel one at a time.
  b) WHAT IS HERE IS KEPT until replacing it is asked for.  The studio's
     rule, for the studio's reason: a restore is not a merge, and the
     backup is usually the older of the two.
  c) IT REFUSES WHAT IT SHOULD, and says so as somebody would read it: a
     zip that is not one, a backup of the other shelf, a bundle that is not
     what its shelf takes.
  d) ONE BAD ITEM IS NOT A BAD BACKUP.  A book nobody can pack is a note in
     the manifest and forty other books in the zip; an item that will not
     install is a warning and the rest still go back.

EVERY TEST RUNS UNDER ITS OWN ROOT and passes it explicitly, because a
shelf walks directories: a test that forgot would enumerate -- and install
into -- the machine's real books/.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for folder in ("lib", "youtube/lib"):
    sys.path.insert(0, os.path.join(REPO, folder))

import bundle                                      # noqa: E402
import shelf                                       # noqa: E402
import ytpages                                     # noqa: E402

BOOK_FIXTURES = [("english", "mini-en"), ("arabic", "mini-ar")]
VIDEO_FIXTURES = [("persian", "fA6bK2mQ8sT"), ("english", "eN5wX7zA9bC")]


class ShelfCase(unittest.TestCase):
    kind = "book"

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = self.td.name
        self.addCleanup(self.td.cleanup)
        if self.kind == "book":
            for folder, slug in BOOK_FIXTURES:
                src = os.path.join(REPO, "tests/fixtures/books", folder, slug)
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(self.root, "books", folder, slug))
        else:
            for folder, vid in VIDEO_FIXTURES:
                src = os.path.join(REPO, "tests/fixtures/videos", folder, vid)
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(
                        self.root, "youtube", "videos", folder, vid))
            self.videos = os.path.join(self.root, "youtube", "videos")
            p = mock.patch.object(ytpages, "VIDEOS", self.videos)
            p.start()
            self.addCleanup(p.stop)

    def far(self):
        """A second, empty toolbox to restore into, so that a round trip
        says "it came back" and not "it never went away"."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        os.makedirs(os.path.join(td.name, "books"), exist_ok=True)
        os.makedirs(os.path.join(td.name, "youtube", "videos"), exist_ok=True)
        return td.name

    def pack(self, **kw):
        path, name = shelf.pack(self.kind, root=self.root, **kw)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        return path, name

    def names(self, root):
        return sorted(os.path.basename(d) for d in shelf.items(self.kind, root))


class Books(ShelfCase):
    kind = "book"

    def test_the_backup_is_one_bundle_for_each_book_and_a_manifest(self):
        path, name = self.pack()
        self.assertTrue(name.startswith("books-backup-") and name.endswith(".zip"), name)
        with zipfile.ZipFile(path) as zf:
            entries = sorted(zf.namelist())
            doc = json.loads(zf.read(shelf.MANIFEST))
        self.assertEqual(entries, ["mini-ar-book.zip", "mini-en-book.zip",
                                   shelf.MANIFEST])
        self.assertEqual(doc["format"], shelf.FORMAT)
        self.assertEqual(doc["kind"], "book")
        self.assertEqual(sorted(i["name"] for i in doc["items"]), ["mini-ar", "mini-en"])

    def test_each_bundle_in_it_is_one_the_single_door_takes(self):
        """The whole point of a zip of zips: half a restore by hand."""
        path, _ = self.pack()
        far = self.far()
        with zipfile.ZipFile(path) as zf:
            one = zf.read("mini-en-book.zip")
        what = bundle.inspect(one, root=far)
        self.assertEqual(what["kind"], "book")
        out = bundle.install(one, root=far)
        self.assertTrue(out["ok"], out)
        self.assertEqual(self.names(far), ["mini-en"])

    def test_book_backup_uses_linked_shape_without_recordings(self):
        book = os.path.join(self.root, "books", "english", "mini-en")
        path = os.path.join(book, "book.json")
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        meta["audio"] = "audio/voice.mp3"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f)
        os.makedirs(os.path.join(book, "audio"))
        with open(os.path.join(book, "audio", "voice.mp3"), "wb") as f:
            f.write(b"ID3")
        backup, _ = self.pack()
        with zipfile.ZipFile(backup) as shelf_zip:
            inner = shelf_zip.read("mini-en-book-linked.zip")
        with zipfile.ZipFile(io.BytesIO(inner)) as book_zip:
            self.assertNotIn("mini-en/audio/voice.mp3", book_zip.namelist())
            self.assertEqual(json.loads(book_zip.read("mini-en/book.json"))["audio"],
                             "audio/voice.mp3")

    def test_it_comes_back_into_an_empty_toolbox(self):
        path, _ = self.pack()
        far = self.far()
        out = shelf.restore("book", path, root=far)
        self.assertEqual(sorted(out["restored"]), ["mini-ar", "mini-en"])
        self.assertEqual((out["kept"], out["warnings"]), ([], []))
        self.assertEqual(self.names(far), ["mini-ar", "mini-en"])

    def test_what_is_already_there_is_kept_until_replacing_is_asked_for(self):
        path, _ = self.pack()
        far = self.far()
        shelf.restore("book", path, root=far)
        again = shelf.restore("book", path, root=far)
        self.assertEqual(again["restored"], [])
        self.assertEqual(sorted(again["kept"]), ["mini-ar", "mini-en"])
        forced = shelf.restore("book", path, replace=True, root=far)
        self.assertEqual(sorted(forced["restored"]), ["mini-ar", "mini-en"])
        self.assertEqual(forced["kept"], [])
        # and there is still one of each, not two
        self.assertEqual(self.names(far), ["mini-ar", "mini-en"])

    def test_a_shape_is_carried_through_to_every_bundle(self):
        path, _ = self.pack(mode="text")
        with zipfile.ZipFile(path) as zf:
            self.assertEqual(json.loads(zf.read(shelf.MANIFEST))["shape"], "text")

    def test_an_empty_shelf_backs_up_to_a_backup_with_nothing_in_it(self):
        empty = self.far()
        path, _ = shelf.pack("book", root=empty)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        with zipfile.ZipFile(path) as zf:
            self.assertEqual(zf.namelist(), [shelf.MANIFEST])
        with self.assertRaises(shelf.ShelfError) as e:
            shelf.restore("book", path, root=empty)
        self.assertIn("no books", str(e.exception))


class Videos(ShelfCase):
    kind = "video"

    def test_it_comes_back_into_an_empty_toolbox(self):
        path, name = self.pack()
        self.assertTrue(name.startswith("videos-backup-"), name)
        far = self.far()
        with mock.patch.object(ytpages, "VIDEOS",
                               os.path.join(far, "youtube", "videos")):
            out = shelf.restore("video", path, root=far)
            self.assertEqual(sorted(out["restored"]),
                             sorted(v for _f, v in VIDEO_FIXTURES))
            self.assertEqual((out["kept"], out["warnings"]), ([], []))
            self.assertEqual(self.names(far), sorted(v for _f, v in VIDEO_FIXTURES))

    def test_what_is_already_there_is_kept(self):
        path, _ = self.pack()
        far = self.far()
        with mock.patch.object(ytpages, "VIDEOS",
                               os.path.join(far, "youtube", "videos")):
            shelf.restore("video", path, root=far)
            again = shelf.restore("video", path, root=far)
        self.assertEqual(again["restored"], [])
        self.assertEqual(len(again["kept"]), len(VIDEO_FIXTURES))


class Refusals(ShelfCase):
    kind = "book"

    def test_a_file_that_is_not_a_zip(self):
        with self.assertRaises(shelf.ShelfError) as e:
            shelf.restore("book", b"not a zip at all", root=self.far())
        self.assertIn("not a zip", str(e.exception))

    def test_a_zip_that_is_not_a_backup(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("hello.txt", "hi")
        with self.assertRaises(shelf.ShelfError) as e:
            shelf.restore("book", buf.getvalue(), root=self.far())
        self.assertIn(shelf.MANIFEST, str(e.exception))

    def test_a_backup_of_the_other_shelf_is_refused_by_name(self):
        path, _ = self.pack()
        with self.assertRaises(shelf.ShelfError) as e:
            shelf.restore("video", path, root=self.far())
        self.assertIn("backup of books", str(e.exception))
        self.assertIn("videos go", str(e.exception))

    def test_there_is_no_shelf_of_something_else(self):
        for call in (lambda: shelf.pack("recipe"),
                     lambda: shelf.restore("recipe", b"", root=self.root),
                     lambda: shelf.items("recipe")):
            with self.assertRaises(shelf.ShelfError):
                call()

    def test_one_item_that_will_not_go_back_is_a_warning_and_no_more(self):
        """A backup of forty books must not be undone by the one of them
        somebody has corrupted."""
        path, _ = self.pack()
        far = self.far()
        with zipfile.ZipFile(path) as zf:
            good = {n: zf.read(n) for n in zf.namelist()}
        broken = os.path.join(self.root, "broken.zip")
        with zipfile.ZipFile(broken, "w") as zf:
            for n, data in good.items():
                zf.writestr(n, b"this is not a bundle" if n == "mini-ar-book.zip" else data)
        out = shelf.restore("book", broken, root=far)
        self.assertEqual(out["restored"], ["mini-en"])
        self.assertEqual(len(out["warnings"]), 1, out["warnings"])
        self.assertIn("mini-ar-book.zip", out["warnings"][0])
        self.assertEqual(self.names(far), ["mini-en"])


if __name__ == "__main__":
    unittest.main()
